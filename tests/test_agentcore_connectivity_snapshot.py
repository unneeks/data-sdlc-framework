"""Unit tests for apps/api/main.py::_agentcore_connectivity_snapshot(),
which drives the top-of-app status bar's real (not merely mode-based)
AgentCore reachability, using the same settings/test the AgentCore
Connection Tester page itself uses.
"""
import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from apps.api.main import _agentcore_connectivity_snapshot, harness_config
from domain.orchestration import SystemMode
from harness.connection_tester import ConnectionSettings


def test_demo_mode_still_runs_the_live_test(monkeypatch):
    """Connectivity is a fact about this machine's settings, not about
    whether the rest of the app is currently simulating invocations — the
    check always runs live, in DEMO mode too."""
    monkeypatch.setattr(harness_config, "mode", SystemMode.DEMO)
    monkeypatch.setattr("apps.api.main.load_settings", lambda: ConnectionSettings(region="ap-southeast-2", project="p"))
    monkeypatch.setattr("apps.api.main.run_connection_test", lambda settings: {
        "aws_identity": {"available": True},
        "agentcore": {"available": True, "harness_count": 3, "harness_arns": ["arn:aws:bedrock-agentcore:ap-southeast-2:1:harness/a"]},
    })

    snapshot = _agentcore_connectivity_snapshot()
    assert snapshot == {
        "checked": True, "reachable": True, "region": "ap-southeast-2", "project": "p",
        "reason": None, "harness_count": 3, "sample_harness_arn": "arn:aws:bedrock-agentcore:ap-southeast-2:1:harness/a",
    }


def test_real_mode_reachable_when_both_checks_succeed(monkeypatch):
    monkeypatch.setattr(harness_config, "mode", SystemMode.REAL)
    monkeypatch.setattr("apps.api.main.load_settings", lambda: ConnectionSettings(region="ap-southeast-2", project="p"))
    monkeypatch.setattr("apps.api.main.run_connection_test", lambda settings: {
        "aws_identity": {"available": True},
        "agentcore": {"available": True, "harness_count": 7, "harness_arns": ["arn:aws:bedrock-agentcore:ap-southeast-2:1:harness/x", "arn:...:y"]},
    })

    snapshot = _agentcore_connectivity_snapshot()
    assert snapshot["checked"] is True
    assert snapshot["reachable"] is True
    assert snapshot["reason"] is None
    assert snapshot["harness_count"] == 7
    assert snapshot["sample_harness_arn"] == "arn:aws:bedrock-agentcore:ap-southeast-2:1:harness/x"


def test_real_mode_unreachable_surfaces_aws_identity_reason(monkeypatch):
    monkeypatch.setattr(harness_config, "mode", SystemMode.REAL)
    monkeypatch.setattr("apps.api.main.load_settings", lambda: ConnectionSettings(region="ap-southeast-2", project="p"))
    monkeypatch.setattr("apps.api.main.run_connection_test", lambda settings: {
        "aws_identity": {"available": False, "reason": "InvalidClientTokenId"}, "agentcore": None,
    })

    snapshot = _agentcore_connectivity_snapshot()
    assert snapshot["checked"] is True
    assert snapshot["reachable"] is False
    assert snapshot["reason"] == "InvalidClientTokenId"
    assert snapshot["harness_count"] is None
    assert snapshot["sample_harness_arn"] is None


def test_real_mode_unreachable_surfaces_agentcore_reason_when_aws_identity_ok(monkeypatch):
    monkeypatch.setattr(harness_config, "mode", SystemMode.REAL)
    monkeypatch.setattr("apps.api.main.load_settings", lambda: ConnectionSettings(region="ap-southeast-2", project="p"))
    monkeypatch.setattr("apps.api.main.run_connection_test", lambda settings: {
        "aws_identity": {"available": True}, "agentcore": {"available": False, "reason": "AccessDeniedException"},
    })

    snapshot = _agentcore_connectivity_snapshot()
    assert snapshot["reachable"] is False
    assert snapshot["reason"] == "AccessDeniedException"


def test_real_mode_unreachable_surfaces_top_level_error(monkeypatch):
    monkeypatch.setattr(harness_config, "mode", SystemMode.REAL)
    monkeypatch.setattr("apps.api.main.load_settings", lambda: ConnectionSettings(region="ap-southeast-2", project="p"))
    monkeypatch.setattr("apps.api.main.run_connection_test", lambda settings: {
        "error": "failed to build AWS session: bad profile", "aws_identity": None, "agentcore": None,
    })

    snapshot = _agentcore_connectivity_snapshot()
    assert snapshot["reachable"] is False
    assert snapshot["reason"] == "failed to build AWS session: bad profile"
