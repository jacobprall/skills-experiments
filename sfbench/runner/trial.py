"""Trial runner — full lifecycle: setup → agent → evaluate → teardown."""

from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console

from sfbench.agents.base import AgentAdapter
from sfbench.evaluator.sql import evaluate_requirements, evaluate_sql_assertions
from sfbench.models.task import TaskConfig, TrialContext, resolve_task_config
from sfbench.models.transcript import save_transcript
from sfbench.models.trial import TrialResult
from sfbench.sandbox.manager import SandboxManager

console = Console()

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS_DIR = PROJECT_ROOT / "results"


def run_trial(
    config: TaskConfig,
    agent: AgentAdapter,
    plugin_set: str = "none",
    connection: str = "default",
    persist: bool = False,
    timeout: int = 600,
) -> TrialResult:
    """Run a single trial: sandbox setup → agent execution → evaluation → teardown."""
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
    sandbox = SandboxManager(connection=connection)

    console.print(f"\n[bold]{'='*60}[/bold]")
    console.print(f"[bold]Task: {config.task_id}[/bold] (agent={agent.name}, plugin_set={plugin_set})")
    console.print(f"[bold]{'='*60}[/bold]")

    result = TrialResult(
        task_id=config.task_id,
        agent=agent.name,
        plugin_set=plugin_set,
        model=agent.model,
        run_id=run_id,
        started_at=datetime.now(),
    )

    ctx = sandbox.create_trial_context(config.task_id)

    try:
        # 1. Create sandbox schemas
        console.print("\n[bold]Setting up sandbox...[/bold]")
        if not sandbox.setup_sandbox(ctx):
            result.error = "Sandbox setup failed"
            result.finished_at = datetime.now()
            return result

        # 2. Resolve template variables in task config
        resolved_config = resolve_task_config(config, ctx)

        # 3. Run shared environment scripts
        if config.environment:
            console.print(f"[bold]Loading environment: {config.environment}[/bold]")
            if not sandbox.run_environment_scripts(config.environment, ctx):
                result.error = "Environment setup failed"
                result.finished_at = datetime.now()
                if not persist:
                    sandbox.teardown_sandbox(ctx)
                return result

        # 4. Run task-specific setup scripts
        if config.setup.scripts:
            console.print("[bold]Running task setup scripts...[/bold]")
            if not sandbox.run_task_setup_scripts(config, ctx):
                result.error = "Task setup failed"
                result.finished_at = datetime.now()
                if not persist:
                    sandbox.teardown_sandbox(ctx)
                return result

        # 5. Set up agent workspace (plugin set)
        if agent.name != "sage":
            from sfbench.agents.plugins import configure_workspace
            agent.setup_workspace(resolved_config, ctx, plugin_set)
            if hasattr(agent, '_workspace_dir') and agent._workspace_dir:
                configure_workspace(agent._workspace_dir, plugin_set)

        # 7. Execute agent via orchestrator
        console.print(f"\n[bold]Running agent: {agent.name}[/bold]")
        from sfbench.orchestrator.runner import Orchestrator

        has_adversarial = any(
            s.type.value in ("adversarial", "red_herring", "redirect")
            for s in resolved_config.steps
        )
        orchestrator = Orchestrator(use_llm=has_adversarial)
        transcript = orchestrator.run(resolved_config, ctx, agent)

        # Save transcript
        trial_dir = RESULTS_DIR / run_id / config.task_id
        trial_dir.mkdir(parents=True, exist_ok=True)
        transcript_path = trial_dir / "transcript.jsonl"
        save_transcript(transcript, transcript_path)
        result.transcript_path = str(transcript_path)

        # 6. Evaluate requirements (gates)
        console.print("\n[bold]Evaluating requirements...[/bold]")
        result.requirement_results = evaluate_requirements(
            resolved_config.requirements, ctx
        )

        # Evaluate SQL assertions (points)
        console.print("\n[bold]Evaluating assertions...[/bold]")
        result.assertion_results = evaluate_sql_assertions(
            resolved_config.assertions, ctx
        )

        # Evaluate behavioral assertions via LLM (if any)
        behavioral = [a for a in resolved_config.assertions if a.type.value == "behavioral"]
        if behavioral and agent.name != "sage":
            from sfbench.evaluator.llm import evaluate_behavioral_assertions
            console.print("\n[bold]Evaluating behavioral assertions (LLM)...[/bold]")
            behavioral_results = evaluate_behavioral_assertions(
                resolved_config.assertions, transcript.entries, resolved_config
            )
            result.assertion_results.extend(behavioral_results)

        # Evaluate traps via LLM (if any)
        if resolved_config.traps and agent.name != "sage":
            from sfbench.evaluator.llm import evaluate_traps
            console.print("\n[bold]Evaluating trap detection (LLM)...[/bold]")
            result.trap_results = evaluate_traps(
                resolved_config.traps, transcript.entries, resolved_config
            )

        result.finished_at = datetime.now()

        # Save result JSON
        result_path = trial_dir / "trial_result.json"
        result_path.write_text(result.model_dump_json(indent=2))

        # Generate markdown report
        from sfbench.evaluator.report import generate_markdown_report
        generate_markdown_report(result, resolved_config, trial_dir)

        _print_trial_result(result)

    except Exception as e:
        result.error = str(e)
        result.finished_at = datetime.now()
        console.print(f"[red]Trial error: {e}[/red]")

    finally:
        if agent.name != "sage":
            agent.cleanup_workspace()
        if not persist:
            console.print("\n[bold]Tearing down sandbox...[/bold]")
            sandbox.teardown_sandbox(ctx)
        else:
            console.print(f"\n[yellow]Sandbox persisted. Schemas: {ctx.raw_schema}, ...[/yellow]")

    return result


def _print_trial_result(result: TrialResult) -> None:
    """Print a summary of the trial result."""
    console.print(f"\n[bold]{'─'*40}[/bold]")
    gate_status = "[green]PASSED[/green]" if result.passed else "[red]FAILED[/red]"
    console.print(f"  Gates: {gate_status}")
    console.print(f"  Score: {result.total_points_earned}/{result.total_points_available} ({result.composite_pct:.0f}%)")
    console.print(f"  Duration: {result.duration_seconds:.1f}s")
    if result.error:
        console.print(f"  [red]Error: {result.error}[/red]")
    console.print(f"[bold]{'─'*40}[/bold]")
