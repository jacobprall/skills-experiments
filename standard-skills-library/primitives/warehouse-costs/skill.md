---
type: primitive
name: warehouse-costs
domain: cost-ops
snowflake_docs: "https://docs.snowflake.com/en/sql-reference/account-usage/warehouse_metering_history"
---

# Warehouse Costs

Analyze virtual warehouse credit consumption, service-level cost breakdowns, user/query-level attribution, and period-over-period trends. All queries use SNOWFLAKE.ACCOUNT_USAGE views (requires IMPORTED PRIVILEGES on the SNOWFLAKE database).

## Key Views

| View | What It Contains | Latency |
|------|-----------------|---------|
| `METERING_HISTORY` | Credits by service type (warehouse, serverless, cloud services) | ~2 hours |
| `WAREHOUSE_METERING_HISTORY` | Per-warehouse credit usage by hour | ~2 hours |
| `QUERY_ATTRIBUTION_HISTORY` | Per-query credit attribution (compute + QAS) | ~2 hours |
| `WAREHOUSE_EVENTS_HISTORY` | Warehouse state changes (resize, suspend, resume) | ~2 hours |
| `QUERY_ACCELERATION_HISTORY` | QAS-specific credit usage per warehouse | ~2 hours |
| `ANOMALIES_DAILY` | Snowflake-detected cost anomalies | ~24 hours |
| `BUDGET_DETAILS` | Budget limits vs. current spending | ~24 hours |

## Service-Level Overview

### Cost breakdown by service type

```sql
SELECT
    service_type,
    ROUND(SUM(credits_used), 2) AS total_credits,
    ROUND(SUM(credits_used) / SUM(SUM(credits_used)) OVER () * 100, 1) AS pct_of_total
FROM SNOWFLAKE.ACCOUNT_USAGE.METERING_HISTORY
WHERE start_time >= DATEADD(DAY, -7, CURRENT_DATE())
    AND start_time < CURRENT_DATE()
GROUP BY service_type
ORDER BY total_credits DESC;
```

### Top resources across all categories

Combines warehouses, Cortex functions, and compute pools into one ranked view.

```sql
WITH warehouse_costs AS (
    SELECT 'WAREHOUSE' AS resource_type, warehouse_name AS resource_name,
        ROUND(SUM(credits_used), 2) AS total_credits
    FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
    WHERE start_time >= DATEADD('month', -1, CURRENT_DATE())
    GROUP BY warehouse_name
),
cortex_costs AS (
    SELECT 'CORTEX_FUNCTION' AS resource_type,
        CONCAT(function_name, ' (', COALESCE(model_name, 'default'), ')') AS resource_name,
        ROUND(SUM(token_credits), 4) AS total_credits
    FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_FUNCTIONS_USAGE_HISTORY
    WHERE start_time >= DATEADD('month', -1, CURRENT_DATE())
    GROUP BY function_name, model_name
),
pool_costs AS (
    SELECT 'COMPUTE_POOL' AS resource_type, compute_pool_name AS resource_name,
        ROUND(SUM(credits_used), 2) AS total_credits
    FROM SNOWFLAKE.ACCOUNT_USAGE.SNOWPARK_CONTAINER_SERVICES_HISTORY
    WHERE start_time >= DATEADD('month', -1, CURRENT_DATE())
    GROUP BY compute_pool_name
),
all_resources AS (
    SELECT * FROM warehouse_costs
    UNION ALL SELECT * FROM cortex_costs
    UNION ALL SELECT * FROM pool_costs
)
SELECT resource_type, resource_name, total_credits
FROM all_resources
ORDER BY total_credits DESC
LIMIT 10;
```

## Warehouse Analysis

### Top warehouses by credit usage

```sql
SELECT
    warehouse_name,
    ROUND(SUM(credits_used), 2) AS credits
FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
WHERE start_time >= DATEADD(DAY, -7, CURRENT_DATE())
    AND start_time < CURRENT_DATE()
GROUP BY warehouse_name
ORDER BY credits DESC
LIMIT 15;
```

### Warehouse period comparison (14-day sliding window)

```sql
WITH recent AS (
    SELECT warehouse_name, SUM(credits_used) AS credits
    FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
    WHERE start_time >= DATEADD(DAY, -14, CURRENT_DATE())
    GROUP BY warehouse_name
),
prior AS (
    SELECT warehouse_name, SUM(credits_used) AS credits
    FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
    WHERE start_time >= DATEADD(DAY, -28, CURRENT_DATE())
        AND start_time < DATEADD(DAY, -14, CURRENT_DATE())
    GROUP BY warehouse_name
)
SELECT
    COALESCE(r.warehouse_name, p.warehouse_name) AS warehouse_name,
    ROUND(COALESCE(p.credits, 0), 2) AS prior_14d,
    ROUND(COALESCE(r.credits, 0), 2) AS recent_14d,
    ROUND(COALESCE(r.credits, 0) - COALESCE(p.credits, 0), 2) AS change,
    ROUND(((COALESCE(r.credits, 0) - COALESCE(p.credits, 0)) / NULLIF(p.credits, 0)) * 100, 1) AS pct_change
FROM recent r
FULL OUTER JOIN prior p ON r.warehouse_name = p.warehouse_name
ORDER BY ABS(COALESCE(r.credits, 0) - COALESCE(p.credits, 0)) DESC
LIMIT 15;
```

### Month-over-month warehouse change

```sql
WITH monthly AS (
    SELECT warehouse_name, DATE_TRUNC('month', start_time) AS month,
        SUM(credits_used) AS credits
    FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
    WHERE start_time >= DATE_TRUNC('month', DATEADD('month', -1, CURRENT_DATE()))
    GROUP BY warehouse_name, DATE_TRUNC('month', start_time)
),
comparison AS (
    SELECT warehouse_name,
        SUM(CASE WHEN month = DATE_TRUNC('month', CURRENT_DATE()) THEN credits ELSE 0 END) AS current_month,
        SUM(CASE WHEN month = DATE_TRUNC('month', DATEADD('month', -1, CURRENT_DATE())) THEN credits ELSE 0 END) AS prior_month
    FROM monthly
    GROUP BY warehouse_name
)
SELECT warehouse_name,
    ROUND(current_month, 2) AS current_month,
    ROUND(prior_month, 2) AS prior_month,
    ROUND(current_month - prior_month, 2) AS change,
    CASE WHEN prior_month > 0
        THEN ROUND(((current_month - prior_month) / prior_month) * 100, 1)
        ELSE NULL END AS pct_change,
    CASE
        WHEN current_month > prior_month THEN 'INCREASED'
        WHEN current_month < prior_month THEN 'DECREASED'
        WHEN current_month = prior_month THEN 'UNCHANGED'
        ELSE 'NEW'
    END AS trend
FROM comparison
WHERE current_month > 0 OR prior_month > 0
ORDER BY ABS(current_month - prior_month) DESC;
```

### Warehouse resize events (last 7 days)

```sql
WITH states AS (
    SELECT warehouse_name, timestamp, size,
        LAG(size) OVER (PARTITION BY warehouse_name ORDER BY timestamp) AS prev_size
    FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_EVENTS_HISTORY
    WHERE event_name = 'WAREHOUSE_CONSISTENT'
        AND timestamp >= CURRENT_DATE - 7
)
SELECT warehouse_name, timestamp, prev_size, size AS new_size
FROM states
WHERE prev_size IS NOT NULL AND prev_size != size
ORDER BY timestamp DESC;
```

## Period Trend Queries

### Week-over-week total credits

```sql
SELECT 'current_week' AS period,
    ROUND(IFNULL(SUM(credits_used), 0), 2) AS credits
FROM SNOWFLAKE.ACCOUNT_USAGE.METERING_HISTORY
WHERE start_time >= DATEADD(DAY, -7, CURRENT_DATE()) AND start_time < CURRENT_DATE()
UNION ALL
SELECT 'previous_week',
    ROUND(IFNULL(SUM(credits_used), 0), 2)
FROM SNOWFLAKE.ACCOUNT_USAGE.METERING_HISTORY
WHERE start_time >= DATEADD(DAY, -14, CURRENT_DATE()) AND start_time < DATEADD(DAY, -7, CURRENT_DATE());
```

### Month-over-month total credits

```sql
SELECT 'current_month' AS period,
    ROUND(IFNULL(SUM(credits_used), 0), 2) AS credits
FROM SNOWFLAKE.ACCOUNT_USAGE.METERING_HISTORY
WHERE start_time >= DATE_TRUNC('MONTH', CURRENT_DATE())
    AND start_time < DATE_TRUNC('MONTH', DATEADD(MONTH, 1, CURRENT_DATE()))
UNION ALL
SELECT 'previous_month',
    ROUND(IFNULL(SUM(credits_used), 0), 2)
FROM SNOWFLAKE.ACCOUNT_USAGE.METERING_HISTORY
WHERE start_time >= DATE_TRUNC('MONTH', DATEADD(MONTH, -1, CURRENT_DATE()))
    AND start_time < DATE_TRUNC('MONTH', CURRENT_DATE());
```

### Cost increase root cause (which services grew?)

```sql
WITH monthly AS (
    SELECT DATE_TRUNC('month', start_time) AS month, service_type,
        SUM(credits_used) AS credits
    FROM SNOWFLAKE.ACCOUNT_USAGE.METERING_HISTORY
    WHERE start_time >= DATE_TRUNC('month', DATEADD('month', -2, CURRENT_DATE()))
    GROUP BY DATE_TRUNC('month', start_time), service_type
),
comparison AS (
    SELECT service_type,
        SUM(CASE WHEN month = DATE_TRUNC('month', CURRENT_DATE()) THEN credits ELSE 0 END) AS current_month,
        SUM(CASE WHEN month = DATE_TRUNC('month', DATEADD('month', -1, CURRENT_DATE())) THEN credits ELSE 0 END) AS prior_month
    FROM monthly
    GROUP BY service_type
)
SELECT service_type,
    ROUND(current_month, 2) AS current_month,
    ROUND(prior_month, 2) AS prior_month,
    ROUND(current_month - prior_month, 2) AS increase,
    CASE WHEN prior_month > 0
        THEN ROUND(((current_month - prior_month) / prior_month) * 100, 1)
        ELSE NULL END AS pct_increase
FROM comparison
WHERE current_month > prior_month
ORDER BY (current_month - prior_month) DESC;
```

## User & Query Attribution

### Top users by credit spend

```sql
SELECT
    user_name,
    COUNT(DISTINCT query_id) AS query_count,
    ROUND(SUM(credits_attributed_compute + COALESCE(credits_used_query_acceleration, 0)), 2) AS total_credits
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_ATTRIBUTION_HISTORY
WHERE start_time >= DATEADD(DAY, -7, CURRENT_DATE())
    AND start_time < CURRENT_DATE()
GROUP BY user_name
ORDER BY total_credits DESC
LIMIT 20;
```

### Most expensive individual queries

```sql
SELECT
    query_id, warehouse_name, user_name,
    ROUND(credits_attributed_compute, 2) AS credits_compute,
    ROUND(credits_used_query_acceleration, 2) AS credits_qas,
    start_time
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_ATTRIBUTION_HISTORY
WHERE start_time >= CURRENT_DATE - 7
    AND credits_attributed_compute > 0
ORDER BY credits_attributed_compute DESC
LIMIT 15;
```

### Top query patterns by parameterized hash

Groups structurally similar queries to find expensive patterns regardless of parameter values.

```sql
SELECT
    query_parameterized_hash,
    ROUND(SUM(credits_attributed_compute), 2) AS total_credits,
    COUNT(query_id) AS execution_count,
    ROUND(SUM(credits_attributed_compute) / NULLIF(COUNT(query_id), 0), 4) AS avg_credits_per_run,
    ANY_VALUE(query_id) AS example_query_id
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_ATTRIBUTION_HISTORY
WHERE start_time >= DATEADD(DAY, -7, CURRENT_DATE())
    AND query_parameterized_hash IS NOT NULL
GROUP BY query_parameterized_hash
ORDER BY total_credits DESC
LIMIT 10;
```

To see the actual SQL text for an example query, use the example_query_id with QUERY_HISTORY:
```sql
SELECT query_text FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY WHERE query_id = '<example_query_id>';
```

### Users with greatest spend increase (month-over-month)

```sql
WITH monthly AS (
    SELECT user_name, DATE_TRUNC('month', start_time) AS month,
        SUM(credits_attributed_compute) AS credits
    FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_ATTRIBUTION_HISTORY
    WHERE start_time >= DATE_TRUNC('month', DATEADD('month', -2, CURRENT_DATE()))
    GROUP BY user_name, DATE_TRUNC('month', start_time)
),
comparison AS (
    SELECT user_name,
        SUM(CASE WHEN month = DATE_TRUNC('month', CURRENT_DATE()) THEN credits ELSE 0 END) AS current_month,
        SUM(CASE WHEN month = DATE_TRUNC('month', DATEADD('month', -1, CURRENT_DATE())) THEN credits ELSE 0 END) AS prior_month
    FROM monthly
    GROUP BY user_name
)
SELECT user_name,
    ROUND(current_month, 2) AS current_month,
    ROUND(prior_month, 2) AS prior_month,
    ROUND(current_month - prior_month, 2) AS increase,
    CASE WHEN prior_month > 0
        THEN ROUND(((current_month - prior_month) / prior_month) * 100, 1)
        ELSE NULL END AS pct_increase
FROM comparison
WHERE current_month > prior_month
ORDER BY (current_month - prior_month) DESC
LIMIT 10;
```

### Comprehensive user bill (warehouse + Cortex Analyst)

```sql
WITH user_compute AS (
    SELECT user_name,
        ROUND(SUM(credits_attributed_compute), 4) AS compute_credits,
        ROUND(SUM(COALESCE(credits_used_query_acceleration, 0)), 4) AS qas_credits,
        COUNT(DISTINCT query_id) AS queries
    FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_ATTRIBUTION_HISTORY
    WHERE start_time >= DATEADD('month', -1, CURRENT_DATE())
    GROUP BY user_name
),
user_cortex AS (
    SELECT username AS user_name,
        ROUND(SUM(credits), 4) AS cortex_credits,
        SUM(request_count) AS requests
    FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_ANALYST_USAGE_HISTORY
    WHERE start_time >= DATEADD('month', -1, CURRENT_DATE())
    GROUP BY username
)
SELECT
    COALESCE(c.user_name, x.user_name) AS user_name,
    ROUND(COALESCE(c.compute_credits, 0) + COALESCE(c.qas_credits, 0) + COALESCE(x.cortex_credits, 0), 2) AS total_bill,
    COALESCE(c.compute_credits, 0) AS compute,
    COALESCE(x.cortex_credits, 0) AS cortex,
    COALESCE(c.queries, 0) AS query_count
FROM user_compute c
FULL OUTER JOIN user_cortex x ON c.user_name = x.user_name
ORDER BY total_bill DESC
LIMIT 10;
```

## Anomaly Detection

### Recent anomaly days

Always filter on `IS_ANOMALY = TRUE`. Actual > forecasted alone does not mean anomaly.

```sql
SELECT
    date,
    COUNT(*) AS anomaly_count,
    ROUND(SUM(actual_value), 2) AS actual,
    ROUND(SUM(forecasted_value), 2) AS forecast,
    ROUND(SUM(actual_value - forecasted_value), 2) AS variance,
    ROUND((SUM(actual_value) - SUM(forecasted_value)) / NULLIF(SUM(forecasted_value), 0) * 100, 1) AS variance_pct
FROM SNOWFLAKE.ACCOUNT_USAGE.ANOMALIES_DAILY
WHERE is_anomaly = TRUE AND date >= CURRENT_DATE - 30
GROUP BY date
ORDER BY variance_pct DESC
LIMIT 10;
```

### Top contributors on anomaly days

```sql
WITH anomaly_dates AS (
    SELECT DISTINCT date AS anomaly_date
    FROM SNOWFLAKE.ACCOUNT_USAGE.ANOMALIES_DAILY
    WHERE is_anomaly = TRUE AND date >= DATEADD('month', -3, CURRENT_DATE())
)
SELECT
    DATE(m.start_time) AS anomaly_date,
    m.service_type, m.name AS resource_name,
    ROUND(SUM(m.credits_used), 2) AS credits
FROM SNOWFLAKE.ACCOUNT_USAGE.METERING_HISTORY m
JOIN anomaly_dates ad ON DATE(m.start_time) = ad.anomaly_date
GROUP BY DATE(m.start_time), m.service_type, m.name
QUALIFY ROW_NUMBER() OVER (PARTITION BY DATE(m.start_time) ORDER BY SUM(m.credits_used) DESC) <= 5
ORDER BY anomaly_date DESC, credits DESC;
```

## Budget Monitoring

### Budgets currently over limit

```sql
SELECT
    budget_name, database_name, schema_name,
    ROUND(current_month_spending, 2) AS current_spend,
    credit_limit,
    ROUND(current_month_spending - credit_limit, 2) AS over_by,
    ROUND((current_month_spending - credit_limit) / NULLIF(credit_limit, 0) * 100, 1) AS pct_over
FROM SNOWFLAKE.ACCOUNT_USAGE.BUDGET_DETAILS
WHERE current_month_spending > credit_limit
ORDER BY over_by DESC;
```

### Budgets projected to exceed limit

```sql
WITH r AS (
    SELECT DATEDIFF('second', DATE_TRUNC('month', CURRENT_TIMESTAMP()),
        CURRENT_TIMESTAMP())::FLOAT /
        NULLIF(DATEDIFF('second', DATE_TRUNC('month', CURRENT_TIMESTAMP()),
            DATEADD('month', 1, DATE_TRUNC('month', CURRENT_TIMESTAMP()))), 0) AS ratio
)
SELECT
    bd.budget_name, bd.credit_limit,
    ROUND(bd.current_month_spending, 2) AS current_spend,
    ROUND(bd.current_month_spending / r.ratio, 2) AS projected_month_end,
    ROUND((bd.current_month_spending / r.ratio) - bd.credit_limit, 2) AS projected_over_by
FROM SNOWFLAKE.ACCOUNT_USAGE.BUDGET_DETAILS bd CROSS JOIN r
WHERE r.ratio > 0 AND (bd.current_month_spending / r.ratio) > bd.credit_limit
ORDER BY projected_over_by DESC;
```

## Constraints

- ACCOUNT_USAGE views have ~2 hour latency. Recently started queries or warehouse activity may not appear yet.
- ANOMALIES_DAILY has ~24 hour latency and requires several weeks of history before anomaly detection is reliable.
- QUERY_ATTRIBUTION_HISTORY is available on Enterprise Edition and higher.
- Budget creation is done via Snowsight UI, not SQL. SQL can only read budget status.
- Resource monitors require ACCOUNTADMIN to create.

## Anti-patterns

| Pattern | Why It Fails | Instead |
|---------|-------------|---------|
| Querying WAREHOUSE_METERING_HISTORY for total account costs | Misses serverless, Cortex AI, cloud services | Use METERING_HISTORY for account-level totals |
| Assuming actual > forecast means anomaly | Snowflake's anomaly model uses confidence intervals, not simple comparison | Always filter on `IS_ANOMALY = TRUE` |
| Using QUERY_HISTORY for cost attribution | QUERY_HISTORY doesn't have credit columns | Use QUERY_ATTRIBUTION_HISTORY for per-query credits |
| Comparing incomplete months as if they're full months | Current month is partial — raw sums look lower than prior month | Use daily averages or pro-rate based on days elapsed |

## References

- `primitives/serverless-costs`
- `primitives/cortex-ai-costs`
- [METERING_HISTORY](https://docs.snowflake.com/en/sql-reference/account-usage/metering_history)
- [QUERY_ATTRIBUTION_HISTORY](https://docs.snowflake.com/en/sql-reference/account-usage/query_attribution_history)
