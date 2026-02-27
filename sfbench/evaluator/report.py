"""Report generator — merge SQL + LLM results into TrialResult + markdown report."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console

from sfbench.models.task import TaskConfig
from sfbench.models.trial import AssertionResult, RequirementResult, TrapResult, TrialResult

console = Console()


def generate_markdown_report(
    result: TrialResult,
    config: TaskConfig,
    output_dir: Path,
) -> Path:
    """Generate a markdown analysis report for a trial."""
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "analysis.md"

    lines = [
        f"# Trial Report: {result.task_id}",
        "",
        f"- **Agent:** {result.agent}",
        f"- **Plugin Set:** {result.plugin_set}",
        f"- **Model:** {result.model or 'default'}",
        f"- **Run ID:** {result.run_id}",
        f"- **Started:** {result.started_at.isoformat()}",
        f"- **Duration:** {result.duration_seconds:.1f}s",
        "",
        "---",
        "",
    ]

    # Overall result
    gate_status = "PASSED" if result.passed else "FAILED"
    lines.extend([
        f"## Overall: {gate_status}",
        "",
        f"- **Score:** {result.total_points_earned}/{result.total_points_available} "
        f"({result.composite_pct:.0f}%)",
        "",
    ])

    # Requirements
    lines.extend(["## Requirements (Gates)", ""])
    if result.requirement_results:
        lines.append("| Requirement | Status | Details |")
        lines.append("|---|---|---|")
        for req in result.requirement_results:
            status = "PASS" if req.passed else "**FAIL**"
            detail = req.error or req.actual_value or ""
            lines.append(f"| {req.id} | {status} | {_truncate(detail, 80)} |")
    else:
        lines.append("*No requirements defined.*")
    lines.append("")

    # Assertions
    lines.extend(["## Assertions (Points)", ""])
    if result.assertion_results:
        lines.append("| Assertion | Category | Type | Points | Details |")
        lines.append("|---|---|---|---|---|")
        for a in result.assertion_results:
            pts = f"{a.points_earned}/{a.points_available}"
            detail = a.error or a.actual_value or ""
            lines.append(
                f"| {a.id} | {a.category} | {a.type} | {pts} | {_truncate(detail, 60)} |"
            )
        total = f"**{result.total_points_earned}/{result.total_points_available}**"
        lines.append(f"| **Total** | | | {total} | |")
    else:
        lines.append("*No assertions defined.*")
    lines.append("")

    # Traps
    if result.trap_results:
        lines.extend(["## Trap Detection", ""])
        lines.append("| Trap | Detected | Points | Evidence |")
        lines.append("|---|---|---|---|")
        for t in result.trap_results:
            detected = "Yes" if t.detected else "No"
            pts = f"{t.points_earned}/{t.points_available}"
            evidence = _truncate(t.evidence or "", 60)
            lines.append(f"| {t.id} | {detected} | {pts} | {evidence} |")
        lines.append("")

    # Error
    if result.error:
        lines.extend([
            "## Errors",
            "",
            f"```\n{result.error}\n```",
            "",
        ])

    # Transcript reference
    if result.transcript_path:
        lines.extend([
            "## Transcript",
            "",
            f"Full transcript: `{result.transcript_path}`",
            "",
        ])

    report_text = "\n".join(lines)
    report_path.write_text(report_text)
    console.print(f"  [dim]Report written: {report_path}[/dim]")
    return report_path


def _truncate(text: str, max_len: int) -> str:
    text = text.replace("\n", " ").replace("|", "\\|")
    if len(text) > max_len:
        return text[:max_len - 3] + "..."
    return text
