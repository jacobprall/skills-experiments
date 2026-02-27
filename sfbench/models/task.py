"""Pydantic models for task.yaml configuration."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field


class StepType(str, Enum):
    PROMPT = "prompt"
    REDIRECT = "redirect"
    ADVERSARIAL = "adversarial"
    RED_HERRING = "red_herring"
    CONSTRAINT = "constraint"
    CHECKPOINT = "checkpoint"


class Difficulty(str, Enum):
    SIMPLE = "simple"
    STANDARD = "standard"
    COMPLEX = "complex"
    ADVERSARIAL = "adversarial"


class CheckType(str, Enum):
    SQL = "sql"
    SQL_AS_ROLE = "sql_as_role"


class AssertionType(str, Enum):
    SQL = "sql"
    SQL_AS_ROLE = "sql_as_role"
    BEHAVIORAL = "behavioral"


class Step(BaseModel):
    step_id: int
    type: StepType
    subtype: Optional[str] = None
    trigger: str = "after_previous"
    prompt: str


class Requirement(BaseModel):
    id: str
    description: str
    check: CheckType
    query: str
    pass_if: str
    role: Optional[str] = None


class Assertion(BaseModel):
    id: str
    category: str
    type: AssertionType
    points: int | float
    query: Optional[str] = None
    check: Optional[str] = None
    rubric: Optional[str] = None
    description: str = ""


class Trap(BaseModel):
    id: str
    description: str
    detection_method: str
    points: int | float


class SolutionConfig(BaseModel):
    scripts: list[str] = Field(default_factory=list)


class SetupConfig(BaseModel):
    scripts: list[str] = Field(default_factory=list)


class TeardownConfig(BaseModel):
    scripts: list[str] = Field(default_factory=list)


class SolutionSeed(BaseModel):
    table_name: str
    target_schema: Optional[str] = None
    include_columns: list[str] = Field(default_factory=list)
    exclude_columns: list[str] = Field(default_factory=list)


class TaskConfig(BaseModel):
    task_id: str
    status: str = "ready"
    difficulty: str = "simple"
    category: str = ""
    domains: list[str] = Field(default_factory=list)
    description: str = ""
    author_name: str = ""
    author_email: str = ""
    tags: list[str] = Field(default_factory=list)
    environment: str = ""
    setup: SetupConfig = Field(default_factory=SetupConfig)
    traps: list[Trap] = Field(default_factory=list)
    steps: list[Step] = Field(default_factory=list)
    requirements: list[Requirement] = Field(default_factory=list)
    assertions: list[Assertion] = Field(default_factory=list)
    solution: SolutionConfig = Field(default_factory=SolutionConfig)
    solution_seeds: list[SolutionSeed] = Field(default_factory=list)
    teardown: TeardownConfig = Field(default_factory=TeardownConfig)

    # Set after loading — the directory containing the task.yaml
    task_dir: Optional[Path] = None


class TrialContext(BaseModel):
    """Template variables resolved per trial."""

    database: str
    raw_schema: str
    staging_schema: str
    analytics_schema: str
    governance_schema: str
    admin_role: str
    restricted_role: str
    warehouse: str
    connection: str = "default"


def resolve_template(text: str, ctx: TrialContext) -> str:
    """Replace {variable} placeholders in text with trial context values."""
    replacements = {
        "{database}": ctx.database,
        "{raw_schema}": ctx.raw_schema,
        "{staging_schema}": ctx.staging_schema,
        "{analytics_schema}": ctx.analytics_schema,
        "{governance_schema}": ctx.governance_schema,
        "{admin_role}": ctx.admin_role,
        "{restricted_role}": ctx.restricted_role,
        "{warehouse}": ctx.warehouse,
    }
    result = text
    for placeholder, value in replacements.items():
        result = result.replace(placeholder, value)
    return result


def resolve_task_config(config: TaskConfig, ctx: TrialContext) -> TaskConfig:
    """Return a copy of the config with all template variables resolved."""
    data = config.model_dump()

    def _resolve_dict(d: dict) -> dict:
        resolved = {}
        for k, v in d.items():
            if isinstance(v, str):
                resolved[k] = resolve_template(v, ctx)
            elif isinstance(v, dict):
                resolved[k] = _resolve_dict(v)
            elif isinstance(v, list):
                resolved[k] = _resolve_list(v)
            else:
                resolved[k] = v
        return resolved

    def _resolve_list(lst: list) -> list:
        resolved = []
        for item in lst:
            if isinstance(item, str):
                resolved.append(resolve_template(item, ctx))
            elif isinstance(item, dict):
                resolved.append(_resolve_dict(item))
            elif isinstance(item, list):
                resolved.append(_resolve_list(item))
            else:
                resolved.append(item)
        return resolved

    resolved_data = _resolve_dict(data)
    resolved = TaskConfig(**resolved_data)
    resolved.task_dir = config.task_dir
    return resolved


def load_task_config(task_dir: Path) -> TaskConfig:
    """Load a single task.yaml from a directory."""
    yaml_path = task_dir / "task.yaml"
    if not yaml_path.exists():
        raise FileNotFoundError(f"No task.yaml in {task_dir}")
    with open(yaml_path) as f:
        data = yaml.safe_load(f)
    config = TaskConfig(**data)
    config.task_dir = task_dir
    return config


def load_task_configs(
    tasks_dir: Path,
    task_ids: list[str],
    difficulty: str | None = None,
    domain: str | None = None,
) -> list[TaskConfig]:
    """Load task configs matching the given IDs, with optional filters."""
    if not tasks_dir.exists():
        return []

    all_dirs = sorted(d for d in tasks_dir.iterdir() if d.is_dir() and (d / "task.yaml").exists())
    configs: list[TaskConfig] = []

    for d in all_dirs:
        try:
            config = load_task_config(d)
        except Exception:
            continue

        if config.status != "ready":
            continue

        if "all" not in task_ids and config.task_id not in task_ids:
            continue

        if difficulty and config.difficulty != difficulty:
            continue

        if domain and domain not in config.domains:
            continue

        configs.append(config)

    return configs
