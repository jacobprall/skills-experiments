---
type: router
name: data-observability
domain: data-observability
routes_to:
  - primitives/data-metric-functions
  - primitives/lineage-queries
  - primitives/table-comparison
  - playbooks/investigate-data-issue
  - playbooks/assess-change-impact
---

# Data Observability

Single entry point for data quality monitoring (via DMFs), data lineage analysis, impact assessment, and table comparison. Unifies "is my data good?" with "where did it come from and what does it affect?"

## Decision Criteria

| Input | How to Determine | Example User Statements |
|-------|-----------------|------------------------|
| **Goal** | Is the user investigating a problem, planning a change, or doing a health check? | "Something's wrong with my data", "What depends on this table?", "Is my schema healthy?" |
| **Direction** | Upstream (where does data come from?) or downstream (what does it affect?) | "Root cause", "impact analysis", "blast radius" |
| **Scope** | Single table, single schema, or cross-database? | "This table", "all tables in my schema", "across databases" |

## Routing Logic

```
Start
  ├─ User reports DATA QUALITY PROBLEM (failing metrics, stale data, wrong numbers)?
  │   └─ YES → playbooks/investigate-data-issue
  │
  ├─ User plans a CHANGE and wants to understand impact / dependencies?
  │   └─ YES → playbooks/assess-change-impact
  │
  ├─ User wants a HEALTH SCORE or quality metrics for a schema?
  │   └─ YES → primitives/data-metric-functions
  │
  ├─ User wants to TRACE LINEAGE (upstream source or downstream dependents)?
  │   └─ YES → primitives/lineage-queries
  │
  ├─ User wants to COMPARE two tables (migration, regression, diff)?
  │   └─ YES → primitives/table-comparison
  │
  └─ User asks about QUALITY TRENDS over time?
      └─ YES → primitives/data-metric-functions (trends section)
```

Check for broad intent first. "Something's wrong with my data" should route to the investigate-data-issue playbook, not directly to a primitive.

## Routes To

| Target | Mode | When Selected | What It Provides |
|--------|------|---------------|------------------|
| `playbooks/investigate-data-issue` | Playbook | Broad: data looks wrong, quality problem, broken pipeline | Health check → root cause → lineage trace → recommendations |
| `playbooks/assess-change-impact` | Playbook | Broad: planning a change, need to know blast radius | Downstream deps → usage analysis → risk assessment → change plan |
| `primitives/data-metric-functions` | Reference | Narrow: DMF health scores, quality trends, SLA alerting | DATA_QUALITY_MONITORING_RESULTS queries, health scoring, regression detection |
| `primitives/lineage-queries` | Reference | Narrow: trace upstream/downstream, column lineage | OBJECT_DEPENDENCIES, ACCESS_HISTORY queries |
| `primitives/table-comparison` | Reference | Narrow: diff two tables, validate migration | Row-level diff, schema comparison, aggregate comparison |

## Anti-patterns

| Mis-routing | Why It Happens | Correct Route |
|-------------|----------------|---------------|
| Sending "is my data healthy?" to lineage-queries | "Health" sounds like it might be about lineage trust | Route to `primitives/data-metric-functions` for DMF-based health |
| Sending "what depends on X" to data-metric-functions | Dependency questions are lineage, not quality | Route to `primitives/lineage-queries` or `playbooks/assess-change-impact` |
| Sending "blast radius" to table-comparison | "Blast radius" is business language for downstream impact | Route to `playbooks/assess-change-impact` |
| Skipping quality check before lineage trace | User says "data looks wrong" — need to confirm what's wrong before tracing | Route to `playbooks/investigate-data-issue` which combines both |
