USE ROLE {admin_role};
USE WAREHOUSE {warehouse};

CALL SYSTEM$CLASSIFY('{database}.{raw_schema}.CUSTOMERS', {'auto_tag': true});

CREATE OR REPLACE ROLE {governance_schema}_DATA_STEWARD;

CREATE OR REPLACE MASKING POLICY {database}.{governance_schema}.MASK_SSN AS
(val STRING) RETURNS STRING -> CASE WHEN CURRENT_ROLE() IN ('{admin_role}', '{governance_schema}_DATA_STEWARD') THEN val ELSE '***-**-****' END;
CREATE OR REPLACE MASKING POLICY {database}.{governance_schema}.MASK_EMAIL AS
(val STRING) RETURNS STRING -> CASE WHEN CURRENT_ROLE() IN ('{admin_role}', '{governance_schema}_DATA_STEWARD') THEN val ELSE '***@' || SPLIT_PART(val, '@', 2) END;
CREATE OR REPLACE MASKING POLICY {database}.{governance_schema}.MASK_PHONE AS
(val STRING) RETURNS STRING -> CASE WHEN CURRENT_ROLE() IN ('{admin_role}', '{governance_schema}_DATA_STEWARD') THEN val ELSE '***-***-' || RIGHT(val, 4) END;
CREATE OR REPLACE MASKING POLICY {database}.{governance_schema}.MASK_DOB AS
(val DATE) RETURNS DATE -> CASE WHEN CURRENT_ROLE() IN ('{admin_role}', '{governance_schema}_DATA_STEWARD') THEN val ELSE '1900-01-01'::DATE END;
CREATE OR REPLACE MASKING POLICY {database}.{governance_schema}.MASK_NAME AS
(val STRING) RETURNS STRING -> CASE WHEN CURRENT_ROLE() IN ('{admin_role}', '{governance_schema}_DATA_STEWARD') THEN val ELSE 'REDACTED' END;

ALTER TABLE {database}.{raw_schema}.CUSTOMERS MODIFY COLUMN SSN SET MASKING POLICY {database}.{governance_schema}.MASK_SSN;
ALTER TABLE {database}.{raw_schema}.CUSTOMERS MODIFY COLUMN EMAIL SET MASKING POLICY {database}.{governance_schema}.MASK_EMAIL;
ALTER TABLE {database}.{raw_schema}.CUSTOMERS MODIFY COLUMN PHONE SET MASKING POLICY {database}.{governance_schema}.MASK_PHONE;
ALTER TABLE {database}.{raw_schema}.CUSTOMERS MODIFY COLUMN DATE_OF_BIRTH SET MASKING POLICY {database}.{governance_schema}.MASK_DOB;
ALTER TABLE {database}.{raw_schema}.CUSTOMERS MODIFY COLUMN CUSTOMER_NAME SET MASKING POLICY {database}.{governance_schema}.MASK_NAME;

CREATE OR REPLACE DYNAMIC TABLE {database}.{analytics_schema}.ORDER_METRICS
    TARGET_LAG = '1 minute' WAREHOUSE = {warehouse}
AS
SELECT ORDER_DATE, PRODUCT_CATEGORY, COUNT(*) AS ORDER_COUNT, SUM(TOTAL_AMOUNT) AS REVENUE
FROM {database}.{raw_schema}.ORDERS GROUP BY ORDER_DATE, PRODUCT_CATEGORY;
