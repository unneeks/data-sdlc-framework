"""Unit tests for the Live Agent Orchestrator: DEMO scripted flow, the
client-tool-call pause/resume bridge (built on the same EventBus
wait_for/resolve_callback primitive as harness/loop.py's CLIENT_RUN steps),
the GitHub Copilot backend, and graceful AWS metrics degradation.
"""
import asyncio
import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from domain.orchestration import AgentBackend, ClientToolCallStatus
from harness.bus import EventBus
from harness.client_tools import CLIENT_TOOL_NAMES, dispatch_client_tool
from harness.live_session import LiveAgentSession


class _StubAgentRunner:
    """Minimal stand-in for agents.runner.AgentRunner — only execute_tool is used."""

    def execute_tool(self, tool_name, tool_input, task_input=None):
        return {"tool": tool_name, "input": tool_input, "result": "stubbed"}


def test_demo_session_pauses_for_client_tool_then_resumes():
    """The scripted DEMO flow must request a client tool call, publish it as
    a strongly-typed CLIENT_TOOL_CALL_REQUESTED event, block on it via
    bus.wait_for, and only reach SESSION_COMPLETED after it is resolved."""
    bus = EventBus()
    session = LiveAgentSession(
        session_id="s1", agent_id="impact-analysis-agent", backend=AgentBackend.AGENTCORE,
        live=False, bus=bus, agent_runner=_StubAgentRunner(), agent_config={},
    )

    async def scenario():
        run_task = asyncio.create_task(session.run("assess a schema change"))
        await asyncio.sleep(0.2)

        assert session.status == "RUNNING"
        pending = session.pending_calls()
        assert len(pending) == 1
        assert pending[0]["tool_name"] in CLIENT_TOOL_NAMES
        assert pending[0]["status"] == ClientToolCallStatus.PENDING.value

        result = await session.resolve_client_tool_call(pending[0]["call_id"], approve=True)
        assert result.status == ClientToolCallStatus.COMPLETED

        await run_task
        assert session.status == "COMPLETED"
        assert session.final_text and "impact-analysis-agent" in session.final_text
        assert session.pending_calls() == []

        event_types = [e["event_type"] for e in session.events]
        assert "CLIENT_TOOL_CALL_REQUESTED" in event_types
        assert "CLIENT_TOOL_CALL_RESOLVED" in event_types
        assert event_types.index("CLIENT_TOOL_CALL_REQUESTED") < event_types.index("CLIENT_TOOL_CALL_RESOLVED")
        assert event_types[-1] == "SESSION_COMPLETED"

    asyncio.run(scenario())


def test_denying_a_client_tool_call_still_resumes_the_session():
    bus = EventBus()
    session = LiveAgentSession(
        session_id="s2", agent_id="impact-analysis-agent", backend=AgentBackend.AGENTCORE,
        live=False, bus=bus, agent_runner=_StubAgentRunner(), agent_config={},
    )

    async def scenario():
        run_task = asyncio.create_task(session.run("assess a schema change"))
        await asyncio.sleep(0.2)
        pending = session.pending_calls()
        result = await session.resolve_client_tool_call(pending[0]["call_id"], approve=False)
        assert result.status == ClientToolCallStatus.DENIED

        await run_task
        assert session.status == "COMPLETED"

    asyncio.run(scenario())


def test_resolving_unknown_call_id_raises():
    bus = EventBus()
    session = LiveAgentSession(
        session_id="s3", agent_id="a", backend=AgentBackend.AGENTCORE,
        live=False, bus=bus, agent_runner=_StubAgentRunner(), agent_config={},
    )

    async def scenario():
        try:
            await session.resolve_client_tool_call("does-not-exist", approve=True)
            assert False, "expected KeyError"
        except KeyError:
            pass

    asyncio.run(scenario())


def test_github_copilot_backend_completes_in_one_turn():
    bus = EventBus()

    class StubCopilot:
        def run_turn(self, agent_id, prompt):
            return {"status": "COMPLETED", "text": f"handled {agent_id}: {prompt}"}

    session = LiveAgentSession(
        session_id="s4", agent_id="impact-analysis-agent", backend=AgentBackend.GITHUB_COPILOT,
        live=True, bus=bus, agent_runner=_StubAgentRunner(), agent_config={}, github_backend=StubCopilot(),
    )
    asyncio.run(session.run("assess impact"))
    assert session.status == "COMPLETED"
    assert "handled impact-analysis-agent" in session.final_text


def test_agentcore_live_session_requires_harness_arn():
    bus = EventBus()
    session = LiveAgentSession(
        session_id="s5", agent_id="unconfigured-agent", backend=AgentBackend.AGENTCORE,
        live=True, bus=bus, agent_runner=_StubAgentRunner(), agent_config={},
    )
    asyncio.run(session.run("do something"))
    assert session.status == "FAILED"
    assert session.events[-1]["event_type"] == "SESSION_FAILED"


def test_client_tool_dispatch_confines_paths_to_repository_root():
    result = dispatch_client_tool("client_read_file", {"relative_path": "../../etc/passwd"})
    assert "error" in result


def test_client_tool_git_status_runs_locally():
    result = dispatch_client_tool("client_git_status", {})
    assert "returncode" in result


def test_metrics_module_degrades_gracefully_without_runtime():
    from harness.metrics import get_agentcore_metrics

    result = get_agentcore_metrics(None)
    assert result["available"] is False


if __name__ == "__main__":
    test_demo_session_pauses_for_client_tool_then_resumes()
    test_denying_a_client_tool_call_still_resumes_the_session()
    test_resolving_unknown_call_id_raises()
    test_github_copilot_backend_completes_in_one_turn()
    test_agentcore_live_session_requires_harness_arn()
    test_client_tool_dispatch_confines_paths_to_repository_root()
    test_client_tool_git_status_runs_locally()
    test_metrics_module_degrades_gracefully_without_runtime()
    print("All live orchestrator unit tests passed successfully!")
