"""Pydantic models for trial results."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, computed_field


class RequirementResult(BaseModel):
    id: str
    passed: bool
    description: str = ""
    actual_value: Optional[str] = None
    error: Optional[str] = None


class AssertionResult(BaseModel):
    id: str
    category: str
    type: str
    points_available: float
    points_earned: float
    passed: bool
    description: str = ""
    actual_value: Optional[str] = None
    error: Optional[str] = None


class TrapResult(BaseModel):
    id: str
    detected: bool
    points_available: float
    points_earned: float
    description: str = ""
    evidence: Optional[str] = None


class TrialResult(BaseModel):
    task_id: str
    agent: str
    plugin_set: str
    model: Optional[str] = None
    run_id: str = ""
    started_at: datetime = Field(default_factory=datetime.now)
    finished_at: Optional[datetime] = None

    requirement_results: list[RequirementResult] = Field(default_factory=list)
    assertion_results: list[AssertionResult] = Field(default_factory=list)
    trap_results: list[TrapResult] = Field(default_factory=list)

    transcript_path: Optional[str] = None
    error: Optional[str] = None

    @computed_field
    @property
    def requirements(self) -> dict[str, bool]:
        return {r.id: r.passed for r in self.requirement_results}

    @computed_field
    @property
    def passed(self) -> bool:
        if not self.requirement_results:
            return False
        return all(r.passed for r in self.requirement_results)

    @computed_field
    @property
    def total_points_available(self) -> float:
        pts = sum(a.points_available for a in self.assertion_results)
        pts += sum(t.points_available for t in self.trap_results)
        return pts

    @computed_field
    @property
    def total_points_earned(self) -> float:
        pts = sum(a.points_earned for a in self.assertion_results)
        pts += sum(t.points_earned for t in self.trap_results)
        return pts

    @computed_field
    @property
    def composite_pct(self) -> float:
        if self.total_points_available == 0:
            return 100.0 if self.passed else 0.0
        return (self.total_points_earned / self.total_points_available) * 100

    @computed_field
    @property
    def duration_seconds(self) -> float:
        if self.finished_at is None:
            return 0.0
        return (self.finished_at - self.started_at).total_seconds()
