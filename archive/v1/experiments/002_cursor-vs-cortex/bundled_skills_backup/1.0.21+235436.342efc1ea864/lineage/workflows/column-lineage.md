# Column Lineage Workflow

## Purpose
Trace data lineage at the column level to understand how specific fields flow through your data pipeline.

## When to Use
- **Column Impact Analysis**: Before modifying a column's data type, renaming, or removing
- **Column Root Cause**: Debugging incorrect values in a specific column
- **Column Discovery**: Understanding where a column's data originates
- **Column Change Detection**: Checking if a column definition has changed recently

## Templates

| Template | Use Case | Direction |
|----------|----------|-----------|
| `column-lineage-downstream.sql` | What uses this column? | Downstream |
| `column-lineage-upstream.sql` | Where does this column come from? | Upstream |
| `column-lineage-full.sql` | Complete column path | Both |
| `column-change-detection.sql` | Has this column changed? | Metadata |
| `root-cause-column.sql` | Debug column issues | Upstream |

## Required Information
- **Database**: The database containing the table
- **Schema**: The schema containing the table
- **Table**: The table name
- **Column**: The specific column to trace

## Trigger Phrases

**Downstream (Impact):**
- "What uses the [column] column?"
- "What depends on [table].[column]?"
- "Impact analysis for [column]"
- "If I change [column], what breaks?"

**Upstream (Source):**
- "Where does [column] come from?"
- "What is the source of [table].[column]?"
- "Trace [column] upstream"
- "Column lineage for [column]"

**Full Path:**
- "Full lineage for [column]"
- "Complete path for [table].[column]"
- "End-to-end lineage for [column]"

**Change Detection:**
- "Has [column] changed?"
- "Column changes for [table].[column]"
- "Schema changes affecting [column]"

## Example Interactions

> **Note:** The database/schema/table names below (e.g., `RAW_DB.SALES.ORDERS`) are illustrative examples. The actual output will reflect your specific Snowflake objects.

### Example 1: Column Impact Analysis
**User:** "What will break if I change the AMOUNT column in RAW_DB.SALES.ORDERS?"

**Agent Response:**
```
Column Impact Analysis: RAW_DB.SALES.ORDERS.AMOUNT

═══════════════════════════════════════════════════════════════
DOWNSTREAM DEPENDENCIES (12 objects use this column)
═══════════════════════════════════════════════════════════════

CRITICAL IMPACT:
1. ANALYTICS_DB.FINANCE.REVENUE_SUMMARY.TOTAL_REVENUE
   Impact: CRITICAL | Queries: 89/day | Confidence: HIGH
   
2. ANALYTICS_DB.REPORTING.DAILY_SALES.NET_AMOUNT
   Impact: HIGH | Queries: 45/day | Confidence: HIGH

MODERATE IMPACT:
3. STAGING_DB.TRANSFORM.ORDERS_ENRICHED.AMOUNT
   Impact: MEDIUM | Queries: 12/day | Confidence: MEDIUM

Summary: 12 downstream columns affected | 2 CRITICAL | 1 HIGH | 9 MEDIUM
```

### Example 2: Column Source Tracing
**User:** "Where does ANALYTICS_DB.REPORTS.REVENUE.TOTAL_SALES come from?"

**Agent Response:**
```
Column Source Analysis: ANALYTICS_DB.REPORTS.REVENUE.TOTAL_SALES

═══════════════════════════════════════════════════════════════
UPSTREAM SOURCES (traced 3 levels)
═══════════════════════════════════════════════════════════════

Level 1: STAGING_DB.TRANSFORM.ORDERS_AGG.REVENUE_SUM
         Confidence: HIGH | Last seen: 2 hours ago

Level 2: RAW_DB.INGEST.ORDERS.AMOUNT
         Confidence: HIGH | Source tier: RAW

Level 3: @RAW_DB.STAGES.S3_ORDERS/orders.csv
         Confidence: MEDIUM | Source tier: EXTERNAL

Complete Path:
S3_ORDERS → ORDERS.AMOUNT → ORDERS_AGG.REVENUE_SUM → REVENUE.TOTAL_SALES
```

### Example 3: Column Change Detection
**User:** "Has the DISCOUNT_PCT column in RAW_DB.SALES.ORDERS changed recently?"

**Agent Response:**
```
Column Change Detection: RAW_DB.SALES.ORDERS.DISCOUNT_PCT

═══════════════════════════════════════════════════════════════
CURRENT DEFINITION
═══════════════════════════════════════════════════════════════
Data Type: NUMBER(10,4)
Nullable: YES
Comment: "Discount percentage applied to order"

═══════════════════════════════════════════════════════════════
RECENT CHANGES DETECTED
═══════════════════════════════════════════════════════════════
⚠️  2024-01-15 14:32:00 - ALTER TABLE by ETL_SERVICE
    Changed: NUMBER(5,2) → NUMBER(10,4)
    
Usage: 156 queries in last 30 days by 12 users
Last Read: 2 hours ago

Recommendation: Verify downstream objects handle increased precision
```

## Output Format

### For Downstream Analysis
- List affected downstream columns with impact levels
- Show query frequency and user count
- Provide confidence scores based on ACCESS_HISTORY data
- Summarize total impact

### For Upstream Analysis
- Show source columns by level (depth)
- Indicate source tier (RAW, STAGING, EXTERNAL)
- Provide confidence scores
- Display complete lineage path

### For Change Detection
- Show current column definition
- List recent DDL changes
- Display usage statistics
- Provide recommendations

## Technical Notes

### ACCESS_HISTORY Limitations
- Column-level lineage depends on ACCESS_HISTORY capturing column details
- Not all query patterns expose column-level information
- Confidence scores indicate reliability of lineage data
- Data retained for 365 days

### Best Practices
1. Use fully qualified names: DATABASE.SCHEMA.TABLE.COLUMN
2. For complex transformations, verify with actual query review
3. High confidence = column explicitly tracked; Low = inferred from object access
4. Check multiple time ranges if recent data is sparse
