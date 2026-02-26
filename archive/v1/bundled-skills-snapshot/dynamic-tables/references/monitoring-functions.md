# Monitoring Functions Reference

Functions and commands for monitoring Snowflake Dynamic Tables.

## Key Functions Overview

| Function | Use Case |
|----------|----------|
| `INFORMATION_SCHEMA.DYNAMIC_TABLES()` | Metadata, lag stats, refresh state |
| `INFORMATION_SCHEMA.DYNAMIC_TABLE_REFRESH_HISTORY()` | Refresh history, errors, durations |
| `INFORMATION_SCHEMA.DYNAMIC_TABLE_GRAPH_HISTORY()` | DAG dependencies |
| `SHOW DYNAMIC TABLES` | Quick check for `refresh_mode` and `refresh_mode_reason` |
| `GET_DDL()` | Retrieve DDL definition |

**Note:** `refresh_mode` and `refresh_mode_reason` are only available via `SHOW DYNAMIC TABLES`, not via INFORMATION_SCHEMA.DYNAMIC_TABLES().

---

## INFORMATION_SCHEMA.DYNAMIC_TABLES()

Returns metadata about dynamic tables, including aggregate lag metrics and the status of the most recent refreshes, within 7 days of the current time.

**Reference**: https://docs.snowflake.com/en/sql-reference/functions/dynamic_tables

### Scope

**This function is ACCOUNT-SCOPED** - it returns dynamic tables from ALL databases visible to your current role, not just the current database.

### ⛔ MANDATORY: Set Database Context First

**ALWAYS** run `USE DATABASE` before calling this function (required for execution, not for scoping):
```sql
-- ✅ CORRECT: Set database context first
USE DATABASE ANY_DATABASE;
SELECT * FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLES(...));

-- ❌ WRONG: Will fail with "Invalid identifier"
SELECT * FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLES(...));
```

### Syntax

```sql
SELECT * FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLES(
  [ NAME => '<string>' ]
  [ , REFRESH_DATA_TIMESTAMP_START => <constant_expr> ]
  [ , RESULT_LIMIT => <integer> ]
  [ , INCLUDE_CONNECTED => { TRUE | FALSE } ]
));
```

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `NAME` | - | Optional. Name of a dynamic table (case-insensitive). Can be unqualified (`dt_name`), partially qualified (`schema.dt_name`), or fully qualified (`db.schema.dt_name`) |
| `REFRESH_DATA_TIMESTAMP_START` | 7 days ago | Optional. TIMESTAMP_LTZ for computing lag metrics. Includes refreshes with `LATEST_DATA_TIMESTAMP >= REFRESH_DATA_TIMESTAMP_START` |
| `RESULT_LIMIT` | 100 | Optional. Max rows returned (range: 1-10000). Results are sorted by last completed refresh state: FAILED → UPSTREAM_FAILED → SKIPPED → SUCCEEDED → CANCELED |
| `INCLUDE_CONNECTED` | FALSE | Optional. When TRUE, returns metadata for all DTs connected to the DT specified by NAME. Requires NAME, cannot use with RESULT_LIMIT |

**⚠️ RESULT_LIMIT GUIDANCE**: 
- **Always use `RESULT_LIMIT => 10000`** unless:
  1. You're querying a specific DT by fully qualified `NAME` (e.g., `NAME => 'DB.SCHEMA.MY_DT'`)
  2. You're just checking if any DTs exist (not counting total)
- The default is 100, so queries without `RESULT_LIMIT` will silently truncate results
- If you see exactly 100 rows, you're hitting the default limit — add `RESULT_LIMIT => 10000`
- If you see exactly 10,000 rows, you're hitting the max limit — inform the user there are more than 10k dynamic tables and use `SHOW DYNAMIC TABLES IN DATABASE <db>` or `SHOW DYNAMIC TABLES IN SCHEMA <db.schema>` to count by database/schema

**⚠️ SORTING/FILTERING**: To sort by a different order or apply filters across all DTs, you must specify a large `RESULT_LIMIT` value first. The default sorting/limit is applied before any ORDER BY or WHERE clauses.

### Key Columns

| Column | Type | Description |
|--------|------|-------------|
| `name` | STRING | Dynamic table name |
| `database_name` | STRING | Database containing DT |
| `schema_name` | STRING | Schema containing DT |
| `qualified_name` | STRING | Fully qualified name |
| `target_lag_sec` | NUMBER | Target lag in seconds |
| `target_lag_type` | STRING | USER_DEFINED or DOWNSTREAM |
| `mean_lag_sec` | NUMBER | Average observed lag |
| `maximum_lag_sec` | NUMBER | Longest observed lag |
| `time_within_target_lag_ratio` | FLOAT | % of time meeting lag (0-1) |
| `latest_data_timestamp` | TIMESTAMP | Data freshness timestamp |
| `scheduling_state` | STRING | ACTIVE or SUSPENDED |
| `last_completed_refresh_state` | STRING | SUCCESS, FAILED, etc. |
| `last_completed_refresh_state_code` | STRING | Error code if failed |
| `last_completed_refresh_state_message` | STRING | Error message if failed |

### Example Queries

```sql
USE DATABASE ANY_DB;  -- Any database works, just need context to execute

-- Count all DTs in account (ALWAYS use RESULT_LIMIT for counting)
SELECT COUNT(*) as total_dynamic_tables
FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLES(RESULT_LIMIT => 10000));

-- List all DTs in account with status
SELECT name, database_name, schema_name, scheduling_state, 
       last_completed_refresh_state, time_within_target_lag_ratio
FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLES(RESULT_LIMIT => 10000))
ORDER BY database_name, schema_name, name;

-- Specific DT with full details
SELECT *
FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLES(
  NAME => 'MY_DB.MY_SCHEMA.MY_DT'
));

-- Get all DTs connected to a specific DT (pipeline/DAG view)
SELECT name, target_lag_sec, mean_lag_sec, latest_data_timestamp
FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLES(
  NAME => 'MY_DB.MY_SCHEMA.MY_DT',
  INCLUDE_CONNECTED => TRUE
))
ORDER BY target_lag_sec;

-- DTs with issues (account-wide) - must use high RESULT_LIMIT to filter all
SELECT name, database_name, schema_name, scheduling_state, 
       last_completed_refresh_state, last_completed_refresh_state_message
FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLES(RESULT_LIMIT => 10000))
WHERE last_completed_refresh_state != 'SUCCEEDED'
   OR time_within_target_lag_ratio < 0.9;

-- Compute lag metrics for a specific time window
SELECT name, mean_lag_sec, maximum_lag_sec, time_within_target_lag_ratio
FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLES(
  REFRESH_DATA_TIMESTAMP_START => DATEADD('day', -1, CURRENT_TIMESTAMP()),
  RESULT_LIMIT => 10000
));
```

---

## INFORMATION_SCHEMA.DYNAMIC_TABLE_REFRESH_HISTORY()

Returns refresh history for dynamic tables.

### Syntax

```sql
SELECT * FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLE_REFRESH_HISTORY(
  [ NAME => '<dt_name>' ]
  [ , NAME_PREFIX => '<database>.<schema>' ]
  [ , ERROR_ONLY => TRUE | FALSE ]
  [ , DATA_TIMESTAMP_START => <timestamp> ]
  [ , DATA_TIMESTAMP_END => <timestamp> ]
  [ , RESULT_LIMIT => <integer> ]
));
```

### Key Columns

| Column | Type | Description |
|--------|------|-------------|
| `name` | STRING | Dynamic table name |
| `state` | STRING | SUCCESS, FAILED, SKIPPED, CANCELLED, UPSTREAM_FAILED |
| `state_code` | STRING | Error code if failed |
| `state_message` | STRING | Error message if failed |
| `refresh_start_time` | TIMESTAMP | When refresh started |
| `refresh_end_time` | TIMESTAMP | When refresh completed |
| `data_timestamp` | TIMESTAMP | Data freshness after refresh |
| `refresh_action` | STRING | INCREMENTAL or FULL |
| `refresh_trigger` | STRING | SCHEDULED, MANUAL, INITIAL |
| `query_id` | STRING | Query ID for performance analysis |

### State Values

| State | Meaning |
|-------|---------|
| `SUCCESS` | Refresh completed successfully |
| `FAILED` | Refresh failed with error |
| `SKIPPED` | No changes to process |
| `CANCELLED` | Refresh was cancelled |
| `UPSTREAM_FAILED` | Upstream DT failed |

### Example Queries

```sql
USE DATABASE MY_DB;

-- Recent refresh history
SELECT name, refresh_start_time, refresh_end_time,
       DATEDIFF('second', refresh_start_time, refresh_end_time) as duration_sec,
       state, refresh_action, query_id
FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLE_REFRESH_HISTORY(
  NAME_PREFIX => 'MY_DB.MY_SCHEMA'
))
ORDER BY refresh_start_time DESC
LIMIT 20;

-- Errors only
SELECT name, refresh_start_time, state, state_code, state_message
FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLE_REFRESH_HISTORY(
  ERROR_ONLY => TRUE
))
ORDER BY refresh_start_time DESC;

-- Refresh statistics (last 7 days)
SELECT 
  name,
  COUNT(*) as total_refreshes,
  AVG(DATEDIFF('second', refresh_start_time, refresh_end_time)) as avg_duration_sec,
  MAX(DATEDIFF('second', refresh_start_time, refresh_end_time)) as max_duration_sec,
  COUNT_IF(refresh_action = 'INCREMENTAL') as incremental_count,
  COUNT_IF(refresh_action = 'FULL') as full_count,
  COUNT_IF(state = 'FAILED') as failed_count
FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLE_REFRESH_HISTORY(NAME => 'MY_DT'))
WHERE refresh_start_time > DATEADD('day', -7, CURRENT_TIMESTAMP())
GROUP BY name;
```

---

## INFORMATION_SCHEMA.DYNAMIC_TABLE_GRAPH_HISTORY()

Returns dependency graph information for dynamic tables (DAG structure).

### Syntax

```sql
SELECT * FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLE_GRAPH_HISTORY(
  [ NAME => '<dt_name>' ]
));
```

### Key Columns

| Column | Type | Description |
|--------|------|-------------|
| `name` | STRING | Dynamic table name |
| `inputs` | ARRAY | Array of upstream table names |
| `scheduling_state` | STRING | ACTIVE or SUSPENDED |
| `target_lag_type` | STRING | USER_DEFINED or DOWNSTREAM |
| `target_lag_sec` | NUMBER | Target lag in seconds |

### Example Queries

```sql
USE DATABASE MY_DB;

-- View all dependencies
SELECT name, inputs, scheduling_state, target_lag_type
FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLE_GRAPH_HISTORY());

-- Find upstream tables for a specific DT
SELECT name, inputs
FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLE_GRAPH_HISTORY())
WHERE name = 'MY_DT';

-- Find downstream tables that depend on a specific table
SELECT name, inputs
FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLE_GRAPH_HISTORY())
WHERE ARRAY_CONTAINS('MY_UPSTREAM_TABLE'::VARIANT, inputs);
```

---

## GET_DDL Function

Retrieve the DDL definition of a dynamic table.

### Syntax

```sql
SELECT GET_DDL('DYNAMIC_TABLE', '<fully_qualified_name>');
```

### Example

```sql
SELECT GET_DDL('DYNAMIC_TABLE', 'MY_DB.MY_SCHEMA.MY_DT');
```

---

## SHOW DYNAMIC TABLES

Use SHOW to get `refresh_mode` and `refresh_mode_reason` (not available in INFORMATION_SCHEMA).

### Syntax

```sql
SHOW DYNAMIC TABLES [ LIKE '<pattern>' ] [ IN SCHEMA <database>.<schema> ];
SELECT * FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()));
```

### Key Columns (unique to SHOW)

| Column | Type | Description |
|--------|------|-------------|
| `refresh_mode` | STRING | FULL or INCREMENTAL |
| `refresh_mode_reason` | STRING | Why this mode was chosen |

### Example

```sql
-- Check why a DT uses FULL refresh
SHOW DYNAMIC TABLES LIKE 'MY_DT' IN SCHEMA MY_DB.MY_SCHEMA;
SELECT "name", "refresh_mode", "refresh_mode_reason"
FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()));
```

---

## Common Diagnostic Workflows

### Check Why a DT Uses FULL Refresh

```sql
-- Use SHOW to get refresh_mode and refresh_mode_reason
SHOW DYNAMIC TABLES LIKE 'MY_DT' IN SCHEMA MY_DB.MY_SCHEMA;
SELECT "name", "refresh_mode", "refresh_mode_reason"
FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()));

-- Get the DDL to analyze the query
SELECT GET_DDL('DYNAMIC_TABLE', 'MY_DB.MY_SCHEMA.MY_DT');
```

### Health Check

```sql
-- 1. Check overall status (use SHOW for refresh_mode)
SHOW DYNAMIC TABLES LIKE 'MY_DT' IN SCHEMA MY_DB.MY_SCHEMA;
SELECT "name", "refresh_mode", "refresh_mode_reason", "scheduling_state", "data_timestamp"
FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()));

-- 2. Check recent refreshes (use INFORMATION_SCHEMA)
USE DATABASE MY_DB;
SELECT refresh_start_time, state, refresh_action, 
       DATEDIFF('second', refresh_start_time, refresh_end_time) as duration_sec
FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLE_REFRESH_HISTORY(NAME => 'MY_DT'))
ORDER BY refresh_start_time DESC
LIMIT 5;

-- 3. Check lag statistics
SELECT name, time_within_target_lag_ratio, mean_lag_sec, maximum_lag_sec
FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLES(NAME => 'MY_DB.MY_SCHEMA.MY_DT'));
```

### Troubleshooting Failed Refresh

```sql
-- 1. Get error details from refresh history (use ERROR_ONLY for efficiency)
USE DATABASE MY_DB;
SELECT name, state, state_code, state_message, query_id, refresh_start_time
FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLE_REFRESH_HISTORY(
  NAME => 'MY_DT',
  ERROR_ONLY => TRUE
))
ORDER BY refresh_start_time DESC
LIMIT 5;

-- 2. Check upstream status using graph
SELECT name, inputs, scheduling_state
FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLE_GRAPH_HISTORY())
WHERE name = 'MY_DT';
```

### Performance Analysis

```sql
-- 1. Get refresh statistics (last 7 days)
USE DATABASE MY_DB;
SELECT 
  AVG(DATEDIFF('second', refresh_start_time, refresh_end_time)) as avg_sec,
  MAX(DATEDIFF('second', refresh_start_time, refresh_end_time)) as max_sec,
  COUNT_IF(refresh_action = 'INCREMENTAL') as incr,
  COUNT_IF(refresh_action = 'FULL') as full
FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLE_REFRESH_HISTORY(
  NAME => 'MY_DT',
  DATA_TIMESTAMP_START => DATEADD('day', -7, CURRENT_TIMESTAMP())
))
WHERE refresh_action != 'NO_DATA';

-- 2. Get recent query_id for detailed analysis
SELECT query_id 
FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLE_REFRESH_HISTORY(
  NAME => 'MY_DT',
  DATA_TIMESTAMP_START => DATEADD('day', -1, CURRENT_TIMESTAMP())
))
WHERE state = 'SUCCESS' AND refresh_action != 'NO_DATA'
ORDER BY refresh_start_time DESC 
LIMIT 1;

-- 3. Analyze query operators (use query_id from above)
SELECT operator_type, execution_time_ms, output_rows
FROM TABLE(GET_QUERY_OPERATOR_STATS('<query_id>'))
ORDER BY execution_time_ms DESC 
LIMIT 10;
```
