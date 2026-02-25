---
name: dbt-execute
description: "Execute dbt commands on Snowflake (run, test, build, seed, snapshot, show). Triggers: run, test, build, seed, execute, snapshot, show, preview, deployed object, deployed project, run in deployed, using the deployed, except, exclude, all models except, data quality tests, run tests, seed CSV, load seed, load CSV, seed data, CSV data, preview model, preview output, show output, dbt show."
parent_skill: dbt-projects-on-snowflake
---

# Execute dbt Commands

## When to Load

Main skill routes here for: "run", "test", "build", "seed", "execute", "snapshot", "show", "preview", "deployed object", "deployed project", "run in deployed", "using the deployed", "except", "exclude", "all models except", "data quality tests", "run tests", "seed CSV", "load seed", "load CSV", "seed data", "CSV data", "preview model", "preview output", "show output", "dbt show", "docs", "documentation", "catalog", "lineage", "dbt docs", "generate docs"

## ⚠️ Unsupported Commands

### `docs generate` - Use Local dbt CLI

**`docs generate` is NOT supported via `snow dbt execute` or `EXECUTE DBT PROJECT`.**

Do NOT try:
- ❌ `snow dbt execute ... docs generate` - Will fail with "No such command 'docs'"
- ❌ `EXECUTE DBT PROJECT ... ARGS = '["docs", "generate"]'` - Will fail with "command not supported"

**Instead, use local dbt CLI with the project at `/workspace/my_dbt_project`:**

```bash
cd /workspace/my_dbt_project && dbt docs generate --profiles-dir .
```

**Workflow for Documentation Generation:**

1. **Check dbt CLI is installed (prompt user if missing):**
   ```bash
   dbt --version || echo "dbt CLI not found. Please install dbt-core and dbt-snowflake locally."
   # Examples:
   # pip install dbt-core dbt-snowflake
   # or: pipx install dbt-core dbt-snowflake
   # or: uvx --with dbt-snowflake dbt-core -- dbt --version
   ```

2. **Generate docs using local dbt:**
   ```bash
   cd /workspace/my_dbt_project && dbt docs generate --profiles-dir .
   ```

3. **Artifacts are created in `/workspace/my_dbt_project/target/`:**
   - `catalog.json` - Data catalog with table/column metadata
   - `manifest.json` - Project manifest with model definitions and lineage
   - `index.html` - Interactive documentation site

4. **Write the artifacts path to `/app/docs_path.txt`:**
   ```bash
   echo "/workspace/my_dbt_project/target" > /app/docs_path.txt
   ```

---

## Critical Syntax

**Connection flags MUST come BEFORE the project name:**

```bash
# ✅ CORRECT
snow dbt execute -c default --database my_db --schema my_schema my_project run

# ❌ WRONG - flags after project name
snow dbt execute my_project run --database my_db
```

## ⚠️ CRITICAL: Preview vs Run

**To PREVIEW model output without creating objects, use `show`:**
```bash
snow dbt execute -c default --database my_db --schema my_schema my_project show --select model_name
```

**Do NOT use `run` for preview tasks!** `run` creates actual tables/views in the database.

| Task | Command | Creates Objects? |
|------|---------|------------------|
| Preview/inspect data | `show` | ❌ No |
| Materialize models | `run` | ✅ Yes |

## Workflow

### Step 1: Identify Command

| User Intent | dbt Command |
|-------------|-------------|
| List resources/models in project | `list` |
| Preview model output (no materialization) | `show` |
| Run models | `run` |
| Run tests | `test` |
| Run + test + seed + snapshot | `build` |
| Load CSV seed data | `seed` |
| Capture snapshots | `snapshot` |

### Step 2: Execute Command

**Goal:** Run the dbt command via Snowflake-native execution

**Syntax:**
```bash
snow dbt execute -c <connection> --database <db> --schema <schema> <project> <command> [options]
```

### Available Commands

#### List Resources/Models in Project
```bash
snow dbt execute -c default --database my_db --schema my_schema my_project list
```
Shows all resources (models, seeds, tests, snapshots) defined in the project.

**Note:** This is different from `snow dbt list` which lists **projects** in a schema (see `manage/SKILL.md`).
#### Preview Model Output (show)
```bash
snow dbt execute -c default --database my_db --schema my_schema my_project show --select model_name
```
Previews the compiled SQL output of a model **without materializing any objects**. Use this to inspect what data a model would produce before running it.

**Key behavior:**
- Does NOT create tables or views
- Returns sample rows from the model's query
- Useful for debugging and validating model logic

**Example - preview specific model:**
```bash
snow dbt execute -c default --database my_db --schema my_schema my_project show --select stg_customers
```

#### Run Models
```bash
snow dbt execute -c default --database my_db --schema my_schema my_project run
```
Creates tables/views from models.

#### Run Specific Models
```bash
snow dbt execute -c default --database my_db --schema my_schema my_project run --select model_name
```

#### Run Specific Models WITH dependencies
Use graph selectors to include dependencies:

```bash
# Include upstream deps of the target
snow dbt execute -c default --database my_db --schema my_schema my_project run --select +target_model

# Include downstream deps of the target
snow dbt execute -c default --database my_db --schema my_schema my_project run --select target_model+

# Include both upstream and downstream around the target
snow dbt execute -c default --database my_db --schema my_schema my_project run --select +target_model+
```

#### Run Tests
```bash
snow dbt execute -c default --database my_db --schema my_schema my_project test
```
Executes all schema and data tests.

#### Build (All-in-One)
```bash
snow dbt execute -c default --database my_db --schema my_schema my_project build
```
Runs models + tests + seeds + snapshots in dependency order.

#### Load Seed Data
```bash
snow dbt execute -c default --database my_db --schema my_schema my_project seed
```
Loads CSV files from `seeds/` directory into tables.

#### Capture Snapshots
```bash
snow dbt execute -c default --database my_db --schema my_schema my_project snapshot
```
Creates SCD Type 2 snapshot tables.

#### Select Models by Materialization Type
Use dbt's config selector to run only models with a specific materialization:

```bash
# Run only models materialized as tables
snow dbt execute -c default --database my_db --schema my_schema my_project run --select config.materialized:table

# Run only models materialized as views
snow dbt execute -c default --database my_db --schema my_schema my_project run --select config.materialized:view

# Run only incremental models
snow dbt execute -c default --database my_db --schema my_schema my_project run --select config.materialized:incremental
```

**IMPORTANT:** Use `config.materialized:type` syntax, NOT model names. For example:
- ✅ `--select config.materialized:table` (selects ALL table-materialized models)
- ❌ `--select table_model` (selects a model named "table_model")

#### Run with Runtime Variables (--vars)
```bash
snow dbt execute -c default --database my_db --schema my_schema my_project run --vars '{"var_name": "value"}'
```
Pass runtime variables to dbt models. The vars are passed through to dbt and can be accessed with `{{ var('var_name') }}` in models.

**Example:** If model has `{{ var('name_alias', 'default_name') }}`:
```bash
snow dbt execute -c default --database DB --schema SCHEMA my_project run --vars '{"name_alias": "custom_column_name"}'
```

### Step 3: Verify Results

**Goal:** Confirm command succeeded

1. Check command output for `PASS=N ERROR=0`
2. Optionally verify objects were created:
   ```sql
   SHOW TABLES IN SCHEMA <db>.<schema>;
   ```

## CLI Reference

```bash
snow dbt execute [CONNECTION_FLAGS] NAME COMMAND [dbt_options]
```

| Parameter | Position | Description |
|-----------|----------|-------------|
| `-c, --connection` | Before NAME | Snowflake connection |
| `--database` | Before NAME | Target database |
| `--schema` | Before NAME | Target schema |
| `NAME` | After flags | Project identifier |
| `COMMAND` | After NAME | dbt command (list/show/run/test/build/seed/snapshot) |

**dbt Commands:**
| Command | Creates |
|---------|---------|
| `list` | - (displays resources) |
| `show` | - (previews data only, no objects created) |
| `run` | Tables/views from models |
| `test` | - (validates data) |
| `build` | Tables + snapshots (runs all) |
| `seed` | Seed tables from CSVs |
| `snapshot` | SCD Type 2 snapshot tables |

## Stopping Points

- ⚠️ If command fails, check troubleshooting in `references/troubleshooting.md`

## Output

- Materialized tables/views in target schema
- Test results (pass/fail counts)
- Seed tables from CSV data
- Snapshot tables with SCD columns
