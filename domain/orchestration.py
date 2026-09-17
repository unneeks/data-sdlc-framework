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


class AgentBackend(str, Enum):
    """Which execution surface a live agent invocation reasons on top of.

    Both backends are driven by the same LiveAgentSession turn loop
    (harness/live_session.py) and the same client-tool bridge — this enum
    only selects which adapter performs the actual model turn.
    """
    AGENTCORE = "AGENTCORE"            # AWS Bedrock AgentCore Harness (cloud)
    GITHUB_COPILOT = "GITHUB_COPILOT"  # GitHub Copilot CLI agent


class ToolExecutionSite(str, Enum):
    """Where a tool the LLM asked to call actually runs."""
    SERVER = "SERVER"  # executed inline by the process talking to the harness
    CLIENT = "CLIENT"  # executed on the developer's local machine, out-of-band


class ClientToolCallStatus(str, Enum):
    PENDING = "PENDING"        # requested by the model, awaiting approval/execution
    APPROVED = "APPROVED"      # approved, execution in flight
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    DENIED = "DENIED"


class ClientToolCallRequest(BaseModel):
    """Strongly-typed envelope for 'the harness needs a client-side tool call'.

    This wraps the harness's native toolUse content block (name + input) in a
    validated model the moment it crosses the AgentCore boundary, so every
    consumer (EventBus, the polling API, the UI) works off one typed contract
    instead of a loosely-shaped dict.
    """
    call_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    turn: int
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    status: ClientToolCallStatus = ClientToolCallStatus.PENDING
    requested_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)


class ClientToolCallResult(BaseModel):
    """What the developer machine reports back after running the tool.

    Feeding this back to the harness (as a toolResult on the same
    runtimeSessionId) is what lets the model "resume from where it left off".
    """
    call_id: str
    status: ClientToolCallStatus
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    completed_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)


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
