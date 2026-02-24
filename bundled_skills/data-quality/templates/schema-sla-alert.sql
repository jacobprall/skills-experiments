-- Schema SLA Alert
-- Create a Snowflake Alert to monitor schema health and notify on SLA violations
-- Requires: DMFs attached, DATA_QUALITY_MONITORING_RESULTS enabled, CREATE ALERT privilege

-- Replace the following placeholders:
-- <alert_name>: Name for the alert (e.g., sales_schema_quality_alert)
-- <warehouse>: Warehouse to use for alert evaluation (e.g., COMPUTE_WH)
-- <database>: Target database name
-- <schema>: Target schema name
-- <health_threshold>: Minimum acceptable health percentage (e.g., 90)
-- <log_database>: Database for alert log table (can be same as <database> or a dedicated monitoring database)
-- <log_schema>: Schema for alert log table (can be same as <schema> or a dedicated monitoring schema)
-- <notification_action>: Action to take when alert fires (e.g., stored procedure, email integration)

-- IMPORTANT: This template creates a DQ_ALERT_LOG table to store alert history.
-- Consider using a dedicated monitoring database/schema instead of the monitored schema.
-- Ensure you have CREATE TABLE privileges in the target location.

-- Step 1: Create the alert
CREATE OR REPLACE ALERT <alert_name>
  WAREHOUSE = <warehouse>
  SCHEDULE = '60 MINUTE'  -- Check every hour (adjust as needed)
IF (EXISTS (
  WITH latest_metrics AS (
    SELECT
      database_name,
      schema_name,
      metric_value,
      measurement_time
    FROM SNOWFLAKE.ACCOUNT_USAGE.DATA_QUALITY_MONITORING_RESULTS
    WHERE database_name = '<database>'
      AND schema_name = '<schema>'
      AND measurement_time >= DATEADD(hour, -1, CURRENT_TIMESTAMP())
  ),
  health_check AS (
    SELECT
      database_name,
      schema_name,
      ROUND((COUNT_IF(metric_value = 0) * 100.0) / NULLIF(COUNT(*), 0), 1) AS health_pct,
      COUNT_IF(metric_value > 0) AS failing_metrics,
      COUNT(*) AS total_metrics,
      MAX(measurement_time) AS measured_at
    FROM latest_metrics
    GROUP BY database_name, schema_name
  )
  SELECT 1
  FROM health_check
  WHERE health_pct < <health_threshold>  -- SLA violation threshold
))
THEN
  -- Notification action placeholder
  -- Replace this with your notification mechanism:
  --   Option 1: Call a stored procedure that sends notifications
  --   CALL NOTIFICATIONS_DB.ALERTS.send_dq_alert('<database>.<schema>', health_pct, failing_metrics);
  --
  --   Option 2: Insert into a notifications table
  --   INSERT INTO NOTIFICATIONS_DB.ALERTS.dq_violations
  --   SELECT database_name, schema_name, health_pct, failing_metrics, measured_at
  --   FROM health_check WHERE health_pct < <health_threshold>;
  --
  --   Option 3: Use Snowflake's EMAIL integration (requires setup)
  --   CALL SYSTEM$SEND_EMAIL(...);

  -- For now, log to a monitoring table:
  INSERT INTO <log_database>.<log_schema>.DQ_ALERT_LOG (
    alert_name,
    database_name,
    schema_name,
    health_pct,
    failing_metrics,
    measured_at,
    alert_fired_at
  )
  SELECT
    '<alert_name>',
    database_name,
    schema_name,
    health_pct,
    failing_metrics,
    measured_at,
    CURRENT_TIMESTAMP()
  FROM (
    SELECT
      database_name,
      schema_name,
      ROUND((COUNT_IF(metric_value = 0) * 100.0) / NULLIF(COUNT(*), 0), 1) AS health_pct,
      COUNT_IF(metric_value > 0) AS failing_metrics,
      MAX(measurement_time) AS measured_at
    FROM SNOWFLAKE.ACCOUNT_USAGE.DATA_QUALITY_MONITORING_RESULTS
    WHERE database_name = '<database>'
      AND schema_name = '<schema>'
      AND measurement_time >= DATEADD(hour, -1, CURRENT_TIMESTAMP())
    GROUP BY database_name, schema_name
  )
  WHERE health_pct < <health_threshold>;

-- Step 2: Create alert log table (if it doesn't exist)
-- Run this BEFORE creating the alert above
CREATE TABLE IF NOT EXISTS <log_database>.<log_schema>.DQ_ALERT_LOG (
  alert_name VARCHAR,
  database_name VARCHAR,
  schema_name VARCHAR,
  health_pct FLOAT,
  failing_metrics INTEGER,
  measured_at TIMESTAMP_NTZ,
  alert_fired_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- Step 3: Resume the alert (alerts are created in suspended state)
ALTER ALERT <alert_name> RESUME;

-- Step 4: Verify alert was created
SHOW ALERTS LIKE '<alert_name>';

-- Step 5: View alert history
SELECT *
FROM TABLE(INFORMATION_SCHEMA.ALERT_HISTORY(
  SCHEDULED_TIME_RANGE_START => DATEADD(day, -7, CURRENT_TIMESTAMP())
))
WHERE NAME = '<alert_name>'
ORDER BY SCHEDULED_TIME DESC;

-- Optional: Query alert log to see violations
SELECT
  alert_name,
  database_name || '.' || schema_name AS full_schema_name,
  health_pct,
  failing_metrics,
  measured_at,
  alert_fired_at
FROM <log_database>.<log_schema>.DQ_ALERT_LOG
ORDER BY alert_fired_at DESC
LIMIT 20;

-- Optional: Suspend the alert (to disable)
-- ALTER ALERT <alert_name> SUSPEND;

-- Optional: Drop the alert (to remove)
-- DROP ALERT <alert_name>;

/*
Example Configuration:

CREATE ALERT sales_schema_quality_alert
  WAREHOUSE = COMPUTE_WH
  SCHEDULE = '60 MINUTE'
IF (EXISTS (
  SELECT 1 FROM ... WHERE health_pct < 90
))
THEN
  CALL NOTIFICATIONS.send_alert('SALES_DB.PUBLIC', health_pct);

This alert will:
- Check schema health every hour
- Fire if health drops below 90%
- Log violations to DQ_ALERT_LOG table
- Can be extended to send emails, Slack notifications, etc.

Integration Examples:
1. Slack: Call stored procedure that uses external function to Slack webhook
2. Email: Use Snowflake EMAIL notification integration
3. PagerDuty: Call external function that triggers PagerDuty incident
4. Webhook: Use external function to POST to any webhook endpoint
*/
