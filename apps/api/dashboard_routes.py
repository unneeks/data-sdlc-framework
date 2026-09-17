"""API routes for the Project Dashboard workflow UI.

Same wiring convention as apps/api/live_routes.py: `configure()` is called
once from apps/api/main.py's startup handler with the shared EventBus and
the existing module-level `agent_runner`, so dashboard lanes execute
through the exact same tool dispatch / AgentCore invocation path as every
other agent run in this app.
"""
from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException

from harness.adapters.github_copilot_adapter import GithubCopilotBackend
from harness.bus import EventBus
from harness.project_dashboard import ProjectDashboardSession

router = APIRouter(prefix="/api/dashboard", tags=["project-dashboard"])

_root_dir = Path(__file__).resolve().parent.parent.parent

_bus: Optional[EventBus] = None
_agent_runner: Any = None
_github_backend: Optional[GithubCopilotBackend] = None
_sessions: Dict[str, ProjectDashboardSession] = {}


def configure(bus: EventBus, agent_runner: Any) -> None:
    global _bus, _agent_runner, _github_backend
    _bus = bus
    _agent_runner = agent_runner
    catalog_path = _root_dir / "marketplace" / "agents.json"
    catalog = json.loads(catalog_path.read_text()) if catalog_path.exists() else []
    _github_backend = GithubCopilotBackend(catalog if isinstance(catalog, list) else [])


@router.post("/start")
async def start_dashboard(payload: dict):
    if _bus is None or _agent_runner is None:
        raise HTTPException(status_code=503, detail="dashboard not initialized yet")

    live = bool(payload.get("live", False))
    title = payload.get("title", "Customer Payments Data Product")

    session_id = str(uuid.uuid4())
    session = ProjectDashboardSession(
        session_id=session_id, live=live, bus=_bus,
        agent_runner=_agent_runner, github_backend=_github_backend, title=title,
    )
    _sessions[session_id] = session
    asyncio.create_task(session.run())

    return {"session_id": session_id, "live": live}


def _get_session(session_id: str) -> ProjectDashboardSession:
    session = _sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="unknown session_id")
    return session


@router.get("/{session_id}/snapshot")
def snapshot(session_id: str):
    return _get_session(session_id).snapshot()


@router.post("/{session_id}/work-products/{lane_key}/{work_product_key}/review")
async def review_work_product(session_id: str, lane_key: str, work_product_key: str, payload: dict):
    session = _get_session(session_id)
    approve = bool(payload.get("approve", True))
    version = payload.get("version", "")
    resolved = await session.review(lane_key, work_product_key, approve=approve, version=version)
    if not resolved:
        raise HTTPException(status_code=409, detail="no pending review for this work product")
    return {"lane_key": lane_key, "work_product_key": work_product_key, "approved": approve}
