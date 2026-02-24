---
name: Semantic View Key Concepts
description: Essential knowledge about semantic views and generated SQL
applies_to: [audit, debug, validation]
---

# Semantic View Key Concepts

## When to Load

Before analyzing generated SQL or semantic view.

## Critical Concepts

### 1. Logical vs Physical Tables

**Semantic views use logical table names**:

```yaml
tables:
  - name: SALES_FACT # Logical name (for humans)
    base_table:
      database: PROD
      schema: SALES
      table: TBL_SALES # Physical table (actual database table)
```

**Generated SQL uses physical tables**:

```sql
SELECT * FROM prod.sales.tbl_sales  -- Physical, not SALES_FACT
```

**✅ This is CORRECT** - Cortex Analyst always generates SQL with physical base_table references, never logical names.

**❌ Do NOT flag** "uses physical table instead of logical name" as an issue.

### 2. Semantic Model Elements

**Cannot Add** (physical columns):

- Dimensions - categorical columns
- Facts - numeric columns
- Time dimensions - date/time columns

**Can Add** (computed elements):

- Metrics - aggregations (SUM, COUNT, AVG)
- Filters - named WHERE clauses
- Relationships - table joins
- Module custom instructions - **RECOMMENDED**: targeted LLM guidance for specific pipeline components (sql_generation, question_categorization)
- Custom instructions  **LEGACY IMPLEMENTATION**:- LLM guidance for generating SQL.

**Can Enhance** (all elements):

- Descriptions
- Synonyms
- Sample values

### 3. Deprecated Fields

Never use (from proto):

- `default_aggregation` (deprecated lines 84, 192)
- `measures` (use `facts` instead)
- `one_to_many`, `many_to_many` (relationship types)
- `full_outer`, `cross`, `right_outer` (join types)

### 4. Valid Field Reference

Always check `example_semantic_view.yaml` for valid field structures before generating.

## Common Misconceptions

❌ Generated SQL should use logical table names
✅ Generated SQL correctly uses physical base_table names

❌ Can add new dimensions for missing columns
✅ Can only enhance existing dimensions (they're physical columns)

❌ "measures" and "facts" are different
✅ Use "facts" - "measures" is deprecated terminology

❌ Any physical table reference is suspicious
✅ Physical table references are expected and correct
