"""Unit tests for apps/api/live_routes.py::list_live_agents()'s AgentCore
harness listing, which is built ONLY from a live list_harnesses() call —
never from agentcore_config.json's locally cached snapshot. A cached
ARN/region can silently claim a harness exists (or exists in a region)
when that's no longer true, so an unreachable AWS means an empty
AgentCore list, not a stale guess.
"""
import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

import agents.harness_agents.registry as registry
import harness.connection_tester as connection_tester
from apps.api import live_routes
from harness import metrics as agentcore_metrics


def test_lists_only_harnesses_confirmed_by_the_live_call(monkeypatch):
    monkeypatch.setattr(registry, "list_agents", lambda: [
        {"key": "test-agent", "name": "Test Agent", "mission": "does things", "has_harness": True},
    ])
    monkeypatch.setattr(registry, "get_agent_config", lambda agent_key: {"bedrock_model_id": "us.anthropic.claude-opus-4-6-v1"})
    monkeypatch.setattr(agentcore_metrics, "get_agentcore_runtime_info", lambda agent_id: {
        "harness_arn": "arn:aws:bedrock-agentcore:us-west-2:1:harness/CACHED-STALE",
        "harness_id": "h1", "region": "us-west-2", "status": "READY",
    })
    monkeypatch.setattr(connection_tester, "list_harnesses", lambda settings: {
        "available": True,
        "harnesses": [{"harnessId": "h1", "harnessArn": "arn:aws:bedrock-agentcore:ap-southeast-2:1:harness/LIVE", "status": "READY"}],
    })
    monkeypatch.setattr(connection_tester, "load_settings", lambda: connection_tester.ConnectionSettings())
    monkeypatch.setattr(live_routes, "_load_json", lambda path: [])

    result = live_routes.list_live_agents()
    agentcore_agents = [a for a in result["agents"] if a["backend"] == "AGENTCORE"]
    assert len(agentcore_agents) == 1
    # The live ARN wins, never the cached/stale one, and it's in the
    # settings' region (ap-southeast-2), not the cached us-west-2.
    assert agentcore_agents[0]["harness_arn"] == "arn:aws:bedrock-agentcore:ap-southeast-2:1:harness/LIVE"
    assert agentcore_agents[0]["model_id"] == "us.anthropic.claude-opus-4-6-v1"


def test_live_status_wins_over_stale_cached_status(monkeypatch):
    monkeypatch.setattr(registry, "list_agents", lambda: [
        {"key": "test-agent", "name": "Test Agent", "mission": "does things", "has_harness": True},
    ])
    monkeypatch.setattr(registry, "get_agent_config", lambda agent_key: {"bedrock_model_id": "m"})
    monkeypatch.setattr(agentcore_metrics, "get_agentcore_runtime_info", lambda agent_id: {
        "harness_arn": "arn:...", "harness_id": "h1", "region": "us-west-2", "status": "READY",
    })
    monkeypatch.setattr(connection_tester, "list_harnesses", lambda settings: {
        "available": True, "harnesses": [{"harnessId": "h1", "harnessArn": "arn:live", "status": "STOPPED"}],
    })
    monkeypatch.setattr(connection_tester, "load_settings", lambda: connection_tester.ConnectionSettings())
    monkeypatch.setattr(live_routes, "_load_json", lambda path: [])

    result = live_routes.list_live_agents()
    agentcore_agents = [a for a in result["agents"] if a["backend"] == "AGENTCORE"]
    assert agentcore_agents[0]["harness_status"] == "STOPPED"
    assert agentcore_agents[0]["live_ready"] is False


def test_no_agentcore_harnesses_listed_when_aws_unreachable(monkeypatch):
    """An empty list is the honest answer — never fall back to a locally
    cached snapshot that might no longer be true."""
    monkeypatch.setattr(registry, "list_agents", lambda: [
        {"key": "test-agent", "name": "Test Agent", "mission": "does things", "has_harness": True},
    ])
    monkeypatch.setattr(connection_tester, "list_harnesses", lambda settings: {
        "available": False, "reason": "Unable to locate credentials", "harnesses": [],
    })
    monkeypatch.setattr(connection_tester, "load_settings", lambda: connection_tester.ConnectionSettings())
    monkeypatch.setattr(live_routes, "_load_json", lambda path: [])

    result = live_routes.list_live_agents()
    assert [a for a in result["agents"] if a["backend"] == "AGENTCORE"] == []


def test_a_live_harness_with_no_local_agent_key_is_excluded(monkeypatch):
    """A harness AWS knows about but this app has no registered agent_key
    for isn't invocable from this UI, so it's left out too."""
    monkeypatch.setattr(registry, "list_agents", lambda: [])
    monkeypatch.setattr(connection_tester, "list_harnesses", lambda settings: {
        "available": True, "harnesses": [{"harnessId": "orphan-harness", "harnessArn": "arn:x", "status": "READY"}],
    })
    monkeypatch.setattr(connection_tester, "load_settings", lambda: connection_tester.ConnectionSettings())
    monkeypatch.setattr(live_routes, "_load_json", lambda path: [])

    result = live_routes.list_live_agents()
    assert [a for a in result["agents"] if a["backend"] == "AGENTCORE"] == []


def test_agents_without_a_harness_are_excluded(monkeypatch):
    monkeypatch.setattr(registry, "list_agents", lambda: [
        {"key": "candidate-agent", "name": "Candidate", "mission": "not yet provisioned", "has_harness": False},
    ])
    monkeypatch.setattr(connection_tester, "list_harnesses", lambda settings: {"available": True, "harnesses": []})
    monkeypatch.setattr(connection_tester, "load_settings", lambda: connection_tester.ConnectionSettings())
    monkeypatch.setattr(live_routes, "_load_json", lambda path: [])

    result = live_routes.list_live_agents()
    assert [a for a in result["agents"] if a["backend"] == "AGENTCORE"] == []
