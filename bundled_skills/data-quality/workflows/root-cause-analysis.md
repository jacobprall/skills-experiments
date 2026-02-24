---
parent_skill: data-quality
---

# Workflow 2: Root Cause Analysis

## Trigger Phrases
- "Why is this table failing?"
- "What's wrong with [TABLE]?"
- "Show me the failures"
- "What are the quality issues?"
- "Root cause analysis"

## When to Load
Data-quality Step 2: failure/investigation intent.

## Template to Use
**Primary:** `schema-root-cause-realtime.sql`
- Shows immediate failures with details via dynamic table discovery
- Use for troubleshooting

**Fallback (if real-time fails):** `schema-root-cause.sql`
- Uses historical data
- Use for trend analysis of failures

## Execution Steps

### Step 1: Extract Database and Schema
- From user query: "DEMO_DQ_DB.SALES" → database='DEMO_DQ_DB', schema='SALES'
- If not already provided, ask which DATABASE.SCHEMA to investigate

### Step 2: Execute Template
- Read: `templates/schema-root-cause-realtime.sql`
- This template dynamically discovers tables via `INFORMATION_SCHEMA.TABLES` — no hardcoded table names
- Replace: `<database>` → actual database name, `<schema>` → actual schema name
- Execute via `snowflake_sql_execute`

### Step 3: Present Results
```
Root Cause Analysis: DATABASE.SCHEMA

Top Issues Found:

1. TABLE_NAME.COLUMN_NAME - Metric: NULL_COUNT
   Status: FAILED
   Issue: Column contains 3 null values
   Recommendation: Add NOT NULL constraint or fix upstream data

2. TABLE_NAME2.COLUMN_NAME2 - Metric: UNIQUE_COUNT
   Status: FAILED
   Issue: Duplicate values detected
   Recommendation: Add UNIQUE constraint or deduplicate data
```

### Step 4: Next Steps
- If < 5 issues: suggest addressing them directly
- If > 5 issues: suggest setting up alerts with the SLA alerting workflow

## Output Format
- Table name and column name (if applicable)
- Metric type that failed
- Specific issue description
- Actionable recommendation for each failure

## What to Show
- Top 5-10 failing metrics (prioritize by severity)
- Column-level details when available
- Specific metric values (e.g., "3 nulls found")
- Clear fix recommendations

## Error Handling
- If real-time template fails → Try historical template
- If both fail → Check DMF attachment: `check-dmf-status.sql`
- If no failures found → "All metrics passing! No issues detected."

## Notes
- This is a READ-ONLY workflow (no approval required)
- Digs deeper than health-scoring — shows specific violations, not just counts
- Provides actionable recommendations per failure
- Separate workflow from health scoring (do not auto-chain)

## Halting States
- **Success**: Failures listed with recommendations
- **No failures**: "All metrics passing. No issues detected."
- **No DMFs**: Inform user that monitoring needs to be set up first
