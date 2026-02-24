---
name: dynamic-tables-optimize
description: "Optimize Snowflake dynamic table performance and cost"
parent_skill: dynamic-tables
---

# Optimize Dynamic Tables

Workflow for improving dynamic table performance, converting to incremental refresh, decomposing large DTs, and applying immutability constraints.

## When to Load

Main skill routes here when user wants to:
- Speed up slow refreshes
- Convert full refresh to incremental
- Break large DT into smaller ones
- Reduce compute costs
- Apply immutability constraints

---

## Workflow

### Step 1: Check Diary for Performance History

**Goal:** Understand performance trends over time

**Actions:**

1. **Check connection diary** at `~/.snowflake/cortex/memory/dynamic_tables/<connection>/_connection_diary.md`:
   - Review warehouse usage across DTs
   - Check if similar optimizations were done on other DTs

2. **Check DT diary** at `~/.snowflake/cortex/memory/dynamic_tables/<connection>/<database>.<schema>.<dt_name>.md`:
   - Review historical refresh times
   - Identify when performance degraded
   - Note previous optimization attempts

3. **Write "BEFORE" entry** capturing current state before any changes

---

### Step 2: Analyze Current Configuration

**Goal:** Understand current DT setup

**Actions:**

1. **Get current configuration**:
   ```sql
   SELECT 
     name,
     refresh_mode,
     refresh_mode_reason,
     target_lag_sec,
     scheduling_state,
     warehouse_name
   FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLES(name=>'<dt_name>'));
   ```

2. **Get DT definition**:
   ```sql
   SELECT GET_DDL('DYNAMIC_TABLE', '<fully_qualified_name>');
   ```

3. **Check current refresh statistics** (last 7 days):
   ```sql
   SELECT 
     AVG(DATEDIFF('second', refresh_start_time, refresh_end_time)) as avg_duration_sec,
     MAX(DATEDIFF('second', refresh_start_time, refresh_end_time)) as max_duration_sec,
     PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY 
       DATEDIFF('second', refresh_start_time, refresh_end_time)) as p95_duration_sec,
     COUNT_IF(refresh_action = 'INCREMENTAL') as incremental_count,
     COUNT_IF(refresh_action = 'FULL') as full_count
   FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLE_REFRESH_HISTORY(name=>'<dt_name>'))
   WHERE refresh_start_time > DATEADD('day', -7, CURRENT_TIMESTAMP());
   ```

**⚠️ MANDATORY STOPPING POINT**: Present current configuration analysis.

---

### Step 3: Analyze Query Performance

**Goal:** Identify expensive operations in refresh query

**Actions:**

1. **Get recent refresh query_id**:
   ```sql
   SELECT query_id, refresh_start_time
   FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLE_REFRESH_HISTORY(name=>'<dt_name>'))
   WHERE state = 'SUCCESS'
   ORDER BY refresh_start_time DESC
   LIMIT 1;
   ```

2. **Analyze query operators**:
   ```sql
   SELECT 
     operator_id,
     operator_type,
     execution_time_ms,
     output_rows,
     input_rows,
     operator_statistics
   FROM TABLE(GET_QUERY_OPERATOR_STATS('<query_id>'))
   ORDER BY execution_time_ms DESC
   LIMIT 15;
   ```

3. **Identify bottlenecks**:
   - Look for operators taking >20% of total time
   - Check for expensive JOINs, aggregations, or table scans
   - Note operators that could be split into intermediate DTs

4. **Check warehouse utilization**:
   ```sql
   SELECT 
     query_id,
     warehouse_name,
     warehouse_size,
     total_elapsed_time / 1000 as elapsed_sec,
     bytes_scanned / 1024 / 1024 / 1024 as gb_scanned,
     credits_used_cloud_services
   FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
   WHERE query_type = 'DYNAMIC_TABLE_REFRESH'
     AND query_text ILIKE '%<dt_name>%'
   ORDER BY start_time DESC
   LIMIT 5;
   ```

**⚠️ MANDATORY STOPPING POINT**: Present query performance analysis.

---

### Step 4: Determine Optimization Strategy

**Goal:** Choose the best optimization approach

Based on analysis, determine which optimization(s) to apply:

| Issue | Optimization | Go To |
|-------|-------------|-------|
| Full refresh, query could be incremental | Convert to Incremental | Step 5A |
| Query too complex for single DT | Decompose DT | Step 5B |
| Historical data being reprocessed | Add Immutability Constraints | Step 5C |
| Warehouse too small | Increase Warehouse Size | Step 5D |
| Multiple optimizations needed | Apply in order: 5B → 5C → 5A → 5D |

**⚠️ MANDATORY STOPPING POINT**: Present optimization strategy for approval.

---

### Step 5A: Convert to Incremental Refresh

**Goal:** Restructure query to support incremental refresh

**Actions:**

1. **Load** [references/incremental-operators.md](../references/incremental-operators.md)

2. **Identify unsupported constructs** in current query:
   - Self outer join (same table on both sides) → Use intermediate DT to break self-reference
   - Outer join with GROUP BY subqueries on both sides → Materialize aggregations first
   - Outer join with non-equality predicate (e.g., `ON a.id > b.id`) → Restructure or accept FULL
   - EXCEPT/INTERSECT → Rewrite with LEFT ANTI JOIN
   - Complex window functions → Consider materializing in intermediate DT

3. **Generate modified query** with supported constructs

4. **Generate new CREATE statement**:
   ```sql
   CREATE OR REPLACE DYNAMIC TABLE <dt_name>
     TARGET_LAG = '<same_lag>'
     WAREHOUSE = <same_warehouse>
     REFRESH_MODE = INCREMENTAL
     AS
       <modified_query>;
   ```

**⚠️ MANDATORY STOPPING POINT**: Present modified query before executing.

---

### Step 5B: Decompose Dynamic Table

**Goal:** Break large DT into smaller, more efficient DTs

**Load** [references/dt-decomposition.md](../references/dt-decomposition.md) for detailed guidance.

**Actions:**

1. **Identify decomposition points** from query analysis:
   - Expensive JOINs → Materialize as intermediate DT
   - Multi-stage aggregations → Split into stages
   - Complex transformations → Break into steps

2. **Design intermediate DT pipeline**:
   ```
   Original: SourceA + SourceB + SourceC → Complex Query → FinalDT
   
   Decomposed:
   SourceA → IntermediateDT_1 (expensive join)
                     ↓
   SourceB →────────┘
                     ↓
   IntermediateDT_1 + SourceC → FinalDT (simpler query)
   ```

3. **For each intermediate DT**:
   ```sql
   CREATE DYNAMIC TABLE <intermediate_dt_name>
     TARGET_LAG = DOWNSTREAM  -- Key: use DOWNSTREAM for intermediates
     WAREHOUSE = <warehouse>
     REFRESH_MODE = INCREMENTAL
     AS
       <portion_of_original_query>;
   ```

4. **Recreate final DT** referencing intermediates:
   ```sql
   CREATE OR REPLACE DYNAMIC TABLE <final_dt_name>
     TARGET_LAG = '<original_lag>'
     WAREHOUSE = <warehouse>
     REFRESH_MODE = INCREMENTAL
     AS
       SELECT ... FROM <intermediate_dt_name> ...;
   ```

**⚠️ MANDATORY STOPPING POINT**: Present decomposition plan before creating any DTs.

**⚠️ MANDATORY STOPPING POINT**: Before creating each intermediate DT.

**⚠️ MANDATORY STOPPING POINT**: Before recreating final DT.

---

### Step 5C: Add Immutability Constraints

**Goal:** Prevent reprocessing of historical data

**Actions:**

1. **Identify immutability boundary**:
   - Which rows are historical and shouldn't change?
   - What timestamp column defines "historical"?

2. **Add immutability constraint**:
   ```sql
   ALTER DYNAMIC TABLE <dt_name> 
   ADD IMMUTABLE WHERE (timestamp_col < CURRENT_TIMESTAMP() - INTERVAL '1 day');
   ```

3. **For new DTs, include in CREATE**:
   ```sql
   CREATE DYNAMIC TABLE <dt_name>
     IMMUTABLE WHERE (timestamp_col < CURRENT_TIMESTAMP() - INTERVAL '1 day')
     TARGET_LAG = '<lag>'
     WAREHOUSE = <warehouse>
     AS <query>;
   ```

**Constraints on IMMUTABLE WHERE:**
- Cannot use subqueries
- Cannot use UDFs
- Can use timestamp functions (CURRENT_TIMESTAMP, etc.)

**⚠️ MANDATORY STOPPING POINT**: Present immutability constraint before applying.

---

### Step 5D: Increase Warehouse Size

**Goal:** Provide more compute for faster refreshes

**Actions:**

1. **Analyze current utilization**:
   - If query is CPU-bound, larger warehouse helps
   - If query is I/O-bound, may not help as much

2. **Recreate with larger warehouse**:
   ```sql
   CREATE OR REPLACE DYNAMIC TABLE <dt_name>
     TARGET_LAG = '<same_lag>'
     WAREHOUSE = <larger_warehouse>
     REFRESH_MODE = <same_mode>
     AS
       <same_query>;
   ```

**Alternative**: Use dedicated warehouse for DT refreshes to isolate costs.

**⚠️ MANDATORY STOPPING POINT**: Present warehouse change before executing.

---

### Step 6: Verify Optimization

**Goal:** Confirm optimization improved performance

**Actions:**

1. **Wait for several refresh cycles** (at least 3-5)

2. **Compare before/after metrics**:
   ```sql
   SELECT 
     AVG(DATEDIFF('second', refresh_start_time, refresh_end_time)) as avg_duration_sec,
     COUNT_IF(refresh_action = 'INCREMENTAL') as incremental_count,
     COUNT_IF(refresh_action = 'FULL') as full_count
   FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLE_REFRESH_HISTORY(name=>'<dt_name>'))
   WHERE refresh_start_time > DATEADD('hour', -1, CURRENT_TIMESTAMP());
   ```

3. **Check refresh mode**:
   ```sql
   SELECT refresh_mode, refresh_mode_reason
   FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLES(name=>'<dt_name>'));
   ```

**⚠️ MANDATORY STOPPING POINT**: Present verification results.

---

### Step 7: Write Diary Entries

**Goal:** Document optimization for future reference

**Actions:**

1. **Write "AFTER" DT diary entry** to `~/.snowflake/cortex/memory/dynamic_tables/<connection>/<database>.<schema>.<dt_name>.md`:

   ```markdown
   ## Entry: <CURRENT_TIMESTAMP> - OPTIMIZATION

   ### Before Optimization
   - Refresh Mode: <old_mode>
   - Avg Refresh Time: <old_time>s
   - Incremental/Full Ratio: <old_ratio>

   ### Optimization Applied
   - Type: <decomposition/immutability/incremental/warehouse>
   - Changes: <description>

   ### After Optimization
   - Refresh Mode: <new_mode>
   - Avg Refresh Time: <new_time>s
   - Incremental/Full Ratio: <new_ratio>

   ### Improvement
   - Refresh time: <old>s → <new>s (<X>% improvement)
   - Refresh mode: <FULL> → <INCREMENTAL>

   ### Notes
   - <any observations>
   ```

2. **Update connection diary** at `~/.snowflake/cortex/memory/dynamic_tables/<connection>/_connection_diary.md`:
   - Update DT entry in inventory (new refresh mode, performance)
   - Add session history entry noting the optimization
   - If decomposition created new DTs, add them to inventory
   - Add optimization pattern to cross-DT recommendations if applicable

---

## DT Decomposition Workflow Summary

```
Analyze Query Profile
    ↓
Identify Expensive Operations (>20% of query time)
    ↓
Design Intermediate DTs
    ↓
    ├─→ Expensive JOIN → Create intermediate DT with join result
    ├─→ Heavy Aggregation → Create intermediate DT with pre-aggregation
    └─→ Complex Transform → Create intermediate DT with partial transform
    ↓
Create Intermediate DTs (TARGET_LAG = DOWNSTREAM)
    ↓
Recreate Final DT referencing intermediates
    ↓
Verify Performance Improvement
```

---

## Stopping Points Summary

1. ✋ After analyzing current configuration
2. ✋ After running query performance analysis
3. ✋ After proposing optimization strategy
4. ✋ Before creating ANY intermediate dynamic table
5. ✋ Before adding/modifying immutability constraints
6. ✋ Before changing refresh mode or recreating DT
7. ✋ Before changing warehouse
8. ✋ After verification - confirm improvement

**Resume rule:** Only proceed after explicit user approval.

---

## Output

- Optimized DT configuration
- Before/after performance comparison
- Diary entry documenting changes and improvements
- Recommendations for ongoing optimization

