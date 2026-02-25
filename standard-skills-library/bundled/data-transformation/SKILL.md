---
name: data-transformation
description: "**[REQUIRED]** for building data pipelines, creating dynamic tables, deploying dbt projects on Snowflake, setting up OpenFlow connectors, and end-to-end streaming pipeline workflows. Covers Dynamic Tables with TARGET_LAG and REFRESH_MODE, dbt on Snowflake via snow CLI (not local dbt CLI), and OpenFlow/NiFi-based data integration. Triggers: pipeline, dynamic table, transform, aggregate, ETL, ingest, refresh, streaming, dbt, dbt project, snow dbt, TARGET_LAG, DOWNSTREAM, incremental refresh, change tracking, data pipeline, openflow, connector, NiFi."
---

# Data Transformation

Routes data transformation requests to the appropriate primitive or playbook.

## Routing Logic

```
Start
  ├─ User wants a FULL PIPELINE end to end?
  │   (ingest → stage → enrich → aggregate)
  │   └─ YES → Use the Build Streaming Pipeline playbook below
  │
  ├─ User wants DYNAMIC TABLES specifically?
  │   └─ YES → Use the Dynamic Tables reference below
  │
  ├─ User wants to deploy/run a DBT PROJECT on Snowflake?
  │   └─ YES → Use the dbt on Snowflake reference below
  │
  └─ User wants to set up data INGESTION from external sources?
      └─ YES → Use the OpenFlow reference below
```

---

# Playbook: Build a Streaming Pipeline

Set up a continuously refreshing data pipeline — from ingestion through transformation to business-ready output.

## Objective

A multi-stage transformation pipeline where:
- Source data flows through staging, enrichment, and aggregation layers
- Each layer refreshes automatically based on target lag
- The final table is always within a configured freshness window

## Steps

### Step 1: Identify sources and enable change tracking

```sql
-- Check source tables
SHOW TABLES LIKE '<source_table>' IN SCHEMA <db>.<schema>;

-- Enable change tracking (required for incremental refresh)
ALTER TABLE <db>.<schema>.<source_table> SET CHANGE_TRACKING = TRUE;
```

Present source readiness to user before proceeding.

### Step 2: Design the pipeline stages

Plan the transformation as a chain of dynamic tables:

| Stage | Purpose | Target Lag |
|-------|---------|------------|
| Staging | Clean and normalize raw data | `DOWNSTREAM` |
| Enrichment | Join with dimension tables | `DOWNSTREAM` |
| Aggregation | Final business-level summary | Time-based (e.g., `'1 day'`) |

**CRITICAL: Only the final (leaf) table gets a time-based target lag. All intermediate tables use `DOWNSTREAM` to avoid unnecessary refreshes.**

Present pipeline design to user for approval before creating tables.

### Step 3: Create staging layer

```sql
CREATE OR REPLACE DYNAMIC TABLE <db>.<target_schema>.cleaned_<source>
  TARGET_LAG = DOWNSTREAM
  WAREHOUSE = <warehouse>
  REFRESH_MODE = INCREMENTAL
  AS
    SELECT
      <explicit column list>,
      TRIM(column) AS column,  -- cleaning
      ROUND(amount, 2) AS amount
    FROM <db>.<source_schema>.<source_table>
    WHERE <filter_nulls>;
```

### Step 4: Create enrichment layer

```sql
CREATE OR REPLACE DYNAMIC TABLE <db>.<target_schema>.enriched_<source>
  TARGET_LAG = DOWNSTREAM
  WAREHOUSE = <warehouse>
  REFRESH_MODE = INCREMENTAL
  AS
    SELECT
      s.*,
      d.dimension_column
    FROM <db>.<target_schema>.cleaned_<source> s
    JOIN <db>.<source_schema>.<dimension_table> d
      ON s.key = d.key;
```

### Step 5: Create aggregation layer (leaf table)

```sql
CREATE OR REPLACE DYNAMIC TABLE <db>.<target_schema>.<summary_name>
  TARGET_LAG = '<freshness_target>'
  WAREHOUSE = <warehouse>
  REFRESH_MODE = INCREMENTAL
  AS
    SELECT
      dimension,
      DATE_TRUNC('day', date_col) AS period,
      COUNT(*) AS record_count,
      SUM(amount) AS total_amount,
      AVG(amount) AS avg_amount
    FROM <db>.<target_schema>.enriched_<source>
    GROUP BY dimension, period;
```

### Step 6: Verify pipeline health

```sql
-- Check scheduling state
SELECT name, refresh_mode, target_lag, scheduling_state
FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLES())
ORDER BY name;

-- Check refresh history
SELECT name, state, state_message, refresh_start_time, refresh_end_time
FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLE_REFRESH_HISTORY())
ORDER BY refresh_start_time DESC
LIMIT 20;
```

Present pipeline health to user.

## Anti-patterns

| Mistake | Impact | Instead |
|---------|--------|---------|
| Time-based lag on intermediate tables | Unnecessary refreshes, wasted credits | Use `DOWNSTREAM` on all non-leaf tables |
| One massive dynamic table doing everything | Full refresh every cycle, slow | Chain small tables, each doing one transform |
| Forgetting change tracking on source tables | Incremental refresh silently falls back to full | Enable change tracking before creating DTs |
| Using `SELECT *` in pipeline stages | Schema changes break the pipeline | Explicitly list columns |

---

# Primitive: Dynamic Tables

Declarative tables that automatically refresh based on a SQL query definition.

## Syntax

```sql
CREATE [ OR REPLACE ] DYNAMIC TABLE <db>.<schema>.<name>
  TARGET_LAG = { '<time>' | DOWNSTREAM }
  WAREHOUSE = <warehouse>
  [ REFRESH_MODE = { AUTO | FULL | INCREMENTAL } ]
  AS <query>;
```

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `TARGET_LAG` | Yes | How fresh the data should be. Time-based (`'1 hour'`, `'30 minutes'`) or `DOWNSTREAM` |
| `WAREHOUSE` | Yes | Warehouse for refresh operations |
| `REFRESH_MODE` | No | `AUTO` (default), `FULL`, or `INCREMENTAL` |

### TARGET_LAG values

| Value | When to Use |
|-------|------------|
| `'30 minutes'`, `'1 hour'`, `'1 day'` | Leaf (final) tables — drives the refresh schedule |
| `DOWNSTREAM` | Intermediate tables — only refreshes when a downstream table needs it |

### REFRESH_MODE values

| Mode | Behavior |
|------|----------|
| `AUTO` | Snowflake picks incremental or full based on query complexity |
| `INCREMENTAL` | Only processes changed rows — most efficient but not all queries support it |
| `FULL` | Recomputes entire table each refresh — use when incremental isn't supported |

## Pipeline chaining

Chain dynamic tables for multi-stage pipelines. Only the leaf gets a time-based lag:

```
Source (base table, change tracking ON)
  → Staging DT (TARGET_LAG = DOWNSTREAM)
    → Enrichment DT (TARGET_LAG = DOWNSTREAM)
      → Aggregation DT (TARGET_LAG = '1 day')  ← only leaf has time-based lag
```

## Monitoring

```sql
-- Current state
SELECT name, refresh_mode, target_lag, scheduling_state
FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLES());

-- Refresh history
SELECT name, state, state_message, refresh_start_time, refresh_end_time
FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLE_REFRESH_HISTORY())
ORDER BY refresh_start_time DESC;

-- Suspend/resume
ALTER DYNAMIC TABLE <name> SUSPEND;
ALTER DYNAMIC TABLE <name> RESUME;
```

## Constraints

- Source tables must have `CHANGE_TRACKING = TRUE` for incremental refresh
- `REFRESH_MODE = INCREMENTAL` doesn't support all SQL constructs (e.g., some window functions)
- Dynamic tables cannot be updated with DML — they're read-only, defined by their query
- Warehouse must be running for refreshes to occur

## Anti-patterns

| Pattern | Why It Fails | Instead |
|---------|-------------|---------|
| Time-based lag on intermediate tables | Triggers unnecessary refreshes | Use `DOWNSTREAM` |
| `SELECT *` in definition | Schema changes on source break the DT | List columns explicitly |
| Forgetting change tracking | Falls back to full refresh silently | `ALTER TABLE ... SET CHANGE_TRACKING = TRUE` |
| Single monolithic DT | Complex query = full refresh every time | Chain small, focused DTs |

---

# Primitive: dbt on Snowflake

Deploy and run dbt Core projects directly in Snowflake using the `snow` CLI.

## Syntax

### Deploy a project

```bash
snow dbt deploy <project_name> \
  --source /path/to/dbt \
  --database <db> \
  --schema <schema>
```

### Execute models

```bash
# Run all models (flags BEFORE project name)
snow dbt execute -c <connection> --database <db> --schema <schema> <project_name> run

# Run specific model with dependencies
snow dbt execute -c <connection> --database <db> --schema <schema> <project_name> run --select +target_model+

# Test
snow dbt execute -c <connection> --database <db> --schema <schema> <project_name> test
```

### Schedule via SQL

```sql
CREATE TASK <db>.<schema>.run_dbt_daily
  WAREHOUSE = <wh>
  SCHEDULE = 'USING CRON 0 6 * * * UTC'
AS
EXECUTE DBT PROJECT <db>.<schema>.<project_name> ARGS = '["run"]';

ALTER TASK <db>.<schema>.run_dbt_daily RESUME;
```

## Constraints

- Always use `snow dbt execute` — NOT local `dbt run`, `dbt test`, `dbt build`
- CLI flags must come BEFORE the project name
- Scheduling uses `EXECUTE DBT PROJECT` SQL, not `snow dbt execute`

## Anti-patterns

| Pattern | Why It Fails | Instead |
|---------|-------------|---------|
| Using `dbt run` locally | Different execution engine | Use `snow dbt execute` |
| Putting flags after project name | CLI parsing fails | Flags before project name |
| Using `snow dbt execute` in CREATE TASK | Wrong syntax for SQL context | Use `EXECUTE DBT PROJECT` |

---

# Primitive: OpenFlow

Data integration platform built on Apache NiFi for connector-based ingestion and data movement within Snowflake.

## Core Operations

| Operation | Description |
|-----------|-------------|
| Check connector status | Verify running connectors and health |
| Create connector | Set up a new data connector |
| Start/stop connector | Control connector execution state |
| Monitor throughput | Check data flow rates and backpressure |

## Connector Types

| Category | Examples |
|----------|---------|
| Database sources | PostgreSQL, MySQL, Oracle, SQL Server |
| Cloud storage | S3, GCS, Azure Blob |
| Streaming | Kafka, Kinesis |
| SaaS | Salesforce, ServiceNow |

## Constraints

- OpenFlow runs within Snowflake's managed NiFi environment
- Connector creation requires appropriate roles and network access
- All configurations stored within the Snowflake account

## Anti-patterns

| Pattern | Why It Fails | Instead |
|---------|-------------|---------|
| Using OpenFlow for simple S3 loads | Overhead of connector management | Use stages + `COPY INTO` or Snowpipe |
| Ignoring backpressure warnings | Data loss or OOM errors | Monitor queue sizes and adjust flow rate |

---

## Related Skills

If the user's request also involves these concerns, invoke the corresponding skill:

| Concern | Skill to Invoke | Example |
|---------|----------------|---------|
| Classifying PII or creating masking policies | `data-security` | "Build a pipeline and secure the sensitive data" |
| Building a dashboard or deploying an app | `app-deployment` | "Build a pipeline and create a dashboard" |
| Multi-domain workflow (2+ concerns) | `standard-router` | "Pipeline + masking + dashboard" — invoke router first for correct ordering |

**Execution order for multi-domain workflows:** data-transformation → data-security → app-deployment
