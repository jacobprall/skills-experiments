---
name: catalog-integration-next-steps
description: "Configure table access after catalog integration is verified (universal for all catalog types)"
---

# Next Steps: Querying Catalog Tables

After a catalog integration is verified, present these options to access catalog tables.

## Option A: Create Individual Iceberg Tables

**With vended credentials (no external volume needed):**
```sql
CREATE ICEBERG TABLE <database>.<schema>.<table_name>
  CATALOG = '<integration_name>'
  CATALOG_TABLE_NAME = '<catalog_table_name>'
  CATALOG_NAMESPACE = '<namespace>';
```

**With external volume:**
```sql
CREATE ICEBERG TABLE <database>.<schema>.<table_name>
  CATALOG = '<integration_name>'
  EXTERNAL_VOLUME = '<external_volume_name>'
  CATALOG_TABLE_NAME = '<catalog_table_name>'
  CATALOG_NAMESPACE = '<namespace>';
```

<!-- AGENT NOTE: Debugging CREATE ICEBERG TABLE failures (non-CLD)

For unmanaged Iceberg tables (in a non-CLD database), the table MUST already exist in the 
remote catalog before CREATE ICEBERG TABLE will succeed. Unlike CLD which auto-discovers 
tables, individual CREATE ICEBERG TABLE is just registering an existing remote table.

If CREATE ICEBERG TABLE fails with "table not found" or similar errors:

1. First verify the table exists in the remote catalog:
   SELECT SYSTEM$LIST_ICEBERG_TABLES_FROM_CATALOG('<integration_name>', '<namespace>');

2. Verify the namespace is correct:
   SELECT SYSTEM$LIST_NAMESPACES_FROM_CATALOG('<integration_name>');

Common causes of failure:
- Table /namespave doesn't exist in remote catalog yet (must create it there first)
- Case sensitivity mismatch

This is different from CLD where tables are auto-discovered from the remote catalog.
-->

## Option B: Create Catalog-Linked Database (Recommended)

Auto-discovers and syncs all tables from the external catalog.

**With vended credentials:**
```sql
CREATE DATABASE <database_name>
  LINKED_CATALOG = (
    CATALOG = '<integration_name>'
  );
```

**With external volume:**
```sql
CREATE DATABASE <database_name>
  LINKED_CATALOG = (
    CATALOG = '<integration_name>'
  )
  EXTERNAL_VOLUME = '<external_volume_name>';
```

**With namespace filtering:**
```sql
CREATE DATABASE <database_name>
  LINKED_CATALOG = (
    CATALOG = '<integration_name>'
    ALLOWED_NAMESPACES = ( '<namespace1>', '<namespace2>' )
  );
```

**With read-only mode:**
```sql
CREATE DATABASE <database_name>
  LINKED_CATALOG = (
    CATALOG = '<integration_name>'
    ALLOWED_WRITE_OPERATIONS = NONE
  );
```

## Verification Commands

```sql
-- Check catalog-linked database sync status
SELECT SYSTEM$CATALOG_LINK_STATUS('<database_name>');

-- List schemas
SHOW SCHEMAS IN DATABASE <database_name>;

-- List tables
SHOW TABLES IN SCHEMA <database_name>.<schema_name>;
```

## Documentation

- [CREATE DATABASE (catalog-linked)](https://docs.snowflake.com/sql-reference/sql/create-database-catalog-linked)
- [CREATE ICEBERG TABLE](https://docs.snowflake.com/sql-reference/sql/create-iceberg-table)
- [Iceberg Data Types](https://docs.snowflake.com/en/user-guide/tables-iceberg-data-types#other-data-types) - Supported data type mappings and limitations
