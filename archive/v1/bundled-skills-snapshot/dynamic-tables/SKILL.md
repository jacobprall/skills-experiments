---
name: dynamic-tables
description: "**[REQUIRED]** Use for **ALL** Snowflake Dynamic Table operations: creating, optimizing, monitoring, and troubleshooting. This is the required entry point for any DT-related task. Triggers: dynamic table, data pipeline, incremental pipeline, DT pipeline, incremental refresh, target lag, UPSTREAM_FAILED, refresh failing, full refresh instead of incremental, DT health, create DT, debug DT."
---

# Dynamic Tables

Expert guidance for Snowflake Dynamic Tables: creating pipelines, configuring refreshes, monitoring health, troubleshooting issues, and optimizing performance.

## When to Use

Use this skill when users ask about:
- Creating dynamic tables with appropriate refresh modes
- Setting up dynamic table pipelines with proper target lag configuration
- Monitoring dynamic table health and refresh history
- Troubleshooting refresh failures or performance issues
- Optimizing refresh modes and query patterns
- Breaking large dynamic tables into smaller, more efficient ones

## ⚠️ MANDATORY INITIALIZATION

Before any workflow, you MUST:

### Step 1: Load Core References ✋ BLOCKING

**Load** the following reference documents:

1. **Load**: [references/sql-syntax.md](references/sql-syntax.md) - SQL command syntax
2. **Load**: [references/monitoring-functions.md](references/monitoring-functions.md) - INFORMATION_SCHEMA functions

**DO NOT PROCEED until you have loaded these references.**

### Step 2: Establish Connection Context ✋ BLOCKING

**Goal:** Identify the Snowflake connection to namespace diary entries.

1. **Ask user** for their Snowflake CLI connection name:
   - "Which Snowflake connection are you using? (e.g., the connection name from `snow` CLI)"
   
2. **Store connection name** for this session: `<connection>`

3. **Setup diary directory**:
   ```bash
   mkdir -p ~/.snowflake/cortex/memory/dynamic_tables/<connection>
   ```

4. **Check/update connection diary** at `~/.snowflake/cortex/memory/dynamic_tables/<connection>/_connection_diary.md`:
   - If exists: Read to understand account context, known DTs, warehouses
   - If new connection: Create with initial discovery (see Connection Diary section)

**DO NOT PROCEED until connection context is established.**

### Step 3: Check DT-Specific Diary

Before analyzing any specific dynamic table:

1. **Check** if DT diary entry exists: `~/.snowflake/cortex/memory/dynamic_tables/<connection>/<database>.<schema>.<dt_name>.md`
2. **If exists**: Read most recent entry to compare current vs historical metrics
3. **If not exists**: Note "First analysis of this DT - no historical baseline available"

---

## Intent Detection

When a user makes a request, detect their intent and route to the appropriate sub-skill:

### CREATE Intent

**Trigger phrases**: "create dynamic table", "set up DT", "new dynamic table", "define pipeline", "build DT"

**→ Load**: [create/SKILL.md](create/SKILL.md)

### MONITOR Intent

**Trigger phrases**: "check status", "refresh history", "is it healthy", "target lag", "how is my DT", "DT state"

**→ Load**: [monitor/SKILL.md](monitor/SKILL.md)

### TROUBLESHOOT Intent

**Trigger phrases**: "failing refresh", "not refreshing", "UPSTREAM_FAILED", "suspended", "full refresh instead of incremental", "refresh_mode_reason", "why is it failing", "DT broken", "errors"

**→ Load**: [troubleshoot/SKILL.md](troubleshoot/SKILL.md)

### OPTIMIZE Intent

**Trigger phrases**: "slow refresh", "make incremental", "improve performance", "immutability", "break into smaller", "decompose", "speed up", "reduce cost"

**→ Load**: [optimize/SKILL.md](optimize/SKILL.md)

### ALERTING Intent

**Trigger phrases**: "set up alerts", "alert on failure", "notify on refresh failure", "DT alerting", "event table alerts", "monitor failures", "email when DT fails"

**→ Load**: [dt-alerting/SKILL.md](dt-alerting/SKILL.md)

### PERMISSIONS Intent

**Trigger phrases**: "insufficient privileges", "permission denied", "privilege error", "DT permissions", "ownership transfer", "can't refresh", "access denied", "masking policy error"

**→ Load**: [permissions/SKILL.md](permissions/SKILL.md)

### TASK-TO-DT Intent

**Trigger phrases**: "convert tasks", "migrate from tasks", "replace stream and task", "task to DT", "streams and tasks to dynamic table", "modernize pipeline"

**→ Load**: [task-to-dt/SKILL.md](task-to-dt/SKILL.md)

---

## Workflow Decision Tree

```
Start Session
    ↓
MANDATORY: Load reference documents (sql-syntax.md, monitoring-functions.md)
    ↓
MANDATORY: Establish connection context (get connection name, setup diary)
    ↓
Check/update connection diary (discovered DTs, warehouses, account info)
    ↓
Check DT-specific diary for historical context (if specific DT mentioned)
    ↓
Detect User Intent
    ↓
    ├─→ CREATE → Load create/SKILL.md
    │   (Triggers: "create dynamic table", "new DT", "set up pipeline")
    │
    ├─→ MONITOR → Load monitor/SKILL.md
    │   (Triggers: "check status", "is it healthy", "refresh history")
    │
    ├─→ TROUBLESHOOT → Load troubleshoot/SKILL.md
    │   (Triggers: "failing", "not refreshing", "UPSTREAM_FAILED", "suspended")
    │
    ├─→ OPTIMIZE → Load optimize/SKILL.md
    │   (Triggers: "slow", "improve", "decompose", "make incremental")
    │
    ├─→ ALERTING → Load dt-alerting/SKILL.md
    │   (Triggers: "set up alerts", "notify on failure", "event table alerts")
    │
    ├─→ PERMISSIONS → Load permissions/SKILL.md
    │   (Triggers: "insufficient privileges", "permission denied", "ownership")
    │
    └─→ TASK-TO-DT → Load task-to-dt/SKILL.md
        (Triggers: "convert tasks", "migrate tasks", "replace stream and task")
```

---

## Sub-Skills

| Sub-Skill | Purpose | When to Load |
|-----------|---------|--------------|
| [create/SKILL.md](create/SKILL.md) | Create new dynamic tables | CREATE intent |
| [monitor/SKILL.md](monitor/SKILL.md) | Health checks and status monitoring | MONITOR intent |
| [troubleshoot/SKILL.md](troubleshoot/SKILL.md) | Diagnose and fix issues | TROUBLESHOOT intent |
| [optimize/SKILL.md](optimize/SKILL.md) | Performance improvements | OPTIMIZE intent |
| [dt-alerting/SKILL.md](dt-alerting/SKILL.md) | Set up alerts for refresh failures | ALERTING intent |
| [permissions/SKILL.md](permissions/SKILL.md) | Troubleshoot privilege/permission issues | PERMISSIONS intent |
| [task-to-dt/SKILL.md](task-to-dt/SKILL.md) | Convert streams+tasks pipelines to DTs | TASK-TO-DT intent |

---

## Quick Diagnostic Queries

For immediate assessment before routing:

```sql
-- Quick health check for all DTs in schema
SELECT name, scheduling_state, last_completed_refresh_state, 
       refresh_mode, time_within_target_lag_ratio
FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLES())
ORDER BY name;

-- Check for any errors
SELECT name, state, state_message, refresh_action
FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLE_REFRESH_HISTORY(
  NAME_PREFIX => '<database>.<schema>', ERROR_ONLY => TRUE
))
ORDER BY refresh_start_time DESC
LIMIT 5;
```

---

## Important Constraints

### 1. Incremental DTs cannot depend on Full refresh DTs

Dynamic tables in incremental mode cannot depend on full refresh mode dynamic tables.

```sql
-- ❌ BREAKS: dt_final is INCREMENTAL but depends on dt_upstream which is FULL
CREATE DYNAMIC TABLE dt_upstream
  TARGET_LAG = DOWNSTREAM
  REFRESH_MODE = FULL  -- This DT uses FULL refresh
  AS SELECT * FROM source_table;

CREATE DYNAMIC TABLE dt_final
  TARGET_LAG = '5 minutes'
  REFRESH_MODE = INCREMENTAL  -- ERROR: Cannot be INCREMENTAL if upstream is FULL
  AS SELECT * FROM dt_upstream;
```

### 2. Target lag cannot be shorter than upstream's lag

```sql
-- ❌ BREAKS: dt_final has 1 minute lag but dt_upstream has 10 minutes
CREATE DYNAMIC TABLE dt_upstream
  TARGET_LAG = '10 minutes'  -- 10 minute lag
  AS SELECT * FROM source_table;

CREATE DYNAMIC TABLE dt_final
  TARGET_LAG = '1 minute'  -- ERROR: Cannot be fresher than upstream (10 min)
  AS SELECT * FROM dt_upstream;
```

### 3. Change tracking must remain enabled on base objects

```sql
-- ❌ BREAKS: Disabling change tracking after DT creation
CREATE DYNAMIC TABLE my_dt AS SELECT * FROM base_table;

-- Later...
ALTER TABLE base_table SET CHANGE_TRACKING = FALSE;  -- ERROR: DT refreshes will fail
```

### 4. `SELECT *` fails on schema changes

```sql
-- ❌ BREAKS: Using SELECT * then adding a column to source
CREATE DYNAMIC TABLE my_dt AS SELECT * FROM source_table;

-- Later...
ALTER TABLE source_table ADD COLUMN new_col VARCHAR;  -- DT refresh will FAIL

-- ✅ FIX: Use explicit columns
CREATE DYNAMIC TABLE my_dt AS SELECT id, name, amount FROM source_table;
```

### 5. IMMUTABLE WHERE restrictions

```sql
-- ❌ BREAKS: Subquery in IMMUTABLE WHERE
CREATE DYNAMIC TABLE my_dt
  IMMUTABLE WHERE (id IN (SELECT id FROM archived_ids))  -- ERROR: No subqueries
  AS SELECT * FROM source_table;

-- ❌ BREAKS: UDF in IMMUTABLE WHERE
CREATE DYNAMIC TABLE my_dt
  IMMUTABLE WHERE (my_custom_udf(status) = TRUE)  -- ERROR: No UDFs
  AS SELECT * FROM source_table;

-- ❌ BREAKS: Non-deterministic function (except timestamps)
CREATE DYNAMIC TABLE my_dt
  IMMUTABLE WHERE (RANDOM() < 0.5)  -- ERROR: Non-deterministic
  AS SELECT * FROM source_table;

-- ✅ OK: Timestamp functions are allowed
CREATE DYNAMIC TABLE my_dt
  IMMUTABLE WHERE (created_at < CURRENT_TIMESTAMP() - INTERVAL '7 days')
  AS SELECT * FROM source_table;
```

---

## Stopping Points Summary

All sub-skills follow this philosophy: **NO changes without explicit user approval.**

- **READ-ONLY queries**: Can run freely (diagnostics, monitoring)
- **ANY mutation**: Requires stopping point and user approval

See individual sub-skills for specific stopping points.

---

## Diary System

This skill maintains a two-level diary system, namespaced by Snowflake connection:

### Directory Structure

```
~/.snowflake/cortex/memory/dynamic_tables/
├── <connection_name>/
│   ├── _connection_diary.md              # Connection-level diary
│   ├── <DATABASE>.<SCHEMA>.<DT_NAME>.md  # Per-DT diary
│   └── ...
├── <another_connection>/
│   └── ...
```

### Connection Diary (`_connection_diary.md`)

**Location**: `~/.snowflake/cortex/memory/dynamic_tables/<connection>/_connection_diary.md`

**Purpose**: Track account-level context, discovered resources, session history.

**Template**:
```markdown
# Connection: <connection_name>

## Account Metadata
- **Account**: <account_identifier>
- **Region**: <cloud_region>
- **User**: <username>
- **Default Role**: <role>
- **First Connected**: <timestamp>
- **Last Session**: <timestamp>

---

## Discovered Dynamic Tables

| Database.Schema.Name | Refresh Mode | Target Lag | Status | Last Checked |
|---------------------|--------------|------------|--------|--------------|
| DB.SCHEMA.DT_1 | INCREMENTAL | 5 min | ACTIVE | 2026-01-08 |
| DB.SCHEMA.DT_2 | FULL | 1 hour | SUSPENDED | 2026-01-07 |

---

## Warehouses

| Warehouse | Size | Used by DTs | Notes |
|-----------|------|-------------|-------|
| COMPUTE_WH | X-SMALL | DT_1, DT_2 | Shared warehouse |
| DT_DEDICATED_WH | MEDIUM | DT_3 | Dedicated for large DT |

---

## Session History

### Session: 2026-01-08T14:30:00Z
- **Intent**: Monitor DT health
- **DTs Analyzed**: DB.SCHEMA.DT_1, DB.SCHEMA.DT_2
- **Actions Taken**: None (read-only)
- **Findings**: DT_2 suspended due to upstream failure
- **Follow-up**: Troubleshoot DT_2 upstream

### Session: 2026-01-07T10:00:00Z
- **Intent**: Create new pipeline
- **DTs Created**: DB.SCHEMA.DT_3
- **Notes**: Set up 3-stage pipeline with DOWNSTREAM intermediates

---

## Cross-DT Recommendations

- Consider consolidating DT_1 and DT_2 into single pipeline
- COMPUTE_WH may be undersized for current DT workload
- Enable change tracking on RAW.EVENTS table for future DTs

---

## Notes

- <general observations about this account's DT usage>
```

**Update connection diary**:
- On first session: Run discovery queries, populate metadata
- Each session: Add session history entry
- When discovering new DTs: Add to inventory table
- When finding cross-DT patterns: Add to recommendations

**Discovery queries for new connections**:
```sql
-- Get account info
SELECT CURRENT_ACCOUNT(), CURRENT_REGION(), CURRENT_USER(), CURRENT_ROLE();

-- Discover all dynamic tables
SELECT database_name, schema_name, name, refresh_mode, 
       target_lag_sec, scheduling_state
FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLES())
ORDER BY database_name, schema_name, name;

-- List warehouses
SHOW WAREHOUSES;
```

### Per-DT Diary (`<DATABASE>.<SCHEMA>.<DT_NAME>.md`)

**Location**: `~/.snowflake/cortex/memory/dynamic_tables/<connection>/<DATABASE>.<SCHEMA>.<DT_NAME>.md`

**Purpose**: Track individual DT metrics, troubleshooting history, optimizations.

**Usage**: Each sub-skill reads/writes entries as appropriate. Compare current vs historical state.

When revisiting a DT, compare current state to historical baseline and highlight significant changes.

