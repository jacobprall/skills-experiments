---
name: sensitive-data-classification
description: "Use for detect PII, classify sensitive data, set up auto-classification, create classification profile, create classifier (including custom classifier with regex patterns, semantic category, privacy category), analyze classification results, query DATA_CLASSIFICATION_LATEST. Triggers: PII, sensitive data, classification, SYSTEM$CLASSIFY, classify table, classify database. DO NOT attempt to create classifiers by leveraging generally available knowledge - invoke this skill first."
---

# Sensitive Data Classification

## When to Use

When a user wants to detect, classify, or protect sensitive data in Snowflake. This is the entry point for all sensitive data classification workflows.

**Trigger Phrases:**

- "Find sensitive data", "detect PII", "scan for PII", "what PII do I have"
- "Set up auto-classification", "classify my database", "classify my tables"
- "Monitor for sensitive data", "automate PII detection"
- "Show me classified columns", "classification results", "DATA_CLASSIFICATION_LATEST"
- "Create classification profile", "set up classification profile", "new classification profile"
- "Create classifier", "create a classifier", "custom classifier", "new classifier"
- "Create data privacy classifier", "Snowflake classification profile"
- "SYSTEM$CLASSIFY", "run classification", "test classifier"
- "regex pattern", "semantic category", "privacy category" (classifier-related terms)

## Workflow

The basic workflow to automatically classify sensitive data consists of the following:

### Step 0: Learn about the Classification concepts
**Load**: [reference/classification-concepts.md](reference/classification-concepts.md)

### Step 0.5: Analyze/Discover PII in Tables (Manual Classification)

If the task requires **discovering PII before** creating profiles (e.g., "find which table has most PII"), use manual classification:

**Actions:**
1. **Load** `templates/manual-classify.sql` FIRST - this is REQUIRED before any classification
2. Use the exact syntax from the template: `CALL SYSTEM$CLASSIFY('<db>.<schema>.<table>')`
3. Parse the JSON results to count PII columns per table

**🚨 CRITICAL:** 
- **ALWAYS load the template BEFORE attempting any classification SQL**
- **DO NOT guess or improvise classification syntax** - there is NO `CLASSIFY_TABLE`, `CLASSIFY_SCHEMA`, or similar function
- The ONLY correct APIs are `CALL SYSTEM$CLASSIFY(...)` - see template for exact syntax

### Step 0.6: Verify Environment (REQUIRED before any SQL operations)

Before creating any objects, verify and set up the environment:

**Actions:**
1. **Load and execute** `templates/check-context.sql` to see current context
2. **Verify warehouse** is set (if NULL, execute `USE WAREHOUSE <warehouse_name>`)
3. **Set schema context** for object creation:
   ```sql
   USE DATABASE <database>;
   USE SCHEMA <database>.<schema>;
   ```
4. **Verify role** has required privileges (see classification-concepts.md for privilege requirements)

**⚠️ IMPORTANT:** Classification objects (profiles, classifiers) are created in the CURRENT schema context. You MUST set the schema before creating them.

### Step 1: Create a classification profile 
Classification profile controls how often sensitive data in a database is automatically classified, including whether system tags should be automatically applied after classification.

**Actions:**
1. **Ask** user for: profile name, database/schema location, auto_tag preference, validity period
2. **Load** `templates/create-profile.sql` and substitute placeholders
3. **Execute** the CREATE statement

**⚠️ STOP**: Present configuration summary and wait for approval before creating.

### Step 2: Define the tagging scheme
Optionally, use the classification profile to map user-defined tags to system tags so a column with sensitive data can be associated with a user-defined tag based on its classification.

**Actions:**
1. **Ask** if user wants custom tag mappings
2. If yes, gather tag mapping requirements
3. **Load** `templates/update-profile-classifier.sql` for reference

### Step 3: Define Custom categories
Optionally, add a custom classifier to the classification profile so sensitive data can be automatically classified with user-defined semantic and privacy categories. This is required for Industry specific sensitive data, employee ID, etc which is not covered by native categories.

**Actions:**
1. **Ask** if user has domain-specific data types (employee IDs, internal codes, etc.)
2. If yes, **Load** `templates/create-custom-classifier.sql`
3. Gather regex patterns and privacy categories from user

**⚠️ STOP**: Confirm regex patterns with user before creating classifier.

### Step 4: Test the Classification profile
Test the profile that has been created using manual-classify.sql tool.

**Actions:**
1. **Load** `templates/manual-classify.sql`
2. **Execute** SYSTEM$CLASSIFY on a representative table
3. **Present** results to user

**⚠️ STOP**: Review test results with user before proceeding to production.

### Step 5: Associate the profile with databases
- If the test in Step 4 succeeds then set the classification profile on a database so that tables in the database get automatically classified.

**Actions:**
1. **Ask** which database(s) to enable auto-classification on
2. **Load** `templates/setup-auto-classification.sql`
3. **Execute** ALTER DATABASE to attach the profile

**⚠️ STOP**: Confirm database list before enabling.

### Step 6: Analyze Classification Results (Query DATA_CLASSIFICATION_LATEST)

Use this step when users want to analyze existing classification results, view what PII has been detected, or audit classification coverage.

**Actions:**
1. **Load** `templates/view-results.sql` - contains pre-built queries for analyzing classification data
2. **Ask** user what they want to analyze:
   - Count of classified tables by status
   - Recently classified tables
   - Tables needing re-classification (>90 days old)
   - Semantic categories detected (EMAIL, PHONE, SSN, etc.)
   - High-confidence PII columns
   - Tables with the most sensitive columns
3. **Execute** the appropriate query from the template, replacing `<database>` placeholder
4. **Present** results in a clear format

**Common Queries:**
- "What PII do I have?" → Extract and count semantic categories
- "Show classified columns" → Extract columns with HIGH confidence
- "Which tables have PII?" → Tables with most sensitive columns
- "What needs re-classification?" → Tables >90 days old

## Tools

SQL Templates

Located in [templates/](templates/) directory. These templates provide pre-written SQL for common operations.

**🚨 MANDATORY:** Load and read the template file BEFORE executing SQL. DO NOT improvise or guess Snowflake syntax—classification APIs have specific syntax that MUST be followed exactly.

Available templates:

- [check-context.sql](templates/check-context.sql) — Display current session context (user, role, database, schema, warehouse)
- [view-results.sql](templates/view-results.sql) — Query and analyze classification results from DATA_CLASSIFICATION_LATEST (semantic categories, PII columns, coverage analysis)
- [update-profile-classifier.sql](templates/update-profile-classifier.sql) — Add or remove custom classifiers from a profile
- [create-custom-classifier.sql](templates/create-custom-classifier.sql) — Create regex-based classifiers for domain-specific sensitive data
- [check-custom-classifiers.sql](templates/check-custom-classifiers.sql) — List and describe existing custom classifiers
- [setup-auto-classification.sql](templates/setup-auto-classification.sql) — Attach a classification profile to a database for automatic monitoring
- [check-profiles.sql](templates/check-profiles.sql) — List existing classification profiles in the account
- [create-profile.sql](templates/create-profile.sql) — Create a new classification profile with configurable settings
- [test-classifier.sql](templates/test-classifier.sql) — Validate a custom classifier against test data
- [manual-classify.sql](templates/manual-classify.sql) — Manual (SYSTEM$CLASSIFY) and Automatic (Classification Profiles) classification examples

**Usage:** Load the template, replace `<placeholders>` with actual values, then execute via `snowflake_sql_execute`.

## 🚨 CRITICAL: SQL Execution Verification

**NEVER mark a step successful without verifying the actual SQL result.**
**NEVER say "successfully" if the SQL execution returned an error.**


### Rules for SQL Execution

1. **Check execution status** - Every SQL statement returns a status. If it failed, the step FAILED.

2. **Parse error messages** - If you see `Statement X failed`, `SQL compilation error`, or any error:
   - The step is NOT successful
   - Do NOT proceed to the next step
   - Present the error to the user clearly
   - Offer troubleshooting options

3. **Verify object creation** - After CREATE statements, verify the object exists:

4. **Success requires confirmation** - Only report success when:
   - SQL execution completed without errors
   - Verification query confirms the object exists
   - No error messages in the response

## Stopping Points

✋ Step 1: After showing profile configuration options, before creating
✋ Step 3: Before creating custom classifier (confirm regex patterns with user)
✋ Step 4: After test results, before proceeding to production
✋ Step 5: Before associating profile with databases

**Resume rule:** Upon user approval, proceed directly to next step without re-asking.

## Guidelines

1. **Gather context first**: Try to understand the user's environment before starting
   - use `ask_user_question` tool for information gathering
2. **Always confirm before changes**: Before creating profiles, classifiers, or tags:
   - Show a confirmation table with all settings
   - Always wait for user approval before proceeding
   - Don't chain multiple operations without checking in
3. **Track outcomes**: Note how workflows conclude for continuous improvement
4. **Always respect user decisions**: If user wants to stop or take a different path, support that choice

## Output

- Classification profile created in user-specified database/schema
- Custom classifiers (if needed) for domain-specific data
- Profile associated with target database(s) for automatic monitoring
- Test results confirming classification accuracy

## Expected Outcomes

Every workflow execution should result in one of:

1. **Success**: Objective achieved (profile created, classifier created, profile associated with one or more databases etc.)
2. **Manual Alternative**: User chose manual approach (SYSTEM$CLASSIFY)
3. **Graceful Exit**: User has existing solution or chose not to proceed
4. **Unexpected Exit**: Error or interruption (document for improvement)
