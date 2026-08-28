"""
Unit tests for the Agent Core Harness: loop, event bus, execution-kind
adapters, orchestrator isolation, and the demo/real mode toggle.
"""
import asyncio
import sys
from pathlib import Path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from domain.orchestration import AgentRuntimeKind, AgentStep, StepStatus, SystemMode
from harness.bus import EventBus
from harness.config import HarnessConfig
from harness.loop import resolve_adapter, run_agent_loop


def test_demo_step_completes_without_network_call():
    step = AgentStep(agent_id="a1", task_id="t1", session_id="s1",
                      execution_kind=AgentRuntimeKind.SERVER_RUN)
    bus = EventBus()
    config = HarnessConfig()
    config.mode = SystemMode.DEMO
    result = asyncio.run(run_agent_loop("a1", "t1", "s1", [step], bus, config))
    assert result[0].status == StepStatus.COMPLETED


def test_client_run_step_awaits_callback():
    step = AgentStep(agent_id="a1", task_id="t1", session_id="s1",
                      execution_kind=AgentRuntimeKind.CLIENT_RUN)
    bus = EventBus()
    config = HarnessConfig()
    config.mode = SystemMode.REAL

    async def scenario():
        loop_task = asyncio.create_task(run_agent_loop("a1", "t1", "s1", [step], bus, config))
        # Give the loop a beat to reach AWAITING_CALLBACK before the callback fires.
        await asyncio.sleep(0.05)
        assert step.status == StepStatus.AWAITING_CALLBACK

        from domain.orchestration import AgentEvent
        step.status = StepStatus.COMPLETED
        step.output_payload = {"result": "done"}
        event = AgentEvent(event_type="CLIENT_CALLBACK_RECEIVED", source_agent_id="a1",
                            session_id="s1", payload={"step_id": step.id})
        resolved = await bus.resolve_callback(step.id, event)
        assert resolved is True

        await loop_task
        assert step.status == StepStatus.COMPLETED

    asyncio.run(scenario())


def test_orchestrator_is_sole_dispatcher():
    class PublishOnlyBusHandle:
        def __init__(self):
            self.published = []

        async def publish(self, event):
            self.published.append(event)

    handle = PublishOnlyBusHandle()
    assert not hasattr(handle, "dispatch")
    assert not hasattr(handle, "subscribe_all")


def test_mode_toggle_switches_adapter_class():
    bus = EventBus()
    config = HarnessConfig()

    config.mode = SystemMode.REAL
    real_adapter = resolve_adapter(AgentRuntimeKind.SERVER_RUN, config.mode, bus, config)
    assert real_adapter.__class__.__name__ == "ServerRunAdapter"

    config.mode = SystemMode.DEMO
    demo_adapter = resolve_adapter(AgentRuntimeKind.SERVER_RUN, config.mode, bus, config)
    assert demo_adapter.__class__.__name__ == "DemoAdapter"


def test_agentcore_adapter_boundary_with_stub_boto3():
    class FakeBedrockAgentCoreClient:
        def invoke_agent_runtime(self, **kwargs):
            assert "agentRuntimeArn" in kwargs and "runtimeSessionId" in kwargs
            return {"payload": b'{"result": "ok"}'}

    from harness.adapters.agentcore_adapter import ServerRunAdapter
    config = HarnessConfig()
    config.agent_runtime_arn = "arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/test"
    adapter = ServerRunAdapter(config, client=FakeBedrockAgentCoreClient())
    step = AgentStep(agent_id="a1", task_id="t1", session_id="s1",
                      execution_kind=AgentRuntimeKind.SERVER_RUN)
    result = adapter.start(step)
    assert result["status"] == "COMPLETED"
    assert result["output"] == {"result": "ok"}


if __name__ == "__main__":
    test_demo_step_completes_without_network_call()
    test_client_run_step_awaits_callback()
    test_orchestrator_is_sole_dispatcher()
    test_mode_toggle_switches_adapter_class()
    test_agentcore_adapter_boundary_with_stub_boto3()
    print("All harness unit tests passed successfully!")
