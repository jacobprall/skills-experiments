---
name: fastgen-workflow
description: FastGen API workflow for automated semantic model generation from SQL queries and table metadata
---

# FastGen Workflow

## Overview

This workflow uses the FastGen API to automatically generate semantic models from SQL queries and table metadata. FastGen will:

- Extract table metadata from Snowflake
- Infer primary keys and relationships
- Generate dimensions, measures, and metrics
- Create VQRs from SQL queries

## Prerequisites

- Semantic view name defined
- Snowflake context (database, schema) configured
- SQL context and business information gathered

## Phase 2: Generate and Validate FastGen Config

### Step 2.1: Extract Tables and Columns from SQL

Analyze user-provided SQL queries and extract:

- **Tables**: All references in `database.schema.table` format
- **Columns**: From SELECT, WHERE, GROUP BY, JOIN clauses
- **SQL Queries**: Complete executable statements (clean up placeholders)

Example: `ANALYTICS.LOGS.USAGE_LOGS` → columns: `[account_id, logged_at, user_id, tokens_used]`

### Step 2.2: Build FastGen Config JSON

Construct config JSON (see example at end of file for structure). Key fields:

- `name`: Semantic view name (Step 1.1)
- `sql_source.queries`: Array of SQL queries (can be empty if only tables provided)
- `tables`: Array with `database`, `schema`, `table`, `column_names` per table
- `metadata.warehouse`: Auto-populated from Snowflake connection
- `extensions`: `semantic_view_db`, `semantic_view_schema`, `semantic_description`

Note: Script auto-normalizes unquoted identifiers to UPPERCASE.

### Step 2.3: Validate Config

**Before calling FastGen, validate the config JSON**:

✅ **Required Fields Check**:

- `name` is present and non-empty
- `metadata.warehouse` is present (auto-populated from connection)
- `extensions.semantic_view_db` is present
- `extensions.semantic_view_schema` is present
- At least one table in `tables` array
- `sql_source.queries` array exists (can be empty if only tables provided)

✅ **Table Format Check**:

- Each table has `database`, `schema`, `table` fields
- Each table has `column_names` array (non-empty)

✅ **SQL Query Check** (if queries provided):

- Each query has `sql_text` field
- `sql_text` is non-empty string
- SQL appears to be valid (starts with SELECT/WITH/etc.)

**If validation fails**: Ask user to provide missing information.

### Step 2.4: Save Config File

Save the config JSON to a file:

- Location: `{WORKING_DIR}/creation/<semantic_view_name>_fastgen_config.json`
- Use proper JSON formatting (indent=2)

**⚠️ CRITICAL**: Use the `WORKING_DIR` variable from setup. This is the timestamped session directory created in `setup/SKILL.md`.

**Example path:**
```
{WORKING_DIR}/creation/<semantic_view_name>_fastgen_config.json
# Expands to: /app/semantic_view_20260219_143022/creation/<semantic_view_name>_fastgen_config.json
```

**Present config summary to user** (table count, column count) and proceed directly to Phase 3.

## Phase 3: Call FastGen API

### Step 3.1: Run FastGen Script

Execute the FastGen script with the config file:

```bash
cd {WORKING_DIR}/creation && \
SNOWFLAKE_CONNECTION_NAME=<connection> uv run python {SKILL_BASE_DIR}/scripts/generate_semantic_model_fastgen.py \
  <semantic_view_name>_fastgen_config.json \
  . \
  --connection <connection_name> \
  --no-ssl-verify
```

**⚠️ CRITICAL**: 
- Run from `{WORKING_DIR}/creation/` directory (use `cd` first)
- Output directory is `.` (current directory, which is `{WORKING_DIR}/creation/`)
- Use `{SKILL_BASE_DIR}/scripts/` for script location (absolute path from setup)

**Note**: The `--no-ssl-verify` flag is included by default for internal/test environments. Remove it if working with production Snowflake accounts.

**To use a different role than what's in your config:**

```bash
cd {WORKING_DIR}/creation && \
SNOWFLAKE_CONNECTION_NAME=<connection> uv run python {SKILL_BASE_DIR}/scripts/generate_semantic_model_fastgen.py \
  <semantic_view_name>_fastgen_config.json \
  . \
  --connection <connection_name> \
  --role <role_name> \
  --no-ssl-verify
```

**Parameters**:

- First arg: Path to config JSON file
- Second arg: Output directory (use `.` for current directory, which is `{WORKING_DIR}/creation/`)
- `--connection`: Snowflake connection name (required)
- `--no-ssl-verify`: Disable SSL certificate verification for internal environments (recommended by default)
- `--role` (optional): Override the role from config file

**Expected Output**:

- YAML file: `{WORKING_DIR}/creation/<semantic_view_name>_semantic_model.yaml`
- Metadata JSON: `{WORKING_DIR}/creation/<semantic_view_name>_metadata.json` containing:
  - `semantic_yaml` - Raw YAML content
  - `warnings` - Any warnings from generation
  - `errors` - Any errors encountered
  - `request_id` - Unique identifier for the FastGen request (useful for debugging)
  - `suggestions` - Relationship and primary key suggestions from FastGen

**Monitor for**:

- ✅ Success indicators: "Successfully generated semantic model"
- 🆔 Request ID: Unique identifier printed for debugging
- 💡 Suggestions: Count of relationship/primary key suggestions captured
- ⚠️ Warnings: "FastGen returned warnings"
- ❌ Errors: "FastGen returned errors"

### Step 3.2: Handle FastGen Failures

If FastGen fails (no YAML generated), examine errors:

**Common Errors:**

- **Table access/permissions** → Grant access or use manual approach
- **SQL syntax errors** → Fix queries and retry
- **Timeouts** → Reduce queries/tables and retry
- **API/connection errors** → Retry or use manual approach

**⚠️ ROLE PERMISSIONS ISSUE:**
If you see "couldn't access" errors with **400 Bad Request** status, even though you can SELECT from tables directly:

- **Root cause**: The role may lack FastGen API-level permissions (different from table SELECT grants)
- **Quick fix**: Use the `--role` flag to specify a different role:
  ```bash
  --role ENG_CORTEXSEARCH_RL
  ```
  Or update the role in `~/.snowflake/config.toml` under your connection
- **Example**: `cortex_analyst_engineer` failed → used `--role ENG_CORTEXSEARCH_RL` → succeeded
- **Best practice**: Use ACCOUNTADMIN or request admin to grant FastGen API access to your role

**⚠️ FALLBACK**: If unrecoverable, load `fallback_creation.md` for manual workflow using `infer_primary_keys.py` and `extract_table_metadata.py`.

## Config JSON Reference

See [fastgen_config_spec.md](fastgen_config_spec.md) for complete FastGen configuration schema and examples.
