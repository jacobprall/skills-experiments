#!/usr/bin/env python3
"""
Analyze experiment transcripts from Cursor (.jsonl) or Cortex Code (.jsonl).

Extracts:
  - Turn counts (user vs assistant messages)
  - Estimated tokens (chars / 4 approximation)
  - SQL queries detected (snow sql -q or raw SQL blocks)
  - Tool/file reads detected
  - Conversation length and density metrics

Usage:
  python analyze_transcript.py <transcript.jsonl> [--arm cursor|cortex] [--test T1]
  python analyze_transcript.py --compare <cursor.jsonl> <cortex.jsonl> [--test T1]
"""

import json
import re
import sys
import argparse
from pathlib import Path
from dataclasses import dataclass, field, asdict


@dataclass
class TranscriptMetrics:
    arm: str
    test: str
    file: str
    total_turns: int = 0
    user_turns: int = 0
    assistant_turns: int = 0
    user_chars: int = 0
    assistant_chars: int = 0
    user_est_tokens: int = 0
    assistant_est_tokens: int = 0
    total_est_tokens: int = 0
    sql_queries: list = field(default_factory=list)
    sql_query_count: int = 0
    file_reads: list = field(default_factory=list)
    file_read_count: int = 0
    tool_calls: list = field(default_factory=list)
    tool_call_count: int = 0
    snow_cli_commands: list = field(default_factory=list)
    snow_cli_count: int = 0


def estimate_tokens(text: str) -> int:
    return len(text) // 4


def extract_sql_queries(text: str) -> list[str]:
    """Extract SQL queries from snow sql -q commands and SQL code blocks."""
    queries = []

    snow_sql_pattern = re.findall(
        r'snow\s+sql\s+-q\s+["\'](.+?)["\']',
        text,
        re.DOTALL,
    )
    queries.extend(snow_sql_pattern)

    snow_sql_multiline = re.findall(
        r'snow\s+sql\s+-q\s+"(.*?)"',
        text,
        re.DOTALL,
    )
    for q in snow_sql_multiline:
        if q not in queries:
            queries.extend([q])

    sql_blocks = re.findall(
        r'```sql\s*\n(.*?)```',
        text,
        re.DOTALL,
    )
    queries.extend(sql_blocks)

    return queries


def extract_snow_commands(text: str) -> list[str]:
    """Extract all snow CLI commands (not just sql)."""
    return re.findall(r'(snow\s+(?:sql|object|streamlit|stage|cortex)\s+[^\n]+)', text)


def extract_file_reads(text: str) -> list[str]:
    """Extract file read references (skill files, playbooks, primitives)."""
    patterns = [
        r'(?:Read|read|Reading|reading)\s+[`"]?([^\s`"]+\.(?:md|yaml|sql))[`"]?',
        r'(?:standard-skills-library/[^\s`"]+\.md)',
    ]
    files = []
    for p in patterns:
        files.extend(re.findall(p, text))
    return list(set(files))


def extract_tool_calls(text: str) -> list[str]:
    """Extract tool call patterns from assistant messages."""
    patterns = [
        r'(SHOW\s+\w+)',
        r'(DESCRIBE\s+\w+)',
        r'(CREATE\s+(?:OR\s+REPLACE\s+)?(?:DYNAMIC\s+TABLE|TABLE|VIEW|MASKING\s+POLICY|ROW\s+ACCESS\s+POLICY|STREAMLIT|RESOURCE\s+MONITOR)\s+\S+)',
        r'(ALTER\s+(?:TABLE|DYNAMIC\s+TABLE)\s+\S+)',
        r'(DROP\s+\w+\s+IF\s+EXISTS\s+\S+)',
        r'(SYSTEM\$CLASSIFY)',
        r'(AI_CLASSIFY|AI_EXTRACT|AI_SENTIMENT|AI_COMPLETE|AI_SUMMARIZE_AGG)',
    ]
    calls = []
    for p in patterns:
        calls.extend(re.findall(p, text, re.IGNORECASE))
    return calls


def parse_transcript(filepath: str, arm: str = "unknown", test: str = "unknown") -> TranscriptMetrics:
    metrics = TranscriptMetrics(arm=arm, test=test, file=str(filepath))

    with open(filepath) as f:
        lines = [json.loads(line.strip()) for line in f if line.strip()]

    for obj in lines:
        role = obj.get("role", "unknown")
        # Support both formats: top-level "content" (Cortex export) and nested "message.content"
        content = obj.get("content") or obj.get("message", {}).get("content", [])

        if isinstance(content, list):
            text = " ".join(c.get("text", "") for c in content if isinstance(c, dict))
        elif isinstance(content, str):
            text = content
        else:
            text = str(content)

        metrics.total_turns += 1
        chars = len(text)
        tokens = estimate_tokens(text)

        if role == "user":
            metrics.user_turns += 1
            metrics.user_chars += chars
            metrics.user_est_tokens += tokens
        elif role == "assistant":
            metrics.assistant_turns += 1
            metrics.assistant_chars += chars
            metrics.assistant_est_tokens += tokens

            metrics.sql_queries.extend(extract_sql_queries(text))
            metrics.snow_cli_commands.extend(extract_snow_commands(text))
            metrics.file_reads.extend(extract_file_reads(text))
            metrics.tool_calls.extend(extract_tool_calls(text))

    metrics.total_est_tokens = metrics.user_est_tokens + metrics.assistant_est_tokens
    metrics.sql_query_count = len(metrics.sql_queries)
    metrics.snow_cli_count = len(metrics.snow_cli_commands)
    metrics.file_read_count = len(metrics.file_reads)
    metrics.tool_call_count = len(metrics.tool_calls)

    return metrics


def print_metrics(m: TranscriptMetrics):
    print(f"\n{'=' * 60}")
    print(f"  {m.arm.upper()} — {m.test}")
    print(f"  File: {m.file}")
    print(f"{'=' * 60}")
    print(f"\n  Turns")
    print(f"    User:          {m.user_turns}")
    print(f"    Assistant:     {m.assistant_turns}")
    print(f"    Total:         {m.total_turns}")
    print(f"\n  Estimated Tokens (chars / 4)")
    print(f"    User:          {m.user_est_tokens:,}")
    print(f"    Assistant:     {m.assistant_est_tokens:,}")
    print(f"    Total:         {m.total_est_tokens:,}")
    print(f"\n  Actions")
    print(f"    SQL queries:   {m.sql_query_count}")
    print(f"    Snow CLI cmds: {m.snow_cli_count}")
    print(f"    File reads:    {m.file_read_count}")
    print(f"    DDL/DML ops:   {m.tool_call_count}")
    if m.file_reads:
        print(f"\n  Skill Files Read:")
        for f in sorted(set(m.file_reads)):
            print(f"    - {f}")
    if m.sql_queries:
        print(f"\n  SQL Queries ({m.sql_query_count}):")
        for i, q in enumerate(m.sql_queries[:10], 1):
            preview = q.strip().replace("\n", " ")[:80]
            print(f"    {i}. {preview}...")
        if m.sql_query_count > 10:
            print(f"    ... and {m.sql_query_count - 10} more")


def print_comparison(cursor: TranscriptMetrics, cortex: TranscriptMetrics):
    print(f"\n{'=' * 70}")
    print(f"  COMPARISON — {cursor.test}")
    print(f"{'=' * 70}")
    print(f"\n  {'Metric':<30} {'Cursor':<15} {'Cortex Code':<15} {'Delta':<10}")
    print(f"  {'-' * 70}")

    rows = [
        ("User turns", cursor.user_turns, cortex.user_turns),
        ("Assistant turns", cursor.assistant_turns, cortex.assistant_turns),
        ("Total turns", cursor.total_turns, cortex.total_turns),
        ("Est. tokens (user)", cursor.user_est_tokens, cortex.user_est_tokens),
        ("Est. tokens (assistant)", cursor.assistant_est_tokens, cortex.assistant_est_tokens),
        ("Est. tokens (total)", cursor.total_est_tokens, cortex.total_est_tokens),
        ("SQL queries", cursor.sql_query_count, cortex.sql_query_count),
        ("Snow CLI commands", cursor.snow_cli_count, cortex.snow_cli_count),
        ("File reads", cursor.file_read_count, cortex.file_read_count),
        ("DDL/DML operations", cursor.tool_call_count, cortex.tool_call_count),
    ]

    for label, c_val, x_val in rows:
        if isinstance(c_val, int):
            delta = c_val - x_val
            sign = "+" if delta > 0 else ""
            print(f"  {label:<30} {c_val:<15,} {x_val:<15,} {sign}{delta}")


def export_json(metrics: TranscriptMetrics, outpath: str):
    d = asdict(metrics)
    d["sql_queries"] = [q.strip()[:200] for q in d["sql_queries"]]
    d["snow_cli_commands"] = [c.strip()[:200] for c in d["snow_cli_commands"]]
    d["tool_calls"] = [t.strip()[:200] for t in d["tool_calls"]]
    with open(outpath, "w") as f:
        json.dump(d, f, indent=2)
    print(f"\n  Exported to {outpath}")


def main():
    parser = argparse.ArgumentParser(description="Analyze experiment transcripts")
    parser.add_argument("transcript", nargs="?", help="Path to transcript .jsonl file")
    parser.add_argument("--arm", choices=["cursor", "cortex"], default="cursor")
    parser.add_argument("--test", default="unknown", help="Test ID (T1-T6)")
    parser.add_argument("--compare", nargs=2, metavar=("CURSOR_FILE", "CORTEX_FILE"),
                        help="Compare two transcripts side by side")
    parser.add_argument("--export", help="Export metrics to JSON file")

    args = parser.parse_args()

    if args.compare:
        cursor_m = parse_transcript(args.compare[0], arm="cursor", test=args.test)
        cortex_m = parse_transcript(args.compare[1], arm="cortex", test=args.test)
        print_metrics(cursor_m)
        print_metrics(cortex_m)
        print_comparison(cursor_m, cortex_m)
    elif args.transcript:
        m = parse_transcript(args.transcript, arm=args.arm, test=args.test)
        print_metrics(m)
        if args.export:
            export_json(m, args.export)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
