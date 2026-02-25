-- Schema Root Cause Analysis
-- Identify which tables and columns have failing quality metrics and why
-- Requires: DMFs attached to tables, DATA_QUALITY_MONITORING_RESULTS enabled

-- Replace <database> and <schema> with your target database and schema names

WITH latest_metrics AS (
  SELECT
    database_name,
    schema_name,
    table_name,
    column_name,
    metric_name,
    metric_value,
    threshold,
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
  database_name || '.' || schema_name || '.' || table_name AS full_table_name,
  COALESCE(column_name, '<table-level>') AS column_name,
  metric_name,
  metric_value AS current_value,
  threshold AS expected_threshold,
  CASE
    WHEN metric_value > threshold * 2 THEN 'CRITICAL'
    WHEN metric_value > threshold * 1.5 THEN 'HIGH'
    WHEN metric_value > threshold THEN 'MEDIUM'
    ELSE 'LOW'
  END AS severity,
  CASE metric_name
    WHEN 'NULL_COUNT' THEN 'Add NOT NULL constraint or fix upstream data pipeline'
    WHEN 'FRESHNESS' THEN 'Check ETL schedule - data may be stale'
    WHEN 'DUPLICATE_COUNT' THEN 'Add UNIQUE constraint or deduplicate data'
    WHEN 'ROW_COUNT' THEN 'Check if table is unexpectedly empty or too large'
    WHEN 'NEGATIVE_VALUES' THEN 'Add CHECK constraint to enforce non-negative values'
    ELSE 'Review custom DMF logic and fix data issues'
  END AS recommended_action,
  measured_at
FROM latest_metrics
WHERE metric_value > 0  -- Only show failing metrics
ORDER BY
  CASE
    WHEN metric_value > threshold * 2 THEN 1
    WHEN metric_value > threshold * 1.5 THEN 2
    WHEN metric_value > threshold THEN 3
    ELSE 4
  END,
  metric_value DESC;

-- Summary by table
SELECT
  table_name,
  COUNT(*) AS failing_metric_count,
  LISTAGG(DISTINCT metric_name, ', ') AS failing_metrics,
  MAX(CASE
    WHEN metric_value > threshold * 2 THEN 'CRITICAL'
    WHEN metric_value > threshold * 1.5 THEN 'HIGH'
    WHEN metric_value > threshold THEN 'MEDIUM'
    ELSE 'LOW'
  END) AS max_severity
FROM latest_metrics
WHERE metric_value > 0
GROUP BY table_name
ORDER BY failing_metric_count DESC;
