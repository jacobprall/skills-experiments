"""Agent adapter abstract base class."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from sfbench.models.task import TaskConfig, TrialContext
from sfbench.models.transcript import NormalizedTranscript, TranscriptEntry


class AgentAdapter(ABC):
    """Base class for all agent adapters."""

    name: str = "base"

    def __init__(self, model: Optional[str] = None, connection: str = "default"):
        self.model = model
        self.connection = connection

    @abstractmethod
    def execute(
        self,
        config: TaskConfig,
        ctx: TrialContext,
        step_prompts: list[str],
    ) -> NormalizedTranscript:
        """Execute the task prompts and return a normalized transcript.

        For single-step tasks, step_prompts will have one entry.
        For multi-step tasks, the adapter sends them sequentially,
        continuing the same session.
        """
        ...

    def setup_workspace(self, config: TaskConfig, ctx: TrialContext, plugin_set: str) -> None:
        """Optional: set up agent workspace (skills, rules, etc.)."""
        pass

    def cleanup_workspace(self) -> None:
        """Optional: clean up agent workspace after trial."""
        pass


def get_agent_adapter(name: str, model: Optional[str] = None, connection: str = "default") -> AgentAdapter:
    """Factory function to get an agent adapter by name."""
    if name == "sage":
        from sfbench.agents.sage import SageAdapter
        return SageAdapter(connection=connection)
    elif name == "cursor":
        from sfbench.agents.cursor import CursorAdapter
        return CursorAdapter(model=model, connection=connection)
    elif name == "claude":
        from sfbench.agents.claude import ClaudeAdapter
        return ClaudeAdapter(model=model, connection=connection)
    else:
        raise ValueError(f"Unknown agent: {name}")
