---
type: playbook
name: investigate-data-issue
domain: data-observability
depends_on:
  - data-metric-functions
  - lineage-queries
---

# Investigate Data Issue

Systematically investigate a data quality problem: check health scores, identify failing metrics, trace the issue upstream, and provide root cause analysis with recommendations.

## Objective

After completing this playbook, the user will have:

1. A health score for the affected schema
2. Identification of specific failing metrics and affected tables
3. Upstream lineage trace to find where the issue originates
4. Recent changes that may have caused the problem
5. Actionable recommendations to fix the issue

## Prerequisites

- Access to SNOWFLAKE.ACCOUNT_USAGE views
- For DMF-based health checks: Data Metric Functions must be attached to tables (if not, the playbook falls back to basic table inspection)

## Steps

### Step 1: Check schema health score

If DMFs are attached, query the health snapshot.

Reference: `primitives/data-metric-functions`

```sql
WITH latest AS (
    SELECT database_name, schema_name, table_name, metric_name, metric_value, measurement_time
    FROM SNOWFLAKE.ACCOUNT_USAGE.DATA_QUALITY_MONITORING_RESULTS
    WHERE database_name = '<database>' AND schema_name = '<schema>'
        AND measurement_time = (
            SELECT MAX(measurement_time)
            FROM SNOWFLAKE.ACCOUNT_USAGE.DATA_QUALITY_MONITORING_RESULTS
            WHERE database_name = '<database>' AND schema_name = '<schema>'
        )
)
SELECT
    database_name, schema_name,
    ROUND((COUNT_IF(metric_value = 0) * 100.0) / NULLIF(COUNT(*), 0), 1) AS health_pct,
    COUNT_IF(metric_value = 0) AS passing,
    COUNT_IF(metric_value > 0) AS failing,
    COUNT(*) AS total_metrics,
    COUNT(DISTINCT table_name) AS tables_monitored,
    MAX(measurement_time) AS measured_at
FROM latest
GROUP BY database_name, schema_name;
```

If no DMF data is available, fall back to basic table inspection:
```sql
SELECT table_name, row_count, bytes,
    DATEDIFF('hour', last_altered, CURRENT_TIMESTAMP()) AS hours_since_altered
FROM <database>.INFORMATION_SCHEMA.TABLES
WHERE table_schema = '<schema>'
ORDER BY last_altered DESC;
```

**Checkpoint:**
  severity: info
  present: "Schema health summary — overall score and any immediate red flags"

### Step 2: Identify failing metrics and root cause

Drill into the specific failures.

```sql
WITH latest AS (
    SELECT table_name, column_name, metric_name, metric_value, threshold, measurement_time
    FROM SNOWFLAKE.ACCOUNT_USAGE.DATA_QUALITY_MONITORING_RESULTS
    WHERE database_name = '<database>' AND schema_name = '<schema>'
        AND metric_value > 0
        AND measurement_time = (
            SELECT MAX(measurement_time)
            FROM SNOWFLAKE.ACCOUNT_USAGE.DATA_QUALITY_MONITORING_RESULTS
            WHERE database_name = '<database>' AND schema_name = '<schema>'
        )
)
SELECT
    table_name,
    COALESCE(column_name, '<table-level>') AS column_name,
    metric_name,
    metric_value AS current_value,
    threshold,
    CASE
        WHEN metric_value > threshold * 2 THEN 'CRITICAL'
        WHEN metric_value > threshold * 1.5 THEN 'HIGH'
        WHEN metric_value > threshold THEN 'MEDIUM'
        ELSE 'LOW'
    END AS severity,
    CASE metric_name
        WHEN 'NULL_COUNT' THEN 'Unexpected nulls — check upstream pipeline'
        WHEN 'FRESHNESS' THEN 'Data is stale — check ETL schedule'
        WHEN 'DUPLICATE_COUNT' THEN 'Duplicates found — check deduplication logic'
        WHEN 'ROW_COUNT' THEN 'Unexpected row count — check data loading'
        ELSE 'Review custom metric logic'
    END AS recommendation
FROM latest
ORDER BY
    CASE WHEN metric_value > threshold * 2 THEN 1
         WHEN metric_value > threshold * 1.5 THEN 2
         ELSE 3 END,
    metric_value DESC;
```

### Step 3: Check for stale or broken pipelines

Look for dynamic tables that are suspended, erroring, or falling behind their target lag.

```sql
SELECT
    name, database_name, schema_name,
    scheduling_state,
    target_lag,
    DATEDIFF('minute', data_timestamp, CURRENT_TIMESTAMP()) AS minutes_behind,
    last_suspended_on
FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLES())
WHERE database_name = '<database>'
ORDER BY minutes_behind DESC NULLS LAST;
```

Highlight any tables with `scheduling_state != 'ACTIVE'` or `minutes_behind` exceeding their target lag.

### Step 4: Trace upstream lineage

For the table(s) with the most critical failures, trace upstream to find the source of the problem.

Reference: `primitives/lineage-queries`

```sql
SELECT
    referenced_database || '.' || referenced_schema || '.' || referenced_object_name AS upstream_object,
    referenced_object_domain AS object_type,
    referencing_database || '.' || referencing_schema || '.' || referencing_object_name AS this_object,
    dependency_type
FROM SNOWFLAKE.ACCOUNT_USAGE.OBJECT_DEPENDENCIES
WHERE referencing_database = '<database>'
    AND referencing_schema = '<schema>'
    AND referencing_object_name = '<table>'
ORDER BY referenced_object_domain;
```

### Step 5: Check for recent upstream changes

Look for schema changes or data modifications in upstream objects.

```sql
SELECT
    table_catalog || '.' || table_schema || '.' || table_name AS object_name,
    last_altered,
    DATEDIFF('hour', last_altered, CURRENT_TIMESTAMP()) AS hours_ago,
    row_count, bytes
FROM SNOWFLAKE.ACCOUNT_USAGE.TABLES
WHERE (table_catalog, table_schema, table_name) IN (
    SELECT referenced_database, referenced_schema, referenced_object_name
    FROM SNOWFLAKE.ACCOUNT_USAGE.OBJECT_DEPENDENCIES
    WHERE referencing_database = '<database>'
        AND referencing_schema = '<schema>'
        AND referencing_object_name = '<table>'
)
AND last_altered >= DATEADD('day', -7, CURRENT_TIMESTAMP())
ORDER BY last_altered DESC;
```

**Checkpoint:**
  severity: review
  present: "Root cause analysis — failing metrics, pipeline status, upstream changes, and recommendations"

### Step 6: Provide recommendations

Based on findings, provide specific recommendations:

| Finding | Recommendation |
|---------|---------------|
| DMF failures on null counts | Fix upstream pipeline that's producing nulls; add validation |
| Stale data (freshness failure) | Check ETL schedule; verify task/dynamic table is running |
| Suspended dynamic table | Investigate suspension cause; resume if appropriate |
| Recent upstream schema change | Verify downstream compatibility; check column type changes |
| No DMFs attached | Recommend setting up DMFs for ongoing monitoring |

## Anti-patterns

| Mistake | Impact | Instead |
|---------|--------|---------|
| Jumping to lineage before checking health | May trace the wrong table or miss the real problem | Start with health score to identify which tables are failing |
| Ignoring dynamic table status | Pipeline may be suspended — data quality is a symptom | Always check pipeline status as part of investigation |
| Only checking DMFs when they're not attached | Gets zero results and stops | Fall back to basic table inspection (row counts, freshness, etc.) |
