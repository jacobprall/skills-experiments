---
type: playbook
name: analyze-documents
domain: ai-analytics
depends_on:
  - ai-extract
  - ai-complete
---

# Analyze Documents

Extract structured data from documents (PDFs, images, text files) stored in a Snowflake stage. Follows a test-before-batch pattern to avoid wasting credits on bad prompts.

## Objective

After completing this playbook, the user will have:

1. A stage with directory table enabled
2. Validated extraction fields tested on a single document
3. Batch extraction results for all documents
4. Results stored in a queryable table

## Prerequisites

- Documents uploaded to a named internal or external stage
- SNOWFLAKE.CORTEX_USER database role granted
- Stage must NOT use SNOWFLAKE_FULL encryption or client-side encryption

## Steps

### Step 1: Verify stage and list files

Ensure the stage exists, has files, and has directory table enabled.

```sql
LIST @<stage_path>;
```

If directory table is not enabled:

```sql
ALTER STAGE <stage_path> SET DIRECTORY = (ENABLE = TRUE);
ALTER STAGE <stage_path> REFRESH;
```

Note: DDL commands (ALTER, CREATE, DROP) do NOT use the `@` prefix. Only query references (LIST, DIRECTORY(), TO_FILE) use `@`.

Present the file list to the user so they can confirm scope.

**Checkpoint:**
  severity: info
  present: "File count and types found in stage"

### Step 2: Design the extraction schema

Based on what the user wants to extract, build the responseFormat for AI_EXTRACT.

**Simple fields** — use an object with field-to-question mappings:
```sql
{
    'invoice_number': 'What is the invoice number?',
    'date': 'Invoice date in YYYY-MM-DD format',
    'total': 'Total amount due as a number without currency symbol'
}
```

**Table data** — use JSON schema with column_ordering:
```sql
{
    'schema': {
        'type': 'object',
        'properties': {
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

Prompt engineering tips for extraction questions:
- Specify format: "Return as YYYY-MM-DD", "number only, no currency symbol"
- Disambiguate: "Invoice number, NOT the PO number"
- Handle missing: "If not found, return null"

### Step 3: Test on a single document

Pick one representative file and run AI_EXTRACT on it. This validates the extraction schema before spending credits on the full batch.

Reference: `primitives/ai-extract`

```sql
SELECT AI_EXTRACT(
    file => TO_FILE('@<stage_path>', '<filename>'),
    responseFormat => <extraction_schema>
):response AS result;
```

The filename must be just the file name, NOT the full path from LIST output. If LIST shows `folder/invoice.pdf`, use just `invoice.pdf`.

Review results with the user. If extraction is wrong, refine the schema and re-test.

**Checkpoint:**
  severity: review
  present: "Single-file extraction result — confirm fields are correct before batch"

### Step 4: Batch process all documents

Once the schema is validated, run on all files in the stage.

```sql
SELECT
    relative_path,
    SPLIT_PART(relative_path, '/', -1) AS filename,
    AI_EXTRACT(
        file => TO_FILE('@<stage_path>', SPLIT_PART(relative_path, '/', -1)),
        responseFormat => <extraction_schema>
    ):response AS extracted
FROM DIRECTORY(@<stage_path>)
WHERE relative_path ILIKE '%.pdf'
    OR relative_path ILIKE '%.png'
    OR relative_path ILIKE '%.jpg';
```

For large batches (100+ files), consider running in chunks or using CREATE TABLE AS SELECT to store results incrementally.

### Step 5: Store results in a table

Flatten the extracted JSON into typed columns for downstream use.

```sql
CREATE OR REPLACE TABLE <target_table> AS
SELECT
    relative_path,
    SPLIT_PART(relative_path, '/', -1) AS filename,
    extracted:invoice_number::STRING AS invoice_number,
    extracted:date::DATE AS invoice_date,
    extracted:total::NUMBER(10,2) AS total_amount
FROM (
    SELECT
        relative_path,
        AI_EXTRACT(
            file => TO_FILE('@<stage_path>', SPLIT_PART(relative_path, '/', -1)),
            responseFormat => <extraction_schema>
        ):response AS extracted
    FROM DIRECTORY(@<stage_path>)
    WHERE relative_path ILIKE '%.pdf'
);
```

Verify row count matches expected file count. Check for null values that indicate extraction failures.

**Checkpoint:**
  severity: review
  present: "Final table with row count, sample rows, and any null/error values"

## Anti-patterns

| Mistake | Impact | Instead |
|---------|--------|---------|
| Batch processing before testing on one file | Bad extraction schema wastes credits on entire batch | Always test single file first (step 3) |
| Using full path from LIST as filename | TO_FILE fails — paths include folder prefixes | Use SPLIT_PART(relative_path, '/', -1) for filename only |
| Using `@` prefix in DDL commands | Syntax error on ALTER STAGE | Only use `@` in query references (LIST, DIRECTORY, TO_FILE) |
| Ignoring AI_EXTRACT limits | Fails on documents >125 pages or >100 entity questions | Split large docs; for >125 pages use AI_PARSE_DOCUMENT + AI_COMPLETE |
