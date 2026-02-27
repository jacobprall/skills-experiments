"""Claude Code agent adapter — uses `claude` CLI for headless execution."""

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


class ClaudeAdapter(AgentAdapter):
    name = "claude"

    def __init__(self, model: Optional[str] = None, connection: str = "default"):
        super().__init__(model=model or "sonnet", connection=connection)
        self._workspace_dir: Optional[Path] = None
        self._session_id: Optional[str] = None

    def execute(
        self,
        config: TaskConfig,
        ctx: TrialContext,
        step_prompts: list[str],
    ) -> NormalizedTranscript:
        transcript = NormalizedTranscript(
            task_id=config.task_id,
            agent="claude",
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

            console.print(f"  [dim]Step {i+1}: sending prompt to Claude Code...[/dim]")

            if i == 0:
                raw_output = self._send_initial(prompt)
            else:
                raw_output = self._resume(prompt)

            entries = _parse_claude_output(raw_output, step_id=i + 1)
            transcript.entries.extend(entries)

        return transcript

    def setup_workspace(self, config: TaskConfig, ctx: TrialContext, plugin_set: str) -> None:
        self._workspace_dir = Path(tempfile.mkdtemp(prefix="sfbench_claude_"))
        console.print(f"  [dim]Claude workspace: {self._workspace_dir}[/dim]")

    def cleanup_workspace(self) -> None:
        if self._workspace_dir and self._workspace_dir.exists():
            shutil.rmtree(self._workspace_dir, ignore_errors=True)
        self._workspace_dir = None
        self._session_id = None

    def _send_initial(self, prompt: str) -> str:
        cmd = [
            "claude",
            "-p", prompt,
            "--output-format", "json",
            "--model", self.model or "sonnet",
            "--dangerously-skip-permissions",
        ]
        return self._run_cmd(cmd)

    def _resume(self, prompt: str) -> str:
        cmd = [
            "claude",
            "-p", prompt,
            "--output-format", "json",
            "--model", self.model or "sonnet",
            "--dangerously-skip-permissions",
            "--resume",
        ]
        return self._run_cmd(cmd)

    def _run_cmd(self, cmd: list[str]) -> str:
        env = None
        if self._workspace_dir:
            import os
            env = os.environ.copy()

        console.print(f"  [dim]Running: {' '.join(cmd[:6])}...[/dim]")
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,
                cwd=str(self._workspace_dir) if self._workspace_dir else None,
                env=env,
            )
            return proc.stdout
        except subprocess.TimeoutExpired:
            console.print("  [red]Claude Code timed out after 600s[/red]")
            return '{"error": "timeout"}'
        except FileNotFoundError:
            console.print("  [red]claude CLI not found — install Claude Code first[/red]")
            return '{"error": "claude CLI not found"}'
        except Exception as e:
            console.print(f"  [red]Claude Code error: {e}[/red]")
            return f'{{"error": "{e}"}}'


def _parse_claude_output(raw: str, step_id: int) -> list[TranscriptEntry]:
    """Parse Claude Code JSON output into transcript entries."""
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

        role = msg.get("role", "assistant")
        if role == "assistant":
            role = "agent"

        content = ""
        tool_calls = []
        sql_stmts = []

        # Claude Code JSON has various message shapes
        if isinstance(msg.get("content"), str):
            content = msg["content"]
        elif isinstance(msg.get("content"), list):
            for block in msg["content"]:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        content += block.get("text", "")
                    elif block.get("type") == "tool_use":
                        tool_calls.append(ToolCall(
                            name=block.get("name", ""),
                            arguments=block.get("input", {}),
                        ))
                    elif block.get("type") == "tool_result":
                        content += str(block.get("content", ""))

        if msg.get("type") == "result":
            content = msg.get("result", content)

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
    """Extract SQL statements from text."""
    patterns = [
        r'snow\s+sql\s+-q\s+"([^"]+)"',
        r'snow\s+sql\s+-q\s+\'([^\']+)\'',
    ]
    stmts = []
    for p in patterns:
        stmts.extend(re.findall(p, text, re.DOTALL | re.IGNORECASE))
    return stmts
