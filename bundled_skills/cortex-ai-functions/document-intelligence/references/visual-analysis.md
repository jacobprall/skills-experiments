# Visual Analysis Workflow

Chart, diagram, and blueprint analysis using AI_COMPLETE vision.

## Use When

- User wants to analyze charts, graphs, plots
- User wants to interpret blueprints, schematics, technical drawings
- User wants to extract data from diagrams, flowcharts

## Constraints

| Constraint | Limit |
|------------|-------|
| Max image size | 10 MB (3.75 MB for Claude models) |
| Max resolution | 8000x8000 pixels |
| Supported formats | PNG, JPEG, TIFF, BMP, GIF, WEBP |

PDF files must be converted to images before analysis.

## Pricing

AI_COMPLETE with **claude-3-5-sonnet** (recommended for visual analysis):

| Token Type | Credits per Million |
|------------|---------------------|
| Input      | 1.50                |
| Output     | 7.50                |

**Formula:**
```
cost = (input_tokens × 1.50 + output_tokens × 7.50) / 1,000,000
```

**Quick estimates for claude-3-5-sonnet:**

| Scenario | Input Tokens | Output Tokens | Credits |
|----------|--------------|---------------|---------|
| 1 image | ~1,500 | ~500 | ~0.006 |
| 10 images | ~15,000 | ~5,000 | ~0.06 |
| 100 images | ~150,000 | ~50,000 | ~0.60 |

**Source**: [Snowflake Service Consumption Table](https://www.snowflake.com/legal-files/CreditConsumptionTable.pdf)

**Full pricing details:** See [ai-complete.md](../../references/ai-complete.md)

## REQUIRED: Read Reference First

**BEFORE executing any SQL**, read `../../references/ai-complete.md` to get the correct AI_COMPLETE syntax and patterns. This prevents errors from incorrect function signatures.

---

## Workflow

### 1. Get File Location [WAIT]

**If files are on Snowflake stage:** Get full stage path, proceed to Step 2.

**If files are local:** You must get the upload destination from the user. Do not create any stages or run any SQL until the user provides this information.

Ask: "Which database, schema, and stage name should I use? (e.g., MY_DB.MY_SCHEMA.MY_STAGE)"

Use the exact stage name the user provides. After user responds, create stage with server-side encryption:
```sql
CREATE STAGE IF NOT EXISTS db.schema.user_provided_stage_name 
DIRECTORY = (ENABLE = TRUE) 
ENCRYPTION = (TYPE = 'SNOWFLAKE_SSE');
```

Then upload the files.

### 2. Define Analysis Goal [WAIT]

Ask what to extract from the visuals. Examples by content type:
- Charts: data points, axis labels, trends, legend values
- Blueprints: dimensions, measurements, components, materials
- Diagrams: process steps, connections, labels, hierarchy

### 3. List Files and Handle PDFs [WAIT if PDFs]

Show available files.

If PDFs detected:
1. Inform user that AI_COMPLETE requires images
2. Ask which pages to convert (all, first only, or specific pages)
3. Create images stage with server-side encryption (SNOWFLAKE_SSE)
4. Create PDF-to-image conversion procedure using `pypdfium2` (see below)
5. Convert PDFs to images
6. Refresh images stage directory

**PDF Conversion Procedure (use pypdfium2 - it works in Snowflake):**

```sql
CREATE OR REPLACE PROCEDURE <db>.<schema>.convert_pdf_to_images(
    source_stage STRING,
    file_name STRING,
    dest_stage STRING,
    dpi INT DEFAULT 150
)
RETURNS VARIANT
LANGUAGE PYTHON
RUNTIME_VERSION = '3.11'
PACKAGES = ('snowflake-snowpark-python', 'pypdfium2', 'pillow')
HANDLER = 'convert_pdf'
AS
$$
import pypdfium2 as pdfium
import os

def convert_pdf(session, source_stage: str, file_name: str, dest_stage: str, dpi: int = 150):
    result = {"status": "success", "source_file": file_name, "images_created": 0, "image_files": []}
    try:
        session.file.get(f"{source_stage}/{file_name}", '/tmp/')
        local_path = f'/tmp/{os.path.basename(file_name)}'
        pdf = pdfium.PdfDocument(local_path)
        base_name = os.path.splitext(os.path.basename(file_name))[0]
        scale = dpi / 72
        for page_num in range(len(pdf)):
            page = pdf[page_num]
            bitmap = page.render(scale=scale)
            pil_image = bitmap.to_pil()
            img_filename = f'{base_name}_page_{page_num + 1}.png'
            img_path = f'/tmp/{img_filename}'
            pil_image.save(img_path, 'PNG')
            session.file.put(f'file://{img_path}', dest_stage, auto_compress=False, overwrite=True)
            result["image_files"].append(img_filename)
            result["images_created"] += 1
        pdf.close()
        return result
    except Exception as e:
        return {"status": "error", "message": str(e), "source_file": file_name}
$$;
```

**Important:** Use `pypdfium2`, NOT `pdf2image` - pdf2image requires poppler which is not available.

### 4. Cost Estimate

Display estimated cost for the test image, then proceed to test.

### 5. Single Image Test [WAIT]

Analyze ONE image only. Display full results.

Ask if user wants to proceed with batch processing for all remaining images.

### 6. Batch Process

Display batch cost for all images, then execute batch analysis.

### 7. Post-Processing [WAIT]

Offer options:
1. Done - I have what I need
2. Store results in a Snowflake table
3. Set up a pipeline for continuous processing

If storing in table, suggest pipeline setup afterward. Load `references/pipeline.md`.

---

## Stopping Points

| After Step | Wait For |
|------------|----------|
| 1 | File location (and upload destination if local) |
| 2 | Analysis goal defined |
| 3 | PDF page selection (if PDFs present) |
| 5 | Confirmation to proceed with batch |
| 7 | Post-processing choice |
