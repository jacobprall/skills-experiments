"""Cursor agent adapter — uses `agent` CLI for headless execution."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console

from sfbench.agents.base import AgentAdapter
from sfbench.models.task import TaskConfig, TrialContext
from sfbench.models.transcript import NormalizedTranscript, ToolCall, TranscriptEntry

console = Console()


class CursorAdapter(AgentAdapter):
    name = "cursor"

    def __init__(self, model: Optional[str] = None, connection: str = "default"):
        super().__init__(model=model or "sonnet-4", connection=connection)
        self._workspace_dir: Optional[Path] = None
        self._chat_id: Optional[str] = None

    def execute(
        self,
        config: TaskConfig,
        ctx: TrialContext,
        step_prompts: list[str],
    ) -> NormalizedTranscript:
        transcript = NormalizedTranscript(
            task_id=config.task_id,
            agent="cursor",
            plugin_set="none",
            model=self.model,
            started_at=datetime.now(),
        )

        for i, prompt in enumerate(step_prompts):
            transcript.entries.append(TranscriptEntry(
                role="orchestrator",
                content=prompt,
                step_id=i + 1,
            ))

            console.print(f"  [dim]Step {i+1}: sending prompt to Cursor agent...[/dim]")

            if i == 0:
                raw_output = self._send_initial(prompt)
            else:
                raw_output = self._continue(prompt)

            entries = _parse_cursor_output(raw_output, step_id=i + 1)
            transcript.entries.extend(entries)

        return transcript

    def setup_workspace(self, config: TaskConfig, ctx: TrialContext, plugin_set: str) -> None:
        self._workspace_dir = Path(tempfile.mkdtemp(prefix="sfbench_cursor_"))
        console.print(f"  [dim]Cursor workspace: {self._workspace_dir}[/dim]")

    def cleanup_workspace(self) -> None:
        if self._workspace_dir and self._workspace_dir.exists():
            shutil.rmtree(self._workspace_dir, ignore_errors=True)
        self._workspace_dir = None
        self._chat_id = None

    def _send_initial(self, prompt: str) -> str:
        cmd = [
            "agent",
            "-p",
            "--output-format", "json",
            "--yolo",
            "--trust",
            "--model", self.model or "sonnet-4",
        ]
        if self._workspace_dir:
            cmd.extend(["--workspace", str(self._workspace_dir)])

        cmd.append(prompt)
        return self._run_cmd(cmd)

    def _continue(self, prompt: str) -> str:
        cmd = [
            "agent",
            "--continue",
            "-p",
            "--output-format", "json",
            "--yolo",
            "--trust",
            "--model", self.model or "sonnet-4",
        ]
        if self._workspace_dir:
            cmd.extend(["--workspace", str(self._workspace_dir)])

        cmd.append(prompt)
        return self._run_cmd(cmd)

    def _run_cmd(self, cmd: list[str]) -> str:
        console.print(f"  [dim]Running: {' '.join(cmd[:6])}...[/dim]")
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,
            )
            return proc.stdout
        except subprocess.TimeoutExpired:
            console.print("  [red]Cursor agent timed out after 600s[/red]")
            return '{"error": "timeout"}'
        except Exception as e:
            console.print(f"  [red]Cursor agent error: {e}[/red]")
            return f'{{"error": "{e}"}}'


def _parse_cursor_output(raw: str, step_id: int) -> list[TranscriptEntry]:
    """Parse Cursor agent JSON output into transcript entries."""
    entries: list[TranscriptEntry] = []

    for line in raw.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            entries.append(TranscriptEntry(
                role="agent",
                content=line,
                step_id=step_id,
            ))
            continue

        role = msg.get("role", "agent")
        content = msg.get("content", "")
        tool_calls = []
        sql_stmts = []

        if "tool_calls" in msg:
            for tc in msg["tool_calls"]:
                tool_calls.append(ToolCall(
                    name=tc.get("name", ""),
                    arguments=tc.get("arguments", {}),
                    result=tc.get("result"),
                ))

        if "tool_result" in msg:
            content = str(msg["tool_result"])
            role = "tool_result"

        sql_stmts = _extract_sql_statements(content)

        entries.append(TranscriptEntry(
            role=role,
            content=content,
            tool_calls=tool_calls,
            sql_statements=sql_stmts,
            step_id=step_id,
        ))

    if not entries:
        entries.append(TranscriptEntry(
            role="agent",
            content=raw[:2000] if raw else "(no output)",
            step_id=step_id,
        ))

    return entries


def _extract_sql_statements(text: str) -> list[str]:
    """Extract SQL statements from text (snow sql -q "..." patterns)."""
    patterns = [
        r'snow\s+sql\s+-q\s+"([^"]+)"',
        r'snow\s+sql\s+-q\s+\'([^\']+)\'',
    ]
    stmts = []
    for p in patterns:
        stmts.extend(re.findall(p, text, re.DOTALL | re.IGNORECASE))
    return stmts
