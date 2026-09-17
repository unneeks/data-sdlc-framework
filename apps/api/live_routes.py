"""API routes for the Agent Orchestrator workflow UI (Live / Demo modes).

Kept as its own router rather than growing apps/api/main.py further. Wiring
follows the same "construct dependencies at startup, hand them to this
module" pattern main.py already uses for `event_bus`/`orchestrator`
(see main.py's `start_harness()`): `configure()` is called once from
main.py's startup event with the shared EventBus and the existing
module-level `agent_runner` (agents/runner.py::AgentRunner), so live agent
runs execute tools through the exact same tool_registry.yaml dispatch path
as every other agent invocation in this app.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from domain.orchestration import AgentBackend
from harness import metrics as agentcore_metrics
from harness.adapters.github_copilot_adapter import GithubCopilotBackend
from harness.bus import EventBus
from harness.client_tools import CLIENT_TOOL_DEFINITIONS
from harness.live_session import LiveAgentSession

router = APIRouter(prefix="/api/live", tags=["live-orchestrator"])

_root_dir = Path(__file__).resolve().parent.parent.parent

_bus: Optional[EventBus] = None
_agent_runner: Any = None
_github_backend: Optional[GithubCopilotBackend] = None
_sessions: Dict[str, LiveAgentSession] = {}


def configure(bus: EventBus, agent_runner: Any) -> None:
    """Called once from apps/api/main.py's startup handler."""
    global _bus, _agent_runner, _github_backend
    _bus = bus
    _agent_runner = agent_runner
    catalog = _load_json("marketplace/agents.json")
    _github_backend = GithubCopilotBackend(catalog if isinstance(catalog, list) else [])


def _load_json(rel_path: str) -> Any:
    path = _root_dir / rel_path
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def _build_agentcore_agent_config(agent_id: str) -> Dict[str, Any]:
    config = _agent_runner.get_agent_config(agent_id) or {}
    runtime_info = agentcore_metrics.get_agentcore_runtime_info(agent_id)
    return {**config, **runtime_info}


@router.get("/agents")
def list_live_agents():
    """Every agent invocable from the Live Agent Orchestrator UI, tagged by
    backend. AgentCore harness status is refreshed against a live
    list_harnesses() call when AWS is reachable, so this reflects what's
    actually running right now rather than only the locally cached status
    agentcore_config.json last recorded at provisioning time; falls back
    to that cached status when AWS isn't reachable (e.g. no AWS access in
    this environment) — never a hard failure."""
    agentcore_agents = []
    try:
        from agents.harness_agents.registry import get_agent_config, list_agents as list_harness_agents
        from harness.connection_tester import list_harnesses, load_settings

        live = list_harnesses(load_settings())
        live_status_by_harness_id = {
            h.get("harnessId") or h.get("harness_id"): h.get("status", "UNKNOWN")
            for h in live["harnesses"]
            if h.get("harnessId") or h.get("harness_id")
        }

        for a in list_harness_agents():
            if not a.get("has_harness"):
                continue
            runtime_info = agentcore_metrics.get_agentcore_runtime_info(a["key"])
            status = live_status_by_harness_id.get(runtime_info["harness_id"], runtime_info["status"])
            # AWS's Harness resource carries no model config of its own
            # (create_harness only takes harnessName/executionRoleArn) —
            # the model is chosen per invocation, so "the harness's
            # configured model" is this app's own agent_configs.yaml/
            # .agentcore convention setting, not something list_harnesses
            # could ever return.
            agent_config = get_agent_config(a["key"]) or {}
            agentcore_agents.append({
                "id": a["key"],
                "name": a.get("name", a["key"]),
                "description": a.get("mission", ""),
                "backend": AgentBackend.AGENTCORE.value,
                "live_ready": status == "READY",
                "harness_status": status,
                "model_id": agent_config.get("bedrock_model_id", ""),
                "harness_arn": runtime_info.get("harness_arn", ""),
            })
    except Exception:
        pass

    copilot_agents = []
    catalog = _load_json("marketplace/agents.json")
    for a in catalog if isinstance(catalog, list) else []:
        copilot_agents.append({
            "id": a["id"],
            "name": a["name"],
            "description": a.get("description", ""),
            "backend": AgentBackend.GITHUB_COPILOT.value,
            "live_ready": True,
            "harness_status": "N/A",
        })

    return {"agents": agentcore_agents + copilot_agents}


@router.get("/tools/client")
def list_client_tools():
    """The tools advertised to every live agent as 'runs on the developer's
    machine, requires approval' — surfaced so the UI can show operators what
    an agent might ask to run locally before they grant a run."""
    return {
        "tools": [
            {"name": t["toolSpec"]["name"], "description": t["toolSpec"]["description"]}
            for t in CLIENT_TOOL_DEFINITIONS
        ]
    }


@router.get("/aws/identity")
def aws_identity(region: str = "us-west-2"):
    return agentcore_metrics.get_aws_identity(region=region)


@router.get("/metrics")
def live_metrics(agent_id: str, lookback_minutes: int = 60):
    runtime_info = agentcore_metrics.get_agentcore_runtime_info(agent_id)
    return agentcore_metrics.get_agentcore_metrics(
        runtime_info.get("harness_id") or None,
        region=runtime_info.get("region", "us-west-2"),
        lookback_minutes=lookback_minutes,
    )


@router.post("/session/start")
async def start_session(payload: dict):
    if _bus is None or _agent_runner is None:
        raise HTTPException(status_code=503, detail="live orchestrator not initialized yet")

    agent_id = payload.get("agent_id")
    prompt = payload.get("prompt", "")
    live = bool(payload.get("live", False))
    backend_raw = payload.get("backend", AgentBackend.AGENTCORE.value)
    if not agent_id:
        raise HTTPException(status_code=400, detail="agent_id is required")

    try:
        backend = AgentBackend(backend_raw)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"unknown backend: {backend_raw}")

    session_id = str(uuid.uuid4())
    agent_config = (
        _build_agentcore_agent_config(agent_id) if backend == AgentBackend.AGENTCORE else {}
    )

    session = LiveAgentSession(
        session_id=session_id, agent_id=agent_id, backend=backend, live=live,
        bus=_bus, agent_runner=_agent_runner, agent_config=agent_config,
        github_backend=_github_backend,
    )
    _sessions[session_id] = session

    import asyncio
    asyncio.create_task(session.run(prompt))

    return {"session_id": session_id, "agent_id": agent_id, "backend": backend.value, "live": live}


def _get_session(session_id: str) -> LiveAgentSession:
    session = _sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="unknown session_id")
    return session


@router.get("/session/{session_id}/poll")
def poll_session(session_id: str, since: int = 0):
    session = _get_session(session_id)
    return {
        "status": session.status,
        "events": session.events[since:],
        "next_cursor": len(session.events),
        "pending_calls": session.pending_calls(),
        "final_text": session.final_text,
    }


@router.post("/session/{session_id}/tool-calls/{call_id}/approve")
async def approve_tool_call(session_id: str, call_id: str):
    session = _get_session(session_id)
    try:
        result = await session.resolve_client_tool_call(call_id, approve=True)
    except KeyError as exc:
        return JSONResponse(status_code=409, content={"error": str(exc)})
    return json.loads(result.model_dump_json())


@router.post("/session/{session_id}/tool-calls/{call_id}/deny")
async def deny_tool_call(session_id: str, call_id: str):
    session = _get_session(session_id)
    try:
        result = await session.resolve_client_tool_call(call_id, approve=False)
    except KeyError as exc:
        return JSONResponse(status_code=409, content={"error": str(exc)})
    return json.loads(result.model_dump_json())
