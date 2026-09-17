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


def test_demo_mode_reports_unchecked(monkeypatch):
    monkeypatch.setattr(harness_config, "mode", SystemMode.DEMO)
    monkeypatch.setattr("apps.api.main.load_settings", lambda: ConnectionSettings(region="ap-southeast-2", project="p"))

    def boom(settings):
        raise AssertionError("run_connection_test should not run in DEMO mode")

    monkeypatch.setattr("apps.api.main.run_connection_test", boom)

    snapshot = _agentcore_connectivity_snapshot()
    assert snapshot == {"checked": False, "reachable": None, "region": "ap-southeast-2", "project": "p", "reason": None}


def test_real_mode_reachable_when_both_checks_succeed(monkeypatch):
    monkeypatch.setattr(harness_config, "mode", SystemMode.REAL)
    monkeypatch.setattr("apps.api.main.load_settings", lambda: ConnectionSettings(region="ap-southeast-2", project="p"))
    monkeypatch.setattr("apps.api.main.run_connection_test", lambda settings: {
        "aws_identity": {"available": True}, "agentcore": {"available": True},
    })

    snapshot = _agentcore_connectivity_snapshot()
    assert snapshot["checked"] is True
    assert snapshot["reachable"] is True
    assert snapshot["reason"] is None


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
