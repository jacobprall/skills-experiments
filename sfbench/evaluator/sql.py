"""SQL evaluator — run requirements (gates) and SQL assertions (points)."""

from __future__ import annotations

import re

from rich.console import Console

from sfbench.models.task import Assertion, CheckType, Requirement, TrialContext
from sfbench.models.trial import AssertionResult, RequirementResult
from sfbench.sandbox.snowflake import run_sql_as_role, run_sql_last_result

console = Console()


def evaluate_requirements(
    requirements: list[Requirement], ctx: TrialContext
) -> list[RequirementResult]:
    """Run each requirement query and check pass_if condition. All must pass."""
    results: list[RequirementResult] = []

    for req in requirements:
        result = _evaluate_single_requirement(req, ctx)
        results.append(result)
        status = "[green]PASS[/green]" if result.passed else "[red]FAIL[/red]"
        console.print(f"  Requirement {req.id}: {status}")

    return results


def evaluate_sql_assertions(
    assertions: list[Assertion], ctx: TrialContext
) -> list[AssertionResult]:
    """Run each SQL assertion and compute points."""
    results: list[AssertionResult] = []

    for assertion in assertions:
        if assertion.type.value not in ("sql", "sql_as_role"):
            continue

        result = _evaluate_single_assertion(assertion, ctx)
        results.append(result)
        status = f"[green]+{result.points_earned}[/green]" if result.passed else "[dim]+0[/dim]"
        console.print(f"  Assertion {assertion.id}: {status} / {assertion.points}")

    return results


def _evaluate_single_requirement(req: Requirement, ctx: TrialContext) -> RequirementResult:
    """Run a single requirement check."""
    try:
        if req.check == CheckType.SQL_AS_ROLE and req.role:
            sql_result = run_sql_as_role(req.query, req.role, ctx.connection)
        else:
            sql_result = run_sql_last_result(req.query, ctx.connection)

        if not sql_result.success:
            return RequirementResult(
                id=req.id,
                passed=False,
                description=req.description,
                error=sql_result.error,
            )

        if not sql_result.rows:
            return RequirementResult(
                id=req.id,
                passed=False,
                description=req.description,
                error="Query returned no rows",
            )

        row = sql_result.rows[0]
        passed = _check_condition(req.pass_if, row)

        return RequirementResult(
            id=req.id,
            passed=passed,
            description=req.description,
            actual_value=str(row),
        )

    except Exception as e:
        return RequirementResult(
            id=req.id,
            passed=False,
            description=req.description,
            error=str(e),
        )


def _evaluate_single_assertion(assertion: Assertion, ctx: TrialContext) -> AssertionResult:
    """Run a single SQL assertion."""
    try:
        if not assertion.query or not assertion.check:
            return AssertionResult(
                id=assertion.id,
                category=assertion.category,
                type=assertion.type.value,
                points_available=assertion.points,
                points_earned=0,
                passed=False,
                description=assertion.description,
                error="Missing query or check",
            )

        if assertion.type.value == "sql_as_role":
            sql_result = run_sql_as_role(assertion.query, assertion.check, ctx.connection)
        else:
            sql_result = run_sql_last_result(assertion.query, ctx.connection)

        if not sql_result.success:
            return AssertionResult(
                id=assertion.id,
                category=assertion.category,
                type=assertion.type.value,
                points_available=assertion.points,
                points_earned=0,
                passed=False,
                description=assertion.description,
                error=sql_result.error,
            )

        if not sql_result.rows:
            return AssertionResult(
                id=assertion.id,
                category=assertion.category,
                type=assertion.type.value,
                points_available=assertion.points,
                points_earned=0,
                passed=False,
                description=assertion.description,
                error="Query returned no rows",
            )

        row = sql_result.rows[0]
        passed = _check_condition(assertion.check, row)

        return AssertionResult(
            id=assertion.id,
            category=assertion.category,
            type=assertion.type.value,
            points_available=assertion.points,
            points_earned=assertion.points if passed else 0,
            passed=passed,
            description=assertion.description,
            actual_value=str(row),
        )

    except Exception as e:
        return AssertionResult(
            id=assertion.id,
            category=assertion.category,
            type=assertion.type.value,
            points_available=assertion.points,
            points_earned=0,
            passed=False,
            description=assertion.description,
            error=str(e),
        )


def _check_condition(condition: str, row: dict) -> bool:
    """Evaluate a pass_if/check condition against a result row.

    Supports conditions like:
      - "gaps = 0"
      - "ct > 0"
      - "violations = 0"
      - "count >= 5"

    The row keys are matched case-insensitively.
    """
    row_lower = {k.lower(): v for k, v in row.items()}

    match = re.match(r"(\w+)\s*(=|!=|>|<|>=|<=)\s*(.+)", condition.strip())
    if not match:
        return False

    var_name = match.group(1).lower()
    operator = match.group(2)
    expected_raw = match.group(3).strip()

    actual = row_lower.get(var_name)
    if actual is None:
        return False

    try:
        actual_num = float(actual)
        expected_num = float(expected_raw)
    except (ValueError, TypeError):
        actual_str = str(actual)
        expected_str = expected_raw.strip("'\"")
        if operator == "=":
            return actual_str == expected_str
        elif operator == "!=":
            return actual_str != expected_str
        return False

    if operator == "=":
        return actual_num == expected_num
    elif operator == "!=":
        return actual_num != expected_num
    elif operator == ">":
        return actual_num > expected_num
    elif operator == "<":
        return actual_num < expected_num
    elif operator == ">=":
        return actual_num >= expected_num
    elif operator == "<=":
        return actual_num <= expected_num

    return False
