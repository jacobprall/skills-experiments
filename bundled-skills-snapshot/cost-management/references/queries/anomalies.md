# Anomalies Queries

Queries for detecting and analyzing cost anomalies - unusual spending patterns that deviate from expected forecasts.

**Semantic keywords:** anomalies, anomaly, unusual spending, cost spike, spend anomalies, variance, forecast, unexpected costs, anomaly days, contributors, anomaly trends, cost deviation

---

### Cost Anomaly Analysis - Last 30 Days

**Triggered by:** "Which days had cost anomalies?", "Were there any spend anomalies?", "Any cost anomalies recently?", "unusual spending"

**IMPORTANT:** Always filter on `IS_ANOMALY = TRUE` - do not assume actual > forecasted means anomaly.

```sql
SELECT 
    date, 
    COUNT(*) AS anomaly_count, 
    ROUND(SUM(actual_value), 2) AS total_consumption, 
    ROUND(SUM(forecasted_value), 2) AS total_forecast, 
    ROUND(SUM(actual_value - forecasted_value), 2) AS variance_amount, 
    ROUND((SUM(actual_value) - SUM(forecasted_value)) / SUM(forecasted_value) * 100, 2) AS variance_percent 
FROM SNOWFLAKE.ACCOUNT_USAGE.ANOMALIES_DAILY 
WHERE is_anomaly = TRUE 
    AND date >= CURRENT_DATE - 30 
GROUP BY date 
ORDER BY variance_percent DESC 
LIMIT 10;
```

---

### Anomaly Trends Over Time - Last 3 Months

**Triggered by:** "What is the trend of cost anomalies by week over the past 3 months?", "anomaly trends", "weekly anomalies"

```sql
SELECT 
    DATE_TRUNC('WEEK', date) AS week_start, 
    COUNT(DISTINCT date) AS days_with_anomalies, 
    COUNT(*) AS total_anomalies, 
    ROUND(AVG(actual_value - forecasted_value), 2) AS avg_variance_credits, 
    ROUND(AVG((actual_value - forecasted_value) / forecasted_value * 100), 2) AS avg_variance_percent 
FROM SNOWFLAKE.ACCOUNT_USAGE.ANOMALIES_DAILY 
WHERE is_anomaly = TRUE 
    AND date >= CURRENT_DATE - 90 
GROUP BY week_start 
ORDER BY week_start DESC;
```

---

### Most Expensive Warehouses on Anomaly Days

**Triggered by:** "Over the past 6 months what were the most expensive warehouses on the date that had anomalies?", "anomaly warehouse correlation"

```sql
SELECT a.anomaly_date, a.spend, w.warehouse_name as top_warehouse_name, w.daily_credits_used AS warehouse_credits_used 
FROM (
    SELECT DISTINCT date as anomaly_date, actual_value as spend 
    FROM SNOWFLAKE.ACCOUNT_USAGE.ANOMALIES_DAILY 
    WHERE date >= DATEADD(month, -6, CURRENT_DATE()) AND is_anomaly = TRUE
) a 
JOIN (
    SELECT DATE(CONVERT_TIMEZONE('UTC', start_time)) as usage_date, warehouse_name, SUM(credits_used) as daily_credits_used, 
        ROW_NUMBER() OVER (PARTITION BY DATE(CONVERT_TIMEZONE('UTC', start_time)) ORDER BY SUM(credits_used) DESC) as warehouse_cost_rank 
    FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY 
    GROUP BY DATE(CONVERT_TIMEZONE('UTC', start_time)), warehouse_name 
    QUALIFY warehouse_cost_rank = 1
) w ON a.anomaly_date = w.usage_date 
ORDER BY a.anomaly_date DESC, a.spend DESC;
```

---

### Top 5 Resources Contributing to Each Anomaly

**Triggered by:** "For each cost anomaly over the past 4 months, what were the top 5 resources that contributed most to the excessive spending?", "anomaly contributors", "what caused anomalies?"

```sql
WITH anomaly_dates AS (
    SELECT DISTINCT
        date as anomaly_date,
        actual_value,
        forecasted_value,
        (actual_value - forecasted_value) as anomaly_impact
    FROM SNOWFLAKE.ACCOUNT_USAGE.ANOMALIES_DAILY 
    WHERE is_anomaly = TRUE
      AND date >= DATEADD('month', -4, CURRENT_DATE())
), 
anomaly_day_spending AS (
    SELECT
        DATE(m.start_time) as usage_date,
        m.service_type,
        m.name as resource_name,
        SUM(m.credits_used) as daily_credits,
        SUM(m.credits_used_compute) as daily_compute_credits,
        SUM(m.credits_used_cloud_services) as daily_cloud_credits
    FROM SNOWFLAKE.ACCOUNT_USAGE.METERING_HISTORY m 
    JOIN anomaly_dates ad
        ON DATE(m.start_time) = ad.anomaly_date
    WHERE m.start_time >= DATEADD('month', -4, CURRENT_DATE()) 
    GROUP BY DATE(m.start_time), m.service_type, m.name
), 
normal_day_baseline AS (
    SELECT
        service_type,
        name as resource_name,
        AVG(daily_credits) as avg_normal_credits
    FROM (
        SELECT
            DATE(m.start_time) as usage_date,
            m.service_type as service_type,
            m.name as name,
            SUM(m.credits_used) as daily_credits
        FROM SNOWFLAKE.ACCOUNT_USAGE.METERING_HISTORY m
        WHERE m.start_time >= DATEADD('month', -4, CURRENT_DATE())
          AND DATE(m.start_time) NOT IN (SELECT anomaly_date FROM anomaly_dates)
        GROUP BY DATE(m.start_time), m.service_type, m.name
    ) normal_days
    GROUP BY service_type, name
),
anomaly_contributors AS (
    SELECT
        ads.usage_date as anomaly_date,
        ads.service_type,
        ads.resource_name,
        ROUND(ads.daily_credits, 2) as anomaly_day_credits,
        ROUND(COALESCE(nb.avg_normal_credits, 0), 2) as avg_normal_day_credits,
        ROUND(ads.daily_credits - COALESCE(nb.avg_normal_credits, 0), 2) as credits_above_normal,
        CASE
            WHEN nb.avg_normal_credits > 0 THEN
                ROUND(((ads.daily_credits - nb.avg_normal_credits) / nb.avg_normal_credits) * 100, 2)
            ELSE NULL
        END as percent_above_normal,
        ROW_NUMBER() OVER (
            PARTITION BY ads.usage_date
            ORDER BY (ads.daily_credits - COALESCE(nb.avg_normal_credits, 0)) DESC
        ) as contributor_rank
    FROM anomaly_day_spending ads
    LEFT JOIN normal_day_baseline nb
        ON ads.service_type = nb.service_type
       AND ads.resource_name = nb.resource_name
    WHERE ads.daily_credits > 0
)
SELECT
    anomaly_date,
    contributor_rank,
    service_type,
    resource_name,
    anomaly_day_credits,
    avg_normal_day_credits,
    credits_above_normal,
    percent_above_normal,
    CASE
        WHEN percent_above_normal > 200 THEN 'Major Contributor'
        WHEN percent_above_normal > 100 THEN 'Significant Contributor'
        WHEN percent_above_normal > 50 THEN 'Moderate Contributor'
        WHEN credits_above_normal > 50 THEN 'High Cost Contributor'
        ELSE 'Minor Contributor'
    END as contribution_level
FROM anomaly_contributors
WHERE credits_above_normal > 0
  AND contributor_rank <= 5
ORDER BY anomaly_date DESC, contributor_rank ASC;
```
