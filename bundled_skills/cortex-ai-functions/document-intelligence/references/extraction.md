# Extraction Workflow

Structured field and table extraction using AI_EXTRACT.

## Use When

- User wants specific fields (names, dates, amounts, IDs)
- User wants tables with defined columns (line items, transactions)

## Constraints

| Constraint | Limit |
|------------|-------|
| Max file size | 100 MB |
| Max pages | 125 per call |
| Entity questions | 100 per call |
| Table questions | 10 per call |

## Pricing

```
AI_EXTRACT (arctic_extract model): 5 credits per 1M tokens

Quick estimates:
- 1,000 pages: ~3-5 credits
- 100 pages: ~0.3-0.5 credits

Formula: cost = tokens × (5 / 1,000,000)
Rule of thumb: ~4 characters ≈ 1 token
```

**Full pricing details:** See [ai-extract.md](../../references/ai-extract.md)

## Reference

**BEFORE executing any SQL**, read `../../references/ai-extract.md` to get the correct AI_EXTRACT syntax. This prevents errors from incorrect function signatures.

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

### 2. Define Extraction Fields [WAIT]

Ask what fields to extract. For each field, get:
- Field name
- Description of what to extract
- Type: single value, list, or table

Confirm fields back to user before proceeding.

### 3. List Files

Show available files in the stage. Inform user you'll test on one file first.

### 4. Cost Estimate

Display estimated cost for the test file, then proceed to test.

### 5. Single File Test [WAIT]

Extract from ONE file only. Display results clearly.

Ask if satisfied:
- Yes → proceed to batch
- No → return to Step 2 to refine fields

### 6. Batch Process

Display batch cost for all files, then execute batch extraction.

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
| 2 | Field definitions confirmed |
| 5 | Single file result confirmation |
| 7 | Post-processing choice |
