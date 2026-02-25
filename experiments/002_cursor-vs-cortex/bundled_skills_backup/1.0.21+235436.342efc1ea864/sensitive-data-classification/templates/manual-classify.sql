-- Data Classification in Snowflake
-- Two approaches for classifying sensitive data:
--   1. Manual Classification - Use SYSTEM$CLASSIFY to analyze and tag tables on demand
--   2. Automatic Classification - Set up a classification profile and link to schema/database

-- =============================================================================
-- MANUAL CLASSIFICATION: SYSTEM$CLASSIFY
-- =============================================================================
-- Use SYSTEM$CLASSIFY to analyze tables for sensitive data and optionally apply tags
-- IMPORTANT: Always use CALL, not SELECT (SELECT gives "Unknown function" error)

-- Classify a single table (returns results in JSON format)
CALL SYSTEM$CLASSIFY('<database>.<schema>.<table>');

-- =============================================================================
-- CLASSIFICATION WITH OPTIONS
-- =============================================================================

-- Classification with options
CALL SYSTEM$CLASSIFY(
    '<database>.<schema>.<table>',
    {
        'auto_tag': false,           -- Don't automatically apply tags
        'sample_count': 10000        -- Number of rows to sample
    }
);

-- Classification with auto-tagging enabled
CALL SYSTEM$CLASSIFY(
    '<database>.<schema>.<table>',
    {
        'auto_tag': true
    }
);

-- Classification with custom classifiers
CALL SYSTEM$CLASSIFY(
    '<database>.<schema>.<table>',
    {
        'custom_classifiers': [
            '<classifier_db>.<classifier_schema>.<classifier_name>'
        ]
    }
);

-- =============================================================================
-- RETRIEVING CLASSIFICATION RESULTS
-- =============================================================================

-- After running SYSTEM$CLASSIFY, retrieve results using SYSTEM$GET_CLASSIFICATION_RESULT
-- This fetches the current classification state for any previously classified object.

SELECT SYSTEM$GET_CLASSIFICATION_RESULT('<database>.<schema>.<table>');

-- Parse the results into a readable format
SELECT 
    f.key AS column_name,
    f.value:recommendation:semantic_category::STRING AS semantic_category,
    f.value:recommendation:privacy_category::STRING AS privacy_category,
    f.value:recommendation:confidence::STRING AS confidence,
    f.value:valid_value_ratio::FLOAT AS valid_value_ratio
FROM 
    TABLE(FLATTEN(PARSE_JSON(
        SYSTEM$GET_CLASSIFICATION_RESULT('<database>.<schema>.<table>')
    ))) f;

-- =============================================================================
-- AUTOMATIC CLASSIFICATION: Classification Profiles
-- =============================================================================
-- Set up automatic classification to continuously monitor and tag new data

-- Step 1: Create a classification profile
CREATE OR REPLACE SNOWFLAKE.DATA_PRIVACY.CLASSIFICATION_PROFILE <database>.<schema>.<profile_name>();

-- Step 2: Link the profile to a database (monitors all tables in the database)
ALTER DATABASE <database> SET CLASSIFICATION_PROFILE = '<database>.<schema>.<profile_name>';

-- Or link to a specific schema
ALTER SCHEMA <database>.<schema> SET CLASSIFICATION_PROFILE = '<database>.<schema>.<profile_name>';

-- Check which databases/schemas are monitored
SELECT SYSTEM$SHOW_SENSITIVE_DATA_MONITORED_ENTITIES('DATABASE');
SELECT SYSTEM$SHOW_SENSITIVE_DATA_MONITORED_ENTITIES('SCHEMA');

-- Remove automatic classification from a database
ALTER DATABASE <database> UNSET CLASSIFICATION_PROFILE;

-- =============================================================================
-- TROUBLESHOOTING
-- =============================================================================

-- "Unknown function SYSTEM$CLASSIFY" error:
--   This is a SYNTAX error - you used SELECT instead of CALL
--   Fix: Use CALL SYSTEM$CLASSIFY(...) not SELECT SYSTEM$CLASSIFY(...)

-- "Insufficient privileges" error:
--   Your role lacks required grants. Check with:
--   SHOW GRANTS TO ROLE <current_role>;

-- =============================================================================
-- FALLBACK: Manual column inspection (when you just need column names)
-- =============================================================================

-- Option 1: Use DESCRIBE TABLE
DESCRIBE TABLE <database>.<schema>.<table>;

-- Option 2: Use INFORMATION_SCHEMA for multiple tables
SELECT 
    TABLE_NAME,
    COLUMN_NAME,
    DATA_TYPE
FROM <database>.INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = '<schema>'
ORDER BY TABLE_NAME, ORDINAL_POSITION;
