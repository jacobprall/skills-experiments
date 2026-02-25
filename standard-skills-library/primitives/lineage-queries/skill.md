---
type: primitive
name: lineage-queries
domain: data-observability
snowflake_docs: "https://docs.snowflake.com/en/sql-reference/account-usage/object_dependencies"
---

# Lineage Queries

Trace data lineage in Snowflake: downstream impact analysis, upstream root cause tracing, column-level lineage, and dependency discovery. All queries are read-only and can be executed immediately.

## Key Views

| View | What It Contains | Latency |
|------|-----------------|---------|
| `OBJECT_DEPENDENCIES` | Static dependency graph (which objects reference which) | Hours (new objects may be delayed) |
| `ACCESS_HISTORY` | Actual data access patterns (who queried what, column-level) | ~2 hours |
| `QUERY_HISTORY` | Query text and metadata | ~45 minutes |
| `TABLES` / `COLUMNS` | Schema metadata, last_altered timestamps | ~2 hours |

All queries require `<database>`, `<schema>`, `<table>` replacement with actual values.

## Downstream Impact Analysis

Find everything that depends on a target object and assess risk.

### Direct dependents

```sql
SELECT
    referencing_database || '.' || referencing_schema || '.' || referencing_object_name AS dependent_object,
    referencing_object_domain AS object_type,
    dependency_type
FROM SNOWFLAKE.ACCOUNT_USAGE.OBJECT_DEPENDENCIES
WHERE referenced_database = '<database>'
    AND referenced_schema = '<schema>'
    AND referenced_object_name = '<table>'
    AND referencing_object_domain IN ('TABLE', 'VIEW', 'DYNAMIC TABLE', 'MATERIALIZED VIEW', 'PROCEDURE', 'FUNCTION', 'TASK', 'STREAM')
ORDER BY referencing_object_domain, referencing_object_name;
```

### Dependents with usage stats and risk scoring

```sql
WITH deps AS (
    SELECT referencing_database AS db, referencing_schema AS sch,
        referencing_object_name AS obj, referencing_object_domain AS obj_type
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
    d.db || '.' || d.sch || '.' || d.obj AS dependent_object,
    d.obj_type AS object_type,
    COALESCE(u.queries_7d, 0) AS queries_7d,
    COALESCE(u.users_7d, 0) AS users_7d,
    u.last_accessed,
    CASE
        WHEN COALESCE(u.queries_7d, 0) > 50 THEN 'CRITICAL'
        WHEN d.obj_type = 'DYNAMIC TABLE' THEN 'CRITICAL'
        WHEN COALESCE(u.queries_7d, 0) > 10 THEN 'MODERATE'
        ELSE 'LOW'
    END AS risk_level
FROM deps d
LEFT JOIN usage u ON u.object_name = d.db || '.' || d.sch || '.' || d.obj
ORDER BY COALESCE(u.queries_7d, 0) DESC;
```

### Multi-level cascade (2 levels deep)

```sql
WITH level_1 AS (
    SELECT referencing_database AS db, referencing_schema AS sch,
        referencing_object_name AS obj, referencing_object_domain AS obj_type,
        1 AS depth
    FROM SNOWFLAKE.ACCOUNT_USAGE.OBJECT_DEPENDENCIES
    WHERE referenced_database = '<database>' AND referenced_schema = '<schema>' AND referenced_object_name = '<table>'
),
level_2 AS (
    SELECT od.referencing_database AS db, od.referencing_schema AS sch,
        od.referencing_object_name AS obj, od.referencing_object_domain AS obj_type,
        2 AS depth
    FROM SNOWFLAKE.ACCOUNT_USAGE.OBJECT_DEPENDENCIES od
    JOIN level_1 l ON od.referenced_database = l.db AND od.referenced_schema = l.sch AND od.referenced_object_name = l.obj
)
SELECT db || '.' || sch || '.' || obj AS object, obj_type, depth
FROM (SELECT * FROM level_1 UNION ALL SELECT * FROM level_2)
ORDER BY depth, obj_type, obj;
```

## Upstream Root Cause Tracing

Find what a target object depends on (its sources).

### Direct upstream sources

```sql
SELECT
    referenced_database || '.' || referenced_schema || '.' || referenced_object_name AS source_object,
    referenced_object_domain AS source_type,
    dependency_type
FROM SNOWFLAKE.ACCOUNT_USAGE.OBJECT_DEPENDENCIES
WHERE referencing_database = '<database>'
    AND referencing_schema = '<schema>'
    AND referencing_object_name = '<table>'
ORDER BY referenced_object_domain;
```

### Recent changes in upstream objects

```sql
SELECT
    table_catalog || '.' || table_schema || '.' || table_name AS object_name,
    last_altered,
    DATEDIFF('hour', last_altered, CURRENT_TIMESTAMP()) AS hours_ago,
    row_count
FROM SNOWFLAKE.ACCOUNT_USAGE.TABLES
WHERE (table_catalog, table_schema, table_name) IN (
    SELECT referenced_database, referenced_schema, referenced_object_name
    FROM SNOWFLAKE.ACCOUNT_USAGE.OBJECT_DEPENDENCIES
    WHERE referencing_database = '<database>' AND referencing_schema = '<schema>' AND referencing_object_name = '<table>'
)
AND last_altered >= DATEADD('day', -7, CURRENT_TIMESTAMP())
ORDER BY last_altered DESC;
```

## Column-Level Lineage

Trace which downstream columns consume a specific source column, or where a column's data originates.

### Downstream column consumers

```sql
SELECT
    obj.value:objectName::STRING AS consuming_object,
    col.value:columnName::STRING AS consuming_column,
    COUNT(DISTINCT ah.query_id) AS query_count,
    COUNT(DISTINCT ah.user_name) AS user_count
FROM SNOWFLAKE.ACCOUNT_USAGE.ACCESS_HISTORY ah,
LATERAL FLATTEN(input => ah.base_objects_accessed) base,
LATERAL FLATTEN(input => base.value:columns) src_col,
LATERAL FLATTEN(input => ah.objects_modified) obj,
LATERAL FLATTEN(input => obj.value:columns) col
WHERE base.value:objectName::STRING = '<database>.<schema>.<table>'
    AND src_col.value:columnName::STRING = '<column>'
    AND ah.query_start_time >= DATEADD('day', -30, CURRENT_TIMESTAMP())
GROUP BY 1, 2
ORDER BY query_count DESC;
```

### Upstream column sources

```sql
SELECT
    base.value:objectName::STRING AS source_object,
    src_col.value:columnName::STRING AS source_column,
    COUNT(DISTINCT ah.query_id) AS query_count
FROM SNOWFLAKE.ACCOUNT_USAGE.ACCESS_HISTORY ah,
LATERAL FLATTEN(input => ah.objects_modified) obj,
LATERAL FLATTEN(input => obj.value:columns) col,
LATERAL FLATTEN(input => ah.base_objects_accessed) base,
LATERAL FLATTEN(input => base.value:columns) src_col
WHERE obj.value:objectName::STRING = '<database>.<schema>.<table>'
    AND col.value:columnName::STRING = '<column>'
    AND ah.query_start_time >= DATEADD('day', -30, CURRENT_TIMESTAMP())
GROUP BY 1, 2
ORDER BY query_count DESC;
```

## Fallback: GET_DDL Parsing

When OBJECT_DEPENDENCIES has latency gaps (new objects), parse DDL directly.

```sql
SELECT table_name, view_definition
FROM <database>.INFORMATION_SCHEMA.VIEWS
WHERE table_schema = '<schema>'
    AND view_definition ILIKE '%<source_table>%';
```

```sql
SELECT GET_DDL('VIEW', '<database>.<schema>.<view_name>');
```

## Constraints

- OBJECT_DEPENDENCIES has latency — newly created objects may not appear for hours
- ACCESS_HISTORY retains 365 days of data; older access patterns are not available
- Column-level lineage depends on ACCESS_HISTORY capturing column-level detail (not all query types expose this)
- Single-account scope — cross-account data sharing lineage is not covered
- Recursive depth is limited by CTE recursion limits; practical limit is 3-4 levels

## Anti-patterns

| Pattern | Why It Fails | Instead |
|---------|-------------|---------|
| Relying solely on OBJECT_DEPENDENCIES for new objects | Latency means recent objects may be missing | Fall back to GET_DDL + INFORMATION_SCHEMA for recent objects |
| Treating OBJECT_DEPENDENCIES as data flow | It shows definitional dependencies, not actual data movement | Combine with ACCESS_HISTORY for actual data flow patterns |
| Running column-level lineage without time bounds | Queries the entire 365-day ACCESS_HISTORY, very slow | Always add a time filter (e.g., last 30 days) |

## References

- `primitives/data-metric-functions`
- `primitives/table-comparison`
- [OBJECT_DEPENDENCIES](https://docs.snowflake.com/en/sql-reference/account-usage/object_dependencies)
- [ACCESS_HISTORY](https://docs.snowflake.com/en/sql-reference/account-usage/access_history)
