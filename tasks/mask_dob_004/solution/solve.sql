USE ROLE {admin_role};
USE WAREHOUSE {warehouse};

CREATE OR REPLACE MASKING POLICY {database}.{governance_schema}.MASK_DOB AS
(val DATE) RETURNS DATE ->
    CASE
        WHEN CURRENT_ROLE() IN ('{admin_role}') THEN val
        ELSE '1900-01-01'::DATE
    END;

ALTER TABLE {database}.{raw_schema}.CUSTOMERS
    MODIFY COLUMN DATE_OF_BIRTH
    SET MASKING POLICY {database}.{governance_schema}.MASK_DOB;
