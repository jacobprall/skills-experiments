---
type: primitive
name: cortex-ai-costs
domain: cost-ops
snowflake_docs: "https://docs.snowflake.com/en/sql-reference/account-usage/cortex_functions_usage_history"
---

# Cortex AI Costs

Analyze costs from Snowflake Cortex AI services: LLM functions (AI_CLASSIFY, AI_COMPLETE, AI_EXTRACT, etc.), Cortex Analyst, and Cortex Search. These are billed by token consumption, not warehouse credits.

## Key Views

| View | What It Contains | Billing Unit | Latency |
|------|-----------------|-------------|---------|
| `CORTEX_FUNCTIONS_USAGE_HISTORY` | Per-function token and credit usage | Token credits | ~2 hours |
| `CORTEX_ANALYST_USAGE_HISTORY` | Per-user Cortex Analyst usage | Credits per request | ~2 hours |
| `METERING_HISTORY` | Aggregated Cortex credits (under service_type) | Credits | ~2 hours |

## Cortex Function Costs

### Top functions by cost

```sql
SELECT
    function_name, model_name,
    SUM(tokens) AS total_tokens,
    ROUND(SUM(token_credits), 4) AS total_credits,
    COUNT(*) AS time_windows
FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_FUNCTIONS_USAGE_HISTORY
GROUP BY function_name, model_name
ORDER BY total_credits DESC
LIMIT 10;
```

### Daily function cost trend (last 7 days)

```sql
SELECT
    DATE(start_time) AS day,
    function_name,
    SUM(tokens) AS tokens,
    ROUND(SUM(token_credits), 4) AS credits
FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_FUNCTIONS_USAGE_HISTORY
WHERE start_time >= DATEADD('day', -7, CURRENT_DATE())
GROUP BY DATE(start_time), function_name
ORDER BY day DESC, credits DESC;
```

### Function cost by model (which models are most expensive?)

```sql
SELECT
    model_name,
    COUNT(DISTINCT function_name) AS functions_using_model,
    SUM(tokens) AS total_tokens,
    ROUND(SUM(token_credits), 4) AS total_credits
FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_FUNCTIONS_USAGE_HISTORY
WHERE start_time >= DATEADD('month', -1, CURRENT_DATE())
GROUP BY model_name
ORDER BY total_credits DESC;
```

## Cortex Analyst Costs

### Top users by Cortex Analyst spend

```sql
SELECT
    username,
    ROUND(SUM(credits), 4) AS total_credits,
    SUM(request_count) AS total_requests,
    ROUND(SUM(credits) / NULLIF(SUM(request_count), 0), 6) AS avg_credits_per_request
FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_ANALYST_USAGE_HISTORY
WHERE start_time >= DATE_TRUNC('month', CURRENT_DATE())
GROUP BY username
ORDER BY total_credits DESC
LIMIT 10;
```

### Cortex Analyst daily trend (last 30 days)

```sql
SELECT
    DATE_TRUNC('day', start_time) AS day,
    ROUND(SUM(credits), 4) AS credits,
    SUM(request_count) AS requests,
    COUNT(DISTINCT username) AS unique_users
FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_ANALYST_USAGE_HISTORY
WHERE start_time >= DATEADD('day', -30, CURRENT_DATE())
GROUP BY day
ORDER BY day DESC;
```

### Personal Cortex Analyst spend (current user)

```sql
SELECT
    ROUND(SUM(credits), 4) AS total_credits,
    SUM(request_count) AS total_requests,
    COUNT(DISTINCT DATE(start_time)) AS active_days,
    ROUND(SUM(credits) / NULLIF(SUM(request_count), 0), 6) AS avg_per_request
FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_ANALYST_USAGE_HISTORY
WHERE start_time >= DATEADD('day', -7, CURRENT_DATE())
    AND username = CURRENT_USER();
```

## Cost Optimization Guidance

| Scenario | Recommendation |
|----------|---------------|
| High AI_COMPLETE costs | Use smaller models (e.g., `snowflake-arctic-embed` for simple tasks instead of large LLMs) |
| Repeated identical function calls | Cache results in a table; use incremental processing to avoid re-running on unchanged data |
| AI_CLASSIFY on large tables | Test on a LIMIT sample first, then batch — don't classify millions of rows in one pass |
| Cortex Analyst adoption driving costs | Monitor per-user spend; set expectations on request volume; review if automated tools are calling Analyst |

## Constraints

- Token credit costs vary by model and function. The same function with different models has different per-token rates.
- `CORTEX_FUNCTIONS_USAGE_HISTORY` is aggregated by hourly windows, not per-invocation. Individual function call costs aren't available.
- Cortex AI costs do not appear in `WAREHOUSE_METERING_HISTORY` — they are a separate billing line.
- Cortex Search Service costs appear in `METERING_HISTORY` under a separate service type, not in `CORTEX_FUNCTIONS_USAGE_HISTORY`.

## Anti-patterns

| Pattern | Why It Fails | Instead |
|---------|-------------|---------|
| Looking at WAREHOUSE_METERING_HISTORY for AI costs | Cortex AI doesn't use warehouses | Use CORTEX_FUNCTIONS_USAGE_HISTORY |
| Comparing raw token counts across functions | Different functions have different per-token rates | Compare token_credits (cost), not raw tokens |
| Ignoring Cortex Analyst in cost analysis | Cortex Analyst is separately billed and can be significant | Always check both function usage AND analyst usage |
| Running AI functions on full table without testing | One bad prompt can waste significant credits on millions of rows | Always test on a small sample (LIMIT 10) before batch processing |

## References

- `primitives/warehouse-costs`
- `primitives/serverless-costs`
- [CORTEX_FUNCTIONS_USAGE_HISTORY](https://docs.snowflake.com/en/sql-reference/account-usage/cortex_functions_usage_history)
- [CORTEX_ANALYST_USAGE_HISTORY](https://docs.snowflake.com/en/sql-reference/account-usage/cortex_analyst_usage_history)
