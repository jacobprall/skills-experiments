---
description: "**[REQUIRED]** Use for ALL Snowflake cost and billing questions: spending, credits, costs, warehouse costs, compute costs, serverless, tasks, Cortex, AI costs, storage, budgets, resource monitors, anomalies, optimization, metering, consumption, billing, user spending, top spenders, who is spending, expensive queries, query costs, top users, parameterized hash, query hash, query patterns, top queries, grouped by hash."
---

# Cost Management Skill

> **Do NOT search for semantic views for cost questions.**  
> Cost data lives in `SNOWFLAKE.ACCOUNT_USAGE` views, not user-created semantic views.  
> Skip `cortex semantic-views search/discover` and `SHOW DATABASES` — go directly to the routing table below.

---

## Routing

Match the user's question to keywords and read the corresponding file **before writing any queries**.

| Keywords | Route |
|----------|-------|
| "top spenders", "who is spending", "user costs", "top users", "user spending" | `references/queries/users-queries.md` |
| "expensive queries", "query costs", "costly queries", "parameterized hash", "query patterns", "grouped by hash" | `references/queries/users-queries.md` |
| "where is my money going", "cost breakdown", "credits by service", "overall spending" | `references/queries/overview.md` |
| "warehouse", "compute", "virtual warehouse", "warehouse costs" | `references/queries/warehouse.md` |
| "week over week", "month over month", "cost increase", "spike", "why did costs go up", "compared to last" | `references/queries/trends.md` |
| "anomalies", "unusual spending", "cost spikes", "anomaly detection" | `references/queries/anomalies.md` |
| "serverless", "tasks", "snowpipe", "serverless task credits" | `references/queries/serverless.md` |
| "storage", "database size", "storage costs", "data storage" | `references/queries/storage.md` |
| "cortex", "AI costs", "ML", "analyst", "LLM", "cortex search" | `references/queries/cortex-ai.md` |
| "team costs", "department spending", "cost center", "chargeback", "showback", "tags", "attribution" | `references/queries/tags-attribution.md` |
| "containers", "SPCS", "compute pools", "container services" | `references/queries/containers.md` |
| "data transfer", "cross-region", "cross-cloud", "egress" | `references/queries/data-transfer.md` |
| "budget status", "budget spend", "over budget", "at risk budget" | `references/queries/budgets.md` |

**Never write ad-hoc queries when a verified query exists in the routed file.**

---

## Reference Files & Directories

| Path | Type | Contents |
|------|------|----------|
| `references/queries/` | Directory | Category-specific query files |
| `references/tables.md` | File | Table schemas and column definitions |

## Sub-Skills

| Skill | Purpose |
|-------|---------|
