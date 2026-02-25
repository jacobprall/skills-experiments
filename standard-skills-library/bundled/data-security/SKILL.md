---
name: data-security
description: "**[REQUIRED]** for classifying sensitive data, creating masking policies, row access policies, projection policies, auditing data access, and end-to-end data protection workflows. Uses SYSTEM$CLASSIFY for PII detection (not manual identification), IS_ROLE_IN_SESSION() for context functions (not CURRENT_ROLE()), and split-pattern masking (separate policies per data type). Covers account usage views for governance auditing. Triggers: classify, PII, sensitive data, mask, masking policy, row access policy, projection policy, protect, audit, governance, access history, policy inventory, SYSTEM$CLASSIFY, data classification, column security, role-based access."
---

# Data Security

Routes data security requests to the appropriate primitive or playbook.

## Routing Logic

```
Start
  ├─ User wants END-TO-END data protection?
  │   (classify + mask + verify in one workflow)
  │   └─ YES → Use the Secure Sensitive Data playbook below
  │
  ├─ User wants to CLASSIFY data / find PII?
  │   └─ YES → Use the Data Classification reference below
  │
  ├─ User wants MASKING POLICIES?
  │   └─ YES → Use the Masking Policies reference below
  │
  ├─ User wants ROW ACCESS POLICIES?
  │   └─ YES → Use the Row Access Policies reference below
  │
  ├─ User wants PROJECTION POLICIES?
  │   └─ YES → Use the Projection Policies reference below
  │
  └─ User wants to AUDIT access or review policies?
      └─ YES → Use the Account Usage Views reference below
```

---

# Playbook: Secure Sensitive Data

End-to-end workflow for discovering and protecting sensitive data. Covers classification through verification.

## Objective

Protect sensitive data in a Snowflake schema by:
1. Classifying columns to find PII/sensitive data
2. Creating appropriate masking policies
3. Applying policies to classified columns
4. Verifying protection works correctly

## Steps

### Step 1: Discover tables in scope

```sql
SELECT table_catalog, table_schema, table_name, row_count
FROM <db>.INFORMATION_SCHEMA.TABLES
WHERE table_schema = '<schema>'
  AND table_type = 'BASE TABLE'
ORDER BY table_name;
```

Present to user: number of tables, their names, and row counts.

### Step 2: Classify columns with SYSTEM$CLASSIFY

**CRITICAL: Always use SYSTEM$CLASSIFY — never manually guess which columns contain PII.**

```sql
-- Classify a single table
SELECT *
FROM TABLE(
  SYSTEM$CLASSIFY('<db>.<schema>.<table>', {'auto_tag': true})
);
```

Parse the result JSON. Each row contains:
- `column_name` — the classified column
- `semantic_category` — what type of data (EMAIL, PHONE, NAME, etc.)
- `privacy_category` — sensitivity level (IDENTIFIER, QUASI_IDENTIFIER, SENSITIVE)
- `confidence` — classification confidence (0.0–1.0)
- `recommendation` — suggested action (MASK, RESTRICT, etc.)

**Best practice:** Classify ALL tables in scope, then aggregate results.

```sql
-- Classify all tables in schema (run for each table)
CALL SYSTEM$CLASSIFY('<db>.<schema>.<table_1>', {'auto_tag': true});
CALL SYSTEM$CLASSIFY('<db>.<schema>.<table_2>', {'auto_tag': true});
```

Present classification results to user before proceeding.

### Step 3: Design masking policies

**Use the split pattern — one policy per data type, not one per column.**

| Data Type | Policy Name | Mask Function |
|-----------|-------------|---------------|
| STRING (email, name, phone, SSN) | `MASK_STRING_PII` | `'***MASKED***'` |
| DATE (date of birth) | `MASK_DATE_PII` | `'1900-01-01'::DATE` |
| NUMBER (if applicable) | `MASK_NUMBER_PII` | `0` or `-1` |

**Context function: Always use `IS_ROLE_IN_SESSION()`, NEVER `CURRENT_ROLE()`.**

`IS_ROLE_IN_SESSION()` checks the entire role hierarchy. `CURRENT_ROLE()` only checks the active role, which breaks when users have inherited roles.

### Step 4: Create masking policies

```sql
CREATE OR REPLACE MASKING POLICY <db>.<schema>.MASK_STRING_PII
  AS (val STRING) RETURNS STRING ->
    CASE
      WHEN IS_ROLE_IN_SESSION('<admin_role>') THEN val
      ELSE '***MASKED***'
    END;

CREATE OR REPLACE MASKING POLICY <db>.<schema>.MASK_DATE_PII
  AS (val DATE) RETURNS DATE ->
    CASE
      WHEN IS_ROLE_IN_SESSION('<admin_role>') THEN val
      ELSE '1900-01-01'::DATE
    END;
```

### Step 5: Apply policies to classified columns

```sql
ALTER TABLE <db>.<schema>.<table>
  MODIFY COLUMN <column>
  SET MASKING POLICY <db>.<schema>.MASK_STRING_PII;
```

Apply the appropriate policy based on the column's data type:
- STRING columns with PII → `MASK_STRING_PII`
- DATE columns with PII → `MASK_DATE_PII`
- NUMBER columns with PII → `MASK_NUMBER_PII`

### Step 6: Verify protection

Test with a restricted role:

```sql
USE ROLE <restricted_role>;
SELECT * FROM <db>.<schema>.<table> LIMIT 5;
-- Sensitive columns should show masked values
```

Test with the admin role:

```sql
USE ROLE <admin_role>;
SELECT * FROM <db>.<schema>.<table> LIMIT 5;
-- Should show real values
```

Present verification results to user.

## Anti-patterns

| Mistake | Impact | Instead |
|---------|--------|---------|
| Skipping `SYSTEM$CLASSIFY` | Misses PII columns or misidentifies data types | Always run classification first |
| One policy per column | Policy sprawl, maintenance burden | Split pattern: one policy per data type |
| Using `CURRENT_ROLE()` | Breaks role hierarchy, users with inherited roles see masked data | Use `IS_ROLE_IN_SESSION()` |
| Not verifying with restricted role | Can't confirm masking actually works | Always test with both admin and restricted roles |

---

# Primitive: Data Classification

Discover sensitive data using Snowflake's built-in classification engine.

## Syntax

### Classify a single table

```sql
SELECT *
FROM TABLE(
  SYSTEM$CLASSIFY('<db>.<schema>.<table>', {'auto_tag': true})
);
```

### Classify with custom settings

```sql
SELECT *
FROM TABLE(
  SYSTEM$CLASSIFY(
    '<db>.<schema>.<table>',
    {
      'auto_tag': true,
      'sample_count': 10000,
      'custom_classifiers': ['<db>.<schema>.<classifier_name>']
    }
  )
);
```

### View classification results (after auto-tagging)

```sql
SELECT *
FROM SNOWFLAKE.ACCOUNT_USAGE.DATA_CLASSIFICATION_LATEST
WHERE table_name = '<TABLE>'
  AND schema_name = '<SCHEMA>';
```

### Create a custom classifier

```sql
CREATE OR REPLACE SNOWFLAKE.DATA_PRIVACY.CUSTOM_CLASSIFIER <db>.<schema>.<name>();

-- Add regex-based rule
ALTER SNOWFLAKE.DATA_PRIVACY.CUSTOM_CLASSIFIER <db>.<schema>.<name>()
  ADD INSTANCE RULE <rule_name>
    REGEX '<pattern>'
    SEMANTIC_CATEGORY '<category>'
    PRIVACY_CATEGORY 'IDENTIFIER';
```

## Parameters

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `auto_tag` | boolean | false | Automatically apply system tags to classified columns |
| `sample_count` | integer | 10000 | Number of rows to sample for classification |
| `custom_classifiers` | array | [] | Additional custom classifiers to use |

## Result columns

| Column | Description |
|--------|-------------|
| `column_name` | Classified column |
| `semantic_category` | Data type: EMAIL, PHONE, NAME, US_SSN, DATE_OF_BIRTH, etc. |
| `privacy_category` | IDENTIFIER, QUASI_IDENTIFIER, SENSITIVE |
| `confidence` | 0.0 to 1.0 — higher means more confident |
| `recommendation` | MASK, RESTRICT, or NULL |

## Constraints

- Requires OWNERSHIP or MANAGE GRANTS on target tables
- Classification samples data — not a full table scan
- `auto_tag` requires TAG privileges on the schema
- Results may miss columns with fewer than ~100 non-null values

## Anti-patterns

| Pattern | Why It Fails | Instead |
|---------|-------------|---------|
| Manually identifying PII columns | Misses columns, doesn't scale | Use `SYSTEM$CLASSIFY` |
| Running classification without `auto_tag` | Results are ephemeral — no persistent record | Use `auto_tag: true` for persistent tags |
| Classifying views instead of base tables | Views don't own the data | Classify the underlying base tables |

---

# Primitive: Masking Policies

Column-level security that returns redacted values to unauthorized roles.

## Syntax

```sql
CREATE [ OR REPLACE ] MASKING POLICY <db>.<schema>.<name>
  AS (val <type>) RETURNS <type> ->
    CASE
      WHEN IS_ROLE_IN_SESSION('<authorized_role>') THEN val
      ELSE <masked_value>
    END;
```

### Apply to column

```sql
ALTER TABLE <table>
  MODIFY COLUMN <column>
  SET MASKING POLICY <policy_name>;
```

### Remove from column

```sql
ALTER TABLE <table>
  MODIFY COLUMN <column>
  UNSET MASKING POLICY;
```

### Replace policy on column

```sql
ALTER TABLE <table>
  MODIFY COLUMN <column>
  SET MASKING POLICY <new_policy>
  FORCE;
```

## The Split Pattern (recommended)

Create one policy per data type, not one per column:

```sql
-- String PII (email, name, phone, SSN)
CREATE OR REPLACE MASKING POLICY governance.policies.mask_string_pii
  AS (val STRING) RETURNS STRING ->
    CASE WHEN IS_ROLE_IN_SESSION('DATA_ADMIN') THEN val ELSE '***MASKED***' END;

-- Date PII (date of birth)
CREATE OR REPLACE MASKING POLICY governance.policies.mask_date_pii
  AS (val DATE) RETURNS DATE ->
    CASE WHEN IS_ROLE_IN_SESSION('DATA_ADMIN') THEN val ELSE '1900-01-01'::DATE END;

-- Number PII (if needed)
CREATE OR REPLACE MASKING POLICY governance.policies.mask_number_pii
  AS (val NUMBER) RETURNS NUMBER ->
    CASE WHEN IS_ROLE_IN_SESSION('DATA_ADMIN') THEN val ELSE -1 END;
```

## Context Functions

| Function | Behavior | Use When |
|----------|----------|----------|
| `IS_ROLE_IN_SESSION('X')` | TRUE if X is the active role OR any ancestor | **Always use this** |
| `CURRENT_ROLE()` | Returns only the currently active role name | **Never use for masking** — breaks hierarchy |
| `IS_DATABASE_ROLE_IN_SESSION('X')` | TRUE if database role X is active | Database-scoped roles |

## Discovery

```sql
-- Find all masking policies
SHOW MASKING POLICIES IN DATABASE <db>;

-- Find all policy-column assignments
SELECT *
FROM TABLE(<db>.INFORMATION_SCHEMA.POLICY_REFERENCES(
  ref_entity_domain => 'TABLE',
  ref_entity_name => '<db>.<schema>.<table>'
));

-- Account-wide policy inventory
SELECT policy_name, policy_schema, created
FROM SNOWFLAKE.ACCOUNT_USAGE.MASKING_POLICIES
WHERE deleted IS NULL;
```

## Anti-patterns

| Pattern | Why It Fails | Instead |
|---------|-------------|---------|
| `CURRENT_ROLE() = 'ADMIN'` | Ignores inherited roles — users with admin through hierarchy see masked data | `IS_ROLE_IN_SESSION('ADMIN')` |
| One policy per column | Policy sprawl — 50 columns = 50 policies | Split pattern: one policy per data type |
| Masking policy returns different type | SQL error — return type must match input type | Ensure `AS (val STRING) RETURNS STRING` matches |
| Forgetting to test with restricted role | Can't confirm masking works | Always verify with both authorized and unauthorized roles |

---

# Primitive: Row Access Policies

Row-level security that filters which rows a user can see based on role, identity, or a mapping table.

## Syntax

```sql
CREATE [ OR REPLACE ] ROW ACCESS POLICY <name>
  AS (<arg_name> <arg_type> [, ...])
  RETURNS BOOLEAN -> <body>;
```

### Apply to table

```sql
ALTER TABLE <table>
  ADD ROW ACCESS POLICY <policy_name> ON (<column> [, ...]);
```

### Remove from table

```sql
ALTER TABLE <table>
  DROP ROW ACCESS POLICY <policy_name>;
```

## Examples

### Basic: Role-based row filtering

```sql
CREATE OR REPLACE ROW ACCESS POLICY governance.policies.region_filter
  AS (region_col STRING) RETURNS BOOLEAN ->
    IS_ROLE_IN_SESSION('GLOBAL_ADMIN')
    OR (region_col = 'US' AND IS_ROLE_IN_SESSION('REGION_US'))
    OR (region_col = 'EU' AND IS_ROLE_IN_SESSION('REGION_EU'));

ALTER TABLE sales.public.orders
  ADD ROW ACCESS POLICY governance.policies.region_filter ON (region);
```

### Mapping-table pattern (ABAC)

```sql
CREATE TABLE governance.policies.access_map (
  role_name STRING,
  allowed_region STRING
);

CREATE OR REPLACE FUNCTION governance.policies.allowed_regions()
RETURNS ARRAY
MEMOIZABLE
AS
$$
  SELECT ARRAY_AGG(allowed_region)
  FROM governance.policies.access_map
  WHERE IS_ROLE_IN_SESSION(role_name)
$$;

CREATE OR REPLACE ROW ACCESS POLICY governance.policies.map_based_filter
  AS (region_col STRING) RETURNS BOOLEAN ->
    ARRAY_CONTAINS(region_col::VARIANT, governance.policies.allowed_regions());
```

## Constraints

- Only one row access policy per table (or view)
- Policy body cannot reference other tables directly — use a memoizable function
- Row access policies are evaluated after masking policies
- `ACCOUNTADMIN` is not exempt unless explicitly included in logic

## Anti-patterns

| Pattern | Why It Fails | Instead |
|---------|-------------|---------|
| Hardcoded role lists in policy body | Every new role requires editing the policy | Use a mapping table + memoizable function |
| `CURRENT_ROLE()` for role checks | Ignores role hierarchy | Use `IS_ROLE_IN_SESSION()` |
| Multiple row access policies on one table | Not allowed — only one per table | Combine logic into a single policy |

---

# Primitive: Projection Policies

Column-level access control that prevents specific roles from including a column in SELECT. Unlike masking (which returns masked values), projection policies make the column entirely non-queryable.

## Syntax

```sql
CREATE [ OR REPLACE ] PROJECTION POLICY <name>
  AS ()
  RETURNS PROJECTION_CONSTRAINT -> <body>;
```

Body must return `PROJECTION_CONSTRAINT(ALLOW => TRUE)` or `PROJECTION_CONSTRAINT(ALLOW => FALSE)`.

### Apply to column

```sql
ALTER TABLE <table>
  MODIFY COLUMN <column>
  SET PROJECTION POLICY <policy_name>;
```

### Remove from column

```sql
ALTER TABLE <table>
  MODIFY COLUMN <column>
  UNSET PROJECTION POLICY;
```

## Example

```sql
CREATE OR REPLACE PROJECTION POLICY governance.policies.restrict_ssn
  AS ()
  RETURNS PROJECTION_CONSTRAINT ->
    CASE
      WHEN IS_ROLE_IN_SESSION('HR_ADMIN') THEN PROJECTION_CONSTRAINT(ALLOW => TRUE)
      ELSE PROJECTION_CONSTRAINT(ALLOW => FALSE)
    END;

ALTER TABLE hr.employees
  MODIFY COLUMN ssn
  SET PROJECTION POLICY governance.policies.restrict_ssn;
```

## Anti-patterns

| Pattern | Why It Fails | Instead |
|---------|-------------|---------|
| Using projection when masking would suffice | Blocks all queries including `SELECT *` | Use masking if column should be visible but redacted |
| Forgetting `SELECT *` will fail | Users get cryptic errors | Document which columns have projection policies |

---

# Primitive: Account Usage Views (Governance)

Reference for `SNOWFLAKE.ACCOUNT_USAGE` views used for governance auditing.

## Key Views

| Use Case | View(s) | Key Columns |
|----------|---------|-------------|
| Who accessed what data | `ACCESS_HISTORY` | `query_id`, `user_name`, `direct_objects_accessed` (JSON) |
| Query audit trail | `QUERY_HISTORY` | `query_id`, `user_name`, `query_text`, `start_time` |
| Policy inventory | `MASKING_POLICIES`, `ROW_ACCESS_POLICIES`, `PROJECTION_POLICIES` | `policy_name`, `policy_schema` |
| Policy assignments | `POLICY_REFERENCES` | `policy_name`, `policy_kind`, `ref_entity_name`, `ref_column_name` |
| Classification results | `DATA_CLASSIFICATION_LATEST` | `table_name`, `column_name`, `semantic_category`, `privacy_category` |
| Role grants | `GRANTS_TO_ROLES`, `GRANTS_TO_USERS` | `grantee_name`, `privilege`, `granted_on` |

## JSON column handling (ACCESS_HISTORY)

```sql
SELECT
  ah.user_name,
  ah.query_start_time,
  oa.value:objectName::STRING AS object_name,
  oa.value:objectDomain::STRING AS object_type
FROM SNOWFLAKE.ACCOUNT_USAGE.ACCESS_HISTORY ah,
LATERAL FLATTEN(input => ah.direct_objects_accessed) oa
WHERE ah.query_start_time >= DATEADD(day, -7, CURRENT_TIMESTAMP());
```

## Useful queries

### Sensitive tables without masking policies (gap analysis)

```sql
WITH sensitive AS (
  SELECT DISTINCT
    database_name || '.' || schema_name || '.' || table_name AS fqn
  FROM SNOWFLAKE.ACCOUNT_USAGE.DATA_CLASSIFICATION_LATEST,
  LATERAL FLATTEN(input => result) r
  WHERE r.value:recommendation IS NOT NULL
),
protected AS (
  SELECT DISTINCT
    ref_database_name || '.' || ref_schema_name || '.' || ref_entity_name AS fqn
  FROM SNOWFLAKE.ACCOUNT_USAGE.POLICY_REFERENCES
  WHERE policy_kind = 'MASKING_POLICY'
)
SELECT s.fqn AS unprotected_table
FROM sensitive s
LEFT JOIN protected p ON s.fqn = p.fqn
WHERE p.fqn IS NULL;
```

## Constraints

- Requires `IMPORTED PRIVILEGES` on the `SNOWFLAKE` database
- Data latency up to 120 minutes
- Always apply time filters to avoid full scans

---

## Related Skills

If the user's request also involves these concerns, invoke the corresponding skill:

| Concern | Skill to Invoke | Example |
|---------|----------------|---------|
| Building pipelines or dynamic tables | `data-transformation` | "Build a pipeline and then secure the data" |
| Building a dashboard or deploying an app | `app-deployment` | "Secure the data and build a dashboard" |
| Multi-domain workflow (2+ concerns) | `standard-router` | "Pipeline + masking + dashboard" — invoke router first for correct ordering |

**Execution order for multi-domain workflows:** data-transformation → data-security → app-deployment
