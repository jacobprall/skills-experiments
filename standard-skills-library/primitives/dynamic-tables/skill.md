---
type: primitive
name: dynamic-tables
domain: data-transformation
snowflake_docs: "https://docs.snowflake.com/en/user-guide/dynamic-tables-about"
---

# Dynamic Tables

Incrementally maintained tables defined by a SQL query, automatically refreshed by Snowflake.

## Syntax

```sql
CREATE [ OR REPLACE ] DYNAMIC TABLE <name>
  TARGET_LAG = { '<num> { seconds | minutes | hours | days }' | DOWNSTREAM }
  WAREHOUSE = <warehouse_name>
  [ REFRESH_MODE = { AUTO | FULL | INCREMENTAL } ]
  [ INITIALIZE = { ON_CREATE | ON_SCHEDULE } ]
  AS <select_statement>;
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `name` | identifier | Yes | — | Fully qualified: `<db>.<schema>.<name>` |
| `TARGET_LAG` | string or keyword | Yes | — | Max staleness. Time value for leaf tables, `DOWNSTREAM` for intermediate tables in a pipeline |
| `WAREHOUSE` | identifier | Yes | — | Warehouse used for refresh operations |
| `REFRESH_MODE` | keyword | No | `AUTO` | `INCREMENTAL` for simple queries with small change sets; `FULL` for complex queries or non-deterministic functions; `AUTO` lets Snowflake decide |
| `INITIALIZE` | keyword | No | `ON_CREATE` | `ON_CREATE` populates immediately; `ON_SCHEDULE` defers until first scheduled refresh |

## Parameters

### TARGET_LAG

Controls how fresh the data must be. Two modes:

- **Time-based** (`'5 minutes'`, `'1 hour'`): The table will be refreshed so data is never older than this value. Use on leaf/final tables that users query directly.
- **DOWNSTREAM**: Refresh only when a downstream dynamic table needs fresh data. Use on intermediate tables in a pipeline to avoid unnecessary refreshes.

### REFRESH_MODE

| Mode | When to Use | Trade-off |
|------|-------------|-----------|
| `AUTO` | Default / development | Snowflake picks optimal mode; may change between refreshes |
| `INCREMENTAL` | Simple queries, small change volume (<5% per refresh) | Faster, cheaper refreshes; fails if query uses unsupported operators |
| `FULL` | Complex joins, non-deterministic functions, window functions | Always works; rebuilds entire table each refresh |

Operators that **support** incremental: `SELECT`, `WHERE`, `JOIN` (inner/left/right/cross), `UNION ALL`, `GROUP BY`, `HAVING`, aggregates (`SUM`, `COUNT`, `AVG`, `MIN`, `MAX`).

Operators that **require** full refresh: `UNION` (dedup), `INTERSECT`, `EXCEPT`/`MINUS`, window functions, non-deterministic functions (`CURRENT_TIMESTAMP`, `RANDOM`), `LATERAL FLATTEN`.

### INITIALIZE

- `ON_CREATE`: The dynamic table is populated immediately upon creation. The CREATE statement blocks until the initial data is loaded.
- `ON_SCHEDULE`: The table is created empty and populated on the first scheduled refresh cycle. Useful when creating many tables in a pipeline and you don't want them all populating simultaneously.

## Constraints

- Base tables must have `CHANGE_TRACKING = TRUE` for incremental refresh to work. Enable with `ALTER TABLE <name> SET CHANGE_TRACKING = TRUE`.
- A dynamic table's query cannot reference another dynamic table that hasn't been created yet (forward references are not allowed in pipelines — build bottom-up).
- `TARGET_LAG` minimum is 1 minute for time-based values.
- The warehouse must be running or set to auto-resume for refreshes to execute.
- Dynamic tables do not support clustering keys directly — apply clustering to base tables instead.
- `SELECT *` is supported but fragile — schema changes on base tables will cause refresh failures. Explicitly listing columns avoids this.

## Examples

### Basic: Single table refresh

```sql
CREATE OR REPLACE DYNAMIC TABLE analytics.public.daily_orders
  TARGET_LAG = '1 hour'
  WAREHOUSE = transform_wh
  REFRESH_MODE = INCREMENTAL
  AS
    SELECT
      order_id,
      customer_id,
      order_date,
      total_amount,
      status
    FROM raw.public.orders
    WHERE order_date >= DATEADD(day, -90, CURRENT_DATE());
```

### Pipeline: Chained dynamic tables

```sql
-- Intermediate table: refreshes only when downstream needs it
CREATE OR REPLACE DYNAMIC TABLE analytics.staging.enriched_orders
  TARGET_LAG = DOWNSTREAM
  WAREHOUSE = transform_wh
  REFRESH_MODE = INCREMENTAL
  AS
    SELECT
      o.order_id,
      o.customer_id,
      c.customer_name,
      c.segment,
      o.order_date,
      o.total_amount
    FROM raw.public.orders o
    JOIN raw.public.customers c ON o.customer_id = c.customer_id;

-- Leaf table: drives refresh of the entire pipeline
CREATE OR REPLACE DYNAMIC TABLE analytics.public.segment_summary
  TARGET_LAG = '30 minutes'
  WAREHOUSE = transform_wh
  REFRESH_MODE = INCREMENTAL
  AS
    SELECT
      segment,
      COUNT(*) AS order_count,
      SUM(total_amount) AS total_revenue,
      AVG(total_amount) AS avg_order_value
    FROM analytics.staging.enriched_orders
    GROUP BY segment;
```

### Monitoring refresh health

```sql
-- Check current state
SELECT name, refresh_mode, target_lag, scheduling_state
FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLES());

-- Check recent refresh history
SELECT name, state, state_message, refresh_trigger,
       refresh_start_time, refresh_end_time
FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLE_REFRESH_HISTORY())
ORDER BY refresh_start_time DESC
LIMIT 10;
```

## Anti-patterns

| Pattern | Why It Fails | Instead |
|---------|-------------|---------|
| Time-based lag on intermediate tables | Causes unnecessary refreshes when no downstream consumer needs fresh data | Use `TARGET_LAG = DOWNSTREAM` on intermediate tables |
| `SELECT *` in the query | Schema changes on base tables break the refresh | List columns explicitly |
| Very short lag on large tables (`'1 minute'`) | Continuous refresh consumes warehouse credits with diminishing freshness gains | Set lag to the actual business requirement |
| One massive dynamic table with complex joins | Full refresh every cycle, slow and expensive | Chain smaller dynamic tables; each does one transformation |
| Forgetting change tracking | Incremental refresh silently falls back to full | Run `ALTER TABLE ... SET CHANGE_TRACKING = TRUE` on all base tables |

## References

- [Snowflake Docs: Dynamic Tables](https://docs.snowflake.com/en/user-guide/dynamic-tables-about)
- [Snowflake Docs: DYNAMIC_TABLE_REFRESH_HISTORY](https://docs.snowflake.com/en/sql-reference/functions/dynamic_table_refresh_history)
