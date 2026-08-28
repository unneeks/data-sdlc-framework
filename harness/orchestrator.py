"""
The Orchestrator's own harness loop.

Structurally different from a regular agent's `run_agent_loop`:
- No fixed step list — it reacts to the event stream for the app's lifetime.
- It is the only object constructed with the full EventBus (subscribe_all +
  dispatch), which is what makes "no agent talks to another agent" a fact
  about what references exist, not a convention agents are trusted to obey.
- It performs no domain work itself; its only actions are dispatching new
  agent loops and recording what happened.
"""
import asyncio
from typing import Any, Dict, List

from domain.orchestration import AgentEvent, AgentStep
from harness.bus import EventBus
from harness.config import HarnessConfig
from harness.loop import run_agent_loop


class Orchestrator:
    def __init__(self, bus: EventBus, config: HarnessConfig) -> None:
        self._bus = bus
        self._config = config
        self.event_log: List[AgentEvent] = []

    def dispatch(self, agent_id: str, task_id: str, session_id: str, steps: List[AgentStep]) -> "asyncio.Task":
        """The only entry point that starts another agent's loop."""
        return asyncio.create_task(
            run_agent_loop(agent_id, task_id, session_id, steps, self._bus, self._config)
        )

    async def run(self) -> None:
        async for event in self._bus.subscribe_all():
            self.event_log.append(event)
