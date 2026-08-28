"""
The generic per-agent harness loop: observe -> decide -> act -> report.

The loop shape is identical regardless of execution kind (SERVER_RUN,
CLIENT_RUN, or a MIXED task whose steps interleave both) — only
`resolve_adapter` changes what "act" actually does. A regular agent's loop
is only ever handed `bus.publish` plus its own `steps` list; it has no
reference to any other agent's loop, adapter, or state, and no reference to
the EventBus object itself (see harness/bus.py, harness/orchestrator.py).
"""
from typing import List

from domain.orchestration import AgentEvent, AgentRuntimeKind, AgentStep, StepStatus, SystemMode
from harness.adapters.agentcore_adapter import ServerRunAdapter
from harness.adapters.client_handoff_adapter import ClientHandoffAdapter
from harness.adapters.demo_adapter import DemoAdapter
from harness.bus import EventBus
from harness.config import HarnessConfig
from harness import store


def resolve_adapter(execution_kind: AgentRuntimeKind, mode: SystemMode, bus: EventBus, config: HarnessConfig):
    """Single place mapping (execution_kind, mode) -> concrete AgentAdapter."""
    if mode == SystemMode.DEMO:
        return DemoAdapter()
    if execution_kind == AgentRuntimeKind.CLIENT_RUN:
        return ClientHandoffAdapter(bus)
    return ServerRunAdapter(config)


async def run_agent_loop(
    agent_id: str,
    task_id: str,
    session_id: str,
    steps: List[AgentStep],
    bus: EventBus,
    config: HarnessConfig,
) -> List[AgentStep]:
    store.register_steps(session_id, steps)

    for step in steps:
        # OBSERVE
        await bus.publish(
            AgentEvent(
                event_type="STEP_STARTED",
                source_agent_id=agent_id,
                session_id=session_id,
                payload={"step_id": step.id},
            )
        )

        # DECIDE
        adapter = resolve_adapter(step.execution_kind, config.mode, bus, config)

        # ACT
        result = adapter.start(step)
        step.status = StepStatus(result["status"])
        step.output_payload = result.get("output")

        if step.status == StepStatus.AWAITING_CALLBACK:
            # The callback handler (apps/api/main.py) mutates this same `step`
            # object (looked up by id from harness.store) before resolving the
            # future, so re-reading step.status/output_payload here is enough.
            await bus.wait_for(step.id)

        # REPORT
        await bus.publish(
            AgentEvent(
                event_type="STEP_COMPLETED" if step.status == StepStatus.COMPLETED else "STEP_FAILED",
                source_agent_id=agent_id,
                session_id=session_id,
                payload={"step_id": step.id, "output": step.output_payload},
            )
        )

        if step.status == StepStatus.FAILED:
            break

    return steps
