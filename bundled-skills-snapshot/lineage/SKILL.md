---
name: lineage
description: "Analyze data lineage and dependencies in Snowflake. Use for: impact analysis, root cause debugging, data discovery, column-level tracing. Triggers: 'what depends on', 'what breaks', 'where does this come from', 'is this trustworthy', 'column lineage'."
---

# Lineage & Impact Analysis

## When to Use/Load

This skill activates when users need to:
- **Assess impact** of changes to tables/columns (downstream analysis)
- **Debug data issues** by tracing sources (upstream/root cause)
- **Discover and verify** trusted datasets (provenance)
- **Trace column-level** dependencies and transformations

**Trigger indicators:** Questions about dependencies, lineage, trust, impact, or data provenance.

## Purpose
Navigate the web of data dependencies to ensure reliability, transparency, and rapid recovery across the data ecosystem.

## How It Works

1. **User provides DATABASE.SCHEMA.TABLE** (e.g., "ANALYTICS_DB.REPORTING.REVENUE_SUMMARY")
2. **Agent identifies workflow** based on trigger phrases and other context
3. **Agent reads workflow file** from `workflows/` directory
4. **Agent executes template** with placeholders replaced
5. **Agent presents clean results** formatted per workflow guidelines

**Execution Approach:** Lineage queries are read-only analysis operations. Execute immediately without confirmation since they don't modify data or objects. If executing a recursive SQL query, notify the user that the analysis may take a while due to the complexity of the query.

---

## The 4 Workflows

### 1. Impact Analysis (Downstream)
**File:** `workflows/impact-analysis.md`
**Question:** *"If I change this, what breaks?"*
**Triggers:** "impact analysis", "what depends on this", "what will break", "downstream", "who uses this"
**Templates:** `impact-analysis.sql`, `impact-analysis-multi-level.sql`
**Output:** Downstream objects with risk tiers, usage frequency, affected users

**Snowflake APIs Used:**
- `SNOWFLAKE.ACCOUNT_USAGE.OBJECT_DEPENDENCIES` - Static dependency graph
- `SNOWFLAKE.ACCOUNT_USAGE.ACCESS_HISTORY` - Actual usage patterns
- `SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY` - User attribution

### 2. Root Cause Analysis (Upstream)
**File:** `workflows/root-cause-analysis.md`
**Question:** *"Why is this number wrong?"*
**Triggers:** "root cause", "why is this wrong", "trace upstream", "where does this come from", "debug"
**Templates:** `root-cause-analysis.sql`, `change-detection.sql`
**Output:** Upstream lineage, recent changes, divergence points

**Snowflake APIs Used:**
- `SNOWFLAKE.ACCOUNT_USAGE.OBJECT_DEPENDENCIES` - Upstream objects
- `SNOWFLAKE.ACCOUNT_USAGE.ACCESS_HISTORY` - Data flow patterns
- `SNOWFLAKE.ACCOUNT_USAGE.TABLES` / `COLUMNS` - Schema change detection
- `SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY` - Recent modifications

### 3. Data Discovery & Trust (Provenance)
**File:** `workflows/data-discovery.md`
**Question:** *"Where did this come from and is it the right tool for the job?"*
**Triggers:** "is this trustworthy", "provenance", "recommend dataset", "which table should I use", "verify source"
**Templates:** `data-discovery.sql`, `provenance-verification.sql`
**Output:** Full lineage path, usage statistics, trust indicators

**Snowflake APIs Used:**
- `SNOWFLAKE.ACCOUNT_USAGE.OBJECT_DEPENDENCIES` - Full dependency chain
- `SNOWFLAKE.ACCOUNT_USAGE.ACCESS_HISTORY` - Usage patterns
- `SNOWFLAKE.ACCOUNT_USAGE.TABLES` - Object metadata
- `SNOWFLAKE.ACCOUNT_USAGE.TABLE_STORAGE_METRICS` - Data freshness

### 4. Column-Level Lineage
**File:** `workflows/column-lineage.md`
**Question:** *"What uses this column?" / "Where does this column come from?"*
**Triggers:** "column lineage", "what uses [column]", "where does [column] come from", "trace column", "column impact", "column source"
**Templates:** `column-lineage-downstream.sql`, `column-lineage-upstream.sql`, `column-lineage-full.sql`, `column-change-detection.sql`
**Output:** Column-level dependencies, source columns, transformation paths

**Snowflake APIs Used:**
- `SNOWFLAKE.ACCOUNT_USAGE.ACCESS_HISTORY` - Column-level access patterns (columns array in base_objects_accessed/objects_modified)
- `SNOWFLAKE.ACCOUNT_USAGE.COLUMNS` - Column metadata and definitions
- `SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY` - DDL changes affecting columns

---

## Execution Rules

### Core Execution Flow:
1. **Extract object identifiers** from user message:
   - Table workflows: `DATABASE.SCHEMA.TABLE`
   - Column workflows: `DATABASE.SCHEMA.TABLE.COLUMN`
2. **Identify workflow** from trigger phrases and the object identifier → read workflow file from `workflows/`
3. **Read SQL template** specified in workflow file
4. **Build dynamic scoring** from `config/schema-patterns.yaml` (for trust/risk placeholders)
5. **Replace placeholders** with actual values
6. **Execute and format** results per workflow guidelines

### Placeholder Replacements:
- `<database>`, `<schema>`, `<table>`, `<column>` → actual object names
- `/* SCHEMA_TRUST_SCORING:column */` → dynamic CASE statement from config
- `/* SCHEMA_TRUST_TIER:column */` → dynamic tier name CASE statement  
- `/* SCHEMA_RISK_SCORING:column */` → dynamic risk CASE statement

### Key Principles:
- **Use templates exactly as written** - only replace placeholders
- **No confirmation prompts** for read-only lineage queries
- **Handle errors gracefully** - use fallback templates, provide clear messages
- **One workflow per request** - don't chain multiple analyses automatically

---

## Template Structure

All templates in `templates/` directory use these placeholders:
- `<database>` → Replace with actual database name
- `<schema>` → Replace with actual schema name
- `<table>` → Replace with actual table name
- `<column>` → Replace with actual column name (for column-level lineage)
- `/* SCHEMA_TRUST_SCORING:column_name */` → Dynamic CASE statement returning score (integer)
- `/* SCHEMA_TRUST_TIER:column_name */` → Dynamic CASE statement returning tier name (string)
- `/* SCHEMA_RISK_SCORING:column_name */` → Dynamic CASE statement returning 'CRITICAL' or NULL

**Example:**
```sql
-- Template:
WHERE REFERENCED_DATABASE = '<database>' 
  AND REFERENCED_SCHEMA = '<schema>' 
  AND REFERENCED_OBJECT_NAME = '<table>'

-- After replacement:
WHERE REFERENCED_DATABASE = 'ANALYTICS_DB' 
  AND REFERENCED_SCHEMA = 'REPORTING' 
  AND REFERENCED_OBJECT_NAME = 'SALES_SUMMARY'
```

---

## Dynamic Trust Scoring

Templates use dynamic placeholders for trust/risk scoring. See `reference/dynamic-trust-scoring.md` for complete documentation on:
- Placeholder syntax (`/* PLACEHOLDER_TYPE:column_name */`)
- Building CASE statements from `config/schema-patterns.yaml`
- Why dynamic scoring enables customer customization

---

## Error Handling & Fallback Strategy

**ACCOUNT_USAGE Latency Handling:**

ACCOUNT_USAGE views have 45min-3hr latency. For newly created objects:

1. **Primary:** Try `OBJECT_DEPENDENCIES` first
2. **Fallback 1:** Use `GET_DDL()` to parse view definitions for references
3. **Fallback 2:** Use `INFORMATION_SCHEMA.OBJECT_DEPENDENCIES` (current DB only)
4. **Fallback 3:** Query `TABLES` view for metadata (schema changes still visible)

**Fallback Templates:**
- `impact-analysis-fallback.sql` - DDL parsing for downstream deps
- `root-cause-ddl-fallback.sql` - DDL parsing for upstream lineage

**If template fails:**
1. Try fallback template (ACCOUNT_USAGE → GET_DDL → INFORMATION_SCHEMA)
2. Check ACCESS_HISTORY availability: `check-access-history.sql`
3. Check object existence: `check-object-exists.sql`
4. If object doesn't exist: "Object not found. Check the name and try again."
5. If no lineage data: "No lineage data available. Object may be new or unused."

**Common Issues:**
- "No ACCESS_HISTORY data" → Data is older than 365 days or not accessed
- "OBJECT_DEPENDENCIES empty" → Try GET_DDL() fallback for newly created objects
- "Insufficient privileges" → Need access to ACCOUNT_USAGE views

---

## Expected User Experience

### Example 1: Impact Analysis
**User:** "What will break if I change RAW_DB.SALES.ORDERS?"

**Agent (immediately):**
```
Impact Analysis: RAW_DB.SALES.ORDERS

═══════════════════════════════════════════════════════════════
CRITICAL RISK (2 objects)
═══════════════════════════════════════════════════════════════
1. ANALYTICS_DB.REPORTING.DAILY_REVENUE (Dynamic Table)
   Risk: CRITICAL | Refresh: Every 15 min | Users: 12 in last 7 days
   → Feeds 3 downstream objects including executive dashboard

2. FINANCE_DB.REPORTS.AR_AGING (View)
   Risk: CRITICAL | Queries: 89/day | Users: 5 in last 7 days
   → Used for month-end close process

═══════════════════════════════════════════════════════════════
MODERATE RISK (1 object)
═══════════════════════════════════════════════════════════════
3. STAGING_DB.TRANSFORM.ORDERS_ENRICHED (Table)
   Risk: MODERATE | Last updated: 2024-01-15 | Users: 2 in last 7 days

Summary: 3 downstream dependencies | 2 CRITICAL | 1 MODERATE
Affected Users: 15 unique users in last 7 days
```

### Example 2: Root Cause Analysis
**User:** "Why is ANALYTICS_DB.REPORTING.REVENUE wrong?"

**Agent (immediately):**
```
Root Cause Analysis: ANALYTICS_DB.REPORTING.REVENUE

═══════════════════════════════════════════════════════════════
UPSTREAM LINEAGE (3 levels)
═══════════════════════════════════════════════════════════════
Level 1: STAGING_DB.CLEAN.ORDERS_FACT
Level 2: RAW_DB.INGEST.ORDERS, RAW_DB.INGEST.PRODUCTS
Level 3: External Stage (S3://data-lake/orders/)

═══════════════════════════════════════════════════════════════
RECENT CHANGES DETECTED
═══════════════════════════════════════════════════════════════
⚠️  RAW_DB.INGEST.ORDERS - Schema changed 2 hours ago
    Change: Column DISCOUNT_PCT type changed NUMBER(5,2) → NUMBER(10,4)
    Changed by: ETL_SERVICE_USER

⚠️  STAGING_DB.CLEAN.ORDERS_FACT - Data modified 1 hour ago
    Rows affected: 15,234 rows updated
    Query: MERGE statement by TRANSFORM_TASK

Most Likely Cause: Schema change in RAW_DB.INGEST.ORDERS
Recommendation: Verify DISCOUNT_PCT handling in downstream transforms
```

### Example 3: Data Discovery
**User:** "Which table should I use for customer revenue analysis?"

**Agent (immediately):**
```
Data Discovery: Customer Revenue Analysis

RECOMMENDED:
1. ANALYTICS_DB.CURATED.CUSTOMER_REVENUE_SUMMARY ⭐ Best Match
   Trust Score: 95% | Updated hourly | Users: 45/week
   Why: Pre-aggregated customer revenue with standard dimensions
   Provenance: RAW.ORDERS → STAGING.ORDERS_FACT → This table

Not Recommended:
- RAW_DB.ORDERS (Trust: 60%) - Raw data, requires transformation
- SANDBOX_DB.*.* - Development/test data
```

### Example 4: Column-Level Lineage
**User:** "What uses the AMOUNT column in RAW_DB.SALES.ORDERS?"

**Agent (immediately):**
```
Column Impact Analysis: RAW_DB.SALES.ORDERS.AMOUNT

═══════════════════════════════════════════════════════════════
DOWNSTREAM COLUMNS (8 columns use this data)
═══════════════════════════════════════════════════════════════

CRITICAL IMPACT:
1. ANALYTICS_DB.REPORTING.REVENUE_SUMMARY.TOTAL_REVENUE
   Impact: CRITICAL | Queries: 89/day | Confidence: HIGH
   Transformation: SUM(AMOUNT) aggregation
   
2. FINANCE_DB.REPORTS.AR_AGING.OUTSTANDING_AMOUNT
   Impact: CRITICAL | Queries: 45/day | Confidence: HIGH
   Transformation: Direct reference with filters

HIGH IMPACT:
3. STAGING_DB.TRANSFORM.ORDERS_ENRICHED.NET_AMOUNT
   Impact: HIGH | Queries: 23/day | Confidence: HIGH
   Transformation: AMOUNT * (1 - DISCOUNT_PCT/100)

MODERATE IMPACT:
4. ANALYTICS_DB.MARTS.CUSTOMER_360.LIFETIME_VALUE
   Impact: MEDIUM | Queries: 12/day | Confidence: MEDIUM

Summary: 8 downstream columns | 2 CRITICAL | 1 HIGH | 5 MEDIUM
Recommendation: Coordinate with Finance team before changing
```

### Example 5: Column Source Tracing
**User:** "Where does ANALYTICS_DB.REPORTS.REVENUE.TOTAL_SALES come from?"

**Agent (immediately):**
```
Column Source Analysis: ANALYTICS_DB.REPORTS.REVENUE.TOTAL_SALES

═══════════════════════════════════════════════════════════════
UPSTREAM SOURCES (traced 3 levels)
═══════════════════════════════════════════════════════════════

Level 1 (Direct Source):
  STAGING_DB.TRANSFORM.ORDERS_AGG.REVENUE_SUM
  Confidence: HIGH | Last seen: 2 hours ago
  Transformation: Renamed column

Level 2:
  RAW_DB.INGEST.ORDERS.AMOUNT
  Confidence: HIGH | Source tier: RAW
  Transformation: SUM() aggregation

Level 3 (Origin):
  @RAW_DB.STAGES.S3_ORDERS/orders.csv
  Confidence: MEDIUM | Source tier: EXTERNAL

Complete Path:
S3_ORDERS → ORDERS.AMOUNT → ORDERS_AGG.REVENUE_SUM → REVENUE.TOTAL_SALES
```

---

## Summary Table

| Workflow | Direction | Primary Goal | Key Stakeholder |
|:---------|:----------|:-------------|:----------------|
| **Impact Analysis** | Downstream | Risk Mitigation | Data Engineers / Ops |
| **Root Cause** | Upstream | Troubleshooting | Analysts / Analytics Engineers |
| **Trust & Discovery** | Full Path | Data Literacy | Business Users / Platform Owners |
| **Column Lineage** | Both | Field-Level Tracing | Data Engineers / Analysts |

---

## Workflow Selection Logic

| User Says | Workflow | Template |
|-----------|----------|----------|
| "What will break if I change [table]?" | Impact Analysis | `impact-analysis.sql` |
| "What depends on [table]?" | Impact Analysis | `impact-analysis.sql` |
| "Why is this number wrong?" | Root Cause Analysis | `root-cause-analysis.sql` |
| "Where does [table] come from?" | Root Cause Analysis | `root-cause-analysis.sql` |
| "Is [table] trustworthy?" | Data Discovery | `data-discovery.sql` |
| "Which table should I use for [topic]?" | Data Discovery | `data-discovery.sql` |
| "What uses the [column] column?" | Column Lineage | `column-lineage-downstream.sql` |
| "Where does [column] come from?" | Column Lineage | `column-lineage-upstream.sql` |
| "Full lineage for [column]" | Column Lineage | `column-lineage-full.sql` |
| "Has [column] changed?" | Column Lineage | `column-change-detection.sql` |

---

## Snowflake APIs Reference

See `reference/snowflake-apis.md` for complete documentation on:
- ACCOUNT_USAGE views and their latencies
- Privilege requirements (`GRANT IMPORTED PRIVILEGES`)
- Performance optimization tips

---

## Success Criteria

- User gets answer in **one response**
- Risk tiers clearly communicated (Impact Analysis)
- Recent changes highlighted (Root Cause)
- Trust indicators provided (Discovery)
- No SQL errors shown
- No unnecessary questions
- Clean, actionable results

---

## Stopping Points

Lineage queries are **read-only operations** that don't modify data or schema. Execute immediately without waiting for confirmation.

### ⚠️ MANDATORY STOPPING POINTS

**STOP and ask user if:**
1. **Ambiguous object reference** - Missing or unclear database/schema/table/column name
   - Example: User says "check lineage" without specifying which table
   - Action: Ask "Which table would you like to analyze?"

2. **User explicitly requests review** - "Show me the query first" or "Let me review before running"
   - Action: Present the query and wait for confirmation

3. **Query returns no results** - No lineage data found
   - Action: Explain possible reasons (new object, no access, insufficient privileges) and ask if they want to try a different approach

### ✅ NO STOPPING REQUIRED

**Execute immediately without confirmation:**
- Any SELECT query on `SNOWFLAKE.ACCOUNT_USAGE` views
- Any SELECT query on `INFORMATION_SCHEMA` views
- Parsing DDL with `GET_DDL()` function
- Reading configuration files from `config/`

**Rationale:** These are read-only operations that don't modify data, schema, or access controls.

---

## Production Configuration

**Schema Pattern Configuration (Extensible):**

Trust and risk scoring patterns are defined in `config/schema-patterns.yaml`. This file is read dynamically at runtime, allowing easy customization without modifying SQL templates.

**File:** `config/schema-patterns.yaml`

```yaml
trust_tiers:
  PRODUCTION:
    score: 100
    patterns:
      - "%ANALYTICS%"
      - "%CURATED%"
      # Add your production schema patterns here
      
  STAGING:
    score: 60
    patterns:
      - "%STAG%"
      # Add your staging schema patterns here
      
  RAW:
    score: 40
    patterns:
      - "%RAW%"
      # Add your raw data schema patterns here
      
  UNTRUSTED:
    score: 20
    patterns:
      - "%SANDBOX%"
      - "%TEST%"
      # Add your dev/test schema patterns here

default:
  score: 50
  tier: "UNKNOWN"

risk_critical_patterns:
  - "%FINANCE%"
  - "%REVENUE%"
  # Add schemas that are critical to flag
```

**Customization:** Edit `config/schema-patterns.yaml` using SQL LIKE syntax (% = wildcard, case-insensitive). Example: `%ANALYTICS%` matches ANALYTICS, PROD_ANALYTICS, ANALYTICS_V2.

**Recursive Depth:** Default 3 levels, configurable in templates (`WHERE ul.level < 3`).

**Retention:** ACCESS_HISTORY/QUERY_HISTORY: 365 days; OBJECT_DEPENDENCIES: indefinite (latency on new objects).

---

## Known Limitations

| Limitation | Impact | Workaround |
|------------|--------|------------|
| ACCOUNT_USAGE latency (45min-3hr) | New objects missing from lineage | Use GET_DDL() fallback templates |
| Column lineage depends on ACCESS_HISTORY | Not all queries expose column details | Confidence scores indicate reliability |
| Single account scope | Cross-account sharing not covered | Query each account separately |
| View DDL parsing | May miss dynamic SQL references | Review complex views manually |
| Recursive depth limit | Deep chains truncated at 3-4 levels | Increase in templates if needed |
| Column lineage 90-day lookback | Older transformations not captured | Extend time range in templates |
