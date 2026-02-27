USE ROLE {admin_role};
USE WAREHOUSE {warehouse};

CREATE OR REPLACE VIEW {database}.{analytics_schema}.ORDER_QUALITY_REPORT AS
SELECT
    'null_order_ids' AS check_name,
    COUNT(*) AS issue_count
FROM {database}.{raw_schema}.ORDERS WHERE ORDER_ID IS NULL
UNION ALL
SELECT
    'duplicate_order_ids',
    COUNT(*) - COUNT(DISTINCT ORDER_ID)
FROM {database}.{raw_schema}.ORDERS
UNION ALL
SELECT
    'invalid_status',
    COUNT(*)
FROM {database}.{raw_schema}.ORDERS
WHERE STATUS NOT IN ('completed', 'pending', 'shipped', 'returned')
UNION ALL
SELECT
    'negative_amount',
    COUNT(*)
FROM {database}.{raw_schema}.ORDERS WHERE TOTAL_AMOUNT < 0;
