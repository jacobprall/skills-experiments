-- Schema Health Snapshot
-- Calculate overall schema health score and identify failing metrics count
-- Requires: DMFs attached to tables, DATA_QUALITY_MONITORING_RESULTS enabled

-- Replace <database> and <schema> with your target database and schema names

WITH latest_metrics AS (
  SELECT
    database_name,
    schema_name,
    table_name,
    metric_name,
    metric_value,
    measurement_time
  FROM SNOWFLAKE.ACCOUNT_USAGE.DATA_QUALITY_MONITORING_RESULTS
  WHERE database_name = '<database>'
    AND schema_name = '<schema>'
    AND measurement_time = (
      SELECT MAX(measurement_time)
      FROM SNOWFLAKE.ACCOUNT_USAGE.DATA_QUALITY_MONITORING_RESULTS
      WHERE database_name = '<database>'
        AND schema_name = '<schema>'
    )
)
SELECT
  database_name,
  schema_name,
  ROUND((COUNT_IF(metric_value = 0) * 100.0) / NULLIF(COUNT(*), 0), 1) AS health_pct,
  COUNT_IF(metric_value = 0) AS passing_metrics,
  COUNT_IF(metric_value > 0) AS failing_metrics,
  COUNT(*) AS total_metrics,
  COUNT(DISTINCT table_name) AS tables_monitored,
  COUNT(DISTINCT CASE WHEN metric_value > 0 THEN table_name END) AS tables_with_issues,
  MAX(measurement_time) AS measured_at
FROM latest_metrics
GROUP BY database_name, schema_name;

-- Interpretation:
-- health_pct = 100%: All metrics passing (perfect health)
-- health_pct = 90-99%: Minor issues (good health)
-- health_pct = 75-89%: Moderate issues (needs attention)
-- health_pct < 75%: Significant issues (critical)
