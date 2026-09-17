"""Domain models for the Project Dashboard workflow UI.

Separate from domain/orchestration.py's AgentStep/AgentEvent (the harness's
own execution primitives) because these model a coarser-grained concept:
a "work product" (a document/artifact an agent lane produces) moving
through a human review gate, not a single tool call or harness turn.
"""
from __future__ import annotations

import datetime
from enum import Enum
from typing import Optional

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


class WorkProduct(BaseModel):
    key: str
    name: str
    phase: str
    status: WorkProductStatus = WorkProductStatus.NOT_STARTED
    version: str = ""
    review_gate: bool = False
    updated_at: Optional[str] = None
    requested_at: Optional[str] = None

    def touch(self) -> None:
        self.updated_at = datetime.datetime.utcnow().isoformat() + "Z"
