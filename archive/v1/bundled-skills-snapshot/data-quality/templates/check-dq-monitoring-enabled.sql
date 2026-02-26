-- Check DATA_QUALITY_MONITORING_RESULTS Availability
-- Verify if ACCOUNT_USAGE.DATA_QUALITY_MONITORING_RESULTS view is accessible
-- This view is available by default in Snowflake and stores historical DMF results
-- Required for regression detection, trend analysis, and time-series queries

-- Replace <database> with your target database name

-- NOTE: DATA_QUALITY_MONITORING_RESULTS is NOT a parameter - it's a view that exists by default
-- The queries below check if the view is accessible and contains data

-- Verify historical data is being collected
-- If enabled, this should return results; if disabled or newly enabled, it may be empty
SELECT
    DATABASE_NAME,
    SCHEMA_NAME,
    COUNT(DISTINCT table_name) AS tables_tracked,
    COUNT(DISTINCT DATE_TRUNC('day', measurement_time)) AS days_of_data,
    MIN(measurement_time) AS oldest_record,
    MAX(measurement_time) AS newest_record,
    COUNT(*) AS total_measurements
FROM SNOWFLAKE.ACCOUNT_USAGE.DATA_QUALITY_MONITORING_RESULTS
WHERE DATABASE_NAME = '<database>'
GROUP BY DATABASE_NAME, SCHEMA_NAME
ORDER BY SCHEMA_NAME;

-- Check overall monitoring results availability
SELECT
    COUNT(DISTINCT database_name) AS databases_tracked,
    COUNT(DISTINCT database_name || '.' || schema_name) AS schemas_tracked,
    COUNT(DISTINCT database_name || '.' || schema_name || '.' || table_name) AS tables_tracked,
    MIN(measurement_time) AS earliest_measurement,
    MAX(measurement_time) AS latest_measurement,
    DATEDIFF(day, MIN(measurement_time), MAX(measurement_time)) AS days_of_history
FROM SNOWFLAKE.ACCOUNT_USAGE.DATA_QUALITY_MONITORING_RESULTS;

/*
Interpretation:

If ACCOUNT_USAGE.DATA_QUALITY_MONITORING_RESULTS query returns:
- 0 rows: DMFs haven't run yet, or no DMFs are attached to tables
  → Attach DMFs to tables using check-dmf-status.sql guidance
  → Wait for DMFs to execute (based on schedule: TRIGGER_ON_CHANGES, cron, etc.)
  → Historical tracking starts automatically once DMFs run

- >0 rows but days_of_data = 1: Historical data exists but limited
  → Regression queries need at least 2 measurement points
  → Wait for next scheduled DMF run
  → For now, use schema-health-snapshot.sql or real-time templates

- >0 rows and days_of_data > 1: Good! Sufficient historical data available
  → All time-series queries will work
  → Regression detection available
  → Trend analysis available

What Each Metric Means:
- tables_tracked: Number of tables with DMF execution history
- days_of_data: Number of distinct days with measurements
- oldest_record: When first DMF ran (historical tracking begins here)
- newest_record: Most recent DMF run
- total_measurements: Total number of metric measurements stored

Important Notes:

1. ACCOUNT_USAGE Latency:
   - Data appears in ACCOUNT_USAGE views 45 minutes to 3 hours after DMF execution
   - For immediate results, use real-time templates (schema-*-realtime.sql)
   - For historical analysis, use ACCOUNT_USAGE templates

2. If no historical data (0 rows):
   - Verify DMFs are attached: Run check-dmf-status.sql
   - Check DMF schedule: Ensure tables have DATA_METRIC_SCHEDULE set
   - Wait for DMFs to execute based on schedule
   - Wait additional 45min-3hr for ACCOUNT_USAGE replication

3. If limited historical data (1 day):
   - Regression queries need at least 2 measurement points
   - Use real-time or current snapshot queries for now
   - Wait for next scheduled DMF run

4. If sufficient historical data (2+ days):
   - All advanced queries available:
     * schema-regression-detection.sql (compare runs)
     * schema-quality-trends.sql (analyze over time)
     * schema-sla-alert.sql (monitor for violations)

Prerequisites for Different Queries:

| Query Type                    | Requires DMFs | Requires Monitoring Results | Min History |
|-------------------------------|---------------|----------------------------|-------------|
| schema-health-snapshot.sql    | ✅            | ✅                         | 1 run       |
| schema-root-cause.sql         | ✅            | ✅                         | 1 run       |
| schema-regression-detection.sql| ✅           | ✅                         | 2 runs      |
| schema-quality-trends.sql     | ✅            | ✅                         | 3+ runs     |
| schema-sla-alert.sql          | ✅            | ✅                         | 1 run       |
| check-dmf-status.sql          | ✅            | ❌                         | N/A         |

Note: ACCOUNT_USAGE views have latency (typically 45 min - 3 hours)
For real-time data, query INFORMATION_SCHEMA.DATA_METRICS instead
*/
