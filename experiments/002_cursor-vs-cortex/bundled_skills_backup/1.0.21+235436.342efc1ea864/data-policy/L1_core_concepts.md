# Core Concepts and Building Blocks

Use this file when the user asks for policy syntax or needs a reminder of how policies are defined and applied.

## Overview
- **Masking policy**: masks column values at query time.
- **Row access policy**: filters rows based on a condition.
- **Projection policy**: controls whether columns can appear in query results.
- **Tag-based masking**: applies masking policies via tags for scale.

**Edition requirement:** Enterprise Edition or higher.

## Masking Policy Structure
```sql
CREATE MASKING POLICY <name>
AS (<arg_name> <arg_type> [, <conditional_arg> <arg_type> ...])
RETURNS <return_type> -> <body>
[COMMENT = '<description>']
[EXEMPT_OTHER_POLICIES = TRUE|FALSE]
```

**Key rules**
- Input and output data types must match exactly.
- One masking policy per column.
- Use `IS_ROLE_IN_SESSION()` for role hierarchy checks.

## Data Type Matching
```sql
-- CORRECT: STRING in, STRING out
AS (val STRING) RETURNS STRING -> ...

-- INCORRECT: Cannot return different type
AS (val TIMESTAMP) RETURNS STRING -> ...  -- ERROR
```

## Conditional Masking (Multiple Columns)
```sql
CREATE OR REPLACE MASKING POLICY <policy_name>
AS (email STRING, visibility STRING) RETURNS STRING ->
  CASE
    WHEN visibility = 'PUBLIC' THEN email
    WHEN IS_ROLE_IN_SESSION('PRIVILEGED') THEN email
    ELSE '***MASKED***'
  END;
```

Apply with `USING`:
```sql
ALTER TABLE <table>
  MODIFY COLUMN email
  SET MASKING POLICY <policy_name>
  USING (email, visibility);
```

## Row Access Policy Syntax
```sql
CREATE OR REPLACE ROW ACCESS POLICY <db>.<schema>.<policy_name>
  AS (region STRING)
  RETURNS BOOLEAN ->
    CASE
      WHEN IS_ROLE_IN_SESSION('REGION_US') THEN region = 'US'
      WHEN IS_ROLE_IN_SESSION('REGION_EU') THEN region = 'EU'
      ELSE FALSE
    END;

ALTER TABLE <table>
  ADD ROW ACCESS POLICY <db>.<schema>.<policy_name> ON (region);
```

## Projection Policy Syntax

Projection policies control whether a column can appear in query results. Unlike masking (which transforms values), projection policies can completely hide columns from output.

```sql
CREATE OR REPLACE PROJECTION POLICY <db>.<schema>.<policy_name>
  AS ()
  RETURNS PROJECTION_CONSTRAINT ->
    CASE
      WHEN IS_ROLE_IN_SESSION('DATA_OWNER') THEN PROJECTION_CONSTRAINT(ALLOW => TRUE)
      ELSE PROJECTION_CONSTRAINT(ALLOW => FALSE)
    END;
```

**Apply to a column:**
```sql
ALTER TABLE <table>
  MODIFY COLUMN <column>
  SET PROJECTION POLICY <db>.<schema>.<policy_name>;
```

**Key differences from masking:**
| Aspect | Masking Policy | Projection Policy |
|--------|----------------|-------------------|
| Output | Transformed value (e.g., `***MASKED***`) | Column hidden entirely or NULL |
| Column in WHERE/JOIN | Uses original value | Can still use column for filtering |
| Use case | Show partial or obfuscated data | Completely hide column from results |

**Example: Hide SSN column except for HR:**
```sql
CREATE OR REPLACE PROJECTION POLICY governance.policies.hide_ssn
  AS ()
  RETURNS PROJECTION_CONSTRAINT ->
    CASE
      WHEN IS_ROLE_IN_SESSION('HR_ADMIN') THEN PROJECTION_CONSTRAINT(ALLOW => TRUE)
      ELSE PROJECTION_CONSTRAINT(ALLOW => FALSE)
    END
COMMENT = 'SSN column only visible to HR_ADMIN role';

ALTER TABLE employees
  MODIFY COLUMN ssn
  SET PROJECTION POLICY governance.policies.hide_ssn;
```

## Context Functions for Authorization
| Function | Use Case |
|----------|----------|
| `CURRENT_ROLE()` | Session's active role (simple check) |
| `IS_ROLE_IN_SESSION(role)` | Role hierarchy check (recommended) |
| `INVOKER_ROLE()` | Executing role context (views, UDFs) |
| `IS_GRANTED_TO_INVOKER_ROLE(role)` | Invoker role hierarchy check |
| `CURRENT_USER()` | Current user name |
| `CURRENT_ACCOUNT()` | Account identifier |

**CURRENT_ROLE vs IS_ROLE_IN_SESSION**
```sql
-- Simple check (no hierarchy)
WHEN CURRENT_ROLE() IN ('ANALYST') THEN val

-- Hierarchy-aware (recommended)
WHEN IS_ROLE_IN_SESSION('ANALYST') THEN val
```

**INVOKER_ROLE context**
- Direct table query: returns `CURRENT_ROLE`.
- View query: returns view owner role.
- UDF execution: returns UDF owner role.
- Stored procedure (caller's rights): returns `CURRENT_ROLE`.
- Stored procedure (owner's rights): returns procedure owner role.
- Task: returns task owner role.
- Stream: returns role querying the stream.

## Tag-Based Masking (Detailed)
**How it works**
1. Create a tag.
2. Assign masking policy to the tag.
3. Assign tag to database, schema, table, or column.
4. Columns are protected when data types match.

**One policy per data type per tag**
```sql
-- Create tag
CREATE TAG governance.tags.pii_data;

-- Assign policies (one per data type)
ALTER TAG governance.tags.pii_data SET
  MASKING POLICY string_mask,    -- for STRING columns
  MASKING POLICY number_mask,    -- for NUMBER columns
  MASKING POLICY timestamp_mask; -- for TIMESTAMP columns
```

**Protection scope**
| Scope | Command | Effect |
|-------|---------|--------|
| Database | `ALTER DATABASE db SET TAG tag = 'value'` | All matching columns in database |
| Schema | `ALTER SCHEMA sch SET TAG tag = 'value'` | All matching columns in schema |
| Table | `ALTER TABLE tbl SET TAG tag = 'value'` | All matching columns in table |
| Column | `ALTER TABLE tbl MODIFY COLUMN col SET TAG tag = 'value'` | Specific column |

**Tag inheritance**
- Database → Schema → Table → Column
- Policy on database protects all matching columns in nested objects.

**System functions**
```sql
-- Get tag value on current column being masked
SYSTEM$GET_TAG_ON_CURRENT_COLUMN('tag_name')

-- Get tag value on table containing current row
SYSTEM$GET_TAG_ON_CURRENT_TABLE('tag_name')
```

**Example: tag-aware masking**
```sql
CREATE MASKING POLICY tag_aware_mask AS (val STRING) RETURNS STRING ->
  CASE
    WHEN SYSTEM$GET_TAG_ON_CURRENT_COLUMN('governance.tags.pii') = 'visible' THEN val
    ELSE '***MASKED***'
  END;
```

**Policy precedence**
- Direct assignment takes precedence over tag-based assignment.

## Memoizable Functions (Performance)
Memoizable functions cache query results for performance when policies rely on mapping tables.

**Problem: per-row subquery**
```sql
CREATE MASKING POLICY slow_policy AS (val STRING) RETURNS STRING ->
  CASE
    WHEN EXISTS (SELECT 1 FROM auth_table WHERE role = CURRENT_ROLE()) THEN val
    ELSE '***MASKED***'
  END;
```

**Solution: memoizable function**
```sql
CREATE OR REPLACE FUNCTION is_authorized(role_name VARCHAR)
RETURNS BOOLEAN
MEMOIZABLE
AS
$$
  SELECT ARRAY_CONTAINS(
    role_name::VARIANT,
    (SELECT ARRAY_AGG(role) FROM auth_table WHERE is_authorized = TRUE)
  )
$$;

CREATE MASKING POLICY fast_policy AS (val STRING) RETURNS STRING ->
  CASE
    WHEN is_authorized(CURRENT_ROLE()) THEN val
    ELSE '***MASKED***'
  END;
```

## Privileges
| Privilege | Scope | Description |
|-----------|-------|-------------|
| CREATE MASKING POLICY | Schema | Create new policies |
| APPLY MASKING POLICY | Account | Set/unset policies on any column |
| APPLY ON MASKING POLICY | Policy | Allow object owners to apply specific policy |
| OWNERSHIP | Policy | Full control over policy |

## Runtime Behavior
At query runtime, Snowflake rewrites queries to apply masking policy expressions. Masking applies wherever the column appears: SELECT, JOIN, WHERE, ORDER BY, GROUP BY.

## Common Patterns
**Full mask**
```sql
AS (val STRING) RETURNS STRING ->
  CASE WHEN IS_ROLE_IN_SESSION('AUTHORIZED') THEN val ELSE '***MASKED***' END
```

**Partial mask (email)**
```sql
AS (val STRING) RETURNS STRING ->
  CASE 
    WHEN IS_ROLE_IN_SESSION('ADMIN') THEN val
    WHEN IS_ROLE_IN_SESSION('SUPPORT') THEN REGEXP_REPLACE(val, '.+\@', '*****@')
    ELSE '***MASKED***'
  END
```

**Hash mask (preserves uniqueness)**
```sql
AS (val STRING) RETURNS STRING ->
  CASE WHEN IS_ROLE_IN_SESSION('ANALYST') THEN val ELSE SHA2(val) END
```

## Inspect Policies
```sql
SHOW MASKING POLICIES;
SHOW ROW ACCESS POLICIES;
SHOW PROJECTION POLICIES;

-- Get policy definition (NOTE: first parameter is always 'POLICY', not 'MASKING_POLICY')
SELECT GET_DDL('POLICY', '<db>.<schema>.<policy_name>');

-- List policies on a table
-- ⚠️ INFORMATION_SCHEMA is database-scoped — MUST qualify with database name
SELECT * FROM TABLE(<db>.INFORMATION_SCHEMA.POLICY_REFERENCES(
  REF_ENTITY_NAME => '<db>.<schema>.<table>',
  REF_ENTITY_DOMAIN => 'TABLE'
));
```

> ⚠️ **Common mistakes:**
> - `INFORMATION_SCHEMA.POLICY_REFERENCES(...)` → ERROR. Must use `<db>.INFORMATION_SCHEMA.POLICY_REFERENCES(...)`
> - `GET_DDL('MASKING_POLICY', ...)` → ERROR. Always use `GET_DDL('POLICY', ...)`

## Monitoring & Discovery
```sql
-- List masking policies in a database
SHOW MASKING POLICIES IN DATABASE <db>;

-- Check policy assignments on a table
SELECT * FROM TABLE(<db>.INFORMATION_SCHEMA.POLICY_REFERENCES(
  REF_ENTITY_NAME => '<db>.<schema>.<table>', 
  REF_ENTITY_DOMAIN => 'TABLE'
));

-- Get policy definition
SELECT GET_DDL('POLICY', 'db.schema.policy_name');
```

---

## ⚠️ Common SQL Gotchas

These are frequently-made errors when working with policy SQL. Always use the CORRECT versions:

### 1. GET_DDL Object Type
```sql
-- ❌ WRONG: 'MASKING_POLICY' and 'MASKING POLICY' are invalid
SELECT GET_DDL('MASKING_POLICY', 'db.schema.my_policy');
SELECT GET_DDL('MASKING POLICY', 'db.schema.my_policy');

-- ✅ CORRECT: Use 'POLICY' (works for all policy types)
SELECT GET_DDL('POLICY', 'db.schema.my_policy');
```

### 2. INFORMATION_SCHEMA Views
```sql
-- ❌ WRONG: INFORMATION_SCHEMA.MASKING_POLICIES does NOT exist
SELECT * FROM db.INFORMATION_SCHEMA.MASKING_POLICIES;

-- ✅ CORRECT: Use SHOW command
SHOW MASKING POLICIES IN DATABASE db;

-- ✅ CORRECT: Use ACCOUNT_USAGE (has latency, requires ACCOUNTADMIN)
SELECT * FROM SNOWFLAKE.ACCOUNT_USAGE.MASKING_POLICIES WHERE DELETED IS NULL;
```

### 3. ACCOUNT_USAGE Column Names
```sql
-- ❌ WRONG: Column names vary from SHOW output
SELECT COMMENT FROM SNOWFLAKE.ACCOUNT_USAGE.MASKING_POLICIES;  -- WRONG
SELECT CREATED_ON FROM SNOWFLAKE.ACCOUNT_USAGE.MASKING_POLICIES;  -- WRONG

-- ✅ CORRECT: Actual column names
SELECT POLICY_COMMENT FROM SNOWFLAKE.ACCOUNT_USAGE.MASKING_POLICIES;
SELECT CREATED FROM SNOWFLAKE.ACCOUNT_USAGE.MASKING_POLICIES;
```

### 4. SHOW Command Filtering
```sql
-- ❌ WRONG: LIKE doesn't work with SHOW SCHEMAS
SHOW SCHEMAS IN DATABASE db LIKE '%pattern%';

-- ✅ CORRECT: Use STARTS WITH or filter in subsequent query
SHOW SCHEMAS IN DATABASE db STARTS WITH 'PREFIX_';

-- ✅ CORRECT: Or wrap SHOW in a query
SELECT * FROM TABLE(RESULT_SCAN(LAST_QUERY_ID())) WHERE "name" ILIKE '%pattern%';
```

### 5. DESC MASKING POLICY Output
```sql
-- DESC returns columns: name, signature, return_type, body, ...
-- The body is in column index 3 (0-indexed) or column name "body"
DESC MASKING POLICY db.schema.my_policy;
```

### 6. POLICY_REFERENCES Function
```sql
-- ❌ WRONG: POLICY_REFERENCES is NOT a table/view, it's a TABLE FUNCTION
SELECT * FROM INFORMATION_SCHEMA.POLICY_REFERENCES;
SELECT * FROM db.INFORMATION_SCHEMA.POLICY_REFERENCES WHERE ...;

-- ✅ CORRECT: Use TABLE() wrapper with function call
SELECT * FROM TABLE(db.INFORMATION_SCHEMA.POLICY_REFERENCES(
    REF_ENTITY_NAME => 'db.schema.table',
    REF_ENTITY_DOMAIN => 'TABLE'
));
```

### 7. Non-existent INFORMATION_SCHEMA Views
```sql
-- ❌ WRONG: These views do NOT exist in INFORMATION_SCHEMA
SELECT * FROM db.INFORMATION_SCHEMA.MASKING_POLICIES;
SELECT * FROM db.INFORMATION_SCHEMA.COLUMN_MASKING_POLICIES;
SELECT * FROM db.INFORMATION_SCHEMA.ROW_ACCESS_POLICIES;

-- ✅ CORRECT: Use SHOW commands for database-scoped discovery
SHOW MASKING POLICIES IN DATABASE db;
SHOW ROW ACCESS POLICIES IN DATABASE db;

-- ✅ CORRECT: Use ACCOUNT_USAGE for account-wide queries (needs ACCOUNTADMIN)
SELECT * FROM SNOWFLAKE.ACCOUNT_USAGE.MASKING_POLICIES WHERE DELETED IS NULL;
SELECT * FROM SNOWFLAKE.ACCOUNT_USAGE.ROW_ACCESS_POLICIES WHERE DELETED IS NULL;
SELECT * FROM SNOWFLAKE.ACCOUNT_USAGE.POLICY_REFERENCES WHERE DELETED IS NULL;
```

### 8. SHOW USER FUNCTIONS (not just FUNCTIONS)
```sql
-- ❌ WRONG: SHOW FUNCTIONS returns ALL functions including built-ins (1000s)
SHOW FUNCTIONS IN SCHEMA db.schema;

-- ✅ CORRECT: Use SHOW USER FUNCTIONS for user-defined functions only
SHOW USER FUNCTIONS IN SCHEMA db.schema;
```
