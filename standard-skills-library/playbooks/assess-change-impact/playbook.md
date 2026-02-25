---
type: playbook
name: assess-change-impact
domain: data-observability
depends_on:
  - lineage-queries
  - data-metric-functions
---

# Assess Change Impact

Before modifying a table, schema, or pipeline, understand downstream dependencies, usage patterns, affected users, and blast radius. Produce a risk assessment the user can act on.

## Objective

After completing this playbook, the user will have:

1. A complete list of downstream dependent objects (views, dynamic tables, tasks, etc.)
2. Usage statistics showing how actively each dependent is used
3. Affected users who query the dependents
4. A risk tier assessment (CRITICAL / MODERATE / LOW)
5. A recommendation on whether to proceed, coordinate, or defer

## Prerequisites

- Access to SNOWFLAKE.ACCOUNT_USAGE views
- The target object must exist

## Steps

### Step 1: Identify all downstream dependencies

Query OBJECT_DEPENDENCIES for everything that references the target.

Reference: `primitives/lineage-queries`

```sql
WITH downstream AS (
    SELECT
        referencing_database || '.' || referencing_schema || '.' || referencing_object_name AS dependent_object,
        referencing_object_domain AS object_type,
        dependency_type
    FROM SNOWFLAKE.ACCOUNT_USAGE.OBJECT_DEPENDENCIES
    WHERE referenced_database = '<database>'
        AND referenced_schema = '<schema>'
        AND referenced_object_name = '<table>'
        AND referencing_object_domain IN ('TABLE', 'VIEW', 'DYNAMIC TABLE', 'MATERIALIZED VIEW', 'PROCEDURE', 'FUNCTION', 'TASK', 'STREAM')
)
SELECT * FROM downstream
ORDER BY object_type, dependent_object;
```

If OBJECT_DEPENDENCIES returns no results (new object, or latency), fall back to GET_DDL parsing:
```sql
SELECT table_name, view_definition
FROM <database>.INFORMATION_SCHEMA.VIEWS
WHERE view_definition ILIKE '%<table>%';
```

### Step 2: Assess usage for each dependent

For each downstream object, check how actively it's queried.

```sql
WITH deps AS (
    SELECT referencing_database, referencing_schema, referencing_object_name
    FROM SNOWFLAKE.ACCOUNT_USAGE.OBJECT_DEPENDENCIES
    WHERE referenced_database = '<database>'
        AND referenced_schema = '<schema>'
        AND referenced_object_name = '<table>'
),
usage AS (
    SELECT
        base.value:objectName::STRING AS object_name,
        COUNT(DISTINCT ah.query_id) AS queries_7d,
        COUNT(DISTINCT ah.user_name) AS users_7d,
        MAX(ah.query_start_time) AS last_accessed
    FROM SNOWFLAKE.ACCOUNT_USAGE.ACCESS_HISTORY ah,
    LATERAL FLATTEN(input => ah.base_objects_accessed) base
    WHERE ah.query_start_time >= DATEADD('day', -7, CURRENT_TIMESTAMP())
    GROUP BY 1
)
SELECT
    d.referencing_database || '.' || d.referencing_schema || '.' || d.referencing_object_name AS dependent,
    COALESCE(u.queries_7d, 0) AS queries_last_7d,
    COALESCE(u.users_7d, 0) AS unique_users_7d,
    u.last_accessed,
    CASE
        WHEN COALESCE(u.queries_7d, 0) > 50 THEN 'CRITICAL'
        WHEN COALESCE(u.queries_7d, 0) > 10 THEN 'MODERATE'
        ELSE 'LOW'
    END AS risk_tier
FROM deps d
LEFT JOIN usage u ON u.object_name = d.referencing_database || '.' || d.referencing_schema || '.' || d.referencing_object_name
ORDER BY COALESCE(u.queries_7d, 0) DESC;
```

**Checkpoint:**
  severity: review
  present: "Dependency list with usage stats and risk tiers — confirm understanding before proceeding"

### Step 3: Identify affected users

```sql
SELECT DISTINCT
    ah.user_name,
    ah.role_name,
    COUNT(DISTINCT ah.query_id) AS query_count_7d
FROM SNOWFLAKE.ACCOUNT_USAGE.ACCESS_HISTORY ah,
LATERAL FLATTEN(input => ah.base_objects_accessed) base
WHERE base.value:objectName::STRING IN (
    SELECT referencing_database || '.' || referencing_schema || '.' || referencing_object_name
    FROM SNOWFLAKE.ACCOUNT_USAGE.OBJECT_DEPENDENCIES
    WHERE referenced_database = '<database>'
        AND referenced_schema = '<schema>'
        AND referenced_object_name = '<table>'
)
AND ah.query_start_time >= DATEADD('day', -7, CURRENT_TIMESTAMP())
GROUP BY ah.user_name, ah.role_name
ORDER BY query_count_7d DESC;
```

### Step 4: Check for cascade effects

Some dependents may themselves have dependents — creating a cascade.

```sql
WITH first_level AS (
    SELECT referencing_database AS db, referencing_schema AS sch, referencing_object_name AS obj
    FROM SNOWFLAKE.ACCOUNT_USAGE.OBJECT_DEPENDENCIES
    WHERE referenced_database = '<database>'
        AND referenced_schema = '<schema>'
        AND referenced_object_name = '<table>'
),
second_level AS (
    SELECT od.referencing_database || '.' || od.referencing_schema || '.' || od.referencing_object_name AS cascade_object,
        fl.db || '.' || fl.sch || '.' || fl.obj AS via_object,
        od.referencing_object_domain AS object_type
    FROM SNOWFLAKE.ACCOUNT_USAGE.OBJECT_DEPENDENCIES od
    JOIN first_level fl ON od.referenced_database = fl.db AND od.referenced_schema = fl.sch AND od.referenced_object_name = fl.obj
)
SELECT cascade_object, via_object, object_type
FROM second_level
ORDER BY via_object, cascade_object;
```

### Step 5: Produce risk assessment

Summarize findings as a risk assessment:

| Risk Level | Criteria | Recommendation |
|------------|----------|----------------|
| **CRITICAL** | >50 queries/week, dynamic tables, or has own dependents | Coordinate with affected teams; schedule during maintenance window |
| **MODERATE** | 10-50 queries/week, actively used views | Notify affected users; validate after change |
| **LOW** | <10 queries/week, no cascade dependents | Proceed with standard caution |

Present a clear summary: total dependents, users affected, highest risk tier, and recommended action.

**Checkpoint:**
  severity: critical
  present: "Complete impact assessment with risk tiers, affected users, and recommendation"

## Anti-patterns

| Mistake | Impact | Instead |
|---------|--------|---------|
| Only checking first-level dependencies | Misses cascade effects (dependent's dependents) | Always check at least two levels of dependencies |
| Ignoring usage stats | A view with 100 daily queries is more critical than an unused one | Weight risk by actual usage, not just existence |
| Not identifying affected users | Change breaks someone's workflow with no warning | Always list affected users so they can be notified |
| Treating OBJECT_DEPENDENCIES as complete | Has latency; new objects may not appear | Fall back to GET_DDL + INFORMATION_SCHEMA for recent objects |
