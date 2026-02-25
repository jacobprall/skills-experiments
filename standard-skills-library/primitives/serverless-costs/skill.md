---
type: primitive
name: serverless-costs
domain: cost-ops
snowflake_docs: "https://docs.snowflake.com/en/sql-reference/account-usage/serverless_task_history"
---

# Serverless Costs

Analyze costs from Snowflake serverless features: tasks, Snowpipe, auto-clustering, materialized views, search optimization, and replication. These consume credits without a user-managed warehouse.

## Key Views

| View | What It Contains | Latency |
|------|-----------------|---------|
| `SERVERLESS_TASK_HISTORY` | Per-task credit usage (serverless tasks only) | ~2 hours |
| `PIPE_USAGE_HISTORY` | Snowpipe credit usage by pipe | ~2 hours |
| `AUTO_REFRESH_REGISTRATION_HISTORY` | Auto-refresh credit usage for external tables | ~2 hours |
| `METERING_HISTORY` | Aggregated credits by service_type (includes all serverless types) | ~2 hours |

## Serverless Tasks

### Task credits — last 7 days

```sql
SELECT
    task_name, database_name, schema_name,
    ROUND(SUM(credits_used), 2) AS total_credits
FROM SNOWFLAKE.ACCOUNT_USAGE.SERVERLESS_TASK_HISTORY
WHERE start_time >= DATEADD('day', -7, CURRENT_DATE())
    AND start_time < CURRENT_DATE()
GROUP BY task_name, database_name, schema_name
ORDER BY total_credits DESC;
```

### Top databases by task cost

```sql
SELECT
    database_name,
    COUNT(DISTINCT task_name) AS task_count,
    ROUND(SUM(credits_used), 2) AS total_credits
FROM SNOWFLAKE.ACCOUNT_USAGE.SERVERLESS_TASK_HISTORY
WHERE start_time >= DATEADD('day', -30, CURRENT_DATE())
GROUP BY database_name
ORDER BY total_credits DESC
LIMIT 10;
```

### Recent task activity (last 12 hours)

Useful for spotting runaway tasks in near-real-time (subject to ACCOUNT_USAGE latency).

```sql
SELECT
    task_name, database_name, schema_name,
    start_time, end_time,
    ROUND(credits_used, 4) AS credits
FROM SNOWFLAKE.ACCOUNT_USAGE.SERVERLESS_TASK_HISTORY
WHERE start_time >= DATEADD('hour', -12, CURRENT_TIMESTAMP())
ORDER BY start_time DESC;
```

## All Serverless Features (via METERING_HISTORY)

For a combined view of all serverless costs, filter METERING_HISTORY by serverless service types.

### Serverless cost breakdown by service type

```sql
SELECT
    service_type,
    ROUND(SUM(credits_used), 2) AS total_credits,
    ROUND(SUM(credits_used) / SUM(SUM(credits_used)) OVER () * 100, 1) AS pct_of_total
FROM SNOWFLAKE.ACCOUNT_USAGE.METERING_HISTORY
WHERE start_time >= DATEADD('day', -30, CURRENT_DATE())
    AND service_type IN (
        'AUTO_CLUSTERING',
        'MATERIALIZED_VIEW',
        'SEARCH_OPTIMIZATION',
        'SERVERLESS_TASK',
        'SNOWPIPE',
        'SNOWPIPE_STREAMING',
        'REPLICATION',
        'QUERY_ACCELERATION'
    )
GROUP BY service_type
ORDER BY total_credits DESC;
```

### Serverless cost trend (daily, last 14 days)

```sql
SELECT
    DATE(start_time) AS day,
    service_type,
    ROUND(SUM(credits_used), 2) AS credits
FROM SNOWFLAKE.ACCOUNT_USAGE.METERING_HISTORY
WHERE start_time >= DATEADD('day', -14, CURRENT_DATE())
    AND service_type NOT IN ('WAREHOUSE_METERING')
GROUP BY DATE(start_time), service_type
ORDER BY day DESC, credits DESC;
```

## Constraints

- `SERVERLESS_TASK_HISTORY` only covers serverless (user-managed) tasks. Warehouse-based tasks appear in `TASK_HISTORY` and consume warehouse credits instead.
- Snowpipe credits appear in both `PIPE_USAGE_HISTORY` (per-pipe detail) and `METERING_HISTORY` (aggregated under `SNOWPIPE` service type).
- Serverless costs cannot be attributed to specific users — they run as system operations.

## Anti-patterns

| Pattern | Why It Fails | Instead |
|---------|-------------|---------|
| Looking at WAREHOUSE_METERING_HISTORY for task costs | Serverless tasks don't use warehouses | Use SERVERLESS_TASK_HISTORY or METERING_HISTORY with service_type filter |
| Summing all METERING_HISTORY rows to get "serverless costs" | METERING_HISTORY includes warehouse costs too | Filter by specific serverless service_type values |
| Ignoring auto-clustering costs | Auto-clustering runs silently and can accumulate significant credits | Always include AUTO_CLUSTERING in serverless cost reviews |

## References

- `primitives/warehouse-costs`
- `primitives/cortex-ai-costs`
- [SERVERLESS_TASK_HISTORY](https://docs.snowflake.com/en/sql-reference/account-usage/serverless_task_history)
- [METERING_HISTORY](https://docs.snowflake.com/en/sql-reference/account-usage/metering_history)
