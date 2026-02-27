"""SFBench CLI — run, validate, view, seed."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(name="sfbench", help="Snowflake Operations Benchmark")
console = Console()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = PROJECT_ROOT / "tasks"
RESULTS_DIR = PROJECT_ROOT / "results"


@app.command()
def run(
    task_ids: list[str] = typer.Argument(..., help="Task IDs to run, or 'all'"),
    agent: str = typer.Option("sage", help="Agent to use: sage, cursor, claude"),
    plugin_set: str = typer.Option("none", "--plugin-set", help="Plugin set name"),
    model: Optional[str] = typer.Option(None, help="Model override for the agent"),
    connection: str = typer.Option("default", help="Snowflake connection name"),
    difficulty: Optional[str] = typer.Option(None, help="Filter by difficulty tier"),
    domain: Optional[str] = typer.Option(None, help="Filter by domain"),
    n_concurrent: int = typer.Option(1, "--n-concurrent", help="Max concurrent trials"),
    n_attempts: int = typer.Option(1, "--n-attempts", help="Attempts per task"),
    timeout: int = typer.Option(600, help="Timeout per task in seconds"),
    persist: bool = typer.Option(False, help="Keep sandbox schemas after trial"),
    tasks_dir: Optional[Path] = typer.Option(None, "--tasks-dir", help="Custom tasks directory"),
) -> None:
    """Run benchmark tasks against an agent."""
    from sfbench.models.task import load_task_configs
    from sfbench.runner.trial import run_trial
    from sfbench.agents.base import get_agent_adapter

    effective_tasks_dir = tasks_dir or TASKS_DIR
    configs = load_task_configs(effective_tasks_dir, task_ids, difficulty=difficulty, domain=domain)

    if not configs:
        console.print("[red]No matching tasks found.[/red]")
        raise typer.Exit(1)

    console.print(f"Running {len(configs)} task(s) with agent={agent}, plugin_set={plugin_set}")

    adapter = get_agent_adapter(agent, model=model, connection=connection)
    all_results = []

    for config in configs:
        for attempt in range(n_attempts):
            result = run_trial(
                config,
                adapter,
                plugin_set=plugin_set,
                connection=connection,
                persist=persist,
                timeout=timeout,
            )
            all_results.append(result)

    _print_summary(all_results)


@app.command()
def validate(
    task_ids: list[str] = typer.Argument(None, help="Task IDs to validate, or omit for all"),
    connection: str = typer.Option("default", help="Snowflake connection name"),
    tasks_dir: Optional[Path] = typer.Option(None, "--tasks-dir", help="Custom tasks directory"),
) -> None:
    """Validate tasks by running sage agent and checking all requirements pass."""
    from sfbench.models.task import load_task_configs
    from sfbench.runner.trial import run_trial
    from sfbench.agents.sage import SageAdapter

    effective_tasks_dir = tasks_dir or TASKS_DIR
    ids = task_ids or ["all"]
    configs = load_task_configs(effective_tasks_dir, ids)

    if not configs:
        console.print("[red]No tasks found.[/red]")
        raise typer.Exit(1)

    console.print(f"Validating {len(configs)} task(s) with sage agent...")
    adapter = SageAdapter(connection=connection)
    failures = []

    for config in configs:
        result = run_trial(config, adapter, plugin_set="none", connection=connection, persist=False)
        status = "[green]PASS[/green]" if result.passed else "[red]FAIL[/red]"
        console.print(f"  {config.task_id}: {status} ({result.composite_pct:.0f}%)")
        if not result.passed:
            for req_id, req_pass in result.requirements.items():
                if not req_pass:
                    console.print(f"    [red]REQUIREMENT FAILED: {req_id}[/red]")
            failures.append(config.task_id)

    if failures:
        console.print(f"\n[red]{len(failures)} task(s) failed validation.[/red]")
        raise typer.Exit(1)
    else:
        console.print(f"\n[green]All {len(configs)} task(s) passed validation.[/green]")


@app.command()
def view(
    what: str = typer.Argument("results", help="What to view: results, tasks, dashboard"),
    output: Optional[Path] = typer.Option(None, "--output", help="Output path for dashboard HTML"),
) -> None:
    """View results, task inventory, or generate HTML dashboard."""
    if what == "tasks":
        _view_tasks()
    elif what == "dashboard":
        from sfbench.evaluator.dashboard import generate_dashboard
        path = generate_dashboard(output)
        if path and path.exists():
            console.print(f"[green]Dashboard: {path}[/green]")
    elif what == "results":
        _view_results()
    else:
        console.print(f"[yellow]Unknown view target: {what}. Use: tasks, results, dashboard[/yellow]")


@app.command()
def seed(
    task_ids: list[str] = typer.Argument(..., help="Task IDs to seed"),
    connection: str = typer.Option("default", help="Snowflake connection name"),
) -> None:
    """Generate solution seeds by running sage agent and capturing state."""
    console.print("[yellow]Seed generation not yet implemented.[/yellow]")


def _view_tasks() -> None:
    from sfbench.models.task import load_task_configs

    configs = load_task_configs(TASKS_DIR, ["all"])
    table = Table(title="SFBench Task Library")
    table.add_column("ID")
    table.add_column("Difficulty")
    table.add_column("Domains")
    table.add_column("Steps")
    table.add_column("Traps")
    table.add_column("Requirements")
    table.add_column("Assertions")

    for c in configs:
        table.add_row(
            c.task_id,
            c.difficulty,
            ", ".join(c.domains),
            str(len(c.steps)),
            str(len(c.traps)),
            str(len(c.requirements)),
            str(len(c.assertions)),
        )
    console.print(table)


def _view_results() -> None:
    """Show latest results in a summary table."""
    import json

    result_files = sorted(RESULTS_DIR.rglob("trial_result.json")) if RESULTS_DIR.exists() else []
    if not result_files:
        console.print("[yellow]No results found. Run some tasks first.[/yellow]")
        return

    table = Table(title="All Results")
    table.add_column("Run ID")
    table.add_column("Task")
    table.add_column("Agent")
    table.add_column("Result")
    table.add_column("Score")
    table.add_column("Duration")

    for f in result_files[-50:]:  # last 50
        try:
            data = json.loads(f.read_text())
            passed = data.get("passed", False)
            status = "[green]PASS[/green]" if passed else "[red]FAIL[/red]"
            table.add_row(
                data.get("run_id", "")[:20],
                data.get("task_id", ""),
                data.get("agent", ""),
                status,
                f"{data.get('composite_pct', 0):.0f}%",
                f"{data.get('duration_seconds', 0):.0f}s",
            )
        except Exception:
            continue

    console.print(table)
    console.print(f"\nRun `sfbench view dashboard` to generate an HTML report.")


def _print_summary(results: list) -> None:
    table = Table(title="Results Summary")
    table.add_column("Task")
    table.add_column("Result")
    table.add_column("Score")
    table.add_column("Duration")

    passed = 0
    for r in results:
        status = "[green]PASS[/green]" if r.passed else "[red]FAIL[/red]"
        table.add_row(
            r.task_id,
            status,
            f"{r.composite_pct:.0f}%",
            f"{r.duration_seconds:.0f}s",
        )
        if r.passed:
            passed += 1

    console.print(table)
    total = len(results)
    console.print(f"\n{passed}/{total} tasks passed ({100*passed/max(total,1):.0f}%)")

    # Auto-generate dashboard
    from sfbench.evaluator.dashboard import generate_dashboard
    try:
        generate_dashboard()
    except Exception:
        pass


if __name__ == "__main__":
    app()
