---
type: primitive
name: ai-extract
domain: ai-analytics
snowflake_docs: "https://docs.snowflake.com/en/sql-reference/functions/ai_extract"
---

# AI_EXTRACT

Extract structured fields from text or documents into JSON. Works on text columns, PDFs, images, and other document types via TO_FILE.

## Syntax

```sql
-- From text
AI_EXTRACT( text, responseFormat )

-- From file
AI_EXTRACT( file => TO_FILE('@stage', 'filename'), responseFormat => {...} )
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `text` | VARCHAR | Yes* | Input text string |
| `file` | FILE | Yes* | File via `TO_FILE('@stage', 'filename')` |
| `responseFormat` | VARIANT | Yes | Extraction schema (see formats below) |

*One of `text` or `file` required.

### Return Value

```json
{"error": null, "response": {"field": "value"}}
```

Access: `AI_EXTRACT(...):response:field_name::STRING`

## Response Format Options

### Simple array (field names only)

```sql
['person', 'location', 'organization']
```

### Object (field → question mapping)

```sql
{
    'invoice_number': 'What is the invoice number? NOT the PO number.',
    'date': 'Invoice date in YYYY-MM-DD format',
    'total': 'Total amount due as a number without currency symbol'
}
```

### JSON schema (for table extraction)

```sql
{
    'schema': {
        'type': 'object',
        'properties': {
            'invoice_number': {'type': 'string', 'description': 'Invoice number'},
            'line_items': {
                'type': 'object',
                'description': 'Line items from the invoice',
                'column_ordering': ['description', 'quantity', 'amount'],
                'properties': {
                    'description': {'type': 'array'},
                    'quantity': {'type': 'array'},
                    'amount': {'type': 'array'}
                }
            }
        }
    }
}
```

Table extraction rules: use `type: 'object'` with `column_ordering` array. Column properties must be arrays.

## Core Patterns

### Extract from text column

```sql
SELECT
    ticket_text,
    AI_EXTRACT(ticket_text, ['product', 'issue_type', 'urgency']):response AS extracted
FROM support_tickets
LIMIT 5;
```

### Extract from a single file

```sql
SELECT AI_EXTRACT(
    file => TO_FILE('@mydb.myschema.invoices', 'invoice1.pdf'),
    responseFormat => {
        'invoice_number': 'What is the invoice number?',
        'total': 'What is the total amount?'
    }
):response AS result;
```

### Batch extract from all files in a stage

```sql
ALTER STAGE mydb.myschema.invoices SET DIRECTORY = (ENABLE = TRUE);
ALTER STAGE mydb.myschema.invoices REFRESH;

SELECT
    relative_path,
    SPLIT_PART(relative_path, '/', -1) AS filename,
    AI_EXTRACT(
        file => TO_FILE('@mydb.myschema.invoices', SPLIT_PART(relative_path, '/', -1)),
        responseFormat => {
            'invoice_number': 'What is the invoice number?',
            'total': 'What is the total amount?'
        }
    ):response AS extracted
FROM DIRECTORY(@mydb.myschema.invoices)
WHERE relative_path ILIKE '%.pdf';
```

### Store batch results in a typed table

```sql
CREATE OR REPLACE TABLE extracted_invoices AS
SELECT
    SPLIT_PART(relative_path, '/', -1) AS filename,
    extracted:invoice_number::STRING AS invoice_number,
    extracted:date::DATE AS invoice_date,
    extracted:total::NUMBER(10,2) AS total_amount
FROM (
    SELECT relative_path,
        AI_EXTRACT(
            file => TO_FILE('@mydb.myschema.invoices', SPLIT_PART(relative_path, '/', -1)),
            responseFormat => {'invoice_number': 'Invoice number', 'date': 'Date in YYYY-MM-DD', 'total': 'Total amount'}
        ):response AS extracted
    FROM DIRECTORY(@mydb.myschema.invoices)
    WHERE relative_path ILIKE '%.pdf'
);
```

## TO_FILE Path Rules

This is the most common source of errors with AI_EXTRACT on files.

| Rule | Detail |
|------|--------|
| Stage path and filename are SEPARATE arguments | `TO_FILE('@db.schema.stage', 'file.pdf')` — never concatenate |
| Use filename only, not path from LIST | LIST shows `folder/invoice.pdf` — use `invoice.pdf` or `SPLIT_PART(relative_path, '/', -1)` |
| DDL commands do NOT use `@` prefix | `ALTER STAGE db.schema.stage ...` (no `@`), but `LIST @db.schema.stage` (with `@`) |

## Prompt Engineering for Extraction

| Problem | Solution |
|---------|----------|
| Wrong field extracted | Add "NOT the [other field]" to the question |
| Wrong format | Specify: "Return as YYYY-MM-DD", "number only" |
| Missing field | Add "If not found, return null" |
| Ambiguous | Describe location: "at the top of the page", "in the header" |

## Constraints

| Constraint | Limit |
|------------|-------|
| Max file size | 100 MB |
| Max pages per call | 125 |
| Max entity questions | 100 per call |
| Max table questions | 10 per call |
| Supported formats | PDF, PNG, JPEG, DOCX, PPTX, HTML, TXT, CSV, EML, TIFF, BMP, GIF, WEBP |

- Does not work with user stages (`@~`), table stages, or encrypted external stages
- Cannot be used in dynamic table definitions
- Requires SNOWFLAKE.CORTEX_USER database role

## AI_PARSE_DOCUMENT — Full Text Extraction

For documents >125 pages, or when you need the full text (not specific fields), use AI_PARSE_DOCUMENT:

```sql
SELECT AI_PARSE_DOCUMENT(
    TO_FILE('@stage', 'report.pdf'),
    {'mode': 'LAYOUT'}
):content::STRING AS full_text;
```

Supports up to 500 pages. Chain with AI_COMPLETE for analysis on the extracted text.

## Anti-patterns

| Pattern | Why It Fails | Instead |
|---------|-------------|---------|
| Concatenating path in TO_FILE | `TO_FILE('@stage/folder/file.pdf')` fails | Use two arguments: `TO_FILE('@stage', 'file.pdf')` |
| Using `@` in ALTER STAGE | Syntax error | Drop `@` for DDL: `ALTER STAGE stage_name ...` |
| Batch processing without single-file test | Bad extraction schema wastes credits on entire batch | Always test on one file first |
| Using AI_EXTRACT for full document text | AI_EXTRACT answers specific questions — not a text dumper | Use AI_PARSE_DOCUMENT for full text extraction |

## References

- `primitives/ai-classify`
- `primitives/ai-complete`
- [AI_EXTRACT](https://docs.snowflake.com/en/sql-reference/functions/ai_extract)
- [AI_PARSE_DOCUMENT](https://docs.snowflake.com/en/sql-reference/functions/ai_parse_document)
