-- Impact Analysis: Downstream Dependencies with Risk Scoring
-- Find all objects that depend on the target and assess risk
-- Replace <database>, <schema>, <table> with actual values BEFORE executing

WITH downstream_deps AS (
    -- Get all objects that reference the target
    SELECT
        od.referencing_database AS dep_database,
        od.referencing_schema AS dep_schema,
        od.referencing_object_name AS dep_object,
        od.referencing_object_domain AS dep_type,
        od.dependency_type
    FROM SNOWFLAKE.ACCOUNT_USAGE.OBJECT_DEPENDENCIES od
    WHERE od.referenced_database = '<database>'
      AND od.referenced_schema = '<schema>'
      AND od.referenced_object_name = '<table>'
      AND od.referencing_object_domain IN ('TABLE', 'VIEW', 'DYNAMIC TABLE', 'MATERIALIZED VIEW', 'PROCEDURE', 'FUNCTION', 'TASK', 'STREAM')
),
usage_stats AS (
    -- Get usage statistics for each dependent object (last 7 days)
    SELECT
        base.value:objectName::STRING AS object_name,
        COUNT(DISTINCT ah.query_id) AS query_count_7d,
        COUNT(DISTINCT ah.user_name) AS unique_users_7d,
        MAX(ah.query_start_time) AS last_accessed
    FROM SNOWFLAKE.ACCOUNT_USAGE.ACCESS_HISTORY ah,
    LATERAL FLATTEN(input => ah.base_objects_accessed) AS base
    WHERE ah.query_start_time >= DATEADD(day, -7, CURRENT_TIMESTAMP())
    GROUP BY 1
),
cascade_count AS (
    -- Count downstream dependents of each dependent (cascade effect)
    SELECT
        od.referenced_database || '.' || od.referenced_schema || '.' || od.referenced_object_name AS object_name,
        COUNT(*) AS downstream_count
    FROM SNOWFLAKE.ACCOUNT_USAGE.OBJECT_DEPENDENCIES od
    GROUP BY 1
)
SELECT
    d.dep_database || '.' || d.dep_schema || '.' || d.dep_object AS dependent_object,
    d.dep_type AS object_type,
    COALESCE(u.query_count_7d, 0) AS queries_last_7_days,
    COALESCE(u.unique_users_7d, 0) AS unique_users_7_days,
    u.last_accessed,
    COALESCE(c.downstream_count, 0) AS downstream_dependents,
    -- Risk scoring
    CASE
        WHEN COALESCE(u.query_count_7d, 0) > 50 THEN 'CRITICAL'
        WHEN COALESCE(c.downstream_count, 0) > 0 THEN 'CRITICAL'
        -- Schema-based risk from config/schema-patterns.yaml
        WHEN /* SCHEMA_RISK_SCORING:d.dep_schema */ IS NOT NULL THEN 'CRITICAL'
        WHEN d.dep_type = 'DYNAMIC TABLE' THEN 'CRITICAL'
        WHEN COALESCE(u.query_count_7d, 0) BETWEEN 10 AND 50 THEN 'MODERATE'
        ELSE 'LOW'
    END AS risk_level,
    d.dependency_type
FROM downstream_deps d
LEFT JOIN usage_stats u 
    ON u.object_name = d.dep_database || '.' || d.dep_schema || '.' || d.dep_object
LEFT JOIN cascade_count c 
    ON c.object_name = d.dep_database || '.' || d.dep_schema || '.' || d.dep_object
ORDER BY
    CASE 
        WHEN COALESCE(u.query_count_7d, 0) > 50 OR COALESCE(c.downstream_count, 0) > 0 THEN 1
        WHEN COALESCE(u.query_count_7d, 0) BETWEEN 10 AND 50 THEN 2
        ELSE 3
    END,
    COALESCE(u.query_count_7d, 0) DESC;
