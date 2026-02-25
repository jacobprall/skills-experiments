---
type: primitive
name: table-comparison
domain: data-observability
snowflake_docs: "https://docs.snowflake.com/en/user-guide/data-quality-intro"
---

# Table Comparison

Compare two tables to find differences: row-level diffs, schema changes, aggregate discrepancies. Used for migration validation, regression testing, and data reconciliation.

## When to Use

- Validating a migration (dev vs prod, old vs new)
- Regression testing after a pipeline change
- Reconciling data between two systems
- Verifying a data reload or backfill

## Summary Diff

Quick overview: how many rows were added, removed, modified, or unchanged.

Requires a `<key_column>` that uniquely identifies rows in both tables.

```sql
WITH source_keys AS (
    SELECT <key_column>, HASH(*) AS row_hash FROM <source_table>
),
target_keys AS (
    SELECT <key_column>, HASH(*) AS row_hash FROM <target_table>
),
diff AS (
    SELECT
        SUM(CASE WHEN s.<key_column> IS NULL THEN 1 ELSE 0 END) AS rows_added,
        SUM(CASE WHEN t.<key_column> IS NULL THEN 1 ELSE 0 END) AS rows_removed,
        SUM(CASE WHEN s.<key_column> IS NOT NULL AND t.<key_column> IS NOT NULL
                 AND s.row_hash != t.row_hash THEN 1 ELSE 0 END) AS rows_modified,
        SUM(CASE WHEN s.<key_column> IS NOT NULL AND t.<key_column> IS NOT NULL
                 AND s.row_hash = t.row_hash THEN 1 ELSE 0 END) AS rows_unchanged
    FROM source_keys s
    FULL OUTER JOIN target_keys t ON s.<key_column> = t.<key_column>
)
SELECT *,
    rows_added + rows_removed + rows_modified + rows_unchanged AS total_rows,
    CASE
        WHEN rows_added + rows_removed + rows_modified = 0 THEN 'IDENTICAL'
        WHEN rows_modified > 0 THEN 'MODIFIED'
        WHEN rows_added > 0 AND rows_removed > 0 THEN 'CHANGED'
        WHEN rows_added > 0 THEN 'ADDITIONS_ONLY'
        WHEN rows_removed > 0 THEN 'REMOVALS_ONLY'
    END AS diff_status
FROM diff;
```

## Schema Comparison

Check if two tables have the same column structure.

```sql
WITH source_cols AS (
    SELECT column_name, data_type, is_nullable, ordinal_position
    FROM <source_db>.INFORMATION_SCHEMA.COLUMNS
    WHERE table_schema = '<source_schema>' AND table_name = '<source_table>'
),
target_cols AS (
    SELECT column_name, data_type, is_nullable, ordinal_position
    FROM <target_db>.INFORMATION_SCHEMA.COLUMNS
    WHERE table_schema = '<target_schema>' AND table_name = '<target_table>'
)
SELECT
    COALESCE(s.column_name, t.column_name) AS column_name,
    s.data_type AS source_type,
    t.data_type AS target_type,
    CASE
        WHEN s.column_name IS NULL THEN 'ADDED_IN_TARGET'
        WHEN t.column_name IS NULL THEN 'MISSING_IN_TARGET'
        WHEN s.data_type != t.data_type THEN 'TYPE_MISMATCH'
        WHEN s.is_nullable != t.is_nullable THEN 'NULLABLE_MISMATCH'
        ELSE 'MATCH'
    END AS status
FROM source_cols s
FULL OUTER JOIN target_cols t ON s.column_name = t.column_name
ORDER BY COALESCE(s.ordinal_position, t.ordinal_position);
```

## Row Count Comparison

Simple row count check — fast sanity test before deeper diffs.

```sql
SELECT
    (SELECT COUNT(*) FROM <source_table>) AS source_rows,
    (SELECT COUNT(*) FROM <target_table>) AS target_rows,
    (SELECT COUNT(*) FROM <source_table>) - (SELECT COUNT(*) FROM <target_table>) AS difference;
```

## Aggregate Comparison

Compare aggregate statistics per column — catches drift without row-level joins.

```sql
SELECT
    'source' AS table_side,
    COUNT(*) AS row_count,
    COUNT(DISTINCT <key_column>) AS distinct_keys,
    SUM(<numeric_column>) AS sum_val,
    AVG(<numeric_column>) AS avg_val,
    MIN(<numeric_column>) AS min_val,
    MAX(<numeric_column>) AS max_val
FROM <source_table>
UNION ALL
SELECT
    'target',
    COUNT(*), COUNT(DISTINCT <key_column>),
    SUM(<numeric_column>), AVG(<numeric_column>),
    MIN(<numeric_column>), MAX(<numeric_column>)
FROM <target_table>;
```

## Find Specific Modified Rows

After summary diff identifies modifications, drill into which rows changed and which columns differ.

```sql
WITH source_data AS (
    SELECT *, HASH(*) AS row_hash FROM <source_table>
),
target_data AS (
    SELECT *, HASH(*) AS row_hash FROM <target_table>
)
SELECT
    s.<key_column>,
    'MODIFIED' AS change_type
FROM source_data s
JOIN target_data t ON s.<key_column> = t.<key_column>
WHERE s.row_hash != t.row_hash
LIMIT 100;
```

## Workflow: Complete Migration Validation

1. **Schema comparison** — confirm column structure matches
2. **Row count comparison** — quick sanity check
3. **Summary diff** — quantify added/removed/modified rows
4. **Aggregate comparison** — verify totals and distributions match
5. **Row-level diff** (if modifications found) — identify specific changed rows

## Constraints

- `HASH(*)` is sensitive to column order — both tables must have the same column order for valid comparison
- Large tables may need sampling or partitioning for performance
- FULL OUTER JOIN on very large tables can be expensive — start with row counts and aggregates

## Anti-patterns

| Pattern | Why It Fails | Instead |
|---------|-------------|---------|
| Starting with row-level diff on large tables | Expensive FULL OUTER JOIN before knowing if there are differences | Start with row count and aggregate comparison first |
| Using HASH(*) when column order differs | Hashes won't match even if data is identical | Verify schema comparison first, or hash specific columns |
| Comparing tables across environments without accounting for timing | One table may have newer data | Align comparison windows or acknowledge timing differences |

## References

- `primitives/data-metric-functions`
- `primitives/lineage-queries`
