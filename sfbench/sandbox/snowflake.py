"""Snowflake SQL execution helpers via the snow CLI."""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field


@dataclass
class SQLResult:
    """Result of a SQL execution."""

    raw_output: str
    rows: list[dict] = field(default_factory=list)
    success: bool = True
    error: str = ""


def run_sql(query: str, connection: str = "default") -> SQLResult:
    """Execute SQL via `snow sql` and return parsed result."""
    cmd = ["snow", "sql", "-q", query, "-c", connection, "--format", "JSON"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        return SQLResult(raw_output="", success=False, error="Query timed out after 120s")

    output = proc.stdout.strip()

    if proc.returncode != 0:
        return SQLResult(
            raw_output=output,
            success=False,
            error=proc.stderr.strip() or output or f"snow sql exited {proc.returncode}",
        )

    rows = _parse_json_output(output)
    return SQLResult(raw_output=output, rows=rows)


def run_sql_as_role(query: str, role: str, connection: str = "default") -> SQLResult:
    """Execute SQL after switching to a specific role."""
    combined = f"USE ROLE {role};\n{query}"
    return run_sql(combined, connection)


def run_sql_file(path: str, connection: str = "default") -> SQLResult:
    """Execute a .sql file."""
    cmd = ["snow", "sql", "-f", path, "-c", connection, "--format", "JSON"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        return SQLResult(raw_output="", success=False, error="File execution timed out after 120s")

    output = proc.stdout.strip()

    if proc.returncode != 0:
        return SQLResult(
            raw_output=output,
            success=False,
            error=proc.stderr.strip() or output or f"snow sql exited {proc.returncode}",
        )

    rows = _parse_json_output(output)
    return SQLResult(raw_output=output, rows=rows)


def _parse_json_output(output: str, last_result_set: bool = False) -> list[dict]:
    """Parse JSON output from snow sql.

    Multi-statement queries return nested arrays: [[{row}], [{row}], [{row}]].
    Single-statement queries return a flat array: [{row}].

    When last_result_set=True, returns only the last result set (for evaluator queries).
    Otherwise returns all rows flattened.
    """
    if not output:
        return []

    try:
        parsed = json.loads(output)
    except json.JSONDecodeError:
        return []

    if not isinstance(parsed, list) or len(parsed) == 0:
        return [parsed] if isinstance(parsed, dict) else []

    # Check if it's nested (multi-statement): [[{...}], [{...}]]
    if parsed and isinstance(parsed[0], list):
        if last_result_set:
            # Return only the last result set
            return parsed[-1] if parsed[-1] else []
        else:
            # Flatten all result sets
            rows: list[dict] = []
            for result_set in parsed:
                if isinstance(result_set, list):
                    rows.extend(result_set)
            return rows

    # Single result set: [{...}, ...]
    return parsed


def run_sql_last_result(query: str, connection: str = "default") -> SQLResult:
    """Execute SQL and return only the last result set.

    Useful for multi-statement queries where only the final SELECT matters
    (e.g., SET var; EXECUTE IMMEDIATE; SELECT FROM RESULT_SCAN).
    """
    cmd = ["snow", "sql", "-q", query, "-c", connection, "--format", "JSON"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        return SQLResult(raw_output="", success=False, error="Query timed out after 120s")

    output = proc.stdout.strip()

    if proc.returncode != 0:
        return SQLResult(
            raw_output=output,
            success=False,
            error=proc.stderr.strip() or output or f"snow sql exited {proc.returncode}",
        )

    rows = _parse_json_output(output, last_result_set=True)
    return SQLResult(raw_output=output, rows=rows)
