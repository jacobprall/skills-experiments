---
name: document-intelligence
description: "Extract, parse, and analyze documents using Snowflake Cortex AI. Routes to AI_EXTRACT (structured fields), AI_PARSE_DOCUMENT (full text), or AI_COMPLETE (visual analysis). Triggers: extract data from files, process documents, my files, my documents, PDF, image, invoice, contract, receipt, form, OCR, parse document, read document, get text, extract fields, document processing, file extraction, stage files, digitize."
parent_skill: cortex-ai-functions
---

# Document Intelligence

Entry point for all document processing tasks using Snowflake Cortex AI.

## ⚠️ CRITICAL: Always Display Pricing Before Execution

**BEFORE executing ANY AI function (AI_EXTRACT, AI_PARSE_DOCUMENT, AI_COMPLETE), you MUST:**

1. Calculate estimated cost based on file size/page count
2. Display the estimate to the user

**Quick Pricing Reference:**

| Function | Pricing | Example |
|----------|---------|---------|
| AI_EXTRACT | 5 credits / 1M tokens | 1,000 pages ≈ 3-5 credits |
| AI_PARSE_DOCUMENT (OCR) | 0.5 credits / 1,000 pages | 1,000 pages ≈ 0.5 credits |
| AI_PARSE_DOCUMENT (LAYOUT) | 3.33 credits / 1,000 pages | 1,000 pages ≈ 3.33 credits |
| AI_COMPLETE (claude-3-5-sonnet) | 1.50 input / 7.50 output per 1M tokens | 100 images ≈ 0.60 credits |

**Detailed pricing with formulas:** See [AI_EXTRACT](../references/ai-extract.md), [AI_PARSE_DOCUMENT](../references/ai-parse-doc.md), [AI_COMPLETE](../references/ai-complete.md)

**Never skip displaying pricing.** This is mandatory before any AI function execution.

---

## Reference Files

| Reference | Location | Use For |
|-----------|----------|---------|
| Extraction | `references/extraction.md` | Structured field/table extraction (AI_EXTRACT) |
| Parsing | `references/parsing.md` | Full text parsing (AI_PARSE_DOCUMENT) |
| Visual Analysis | `references/visual-analysis.md` | Charts, blueprints, diagrams (AI_COMPLETE) |
| Pipeline | `references/pipeline.md` | Post-processing, storage, automation |

## When to Use

- User wants to extract data from documents (PDFs, images, Office files)
- User mentions AI_EXTRACT or AI_PARSE_DOCUMENT
- User wants to process invoices, contracts, forms, reports
- User needs to analyze charts, blueprints, diagrams

---

## Workflow

1. **Determine extraction goal** - Ask user what they want to extract [WAIT]
2. **Get file location** - Snowflake stage, local file, or cloud storage [WAIT]
3. **Validate file type** - Infer from extension, check compatibility
4. **Execute flow** - Load appropriate sub-skill
5. **Post-processing** - Offer storage and pipeline options

---

## Step 1: Determine Extraction Goal [WAIT]

Ask the user what they want to extract:

```
What would you like to extract from your document?

1. Structured extraction - Specific fields or tables (e.g., invoice number, line items)
2. Full text parsing - Complete document text with or without layout preserved
3. Visual analysis - Charts, graphs, diagrams, blueprints

Or describe what you need in your own words.
```

**Route based on response:**

| User Mentions | Flow | Load |
|---------------|------|------|
| Specific fields, names, dates, amounts, IDs | Extraction | `references/extraction.md` |
| Tables with columns, line items | Extraction | `references/extraction.md` |
| Full text, all content, complete document | Parsing | `references/parsing.md` |
| Layout, formatting, structure preserved | Parsing | `references/parsing.md` |
| OCR, scanned document | Parsing | `references/parsing.md` |
| Charts, graphs, plots | Visual Analysis | `references/visual-analysis.md` |
| Diagrams, blueprints, schematics | Visual Analysis | `references/visual-analysis.md` |

**If multiple types needed:** Execute flows sequentially, completing each before starting the next.

---

## Step 2: Get File Location [WAIT]

Ask where files are stored:

```
Where is your file located?
1. Snowflake stage (e.g., @my_db.my_schema.my_stage)
2. Local file on my computer
3. Cloud storage (S3, Azure, GCS, Google Drive, etc.)
```

**Snowflake stage:** Get full path and proceed.

**Local file:** You must ask for the full stage path. Do not create any stages or run any SQL until the user provides this information.

Ask: "Which database, schema, and stage name should I use? (e.g., MY_DB.MY_SCHEMA.MY_STAGE)"

Use the exact stage name the user provides. After user responds, create stage with server-side encryption:
```sql
CREATE STAGE IF NOT EXISTS db.schema.user_provided_stage_name
  DIRECTORY = (ENABLE = TRUE)
  ENCRYPTION = (TYPE = 'SNOWFLAKE_SSE');
```
Upload using: `snow stage copy "<local_path>" @db.schema.user_provided_stage_name`

**Cloud storage:** Load `openflow` skill to set up connector.

---

## Step 3: Validate File Type

Infer file type from extension. Do NOT ask user.

**Supported formats:**

| Extension | AI_EXTRACT | AI_PARSE_DOCUMENT | AI_COMPLETE |
|-----------|------------|-------------------|-------------|
| .pdf | Yes | Yes | Yes (convert to image) |
| .png, .jpg, .jpeg, .tiff, .webp | Yes | Yes | Yes |
| .docx, .pptx | Yes | Yes | No |
| .html, .txt | Yes | Yes | No |
| .csv, .md, .eml | Yes | No | No |
| .xlsx, .xls, .doc, .ppt | No | No | No |

**Unsupported formats:** Suggest exporting to PDF or loading directly into Snowflake.

---

## Step 4: Execute Flow

Load the appropriate sub-skill based on Step 1:

- Structured fields/tables → `references/extraction.md`
- Full text/OCR → `references/parsing.md`
- Charts/diagrams/blueprints → `references/visual-analysis.md`

---

## Step 5: Post-Processing

After any flow completes, load `references/pipeline.md` for:
- One-time extraction (done)
- Store results in Snowflake table
- Set up continuous processing pipeline

**Important:** After storing results in a table, always suggest setting up a pipeline.

---

## Key Constraints

| Function | Max File Size | Max Pages | Output |
|----------|---------------|-----------|--------|
| AI_EXTRACT | 100 MB | 125 | JSON |
| AI_PARSE_DOCUMENT | 50 MB | 500 | Markdown |
| AI_COMPLETE | 10 MB (image) | N/A | Text |

---

## Follow-Up Requests

When user asks a follow-up question or wants to extract something different, re-evaluate which flow is best. Do not assume the same flow applies.

| User Wants | Best Flow |
|------------|-----------|
| Named fields (invoice_number, date) | Extraction |
| Table data with known columns | Extraction |
| Full document text with structure | Parsing |
| OCR from scanned documents | Parsing |
| Chart/graph interpretation | Visual Analysis |
| Blueprint/diagram analysis | Visual Analysis |

---

## Stopping Points

| After Step | Wait For |
|------------|----------|
| Step 1 | Extraction goal selection |
| Step 2 | File location |
| Step 5 | Post-processing choice |

## Output

Routes user to appropriate sub-skill, then assists with post-processing options.
