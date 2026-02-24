# Snowflake APIs Reference

## Account Usage Views

| API | Description | Use Case | Latency |
|-----|-------------|----------|---------|
| `ACCOUNT_USAGE.OBJECT_DEPENDENCIES` | Static dependency graph from DDL | All workflows | Near real-time |
| `ACCOUNT_USAGE.ACCESS_HISTORY` | Runtime data access patterns | Usage patterns, user attribution | 45min-3hr |
| `ACCOUNT_USAGE.QUERY_HISTORY` | Query execution details | Change attribution, debugging | 45min-3hr |
| `ACCOUNT_USAGE.TABLES` | Table metadata and timestamps | Schema change detection | 45min-3hr |
| `ACCOUNT_USAGE.COLUMNS` | Column metadata | Schema change detection | 45min-3hr |
| `ACCOUNT_USAGE.TABLE_STORAGE_METRICS` | Storage and freshness metrics | Trust scoring | 45min-3hr |
| `INFORMATION_SCHEMA.OBJECT_DEPENDENCIES` | Real-time deps (current DB only) | Fallback for real-time needs | Real-time |

## Privilege Requirements

```sql
-- Required for lineage queries
GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE TO ROLE <role_name>;
```

Without this grant, ACCOUNT_USAGE views will return empty results.

## Performance Notes

- **ACCOUNT_USAGE queries:** Fast for targeted queries, slow for full scans
- **ACCESS_HISTORY:** Limited to 365 days retention
- **OBJECT_DEPENDENCIES:** May have large result sets for heavily-used tables
- **Always filter by time** to improve performance
- **Use specific object names** when possible
