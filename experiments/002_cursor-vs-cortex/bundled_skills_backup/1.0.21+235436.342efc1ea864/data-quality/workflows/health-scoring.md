---
parent_skill: data-quality
---

# Workflow 1: Schema Health Scoring

## Trigger Phrases
- "Can I trust my schema?"
- "Schema health check"
- "Schema quality score"
- "How healthy is [DATABASE.SCHEMA]?"

## When to Load
Data-quality Step 2: health/trust/score intent.

## Template to Use
**Primary:** `schema-health-snapshot-realtime.sql`
- Provides immediate, real-time health score via dynamic table discovery
- Use for demos and ad-hoc checks

**Fallback (if real-time fails):** `schema-health-snapshot.sql`
- Uses historical ACCOUNT_USAGE data (45min-3hr lag)
- Use for production monitoring

## Execution Steps

### Step 1: Extract Database and Schema
- From user query: "DEMO_DQ_DB.SALES" → database='DEMO_DQ_DB', schema='SALES'
- If not already provided, ask which DATABASE.SCHEMA to check

### Step 2: Execute Template
- Read: `templates/schema-health-snapshot-realtime.sql`
- This template dynamically discovers tables via `INFORMATION_SCHEMA.TABLES` — no hardcoded table names
- Replace: `<database>` → actual database name, `<schema>` → actual schema name
- Execute via `snowflake_sql_execute` (NO permission prompt)

### Step 3: Present Results
```
Schema Health Report: DATABASE.SCHEMA

Overall Health: XX.X%
Metrics: X passing, Y failing
Tables Monitored: Z tables
Issues Found: N tables with problems
```

### Step 4: Next Steps
- If health = 100%: "All metrics passing."
- If health < 100%: "Would you like to see root cause analysis?"
- Do NOT auto-run root cause (that's a separate workflow)

## Output Format
- Overall health percentage
- Count of passing vs failing metrics
- Number of tables monitored
- Number of tables with issues

## Error Handling
- If real-time template fails → Try historical template
- If both fail → Check DMF attachment: `check-dmf-status.sql`
- If no DMFs → "No DMFs found. Set up monitoring first."

## Notes
- This is a READ-ONLY workflow (no approval required)
- Does not drill into specific failures (use root-cause-analysis.md for that)
- Fast execution (< 5 seconds for schemas with < 20 tables)

## Halting States
- **Success**: Health report presented — suggest next steps based on score
- **No DMFs**: Inform user that monitoring needs to be set up first
