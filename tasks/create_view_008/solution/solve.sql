USE ROLE {admin_role};
USE WAREHOUSE {warehouse};

CREATE OR REPLACE SECURE VIEW {database}.{analytics_schema}.CUSTOMER_ORDERS AS
SELECT
    c.CUSTOMER_ID,
    c.CUSTOMER_NAME,
    o.ORDER_ID,
    o.ORDER_DATE,
    o.TOTAL_AMOUNT,
    o.STATUS
FROM {database}.{raw_schema}.CUSTOMERS c
JOIN {database}.{raw_schema}.ORDERS o ON c.CUSTOMER_ID = o.CUSTOMER_ID;
