"""Data models for Agent Builder — shared across all platforms."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any


class InvolvementCode(str, Enum):
    OWNS = "OWNS"
    CONTRIBUTES = "CONTRIBUTES"
    CONSUMES = "CONSUMES"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


class SplitDecision(str, Enum):
    KEEP_AS_ONE = "KEEP_AS_ONE"
    SPLIT_INTO_SUBAGENTS = "SPLIT_INTO_SUBAGENTS"


@dataclass
class AgentRole:
    role_name: str
    primary_responsibility: str
    phase_scope: list[str] = field(default_factory=list)
    role_id: str = ""

    def __post_init__(self):
        if not self.role_id:
            self.role_id = self.role_name.lower().replace(" ", "_").replace("-", "_")


@dataclass
class ActivityClassification:
    activity_id: str
    activity_name: str
    classification: InvolvementCode
    rationale: str
    source_file: str = ""


@dataclass
class ExtractedField:
    field_name: str
    values: list[dict[str, Any]]
    source_activity: str
    citation: str


@dataclass
class SplitCriterion:
    name: str
    recommendation: str  # "SPLIT" or "KEEP"
    rationale: str


@dataclass
class SplitEvaluation:
    decision: SplitDecision
    rationale: str
    criteria: list[SplitCriterion] = field(default_factory=list)
    split_score: int = 0
    keep_score: int = 0
    proposed_subagents: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class SkillMapping:
    skill_id: str
    description: str
    layer: int  # 2=core, 3=conditional
    applicable_when: str
    required_context_fields: list[str] = field(default_factory=list)
    required_tools: list[str] = field(default_factory=list)
    is_existing: bool = False
    responsibilities_covered: list[str] = field(default_factory=list)


@dataclass
class AgentDesign:
    role: AgentRole
    classifications: list[ActivityClassification] = field(default_factory=list)
    split_evaluation: SplitEvaluation | None = None
    responsibilities: list[dict[str, Any]] = field(default_factory=list)
    inputs: list[dict[str, Any]] = field(default_factory=list)
    outputs: list[dict[str, Any]] = field(default_factory=list)
    decisions: list[dict[str, Any]] = field(default_factory=list)
    tools: list[dict[str, Any]] = field(default_factory=list)
    knowledge: list[dict[str, Any]] = field(default_factory=list)
    skills: list[SkillMapping] = field(default_factory=list)
    workflow_steps: list[dict[str, Any]] = field(default_factory=list)
    handoffs: list[dict[str, Any]] = field(default_factory=list)
    evaluation_metrics: list[dict[str, Any]] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    information_gaps: list[str] = field(default_factory=list)
    delivery_model_root: str = ""
    generated_date: str = ""

    def __post_init__(self):
        if not self.generated_date:
            self.generated_date = date.today().isoformat()

    @property
    def owns_activities(self) -> list[ActivityClassification]:
        return [c for c in self.classifications if c.classification == InvolvementCode.OWNS]

    @property
    def contributes_activities(self) -> list[ActivityClassification]:
        return [c for c in self.classifications if c.classification == InvolvementCode.CONTRIBUTES]
