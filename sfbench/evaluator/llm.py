"""LLM transcript evaluator — analyzes agent behavior from JSONL transcripts."""

from __future__ import annotations

import json
from typing import Optional

from rich.console import Console

from sfbench.models.task import Assertion, AssertionType, TaskConfig, Trap
from sfbench.models.transcript import TranscriptEntry
from sfbench.models.trial import AssertionResult, TrapResult

console = Console()

DEFAULT_MODEL = "claude-sonnet-4-20250514"


def evaluate_behavioral_assertions(
    assertions: list[Assertion],
    transcript_entries: list[TranscriptEntry],
    config: TaskConfig,
    model: str = DEFAULT_MODEL,
) -> list[AssertionResult]:
    """Use an LLM to evaluate behavioral assertions against the transcript."""
    behavioral = [a for a in assertions if a.type == AssertionType.BEHAVIORAL]
    if not behavioral:
        return []

    transcript_text = _format_transcript(transcript_entries)
    results: list[AssertionResult] = []

    rubric_items = []
    for a in behavioral:
        rubric_items.append({
            "id": a.id,
            "category": a.category,
            "points": a.points,
            "rubric": a.rubric or a.description,
        })

    try:
        import anthropic

        client = anthropic.Anthropic()

        system = (
            "You are an expert evaluator for a Snowflake operations benchmark. "
            "You analyze agent transcripts to assess behavioral quality.\n\n"
            "For each rubric item, determine if the agent demonstrated the described behavior. "
            "Respond with a JSON object containing an 'evaluations' array. Each evaluation has:\n"
            "- id: the assertion id\n"
            "- passed: boolean\n"
            "- reasoning: brief explanation (1-2 sentences)\n"
            "- evidence: relevant quote from transcript (if any)\n\n"
            "Be fair but rigorous. Only mark passed=true if there's clear evidence."
        )

        user_msg = (
            f"## Task\n{config.description}\n\n"
            f"## Agent Transcript\n```\n{transcript_text}\n```\n\n"
            f"## Rubric Items\n```json\n{json.dumps(rubric_items, indent=2)}\n```\n\n"
            "Evaluate each rubric item. Return JSON only."
        )

        message = client.messages.create(
            model=model,
            max_tokens=2000,
            system=system,
            messages=[{"role": "user", "content": user_msg}],
        )

        response_text = message.content[0].text
        evaluations = _parse_llm_evaluations(response_text)

        eval_map = {e["id"]: e for e in evaluations}

        for a in behavioral:
            ev = eval_map.get(a.id, {})
            passed = ev.get("passed", False)
            results.append(AssertionResult(
                id=a.id,
                category=a.category,
                type="behavioral",
                points_available=a.points,
                points_earned=a.points if passed else 0,
                passed=passed,
                description=a.description,
                actual_value=ev.get("reasoning", ""),
            ))

            status = f"[green]+{a.points}[/green]" if passed else "[dim]+0[/dim]"
            console.print(f"  Behavioral {a.id}: {status} / {a.points}")

    except Exception as e:
        console.print(f"  [red]LLM evaluation error: {e}[/red]")
        for a in behavioral:
            results.append(AssertionResult(
                id=a.id,
                category=a.category,
                type="behavioral",
                points_available=a.points,
                points_earned=0,
                passed=False,
                description=a.description,
                error=str(e),
            ))

    return results


def evaluate_traps(
    traps: list[Trap],
    transcript_entries: list[TranscriptEntry],
    config: TaskConfig,
    model: str = DEFAULT_MODEL,
) -> list[TrapResult]:
    """Use an LLM to detect whether the agent identified and handled traps."""
    if not traps:
        return []

    transcript_text = _format_transcript(transcript_entries)
    results: list[TrapResult] = []

    trap_items = []
    for t in traps:
        trap_items.append({
            "id": t.id,
            "description": t.description,
            "detection_method": t.detection_method,
            "points": t.points,
        })

    try:
        import anthropic

        client = anthropic.Anthropic()

        system = (
            "You are an expert evaluator for a Snowflake operations benchmark. "
            "You analyze agent transcripts to determine if the agent detected "
            "pre-seeded traps (anti-patterns, broken objects, misleading configurations).\n\n"
            "For each trap, determine if the agent:\n"
            "1. Noticed the trap (mentioned it, queried related objects)\n"
            "2. Correctly identified it as problematic\n"
            "3. Took appropriate action (fixed, warned, or explicitly chose not to change)\n\n"
            "Respond with JSON: an array of objects with:\n"
            "- id: the trap id\n"
            "- detected: boolean (true if agent noticed AND correctly identified it)\n"
            "- evidence: relevant quote or description of agent's behavior\n"
            "- reasoning: brief explanation"
        )

        user_msg = (
            f"## Task\n{config.description}\n\n"
            f"## Agent Transcript\n```\n{transcript_text}\n```\n\n"
            f"## Pre-seeded Traps\n```json\n{json.dumps(trap_items, indent=2)}\n```\n\n"
            "Evaluate each trap. Return JSON only."
        )

        message = client.messages.create(
            model=model,
            max_tokens=2000,
            system=system,
            messages=[{"role": "user", "content": user_msg}],
        )

        response_text = message.content[0].text
        evaluations = _parse_llm_evaluations(response_text, key="id")

        eval_map = {e["id"]: e for e in evaluations}

        for t in traps:
            ev = eval_map.get(t.id, {})
            detected = ev.get("detected", False)
            results.append(TrapResult(
                id=t.id,
                detected=detected,
                points_available=t.points,
                points_earned=t.points if detected else 0,
                description=t.description,
                evidence=ev.get("evidence", ""),
            ))

            status = f"[green]+{t.points}[/green]" if detected else "[dim]+0[/dim]"
            console.print(f"  Trap {t.id}: {status} / {t.points}")

    except Exception as e:
        console.print(f"  [red]LLM trap evaluation error: {e}[/red]")
        for t in traps:
            results.append(TrapResult(
                id=t.id,
                detected=False,
                points_available=t.points,
                points_earned=0,
                description=t.description,
                evidence=f"Error: {e}",
            ))

    return results


def _format_transcript(entries: list[TranscriptEntry]) -> str:
    """Format transcript entries into readable text for LLM analysis."""
    lines = []
    for entry in entries:
        prefix = f"[{entry.role}]"
        if entry.step_id:
            prefix = f"[step {entry.step_id} / {entry.role}]"

        if entry.content:
            lines.append(f"{prefix} {entry.content[:3000]}")

        for tc in entry.tool_calls:
            lines.append(f"{prefix} Tool: {tc.name}({json.dumps(tc.arguments)[:500]})")
            if tc.result:
                lines.append(f"  → {tc.result[:1000]}")

        for sql in entry.sql_statements:
            lines.append(f"{prefix} SQL: {sql[:1000]}")

    return "\n".join(lines)


def _parse_llm_evaluations(text: str, key: str = "id") -> list[dict]:
    """Extract JSON evaluation array from LLM response text."""
    # Try to find JSON in the response
    text = text.strip()

    # Remove markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    # Try parsing as-is
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict) and "evaluations" in parsed:
            return parsed["evaluations"]
        if isinstance(parsed, dict) and isinstance(parsed.get("traps"), list):
            return parsed["traps"]
        return [parsed]
    except json.JSONDecodeError:
        pass

    # Try to find array in text
    import re
    match = re.search(r'\[.*\]', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return []
