---
type: primitive
name: dbt-snowflake
domain: data-transformation
snowflake_docs: "https://docs.snowflake.com/en/developer-guide/builders/building-with-dbt"
tested_on:
  snowflake_version: "8.23"
  test_date: "2026-02-15"
  test_account_type: "enterprise"
last_reviewed: "2026-02-15"
---

# dbt on Snowflake

Deploy and run dbt Core projects directly in Snowflake using the `snow` CLI. Uses Snowflake-native syntax that differs from standard dbt CLI.

## Syntax

### Deploy a project

```bash
snow dbt deploy <project_name> \
  --source /path/to/dbt \
  --database <db> \
  --schema <schema> \
  [--external-access-integration <EAI>]
```

### Execute models

```bash
# Run all models (flags BEFORE project name)
snow dbt execute -c <connection> --database <db> --schema <schema> <project_name> run

# Run specific model with dependencies
snow dbt execute -c <connection> --database <db> --schema <schema> <project_name> run --select +target_model+

# Test
snow dbt execute -c <connection> --database <db> --schema <schema> <project_name> test

# Seed
snow dbt execute -c <connection> --database <db> --schema <schema> <project_name> seed

# Full refresh
snow dbt execute -c <connection> --database <db> --schema <schema> <project_name> run --full-refresh
```

### Manage projects

```bash
# List projects
snow dbt list --in schema <schema> --database <db>

# Describe a project
snow dbt describe <project_name> --database <db> --schema <schema>
```

### Schedule via SQL

```sql
CREATE TASK <db>.<schema>.run_dbt_daily
  WAREHOUSE = <wh>
  SCHEDULE = 'USING CRON 0 6 * * * UTC'
AS
EXECUTE DBT PROJECT <db>.<schema>.<project_name> ARGS = '["run"]';
```

### Monitor

```sql
-- Execution logs
SELECT * FROM TABLE(INFORMATION_SCHEMA.TASK_HISTORY())
WHERE name = '<task_name>'
ORDER BY scheduled_time DESC;
```

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `project_name` | Yes | Name of the deployed dbt project |
| `--source` | Deploy only | Local path to dbt project directory |
| `--database` | Yes | Target Snowflake database |
| `--schema` | Yes | Target Snowflake schema |
| `-c` / `--connection` | Execute | Snowflake CLI connection name |
| `--select` | No | Model selection syntax: `+model+` for upstream/downstream |
| `--full-refresh` | No | Rebuild incremental models from scratch |
| `--external-access-integration` | No | EAI name for projects needing external network access |

## Constraints

- Always use `snow dbt execute` for Snowflake-native execution. Do NOT use local `dbt run`, `dbt test`, `dbt build`.
- CLI flags must come BEFORE the project name in `execute` commands.
- Scheduling uses `EXECUTE DBT PROJECT` SQL, not `snow dbt execute`.
- `--external-access-integration` is required if the dbt project needs to reach external endpoints.

## Examples

### Full workflow

```bash
# Deploy
snow dbt deploy my_project --source ./my_dbt_project --database analytics --schema transforms

# Execute all models
snow dbt execute -c default --database analytics --schema transforms my_project run

# Run tests
snow dbt execute -c default --database analytics --schema transforms my_project test
```

### Schedule daily runs

```sql
CREATE TASK analytics.transforms.daily_dbt
  WAREHOUSE = transform_wh
  SCHEDULE = 'USING CRON 0 6 * * * UTC'
AS
EXECUTE DBT PROJECT analytics.transforms.my_project ARGS = '["run"]';

ALTER TASK analytics.transforms.daily_dbt RESUME;
```

## Anti-patterns

| Pattern | Why It Fails | Instead |
|---------|-------------|---------|
| Using `dbt run` locally instead of `snow dbt execute` | Different execution engine and behavior | Always use `snow dbt execute` for Snowflake-native execution |
| Putting flags after project name | CLI parsing fails | `snow dbt execute -c conn --database db project_name run` |
| Using `snow dbt execute` in `CREATE TASK` | Wrong syntax for SQL context | Use `EXECUTE DBT PROJECT` SQL syntax in tasks |

## References

- `primitives/dynamic-tables`
- [Snowflake Docs: dbt on Snowflake](https://docs.snowflake.com/en/developer-guide/builders/building-with-dbt)
