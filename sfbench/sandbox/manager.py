"""Sandbox manager — create isolated Snowflake schemas per trial."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Optional

from rich.console import Console

from sfbench.models.task import TaskConfig, TrialContext
from sfbench.sandbox.snowflake import SQLResult, run_sql, run_sql_file

console = Console()

DATABASE = "SNOWFLAKE_LEARNING_DB"
ADMIN_ROLE = "SNOWFLAKE_LEARNING_ADMIN_ROLE"
RESTRICTED_ROLE = "SNOWFLAKE_LEARNING_ROLE"
WAREHOUSE = "SNOWFLAKE_LEARNING_WH"

SHARED_ENV_DIR = Path(__file__).resolve().parent.parent.parent / "shared" / "environments"


class SandboxManager:
    def __init__(self, connection: str = "default"):
        self.connection = connection

    def create_trial_context(
        self, task_id: str, trial_id: Optional[str] = None
    ) -> TrialContext:
        """Generate a TrialContext with unique schema names for isolation."""
        tid = trial_id or uuid.uuid4().hex[:8]
        prefix = f"SFBENCH_{task_id.upper()}_{tid.upper()}"

        return TrialContext(
            database=DATABASE,
            raw_schema=f"{prefix}_RAW",
            staging_schema=f"{prefix}_STAGING",
            analytics_schema=f"{prefix}_ANALYTICS",
            governance_schema=f"{prefix}_GOVERNANCE",
            admin_role=ADMIN_ROLE,
            restricted_role=RESTRICTED_ROLE,
            warehouse=WAREHOUSE,
            connection=self.connection,
        )

    def setup_sandbox(self, ctx: TrialContext) -> bool:
        """Create trial schemas and grants."""
        schemas = [ctx.raw_schema, ctx.staging_schema, ctx.analytics_schema, ctx.governance_schema]

        ddl_parts = [f"USE ROLE {ctx.admin_role};", f"USE WAREHOUSE {ctx.warehouse};"]
        for schema in schemas:
            ddl_parts.append(
                f"CREATE SCHEMA IF NOT EXISTS {ctx.database}.{schema};"
            )

        # Grants to restricted_role are handled by environment/task setup scripts
        # if needed and if the role hierarchy allows it.

        ddl = "\n".join(ddl_parts)
        result = run_sql(ddl, self.connection)
        if not result.success:
            console.print(f"[red]Sandbox setup failed: {result.error}[/red]")
            return False

        console.print(f"[dim]Created sandbox schemas: {', '.join(schemas)}[/dim]")
        return True

    def run_environment_scripts(self, environment_name: str, ctx: TrialContext) -> bool:
        """Execute shared environment SQL scripts with template resolution."""
        env_dir = SHARED_ENV_DIR / environment_name
        if not env_dir.exists():
            console.print(f"[yellow]Environment directory not found: {env_dir}[/yellow]")
            return True

        script_order = ["create_roles.sql", "create_tables.sql", "create_traps.sql"]
        sql_files = []
        for name in script_order:
            p = env_dir / name
            if p.exists():
                sql_files.append(p)

        for p in sorted(env_dir.glob("*.sql")):
            if p not in sql_files and p.name != "teardown.sql":
                sql_files.append(p)

        return self._execute_scripts(sql_files, ctx)

    def run_task_setup_scripts(self, config: TaskConfig, ctx: TrialContext) -> bool:
        """Execute task-specific setup scripts."""
        if not config.task_dir or not config.setup.scripts:
            return True

        scripts = []
        for script_name in config.setup.scripts:
            p = config.task_dir / "setup" / script_name
            if p.exists():
                scripts.append(p)
            else:
                console.print(f"[red]Setup script not found: {p}[/red]")
                return False

        return self._execute_scripts(scripts, ctx)

    def teardown_sandbox(self, ctx: TrialContext) -> bool:
        """Drop trial schemas."""
        schemas = [ctx.raw_schema, ctx.staging_schema, ctx.analytics_schema, ctx.governance_schema]

        ddl_parts = [f"USE ROLE {ctx.admin_role};"]
        for schema in schemas:
            ddl_parts.append(f"DROP SCHEMA IF EXISTS {ctx.database}.{schema} CASCADE;")

        ddl = "\n".join(ddl_parts)
        result = run_sql(ddl, self.connection)
        if not result.success:
            console.print(f"[yellow]Sandbox teardown warning: {result.error}[/yellow]")
            return False

        console.print(f"[dim]Dropped sandbox schemas: {', '.join(schemas)}[/dim]")
        return True

    def _execute_scripts(self, scripts: list[Path], ctx: TrialContext) -> bool:
        """Execute SQL scripts with template variable replacement."""
        from sfbench.models.task import resolve_template

        for script_path in scripts:
            raw_sql = script_path.read_text()
            resolved_sql = resolve_template(raw_sql, ctx)

            result = run_sql(resolved_sql, self.connection)
            if not result.success:
                console.print(f"[red]Script failed: {script_path.name} — {result.error}[/red]")
                return False

            console.print(f"[dim]Executed: {script_path.name}[/dim]")
        return True
