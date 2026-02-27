USE ROLE {admin_role};
USE WAREHOUSE {warehouse};
CALL SYSTEM$CLASSIFY('{database}.{raw_schema}.CUSTOMERS', {'auto_tag': true});
