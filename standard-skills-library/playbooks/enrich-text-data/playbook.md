---
type: playbook
name: enrich-text-data
domain: ai-analytics
depends_on:
  - ai-classify
  - ai-extract
  - ai-complete
---

# Enrich Text Data

Apply multiple AI functions to a table's text column: classify, extract entities, run sentiment, and build automated summaries. Uses a test-before-batch pattern throughout.

## Objective

After completing this playbook, the user will have:

1. An enriched table with AI-derived columns (category, entities, sentiment, etc.)
2. Optionally, an automated summary via dynamic table
3. All enrichments validated on sample data before full batch

## Prerequisites

- Source table with a text column
- SNOWFLAKE.CORTEX_USER database role granted
- A warehouse set in session context

## Steps

### Step 1: Plan the enrichment pipeline

Review sample data and determine which AI functions to apply. Present a plan to the user.

| Enrichment | Function | Output Column Type |
|------------|----------|-------------------|
| Categorize into labels | AI_CLASSIFY | VARCHAR |
| Extract structured fields | AI_EXTRACT (text mode) | VARIANT / multiple VARCHAR |
| Sentiment score | AI_CLASSIFY with sentiment labels, or AI_SENTIMENT | VARCHAR or FLOAT |
| Boolean filter | AI_FILTER | BOOLEAN |
| Custom prompt | AI_COMPLETE | VARCHAR |

The user specifies which enrichments they want. Build the plan accordingly.

**Checkpoint:**
  severity: review
  present: "Enrichment plan — which functions, which columns, estimated row count"

### Step 2: Test each enrichment on a sample

Run each planned AI function on 5-10 rows. This catches prompt issues before spending credits at scale.

Reference: `primitives/ai-classify`, `primitives/ai-extract`, `primitives/ai-complete`

**Classification test:**
```sql
SELECT
    <text_column>,
    AI_CLASSIFY(<text_column>, ['category1', 'category2', 'category3']):labels[0]::VARCHAR AS category
FROM <source_table>
LIMIT 5;
```

**Extraction test:**
```sql
SELECT
    <text_column>,
    AI_EXTRACT(<text_column>, ['field1', 'field2']):response AS extracted
FROM <source_table>
LIMIT 5;
```

**Sentiment test:**
```sql
SELECT
    <text_column>,
    AI_CLASSIFY(<text_column>, ['positive', 'negative', 'neutral']):labels[0]::VARCHAR AS sentiment
FROM <source_table>
LIMIT 5;
```

Review results with the user. Refine prompts, categories, or extraction fields as needed. Re-test until results are satisfactory.

**Checkpoint:**
  severity: review
  present: "Sample results for each enrichment — confirm quality before batch"

### Step 3: Run the full enrichment batch

Create an enriched table with all AI-derived columns.

```sql
CREATE OR REPLACE TABLE <enriched_table> AS
SELECT
    t.*,
    AI_CLASSIFY(t.<text_column>,
        ['category1', 'category2', 'category3']
    ):labels[0]::VARCHAR AS category,
    AI_EXTRACT(t.<text_column>,
        ['field1', 'field2']
    ):response:field1::VARCHAR AS field1,
    AI_CLASSIFY(t.<text_column>,
        ['positive', 'negative', 'neutral']
    ):labels[0]::VARCHAR AS sentiment
FROM <source_table> t;
```

For large tables, consider processing in batches:
```sql
CREATE TABLE <enriched_table> LIKE <source_table>;
ALTER TABLE <enriched_table> ADD COLUMN category VARCHAR, sentiment VARCHAR;

INSERT INTO <enriched_table>
SELECT t.*, AI_CLASSIFY(...), AI_CLASSIFY(...)
FROM <source_table> t
WHERE <primary_key> BETWEEN 1 AND 10000;
-- Repeat for subsequent ranges
```

Verify row count matches source. Check for NULL values indicating function failures.

### Step 4: Build automated summary (optional)

If the user wants an ongoing summary that updates as new data arrives, create a dynamic table.

Reference: `primitives/ai-complete` (AI_AGG section)

```sql
CREATE OR REPLACE DYNAMIC TABLE <summary_table>
    TARGET_LAG = '1 hour'
    WAREHOUSE = <warehouse>
AS
SELECT
    category,
    COUNT(*) AS volume,
    ROUND(AVG(CASE sentiment
        WHEN 'positive' THEN 1
        WHEN 'neutral' THEN 0
        WHEN 'negative' THEN -1
    END), 2) AS avg_sentiment_score,
    COUNT(CASE WHEN sentiment = 'negative' THEN 1 END) AS negative_count
FROM <enriched_table>
GROUP BY category;
```

Note: AI functions (AI_CLASSIFY, AI_EXTRACT, etc.) cannot run inside dynamic tables directly. The enrichment must happen in step 3 (materialized table), and the dynamic table aggregates the pre-enriched results.

**Checkpoint:**
  severity: info
  present: "Summary table structure and sample output"

## Efficiency Patterns

| Pattern | When to Use |
|---------|-------------|
| Enrich into a materialized table, aggregate in dynamic table | Large tables where re-running AI functions on refresh would be expensive |
| Use STREAM + TASK to enrich only new/changed rows | Continuous ingestion where source table grows over time |
| Cache AI results in a separate lookup table keyed by text hash | When the same text values appear multiple times |

## Anti-patterns

| Mistake | Impact | Instead |
|---------|--------|---------|
| Running AI functions in a dynamic table definition | Functions re-run on every refresh, wasting credits on unchanged data | Enrich into a materialized table first; dynamic table aggregates results |
| Skipping sample test | Bad prompts burn credits across entire table | Always test on LIMIT 5-10 first |
| Running classify + extract + sentiment in separate passes | 3x the query time | Combine all AI columns in a single SELECT |
| Using AI_COMPLETE for simple classification | More expensive and less consistent than AI_CLASSIFY | Use purpose-built functions when available |
