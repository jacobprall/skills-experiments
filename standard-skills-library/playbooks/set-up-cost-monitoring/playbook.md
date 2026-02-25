---
type: playbook
name: set-up-cost-monitoring
domain: cost-ops
depends_on:
  - warehouse-costs
  - serverless-costs
  - cortex-ai-costs
---

# Set Up Cost Monitoring

Establish ongoing visibility into Snowflake spending with budget checks, anomaly awareness, and resource monitors.

## Objective

After completing this playbook, the user will have:

1. A clear picture of current budget status (over-limit and at-risk budgets)
2. Resource monitors configured on high-spend warehouses (if desired)
3. An understanding of Snowflake's built-in anomaly detection
4. Recommended queries they can run periodically to track spending

## Prerequisites

- ACCOUNTADMIN role (for resource monitor creation)
- Existing budgets configured (this playbook checks status, does not create budgets from scratch — budget creation requires Snowsight UI)

## Steps

### Step 1: Assess current budget status

Check which budgets exist, which are over their limit, and which are projected to exceed.

Reference: `primitives/warehouse-costs`

```sql
-- Budgets currently over their spending limit
SELECT
    budget_name, database_name, schema_name,
    ROUND(current_month_spending, 2) AS current_spend,
    credit_limit,
    ROUND(current_month_spending - credit_limit, 2) AS over_by,
    ROUND((current_month_spending - credit_limit) / NULLIF(credit_limit, 0) * 100, 2) AS pct_over
FROM SNOWFLAKE.ACCOUNT_USAGE.BUDGET_DETAILS
WHERE current_month_spending > credit_limit
ORDER BY over_by DESC;
```

```sql
-- Budgets projected to exceed limit by month-end
WITH m AS (
    SELECT DATE_TRUNC('month', CURRENT_TIMESTAMP()) AS month_start,
        DATEADD('month', 1, DATE_TRUNC('month', CURRENT_TIMESTAMP())) AS next_month_start
),
r AS (
    SELECT DATEDIFF('second', m.month_start, CURRENT_TIMESTAMP())::FLOAT /
        NULLIF(DATEDIFF('second', m.month_start, m.next_month_start), 0) AS ratio
    FROM m
)
SELECT
    bd.budget_name, bd.credit_limit,
    ROUND(bd.current_month_spending, 2) AS current_spend,
    ROUND(CASE WHEN r.ratio > 0 THEN bd.current_month_spending / r.ratio ELSE NULL END, 2) AS projected_month_end,
    ROUND((CASE WHEN r.ratio > 0 THEN bd.current_month_spending / r.ratio ELSE NULL END) - bd.credit_limit, 2) AS projected_over_by
FROM SNOWFLAKE.ACCOUNT_USAGE.BUDGET_DETAILS bd
CROSS JOIN r
WHERE r.ratio > 0
    AND (bd.current_month_spending / r.ratio) > bd.credit_limit
ORDER BY projected_over_by DESC;
```

**Checkpoint:**
  severity: info
  present: "Budget status summary — which are over, which are at risk"

### Step 2: Identify high-spend warehouses needing resource monitors

Find warehouses without resource monitors that are consuming significant credits.

```sql
-- Top warehouses by recent spend
SELECT
    warehouse_name,
    ROUND(SUM(credits_used), 2) AS credits_last_7d
FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
WHERE start_time >= DATEADD(DAY, -7, CURRENT_DATE())
GROUP BY warehouse_name
ORDER BY credits_last_7d DESC
LIMIT 10;
```

Cross-reference with the resource monitors found in probes. For warehouses without monitors, recommend creating one.

**Checkpoint:**
  severity: review
  present: "Warehouses without resource monitors and their spend levels — confirm which ones to protect"

### Step 3: Create resource monitors (conditional)

For each warehouse the user approves, create a resource monitor. Resource monitors can suspend warehouses when credit thresholds are reached.

```sql
CREATE RESOURCE MONITOR <monitor_name>
  WITH CREDIT_QUOTA = <monthly_credits>
  FREQUENCY = MONTHLY
  START_TIMESTAMP = IMMEDIATELY
  TRIGGERS
    ON 75 PERCENT DO NOTIFY
    ON 90 PERCENT DO NOTIFY
    ON 100 PERCENT DO SUSPEND;

ALTER WAREHOUSE <warehouse_name> SET RESOURCE_MONITOR = <monitor_name>;
```

**Compensation:**
```sql
ALTER WAREHOUSE <warehouse_name> UNSET RESOURCE_MONITOR;
DROP RESOURCE MONITOR IF EXISTS <monitor_name>;
```

**Checkpoint:**
  severity: critical
  present: "Resource monitor configuration — confirm before creating (SUSPEND trigger will stop warehouse)"

### Step 4: Review anomaly detection baseline

Check recent anomaly history to establish what "normal" looks like.

```sql
SELECT
    DATE_TRUNC('WEEK', date) AS week_start,
    COUNT(DISTINCT date) AS days_with_anomalies,
    COUNT(*) AS total_anomalies,
    ROUND(AVG(actual_value - forecasted_value), 2) AS avg_variance_credits
FROM SNOWFLAKE.ACCOUNT_USAGE.ANOMALIES_DAILY
WHERE is_anomaly = TRUE
    AND date >= CURRENT_DATE - 90
GROUP BY week_start
ORDER BY week_start DESC;
```

Explain that ANOMALIES_DAILY is Snowflake's built-in anomaly detection — no setup required. Recommend the user check this view weekly or set up a task to alert on new anomalies.

### Step 5: Provide monitoring runbook

Summarize the monitoring setup and provide a set of queries the user can run on a regular cadence:

| Cadence | What to Check | Query Source |
|---------|--------------|--------------|
| Daily | Anomaly alerts | ANOMALIES_DAILY where is_anomaly = TRUE and date = yesterday |
| Weekly | Top warehouse spend + WoW trend | primitives/warehouse-costs |
| Weekly | Top user spend | primitives/warehouse-costs (attribution section) |
| Monthly | Budget status (over + projected) | Step 1 queries above |
| Monthly | Service-type cost breakdown + MoM trend | primitives/warehouse-costs (overview section) |

## Anti-patterns

| Mistake | Impact | Instead |
|---------|--------|---------|
| Setting resource monitor to SUSPEND without NOTIFY thresholds | Warehouse stops abruptly with no warning | Always include NOTIFY triggers at 75% and 90% before SUSPEND |
| Creating budgets via SQL | Budgets are created in Snowsight, not SQL | Guide user to Snowsight for budget creation; use SQL only to check status |
| Ignoring ANOMALIES_DAILY | Missing Snowflake's free built-in detection | Always check anomaly history as part of monitoring setup |
| Setting credit quotas too tight | Warehouses suspend during legitimate peak usage | Base quotas on historical p90 spend, not average |
