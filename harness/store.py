"""
In-memory step/session store for v1 — no DB exists in this app today, so
this mirrors that: a plain module-level dict, reset on process restart.
"""
from typing import Dict, List

from domain.orchestration import AgentStep

_steps_by_id: Dict[str, AgentStep] = {}
_steps_by_session: Dict[str, List[AgentStep]] = {}


def register_steps(session_id: str, steps: List[AgentStep]) -> None:
    _steps_by_session.setdefault(session_id, [])
    for step in steps:
        _steps_by_id[step.id] = step
        _steps_by_session[session_id].append(step)


def get_step(step_id: str) -> AgentStep:
    return _steps_by_id.get(step_id)


def get_session_steps(session_id: str) -> List[AgentStep]:
    return _steps_by_session.get(session_id, [])
