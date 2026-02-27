USE ROLE {admin_role};
USE WAREHOUSE {warehouse};

CREATE OR REPLACE TAG {database}.{governance_schema}.PII_LEVEL
    ALLOWED_VALUES 'HIGH', 'MEDIUM', 'LOW';

ALTER TABLE {database}.{raw_schema}.CUSTOMERS
    MODIFY COLUMN SSN SET TAG {database}.{governance_schema}.PII_LEVEL = 'HIGH';

ALTER TABLE {database}.{raw_schema}.CUSTOMERS
    MODIFY COLUMN EMAIL SET TAG {database}.{governance_schema}.PII_LEVEL = 'MEDIUM';

ALTER TABLE {database}.{raw_schema}.CUSTOMERS
    MODIFY COLUMN PHONE SET TAG {database}.{governance_schema}.PII_LEVEL = 'MEDIUM';
