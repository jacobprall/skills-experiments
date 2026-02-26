# FastGen Configuration Specification

This document describes the JSON configuration schema for the FastGen API, which automatically generates semantic models from SQL queries and table metadata.

## Schema Overview

```json
{
  "name": "string (required)",
  "tables": [
    {
      "database": "string (required)",
      "schema": "string (required)",
      "table": "string (required)",
      "column_names": ["string"] (required, non-empty)
    }
  ],
  "sql_source": {
    "queries": [
      {
        "sql_text": "string (required)",
        "database": "string (optional)",
        "schema": "string (optional)",
        "correspondingQuestion": "string (optional)"
      }
    ]
  },
  "metadata": {
    "warehouse": "string (auto-populated from connection)"
  },
  "extensions": {
    "semantic_view_db": "string (required)",
    "semantic_view_schema": "string (required)",
    "semantic_description": "string (optional)"
  }
}
```

## Required Fields

### `name`
- **Type:** string
- **Description:** The name for the generated semantic model/view
- **Example:** `"sales_analytics"`

### `tables`
- **Type:** array of table objects
- **Description:** List of source tables to include in the semantic model
- **Minimum:** At least one table required

#### Table Object Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `database` | string | Yes | Snowflake database name |
| `schema` | string | Yes | Snowflake schema name |
| `table` | string | Yes | Table name |
| `column_names` | array of strings | Yes | List of columns to include (non-empty) |

### `extensions.semantic_view_db`
- **Type:** string
- **Description:** Database where the semantic view will be created
- **Example:** `"ANALYTICS"`

### `extensions.semantic_view_schema`
- **Type:** string
- **Description:** Schema where the semantic view will be created
- **Example:** `"SEMANTIC_MODELS"`

## Optional Fields

### `sql_source.queries`
- **Type:** array of query objects
- **Description:** SQL queries to generate Verified Query Results (VQRs)
- **Default:** Empty array (no VQRs generated)

#### Query Object Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `sql_text` | string | Yes | The SQL query text |
| `database` | string | No | Default database context for the query |
| `schema` | string | No | Default schema context for the query |
| `correspondingQuestion` | string | No | Natural language question the query answers |

### `metadata.warehouse`
- **Type:** string
- **Description:** Snowflake warehouse for query execution
- **Note:** Auto-populated from the Snowflake connection if not specified

### `extensions.semantic_description`
- **Type:** string
- **Description:** High-level description of the semantic model's purpose
- **Example:** `"Analytics model for tracking sales performance across regions"`

## Identifier Normalization

The FastGen script automatically normalizes unquoted identifiers to UPPERCASE:

- `analytics` → `ANALYTICS`
- `my_table` → `MY_TABLE`

To preserve case-sensitive identifiers, use escaped quotes:

- `\"MixedCase\"` → preserved as `MixedCase`

## Examples

### Minimal Configuration (Tables Only)

```json
{
  "name": "simple_model",
  "tables": [
    {
      "database": "ANALYTICS",
      "schema": "PUBLIC",
      "table": "ORDERS",
      "column_names": ["ORDER_ID", "CUSTOMER_ID", "ORDER_DATE", "TOTAL_AMOUNT"]
    }
  ],
  "extensions": {
    "semantic_view_db": "ANALYTICS",
    "semantic_view_schema": "SEMANTIC"
  }
}
```

### Configuration with SQL Queries

```json
{
  "name": "sales_analytics",
  "tables": [
    {
      "database": "SALES",
      "schema": "PUBLIC",
      "table": "ORDERS",
      "column_names": ["ORDER_ID", "CUSTOMER_ID", "ORDER_DATE", "TOTAL_AMOUNT", "STATUS"]
    },
    {
      "database": "SALES",
      "schema": "PUBLIC",
      "table": "CUSTOMERS",
      "column_names": ["CUSTOMER_ID", "NAME", "REGION", "SIGNUP_DATE"]
    }
  ],
  "sql_source": {
    "queries": [
      {
        "sql_text": "SELECT c.REGION, SUM(o.TOTAL_AMOUNT) as revenue FROM SALES.PUBLIC.ORDERS o JOIN SALES.PUBLIC.CUSTOMERS c ON o.CUSTOMER_ID = c.CUSTOMER_ID GROUP BY c.REGION",
        "database": "SALES",
        "schema": "PUBLIC",
        "correspondingQuestion": "What is the total revenue by region?"
      }
    ]
  },
  "extensions": {
    "semantic_view_db": "SALES",
    "semantic_view_schema": "SEMANTIC_MODELS",
    "semantic_description": "Sales analytics model for revenue and customer analysis"
  }
}
```

### Multi-Table Configuration for Relationship Inference

```json
{
  "name": "employee_hierarchy",
  "tables": [
    {
      "database": "HR",
      "schema": "PUBLIC",
      "table": "EMPLOYEES",
      "column_names": ["EMPLOYEE_ID", "NAME", "DEPARTMENT_ID", "MANAGER_ID"]
    },
    {
      "database": "HR",
      "schema": "PUBLIC",
      "table": "DEPARTMENTS",
      "column_names": ["DEPARTMENT_ID", "DEPARTMENT_NAME", "BUDGET"]
    },
    {
      "database": "HR",
      "schema": "PUBLIC",
      "table": "PROJECTS",
      "column_names": ["PROJECT_ID", "PROJECT_NAME", "LEAD_EMPLOYEE_ID"]
    }
  ],
  "extensions": {
    "semantic_view_db": "HR",
    "semantic_view_schema": "SEMANTIC"
  }
}
```

## Validation Checklist

Before calling FastGen, verify:

- [ ] `name` is present and non-empty
- [ ] At least one table in `tables` array
- [ ] Each table has `database`, `schema`, `table` fields
- [ ] Each table has non-empty `column_names` array
- [ ] `extensions.semantic_view_db` is present
- [ ] `extensions.semantic_view_schema` is present
- [ ] If queries provided, each has non-empty `sql_text`

## Output Files

The FastGen script generates:

1. **`<name>_semantic_model.yaml`** - The generated semantic model in YAML format
2. **`<name>_metadata.json`** - Metadata including:
   - `semantic_yaml` - Raw YAML content
   - `warnings` - Any warnings from generation
   - `errors` - Any errors encountered
   - `request_id` - Unique identifier for the FastGen request
   - `suggestions` - Relationship and primary key suggestions from FastGen

## Related Documentation

- [fastgen_workflow.md](fastgen_workflow.md) - Step-by-step workflow for using FastGen
- [fallback_creation.md](fallback_creation.md) - Manual creation workflow if FastGen fails
