USE ROLE {admin_role};
USE WAREHOUSE {warehouse};

CREATE OR REPLACE MASKING POLICY {database}.{governance_schema}.MASK_EMAIL AS
(val STRING) RETURNS STRING ->
    CASE
        WHEN CURRENT_ROLE() IN ('{admin_role}') THEN val
        ELSE '***@' || SPLIT_PART(val, '@', 2)
    END;

ALTER TABLE {database}.{raw_schema}.CUSTOMERS
    MODIFY COLUMN EMAIL
    SET MASKING POLICY {database}.{governance_schema}.MASK_EMAIL;
