---
type: primitive
name: row-access-policies
domain: data-security
snowflake_docs: "https://docs.snowflake.com/en/sql-reference/sql/create-row-access-policy"
---

# Row Access Policies

Row-level security that filters which rows a user can see based on role, identity, or a mapping table. Requires Enterprise Edition or higher.

## Syntax

```sql
CREATE [ OR REPLACE ] ROW ACCESS POLICY <name>
  AS (<arg_name> <arg_type> [, ...])
  RETURNS BOOLEAN -> <body>;
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `name` | identifier | Yes | — | Fully qualified: `<db>.<schema>.<name>` |
| `arg_name` | identifier | Yes | — | Column(s) used for filtering |
| `arg_type` | data type | Yes | — | Must match the bound column's data type |
| `body` | expression | Yes | — | Boolean expression — `TRUE` = row visible, `FALSE` = row hidden |

### Applying to a table

```sql
ALTER TABLE <table>
  ADD ROW ACCESS POLICY <policy_name> ON (<column> [, ...]);
```

### Removing from a table

```sql
ALTER TABLE <table>
  DROP ROW ACCESS POLICY <policy_name>;
```

## Parameters

Row access policy arguments map to table columns at binding time. The policy body returns `TRUE` (show row) or `FALSE` (hide row).

Multiple columns can be passed for compound filtering:

```sql
CREATE OR REPLACE ROW ACCESS POLICY filter_by_region_and_dept
  AS (region STRING, department STRING) RETURNS BOOLEAN ->
    IS_ROLE_IN_SESSION('ADMIN')
    OR (region = 'US' AND IS_ROLE_IN_SESSION('REGION_US'))
    OR (department = CURRENT_SESSION_CONTEXT('department'));
```

## Constraints

- Only one row access policy per table (or view).
- The policy body cannot reference other tables directly. Use a memoizable function for mapping-table lookups.
- Row access policies are evaluated after masking policies.
- Rows filtered out are invisible — `COUNT(*)` reflects only visible rows.
- `ACCOUNTADMIN` is not exempt unless explicitly included in the policy logic.

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

Mapping table + memoizable function. Scales across many roles without editing the policy body.

```sql
-- Mapping table: which roles can see which regions
CREATE TABLE governance.policies.access_map (
  role_name STRING,
  allowed_region STRING
);

INSERT INTO governance.policies.access_map VALUES
  ('ANALYST_US', 'US'), ('ANALYST_EU', 'EU'), ('GLOBAL_ADMIN', 'US'), ('GLOBAL_ADMIN', 'EU');

-- Memoizable lookup
CREATE OR REPLACE FUNCTION governance.policies.allowed_regions()
RETURNS ARRAY
MEMOIZABLE
AS
$$
  SELECT ARRAY_AGG(allowed_region)
  FROM governance.policies.access_map
  WHERE IS_ROLE_IN_SESSION(role_name)
$$;

-- Policy using the lookup
CREATE OR REPLACE ROW ACCESS POLICY governance.policies.map_based_filter
  AS (region_col STRING) RETURNS BOOLEAN ->
    ARRAY_CONTAINS(region_col::VARIANT, governance.policies.allowed_regions());

ALTER TABLE sales.public.orders
  ADD ROW ACCESS POLICY governance.policies.map_based_filter ON (region);
```

### Discovery: Find all row access policies

```sql
SHOW ROW ACCESS POLICIES IN DATABASE my_db;

SELECT * FROM SNOWFLAKE.ACCOUNT_USAGE.ROW_ACCESS_POLICIES
WHERE deleted_on IS NULL;
```

## Anti-patterns

| Pattern | Why It Fails | Instead |
|---------|-------------|---------|
| Hardcoded role lists in policy body | Every new role requires editing the policy | Use a mapping table + memoizable function |
| `CURRENT_ROLE()` for role checks | Ignores role hierarchy | Use `IS_ROLE_IN_SESSION()` |
| Assuming `ACCOUNTADMIN` bypasses the policy | It does not unless explicitly coded | Include `IS_ROLE_IN_SESSION('ACCOUNTADMIN')` if bypass is intended |
| Multiple row access policies on one table | Not allowed — only one per table | Combine logic into a single policy |

## References

- `primitives/masking-policies`
- `primitives/projection-policies`
- [Snowflake Docs: Row Access Policies](https://docs.snowflake.com/en/sql-reference/sql/create-row-access-policy)
