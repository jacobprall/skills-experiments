-- Trap: Legacy masking policy that hides email but uses a broken pattern (returns NULL, not masked)
USE ROLE {admin_role};
USE WAREHOUSE {warehouse};

CREATE OR REPLACE MASKING POLICY {database}.{governance_schema}.LEGACY_MASK_EMAIL AS
(val STRING) RETURNS STRING ->
    CASE
        WHEN CURRENT_ROLE() IN ('{admin_role}') THEN val
        ELSE NULL
    END;

-- Trap: A phone masking policy exists but is NOT applied to any column
CREATE OR REPLACE MASKING POLICY {database}.{governance_schema}.MASK_PHONE AS
(val STRING) RETURNS STRING ->
    CASE
        WHEN CURRENT_ROLE() IN ('{admin_role}') THEN val
        ELSE '***-***-' || RIGHT(val, 4)
    END;
