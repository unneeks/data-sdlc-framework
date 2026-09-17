"""Domain models for the Project Dashboard workflow UI.

Separate from domain/orchestration.py's AgentStep/AgentEvent (the harness's
own execution primitives) because these model a coarser-grained concept:
a "work product" (a document/artifact an agent lane produces) moving
through a human review gate, not a single tool call or harness turn.
"""
from __future__ import annotations

import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class WorkProductStatus(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    AWAITING_REVIEW = "AWAITING_REVIEW"
    COMPLETED = "COMPLETED"


class LaneStatus(str, Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ChecklistItem(BaseModel):
    id: str
    text: str
    completed: bool = False
    verified_by: Optional[str] = None


class Comment(BaseModel):
    id: str
    task_id: str
    author: str
    author_type: str  # "agent", "human", "system"
    body: str
    timestamp: str
    thread_id: Optional[str] = None


class WorkProduct(BaseModel):
    key: str
    name: str
    phase: str
    status: WorkProductStatus = WorkProductStatus.NOT_STARTED
    version: str = ""
    review_gate: bool = False
    updated_at: Optional[str] = None
    requested_at: Optional[str] = None
    checklist: List[ChecklistItem] = Field(default_factory=list)
    owner: Optional[Dict[str, Optional[str]]] = None  # {agent_id?: str, human_role?: str}

    def touch(self) -> None:
        self.updated_at = datetime.datetime.utcnow().isoformat() + "Z"


class ProjectRecord(BaseModel):
    """A persisted project created at onboarding — the datastore backing the
    Project Dashboard's phases/lanes, replacing the single hardcoded template
    every dashboard session used to share (see harness/project_dashboard.py's
    DEFAULT_PHASES/DEFAULT_LANE_DEFINITIONS, which this seeds from)."""

    project_id: str
    title: str
    delivery_type_id: Optional[str] = None
    created_at: str
    phases: List[Dict[str, Any]]
    lanes: List[Dict[str, Any]]
