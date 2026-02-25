---
type: primitive
name: data-metric-functions
domain: data-observability
snowflake_docs: "https://docs.snowflake.com/en/user-guide/data-quality-intro"
---

# Data Metric Functions (DMFs)

Monitor data quality across Snowflake schemas using Data Metric Functions. Query DMF results for health scoring, root cause analysis, regression detection, trend analysis, and SLA alerting.

This primitive covers **querying DMF results**, not attaching or creating DMFs (guide users to Snowflake docs for DMF setup).

## Key Views

| View | What It Contains | Latency |
|------|-----------------|---------|
| `DATA_QUALITY_MONITORING_RESULTS` | DMF evaluation results (pass/fail per metric per table) | ~2 hours |

All queries require replacement of `<database>` and `<schema>` with actual values.

## Schema Health Score

Overall health percentage for a schema based on latest DMF run.

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

Interpretation: 100% = all passing, 90-99% = minor issues, 75-89% = needs attention, <75% = critical.

## Root Cause Analysis

Identify which tables and columns have failing metrics, with severity and recommendations.

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
        ELSE 'MEDIUM'
    END AS severity,
    CASE metric_name
        WHEN 'NULL_COUNT' THEN 'Unexpected nulls — check upstream pipeline'
        WHEN 'FRESHNESS' THEN 'Data is stale — check ETL schedule'
        WHEN 'DUPLICATE_COUNT' THEN 'Duplicates — check deduplication logic'
        WHEN 'ROW_COUNT' THEN 'Unexpected row count — check data loading'
        ELSE 'Review custom metric logic'
    END AS recommendation
FROM latest
ORDER BY
    CASE WHEN metric_value > threshold * 2 THEN 1 WHEN metric_value > threshold * 1.5 THEN 2 ELSE 3 END,
    metric_value DESC;
```

### Summary by table

```sql
SELECT table_name,
    COUNT(*) AS failing_metrics,
    LISTAGG(DISTINCT metric_name, ', ') AS metrics_failing,
    MAX(CASE WHEN metric_value > threshold * 2 THEN 'CRITICAL' WHEN metric_value > threshold * 1.5 THEN 'HIGH' ELSE 'MEDIUM' END) AS max_severity
FROM SNOWFLAKE.ACCOUNT_USAGE.DATA_QUALITY_MONITORING_RESULTS
WHERE database_name = '<database>' AND schema_name = '<schema>'
    AND metric_value > 0
    AND measurement_time = (SELECT MAX(measurement_time) FROM SNOWFLAKE.ACCOUNT_USAGE.DATA_QUALITY_MONITORING_RESULTS WHERE database_name = '<database>' AND schema_name = '<schema>')
GROUP BY table_name
ORDER BY failing_metrics DESC;
```

## Regression Detection

Compare the latest DMF run to a previous run to spot new failures.

```sql
WITH runs AS (
    SELECT DISTINCT measurement_time
    FROM SNOWFLAKE.ACCOUNT_USAGE.DATA_QUALITY_MONITORING_RESULTS
    WHERE database_name = '<database>' AND schema_name = '<schema>'
    ORDER BY measurement_time DESC
    LIMIT 2
),
current_run AS (
    SELECT table_name, metric_name, metric_value
    FROM SNOWFLAKE.ACCOUNT_USAGE.DATA_QUALITY_MONITORING_RESULTS
    WHERE database_name = '<database>' AND schema_name = '<schema>'
        AND measurement_time = (SELECT MAX(measurement_time) FROM runs)
),
previous_run AS (
    SELECT table_name, metric_name, metric_value
    FROM SNOWFLAKE.ACCOUNT_USAGE.DATA_QUALITY_MONITORING_RESULTS
    WHERE database_name = '<database>' AND schema_name = '<schema>'
        AND measurement_time = (SELECT MIN(measurement_time) FROM runs)
)
SELECT
    COALESCE(c.table_name, p.table_name) AS table_name,
    COALESCE(c.metric_name, p.metric_name) AS metric_name,
    COALESCE(p.metric_value, 0) AS previous_value,
    COALESCE(c.metric_value, 0) AS current_value,
    CASE
        WHEN p.metric_value = 0 AND c.metric_value > 0 THEN 'NEW_FAILURE'
        WHEN p.metric_value > 0 AND c.metric_value = 0 THEN 'RESOLVED'
        WHEN c.metric_value > p.metric_value THEN 'WORSENED'
        WHEN c.metric_value < p.metric_value THEN 'IMPROVED'
        ELSE 'UNCHANGED'
    END AS status
FROM current_run c
FULL OUTER JOIN previous_run p ON c.table_name = p.table_name AND c.metric_name = p.metric_name
WHERE NOT (COALESCE(c.metric_value, 0) = 0 AND COALESCE(p.metric_value, 0) = 0)
ORDER BY
    CASE WHEN p.metric_value = 0 AND c.metric_value > 0 THEN 1 WHEN c.metric_value > p.metric_value THEN 2 ELSE 3 END;
```

## Quality Trends Over Time

```sql
SELECT
    DATE_TRUNC('day', measurement_time) AS day,
    ROUND((COUNT_IF(metric_value = 0) * 100.0) / NULLIF(COUNT(*), 0), 1) AS health_pct,
    COUNT_IF(metric_value > 0) AS failing_metrics,
    COUNT(*) AS total_metrics
FROM SNOWFLAKE.ACCOUNT_USAGE.DATA_QUALITY_MONITORING_RESULTS
WHERE database_name = '<database>' AND schema_name = '<schema>'
    AND measurement_time >= DATEADD('day', -30, CURRENT_TIMESTAMP())
GROUP BY day
ORDER BY day DESC;
```

## Fallback: Basic Table Inspection (No DMFs)

When DMFs aren't attached, fall back to basic health indicators.

```sql
SELECT
    table_name,
    row_count,
    ROUND(bytes / (1024*1024), 2) AS size_mb,
    last_altered,
    DATEDIFF('hour', last_altered, CURRENT_TIMESTAMP()) AS hours_since_altered,
    CASE
        WHEN DATEDIFF('hour', last_altered, CURRENT_TIMESTAMP()) > 48 THEN 'POSSIBLY_STALE'
        ELSE 'RECENT'
    END AS freshness_status
FROM <database>.INFORMATION_SCHEMA.TABLES
WHERE table_schema = '<schema>'
ORDER BY last_altered DESC;
```

## Dynamic Table Health

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

## Constraints

- DMF results require DMFs to be attached to tables (this primitive does not cover DMF setup)
- DATA_QUALITY_MONITORING_RESULTS has ~2 hour latency
- Need at least 2 measurement runs for regression detection
- Health scores are only meaningful if DMFs cover the columns/tables you care about

## Anti-patterns

| Pattern | Why It Fails | Instead |
|---------|-------------|---------|
| Assuming 100% health means data is correct | DMFs only check what they're configured to check | Health score reflects DMF coverage, not absolute correctness |
| Comparing runs from different metric sets | If new DMFs were added between runs, regression detection will show false "new failures" | Compare only metrics that exist in both runs |
| Creating SLA alerts without baseline | Alerting on metrics that normally fluctuate causes noise | Establish baseline with trend analysis first |

## References

- `primitives/lineage-queries`
- `primitives/table-comparison`
- [Data Quality Monitoring](https://docs.snowflake.com/en/user-guide/data-quality-intro)
