"""Unit tests for harness/adapters/agentcore_adapter.py's ServerRunAdapter,
specifically that its lazily-built boto3 client goes through
harness.connection_tester.build_boto3_client() (the app-wide connectivity
settings source) rather than a bare boto3.client() call.
"""
import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

import harness.connection_tester as connection_tester
from harness.adapters.agentcore_adapter import ServerRunAdapter
from harness.config import HarnessConfig


def _use_tmp_config(monkeypatch, tmp_path):
    config_path = tmp_path / "agentcore_config.json"
    monkeypatch.setattr(connection_tester, "_CONFIG_JSON_PATH", config_path)
    return config_path


def _clear_all_recognized_env_vars(monkeypatch):
    for var in [
        "AGENTCORE_AWS_REGION", "AWS_DEFAULT_REGION", "AWS_REGION", "AGENTCORE_PROJECT",
        "AWS_PROFILE", "AGENTCORE_CONNECTION_PROFILE", "AGENTCORE_CONNECTION_CREDENTIALS_PATH",
        "AWS_SHARED_CREDENTIALS_FILE",
    ]:
        monkeypatch.delenv(var, raising=False)


def test_get_client_delegates_to_build_boto3_client_with_config_region(monkeypatch, tmp_path):
    _use_tmp_config(monkeypatch, tmp_path)
    _clear_all_recognized_env_vars(monkeypatch)

    captured = {}

    def fake_build_boto3_client(service_name, default_region=None, **kwargs):
        captured["service_name"] = service_name
        captured["default_region"] = default_region
        return object()

    monkeypatch.setattr(connection_tester, "build_boto3_client", fake_build_boto3_client)

    config = HarnessConfig()
    config.aws_region = "eu-west-2"
    adapter = ServerRunAdapter(config)
    adapter._get_client()

    assert captured == {"service_name": "bedrock-agentcore", "default_region": "eu-west-2"}


def test_get_client_honors_explicit_saved_region_override(monkeypatch, tmp_path):
    """An explicit Connection Tester override still wins even though the
    adapter's own HarnessConfig region is passed as default_region — proves
    the wiring, not just that the function got called."""
    config_path = _use_tmp_config(monkeypatch, tmp_path)
    config_path.write_text('{"connection_tester": {"region": "ap-south-1"}}')
    _clear_all_recognized_env_vars(monkeypatch)

    captured = {}
    monkeypatch.setattr("boto3.client", lambda service_name, **kwargs: captured.update({"service_name": service_name, **kwargs}))

    config = HarnessConfig()
    config.aws_region = "eu-west-2"
    adapter = ServerRunAdapter(config)
    adapter._get_client()

    assert captured["region_name"] == "ap-south-1"


def test_get_client_reuses_injected_client_without_calling_build_boto3_client(monkeypatch, tmp_path):
    _use_tmp_config(monkeypatch, tmp_path)

    def boom(*args, **kwargs):
        raise AssertionError("build_boto3_client should not be called when a client was injected")

    monkeypatch.setattr(connection_tester, "build_boto3_client", boom)

    sentinel = object()
    adapter = ServerRunAdapter(HarnessConfig(), client=sentinel)
    assert adapter._get_client() is sentinel
