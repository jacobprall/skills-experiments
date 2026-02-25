# Parsing Workflow

Full text extraction using AI_PARSE_DOCUMENT.

## Use When

- User wants full text from documents
- User wants layout/structure preserved (tables, headers)
- User needs OCR from scanned documents

## Constraints

| Constraint | Limit |
|------------|-------|
| Max file size | 50 MB |
| Max pages | 500 per call |

## Pricing

```
AI_PARSE_DOCUMENT:
- OCR mode: 0.5 credits per 1,000 pages
- LAYOUT mode: 3.33 credits per 1,000 pages

Quick estimates (1,000 pages):
- OCR: ~0.5 credits
- LAYOUT: ~3.33 credits

Formulas:
OCR:    cost = pages × 0.0005
LAYOUT: cost = pages × 0.00333
```

**Full pricing details:** See [ai-parse-doc.md](../../references/ai-parse-doc.md)

## Reference

**BEFORE executing any SQL**, read `../../references/ai-parse-doc.md` to get the correct AI_PARSE_DOCUMENT syntax. This prevents errors from incorrect function signatures.

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

### 2. Choose Parsing Mode [WAIT]

Ask which mode to use:

1. **LAYOUT mode**
   - Preserves document structure: tables, headings, lists
   - Best for: reports, forms, structured documents
   - Cost: 3.33 credits per 1,000 pages

2. **OCR mode**
   - Plain text output, no structure preserved
   - Best for: scanned documents, simple text extraction
   - Cost: 0.5 credits per 1,000 pages

### 3. List Files

Show available files in the stage. Inform user you'll test on one file first.

### 4. Cost Estimate

Display estimated cost for the test file, then proceed to test.

### 5. Single File Test [WAIT]

Parse ONE file only. Display first ~1500 characters of results.

Ask if satisfied:
- Yes → proceed to batch
- No → try the other mode, return to Step 4

### 6. Batch Process

Display batch cost for all files, then execute batch parsing.

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
| 2 | Parsing mode selection |
| 5 | Single file result confirmation |
| 7 | Post-processing choice |
