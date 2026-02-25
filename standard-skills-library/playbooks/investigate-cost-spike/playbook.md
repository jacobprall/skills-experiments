---
type: playbook
name: investigate-cost-spike
domain: cost-ops
depends_on:
  - warehouse-costs
  - serverless-costs
  - cortex-ai-costs
---

# Investigate Cost Spike

Systematically investigate a Snowflake cost increase: identify what changed, where the money went, who drove it, and what to do about it.

## Objective

After completing this playbook, the user will have:

1. A clear picture of overall spending by service type
2. Identification of the top cost drivers (warehouses, serverless, Cortex AI)
3. Week-over-week or month-over-month trend analysis showing what changed
4. Anomaly detection results highlighting unusual spending patterns
5. User and query-level attribution for the largest cost increases
6. Actionable recommendations to reduce costs

## Prerequisites

- A role with access to SNOWFLAKE.ACCOUNT_USAGE views (ACCOUNTADMIN, or a role with IMPORTED PRIVILEGES on the SNOWFLAKE database)
- A warehouse set in session context

## Steps

### Step 1: Get the overall cost breakdown

Query METERING_HISTORY for a service-level breakdown to understand where money is going.

Reference: `primitives/warehouse-costs` (overview queries)

```sql
SELECT
    service_type,
    ROUND(SUM(credits_used), 2) AS total_credits,
    ROUND(SUM(credits_used) / SUM(SUM(credits_used)) OVER () * 100, 1) AS percentage_of_total
FROM SNOWFLAKE.ACCOUNT_USAGE.METERING_HISTORY
WHERE start_time >= DATEADD(DAY, -7, CURRENT_DATE())
    AND start_time < CURRENT_DATE()
GROUP BY service_type
ORDER BY total_credits DESC;
```

Present results in a format a non-technical user can understand. Translate service_type values into plain language (e.g., WAREHOUSE_METERING = "Virtual warehouse compute", AUTO_CLUSTERING = "Automatic data organization").

**Checkpoint:**
  severity: info
  present: "Service-level cost breakdown with percentages"

### Step 2: Compare to prior period (trend analysis)

Show how spending changed compared to the prior period to quantify the increase.

Reference: `primitives/warehouse-costs` (trend queries)

```sql
WITH recent AS (
    SELECT service_type, SUM(credits_used) AS credits
    FROM SNOWFLAKE.ACCOUNT_USAGE.METERING_HISTORY
    WHERE start_time >= DATEADD(DAY, -7, CURRENT_DATE())
    GROUP BY service_type
),
prior AS (
    SELECT service_type, SUM(credits_used) AS credits
    FROM SNOWFLAKE.ACCOUNT_USAGE.METERING_HISTORY
    WHERE start_time >= DATEADD(DAY, -14, CURRENT_DATE())
        AND start_time < DATEADD(DAY, -7, CURRENT_DATE())
    GROUP BY service_type
)
SELECT
    COALESCE(r.service_type, p.service_type) AS service_type,
    ROUND(COALESCE(p.credits, 0), 2) AS prior_period,
    ROUND(COALESCE(r.credits, 0), 2) AS current_period,
    ROUND(COALESCE(r.credits, 0) - COALESCE(p.credits, 0), 2) AS change,
    ROUND(((COALESCE(r.credits, 0) - COALESCE(p.credits, 0)) / NULLIF(p.credits, 0)) * 100, 1) AS pct_change
FROM recent r
FULL OUTER JOIN prior p ON r.service_type = p.service_type
ORDER BY ABS(COALESCE(r.credits, 0) - COALESCE(p.credits, 0)) DESC;
```

Highlight which service types increased the most. This tells the user *what category* drove the cost increase.

### Step 3: Drill into top cost drivers

Based on step 2 results, drill into the category with the largest increase.

**If warehouse costs dominate:** Query top warehouses by credit usage.

Reference: `primitives/warehouse-costs`

```sql
SELECT
    warehouse_name,
    ROUND(SUM(credits_used), 2) AS credits
FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
WHERE start_time >= DATEADD(DAY, -7, CURRENT_DATE())
    AND start_time < CURRENT_DATE()
GROUP BY warehouse_name
ORDER BY credits DESC
LIMIT 10;
```

**If serverless costs dominate:** Query top tasks.

Reference: `primitives/serverless-costs`

**If Cortex AI costs dominate:** Query top functions and models.

Reference: `primitives/cortex-ai-costs`

### Step 4: Check for anomalies

Query the ANOMALIES_DAILY view to see if Snowflake's built-in anomaly detection flagged any days.

```sql
SELECT
    date,
    COUNT(*) AS anomaly_count,
    ROUND(SUM(actual_value), 2) AS total_consumption,
    ROUND(SUM(forecasted_value), 2) AS total_forecast,
    ROUND(SUM(actual_value - forecasted_value), 2) AS variance_amount,
    ROUND((SUM(actual_value) - SUM(forecasted_value)) / NULLIF(SUM(forecasted_value), 0) * 100, 2) AS variance_percent
FROM SNOWFLAKE.ACCOUNT_USAGE.ANOMALIES_DAILY
WHERE is_anomaly = TRUE
    AND date >= CURRENT_DATE - 30
GROUP BY date
ORDER BY variance_percent DESC
LIMIT 10;
```

Always filter on `IS_ANOMALY = TRUE`. Do not assume actual > forecasted means anomaly.

### Step 5: Identify who and what is driving the cost

Query user-level and query-level attribution for the period in question.

Reference: `primitives/warehouse-costs` (user/query attribution section)

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
LIMIT 10;
```

For the top users, also check query patterns by parameterized hash to identify repeated expensive queries.

**Checkpoint:**
  severity: review
  present: "Complete investigation summary: service breakdown, trend, top drivers, anomalies, user attribution"

### Step 6: Provide actionable recommendations

Based on findings, provide specific, actionable recommendations. Common patterns:

| Finding | Recommendation |
|---------|---------------|
| Single warehouse dominates cost | Review warehouse size, consider auto-suspend, multi-cluster config |
| Warehouse running 24/7 with low utilization | Enable auto-suspend (e.g., AUTO_SUSPEND = 60 seconds) |
| One user running expensive queries | Review query patterns, suggest query optimization or result caching |
| Serverless tasks consuming unexpected credits | Review task schedules, check for runaway tasks |
| Cortex AI costs spiking | Check batch sizes, review model selection (smaller models for simple tasks) |
| Cost anomaly on specific date | Correlate with deployment events, new pipelines, or data volume changes |

Present recommendations ordered by estimated impact (largest savings first). Frame in business terms the user can act on.

## Anti-patterns

| Mistake | Impact | Instead |
|---------|--------|---------|
| Jumping straight to warehouse detail without overview | Misses serverless, Cortex AI, or storage as the real driver | Always start with service-level breakdown (step 1) |
| Showing raw SQL output without interpretation | Non-technical users can't interpret credit numbers | Translate to business language, include percentages and trends |
| Reporting anomalies without context | "There was an anomaly" is not actionable | Cross-reference anomaly dates with top contributors |
| Skipping user attribution | Costs can't be addressed without knowing who/what drives them | Always include user and query-level analysis |
