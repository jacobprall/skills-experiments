---
parent_skill: data-quality
---

# Data Metric Functions (DMF) Concepts

## Overview

Snowflake Data Metric Functions (DMFs) provide built-in data quality monitoring capabilities to automatically track and measure data quality metrics across your tables and schemas. Understanding these concepts is essential before working with schema-level data quality monitoring workflows.

## Key Concepts

### 1. Data Metric Functions (DMFs)

A **Data Metric Function (DMF)** is a Snowflake function that computes a quality metric for a table or column. DMFs run automatically when data changes, enabling continuous data quality monitoring.

**Two types of DMFs:**

| Type | Description | Use Case |
|------|-------------|----------|
| **System DMFs** | Pre-built metrics by Snowflake | Common quality checks (nulls, freshness, uniqueness) |
| **Custom DMFs** | User-defined quality metrics | Domain-specific quality rules |

### 2. System DMFs

Snowflake provides built-in system DMFs for common quality checks:

**Data Freshness:**
```sql
SNOWFLAKE.CORE.FRESHNESS(
  TABLE_NAME => 'schema.table',
  TIMESTAMP_COLUMN => 'updated_at'
)
```
Measures how recent the data is based on a timestamp column.

**Null Count:**
```sql
SNOWFLAKE.CORE.NULL_COUNT(
  TABLE_NAME => 'schema.table',
  COLUMN_NAME => 'customer_id'
)
```
Counts null values in a column.

**Unique Count:**
```sql
SNOWFLAKE.CORE.UNIQUE_COUNT(
  TABLE_NAME => 'schema.table',
  COLUMN_NAME => 'email'
)
```
Counts unique values in a column.

**Duplicate Count:**
```sql
SNOWFLAKE.CORE.DUPLICATE_COUNT(
  TABLE_NAME => 'schema.table',
  COLUMN_NAME => 'email'
)
```
Counts duplicate values in a column.

**Row Count:**
```sql
SNOWFLAKE.CORE.ROW_COUNT(
  TABLE_NAME => 'schema.table'
)
```
Counts total rows in a table.

### 3. Custom DMFs

For domain-specific quality rules, create **Custom DMFs**:

```sql
CREATE OR REPLACE DATA METRIC FUNCTION my_schema.valid_email_pct()
RETURNS NUMBER
AS
$$
SELECT
  (COUNT_IF(email RLIKE '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}$') * 100.0) /
  NULLIF(COUNT(*), 0)
FROM TABLE(UPSTREAM_TABLES())
$$;
```

**Use cases:**
- Business rule validation (e.g., price > 0)
- Format validation (e.g., email patterns, phone formats)
- Referential integrity (e.g., foreign key checks)
- Statistical outliers (e.g., values outside 3 standard deviations)
- Cross-column validation (e.g., start_date < end_date)

### 4. Attaching DMFs to Tables

DMFs must be attached to tables to monitor them:

```sql
-- Attach a single DMF to a table
ALTER TABLE my_schema.customers
  ADD DATA METRIC FUNCTION SNOWFLAKE.CORE.NULL_COUNT
  ON (email);

-- Attach multiple DMFs
ALTER TABLE my_schema.customers
  ADD DATA METRIC FUNCTION SNOWFLAKE.CORE.FRESHNESS ON (updated_at),
  ADD DATA METRIC FUNCTION SNOWFLAKE.CORE.DUPLICATE_COUNT ON (email),
  ADD DATA METRIC FUNCTION my_schema.valid_email_pct ON ();
```

**Schema-wide attachment:**
```sql
-- Attach DMF to all tables in a schema
ALTER SCHEMA my_schema
  SET DATA_METRIC_SCHEDULE = 'TRIGGER_ON_CHANGES';
```

### 5. DMF Scheduling

DMFs can run on different schedules:

| Schedule Type | Description | Use Case |
|--------------|-------------|----------|
| `TRIGGER_ON_CHANGES` | Run when data changes | Real-time quality monitoring |
| `CRON` | Run on a schedule (e.g., hourly, daily) | Periodic quality checks |
| `MANUAL` | Run only when explicitly triggered | Ad-hoc quality audits |

```sql
-- Set schedule for a schema
ALTER SCHEMA my_schema
  SET DATA_METRIC_SCHEDULE = 'USING CRON 0 */6 * * * UTC';
```

### 6. DATA_QUALITY_MONITORING_RESULTS

To enable time-series analysis and trend tracking, enable `DATA_QUALITY_MONITORING_RESULTS`:

```sql
-- Enable at account level
ALTER ACCOUNT SET DATA_QUALITY_MONITORING_RESULTS = TRUE;

-- Enable for a specific database
ALTER DATABASE my_database SET DATA_QUALITY_MONITORING_RESULTS = TRUE;
```

**What it does:**
- Stores historical DMF results over time
- Enables regression detection (comparing current vs. previous runs)
- Powers trend analysis queries
- Supports SLA alerting based on quality degradation

**Without DATA_QUALITY_MONITORING_RESULTS:**
- Only current DMF values are available
- No historical comparison possible
- Regression and trend queries won't work

### 7. Viewing DMF Results

**Current DMF status:**
```sql
-- See which DMFs are attached to tables
SELECT *
FROM INFORMATION_SCHEMA.DATA_METRICS
WHERE TABLE_SCHEMA = 'MY_SCHEMA';
```

**Historical DMF results:**
```sql
-- Query time-series results (requires DATA_QUALITY_MONITORING_RESULTS enabled)
SELECT *
FROM SNOWFLAKE.ACCOUNT_USAGE.DATA_QUALITY_MONITORING_RESULTS
WHERE DATABASE_NAME = 'MY_DATABASE'
  AND SCHEMA_NAME = 'MY_SCHEMA'
ORDER BY MEASUREMENT_TIME DESC;
```

### 8. Schema-Level Health Score

A **Schema Health Score** aggregates all DMF results across tables:

```sql
-- Calculate schema health percentage
SELECT
  (COUNT_IF(metric_value = 0) * 100.0) / COUNT(*) AS health_pct,
  COUNT_IF(metric_value > 0) AS failing_metrics,
  COUNT(*) AS total_metrics
FROM SNOWFLAKE.ACCOUNT_USAGE.DATA_QUALITY_MONITORING_RESULTS
WHERE DATABASE_NAME = 'MY_DATABASE'
  AND SCHEMA_NAME = 'MY_SCHEMA'
  AND MEASUREMENT_TIME = (
    SELECT MAX(MEASUREMENT_TIME)
    FROM SNOWFLAKE.ACCOUNT_USAGE.DATA_QUALITY_MONITORING_RESULTS
  );
```

**Interpretation:**
- 100% = All metrics passing (perfect health)
- 90-99% = Minor issues (good health)
- 75-89% = Moderate issues (needs attention)
- <75% = Significant issues (critical)

### 9. SLA Enforcement

Set quality SLAs and alert when violated:

```sql
-- Alert if schema health drops below 90%
CREATE ALERT my_schema_sla_alert
  WAREHOUSE = compute_wh
  SCHEDULE = '60 MINUTE'
IF (EXISTS (
  SELECT 1
  FROM (
    SELECT
      (COUNT_IF(metric_value = 0) * 100.0) / COUNT(*) AS health_pct
    FROM SNOWFLAKE.ACCOUNT_USAGE.DATA_QUALITY_MONITORING_RESULTS
    WHERE DATABASE_NAME = 'MY_DATABASE'
      AND SCHEMA_NAME = 'MY_SCHEMA'
      AND MEASUREMENT_TIME >= DATEADD(hour, -1, CURRENT_TIMESTAMP())
  )
  WHERE health_pct < 90
))
THEN CALL send_notification('Schema health SLA violated!');
```

### 10. Regression Detection

Compare current quality vs. previous run:

```sql
-- Detect tables with quality degradation
WITH current_run AS (
  SELECT table_name, metric_name, metric_value
  FROM SNOWFLAKE.ACCOUNT_USAGE.DATA_QUALITY_MONITORING_RESULTS
  WHERE measurement_time = (SELECT MAX(measurement_time) FROM ...)
),
previous_run AS (
  SELECT table_name, metric_name, metric_value
  FROM SNOWFLAKE.ACCOUNT_USAGE.DATA_QUALITY_MONITORING_RESULTS
  WHERE measurement_time = (SELECT MAX(measurement_time) FROM ... WHERE measurement_time < (SELECT MAX...))
)
SELECT
  c.table_name,
  c.metric_name,
  p.metric_value AS previous_value,
  c.metric_value AS current_value,
  c.metric_value - p.metric_value AS change
FROM current_run c
JOIN previous_run p ON c.table_name = p.table_name AND c.metric_name = p.metric_name
WHERE c.metric_value > p.metric_value  -- Quality degraded
ORDER BY change DESC;
```

## Privilege Requirements

| Operation | Required Privilege |
|-----------|-------------------|
| Create DMF | CREATE DATA METRIC FUNCTION on schema |
| Attach DMF to table | MODIFY on table |
| View DMF metadata | SELECT on INFORMATION_SCHEMA.DATA_METRICS |
| View DMF results | ACCESS to ACCOUNT_USAGE views |
| Create alerts | CREATE ALERT on schema + EXECUTE TASK |
| Enable monitoring results | ACCOUNTADMIN (for account) or MODIFY (for database) |

## Best Practices

1. **Start with system DMFs** - Use built-in metrics before creating custom ones
2. **Attach at schema level** - Automatically monitor all tables in a schema
3. **Enable DATA_QUALITY_MONITORING_RESULTS early** - Required for trend analysis
4. **Set appropriate schedules** - Balance freshness vs. compute costs
5. **Define SLAs upfront** - Know what "healthy" means for your data
6. **Test custom DMFs** - Validate logic before attaching to production tables
7. **Monitor compute usage** - DMFs consume warehouse credits

## DMF Verification (CRITICAL)

**Always verify DMFs are attached and functioning:**

```sql
-- Check if DMFs are attached
SELECT COUNT(*) AS dmf_count
FROM INFORMATION_SCHEMA.DATA_METRICS
WHERE TABLE_SCHEMA = 'MY_SCHEMA';
```

**If dmf_count = 0:**
- No DMFs attached to schema
- Schema health queries will return empty results
- User needs to attach DMFs first

```sql
-- Check if DATA_QUALITY_MONITORING_RESULTS is enabled
SHOW PARAMETERS LIKE 'DATA_QUALITY_MONITORING_RESULTS' IN DATABASE my_database;
```

**If value = FALSE:**
- Historical results not stored
- Regression detection won't work
- Trend analysis not possible
- Only current snapshot available

## Workflow Integration

```
                    ┌─────────────────────┐
                    │   Define DMFs       │
                    │  (System + Custom)  │
                    └──────────┬──────────┘
                               │
                               ▼
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│  Attach DMFs    │──▶│  Set Schedule   │──▶│  Enable Results │
│  to Tables      │   │ (Trigger/Cron)  │   │    Tracking     │
└─────────────────┘   └─────────────────┘   └────────┬────────┘
                                                     │
                                                     ▼
                                            ┌─────────────────┐
                                            │   Monitor &     │
                                            │  Alert on SLAs  │
                                            └─────────────────┘
```

## Common Patterns

### Pattern 1: Schema Health Dashboard
1. Attach DMFs to all tables in schema
2. Enable DATA_QUALITY_MONITORING_RESULTS
3. Query schema health score periodically
4. Visualize trends in dashboard

### Pattern 2: Automated Quality Gates
1. Define quality SLAs (e.g., 95% health)
2. Create alerts for SLA violations
3. Integrate with CI/CD pipelines
4. Block deployments if quality degrades

### Pattern 3: Root Cause Analysis
1. Detect schema health drop
2. Query failing tables and metrics
3. Drill down to column-level issues
4. Remediate data quality problems

## Next Steps

After understanding DMF concepts:

1. **For schema health checks**: Use `schema-health-snapshot.sql` template
2. **For root cause analysis**: Use `schema-root-cause.sql` template
3. **For regression detection**: Use `schema-regression-detection.sql` template
4. **For SLA enforcement**: Use `schema-sla-alert.sql` template
5. **For trend analysis**: Use `schema-quality-trends.sql` template
