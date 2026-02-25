---
name: dynamic-tables-monitor
description: "Monitor health and status of Snowflake dynamic tables"
parent_skill: dynamic-tables
---

# Monitor Dynamic Tables

Workflow for checking health, status, and performance of dynamic tables. This is a READ-ONLY workflow.

## When to Load

Main skill routes here when user wants to:
- Check dynamic table status or health
- View refresh history
- Understand pipeline dependencies
- Assess target lag compliance

---

## Workflow

### Step 1: Check Diary for Historical Context

**Goal:** Load previous analysis if available

**Actions:**

1. **Check connection diary** at `~/.snowflake/cortex/memory/dynamic_tables/<connection>/_connection_diary.md`:
   - Review known DTs in this account
   - Check if target DT is already in inventory

2. **Check DT diary** at `~/.snowflake/cortex/memory/dynamic_tables/<connection>/<database>.<schema>.<dt_name>.md`:
   - If exists: Read most recent entry, note previous metrics for comparison
   - If not exists: Note "First analysis of this DT - no historical baseline available"

---

### Step 2: Query Overall State

**Goal:** Get current health status of dynamic table(s)

**Actions:**

1. **For all DTs in a schema**:
   ```sql
   SELECT 
     name, 
     scheduling_state,
     last_completed_refresh_state,
     refresh_mode,
     target_lag_sec,
     maximum_lag_sec,
     time_within_target_lag_ratio
   FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLES())
   ORDER BY name;
   ```

2. **For a specific DT**:
   ```sql
   SELECT 
     name,
     scheduling_state,
     last_completed_refresh_state,
     refresh_mode,
     refresh_mode_reason,
     target_lag_sec,
     maximum_lag_sec,
     time_within_target_lag_ratio
   FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLES(name=>'<dynamic_table_name>'));
   ```

3. **Interpret key metrics**:

   | Metric | Healthy Value | Concern |
   |--------|--------------|---------|
   | `scheduling_state` | ACTIVE | SUSPENDED = needs attention |
   | `last_completed_refresh_state` | SUCCESS | FAILED, UPSTREAM_FAILED = issue |
   | `time_within_target_lag_ratio` | > 0.95 | < 0.90 = not meeting freshness |
   | `refresh_mode` | INCREMENTAL | FULL = may need optimization |

---

### Step 3: Check Refresh History

**Goal:** Understand recent refresh behavior

**Actions:**

1. **Get recent refresh history**:
   ```sql
   SELECT 
     name,
     data_timestamp,
     refresh_start_time,
     refresh_end_time,
     DATEDIFF('second', refresh_start_time, refresh_end_time) as duration_sec,
     state,
     state_code,
     state_message,
     refresh_action,
     refresh_trigger,
     query_id
   FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLE_REFRESH_HISTORY(
     NAME_PREFIX => '<database>.<schema>'
   ))
   ORDER BY refresh_start_time DESC
   LIMIT 10;
   ```

2. **Check for errors only** (last 7 days):
   ```sql
   SELECT 
     name, 
     refresh_start_time,
     state, 
     state_code,
     state_message,
     refresh_action
   FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLE_REFRESH_HISTORY(
     NAME_PREFIX => '<database>.<schema>',
     ERROR_ONLY => TRUE
   ))
   WHERE refresh_start_time > DATEADD('day', -7, CURRENT_TIMESTAMP())
   ORDER BY refresh_start_time DESC
   LIMIT 20;
   ```

3. **Calculate refresh statistics** (last 7 days):
   ```sql
   SELECT 
     name,
     COUNT(*) as total_refreshes,
     AVG(DATEDIFF('second', refresh_start_time, refresh_end_time)) as avg_duration_sec,
     MAX(DATEDIFF('second', refresh_start_time, refresh_end_time)) as max_duration_sec,
     COUNT_IF(refresh_action = 'INCREMENTAL') as incremental_count,
     COUNT_IF(refresh_action = 'FULL') as full_count,
     COUNT_IF(state = 'FAILED') as failed_count
   FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLE_REFRESH_HISTORY(name=>'<dt_name>'))
   WHERE refresh_start_time > DATEADD('day', -7, CURRENT_TIMESTAMP())
   GROUP BY name;
   ```

---

### Step 4: View Pipeline Dependencies

**Goal:** Understand DAG structure and upstream/downstream relationships

**Actions:**

1. **Get dependency graph**:
   ```sql
   SELECT 
     name,
     inputs,
     scheduling_state,
     target_lag_type,
     target_lag_sec
   FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLE_GRAPH_HISTORY())
   WHERE name = '<dynamic_table_name>'
      OR ARRAY_CONTAINS('<dynamic_table_name>'::VARIANT, inputs);
   ```

2. **Interpret dependencies**:
   - `inputs` array shows upstream tables
   - Tables with `target_lag_type = 'DOWNSTREAM'` refresh when downstream needs them
   - Look for upstream tables with issues that could affect downstream

---

### Step 5: Analyze Refresh Query Performance

**Goal:** Understand compute usage and identify potential bottlenecks

**Actions:**

1. **Get refresh query details** (using query_id from refresh history):
   ```sql
   SELECT 
     query_id,
     query_text,
     total_elapsed_time / 1000 as elapsed_sec,
     bytes_scanned / 1024 / 1024 / 1024 as gb_scanned,
     rows_produced,
     partitions_scanned,
     partitions_total,
     warehouse_name,
     warehouse_size
   FROM TABLE(INFORMATION_SCHEMA.QUERY_HISTORY())
   WHERE query_type = 'DYNAMIC_TABLE_REFRESH'
     AND query_text ILIKE '%<dt_name>%'
   ORDER BY start_time DESC
   LIMIT 5;
   ```

2. **For deeper analysis**, get query operator stats:
   ```sql
   SELECT * FROM TABLE(GET_QUERY_OPERATOR_STATS('<query_id>'))
   ORDER BY execution_time DESC
   LIMIT 10;
   ```

---

### Step 6: Compare to Historical Baseline

**Goal:** Identify changes from previous analysis

**Actions:**

1. **If diary entry exists**, compare:
   - Refresh duration: increased/decreased?
   - `time_within_target_lag_ratio`: improved/degraded?
   - Refresh mode: changed from INCREMENTAL to FULL?
   - Error frequency: more/fewer failures?

2. **Highlight significant changes**:
   - "Refresh time increased from 45s → 120s (167% increase)"
   - "time_within_target_lag_ratio dropped from 0.98 → 0.72"
   - "Refresh mode changed from INCREMENTAL → FULL"

---

### Step 7: Write Diary Entries

**Goal:** Record current state for future comparison

**Actions:**

1. **Write/append DT diary entry** to `~/.snowflake/cortex/memory/dynamic_tables/<connection>/<database>.<schema>.<dt_name>.md`:

   ```markdown
   ## Entry: <CURRENT_TIMESTAMP>

   ### Configuration
   - Refresh Mode: <refresh_mode>
   - Target Lag: <target_lag_sec> seconds
   - Warehouse: <warehouse_name>

   ### Health Metrics
   - scheduling_state: <value>
   - last_completed_refresh_state: <value>
   - time_within_target_lag_ratio: <value>
   - maximum_lag_sec: <value>

   ### Refresh Performance (last 7 days)
   - Total refreshes: <count>
   - Avg refresh time: <avg_sec>s
   - Max refresh time: <max_sec>s
   - Incremental refreshes: <count>
   - Full refreshes: <count>
   - Failed refreshes: <count>

   ### Notes
   - <any observations or recommendations>
   ```

2. **Update connection diary** at `~/.snowflake/cortex/memory/dynamic_tables/<connection>/_connection_diary.md`:
   - Update DT entry in "Discovered Dynamic Tables" with latest status
   - Add session history entry noting the health check
   - Add any cross-DT observations to recommendations

---

## Present Health Report

Summarize findings for user:

```
📊 Dynamic Table Health Report: <database>.<schema>.<dt_name>

Status: ✅ HEALTHY | ⚠️ WARNING | 🚨 CRITICAL

Configuration:
- Refresh Mode: INCREMENTAL
- Target Lag: 5 minutes
- Warehouse: COMPUTE_WH

Current Health:
- Scheduling State: ACTIVE ✅
- Last Refresh: SUCCESS ✅
- Target Lag Compliance: 98% ✅

Performance (last 7 days):
- Avg Refresh Time: 45s
- Incremental/Full Ratio: 10/0 ✅
- Failed Refreshes: 0 ✅

[If diary exists]
Changes Since Last Check (<previous_date>):
- Refresh time: 45s → 52s (+15%)
- Target lag compliance: 98% → 98% (stable)

Recommendations:
- <any issues or optimization opportunities>
```

---

## Stopping Points

This is a READ-ONLY workflow. No mandatory stopping points, but:
- Present findings clearly
- If issues found, offer to route to TROUBLESHOOT workflow
- If optimization opportunities found, offer to route to OPTIMIZE workflow

---

## Output

- Health report with key metrics
- Historical comparison (if diary exists)
- Updated diary entry
- Recommendations for next steps (if issues found)

