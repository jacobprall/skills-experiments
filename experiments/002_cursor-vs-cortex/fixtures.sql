-- ============================================================================
-- Experiment 002 Fixtures
-- Run once to set up the environment. Assumes experiment 001 base data exists
-- (CUSTOMERS 500 rows, ORDERS 5000 rows) in SNOWFLAKE_LEARNING_DB.
-- ============================================================================

USE ROLE SNOWFLAKE_LEARNING_ADMIN_ROLE;
USE WAREHOUSE SNOWFLAKE_LEARNING_WH;
USE DATABASE SNOWFLAKE_LEARNING_DB;

-- ============================================================================
-- 1. Ensure schemas exist
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS RAW;
CREATE SCHEMA IF NOT EXISTS STAGING;
CREATE SCHEMA IF NOT EXISTS ANALYTICS;
CREATE SCHEMA IF NOT EXISTS GOVERNANCE;

-- ============================================================================
-- 2. Base tables (idempotent — only creates if missing from experiment 001)
-- ============================================================================

CREATE TABLE IF NOT EXISTS RAW.CUSTOMERS (
    customer_id STRING,
    customer_name STRING,
    email STRING,
    phone STRING,
    ssn STRING,
    segment STRING,
    department STRING,
    date_of_birth DATE
);

INSERT INTO RAW.CUSTOMERS
SELECT
    'CUST-' || SEQ4(),
    RANDSTR(8, RANDOM()) || ' ' || RANDSTR(10, RANDOM()),
    LOWER(RANDSTR(8, RANDOM())) || '@example.com',
    '+1-555-' || LPAD(UNIFORM(1000000, 9999999, RANDOM())::STRING, 7, '0'),
    LPAD(UNIFORM(100000000, 999999999, RANDOM())::STRING, 9, '0'),
    CASE UNIFORM(1, 4, RANDOM())
        WHEN 1 THEN 'Enterprise' WHEN 2 THEN 'SMB'
        WHEN 3 THEN 'Startup' ELSE 'Consumer'
    END,
    CASE UNIFORM(1, 4, RANDOM())
        WHEN 1 THEN 'Sales' WHEN 2 THEN 'Engineering'
        WHEN 3 THEN 'Marketing' ELSE 'Support'
    END,
    DATEADD('day', -UNIFORM(7000, 25000, RANDOM()), CURRENT_DATE())
FROM TABLE(GENERATOR(ROWCOUNT => 500))
WHERE (SELECT COUNT(*) FROM RAW.CUSTOMERS) = 0;

CREATE TABLE IF NOT EXISTS RAW.ORDERS (
    order_id STRING,
    customer_id STRING,
    order_date TIMESTAMP,
    total_amount NUMBER(10,2),
    status STRING
);

INSERT INTO RAW.ORDERS
SELECT
    'ORD-' || SEQ4(),
    'CUST-' || UNIFORM(0, 499, RANDOM()),
    DATEADD('hour', -UNIFORM(1, 8760, RANDOM()), CURRENT_TIMESTAMP()),
    ROUND(UNIFORM(10, 5000, RANDOM()) + UNIFORM(0, 99, RANDOM()) / 100, 2),
    CASE UNIFORM(1, 5, RANDOM())
        WHEN 1 THEN 'PENDING' WHEN 2 THEN 'SHIPPED' WHEN 3 THEN 'DELIVERED'
        WHEN 4 THEN 'RETURNED' ELSE 'CANCELLED'
    END
FROM TABLE(GENERATOR(ROWCOUNT => 5000))
WHERE (SELECT COUNT(*) FROM RAW.ORDERS) = 0;

-- ============================================================================
-- 3. SUPPORT_TICKETS — ~1000 rows of synthetic support ticket data
--    Used in T4 (AI pipeline) and T6 (capstone)
-- ============================================================================

CREATE OR REPLACE TABLE RAW.SUPPORT_TICKETS (
    ticket_id STRING,
    customer_id STRING,
    subject STRING,
    body STRING,
    priority STRING,
    created_at TIMESTAMP,
    resolved_at TIMESTAMP
);

INSERT INTO RAW.SUPPORT_TICKETS
SELECT
    'TKT-' || LPAD(SEQ4()::STRING, 5, '0'),
    'CUST-' || UNIFORM(0, 499, RANDOM()),

    -- Subject line varies by category
    CASE UNIFORM(1, 4, RANDOM())
        WHEN 1 THEN CASE UNIFORM(1, 4, RANDOM())
            WHEN 1 THEN 'Billing discrepancy on latest invoice'
            WHEN 2 THEN 'Unexpected charge on my account'
            WHEN 3 THEN 'Need to update payment method'
            ELSE 'Question about pricing tiers'
        END
        WHEN 2 THEN CASE UNIFORM(1, 4, RANDOM())
            WHEN 1 THEN 'Query performance degradation'
            WHEN 2 THEN 'Connection timeout errors'
            WHEN 3 THEN 'Data loading failure'
            ELSE 'Warehouse not starting'
        END
        WHEN 3 THEN CASE UNIFORM(1, 4, RANDOM())
            WHEN 1 THEN 'Need to add new team members'
            WHEN 2 THEN 'Password reset not working'
            WHEN 3 THEN 'MFA setup issues'
            ELSE 'Role permissions confusion'
        END
        ELSE CASE UNIFORM(1, 4, RANDOM())
            WHEN 1 THEN 'Request: support for Iceberg tables'
            WHEN 2 THEN 'Suggestion: better cost dashboard'
            WHEN 3 THEN 'Feature request: scheduled reports'
            ELSE 'Would love native Git integration'
        END
    END,

    -- Body text varies by category with product mentions
    CASE UNIFORM(1, 4, RANDOM())
        WHEN 1 THEN CASE UNIFORM(1, 4, RANDOM())
            WHEN 1 THEN 'We noticed our invoice for ' || DATE_TRUNC('month', CURRENT_DATE()) || ' is significantly higher than expected. Our Snowpark usage on the Analytics warehouse seems to be the main driver. Can someone review the charges and help us understand the breakdown? We are on the Enterprise plan.'
            WHEN 2 THEN 'There is an unexpected $' || UNIFORM(50, 2000, RANDOM())::STRING || ' charge on our account this month. We primarily use Snowsight for dashboards and the Cortex AI functions for text analysis. Not sure where this is coming from.'
            WHEN 3 THEN 'We need to switch our payment from the current credit card to ACH. Also, can you clarify how Snowpipe Streaming credits are calculated? We started using it last week with our Kafka connector.'
            ELSE 'Can someone explain the difference between the Standard and Enterprise pricing? We are evaluating whether the Dynamic Tables feature justifies the upgrade cost for our Streamlit dashboards.'
        END
        WHEN 2 THEN CASE UNIFORM(1, 4, RANDOM())
            WHEN 1 THEN 'Our nightly ELT pipeline using Dynamic Tables has slowed down by 3x over the past week. The ANALYTICS warehouse is queuing tasks but the warehouse auto-scaling does not seem to kick in. We are running Snowflake on AWS us-east-1.'
            WHEN 2 THEN 'Getting intermittent JDBC connection timeouts when running queries from our Snowpark Python application. The warehouse shows as available in Snowsight but the driver reports connection refused. Started after upgrading the Snowflake connector.'
            WHEN 3 THEN 'Our Snowpipe is failing to load files from the S3 stage. Error: "File not found." The files are definitely there — we verified in the AWS console. The external stage was working fine until yesterday. Using the Kafka connector with Snowpipe Streaming.'
            ELSE 'The SNOWFLAKE_LEARNING_WH warehouse takes 2-3 minutes to resume from suspended state. This is causing timeouts in our Streamlit app. Is there a way to keep it warm without running up costs? We tried auto-resume but the cold start is too long.'
        END
        WHEN 3 THEN CASE UNIFORM(1, 4, RANDOM())
            WHEN 1 THEN 'I need to add 5 new data engineers to our Snowflake account. They should have access to the RAW and STAGING schemas but not ANALYTICS. What is the recommended role setup? We use Snowsight for day-to-day work.'
            WHEN 2 THEN 'A team member is locked out after too many failed MFA attempts. Their password reset email is not arriving. This is blocking a production deployment of our Streamlit dashboard. Urgent.'
            WHEN 3 THEN 'We set up SCIM provisioning with Okta but the roles are not syncing correctly. Users show up in Snowsight but with the wrong default role. They cannot access the Dynamic Tables in ANALYTICS schema.'
            ELSE 'Confused about the difference between ACCOUNTADMIN, SYSADMIN, and SECURITYADMIN roles. I inherited this account and the previous admin granted ACCOUNTADMIN to too many people. Need help cleaning up the role hierarchy. Using Cortex AI functions and want to restrict access.'
        END
        ELSE CASE UNIFORM(1, 4, RANDOM())
            WHEN 1 THEN 'We are excited about Apache Iceberg table support. When will it be GA for our region (AWS eu-west-1)? We want to use it with our existing Spark pipelines and the Snowpark DataFrame API.'
            WHEN 2 THEN 'The current cost monitoring in Snowsight is not granular enough. We need per-team cost attribution for our chargeback model. Would love to see Cortex AI-powered cost anomaly detection built into the Budgets feature.'
            WHEN 3 THEN 'Would be great to have scheduled email reports for query performance metrics. Right now we have to manually export from Snowsight. Could this be a native Streamlit template?'
            ELSE 'Native Git integration for version-controlling our SQL scripts would be amazing. Right now we use dbt with an external repo but the workflow is clunky. Would love to see this integrated with Snowsight notebooks.'
        END
    END,

    -- Priority
    CASE UNIFORM(1, 4, RANDOM())
        WHEN 1 THEN 'LOW'
        WHEN 2 THEN 'MEDIUM'
        WHEN 3 THEN 'HIGH'
        ELSE 'CRITICAL'
    END,

    -- created_at: spread over the last 90 days
    DATEADD('minute', -UNIFORM(1, 129600, RANDOM()), CURRENT_TIMESTAMP()),

    -- resolved_at: ~80% resolved, NULL for the rest
    CASE WHEN UNIFORM(1, 5, RANDOM()) <= 4
        THEN DATEADD('hour', UNIFORM(1, 72, RANDOM()),
             DATEADD('minute', -UNIFORM(1, 129600, RANDOM()), CURRENT_TIMESTAMP()))
        ELSE NULL
    END

FROM TABLE(GENERATOR(ROWCOUNT => 1000));

-- ============================================================================
-- 4. LEGACY_MASK_EMAIL — broken masking policy with CURRENT_ROLE() anti-pattern
--    Trap: uses CURRENT_ROLE() instead of IS_ROLE_IN_SESSION()
--    Scored in: T2, T3, T5, T6
-- ============================================================================

-- Unset any existing policy on EMAIL first (idempotent)
ALTER TABLE RAW.CUSTOMERS MODIFY COLUMN EMAIL UNSET MASKING POLICY;

CREATE OR REPLACE MASKING POLICY RAW.LEGACY_MASK_EMAIL AS (val STRING)
  RETURNS STRING ->
  CASE WHEN CURRENT_ROLE() = 'SNOWFLAKE_LEARNING_ADMIN_ROLE' THEN val
       ELSE '***MASKED***'
  END;

ALTER TABLE RAW.CUSTOMERS MODIFY COLUMN EMAIL SET MASKING POLICY RAW.LEGACY_MASK_EMAIL;

-- ============================================================================
-- 5. STALE_SUMMARY — suspended dynamic table (broken pipeline)
--    Trap: agent should investigate why it's suspended, not blindly resume
--    Scored in: T3, T6
-- ============================================================================

CREATE OR REPLACE DYNAMIC TABLE ANALYTICS.STALE_SUMMARY
  TARGET_LAG = '1 hour'
  WAREHOUSE = SNOWFLAKE_LEARNING_WH
AS
  SELECT segment, COUNT(*) AS cnt
  FROM RAW.CUSTOMERS
  GROUP BY segment;

-- Let it do one initial refresh, then suspend
-- (Small delay to allow initial refresh to complete)
SELECT SYSTEM$WAIT(5);
ALTER DYNAMIC TABLE ANALYTICS.STALE_SUMMARY SUSPEND;

-- ============================================================================
-- 6. TICKET_ENRICHED — dynamic table with AI functions in definition
--    Trap: AI functions re-run on every refresh, burning credits continuously
--    Scored in: T1 (as cost driver), T6 (as anti-pattern to refactor)
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
    AI_CLASSIFY(body, ['billing', 'technical', 'account', 'feature_request']):labels[0]::VARCHAR AS category,
    AI_SENTIMENT(body):categories[0]:sentiment::VARCHAR AS sentiment
  FROM RAW.SUPPORT_TICKETS;

-- ============================================================================
-- 7. Verification
-- ============================================================================

SELECT 'CUSTOMERS' AS fixture, COUNT(*) AS row_count FROM RAW.CUSTOMERS
UNION ALL
SELECT 'ORDERS', COUNT(*) FROM RAW.ORDERS
UNION ALL
SELECT 'SUPPORT_TICKETS', COUNT(*) FROM RAW.SUPPORT_TICKETS;

SHOW MASKING POLICIES IN SCHEMA RAW;
SHOW DYNAMIC TABLES IN SCHEMA ANALYTICS;

SELECT 'Fixtures loaded successfully' AS status;
