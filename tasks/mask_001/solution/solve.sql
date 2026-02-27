USE ROLE {admin_role};
USE WAREHOUSE {warehouse};

CREATE OR REPLACE MASKING POLICY {database}.{governance_schema}.MASK_SSN AS
(val STRING) RETURNS STRING ->
    CASE
        WHEN CURRENT_ROLE() IN ('{admin_role}') THEN val
        ELSE '***-**-****'
    END;

ALTER TABLE {database}.{raw_schema}.CUSTOMERS
    MODIFY COLUMN SSN
    SET MASKING POLICY {database}.{governance_schema}.MASK_SSN;
