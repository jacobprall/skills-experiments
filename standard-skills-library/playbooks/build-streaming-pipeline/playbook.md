---
type: playbook
name: build-streaming-pipeline
domain: data-transformation
depends_on:
  - dynamic-tables
  - dbt-snowflake
  - openflow
---

# Build a Streaming Pipeline

Set up a continuously refreshing data pipeline — from ingestion through transformation to business-ready output.

## Objective

A multi-stage transformation pipeline where:
- External data is ingested via OpenFlow (if not already in Snowflake)
- Source data flows through staging, enrichment, and aggregation layers
- Each layer refreshes automatically based on target lag
- The final table is always within a configured freshness window

## Prerequisites

- A dedicated warehouse for refresh operations (cost isolation)
- `CREATE DYNAMIC TABLE` privilege on the target schema
- If external sources: OpenFlow connector configured (see `primitives/openflow`)

## Pre-execution Probes

Before starting, the agent should probe the environment:

```sql
-- Check if source tables exist and have change tracking
SHOW TABLES IN SCHEMA <db>.<schema>;

-- Check for existing dynamic tables that might conflict
SHOW DYNAMIC TABLES IN SCHEMA <db>.<target_schema>;

-- Check warehouse availability
SHOW WAREHOUSES LIKE '<warehouse_name>';

-- If external sources: check OpenFlow connector status
SHOW CONNECTIONS IN ACCOUNT;
```

These probes reveal whether source tables are ready, whether change tracking is enabled, and whether target schemas already have dynamic tables that might conflict.

## Steps

### Step 1: Identify sources and ensure data is in Snowflake

**This step branches based on `data_location` input.**

If data is already in Snowflake, enable change tracking on source tables:

Reference: `primitives/dynamic-tables`

```sql
SHOW TABLES LIKE '<source_table>' IN SCHEMA <db>.<schema>;
ALTER TABLE <db>.<schema>.<source_table> SET CHANGE_TRACKING = TRUE;
```

If data is coming from external sources, set up ingestion first:

Reference: `primitives/openflow`

Configure an OpenFlow connector for the external source. Once data lands in Snowflake tables, enable change tracking on those landing tables before proceeding.

**Checkpoint:**
  severity: review
  present: "Source readiness status — which tables exist, which have change tracking enabled, whether external connectors are configured"

Options: approve, modify (fix specific sources), abort, different-approach.

Expected errors:

| Pattern | Recovery | Retryable |
|---------|----------|-----------|
| `Insufficient privileges` | Grant ALTER on source tables | No — escalate |
| `does not exist` | Verify table/schema names with user | Yes |
| `Change tracking is not supported` | Table type doesn't support change tracking (e.g., external tables) | No — escalate |

### Step 2: Design the pipeline stages

Plan the transformation as a chain of dynamic tables. Each stage does one transformation:

Reference: `primitives/dynamic-tables`

| Stage | Purpose | Target Lag |
|-------|---------|------------|
| Staging | Clean and normalize raw data | `DOWNSTREAM` |
| Enrichment | Join with dimension tables | `DOWNSTREAM` |
| Aggregation | Final business-level summary | Time-based (e.g., `'30 minutes'`) |

Only the final (leaf) table gets a time-based target lag. All intermediate tables use `DOWNSTREAM` to avoid unnecessary refreshes.

**Checkpoint:**
  severity: review
  present: "Proposed pipeline design — stages, SQL logic per stage, target lag assignments"

Options: approve, modify (adjust stages or lag), abort, different-approach.

### Step 3: Create staging layer

Reference: `primitives/dynamic-tables`

```sql
CREATE OR REPLACE DYNAMIC TABLE <db>.staging.cleaned_orders
  TARGET_LAG = DOWNSTREAM
  WAREHOUSE = transform_wh
  REFRESH_MODE = INCREMENTAL
  AS
    SELECT
      order_id,
      TRIM(customer_id) AS customer_id,
      order_date,
      ROUND(total_amount, 2) AS total_amount,
      UPPER(status) AS status
    FROM <db>.raw.orders
    WHERE order_date IS NOT NULL;
```

**Compensation:**
```sql
DROP DYNAMIC TABLE IF EXISTS <db>.staging.cleaned_orders;
```

**Creates:**
- type: dynamic_table
  name: "<db>.staging.cleaned_orders"

Expected errors:

| Pattern | Recovery | Retryable |
|---------|----------|-----------|
| `Insufficient privileges` | Grant CREATE DYNAMIC TABLE on target schema | No — escalate |
| `already exists` | Use CREATE OR REPLACE (confirmed safe via pre-execution probe) | Yes |
| `Change tracking has not been enabled` | Run ALTER TABLE ... SET CHANGE_TRACKING = TRUE on source | Yes |

### Step 4: Create enrichment layer

Reference: `primitives/dynamic-tables`

```sql
CREATE OR REPLACE DYNAMIC TABLE <db>.staging.enriched_orders
  TARGET_LAG = DOWNSTREAM
  WAREHOUSE = transform_wh
  REFRESH_MODE = INCREMENTAL
  AS
    SELECT
      o.order_id,
      o.customer_id,
      c.customer_name,
      c.segment,
      o.order_date,
      o.total_amount,
      o.status
    FROM <db>.staging.cleaned_orders o
    JOIN <db>.raw.customers c ON o.customer_id = c.customer_id;
```

**Compensation:**
```sql
DROP DYNAMIC TABLE IF EXISTS <db>.staging.enriched_orders;
```

**Creates:**
- type: dynamic_table
  name: "<db>.staging.enriched_orders"

### Step 5: Create aggregation layer (leaf table)

Reference: `primitives/dynamic-tables`

```sql
CREATE OR REPLACE DYNAMIC TABLE <db>.analytics.order_summary
  TARGET_LAG = '30 minutes'
  WAREHOUSE = transform_wh
  REFRESH_MODE = INCREMENTAL
  AS
    SELECT
      segment,
      DATE_TRUNC('day', order_date) AS order_day,
      COUNT(*) AS order_count,
      SUM(total_amount) AS total_revenue,
      AVG(total_amount) AS avg_order_value
    FROM <db>.staging.enriched_orders
    GROUP BY segment, order_day;
```

**Compensation:**
```sql
DROP DYNAMIC TABLE IF EXISTS <db>.analytics.order_summary;
```

**Creates:**
- type: dynamic_table
  name: "<db>.analytics.order_summary"

### Step 6: Verify pipeline health

```sql
SELECT name, refresh_mode, target_lag, scheduling_state
FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLES())
ORDER BY name;

SELECT name, state, state_message, refresh_start_time, refresh_end_time
FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLE_REFRESH_HISTORY())
ORDER BY refresh_start_time DESC
LIMIT 20;
```

**Checkpoint:**
  severity: critical
  present: "Pipeline health — scheduling state, refresh history, any errors"

This checkpoint is `critical` because it confirms the pipeline is operational. Options: approve (pipeline complete), modify (adjust lag or fix errors), abort, different-approach.

## Anti-patterns

| Mistake | Impact | Instead |
|---------|--------|---------|
| Time-based lag on intermediate tables | Unnecessary refreshes, wasted credits | Use `DOWNSTREAM` on all non-leaf tables |
| One massive dynamic table doing everything | Full refresh every cycle, slow | Chain small tables, each doing one transform |
| Forgetting change tracking on source tables | Incremental refresh silently falls back to full | Enable change tracking before creating DTs |
| Using `SELECT *` in pipeline stages | Schema changes break the pipeline | Explicitly list columns |
| Skipping environment probes | Creates tables that conflict with existing ones | Always probe for existing dynamic tables first |
