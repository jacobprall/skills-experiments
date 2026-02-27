USE ROLE {admin_role};
USE WAREHOUSE {warehouse};

CREATE OR REPLACE STREAM {database}.{staging_schema}.ORDERS_STREAM
    ON TABLE {database}.{raw_schema}.ORDERS
    APPEND_ONLY = TRUE;
