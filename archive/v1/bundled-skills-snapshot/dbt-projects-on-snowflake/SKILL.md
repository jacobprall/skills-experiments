---
name: dbt-projects-on-snowflake
description: "Use for Snowflake-NATIVE dbt operations via `snow dbt` CLI or `EXECUTE DBT PROJECT` SQL. This skill is ONLY for deployed dbt projects running inside Snowflake — NOT for local dbt CLI usage (`dbt run`, `dbt build`, `dbt test`). Triggers: snow dbt, deploy dbt project, EXECUTE DBT PROJECT, snow dbt execute, snow dbt deploy, snow dbt list, deployed dbt project, schedule dbt project, CREATE TASK for dbt, dbt automation, recurring dbt runs, dbt every X hours/minutes, task chain for dbt, dbt logs, execution logs, execution history, dbt archive, download artifacts, external-access-integration, EAI, add version, new version, update version, VERSION$, version alias."
---

# Snowflake-Native dbt Projects

Deploy and run dbt Core projects directly **inside Snowflake** using the `snow` CLI and `EXECUTE DBT PROJECT` SQL.

**SCOPE:** This skill is ONLY for Snowflake-native dbt — projects deployed via `snow dbt deploy` and executed via `snow dbt execute` or `EXECUTE DBT PROJECT` SQL. It does NOT apply to local dbt CLI usage (`dbt run`, `dbt build`, `dbt test`, `dbt seed`).

**DO NOT use this skill when:**
- The user is running dbt locally against Snowflake (standard `dbt run`, `dbt build`, etc.)
- The user has a local `profiles.yml` with password/authenticator fields (this is normal for local dbt)
- The user is editing dbt models, fixing SQL bugs, or doing dbt development work

**WHY THIS SKILL EXISTS:** Snowflake's native dbt integration uses unique syntax (`snow dbt`, `EXECUTE DBT PROJECT`) that differs from standard dbt CLI. This skill provides the correct syntax for that specific workflow.

## Intent Detection

**Only match these intents when the user is explicitly working with Snowflake-native dbt (deployed projects, `snow dbt`, `EXECUTE DBT PROJECT`).** Do NOT match for standard local dbt CLI work.

| Intent | Triggers | Action |
|--------|----------|--------|
| **DEPLOY** | "snow dbt deploy", "deploy dbt project to snowflake", "create dbt project in snowflake", "upload dbt", "external access integration" | Load `deploy/SKILL.md` |
| **EXECUTE** | "snow dbt execute", "EXECUTE DBT PROJECT", "run deployed project", "execute deployed project", "snow dbt show" | Load `execute/SKILL.md` |
| **MANAGE** | "snow dbt list", "list dbt projects", "show dbt projects", "describe dbt project", "drop dbt project", "rename dbt project", "SHOW DBT PROJECTS", "add version", "VERSION$" | Load `manage/SKILL.md` |
| **SCHEDULE** | "schedule dbt project", "CREATE TASK for dbt", "EXECUTE DBT PROJECT in task", "automate dbt runs" | Load `schedule/SKILL.md` |
| **MONITOR** | "dbt execution logs", "dbt artifacts", "dbt archive", "dbt execution history" | Load `monitoring/SKILL.md` |

## Quick Reference

```bash
# Deploy (add --external-access-integration if project needs external network access)
snow dbt deploy my_project --source /path/to/dbt --database my_db --schema my_schema --external-access-integration MY_EAI

# PREVIEW model output (does NOT create objects)
snow dbt execute -c default --database my_db --schema my_schema my_project show --select model_name

# Execute/RUN models (creates tables/views)
snow dbt execute -c default --database my_db --schema my_schema my_project run

# Execute specific models with dependencies
# Upstream deps of target:
snow dbt execute -c default --database my_db --schema my_schema my_project run --select +target_model
# Downstream deps of target:
snow dbt execute -c default --database my_db --schema my_schema my_project run --select target_model+
# Both sides:
snow dbt execute -c default --database my_db --schema my_schema my_project run --select +target_model+

# List (omit --database to use connection default)
snow dbt list --in schema my_schema --database my_db

# Schedule (via SQL - always use EXECUTE DBT PROJECT)
CREATE TASK my_db.my_schema.run_dbt_daily
  WAREHOUSE = my_wh
  SCHEDULE = 'USING CRON 0 6 * * * UTC'
AS
EXECUTE DBT PROJECT my_db.my_schema.my_project ARGS = '["run"]';
```

## Workflow

```
User Request
     ↓
Intent Detection
     ↓
├─→ DEPLOY   → Load deploy/SKILL.md
├─→ EXECUTE  → Load execute/SKILL.md
├─→ MANAGE   → Load manage/SKILL.md
├─→ SCHEDULE → Load schedule/SKILL.md
└─→ MONITOR  → Load monitoring/SKILL.md
```

## Stopping Points

- ⚠️ Before any destructive operation (DROP, RENAME)

## Output

- Deployed dbt projects in Snowflake
- Materialized tables/views from dbt models
- Test results from dbt test
- Scheduled TASK objects for automated execution
- Execution logs and artifacts for debugging
