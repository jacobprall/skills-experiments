---
name: standard-router
description: "**[REQUIRED]** for ANY request that spans multiple concerns (e.g., pipeline + security, security + dashboard, pipeline + security + app) or when the user's intent is ambiguous. This skill determines execution order and chains domain skills correctly. ALWAYS invoke this skill FIRST when the request mentions two or more of: (1) data transformation/pipelines/dynamic tables/dbt/ETL, (2) data security/masking/classification/PII/policies/governance, (3) app deployment/dashboard/Streamlit/SPCS/React. Execution order: data-transformation first (produces tables), then data-security (requires tables), then app-deployment (requires tables). Also invoke when the request is vague and could match multiple domains. Triggers: pipeline AND security, pipeline AND dashboard, security AND dashboard, end-to-end, full workflow, build and protect, transform and mask, ingest secure deploy."
---

# Meta-Router

Single entry point for the Standard Skills Library. Resolves user intent to one or more domain routers.

## How It Works

1. **Parse user intent** — identify which domains are involved
2. **Single domain?** — route directly to that domain's router
3. **Multiple domains?** — topologically sort by `requires`/`produces`, chain in order

## Decision Criteria

| Signal | How to Detect | Example |
|--------|---------------|---------|
| **Domain keywords** | Match against domain descriptions and common terms | "mask columns" → data-security, "deploy app" → app-deployment |
| **Multi-domain intent** | User describes an end-to-end flow spanning concerns | "Ingest data, secure it, build a dashboard" |
| **Ambiguous intent** | Keywords could map to multiple domains | "protect my pipeline" — security or transformation? |

### Domain Keywords

| Domain | Keywords |
|--------|----------|
| `data-transformation` | transform, pipeline, refresh, dynamic table, dbt, aggregate, join, ETL, ingest, load |
| `data-security` | mask, protect, classify, PII, policy, audit, access control, governance, sensitive |
| `app-deployment` | app, dashboard, Streamlit, deploy, SPCS, container, UI, frontend |

## Routing Logic

```
Start
  │
  ├─ Identify domains in user intent
  │
  ├─ Single domain detected?
  │   └─ YES → Route to that domain's skill
  │            (domain skill decides: playbook vs guided vs reference)
  │
  ├─ Multiple domains detected?
  │   │
  │   ├─ Build dependency graph from requires/produces
  │   │
  │   ├─ Topologically sort domains
  │   │   (domains that produce what others require go first)
  │   │
  │   └─ Execute phases in order, carrying context forward
  │
  └─ No clear domain?
      └─ Ask user to clarify their goal with structured options
```

## Domain Dependencies

| Domain | Produces | Requires | Order |
|--------|----------|----------|-------|
| `data-transformation` | tables, pipelines | nothing | First |
| `data-security` | policies, governance | tables | Second |
| `app-deployment` | applications, URLs | tables | Third |

## Context Handoff Between Domains

Each phase produces outputs that flow to subsequent phases:

| Domain | Produces | Consumed By |
|--------|----------|-------------|
| `data-transformation` | Table names, pipeline definitions | data-security, app-deployment |
| `data-security` | Policy names, protected tables | app-deployment |
| `app-deployment` | Service endpoints, app URLs | (terminal) |

## Multi-Domain Chaining Example

User: "Build a pipeline, apply masking policies, then build a dashboard"

1. **Identify domains**: data-transformation, data-security, app-deployment
2. **Sorted order**: `[data-transformation, data-security, app-deployment]`
3. **Phase 1** — data-transformation: Build pipeline, produce table names
4. **Phase 2** — data-security: Apply policies to those tables
5. **Phase 3** — app-deployment: Build dashboard querying those tables

## Guardrails

| Rule | Limit | On Violation |
|------|-------|--------------|
| Max steps per domain | 8 | Suggest breaking into smaller goals |
| Prohibited actions | DROP DATABASE, DROP SCHEMA, GRANT OWNERSHIP, ALTER ACCOUNT | Block — too destructive |
| Checkpoint frequency | After every step in guided mode | Compensates for higher risk |

## Anti-patterns

| Pattern | Problem | Correction |
|---------|---------|------------|
| Guessing domain order | Chaining without checking requires/produces | Use topological sort based on declared dependencies |
| Ignoring context handoff | Starting phase 2 without outputs from phase 1 | Carry forward tables, policies, endpoints from completed phases |
| Over-chaining | Breaking a single-domain request into multiple phases | If the user's intent fits one domain, route directly |
