-- ============================================================================
-- Experiment 002 Reset
-- Run between each test to restore the environment to a clean state.
-- Preserves base data and re-creates all fixture "traps."
-- ============================================================================

USE ROLE SNOWFLAKE_LEARNING_ADMIN_ROLE;
USE WAREHOUSE SNOWFLAKE_LEARNING_WH;
USE DATABASE SNOWFLAKE_LEARNING_DB;

-- ============================================================================
-- 1. Drop agent-created masking policies (keep LEGACY_MASK_EMAIL)
-- ============================================================================

-- Unset all masking policies from CUSTOMERS columns first
-- (prevents "column has policy" errors when dropping policies)
ALTER TABLE RAW.CUSTOMERS MODIFY COLUMN EMAIL UNSET MASKING POLICY;
ALTER TABLE RAW.CUSTOMERS MODIFY COLUMN SSN UNSET MASKING POLICY;
ALTER TABLE RAW.CUSTOMERS MODIFY COLUMN PHONE UNSET MASKING POLICY;
ALTER TABLE RAW.CUSTOMERS MODIFY COLUMN DATE_OF_BIRTH UNSET MASKING POLICY;
ALTER TABLE RAW.CUSTOMERS MODIFY COLUMN CUSTOMER_NAME UNSET MASKING POLICY;

-- Drop all masking policies in RAW schema, then re-create the broken one
DROP MASKING POLICY IF EXISTS RAW.LEGACY_MASK_EMAIL;
DROP MASKING POLICY IF EXISTS RAW.MASK_EMAIL;
DROP MASKING POLICY IF EXISTS RAW.MASK_SSN;
DROP MASKING POLICY IF EXISTS RAW.MASK_PHONE;
DROP MASKING POLICY IF EXISTS RAW.MASK_DOB;
DROP MASKING POLICY IF EXISTS RAW.MASK_DATE_OF_BIRTH;
DROP MASKING POLICY IF EXISTS RAW.MASK_NAME;
DROP MASKING POLICY IF EXISTS RAW.MASK_CUSTOMER_NAME;

-- Also check GOVERNANCE schema (agents sometimes create policies there)
DROP MASKING POLICY IF EXISTS GOVERNANCE.MASK_EMAIL;
DROP MASKING POLICY IF EXISTS GOVERNANCE.MASK_SSN;
DROP MASKING POLICY IF EXISTS GOVERNANCE.MASK_PHONE;
DROP MASKING POLICY IF EXISTS GOVERNANCE.MASK_DOB;
DROP MASKING POLICY IF EXISTS GOVERNANCE.MASK_DATE_OF_BIRTH;
DROP MASKING POLICY IF EXISTS GOVERNANCE.MASK_NAME;
DROP MASKING POLICY IF EXISTS GOVERNANCE.MASK_CUSTOMER_NAME;
DROP MASKING POLICY IF EXISTS GOVERNANCE.MASK_PII_STRING;
DROP MASKING POLICY IF EXISTS GOVERNANCE.MASK_PII_DATE;
DROP MASKING POLICY IF EXISTS GOVERNANCE.LEGACY_MASK_EMAIL;

-- ============================================================================
-- 2. Drop agent-created row access and projection policies
-- ============================================================================

DROP ROW ACCESS POLICY IF EXISTS RAW.RAP_CUSTOMERS;
DROP ROW ACCESS POLICY IF EXISTS GOVERNANCE.RAP_CUSTOMERS;
DROP PROJECTION POLICY IF EXISTS RAW.PP_CUSTOMERS;
DROP PROJECTION POLICY IF EXISTS GOVERNANCE.PP_CUSTOMERS;

-- ============================================================================
-- 3. Drop agent-created dynamic tables (keep fixtures — we'll re-create them)
-- ============================================================================

DROP DYNAMIC TABLE IF EXISTS ANALYTICS.STALE_SUMMARY;
DROP DYNAMIC TABLE IF EXISTS ANALYTICS.TICKET_ENRICHED;
DROP DYNAMIC TABLE IF EXISTS ANALYTICS.TICKET_SUMMARY;
DROP DYNAMIC TABLE IF EXISTS ANALYTICS.ORDER_SUMMARY;
DROP DYNAMIC TABLE IF EXISTS ANALYTICS.REVENUE_SUMMARY;
DROP DYNAMIC TABLE IF EXISTS ANALYTICS.CUSTOMER_SUMMARY;
DROP DYNAMIC TABLE IF EXISTS ANALYTICS.CUSTOMER_ORDERS;
DROP DYNAMIC TABLE IF EXISTS ANALYTICS.SUPPORT_SUMMARY;

-- ============================================================================
-- 4. Drop agent-created regular tables in ANALYTICS/STAGING
-- ============================================================================

DROP TABLE IF EXISTS ANALYTICS.TICKETS_ENRICHED;
DROP TABLE IF EXISTS ANALYTICS.TICKET_ENRICHED_MATERIALIZED;
DROP TABLE IF EXISTS STAGING.TICKETS_ENRICHED;
DROP TABLE IF EXISTS STAGING.SUPPORT_TICKETS_ENRICHED;

-- ============================================================================
-- 5. Drop agent-created views
-- ============================================================================

DROP VIEW IF EXISTS ANALYTICS.TICKET_SUMMARY_V;
DROP VIEW IF EXISTS ANALYTICS.COST_SUMMARY;
DROP VIEW IF EXISTS ANALYTICS.CUSTOMER_OVERVIEW;

-- ============================================================================
-- 6. Drop agent-created Streamlit apps
-- ============================================================================

DROP STREAMLIT IF EXISTS ANALYTICS.SUPPORT_DASHBOARD;
DROP STREAMLIT IF EXISTS ANALYTICS.COST_DASHBOARD;
DROP STREAMLIT IF EXISTS ANALYTICS.DATA_DASHBOARD;

-- ============================================================================
-- 7. Drop agent-created resource monitors
-- ============================================================================

DROP RESOURCE MONITOR IF EXISTS COST_ALERT_MONITOR;
DROP RESOURCE MONITOR IF EXISTS WH_MONITOR;
DROP RESOURCE MONITOR IF EXISTS SNOWFLAKE_LEARNING_WH_MONITOR;

-- ============================================================================
-- 8. Re-create fixture: LEGACY_MASK_EMAIL (broken — CURRENT_ROLE anti-pattern)
-- ============================================================================

CREATE OR REPLACE MASKING POLICY RAW.LEGACY_MASK_EMAIL AS (val STRING)
  RETURNS STRING ->
  CASE WHEN CURRENT_ROLE() = 'SNOWFLAKE_LEARNING_ADMIN_ROLE' THEN val
       ELSE '***MASKED***'
  END;

ALTER TABLE RAW.CUSTOMERS MODIFY COLUMN EMAIL SET MASKING POLICY RAW.LEGACY_MASK_EMAIL;

-- ============================================================================
-- 9. Re-create fixture: STALE_SUMMARY (suspended dynamic table)
-- ============================================================================

CREATE OR REPLACE DYNAMIC TABLE ANALYTICS.STALE_SUMMARY
  TARGET_LAG = '1 hour'
  WAREHOUSE = SNOWFLAKE_LEARNING_WH
AS
  SELECT segment, COUNT(*) AS cnt
  FROM RAW.CUSTOMERS
  GROUP BY segment;

SELECT SYSTEM$WAIT(5);
ALTER DYNAMIC TABLE ANALYTICS.STALE_SUMMARY SUSPEND;

-- ============================================================================
-- 10. Re-create fixture: TICKET_ENRICHED (AI functions in dynamic table)
-- ============================================================================

CREATE OR REPLACE DYNAMIC TABLE ANALYTICS.TICKET_ENRICHED
  TARGET_LAG = '1 hour'
  WAREHOUSE = SNOWFLAKE_LEARNING_WH
AS
  SELECT
    ticket_id,
    customer_id,
    subject,
    body,
    priority,
    created_at,
    resolved_at,
    SNOWFLAKE.CORTEX.CLASSIFY_TEXT(body, ['billing', 'technical', 'account', 'feature_request']):label::VARCHAR AS category,
    SNOWFLAKE.CORTEX.SENTIMENT(body) AS sentiment_score
  FROM RAW.SUPPORT_TICKETS;

-- ============================================================================
-- 11. Verify base data is intact
-- ============================================================================

SELECT 'CUSTOMERS' AS fixture, COUNT(*) AS row_count FROM RAW.CUSTOMERS
UNION ALL
SELECT 'ORDERS', COUNT(*) FROM RAW.ORDERS
UNION ALL
SELECT 'SUPPORT_TICKETS', COUNT(*) FROM RAW.SUPPORT_TICKETS;

-- Verify: should be 500, 5000, 1000
-- If any are 0, re-run fixtures.sql

SHOW MASKING POLICIES IN SCHEMA RAW;
SHOW DYNAMIC TABLES IN SCHEMA ANALYTICS;

SELECT 'Reset complete' AS status;
