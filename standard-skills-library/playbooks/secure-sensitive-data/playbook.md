---
type: playbook
name: secure-sensitive-data
domain: data-security
depends_on:
  - data-classification
  - masking-policies
  - row-access-policies
  - projection-policies
  - account-usage-views
---

# Secure Sensitive Data

Discover sensitive data, apply protection policies, and verify coverage — end to end.

## Objective

After completing this playbook, the user will have:

1. An inventory of sensitive columns across their target database(s)
2. Masking policies applied to columns containing PII/sensitive data
3. Projection policies blocking direct query of high-sensitivity columns (if needed)
4. Row access policies on tables requiring role-based row filtering (if needed)
5. Verification that policies are working correctly
6. Governance queries to monitor ongoing compliance

## Prerequisites

- ACCOUNTADMIN or SECURITYADMIN role (for creating policies and classification profiles)
- A warehouse set in session context
- Target database and schema identified

## Pre-execution Probes

Before starting, the agent should probe the environment:

```sql
SHOW MASKING POLICIES IN ACCOUNT;
SHOW ROW ACCESS POLICIES IN ACCOUNT;
SHOW PROJECTION POLICIES IN ACCOUNT;
SELECT table_catalog, table_schema, table_name
  FROM <target>.INFORMATION_SCHEMA.TABLES;
```

These probes reveal existing policies (to avoid collisions) and the scope of tables to classify.

## Steps

### Step 1: Discover sensitive data

Run classification against target tables to build an inventory of sensitive columns.

Reference: `primitives/data-classification`

For a small scope (< 10 tables), classify individually:

```sql
CALL SYSTEM$CLASSIFY('mydb.myschema.customers');
```

For larger scopes, use a classification profile:

```sql
CALL SYSTEM$CLASSIFY('mydb', {'profile': 'full_scan'});
```

Parse results to find sensitive columns:

```sql
SELECT
  f.value:column_name::STRING AS column_name,
  f.value:semantic_category::STRING AS category,
  f.value:privacy_category::STRING AS privacy,
  f.value:confidence::STRING AS confidence
FROM TABLE(RESULT_SCAN(LAST_QUERY_ID())) r,
     LATERAL FLATTEN(input => PARSE_JSON(r."classify")) f
WHERE f.value:confidence::STRING IN ('HIGH', 'MEDIUM');
```

**Checkpoint:**
  severity: review
  present: "Classification results grouped by category and confidence level"

The agent generates options based on results — at minimum: approve, modify (re-scan specific tables or adjust confidence threshold), abort, different-approach.

Expected errors:

| Pattern | Recovery | Retryable |
|---------|----------|-----------|
| `Insufficient privileges` | Grant OWNERSHIP or SELECT on target tables to {admin_role} | No — escalate |
| `does not exist` | Verify target_scope spelling and that database/schema exist | Yes |

### Step 2: Design the protection strategy

Propose a grouped protection strategy based on classification results. This step gathers the `protection_strategy` input.

| Data Type Found | Recommended Policy | Rationale |
|----------------|-------------------|-----------|
| SSN, credit card, account numbers | Masking + projection | Values hidden; column blocked from SELECT for non-privileged roles |
| Email, phone, address | Masking | Values visible only to authorized roles |
| Salary, medical records | Row access | Entire rows restricted by role |
| Internal IDs that reveal structure | Projection | Column not queryable by certain roles |
| Names, dates of birth | Masking | Partially masked for non-privileged roles |

Present the strategy as a grouped proposal (not per-column questions). The user approves the batch.

**Checkpoint:**
  severity: review
  present: "Complete protection plan — which columns get which policy type, which roles are exempt, which existing policies are kept"

Options: approve, modify, abort, different-approach.

### Step 3: Create masking policies

Build reusable masking policies using the split pattern for maintainability.

Reference: `primitives/masking-policies`

```sql
CREATE OR REPLACE FUNCTION governance.policies.should_unmask()
RETURNS BOOLEAN
MEMOIZABLE
AS
$$
  SELECT IS_ROLE_IN_SESSION('DATA_STEWARD')
      OR IS_ROLE_IN_SESSION('ANALYST_FULL')
$$;

CREATE OR ALTER MASKING POLICY governance.policies.mask_string
  AS (val STRING) RETURNS STRING ->
    CASE
      WHEN governance.policies.should_unmask() THEN val
      ELSE '***MASKED***'
    END;

ALTER TABLE mydb.myschema.customers
  MODIFY COLUMN email SET MASKING POLICY governance.policies.mask_string;
```

Use `CREATE OR ALTER` to avoid collisions with pre-existing policies found during probing.

**Compensation:**
```sql
DROP FUNCTION IF EXISTS governance.policies.should_unmask();
DROP MASKING POLICY IF EXISTS governance.policies.mask_string;
-- For each column that had policy applied:
ALTER TABLE {table} MODIFY COLUMN {column} UNSET MASKING POLICY;
```

**Creates:**
- type: function
  name: "governance.policies.should_unmask"
- type: masking_policy
  name: "governance.policies.mask_string"

Expected errors:

| Pattern | Recovery | Retryable |
|---------|----------|-----------|
| `Insufficient privileges` | Grant CREATE MASKING POLICY to {admin_role} | No — escalate |
| `already exists` | Use CREATE OR ALTER syntax | Yes |
| `column already has a masking policy` | UNSET existing policy first, then SET new one | Yes |

**Sub-step 3b: Create projection policies (if strategy requires)**

If the protection strategy includes projection policies, create them here.

Reference: `primitives/projection-policies`

```sql
CREATE OR ALTER PROJECTION POLICY governance.policies.block_sensitive
  AS () RETURNS PROJECTION_CONSTRAINT ->
    CASE
      WHEN IS_ROLE_IN_SESSION('DATA_STEWARD') THEN PROJECTION_CONSTRAINT(ALLOW => TRUE)
      ELSE PROJECTION_CONSTRAINT(ALLOW => FALSE)
    END;

ALTER TABLE mydb.myschema.customers
  MODIFY COLUMN ssn SET PROJECTION POLICY governance.policies.block_sensitive;
```

**Compensation:**
```sql
DROP PROJECTION POLICY IF EXISTS governance.policies.block_sensitive;
ALTER TABLE {table} MODIFY COLUMN {column} UNSET PROJECTION POLICY;
```

**Creates:**
- type: projection_policy
  name: "governance.policies.block_sensitive"

### Step 4: Create row access policies (conditional)

**This step is conditional.** Skip if the protection strategy from step 2 does not include row-level restrictions. Emit a `step_skipped` event with the reason.

Apply row-level filtering for tables where certain roles should only see a subset of rows.

Reference: `primitives/row-access-policies`

```sql
CREATE OR REPLACE ROW ACCESS POLICY governance.policies.department_filter
  AS (department_col STRING) RETURNS BOOLEAN ->
    IS_ROLE_IN_SESSION('HR_ADMIN')
    OR department_col = CURRENT_SESSION_CONTEXT('department');

ALTER TABLE mydb.myschema.employees
  ADD ROW ACCESS POLICY governance.policies.department_filter
  ON (department);
```

**Compensation:**
```sql
ALTER TABLE {table} DROP ROW ACCESS POLICY governance.policies.department_filter;
DROP ROW ACCESS POLICY IF EXISTS governance.policies.department_filter;
```

**Creates:**
- type: row_access_policy
  name: "governance.policies.department_filter"

Expected errors:

| Pattern | Recovery | Retryable |
|---------|----------|-----------|
| `already has a ROW ACCESS POLICY` | Only one RAP per table — drop existing first or modify it | No — escalate (requires user decision) |

### Step 5: Verify policies are working

Test that policies behave correctly across privileged and non-privileged roles. The agent should test with at least two roles: one that should see masked/blocked data and one that should see real data.

```sql
-- Test as a restricted role
USE ROLE analyst_restricted;
SELECT email, phone FROM mydb.myschema.customers LIMIT 5;
-- Expected: masked values

-- Test projection block
SELECT ssn FROM mydb.myschema.customers LIMIT 1;
-- Expected: error (projection policy denies access)

-- Test as an authorized role
USE ROLE data_steward;
SELECT email, phone, ssn FROM mydb.myschema.customers LIMIT 5;
-- Expected: real values
```

**Checkpoint:**
  severity: critical
  present: "Verification results for each policy type and role combination"

This checkpoint is `critical` because it confirms security controls are working correctly before moving to production monitoring. Options: approve (proceed to monitoring), modify (adjust policies), abort (policies are in place, skip monitoring), different-approach.

### Step 6: Set up ongoing monitoring

Create governance queries to track policy coverage and access patterns.

Reference: `primitives/account-usage-views`

```sql
-- Policy coverage inventory
SELECT *
FROM SNOWFLAKE.ACCOUNT_USAGE.POLICY_REFERENCES
WHERE policy_kind IN ('MASKING_POLICY', 'PROJECTION_POLICY', 'ROW_ACCESS_POLICY')
ORDER BY created_on DESC;

-- Gap analysis: sensitive columns without protection
SELECT DISTINCT
  cl.table_name,
  cl.column_name,
  cl.semantic_category
FROM TABLE(INFORMATION_SCHEMA.DATA_CLASSIFICATION_LATEST('mydb')) cl
LEFT JOIN SNOWFLAKE.ACCOUNT_USAGE.POLICY_REFERENCES pr
  ON cl.table_name = pr.ref_entity_name
  AND cl.column_name = pr.ref_column_name
  AND pr.policy_kind IN ('MASKING_POLICY', 'PROJECTION_POLICY')
WHERE pr.policy_name IS NULL
  AND cl.confidence = 'HIGH';

-- Recent access to protected columns (last 30 days)
SELECT
  query_start_time,
  user_name,
  role_name,
  direct_objects_accessed
FROM SNOWFLAKE.ACCOUNT_USAGE.ACCESS_HISTORY
WHERE query_start_time > DATEADD('day', -30, CURRENT_TIMESTAMP())
ORDER BY query_start_time DESC;
```

Note: ACCOUNT_USAGE views have 120-minute latency. Governance queries will reflect current state after approximately 2 hours.

## Anti-patterns

| Mistake | Impact | Instead |
|---------|--------|---------|
| Creating per-table masking policies | Policy sprawl — dozens of identical policies that are hard to update | Use generic reusable policies with the split pattern |
| Using `CURRENT_ROLE()` in policy conditions | Fails when roles are inherited through hierarchy | Use `IS_ROLE_IN_SESSION()` which checks the full role hierarchy |
| Skipping classification and manually guessing which columns have PII | Missed columns = unprotected sensitive data | Always run `SYSTEM$CLASSIFY` first for a complete inventory |
| Applying policies without testing | Policies may be too restrictive (blocking legitimate access) or too permissive | Test with multiple roles before deploying to production |
| Skipping environment probes | Creates policies that collide with existing ones | Always probe for existing policies before creating new ones |
