USE ROLE {admin_role};
USE WAREHOUSE {warehouse};

CREATE OR REPLACE VIEW {database}.{analytics_schema}.TICKET_DASHBOARD AS
WITH volume AS (
    SELECT STATUS, COUNT(*) AS TICKET_COUNT
    FROM {database}.{raw_schema}.SUPPORT_TICKETS GROUP BY STATUS
),
resolution AS (
    SELECT AVG(TIMESTAMPDIFF('HOUR', CREATED_AT, RESOLVED_AT)) AS AVG_RESOLUTION_HOURS
    FROM {database}.{raw_schema}.SUPPORT_TICKETS WHERE RESOLVED_AT IS NOT NULL
),
top_customers AS (
    SELECT t.CUSTOMER_ID, c.CUSTOMER_NAME, COUNT(*) AS OPEN_TICKET_COUNT
    FROM {database}.{raw_schema}.SUPPORT_TICKETS t
    JOIN {database}.{raw_schema}.CUSTOMERS c ON t.CUSTOMER_ID = c.CUSTOMER_ID
    WHERE t.STATUS != 'resolved'
    GROUP BY t.CUSTOMER_ID, c.CUSTOMER_NAME
    ORDER BY OPEN_TICKET_COUNT DESC
    LIMIT 10
)
SELECT 'volume_by_status' AS metric_type, STATUS AS dimension,
       TICKET_COUNT AS value, NULL AS detail
FROM volume
UNION ALL
SELECT 'avg_resolution_hours', 'all', AVG_RESOLUTION_HOURS, NULL FROM resolution
UNION ALL
SELECT 'top_open_customers', CUSTOMER_NAME, OPEN_TICKET_COUNT, NULL FROM top_customers;
