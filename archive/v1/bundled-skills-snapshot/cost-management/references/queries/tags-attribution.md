# Tags & Attribution Queries

Queries for cost attribution using Snowflake tags - allocating costs to teams, departments, cost centers, and identifying untagged resources.

**Semantic keywords:** tags, attribution, team costs, department, cost center, chargeback, showback, tag combination, untagged resources, missing tags, cost allocation, team spending, tag value

---

### Team Cost Breakdown Across All Services

**Triggered by:** "What did each team spend in total?", "team costs by service type", "cost breakdown by team", "department costs"

```sql
SELECT 
    tr.tag_name, 
    tr.tag_value AS team, 
    m.service_type, 
    COUNT(DISTINCT m.name) AS resource_count, 
    ROUND(SUM(m.credits_used), 2) AS total_credits, 
    ROUND(SUM(m.credits_used_compute), 2) AS compute_credits, 
    ROUND(SUM(m.credits_used_cloud_services), 2) AS cloud_services_credits 
FROM SNOWFLAKE.ACCOUNT_USAGE.METERING_HISTORY m 
JOIN SNOWFLAKE.ACCOUNT_USAGE.TAG_REFERENCES tr ON m.name = tr.object_name 
WHERE m.start_time >= DATEADD(MONTH, -1, CURRENT_DATE()) 
    AND m.start_time < CURRENT_DATE() 
    AND tr.tag_value IS NOT NULL AND tr.tag_value != '' 
GROUP BY tr.tag_name, tr.tag_value, m.service_type 
ORDER BY total_credits DESC;
```

---

### Team Cost Breakdown by Warehouse

**Triggered by:** "What is the total cost breakdown by team across all warehouses?", "team warehouse costs"

```sql
SELECT 
    tr.tag_name, 
    tr.tag_value AS team, 
    COUNT(DISTINCT wm.warehouse_name) AS warehouse_count, 
    ROUND(SUM(wm.credits_used), 2) AS total_credits, 
    ROUND(AVG(wm.credits_used), 2) AS avg_credits_per_warehouse 
FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY wm 
JOIN SNOWFLAKE.ACCOUNT_USAGE.TAG_REFERENCES tr ON wm.warehouse_name = tr.object_name 
WHERE tr.domain = 'WAREHOUSE' 
    AND tr.tag_value IS NOT NULL AND tr.tag_value != '' 
    AND wm.start_time >= DATEADD(DAY, -7, CURRENT_DATE()) 
    AND wm.start_time < CURRENT_DATE() 
GROUP BY tr.tag_name, tr.tag_value 
ORDER BY total_credits DESC;
```

---

### Top Teams by Warehouse Spend

**Triggered by:** "Which teams or cost centers have the highest warehouse costs?", "top teams by spend"

```sql
SELECT 
    tr.tag_name, 
    tr.tag_value AS team, 
    wm.warehouse_name, 
    ROUND(SUM(wm.credits_used), 2) AS credits 
FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY wm 
JOIN SNOWFLAKE.ACCOUNT_USAGE.TAG_REFERENCES tr ON wm.warehouse_name = tr.object_name 
WHERE tr.domain = 'WAREHOUSE' 
    AND tr.tag_value IS NOT NULL AND tr.tag_value != '' 
    AND wm.start_time >= DATEADD(DAY, -7, CURRENT_DATE()) 
    AND wm.start_time < CURRENT_DATE() 
GROUP BY tr.tag_name, tr.tag_value, wm.warehouse_name 
ORDER BY credits DESC 
LIMIT 100;
```

---

### Simple Tag Combination Cost Overview

**Triggered by:** "Show me a quick overview of all tag combinations and their spending", "basic cost totals by tag", "tag spending overview"

```sql
SELECT 
    tr.tag_name, 
    tr.tag_value, 
    CONCAT(tr.tag_name, '=', tr.tag_value) AS tag_combination, 
    tr.domain AS resource_type, 
    COUNT(DISTINCT tr.object_name) AS tagged_resources, 
    ROUND(SUM(m.credits_used), 2) AS total_credits, 
    ROUND(SUM(m.credits_used_compute), 2) AS compute_credits 
FROM SNOWFLAKE.ACCOUNT_USAGE.TAG_REFERENCES tr 
JOIN SNOWFLAKE.ACCOUNT_USAGE.METERING_HISTORY m ON tr.object_name = m.name 
WHERE m.start_time >= DATEADD('month', -1, CURRENT_DATE()) 
    AND tr.tag_name IS NOT NULL AND tr.tag_value IS NOT NULL AND tr.tag_value != '' 
GROUP BY tr.tag_name, tr.tag_value, tr.domain 
HAVING SUM(m.credits_used) > 0 
ORDER BY total_credits DESC 
LIMIT 20;
```

---

### Untagged Resources Consuming Credits

**Triggered by:** "Which resources are consuming credits but have no tags assigned?", "untagged resources", "missing cost attribution"

```sql
WITH tagged_resources AS (
    SELECT DISTINCT object_name, domain 
    FROM SNOWFLAKE.ACCOUNT_USAGE.TAG_REFERENCES 
    WHERE tag_name IS NOT NULL AND tag_value IS NOT NULL AND tag_value != ''
), 
resource_spending AS (
    SELECT CASE WHEN m.name IS NULL OR m.name = '' THEN CONCAT('UNNAMED_', m.service_type) ELSE m.name END AS resource_name, 
        m.service_type AS service_category, 
        CASE WHEN m.service_type = 'WAREHOUSE_METERING' THEN 'WAREHOUSE' 
             WHEN m.service_type = 'STORAGE' THEN 'DATABASE' 
             ELSE 'OTHER' END AS resource_domain, 
        ROUND(SUM(m.credits_used), 2) AS total_credits 
    FROM SNOWFLAKE.ACCOUNT_USAGE.METERING_HISTORY m 
    WHERE m.start_time >= DATEADD('month', -1, CURRENT_DATE()) AND m.credits_used > 0 
    GROUP BY 1, 2
) 
SELECT rs.resource_name, rs.service_category, rs.total_credits 
FROM resource_spending rs 
LEFT JOIN tagged_resources tr ON rs.resource_name = tr.object_name AND rs.resource_domain = tr.domain 
WHERE tr.object_name IS NULL AND rs.total_credits > 0 
ORDER BY rs.total_credits DESC 
LIMIT 25;
```
