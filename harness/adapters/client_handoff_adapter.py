"""
CLIENT_RUN adapter: the harness never shells out to a `claude` CLI. A
client-run step is a handoff marker only — this adapter publishes a
HANDOFF_REQUESTED event and returns immediately. Resumption happens only
when the client posts back to POST /api/harness/callback.
"""
import asyncio
from typing import Any, Dict

from domain.orchestration import AgentEvent, AgentStep
from harness.bus import EventBus


class ClientHandoffAdapter:
    def __init__(self, bus: EventBus) -> None:
        self._bus = bus

    def start(self, step: AgentStep) -> Dict[str, Any]:
        event = AgentEvent(
            event_type="HANDOFF_REQUESTED",
            source_agent_id=step.agent_id,
            session_id=step.session_id,
            payload={
                "step_id": step.id,
                "agent_id": step.agent_id,
                "instructions": step.input_payload,
            },
        )
        # publish() is async; start() is a sync contract point, so fire-and-forget
        # onto the running loop rather than blocking on the publish.
        asyncio.ensure_future(self._bus.publish(event))
        return {"status": "AWAITING_CALLBACK", "output": None}
