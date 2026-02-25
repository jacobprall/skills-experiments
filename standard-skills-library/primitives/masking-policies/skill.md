---
type: primitive
name: masking-policies
domain: data-security
snowflake_docs: "https://docs.snowflake.com/en/sql-reference/sql/create-masking-policy"
---

# Masking Policies

Column-level security that dynamically masks data based on the querying user's role or context. Requires Enterprise Edition or higher.

## Syntax

```sql
CREATE [ OR REPLACE ] MASKING POLICY <name>
  AS (<arg_name> <arg_type> [, <conditional_arg> <arg_type> ...])
  RETURNS <return_type> -> <body>
  [ COMMENT = '<description>' ]
  [ EXEMPT_OTHER_POLICIES = TRUE | FALSE ];
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `name` | identifier | Yes | — | Fully qualified: `<db>.<schema>.<name>` |
| `arg_name` | identifier | Yes | — | Name of the input column value |
| `arg_type` | data type | Yes | — | Must match the column's data type exactly |
| `return_type` | data type | Yes | — | Must match `arg_type` |
| `body` | expression | Yes | — | CASE expression defining masking logic |
| `EXEMPT_OTHER_POLICIES` | boolean | No | `FALSE` | If `TRUE`, row access and projection policies are not evaluated when this policy is applied |

### Applying to a column

```sql
ALTER TABLE <table>
  MODIFY COLUMN <column>
  SET MASKING POLICY <policy_name>
  [ USING (<column>, <conditional_column>, ...) ];
```

### Removing from a column

```sql
ALTER TABLE <table>
  MODIFY COLUMN <column>
  UNSET MASKING POLICY;
```

## Parameters

### Conditional masking (USING clause)

Pass additional columns to the policy body for context-aware masking. The first argument is always the masked column; subsequent arguments are auxiliary.

```sql
CREATE OR REPLACE MASKING POLICY mask_email_by_visibility
  AS (email STRING, visibility STRING) RETURNS STRING ->
    CASE
      WHEN visibility = 'PUBLIC' THEN email
      WHEN IS_ROLE_IN_SESSION('PRIVILEGED') THEN email
      ELSE '***MASKED***'
    END;

ALTER TABLE users
  MODIFY COLUMN email
  SET MASKING POLICY mask_email_by_visibility
  USING (email, visibility);
```

### Tag-based masking

Attach masking policies to tags instead of individual columns. One policy per data type per tag.

```sql
CREATE TAG governance.tags.pii_data;

ALTER TAG governance.tags.pii_data SET
  MASKING POLICY mask_string,
  MASKING POLICY mask_number,
  MASKING POLICY mask_timestamp;

ALTER TABLE customers MODIFY COLUMN email SET TAG governance.tags.pii_data = 'EMAIL';
```

Inside a tag-based policy, use `SYSTEM$GET_TAG_ON_CURRENT_COLUMN('tag_name')` to read the tag value and vary behavior per column.

### Context functions

| Function | Behavior | Recommended |
|----------|----------|-------------|
| `IS_ROLE_IN_SESSION(role)` | Checks full role hierarchy | Yes |
| `CURRENT_ROLE()` | Active role only, ignores inheritance | No |
| `INVOKER_ROLE()` | Executing role in owner's-rights context | Situational |
| `IS_GRANTED_TO_INVOKER_ROLE(role)` | Invoker role hierarchy check | Situational |

## Constraints

- Input and output data types must match exactly — a `STRING` column requires a `STRING -> STRING` policy
- Only one masking policy per column (directly or via tag). Applying a new one requires unsetting the old one first.
- Masking policies cannot reference other tables directly in the body. Use a memoizable function for lookup-based masking.
- Columns used in `USING` clause must be in the same table.
- Tag-based masking supports one policy per data type per tag.

## Examples

### Basic: Role-based string masking

```sql
CREATE OR REPLACE MASKING POLICY governance.policies.mask_pii_string
  AS (val STRING) RETURNS STRING ->
    CASE
      WHEN IS_ROLE_IN_SESSION('DATA_STEWARD') THEN val
      ELSE '***MASKED***'
    END;
```

### Split pattern (for managing multiple policies)

Extract the authorization check into a shared memoizable function, then reference it from all policies. When authorization logic changes, update one function.

```sql
CREATE OR REPLACE FUNCTION governance.policies.should_unmask()
RETURNS BOOLEAN
MEMOIZABLE
AS
$$
  SELECT IS_ROLE_IN_SESSION('DATA_STEWARD')
      OR IS_ROLE_IN_SESSION('ANALYST_FULL')
$$;

CREATE OR REPLACE MASKING POLICY governance.policies.mask_string
  AS (val STRING) RETURNS STRING ->
    CASE WHEN governance.policies.should_unmask() THEN val ELSE '***MASKED***' END;

CREATE OR REPLACE MASKING POLICY governance.policies.mask_number
  AS (val NUMBER) RETURNS NUMBER ->
    CASE WHEN governance.policies.should_unmask() THEN val ELSE -1 END;

CREATE OR REPLACE MASKING POLICY governance.policies.mask_timestamp
  AS (val TIMESTAMP_NTZ) RETURNS TIMESTAMP_NTZ ->
    CASE WHEN governance.policies.should_unmask() THEN val ELSE '1900-01-01'::TIMESTAMP_NTZ END;
```

### Partial masking

```sql
CREATE OR REPLACE MASKING POLICY governance.policies.mask_email_partial
  AS (val STRING) RETURNS STRING ->
    CASE
      WHEN IS_ROLE_IN_SESSION('DATA_STEWARD') THEN val
      ELSE REGEXP_REPLACE(val, '.+@', '****@')
    END;
```

### Discovery: Find all policies and assignments

```sql
SHOW MASKING POLICIES IN DATABASE my_db;

SELECT * FROM TABLE(INFORMATION_SCHEMA.POLICY_REFERENCES(
  POLICY_NAME => 'my_db.governance.mask_string'
));
```

## Anti-patterns

| Pattern | Why It Fails | Instead |
|---------|-------------|---------|
| Per-table policies with identical logic | Policy sprawl — dozens of copies to maintain | Use generic reusable policies with the split pattern |
| `CURRENT_ROLE()` in policy body | Fails for inherited roles — user with role X via hierarchy won't match | Use `IS_ROLE_IN_SESSION()` |
| Direct table lookups in policy body | Not allowed — policies can't reference other tables | Use a memoizable function for lookups |
| Applying both direct and tag-based policies to same column | Conflict — only one policy per column | Choose one approach per column |

## References

- `primitives/row-access-policies`
- `primitives/projection-policies`
- [Snowflake Docs: Masking Policies](https://docs.snowflake.com/en/sql-reference/sql/create-masking-policy)
