"""
Domain entities for the Agent Core Harness: execution kinds, system mode,
and the event/step shapes used to coordinate agent execution through the
Orchestrator.
"""
from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
import uuid
import datetime


class AgentRuntimeKind(str, Enum):
    SERVER_RUN = "SERVER_RUN"  # executes in AWS Bedrock AgentCore
    CLIENT_RUN = "CLIENT_RUN"  # delegated to the user's local Claude Code session
    MIXED = "MIXED"            # task-level tag; actual kind resolved per-step


class SystemMode(str, Enum):
    DEMO = "DEMO"
    REAL = "REAL"


class StepStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    AWAITING_CALLBACK = "AWAITING_CALLBACK"  # client-run only
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class AgentStep(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str
    task_id: str
    session_id: str
    execution_kind: AgentRuntimeKind
    input_payload: Dict[str, Any] = Field(default_factory=dict)
    output_payload: Optional[Dict[str, Any]] = None
    status: StepStatus = StepStatus.PENDING
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)


class AgentEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str  # STEP_STARTED, STEP_COMPLETED, STEP_FAILED, HANDOFF_REQUESTED, CLIENT_CALLBACK_RECEIVED
    source_agent_id: str
    session_id: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)


class Orchestrator(BaseModel):
    """Marker/config model identifying the single distinguished orchestrator agent."""
    id: str = "orchestrator-agent"
    name: str = "Orchestrator Agent"
    description: str = "Sole agent permitted to dispatch invocations to other agents."
