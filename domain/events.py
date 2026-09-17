"""The SDLC event envelope — the durable, cross-process message contract
between an AgentCore Harness agent and whichever orchestrator (web app
backend today, a CLI in future) is watching for it.

Kept separate from domain/orchestration.py::AgentEvent, which is an
in-process, loosely-typed (`payload: Dict[str, Any]`), ad hoc-string
`event_type` shape consumed by harness/bus.py's asyncio queues for turn-loop
visibility. This envelope has different concerns: it must be durably
JSON-serializable to S3, carry a schema version, use a closed and
extensible event-type enum instead of a free string, and validate a
strongly-typed payload per event type on read — none of which the
in-process AgentEvent needs. The two are unrelated on purpose; do not merge
them.

One envelope shape for every event type (per docs/adr/0008), with only
`payload` varying by `event_type`. New event types are additive — never
remove or repurpose an existing SDLCEventType value once agents have been
told about it via .agentcore/skills/.
"""
from __future__ import annotations

import datetime
import uuid
from enum import Enum
from typing import List, Union

from pydantic import BaseModel, Field


class SDLCEventType(str, Enum):
    CODE_PUSHED_TO_S3 = "CODE_PUSHED_TO_S3"
    DOCUMENT_PUBLISHED = "DOCUMENT_PUBLISHED"


class CodePushedToS3Payload(BaseModel):
    bucket: str
    code_prefix: str
    tarball_key: str
    branch_name: str
    commit_sha: str
    base_commit_sha: str
    session_id: str
    agent_id: str
    files_changed: int = 0


class DocumentDescriptor(BaseModel):
    document_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    s3_key: str
    bucket: str
    content_type: str = "text/markdown"
    description: str = ""
    size_bytes: int = 0


class DocumentPublishedPayload(BaseModel):
    session_id: str
    agent_id: str
    documents: List[DocumentDescriptor] = Field(min_length=1)


class SdlcEventEnvelope(BaseModel):
    """The one envelope shape written as a single S3 object per event."""

    schema_version: str = "1"
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: SDLCEventType
    project_key: str
    session_id: str
    agent_id: str
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    payload: Union[CodePushedToS3Payload, DocumentPublishedPayload]
