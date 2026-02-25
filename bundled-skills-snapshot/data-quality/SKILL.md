---
name: data-quality
description: "Schema-level data quality monitoring, table comparison, and dataset popularity analysis using Snowflake Data Metric Functions (DMFs) and Access History. Use when user asks about: data quality, schema health, DMF results, quality score, trust my data, quality regression, quality trends, SLA alerting, data metric functions, failing metrics, quality issues, compare tables, data diff, validate migration, table comparison, popular tables, most used tables, unused data, dataset usage, table popularity."
---

# Data Quality

Monitor, analyze, and enforce data quality across Snowflake schemas using Data Metric Functions (DMFs). Compare tables for migration validation, regression testing, and data reconciliation. Analyze dataset popularity and usage patterns to prioritize governance.

## When to Use

Activate this skill when the user mentions any of:

- **Health/trust keywords**: "schema health", "data quality score", "can I trust my data", "quality check"
- **DMF keywords**: "data metric function", "DMF", "DMF results", "metrics failing"
- **Issue investigation**: "why is this table failing", "what's wrong with my data", "root cause", "quality issues"
- **Change detection**: "quality regression", "what changed", "what broke", "did quality get worse"
- **Trend keywords**: "quality trends", "is quality improving", "quality over time"
- **Alerting keywords**: "quality alerts", "SLA monitoring", "alert me on quality drops", "enforce DQ SLAs"
- **Table comparison keywords**: "compare tables", "data diff", "table diff", "validate migration", "dev vs prod data", "find differences", "data reconciliation"
- **Popularity/usage keywords**: "popular tables", "most used tables", "least used", "unused tables", "stale data", "dataset usage", "table popularity", "who uses this table", "is this table used"

**Do NOT use** for: single-table ad-hoc queries, DMF attachment/setup (guide user to Snowflake docs instead), or non-quality-related schema operations.

## Workflow Decision Tree

```
User request
  |
  v
Step 1: Identify intent
  |
  ├── Health/trust/score ----------> Load workflows/health-scoring.md
  |
  ├── Failures/root cause ---------> Load workflows/root-cause-analysis.md
  |
  ├── Regression/what changed -----> Load workflows/regression-detection.md
  |
  ├── Trends/over time ------------> Load workflows/trend-analysis.md
  |
  ├── Alerts/SLA/notify -----------> Load workflows/sla-alerting.md
  |
  ├── Compare tables/diff/migrate -> Load workflows/compare-tables.md
  |                                    (has its own sub-workflows)
  |
  └── Popularity/usage/unused -----> Load workflows/popularity.md
```

## Workflow

### Step 1: Route to Workflow

**Goal:** Determine which workflow matches the user's intent and load it.

For DMF-based workflows (1-5), also extract `DATABASE.SCHEMA` from the user's message. If only a schema name is provided, ask which database it belongs to.

| User Intent | Workflow to Load |
|---|---|
| Health check, trust, quality score | **Load** `workflows/health-scoring.md` |
| Why failing, what's wrong, root cause | **Load** `workflows/root-cause-analysis.md` |
| What changed, regression, what broke | **Load** `workflows/regression-detection.md` |
| Quality trends, improving, over time | **Load** `workflows/trend-analysis.md` |
| Set up alerts, SLA, notify on drops | **Load** `workflows/sla-alerting.md` |
| Compare tables, data diff, validate migration, dev vs prod | **Load** `workflows/compare-tables.md` |
| Popular tables, most/least used, unused data, who uses this | **Load** `workflows/popularity.md` |

If the intent is ambiguous, ask the user which workflow they want.

### Step 2: Execute Template from Workflow

**Goal:** Run the SQL template specified by the loaded workflow.

**Actions:**

1. Read the SQL template specified in the workflow file (from `templates/` directory)
2. Replace all placeholders:
   - `<database>` with the actual database name
   - `<schema>` with the actual schema name
3. Execute using `snowflake_sql_execute`
4. If the primary template fails, try the fallback template specified in the workflow

**Note:** The compare-tables and popularity workflows have their own step-by-step execution flows — follow the loaded workflow directly when those routes are selected.

**Error handling:**
- If template fails and fallback also fails: check prerequisites with `templates/check-dmf-status.sql`
- If no DMFs found: inform user that DMFs need to be attached first
- If no data yet: inform user that DMFs haven't run — wait 1-2 minutes
- Maximum 2 fallback attempts before reporting the error to the user

### Step 3: Present Results

**Goal:** Format and present results per the workflow's output guidelines.

Follow the output format specified in the loaded workflow file. Suggest logical next steps (e.g., root cause analysis after health check).

## Tools

### snowflake_sql_execute

**Description:** Executes SQL queries against the user's Snowflake account.

**When to use:** All template executions — health checks, root cause analysis, regression detection, trend analysis, and alert creation.

**Usage pattern:**
1. Read the appropriate SQL template from `templates/`
2. Replace `<database>` and `<schema>` placeholders with actual values
3. Execute the resulting SQL via `snowflake_sql_execute`

**Templates available (DMF workflows):**

| Template | Purpose | Type |
|---|---|---|
| `check-dmf-status.sql` | Verify DMF setup | Read |
| `check-dq-monitoring-enabled.sql` | Check historical tracking | Read |
| `schema-health-snapshot-realtime.sql` | Current health (instant) | Read |
| `schema-health-snapshot.sql` | Health from ACCOUNT_USAGE | Read |
| `schema-root-cause-realtime.sql` | Current failures (instant) | Read |
| `schema-root-cause.sql` | Failures from ACCOUNT_USAGE | Read |
| `schema-regression-detection.sql` | Compare runs over time | Read |
| `schema-quality-trends.sql` | Time-series analysis | Read |
| `schema-sla-alert.sql` | Create automated alert | **Write** |

For compare-tables tools (`data_diff` CLI, SQL templates), see `workflows/compare-tables.md`.

## Stopping Points

- ✋ **Before SLA alert creation**: The `sla-alerting` workflow creates Snowflake ALERT objects and a log table — present the full configuration and get explicit user approval before executing any CREATE statements
- ✋ **Before materializing diff results**: The compare-tables workflow can write diff results to a new table — confirm table name and location with user first
- ✋ **After health check with failures**: Present results and ask if user wants root cause analysis (do not auto-chain workflows)
- ✋ **On prerequisite failure**: If DMFs are not attached or monitoring is not enabled, explain what's needed and ask if user wants help setting it up

**Resume rule:** Upon user approval, proceed directly to the next step without re-asking.

## Output

Each workflow produces structured output:

- **Health Scoring**: Overall health percentage, passing/failing metric counts, tables monitored
- **Root Cause Analysis**: Failing metrics by table/column, issue descriptions, fix recommendations
- **Regression Detection**: Health delta (previous vs current), new failures, resolved issues
- **Trend Analysis**: Time-series health scores, persistent vs transient issues, trend direction
- **SLA Alerting**: Alert configuration summary, activation status, monitoring instructions
- **Compare Tables**: Row counts, added/removed/modified rows, schema differences, validation report (see `workflows/compare-tables.md` for details)
- **Dataset Popularity**: Popularity-ranked tables, unused/stale object list, storage cost estimates, usage trends, top consumers

## Error Handling

| Error | Action |
|---|---|
| Real-time template fails | Try historical (ACCOUNT_USAGE) fallback template |
| Historical template fails | Run `check-dmf-status.sql` to verify DMFs are attached |
| No DMFs found | Inform user: "No DMFs attached. Set up monitoring first." |
| No data available | Inform user: "DMFs haven't run yet. Wait 1-2 minutes." |
| Insufficient history | Inform user: "Need at least 2 measurements for comparison." |
| SQL compilation error | Report the error clearly — do not hide failures or fabricate results |

## Reference

For detailed DMF concepts, **Load** `reference/dmf-concepts.md` when the user asks about DMF setup, concepts, or best practices.
