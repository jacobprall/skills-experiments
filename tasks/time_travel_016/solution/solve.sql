USE ROLE {admin_role};
USE WAREHOUSE {warehouse};

ALTER TABLE {database}.{raw_schema}.CUSTOMERS
    SET DATA_RETENTION_TIME_IN_DAYS = 14;

ALTER TABLE {database}.{raw_schema}.ORDERS
    SET DATA_RETENTION_TIME_IN_DAYS = 7;
