-- Schema Quality Trends
-- Analyze data quality trends over time to identify patterns and degradation
-- Requires: DMFs attached, DATA_QUALITY_MONITORING_RESULTS enabled, sufficient historical data

-- Replace <database> and <schema> with your target database and schema names
-- Replace <days_back> with the number of days to analyze (e.g., 30 for last 30 days)

-- Daily schema health trend
WITH daily_health AS (
  SELECT
    DATE_TRUNC('day', measurement_time) AS measurement_date,
    database_name,
    schema_name,
    ROUND((COUNT_IF(metric_value = 0) * 100.0) / NULLIF(COUNT(*), 0), 1) AS health_pct,
    COUNT_IF(metric_value = 0) AS passing_metrics,
    COUNT_IF(metric_value > 0) AS failing_metrics,
    COUNT(*) AS total_metrics
  FROM SNOWFLAKE.ACCOUNT_USAGE.DATA_QUALITY_MONITORING_RESULTS
  WHERE database_name = '<database>'
    AND schema_name = '<schema>'
    AND measurement_time >= DATEADD(day, -<days_back>, CURRENT_TIMESTAMP())
  GROUP BY
    DATE_TRUNC('day', measurement_time),
    database_name,
    schema_name
)
SELECT
  measurement_date,
  database_name || '.' || schema_name AS full_schema_name,
  health_pct,
  failing_metrics,
  total_metrics,
  LAG(health_pct, 1) OVER (ORDER BY measurement_date) AS previous_day_health,
  health_pct - LAG(health_pct, 1) OVER (ORDER BY measurement_date) AS day_over_day_change,
  CASE
    WHEN health_pct > LAG(health_pct, 1) OVER (ORDER BY measurement_date) THEN 'IMPROVING'
    WHEN health_pct < LAG(health_pct, 1) OVER (ORDER BY measurement_date) THEN 'DEGRADING'
    ELSE 'STABLE'
  END AS trend
FROM daily_health
ORDER BY measurement_date DESC;

-- Weekly aggregated trend
WITH daily_metrics AS (
  SELECT
    DATE_TRUNC('week', measurement_time) AS week_start_date,
    DATE_TRUNC('day', measurement_time) AS measurement_day,
    database_name,
    schema_name,
    (COUNT_IF(metric_value = 0) * 100.0) / NULLIF(COUNT(*), 0) AS daily_health_pct,
    COUNT_IF(metric_value > 0) AS daily_failing_metrics
  FROM SNOWFLAKE.ACCOUNT_USAGE.DATA_QUALITY_MONITORING_RESULTS
  WHERE database_name = '<database>'
    AND schema_name = '<schema>'
    AND measurement_time >= DATEADD(day, -<days_back>, CURRENT_TIMESTAMP())
  GROUP BY
    DATE_TRUNC('week', measurement_time),
    DATE_TRUNC('day', measurement_time),
    database_name,
    schema_name
),
weekly_health AS (
  SELECT
    week_start_date,
    database_name,
    schema_name,
    ROUND(AVG(daily_health_pct), 1) AS avg_health_pct,
    ROUND(MIN(daily_health_pct), 1) AS min_health_pct,
    ROUND(MAX(daily_health_pct), 1) AS max_health_pct,
    ROUND(AVG(daily_failing_metrics), 0) AS avg_failing_metrics
  FROM daily_metrics
  GROUP BY
    week_start_date,
    database_name,
    schema_name
)
SELECT
  week_start_date,
  database_name || '.' || schema_name AS full_schema_name,
  avg_health_pct AS avg_weekly_health,
  min_health_pct AS worst_day_health,
  max_health_pct AS best_day_health,
  avg_failing_metrics,
  LAG(avg_health_pct, 1) OVER (ORDER BY week_start_date) AS previous_week_health,
  ROUND(avg_health_pct - LAG(avg_health_pct, 1) OVER (ORDER BY week_start_date), 1) AS week_over_week_change
FROM weekly_health
ORDER BY week_start_date DESC;

-- Metric-level trend (which metrics are consistently failing)
SELECT
  metric_name,
  table_name,
  COALESCE(column_name, '<table-level>') AS column_name,
  COUNT(DISTINCT DATE_TRUNC('day', measurement_time)) AS days_failing,
  ROUND(AVG(metric_value), 2) AS avg_metric_value,
  MIN(metric_value) AS best_value,
  MAX(metric_value) AS worst_value,
  MIN(measurement_time) AS first_failure,
  MAX(measurement_time) AS last_failure
FROM SNOWFLAKE.ACCOUNT_USAGE.DATA_QUALITY_MONITORING_RESULTS
WHERE database_name = '<database>'
  AND schema_name = '<schema>'
  AND metric_value > 0  -- Only failing metrics
  AND measurement_time >= DATEADD(day, -<days_back>, CURRENT_TIMESTAMP())
GROUP BY metric_name, table_name, column_name
HAVING days_failing > 1  -- Consistently failing (more than 1 day)
ORDER BY days_failing DESC, avg_metric_value DESC
LIMIT 20;

-- Table-level trend (which tables are most problematic over time)
WITH daily_table_metrics AS (
  SELECT
    table_name,
    DATE_TRUNC('day', measurement_time) AS measurement_day,
    metric_name,
    (COUNT_IF(metric_value = 0) * 100.0) / NULLIF(COUNT(*), 0) AS daily_health_pct,
    COUNT_IF(metric_value > 0) AS daily_failures,
    MIN(measurement_time) AS first_measurement,
    MAX(measurement_time) AS last_measurement
  FROM SNOWFLAKE.ACCOUNT_USAGE.DATA_QUALITY_MONITORING_RESULTS
  WHERE database_name = '<database>'
    AND schema_name = '<schema>'
    AND measurement_time >= DATEADD(day, -<days_back>, CURRENT_TIMESTAMP())
  GROUP BY
    DATE_TRUNC('day', measurement_time),
    table_name,
    metric_name
)
SELECT
  table_name,
  COUNT(DISTINCT measurement_day) AS days_with_failures,
  COUNT(DISTINCT metric_name) AS distinct_failing_metrics,
  ROUND(AVG(daily_health_pct), 1) AS avg_table_health,
  SUM(daily_failures) AS total_failures,
  MIN(first_measurement) AS first_issue_detected,
  MAX(last_measurement) AS last_issue_detected
FROM daily_table_metrics
WHERE daily_failures > 0
GROUP BY table_name
HAVING total_failures > 0
ORDER BY days_with_failures DESC, total_failures DESC
LIMIT 20;

-- Overall trend summary
WITH trend_summary AS (
  SELECT
    DATE_TRUNC('day', measurement_time) AS measurement_date,
    ROUND((COUNT_IF(metric_value = 0) * 100.0) / NULLIF(COUNT(*), 0), 1) AS health_pct
  FROM SNOWFLAKE.ACCOUNT_USAGE.DATA_QUALITY_MONITORING_RESULTS
  WHERE database_name = '<database>'
    AND schema_name = '<schema>'
    AND measurement_time >= DATEADD(day, -<days_back>, CURRENT_TIMESTAMP())
  GROUP BY DATE_TRUNC('day', measurement_time)
)
SELECT
  MIN(measurement_date) AS period_start,
  MAX(measurement_date) AS period_end,
  DATEDIFF(day, MIN(measurement_date), MAX(measurement_date)) AS days_analyzed,
  ROUND(AVG(health_pct), 1) AS avg_health,
  MIN(health_pct) AS worst_health,
  MAX(health_pct) AS best_health,
  ROUND(STDDEV(health_pct), 1) AS health_volatility,
  CASE
    WHEN REGR_SLOPE(health_pct, DATEDIFF(day, MIN(measurement_date) OVER (), measurement_date)) > 0.1
    THEN 'IMPROVING'
    WHEN REGR_SLOPE(health_pct, DATEDIFF(day, MIN(measurement_date) OVER (), measurement_date)) < -0.1
    THEN 'DEGRADING'
    ELSE 'STABLE'
  END AS overall_trend,
  ROUND(
    REGR_SLOPE(health_pct, DATEDIFF(day, MIN(measurement_date) OVER (), measurement_date)),
    3
  ) AS trend_slope
FROM trend_summary;

/*
Interpretation Guide:

Daily/Weekly Trends:
- health_pct: Overall schema health percentage
- day_over_day_change: How much health changed from previous day
- trend: Whether quality is IMPROVING, DEGRADING, or STABLE

Metric-level Trends:
- days_failing: How many days this metric has been failing
- avg_metric_value: Average severity of failures
- Use this to identify chronic issues vs. one-off problems

Table-level Trends:
- days_with_failures: How many days the table had any failing metrics
- distinct_failing_metrics: Number of different metrics that failed
- High values indicate systemic table issues

Overall Trend Summary:
- avg_health: Average health over the period
- health_volatility: How stable the quality is (low = stable, high = erratic)
- trend_slope: Mathematical trend (positive = improving, negative = degrading)
- overall_trend: Simplified trend direction

Dashboard Visualization Suggestions:
1. Line chart: daily health_pct over time
2. Bar chart: top 10 tables by days_with_failures
3. Heatmap: metric_name vs. table_name with avg_metric_value as intensity
4. KPI cards: current health, avg health, trend direction
*/
