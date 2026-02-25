---
type: primitive
name: account-usage-views
domain: data-security
snowflake_docs: "https://docs.snowflake.com/en/sql-reference/account-usage"
---

# Account Usage Views (Governance)

Reference for `SNOWFLAKE.ACCOUNT_USAGE` views used for data governance: auditing access, reviewing policies, tracking classification, and understanding object dependencies.

## Syntax

All views live in the `SNOWFLAKE.ACCOUNT_USAGE` schema. Query them like any table:

```sql
SELECT * FROM SNOWFLAKE.ACCOUNT_USAGE.<view_name>
WHERE <time_filter>;
```

Views have up to 120-minute latency. Use `INFORMATION_SCHEMA` equivalents for real-time data (where available).

## Parameters

### Key views by use case

| Use Case | View(s) | Key Columns |
|----------|---------|-------------|
| Who accessed what data | `ACCESS_HISTORY` | `query_id`, `user_name`, `direct_objects_accessed` (JSON), `base_objects_accessed` (JSON) |
| Query audit trail | `QUERY_HISTORY` | `query_id`, `user_name`, `query_text`, `start_time` |
| Policy inventory | `MASKING_POLICIES`, `ROW_ACCESS_POLICIES`, `PROJECTION_POLICIES`, `AGGREGATION_POLICIES` | `policy_name`, `policy_schema`, `created` |
| Policy assignments | `POLICY_REFERENCES` | `policy_name`, `policy_kind`, `ref_entity_name`, `ref_column_name` |
| Classification results | `DATA_CLASSIFICATION_LATEST` | `table_name`, `column_name`, `semantic_category`, `privacy_category`, `confidence` |
| Tags and tag assignments | `TAGS`, `TAG_REFERENCES` | `tag_name`, `tag_value`, `object_name` |
| Role grants | `GRANTS_TO_ROLES`, `GRANTS_TO_USERS` | `grantee_name`, `privilege`, `granted_on`, `name` |
| Object inventory | `TABLES`, `VIEWS`, `COLUMNS`, `DATABASES`, `SCHEMATA` | Standard metadata columns |
| Dependencies | `OBJECT_DEPENDENCIES` | `referencing_object_name`, `referenced_object_name` |

### JSON column handling

`ACCESS_HISTORY` contains JSON array columns. Use `LATERAL FLATTEN` to extract:

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

## Constraints

- Requires `IMPORTED PRIVILEGES` on the `SNOWFLAKE` database (granted by `ACCOUNTADMIN`).
- Data latency is up to 120 minutes for most views.
- `ACCESS_HISTORY` retains 365 days of data.
- Use `UPPER()` for case-insensitive matching on identifiers.
- For large accounts, always apply time filters to avoid full table scans.

## Examples

### Top 10 most-accessed objects in the last 7 days

```sql
SELECT
  oa.value:objectName::STRING AS object_name,
  COUNT(*) AS access_count
FROM SNOWFLAKE.ACCOUNT_USAGE.ACCESS_HISTORY ah,
LATERAL FLATTEN(input => ah.direct_objects_accessed) oa
WHERE ah.query_start_time >= DATEADD(day, -7, CURRENT_TIMESTAMP())
  AND oa.value:objectDomain::STRING IN ('Table', 'View')
GROUP BY object_name
ORDER BY access_count DESC
LIMIT 10;
```

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

### Roles with privileges on a specific table

```sql
SELECT grantee_name, privilege, grant_option
FROM SNOWFLAKE.ACCOUNT_USAGE.GRANTS_TO_ROLES
WHERE granted_on = 'TABLE'
  AND name = UPPER('my_table')
  AND deleted_on IS NULL
ORDER BY grantee_name;
```

### Policy inventory across account

```sql
SELECT 'MASKING' AS type, policy_name, policy_schema FROM SNOWFLAKE.ACCOUNT_USAGE.MASKING_POLICIES WHERE deleted IS NULL
UNION ALL
SELECT 'ROW_ACCESS', policy_name, policy_schema FROM SNOWFLAKE.ACCOUNT_USAGE.ROW_ACCESS_POLICIES WHERE deleted IS NULL
UNION ALL
SELECT 'PROJECTION', policy_name, policy_schema FROM SNOWFLAKE.ACCOUNT_USAGE.PROJECTION_POLICIES WHERE deleted IS NULL
ORDER BY type, policy_name;
```

## Anti-patterns

| Pattern | Why It Fails | Instead |
|---------|-------------|---------|
| Querying `ACCESS_HISTORY` without time filters | Scans up to 365 days of data — slow and expensive | Always filter on `query_start_time` |
| Expecting real-time data from `ACCOUNT_USAGE` | Up to 120-minute latency | Use `INFORMATION_SCHEMA` for real-time needs |
| Case-sensitive matching on identifiers | Snowflake stores identifiers in uppercase by default | Wrap values with `UPPER()` |

## References

- [Snowflake Docs: Account Usage](https://docs.snowflake.com/en/sql-reference/account-usage)
