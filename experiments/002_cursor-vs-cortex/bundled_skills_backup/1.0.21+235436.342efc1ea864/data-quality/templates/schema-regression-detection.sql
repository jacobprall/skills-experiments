-- Schema Regression Detection
-- Compare current quality vs. previous run to detect degradation
-- Requires: DMFs attached, DATA_QUALITY_MONITORING_RESULTS enabled, at least 2 historical runs

-- Replace <database> and <schema> with your target database and schema names

WITH measurement_times AS (
  SELECT DISTINCT measurement_time
  FROM SNOWFLAKE.ACCOUNT_USAGE.DATA_QUALITY_MONITORING_RESULTS
  WHERE database_name = '<database>'
    AND schema_name = '<schema>'
  ORDER BY measurement_time DESC
  LIMIT 2
),
current_run AS (
  SELECT
    table_name,
    column_name,
    metric_name,
    metric_value,
    measurement_time
  FROM SNOWFLAKE.ACCOUNT_USAGE.DATA_QUALITY_MONITORING_RESULTS
  WHERE database_name = '<database>'
    AND schema_name = '<schema>'
    AND measurement_time = (SELECT MAX(measurement_time) FROM measurement_times)
),
previous_run AS (
  SELECT
    table_name,
    column_name,
    metric_name,
    metric_value,
    measurement_time
  FROM SNOWFLAKE.ACCOUNT_USAGE.DATA_QUALITY_MONITORING_RESULTS
  WHERE database_name = '<database>'
    AND schema_name = '<schema>'
    AND measurement_time = (SELECT MIN(measurement_time) FROM measurement_times)
)
-- Overall schema health change
SELECT
  'OVERALL SCHEMA HEALTH' AS analysis_type,
  ROUND((COUNT_IF(p.metric_value = 0) * 100.0) / NULLIF(COUNT(*), 0), 1) AS previous_health_pct,
  ROUND((COUNT_IF(c.metric_value = 0) * 100.0) / NULLIF(COUNT(*), 0), 1) AS current_health_pct,
  ROUND(
    (COUNT_IF(c.metric_value = 0) * 100.0) / NULLIF(COUNT(*), 0) -
    (COUNT_IF(p.metric_value = 0) * 100.0) / NULLIF(COUNT(*), 0),
    1
  ) AS health_change,
  CASE
    WHEN (COUNT_IF(c.metric_value = 0) * 100.0) / NULLIF(COUNT(*), 0) >
         (COUNT_IF(p.metric_value = 0) * 100.0) / NULLIF(COUNT(*), 0)
    THEN 'IMPROVED'
    WHEN (COUNT_IF(c.metric_value = 0) * 100.0) / NULLIF(COUNT(*), 0) <
         (COUNT_IF(p.metric_value = 0) * 100.0) / NULLIF(COUNT(*), 0)
    THEN 'DEGRADED'
    ELSE 'STABLE'
  END AS trend,
  MAX(p.measurement_time) AS previous_run_time,
  MAX(c.measurement_time) AS current_run_time
FROM current_run c
FULL OUTER JOIN previous_run p
  ON c.table_name = p.table_name
  AND c.metric_name = p.metric_name
  AND COALESCE(c.column_name, '') = COALESCE(p.column_name, '')
GROUP BY analysis_type;

-- Tables with quality regressions (metrics that got worse)
SELECT
  c.table_name,
  COALESCE(c.column_name, '<table-level>') AS column_name,
  c.metric_name,
  p.metric_value AS previous_value,
  c.metric_value AS current_value,
  c.metric_value - p.metric_value AS absolute_change,
  CASE
    WHEN p.metric_value = 0 THEN NULL
    ELSE ROUND(((c.metric_value - p.metric_value) * 100.0) / p.metric_value, 1)
  END AS pct_change,
  CASE
    WHEN c.metric_value - p.metric_value > p.metric_value THEN 'CRITICAL'
    WHEN c.metric_value - p.metric_value > p.metric_value * 0.5 THEN 'HIGH'
    WHEN c.metric_value - p.metric_value > 0 THEN 'MEDIUM'
    ELSE 'LOW'
  END AS severity,
  p.measurement_time AS previous_run_time,
  c.measurement_time AS current_run_time
FROM current_run c
JOIN previous_run p
  ON c.table_name = p.table_name
  AND c.metric_name = p.metric_name
  AND COALESCE(c.column_name, '') = COALESCE(p.column_name, '')
WHERE c.metric_value > p.metric_value  -- Quality degraded (higher metric value = worse)
ORDER BY
  c.metric_value - p.metric_value DESC,
  c.table_name;

-- New failures (metrics that were passing, now failing)
SELECT
  c.table_name,
  COALESCE(c.column_name, '<table-level>') AS column_name,
  c.metric_name,
  p.metric_value AS previous_value,
  c.metric_value AS current_value,
  'NEW_FAILURE' AS status,
  c.measurement_time AS failed_at
FROM current_run c
JOIN previous_run p
  ON c.table_name = p.table_name
  AND c.metric_name = p.metric_name
  AND COALESCE(c.column_name, '') = COALESCE(p.column_name, '')
WHERE p.metric_value = 0  -- Was passing
  AND c.metric_value > 0  -- Now failing
ORDER BY c.table_name;

-- Summary by table
SELECT
  c.table_name,
  COUNT(*) AS total_metrics,
  COUNT_IF(c.metric_value > p.metric_value) AS degraded_metrics,
  COUNT_IF(p.metric_value = 0 AND c.metric_value > 0) AS new_failures,
  COUNT_IF(c.metric_value < p.metric_value) AS improved_metrics,
  ROUND(
    (COUNT_IF(c.metric_value = 0) * 100.0) / NULLIF(COUNT(*), 0) -
    (COUNT_IF(p.metric_value = 0) * 100.0) / NULLIF(COUNT(*), 0),
    1
  ) AS health_change_pct
FROM current_run c
FULL OUTER JOIN previous_run p
  ON c.table_name = p.table_name
  AND c.metric_name = p.metric_name
  AND COALESCE(c.column_name, '') = COALESCE(p.column_name, '')
WHERE c.table_name IS NOT NULL
GROUP BY c.table_name
HAVING degraded_metrics > 0 OR new_failures > 0
ORDER BY new_failures DESC, degraded_metrics DESC;
