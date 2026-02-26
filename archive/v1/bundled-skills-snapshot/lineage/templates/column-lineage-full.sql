-- Column Lineage: Full Path Tracing
-- Trace complete column lineage from source to destination
-- Replace <database>, <schema>, <table>, <column> with actual values BEFORE executing
--
-- CONFIGURABLE: Adjust DATEADD day value to extend/shorten lookback period (default: 90 days)
-- CONFIGURABLE: Adjust recursion depth limit (default: 4 levels)
-- ACCESS_HISTORY retention is 365 days maximum

-- This query builds a complete lineage path by following column transformations
-- through ACCESS_HISTORY patterns

WITH RECURSIVE column_lineage AS (
    -- Base case: Start with the target column
    SELECT 
        '<database>.<schema>.<table>' AS object_name,
        '<column>' AS column_name,
        'TARGET' AS object_type,
        0 AS level,
        '<database>.<schema>.<table>.<column>' AS lineage_path,
        ARRAY_CONSTRUCT('<database>.<schema>.<table>') AS visited
    
    UNION ALL
    
    -- Recursive: Find upstream sources
    SELECT 
        base.value:objectName::STRING AS object_name,
        src_col.value:columnName::STRING AS column_name,
        base.value:objectDomain::STRING AS object_type,
        cl.level + 1 AS level,
        base.value:objectName::STRING || '.' || COALESCE(src_col.value:columnName::STRING, '*') || ' → ' || cl.lineage_path AS lineage_path,
        ARRAY_APPEND(cl.visited, base.value:objectName::STRING) AS visited
    FROM column_lineage cl
    JOIN SNOWFLAKE.ACCOUNT_USAGE.ACCESS_HISTORY ah
        ON ah.query_start_time >= DATEADD(day, -60, CURRENT_TIMESTAMP()),
      LATERAL FLATTEN(input => ah.objects_modified) AS modified,
      LATERAL FLATTEN(input => modified.value:columns, outer => true) AS dest_col,
      LATERAL FLATTEN(input => ah.base_objects_accessed) AS base,
      LATERAL FLATTEN(input => base.value:columns, outer => true) AS src_col
    WHERE cl.level < 3  -- Limit recursion depth
    AND modified.value:objectName::STRING = cl.object_name
    AND dest_col.value:columnName::STRING = cl.column_name OR dest_col.value IS NULL
    AND base.value:objectDomain::STRING IN ('Table', 'View', 'Dynamic Table', 'Stage')
    AND base.value:objectName::STRING != cl.object_name
    AND NOT ARRAY_CONTAINS(base.value:objectName::STRING::VARIANT, cl.visited)
),
-- Get metadata for each object in the lineage
lineage_with_metadata AS (
    SELECT DISTINCT
        cl.level,
        cl.object_name,
        cl.column_name,
        cl.object_type,
        cl.lineage_path,
        t.table_schema,
        t.table_owner AS owner,
        t.last_altered,
        t.row_count
    FROM column_lineage cl
    LEFT JOIN SNOWFLAKE.ACCOUNT_USAGE.TABLES t
        ON t.table_catalog || '.' || t.table_schema || '.' || t.table_name = cl.object_name
        AND t.deleted IS NULL
)
SELECT
    level,
    object_name,
    column_name,
    object_type,
    owner,
    last_altered,
    row_count,
    lineage_path,
    -- Node type indicator
    -- For trust tier, use config/schema-patterns.yaml
    CASE
        WHEN level = 0 THEN 'TARGET'
        WHEN object_type = 'Stage' THEN 'EXTERNAL_SOURCE'
        ELSE /* SCHEMA_TRUST_TIER:table_schema */
    END AS node_type
FROM lineage_with_metadata
ORDER BY level, object_name
LIMIT 100;
