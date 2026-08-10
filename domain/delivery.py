"""
Delivery Twin definitions for Delivery Types, Blueprints, Plans, Tasks, Gates, and Evidence.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class ChecklistItem(BaseModel):
    id: str
    description: str
    completed: bool = False
    verified_by: Optional[str] = None

class AcceptanceCriterion(BaseModel):
    id: str
    criterion: str
    met: bool = False
    evidence_id: Optional[str] = None

class DeliveryInput(BaseModel):
    name: str
    type: str
    required: bool = True

class DeliveryOutput(BaseModel):
    name: str
    type: str
    artifact_id: Optional[str] = None

class Evidence(BaseModel):
    id: str
    title: str
    category: str  # "git_diff", "data_profile", "lineage_diff", "test_report", "architecture_spec"
    source: str
    confidence: str = "CONFIRMED"  # OBSERVED, INFERRED, LIKELY, CONFIRMED
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class Approval(BaseModel):
    gate_id: str
    approver_role: str
    decision: str  # "APPROVED", "APPROVED_WITH_CONDITIONS", "REJECTED", "PENDING"
    reason: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class ApprovalGate(BaseModel):
    id: str
    name: str
    phase: str
    required_role: str
    status: str = "BLOCKED"  # PASSED, BLOCKED, PENDING
    required_evidence: List[str] = Field(default_factory=list)
    blocking_reasons: List[str] = Field(default_factory=list)

class DeliveryTask(BaseModel):
    id: str
    name: str
    phase: str
    sequence: int
    purpose: str
    inputs: List[DeliveryInput] = Field(default_factory=list)
    outputs: List[DeliveryOutput] = Field(default_factory=list)
    required_agents: List[str] = Field(default_factory=list)
    required_skills: List[str] = Field(default_factory=list)
    checklist: List[ChecklistItem] = Field(default_factory=list)
    acceptance_criteria: List[AcceptanceCriterion] = Field(default_factory=list)
    status: str = "NOT_STARTED"  # NOT_STARTED, IN_PROGRESS, COMPLETED, FAILED

class DeliveryPhase(BaseModel):
    id: str
    name: str
    sequence: int
    purpose: str
    tasks: List[DeliveryTask] = Field(default_factory=list)
    gates: List[ApprovalGate] = Field(default_factory=list)
    status: str = "NOT_STARTED"  # NOT_STARTED, IN_PROGRESS, COMPLETED

class DeliveryType(BaseModel):
    id: str
    name: str
    description: str
    business_purpose: str
    baseline_risk: str  # "HIGH", "MEDIUM", "LOW"
    phases_count: int
    tasks_count: int
    default_agents: List[str] = Field(default_factory=list)
    required_skills: List[str] = Field(default_factory=list)

class DeliveryBlueprint(BaseModel):
    id: str
    delivery_type_id: str
    version: str
    phases: List[DeliveryPhase] = Field(default_factory=list)
    risk_rules: List[str] = Field(default_factory=list)
    approval_rules: List[str] = Field(default_factory=list)

class DeliveryPlan(BaseModel):
    id: str
    name: str
    project_id: str
    primary_delivery_type: str
    secondary_delivery_types: List[str] = Field(default_factory=list)
    blueprint_id: str
    status: str = "IN_PROGRESS"
    phases: List[DeliveryPhase] = Field(default_factory=list)
    assigned_agents: List[str] = Field(default_factory=list)
    evidence_collected: List[Evidence] = Field(default_factory=list)
