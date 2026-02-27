"""Sage agent — executes solution scripts directly to validate task correctness."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console

from sfbench.agents.base import AgentAdapter
from sfbench.models.task import TaskConfig, TrialContext, resolve_template
from sfbench.models.transcript import NormalizedTranscript, TranscriptEntry
from sfbench.sandbox.snowflake import run_sql

console = Console()


class SageAdapter(AgentAdapter):
    name = "sage"

    def __init__(self, connection: str = "default"):
        super().__init__(model=None, connection=connection)

    def execute(
        self,
        config: TaskConfig,
        ctx: TrialContext,
        step_prompts: list[str],
    ) -> NormalizedTranscript:
        """Execute solution/*.sql scripts in order."""
        transcript = NormalizedTranscript(
            task_id=config.task_id,
            agent="sage",
            plugin_set="none",
            started_at=datetime.now(),
        )

        if not config.task_dir:
            transcript.entries.append(TranscriptEntry(
                role="system",
                content="Error: task_dir not set",
            ))
            return transcript

        solution_dir = config.task_dir / "solution"
        if not solution_dir.exists():
            transcript.entries.append(TranscriptEntry(
                role="system",
                content=f"Error: solution directory not found at {solution_dir}",
            ))
            return transcript

        scripts = config.solution.scripts
        if not scripts:
            scripts = sorted(f.name for f in solution_dir.glob("*.sql"))

        for script_name in scripts:
            script_path = solution_dir / script_name
            if not script_path.exists():
                transcript.entries.append(TranscriptEntry(
                    role="system",
                    content=f"Error: script not found: {script_path}",
                ))
                continue

            raw_sql = script_path.read_text()
            resolved_sql = resolve_template(raw_sql, ctx)

            transcript.entries.append(TranscriptEntry(
                role="agent",
                content=f"Executing {script_name}",
                sql_statements=[resolved_sql],
            ))

            result = run_sql(resolved_sql, self.connection)

            transcript.entries.append(TranscriptEntry(
                role="tool_result",
                content=result.raw_output if result.success else f"ERROR: {result.error}",
                metadata={"success": result.success, "script": script_name},
            ))

            if result.success:
                console.print(f"  [dim]Sage executed: {script_name}[/dim]")
            else:
                console.print(f"  [red]Sage failed: {script_name} — {result.error}[/red]")

        return transcript
