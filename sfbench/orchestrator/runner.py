"""LLM orchestrator — reads task steps and feeds prompts to agents.

For single-step tasks: sends the prompt directly.
For multi-step tasks: delivers prompts sequentially, continuing the session.
For adversarial tasks: uses an LLM to rephrase redirects naturally so the
agent doesn't see templated/mechanical instructions.
"""

from __future__ import annotations

from typing import Optional

from rich.console import Console

from sfbench.agents.base import AgentAdapter
from sfbench.models.task import Step, StepType, TaskConfig, TrialContext
from sfbench.models.transcript import NormalizedTranscript, TranscriptEntry

console = Console()


class Orchestrator:
    """Manages multi-step prompt delivery to agents."""

    def __init__(
        self,
        use_llm: bool = False,
        llm_model: str = "claude-sonnet-4-20250514",
    ):
        self.use_llm = use_llm
        self.llm_model = llm_model

    def run(
        self,
        config: TaskConfig,
        ctx: TrialContext,
        agent: AgentAdapter,
    ) -> NormalizedTranscript:
        """Execute all task steps against the agent, returning a full transcript."""
        steps = config.steps
        if not steps:
            steps = [Step(
                step_id=1,
                type=StepType.PROMPT,
                prompt=config.description or "No prompt defined",
            )]

        prompts = []
        for step in steps:
            if self.use_llm and step.type in (
                StepType.ADVERSARIAL,
                StepType.RED_HERRING,
                StepType.REDIRECT,
            ):
                prompt = self._rephrase_with_llm(step, config)
            else:
                prompt = step.prompt
            prompts.append(prompt)

        console.print(f"  [dim]Orchestrator: delivering {len(prompts)} step(s)[/dim]")
        transcript = agent.execute(config, ctx, prompts)

        return transcript

    def _rephrase_with_llm(self, step: Step, config: TaskConfig) -> str:
        """Use an LLM to rephrase adversarial/redirect prompts for natural delivery.

        Makes the prompt sound like a real stakeholder rather than a benchmark instruction.
        """
        try:
            import anthropic

            client = anthropic.Anthropic()

            system_prompt = (
                "You are a stakeholder in a data engineering team. You're chatting with an AI "
                "assistant that's helping with Snowflake tasks. Rephrase the following instruction "
                "so it sounds natural — like something a real person would say mid-conversation. "
                "Keep the core intent but make it conversational. Don't mention that you're "
                "testing or benchmarking anything."
            )

            context = f"Task context: {config.description}\nStep type: {step.type.value}"
            if step.subtype:
                context += f"\nSubtype: {step.subtype}"

            message = client.messages.create(
                model=self.llm_model,
                max_tokens=500,
                system=system_prompt,
                messages=[{
                    "role": "user",
                    "content": f"{context}\n\nOriginal instruction:\n{step.prompt}\n\n"
                               "Rephrase this naturally:",
                }],
            )

            rephrased = message.content[0].text
            console.print(f"  [dim]LLM rephrased step {step.step_id} ({step.type.value})[/dim]")
            return rephrased

        except Exception as e:
            console.print(f"  [yellow]LLM rephrase failed, using original: {e}[/yellow]")
            return step.prompt
