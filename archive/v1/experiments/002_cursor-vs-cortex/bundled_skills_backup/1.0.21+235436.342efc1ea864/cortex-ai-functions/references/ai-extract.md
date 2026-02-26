# AI_EXTRACT

Extract structured fields from text or documents into JSON output.

**Docs**: [docs.snowflake.com/en/sql-reference/functions/ai_extract](https://docs.snowflake.com/en/sql-reference/functions/ai_extract)

## ⚠️ CRITICAL: Always Display Pricing Before Execution

**You MUST calculate and display cost estimate before AI_EXTRACT calls.**

**Pricing (arctic_extract model):** 5 credits per million tokens

| Scale | Estimated Cost |
|-------|----------------|
| 1,000 pages | ~$10-15 (3-5 credits) |

**Formula:** `cost = tokens × (5 credits / 1M tokens)`

*See [AI Functions Costs](https://docs.snowflake.com/en/user-guide/snowflake-cortex/aisql#costs) for current rates.*

---

## TO_FILE Path Handling (READ THIS FIRST)

**This is the most common source of errors.** Follow these rules exactly:

### Rule 1: Stage path and filename are SEPARATE arguments

```sql
-- CORRECT: Two separate arguments
TO_FILE('@db.schema.mystage', 'invoice.pdf')

-- WRONG: Concatenated path
TO_FILE('@db.schema.mystage/invoice.pdf')
```

### Rule 2: Use the FILENAME only, not the path from LIST/DIRECTORY

When you run LIST or DIRECTORY, the output shows paths like `folder/invoice.pdf`. **Do NOT use this full path as the filename argument.** Extract just the filename.

**Example scenario:**
- User provides stage: `@mydb.myschema.docs`
- User wants file: `report.pdf`
- LIST shows: `files/report.pdf` (includes folder prefix)

```sql
-- WRONG: Using the path from LIST output
TO_FILE('@mydb.myschema.docs', 'files/report.pdf')

-- CORRECT: Using just the filename
TO_FILE('@mydb.myschema.docs', 'report.pdf')
```

### Rule 3: For batch processing, strip the folder prefix from relative_path

When processing files via DIRECTORY(), the `relative_path` column may include folder prefixes. Strip them:

```sql
-- If relative_path is 'files/report.pdf', extract just 'report.pdf'
SELECT 
    relative_path,
    AI_EXTRACT(
        file => TO_FILE('@mydb.myschema.docs', 
                        SPLIT_PART(relative_path, '/', -1)),  -- Gets just filename
        responseFormat => ['invoice_number', 'total']
    ):response AS result
FROM DIRECTORY(@mydb.myschema.docs)
WHERE relative_path ILIKE '%.pdf';
```

**Alternative:** If files are at root level of stage, `relative_path` can be used directly:

```sql
-- Only when relative_path equals filename (no folder prefix)
TO_FILE('@stage', relative_path)
```

### Rule 4: DDL commands do NOT use @ prefix

The `@` symbol is only used when **referencing** a stage in queries. DDL commands (ALTER, CREATE, DROP) use the stage name directly:

```sql
-- WRONG: Using @ in DDL
ALTER STAGE @mydb.myschema.mystage SET DIRECTORY = (ENABLE = TRUE);

-- CORRECT: No @ prefix for DDL
ALTER STAGE mydb.myschema.mystage SET DIRECTORY = (ENABLE = TRUE);
```

| Command Type | Use `@`? | Example |
|--------------|----------|---------|
| LIST | Yes | `LIST @db.schema.stage` |
| DIRECTORY() | Yes | `FROM DIRECTORY(@db.schema.stage)` |
| TO_FILE() | Yes | `TO_FILE('@db.schema.stage', 'file.pdf')` |
| ALTER STAGE | **No** | `ALTER STAGE db.schema.stage ...` |
| CREATE STAGE | **No** | `CREATE STAGE db.schema.stage ...` |
| DROP STAGE | **No** | `DROP STAGE db.schema.stage` |

---

## Signature

```sql
-- From text
AI_EXTRACT( text, responseFormat )

-- From file
AI_EXTRACT( file => TO_FILE('@stage', 'filename'), responseFormat => {...} )
```

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `text` | VARCHAR | Yes* | Input string for extraction |
| `file` | FILE | Yes* | File via `TO_FILE('@stage', 'filename')` |
| `responseFormat` | VARIANT | Yes | Extraction schema |

*One of `text` or `file` required.

## Response Format Options

### Format 1: Simple Object (Field → Question)
```sql
{ 'invoice_number': 'What is the invoice number?', 'total': 'What is the total?' }
```

### Format 2: Array of Strings
```sql
['person', 'location', 'organization']
```

### Format 3: JSON Schema (for Tables)
```sql
{
  'schema': {
    'type': 'object',
    'properties': {
      'invoice_number': { 'type': 'string', 'description': 'Invoice number' },
      'line_items': {
        'type': 'object',
        'description': 'Line items table',
        'column_ordering': ['description', 'qty', 'amount'],
        'properties': {
          'description': { 'type': 'array' },
          'qty': { 'type': 'array' },
          'amount': { 'type': 'array' }
        }
      }
    }
  }
}
```

**Table rules:** Use `type: 'object'` with `column_ordering` array. Column properties must be arrays.

## Returns

```json
{
  "error": null,
  "response": {
    "field_name": "extracted value",
    "table_field": {
      "col1": ["row1", "row2"],
      "col2": ["val1", "val2"]
    }
  }
}
```

Access: `AI_EXTRACT(...):response:field_name::STRING`

## Constraints

| Constraint | Limit |
|------------|-------|
| Max file size | 100 MB |
| Max pages | 125 per call |
| Entity questions | 100 per call |
| Table questions | 10 per call |

**Supported:** PDF, PNG, JPEG, DOCX, PPTX, HTML, TXT, CSV, EML, TIFF, BMP, GIF, WEBP

---

## Usage Patterns

### Pattern 1: Text Extraction

```sql
SELECT AI_EXTRACT(
    text => 'Jan Kowalski lives in Warsaw and works for Snowflake',
    responseFormat => ['person', 'location', 'organization']
):response AS result;
-- {"person": "Jan Kowalski", "location": "Warsaw", "organization": "Snowflake"}
```

### Pattern 2: Single File Extraction

**Given:** Stage `@mydb.myschema.invoices` and file `invoice1.pdf`

```sql
SELECT AI_EXTRACT(
    file => TO_FILE('@mydb.myschema.invoices', 'invoice1.pdf'),
    responseFormat => {
        'invoice_number': 'What is the invoice number?',
        'total': 'What is the total amount?'
    }
):response AS result;
```

### Pattern 3: Batch Processing (All Files in Stage)

**Given:** Stage `@mydb.myschema.invoices` containing files in subfolders

```sql
-- Enable directory table (NOTE: DDL commands do NOT use @ prefix)
ALTER STAGE mydb.myschema.invoices SET DIRECTORY = (ENABLE = TRUE);
ALTER STAGE mydb.myschema.invoices REFRESH;

-- Process all PDFs - use SPLIT_PART to get filename only
SELECT 
    relative_path,
    SPLIT_PART(relative_path, '/', -1) AS filename,
    AI_EXTRACT(
        file => TO_FILE('@mydb.myschema.invoices', SPLIT_PART(relative_path, '/', -1)),
        responseFormat => {
            'invoice_number': 'What is the invoice number?',
            'total': 'What is the total amount?'
        }
    ):response AS result
FROM DIRECTORY(@mydb.myschema.invoices)
WHERE relative_path ILIKE '%.pdf';
```

### Pattern 4: Table Extraction (Line Items)

```sql
SELECT AI_EXTRACT(
    file => TO_FILE('@mydb.myschema.invoices', 'invoice1.pdf'),
    responseFormat => {
        'schema': {
            'type': 'object',
            'properties': {
                'invoice_number': {
                    'type': 'string',
                    'description': 'Invoice number'
                },
                'line_items': {
                    'type': 'object',
                    'description': 'Line items from the invoice',
                    'column_ordering': ['description', 'quantity', 'unit_price', 'amount'],
                    'properties': {
                        'description': { 'type': 'array' },
                        'quantity': { 'type': 'array' },
                        'unit_price': { 'type': 'array' },
                        'amount': { 'type': 'array' }
                    }
                }
            }
        }
    }
):response AS result;
```

### Pattern 5: Mixed Extraction (Fields + Table)

```sql
SELECT AI_EXTRACT(
    file => TO_FILE('@stage', 'report.pdf'),
    responseFormat => {
        'schema': {
            'type': 'object',
            'properties': {
                'title': { 'type': 'string', 'description': 'Document title' },
                'authors': { 'type': 'array', 'description': 'List of authors' },
                'data_table': {
                    'type': 'object',
                    'column_ordering': ['month', 'revenue'],
                    'properties': {
                        'month': { 'type': 'array' },
                        'revenue': { 'type': 'array' }
                    }
                }
            }
        }
    }
):response AS result;
```

---

## Real-World Example: Invoice Processing

**Scenario:** User has stage `@acme.finance.billing_docs` with invoice PDFs

**Step 1: List files**
```sql
LIST @acme.finance.billing_docs;
-- Shows: documents/inv_001.pdf, documents/inv_002.pdf, etc.
```

**Step 2: Single file test (use filename only, NOT the path from LIST)**
```sql
SELECT AI_EXTRACT(
    file => TO_FILE('@acme.finance.billing_docs', 'inv_001.pdf'),
    responseFormat => {
        'invoice_number': 'What is the invoice number?',
        'date': 'Invoice date in YYYY-MM-DD format',
        'total': 'Total amount due'
    }
):response AS result;
```

**Step 3: Batch all files**
```sql
SELECT 
    SPLIT_PART(relative_path, '/', -1) AS filename,
    AI_EXTRACT(
        file => TO_FILE('@acme.finance.billing_docs', SPLIT_PART(relative_path, '/', -1)),
        responseFormat => {
            'invoice_number': 'What is the invoice number?',
            'date': 'Invoice date in YYYY-MM-DD format',
            'total': 'Total amount due'
        }
    ):response AS result
FROM DIRECTORY(@acme.finance.billing_docs)
WHERE relative_path ILIKE '%.pdf';
```

---

## Prompt Engineering Tips

| Problem | Solution |
|---------|----------|
| Wrong field extracted | Add "NOT the [other field]" to question |
| Wrong format | Specify: "Return as YYYY-MM-DD", "number only" |
| Missing field | Add "If not found, return null" |
| Ambiguous | Describe location: "at the top", "in the header" |

**Good questions:**
```sql
'invoice_number': 'What is the invoice number? Usually labeled "Invoice #". NOT the PO number.'
'date': 'What is the invoice date? Return in YYYY-MM-DD format. NOT the due date.'
'total': 'What is the total amount due? Return as number without currency symbol.'
```

---

## Error Cases

| Error | Cause | Fix |
|-------|-------|-----|
| File not found | Wrong path in TO_FILE | Use filename only, not full path from LIST |
| `invalid array format` | Malformed responseFormat | Check syntax |
| `too many questions` | >100 entities or >10 tables | Split into multiple calls |

## Large Documents (>125 pages)

AI_EXTRACT limit is 125 pages. Options:
1. Split PDF into chunks before processing
2. Use AI_PARSE_DOCUMENT (500 page limit) + AI_COMPLETE

## Stage Restrictions

**Works with:** Named internal stages, external stages (S3, Azure, GCS)

**Does NOT work with:** User stages (`@~`), table stages, encrypted external stages

## Related Functions

- `AI_PARSE_DOCUMENT` - Full document parsing (500 page limit)
- `AI_COMPLETE` - For visual analysis or post-parse extraction
- `AI_CLASSIFY` - Categorize documents