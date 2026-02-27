USE ROLE {admin_role};
USE WAREHOUSE {warehouse};

CREATE OR REPLACE ROW ACCESS POLICY {database}.{governance_schema}.RAP_TICKETS AS
(priority_val VARCHAR) RETURNS BOOLEAN ->
    CASE
        WHEN CURRENT_ROLE() IN ('{admin_role}') THEN TRUE
        WHEN CURRENT_ROLE() IN ('{restricted_role}') AND priority_val = 'low' THEN TRUE
        ELSE FALSE
    END;

ALTER TABLE {database}.{raw_schema}.SUPPORT_TICKETS
    ADD ROW ACCESS POLICY {database}.{governance_schema}.RAP_TICKETS
    ON (PRIORITY);
