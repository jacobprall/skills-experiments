# Cortex AI Queries

Queries for analyzing costs related to Snowflake Cortex AI services including LLM functions and Cortex Analyst.

**Semantic keywords:** cortex, AI, ML, LLM, artificial intelligence, machine learning, cortex functions, cortex analyst, AI costs, tokens, model costs, AI usage, team AI, personal AI spend

---

### Top Cortex Functions by Cost

**Triggered by:** "Which Cortex functions are the most expensive?", "What are my top AI function costs?", "Which AI models consumed the most credits?"

```sql
SELECT 
    function_name, 
    model_name, 
    SUM(tokens) AS total_tokens, 
    ROUND(SUM(token_credits), 2) AS total_credits, 
    COUNT(*) AS time_windows 
FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_FUNCTIONS_USAGE_HISTORY 
GROUP BY function_name, model_name 
ORDER BY total_credits DESC 
LIMIT 10;
```

---

### Cortex Function Usage Trends - Last Week

**Triggered by:** "Show me the daily trend of Cortex function usage and costs over the past week", "Cortex daily trend"

```sql
SELECT 
    DATE(start_time) AS usage_date, 
    function_name, 
    SUM(tokens) AS total_tokens, 
    ROUND(SUM(token_credits), 2) AS total_credits 
FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_FUNCTIONS_USAGE_HISTORY 
WHERE start_time >= DATEADD('D', -7, CURRENT_DATE) 
GROUP BY DATE(start_time), function_name 
ORDER BY usage_date DESC, total_credits DESC;
```

---

### Top Cortex Analyst Users by Credits - This Month

**Triggered by:** "Which users consumed the most Cortex Analyst credits this month?", "Cortex Analyst top users"

```sql
SELECT 
    username, 
    ROUND(SUM(credits), 2) AS total_credits, 
    SUM(request_count) AS total_requests, 
    ROUND(SUM(credits) / NULLIF(SUM(request_count), 0), 4) AS avg_credits_per_request 
FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_ANALYST_USAGE_HISTORY 
WHERE start_time >= DATE_TRUNC('month', CURRENT_DATE) 
GROUP BY username 
ORDER BY total_credits DESC 
LIMIT 10;
```

---

### Cortex Analyst Usage Trend - Last 30 Days

**Triggered by:** "How has Cortex Analyst usage trended over the past month?", "Cortex Analyst trend"

```sql
SELECT 
    DATE_TRUNC('DAY', start_time) AS usage_date, 
    ROUND(SUM(credits), 2) AS daily_credits, 
    SUM(request_count) AS daily_requests, 
    COUNT(DISTINCT username) AS unique_users 
FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_ANALYST_USAGE_HISTORY 
WHERE start_time >= DATEADD('D', -30, CURRENT_DATE) 
GROUP BY usage_date 
ORDER BY usage_date DESC;
```

---

### My Personal Cortex Analyst Spend - Last Week

**Triggered by:** "How much have I personally spent interacting with cortex analyst over the past week?", "my Cortex costs"

```sql
SELECT 
    'My Cortex Analyst Conversations' as cost_type, 
    ROUND(SUM(credits), 4) as total_credits_used, 
    SUM(request_count) as total_requests, 
    COUNT(DISTINCT DATE(start_time)) as active_days, 
    ROUND(SUM(credits) / NULLIF(SUM(request_count), 0), 6) as avg_credits_per_request 
FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_ANALYST_USAGE_HISTORY 
WHERE start_time >= DATEADD('day', -7, CURRENT_DATE()) 
    AND username = CURRENT_USER();
```

---

### Top 5 Users Contributing to Cortex Analyst Costs

**Triggered by:** "What are the top 5 users which contributed most to the cortex analyst costs over the past month?"

```sql
SELECT 
    username, 
    ROUND(SUM(credits), 4) as total_credits_spent, 
    SUM(request_count) as total_requests, 
    COUNT(DISTINCT DATE(start_time)) as active_days, 
    ROUND(SUM(credits) / NULLIF(SUM(request_count), 0), 6) as avg_credits_per_request 
FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_ANALYST_USAGE_HISTORY 
WHERE start_time >= DATEADD('month', -1, CURRENT_DATE()) 
GROUP BY username 
ORDER BY total_credits_spent DESC 
LIMIT 5;
```

---

### Which Team Consumed Most Cortex AI Functions?

**Triggered by:** "Which team consumed the most Cortex AI functions over the past month?", "team Cortex usage"

```sql
WITH warehouse_tags AS (
    SELECT DISTINCT wm.warehouse_id, wm.warehouse_name, tr.tag_name, tr.tag_value 
    FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY wm 
    JOIN SNOWFLAKE.ACCOUNT_USAGE.TAG_REFERENCES tr ON wm.warehouse_name = tr.object_name 
    WHERE tr.domain = 'WAREHOUSE' AND tr.tag_value IS NOT NULL
), 
cortex_functions_by_team AS (
    SELECT wt.tag_name AS tag_key, wt.tag_value AS team_name, 
        SUM(cf.token_credits) AS total_credits, 
        COUNT(DISTINCT cf.function_name) AS unique_functions, 
        COUNT(DISTINCT cf.model_name) AS unique_models 
    FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_FUNCTIONS_USAGE_HISTORY cf 
    JOIN warehouse_tags wt ON cf.warehouse_id = wt.warehouse_id 
    WHERE cf.start_time >= DATEADD(month, -1, CURRENT_DATE()) 
    GROUP BY wt.tag_name, wt.tag_value
) 
SELECT tag_key, team_name, ROUND(total_credits, 4) AS total_cortex_credits, unique_functions, unique_models 
FROM cortex_functions_by_team 
ORDER BY total_credits DESC 
LIMIT 10;
```
