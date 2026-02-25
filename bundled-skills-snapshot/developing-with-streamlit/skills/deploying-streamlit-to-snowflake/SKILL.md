---
name: deploying-streamlit-to-snowflake
description: 'Deploy Streamlit applications to Snowflake using the `snow` CLI tool. Covers snowflake.yml manifest configuration, compute pools, container runtime, and deployment workflow.'
---

# Deploying Streamlit to Snowflake

Deploy local Streamlit apps to Snowflake using the `snow` CLI.

## Prerequisites

- **Snowflake CLI v3.14.0+**: Required for `definition_version: 2` (SPCS container runtime)
- **A Streamlit app**: Your main entry point file (e.g., `streamlit_app.py`)
- **A configured Snowflake connection**: Run `snow connection list` to verify

### Check and Ensure Correct CLI Version

**CRITICAL**: Always check the CLI version before deployment. Older versions don't support SPCS container runtime.

```bash
snow --version
```

If version is below 3.14.0, use `uvx` to run the latest CLI without installing:

```bash
# Use uvx to run latest snow CLI (recommended)
uvx --from snowflake-cli snow streamlit deploy --replace
```

This bypasses any outdated local installation and ensures you always use the latest CLI.

## Deployment Workflow

### Step 1: Get Connection Details

**CRITICAL**: Before creating `snowflake.yml`, get the actual values from the user's Snowflake connection. Do NOT use placeholder values like `MY_DATABASE`.

```bash
# Get connection details (database, schema, warehouse, role)
snow connection list
```

This returns JSON with the configured connection values. Use these values in `snowflake.yml`.

**If connection details are missing or incomplete**, ask the user:
- What database should the app be deployed to?
- What schema within that database?
- What warehouse should the app use for queries?

For **compute_pool**, the standard pool for Streamlit apps is `STREAMLIT_DEDICATED_POOL`. If unsure, ask the user or check available pools:
```bash
snow sql -q "SHOW COMPUTE POOLS"
```

### Step 2: Create Project Structure

```text
my_streamlit_app/
  snowflake.yml        # Deployment manifest (required)
  streamlit_app.py     # Main entry point
  pyproject.toml       # Python dependencies (streamlit>=1.52.0)
  src/                 # Additional modules
    helpers.py
  data/                # Data files
    sample.csv
```

**pyproject.toml** must include `streamlit>=1.52.0` (or higher) for SPCS container runtime support:

```toml
[project]
name = "my-app"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "streamlit>=1.52.0",
]
```

**Quick start with templates:**
```bash
# Single-page app
snow init my_app --template streamlit_vnext_single_page

# Multi-page app
snow init my_app --template streamlit_vnext_multi_page
```

### Step 3: Create `snowflake.yml`

Use the actual values from Step 1 (not placeholders):

```yaml
definition_version: 2
entities:
  my_streamlit:
    type: streamlit
    identifier:
      name: MY_APP_NAME           # Choose a name for the app
      database: <FROM_CONNECTION> # Use actual database from connection
      schema: <FROM_CONNECTION>   # Use actual schema from connection
    query_warehouse: <FROM_CONNECTION>  # Use actual warehouse from connection
    compute_pool: STREAMLIT_DEDICATED_POOL
    runtime_name: SYSTEM$ST_CONTAINER_RUNTIME_PY3_11
    external_access_integrations:
      - PYPI_ACCESS_INTEGRATION   # For pip installs
    main_file: streamlit_app.py
    artifacts:
      - streamlit_app.py
      - pyproject.toml
      - src/helpers.py            # Include ALL files your app needs
      - data/sample.csv
```

### Step 4: Verify App Runs Locally

**IMPORTANT**: Before deploying, verify the app runs locally to catch dependency or import errors early.

```bash
# Install dependencies
uv sync

# Quick check: verify imports work (catches missing dependencies)
uv run python -c "import streamlit_app"

# Full check: run the app locally
uv run streamlit run streamlit_app.py
```

Check that:
- The import check passes without errors
- The app starts without import errors
- All pages/components load correctly

If there are errors, fix `pyproject.toml`, run `uv sync` again, and re-test before deploying.

### Step 5: Deploy

```bash
cd my_streamlit_app
snow streamlit deploy --replace
```

The `--replace` flag updates an existing app with the same name.

### Step 6: Access Your App

After deployment, `snow` outputs the app URL. You can also find it in Snowsight under **Projects > Streamlit**.

## Configuration Reference

| Parameter | Description | Example |
|-----------|-------------|---------|
| `name` | Unique app identifier | `MY_DASHBOARD` |
| `database` | Target database | `ANALYTICS_DB` |
| `schema` | Target schema | `DASHBOARDS` |
| `query_warehouse` | Warehouse for SQL queries | `COMPUTE_WH` |
| `compute_pool` | Pool running the Python runtime | `STREAMLIT_DEDICATED_POOL` |
| `runtime_name` | Container runtime version | `SYSTEM$ST_CONTAINER_RUNTIME_PY3_11` |
| `main_file` | Entry point script | `streamlit_app.py` |
| `artifacts` | All files to upload (must include main_file) | See example above |
| `external_access_integrations` | Network access for pip, APIs | `PYPI_ACCESS_INTEGRATION` |

## Key Points

1. **Always use container runtime** (`runtime_name`) for best performance
2. **List ALL files** in `artifacts` - anything not listed won't be deployed
3. **Dependencies go in `pyproject.toml`** - installed automatically on deploy
4. **Iterate with `--replace`** - redeploy without creating duplicates

## Troubleshooting

**App not updating?**
- Ensure you're using `--replace`
- Check that changed files are in `artifacts`

**Import errors?**
- Verify all modules are in `artifacts`
- Check `pyproject.toml` has all pip dependencies

**Network/pip errors?**
- Add `PYPI_ACCESS_INTEGRATION` to `external_access_integrations`
