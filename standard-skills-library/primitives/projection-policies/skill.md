---
type: primitive
name: projection-policies
domain: data-security
snowflake_docs: "https://docs.snowflake.com/en/sql-reference/sql/create-projection-policy"
---

# Projection Policies

Column-level access control that prevents specific roles from including a column in SELECT. Unlike masking (which returns masked values), projection policies make the column entirely non-queryable. Requires Enterprise Edition or higher.

## Syntax

```sql
CREATE [ OR REPLACE ] PROJECTION POLICY <name>
  AS ()
  RETURNS PROJECTION_CONSTRAINT -> <body>;
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `name` | identifier | Yes | — | Fully qualified: `<db>.<schema>.<name>` |
| `body` | expression | Yes | — | Must return `PROJECTION_CONSTRAINT(ALLOW => TRUE/FALSE)` |

### Applying to a column

```sql
ALTER TABLE <table>
  MODIFY COLUMN <column>
  SET PROJECTION POLICY <policy_name>;
```

### Removing from a column

```sql
ALTER TABLE <table>
  MODIFY COLUMN <column>
  UNSET PROJECTION POLICY;
```

## Parameters

Projection policies take no input arguments — they use context functions to determine the querying user's identity.

The body must return `PROJECTION_CONSTRAINT(ALLOW => TRUE)` (column queryable) or `PROJECTION_CONSTRAINT(ALLOW => FALSE)` (column blocked).

## Constraints

- Only one projection policy per column.
- When `ALLOW => FALSE`, any query that references the column fails — including `SELECT *`.
- Projection policies are evaluated independently of masking policies.
- Cannot be combined with masking on the same column via tags (choose one approach).

## Examples

### Basic: Role-based column restriction

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
| Using projection when masking would suffice | Blocks all queries including `SELECT *`, which may be too restrictive | Use masking policies if the column should be visible but redacted |
| Forgetting that `SELECT *` will fail | Users get cryptic errors when a projection policy blocks a column | Document which columns have projection policies; masking policies allow the column to remain visible in redacted form |

## References

- `primitives/masking-policies`
- `primitives/row-access-policies`
- [Snowflake Docs: Projection Policies](https://docs.snowflake.com/en/sql-reference/sql/create-projection-policy)
