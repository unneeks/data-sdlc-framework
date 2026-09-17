"""Unit test for agents/runner.py::AgentRunner._run_harness's region
resolution: it used to hardcode `region = "us-west-2"`, ignoring
agentcore_config.json entirely (more than any other AgentCore call site).
It must now read the deployed harness's own region via
harness.metrics.get_agentcore_runtime_info (matching harness/live_session.py's
existing pattern) and build its boto3 client through
harness.connection_tester.build_boto3_client so an explicit Connection
Tester override still applies.
"""
import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

import agents.runner as runner_module
from agents.runner import AgentRunner


def _make_runner() -> AgentRunner:
    runner = AgentRunner(str(root_dir))
    runner._harness_arns = {"test-agent": "arn:aws:bedrock-agentcore:ap-southeast-2:1:harness/test"}
    return runner


class _FakeHarnessClient:
    def invoke_harness(self, **kwargs):
        return {"stream": [{"messageStop": {"stopReason": "end_turn"}}]}


def test_run_harness_uses_deployed_region_not_hardcoded_literal(monkeypatch):
    captured = {}

    def fake_get_agentcore_runtime_info(agent_id):
        captured["agent_id_looked_up"] = agent_id
        return {"region": "ap-southeast-2"}

    def fake_build_boto3_client(service_name, default_region=None, **kwargs):
        captured["service_name"] = service_name
        captured["default_region"] = default_region
        return _FakeHarnessClient()

    monkeypatch.setattr("harness.metrics.get_agentcore_runtime_info", fake_get_agentcore_runtime_info)
    monkeypatch.setattr("harness.connection_tester.build_boto3_client", fake_build_boto3_client)

    runner = _make_runner()
    trace = {"session_id": "s1", "steps": []}
    config = {"bedrock_model_id": "test-model"}

    result = runner._run_harness("test-agent", config, task_input={}, trace=trace)

    assert captured["agent_id_looked_up"] == "test-agent"
    assert captured["service_name"] == "bedrock-agentcore"
    assert captured["default_region"] == "ap-southeast-2"  # from the deployed harness config, not a hardcoded literal
    assert result == {"raw_response": "", "agent_key": "test-agent"}


def test_run_harness_raises_when_no_harness_arn_configured():
    runner = _make_runner()
    runner._harness_arns = {}
    try:
        runner._run_harness("test-agent", {"bedrock_model_id": "m"}, task_input={}, trace={"session_id": "s1", "steps": []})
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "No harness ARN configured" in str(exc)
