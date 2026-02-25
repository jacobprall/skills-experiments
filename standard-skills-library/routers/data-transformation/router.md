---
type: router
name: data-transformation
domain: data-transformation
routes_to:
  - primitives/dynamic-tables
  - primitives/dbt-snowflake
  - primitives/openflow
  - playbooks/build-streaming-pipeline
---

# Data Transformation

Routes data pipeline and transformation requests to the right approach: dynamic tables for incremental refresh, dbt for orchestrated model transforms, or OpenFlow for connector-based ingestion.

## Decision Criteria

| Input | How to Determine | Example User Statements |
|-------|-----------------|------------------------|
| **What data?** | Is data already in Snowflake, or coming from external sources? | "Transform my staging tables" vs "Ingest from Postgres" |
| **Freshness** | How stale can the data be? | "Near real-time", "Updated daily", "On demand" |
| **Complexity** | Simple aggregation, multi-step pipeline, or full dbt project? | "Summarize orders by day" vs "Run my dbt models" |
| **Existing tooling** | Does the user already have dbt, NiFi connectors, or nothing? | "I have a dbt project" vs "Starting from scratch" |

## Routing Logic

```
Start
  ├─ User wants a FULL PIPELINE (ingest + transform + continuous refresh)?
  │   └─ YES → playbooks/build-streaming-pipeline
  │
  ├─ User has an existing dbt project?
  │   └─ YES → primitives/dbt-snowflake
  │
  ├─ Data is coming from external sources via connectors?
  │   └─ YES → primitives/openflow
  │
  ├─ Data is already in Snowflake and needs transformation?
  │   ├─ Simple transform, needs continuous refresh?
  │   │   └─ YES → primitives/dynamic-tables
  │   │
  │   ├─ Complex multi-step pipeline, SQL-native?
  │   │   └─ YES → primitives/dynamic-tables (chain multiple DTs)
  │   │
  │   └─ Needs orchestrated transforms with testing, seeds, docs?
  │       └─ YES → primitives/dbt-snowflake
  │
  └─ Unsure?
      └─ Ask about data location and freshness requirement
```

### Decision matrix

| Requirement | Dynamic Tables | dbt on Snowflake | OpenFlow |
|------------|---------------|-----------------|----------|
| Data already in Snowflake | Yes | Yes | N/A — for ingestion |
| Near-real-time freshness | Yes (target lag) | No (batch) | Yes (streaming) |
| Multi-step SQL pipeline | Yes (chain DTs) | Yes (dbt DAG) | No |
| Testing & documentation | No | Yes (built-in) | No |
| External source ingestion | No | No | Yes |
| Schema evolution handling | Manual | dbt manages | Connector handles |
| Scheduling | Automatic (lag-driven) | Task-based (cron) | Continuous |

## Routes To

| Target | Mode | When Selected | What It Provides |
|--------|------|---------------|------------------|
| `playbooks/build-streaming-pipeline` | Playbook | Broad intent: build a full pipeline from ingestion through transformation | End-to-end workflow: source identification → pipeline design → chained dynamic tables |
| `primitives/dynamic-tables` | Reference | Narrow: data in Snowflake, needs continuous/incremental refresh | CREATE DYNAMIC TABLE syntax, pipeline chaining, refresh monitoring |
| `primitives/dbt-snowflake` | Reference | Narrow: existing or desired dbt project, needs testing/docs | `snow dbt` CLI, EXECUTE DBT PROJECT, scheduling |
| `primitives/openflow` | Reference | Narrow: data coming from external sources, connector-based ingestion | NiFi connector management, throughput monitoring |
| *(multiple primitives)* | Guided | Moderate intent: user has a transformation goal that doesn't fit a pre-built playbook | Agent constructs a plan from relevant primitives, user approves before execution |

## Anti-patterns

| Mis-routing | Why It Happens | Correct Route |
|-------------|----------------|---------------|
| Sending "create a pipeline" to dbt when there's no dbt project | "Pipeline" is ambiguous | If SQL-native and no existing dbt: use dynamic tables |
| Using dynamic tables for data ingestion from external sources | Dynamic tables transform existing Snowflake data, they don't ingest | Use OpenFlow or stages + COPY INTO for ingestion |
| Using OpenFlow for simple table-to-table transforms | Connector overhead for internal transformations | Use dynamic tables for Snowflake-to-Snowflake transforms |
