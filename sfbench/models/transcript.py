"""Pydantic models for normalized transcripts."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    name: str
    arguments: dict = Field(default_factory=dict)
    result: Optional[str] = None


class TranscriptEntry(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.now)
    role: str  # orchestrator | agent | tool_result | system
    content: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    sql_statements: list[str] = Field(default_factory=list)
    step_id: Optional[int] = None
    metadata: dict = Field(default_factory=dict)


class NormalizedTranscript(BaseModel):
    task_id: str
    agent: str
    plugin_set: str
    model: Optional[str] = None
    started_at: datetime = Field(default_factory=datetime.now)
    entries: list[TranscriptEntry] = Field(default_factory=list)


def save_transcript(transcript: NormalizedTranscript, path: Path) -> None:
    """Write transcript as JSONL."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for entry in transcript.entries:
            f.write(entry.model_dump_json() + "\n")


def load_transcript(path: Path) -> list[TranscriptEntry]:
    """Read JSONL transcript file."""
    entries = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(TranscriptEntry(**json.loads(line)))
    return entries
