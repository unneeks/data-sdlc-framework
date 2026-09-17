"""Unit tests for apps/api/live_routes.py::list_live_agents()'s AgentCore
harness status, which now refreshes against a live list_harnesses() call
instead of trusting only the locally cached agentcore_config.json status
recorded at provisioning time.
"""
import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

import agents.harness_agents.registry as registry
import harness.connection_tester as connection_tester
from apps.api import live_routes
from harness import metrics as agentcore_metrics


def test_live_status_overrides_stale_cached_status(monkeypatch):
    """The locally cached status says READY (stale), but AWS's live list
    says the harness no longer exists / isn't ready — the live status
    must win."""
    monkeypatch.setattr(registry, "list_agents", lambda: [
        {"key": "test-agent", "name": "Test Agent", "mission": "does things", "has_harness": True},
    ])
    monkeypatch.setattr(registry, "get_agent_config", lambda agent_key: {"bedrock_model_id": "us.anthropic.claude-opus-4-6-v1"})
    monkeypatch.setattr(agentcore_metrics, "get_agentcore_runtime_info", lambda agent_id: {
        "harness_arn": "arn:aws:bedrock-agentcore:ap-southeast-2:1:harness/h1",
        "harness_id": "h1", "region": "ap-southeast-2", "status": "READY",
    })
    monkeypatch.setattr(connection_tester, "list_harnesses", lambda settings: {
        "available": True, "harnesses": [{"harnessId": "h1", "status": "STOPPED"}],
    })
    monkeypatch.setattr(connection_tester, "load_settings", lambda: connection_tester.ConnectionSettings())
    monkeypatch.setattr(live_routes, "_load_json", lambda path: [])

    result = live_routes.list_live_agents()
    agentcore_agents = [a for a in result["agents"] if a["backend"] == "AGENTCORE"]
    assert len(agentcore_agents) == 1
    assert agentcore_agents[0]["harness_status"] == "STOPPED"
    assert agentcore_agents[0]["live_ready"] is False
    assert agentcore_agents[0]["model_id"] == "us.anthropic.claude-opus-4-6-v1"
    assert agentcore_agents[0]["harness_arn"] == "arn:aws:bedrock-agentcore:ap-southeast-2:1:harness/h1"


def test_falls_back_to_cached_status_when_aws_unreachable(monkeypatch):
    monkeypatch.setattr(registry, "list_agents", lambda: [
        {"key": "test-agent", "name": "Test Agent", "mission": "does things", "has_harness": True},
    ])
    monkeypatch.setattr(registry, "get_agent_config", lambda agent_key: {"bedrock_model_id": "us.anthropic.claude-opus-4-6-v1"})
    monkeypatch.setattr(agentcore_metrics, "get_agentcore_runtime_info", lambda agent_id: {
        "harness_arn": "arn:aws:bedrock-agentcore:ap-southeast-2:1:harness/h1",
        "harness_id": "h1", "region": "ap-southeast-2", "status": "READY",
    })
    monkeypatch.setattr(connection_tester, "list_harnesses", lambda settings: {
        "available": False, "reason": "Unable to locate credentials", "harnesses": [],
    })
    monkeypatch.setattr(connection_tester, "load_settings", lambda: connection_tester.ConnectionSettings())
    monkeypatch.setattr(live_routes, "_load_json", lambda path: [])

    result = live_routes.list_live_agents()
    agentcore_agents = [a for a in result["agents"] if a["backend"] == "AGENTCORE"]
    assert agentcore_agents[0]["harness_status"] == "READY"  # falls back to the cached status
    assert agentcore_agents[0]["live_ready"] is True


def test_agents_without_a_harness_are_excluded(monkeypatch):
    monkeypatch.setattr(registry, "list_agents", lambda: [
        {"key": "candidate-agent", "name": "Candidate", "mission": "not yet provisioned", "has_harness": False},
    ])
    monkeypatch.setattr(connection_tester, "list_harnesses", lambda settings: {"available": True, "harnesses": []})
    monkeypatch.setattr(connection_tester, "load_settings", lambda: connection_tester.ConnectionSettings())
    monkeypatch.setattr(live_routes, "_load_json", lambda path: [])

    result = live_routes.list_live_agents()
    assert [a for a in result["agents"] if a["backend"] == "AGENTCORE"] == []
