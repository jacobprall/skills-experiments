---
name: snowflake-ops
description: "Expert Snowflake operations: build data pipelines, secure sensitive data, deploy apps, analyze costs, and enrich data with AI functions. Use for ANY Snowflake task including SQL queries, dynamic tables, masking policies, data classification, cost analysis, Cortex AI functions, Streamlit apps, SPCS containers, dbt projects, or data security."
---

# Snowflake Operations

Expert knowledge for Snowflake — organized as a strict DAG of routers, playbooks, and primitives. Read the routing table below to find the right skill, then follow it.

## Executing SQL

Run queries using the Snowflake CLI:

```bash
snow sql -q "SELECT CURRENT_ROLE()" -c <connection>
```

Multi-line:

```bash
snow sql -q "
SELECT warehouse_name, ROUND(SUM(credits_used), 2) AS credits
FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
WHERE start_time >= DATEADD(DAY, -7, CURRENT_DATE())
GROUP BY warehouse_name
ORDER BY credits DESC
LIMIT 10;
" -c <connection>
```

Replace `<connection>` with the Snowflake connection name from `~/.snowflake/connections.toml`.

Before starting any workflow, verify connectivity:

```bash
snow sql -q "SELECT CURRENT_ACCOUNT(), CURRENT_ROLE(), CURRENT_WAREHOUSE()" -c <connection>
```

## How to Use This Library

1. **Identify the domain** — match the user's request to a domain using the routing table below
2. **Read the domain router** — `routers/<domain>/router.md` classifies intent and picks the target
3. **Follow the target** — playbooks are step-by-step workflows; primitives are SQL reference
4. **Probe before mutating** — always run discovery queries (SHOW, DESCRIBE, SELECT) before CREATE/ALTER/DROP

| User Intent | Action |
|-------------|--------|
| Broad or multi-step goal within one domain | Read the domain router — it selects a playbook |
| Specific SQL syntax question | Read the relevant primitive directly |
| Goal spanning multiple domains | Identify all domains, execute in dependency order (see chaining) |

## Domain Routing

| Domain | Router | Use When |
|--------|--------|----------|
| `data-transformation` | [routers/data-transformation/router.md](routers/data-transformation/router.md) | Pipelines, dynamic tables, dbt, ETL, aggregation, refresh, streaming |
| `data-security` | [routers/data-security/router.md](routers/data-security/router.md) | Masking, classification, PII, policies, access control, governance, audit |
| `app-deployment` | [routers/app-deployment/router.md](routers/app-deployment/router.md) | Streamlit, React, SPCS, dashboards, containers, deploy |
| `cost-ops` | [routers/cost-ops/router.md](routers/cost-ops/router.md) | Costs, credits, spending, billing, budgets, anomalies, expensive queries |
| `ai-analytics` | [routers/ai-analytics/router.md](routers/ai-analytics/router.md) | AI functions, classify, extract, sentiment, summarize, documents, Cortex |
| `data-observability` | [routers/data-observability/router.md](routers/data-observability/router.md) | Data quality, lineage, dependencies, impact analysis, table comparison, DMFs |

### Domain Keywords

| Domain | Keywords |
|--------|----------|
| `data-transformation` | transform, pipeline, refresh, dynamic table, dbt, aggregate, join, ETL, ingest, load, streaming, task |
| `data-security` | mask, protect, classify, PII, policy, audit, access control, governance, sensitive, SSN, email, HIPAA |
| `app-deployment` | app, dashboard, Streamlit, deploy, SPCS, container, UI, frontend, React, Next.js |
| `cost-ops` | cost, credits, spend, budget, bill, warehouse sizing, expensive queries, anomaly, resource monitor, metering |
| `ai-analytics` | AI, classify, extract, sentiment, summarize, AI_CLASSIFY, AI_EXTRACT, AI_COMPLETE, document, PDF, LLM, Cortex |
| `data-observability` | data quality, lineage, dependencies, impact, blast radius, DMF, stale, freshness, compare tables, diff, health |

## Cross-Domain Chaining

When the user's goal spans multiple domains, execute in dependency order:

| Domain | Produces | Requires | Typical Position |
|--------|----------|----------|-----------------|
| `data-transformation` | tables, pipelines | — | First |
| `ai-analytics` | enriched tables | tables | After transformation |
| `data-security` | policies | tables (or standalone for audits) | After tables exist |
| `data-observability` | health reports | tables (or standalone for health checks) | After tables exist |
| `app-deployment` | applications | tables | After data is ready |
| `cost-ops` | recommendations | — | Anytime (standalone) |

**Rules:**
- Domains that produce what others require go first
- `cost-ops` is always standalone — it queries ACCOUNT_USAGE system views
- `data-security` can run standalone for auditing existing policies
- `data-observability` can run standalone for health checks on existing data
- When order is ambiguous, ask the user what to tackle first

### Example

User: "Build a pipeline from my orders data, make sure PII is protected, and create a dashboard"

1. `data-transformation` — build the pipeline (produces tables)
2. `data-security` — classify and mask PII on the output tables
3. `app-deployment` — build the dashboard on the secured tables

## Key Guardrails

| Rule | Why |
|------|-----|
| Use `IS_ROLE_IN_SESSION()` in policies | `CURRENT_ROLE()` fails with inherited roles — always use `IS_ROLE_IN_SESSION()` |
| Probe before mutating | Run SHOW/DESCRIBE/SELECT before CREATE/ALTER/DROP to avoid collisions |
| Check for existing objects | Don't blindly create — use `CREATE OR REPLACE` or check first |
| Confirm destructive operations | Always confirm before DROP, GRANT OWNERSHIP, or policy changes on production |
| Test policies with multiple roles | Verify masking/access from both privileged and restricted roles |
| Test AI functions on small samples first | AI functions cost credits per-row — test on LIMIT 5-10 before batch |

## Skill Inventory

### Primitives (19)

| Name | Domain | Reference |
|------|--------|-----------|
| `dynamic-tables` | data-transformation | [primitives/dynamic-tables/skill.md](primitives/dynamic-tables/skill.md) |
| `dbt-snowflake` | data-transformation | [primitives/dbt-snowflake/skill.md](primitives/dbt-snowflake/skill.md) |
| `openflow` | data-transformation | [primitives/openflow/skill.md](primitives/openflow/skill.md) |
| `masking-policies` | data-security | [primitives/masking-policies/skill.md](primitives/masking-policies/skill.md) |
| `row-access-policies` | data-security | [primitives/row-access-policies/skill.md](primitives/row-access-policies/skill.md) |
| `projection-policies` | data-security | [primitives/projection-policies/skill.md](primitives/projection-policies/skill.md) |
| `data-classification` | data-security | [primitives/data-classification/skill.md](primitives/data-classification/skill.md) |
| `account-usage-views` | data-security | [primitives/account-usage-views/skill.md](primitives/account-usage-views/skill.md) |
| `warehouse-costs` | cost-ops | [primitives/warehouse-costs/skill.md](primitives/warehouse-costs/skill.md) |
| `serverless-costs` | cost-ops | [primitives/serverless-costs/skill.md](primitives/serverless-costs/skill.md) |
| `cortex-ai-costs` | cost-ops | [primitives/cortex-ai-costs/skill.md](primitives/cortex-ai-costs/skill.md) |
| `ai-classify` | ai-analytics | [primitives/ai-classify/skill.md](primitives/ai-classify/skill.md) |
| `ai-extract` | ai-analytics | [primitives/ai-extract/skill.md](primitives/ai-extract/skill.md) |
| `ai-complete` | ai-analytics | [primitives/ai-complete/skill.md](primitives/ai-complete/skill.md) |
| `data-metric-functions` | data-observability | [primitives/data-metric-functions/skill.md](primitives/data-metric-functions/skill.md) |
| `lineage-queries` | data-observability | [primitives/lineage-queries/skill.md](primitives/lineage-queries/skill.md) |
| `table-comparison` | data-observability | [primitives/table-comparison/skill.md](primitives/table-comparison/skill.md) |
| `spcs-deployment` | app-deployment | [primitives/spcs-deployment/skill.md](primitives/spcs-deployment/skill.md) |
| `streamlit-in-snowflake` | app-deployment | [primitives/streamlit-in-snowflake/skill.md](primitives/streamlit-in-snowflake/skill.md) |

### Playbooks (9)

| Name | Domain | Outcome |
|------|--------|---------|
| `secure-sensitive-data` | data-security | Discover PII, apply masking/row/projection policies, verify, monitor |
| `build-streaming-pipeline` | data-transformation | Chained dynamic tables: source → staging → enrichment → aggregation |
| `build-react-app` | app-deployment | Next.js app connected to Snowflake, deployed to SPCS |
| `investigate-cost-spike` | cost-ops | Full investigation: breakdown → trends → anomalies → attribution → recommendations |
| `set-up-cost-monitoring` | cost-ops | Budget status, anomaly detection, resource monitor setup |
| `enrich-text-data` | ai-analytics | AI enrichment pipeline: classify + extract + sentiment with test-before-batch |
| `analyze-documents` | ai-analytics | Process PDFs/documents from a stage: extract fields, batch process |
| `investigate-data-issue` | data-observability | Health check → root cause → lineage trace → recommendations |
| `assess-change-impact` | data-observability | Downstream deps → usage analysis → risk assessment → change plan |

## Anti-patterns

| Pattern | Why It Fails | Instead |
|---------|-------------|---------|
| Jumping to SQL without reading the primitive | Misses constraints, anti-patterns, better approaches | Read the primitive first — it's concise |
| Creating objects without checking what exists | Collisions, errors, overwriting state | Probe: SHOW, DESCRIBE, INFORMATION_SCHEMA |
| `CURRENT_ROLE()` in policy bodies | Fails with inherited roles | `IS_ROLE_IN_SESSION()` |
| Running AI functions on full table without testing | Bad prompts waste credits at scale | Test on LIMIT 5-10 first |
| Skipping classification before masking | Missed PII = false sense of security | Run `SYSTEM$CLASSIFY` first |
| Querying `WAREHOUSE_METERING_HISTORY` for total costs | Misses serverless, Cortex AI, cloud services | Use `METERING_HISTORY` for account totals |
| Time-based `TARGET_LAG` on intermediate dynamic tables | Unnecessary refreshes, wasted credits | Use `DOWNSTREAM` on non-leaf tables |
