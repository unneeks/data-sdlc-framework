"""Unit tests for harness/metrics.py's get_aws_identity/get_agentcore_metrics,
specifically that they now build their boto3 clients through
harness.connection_tester.build_boto3_client() rather than a bare
boto3.client() call, while preserving today's caller-supplied region as
the fallback when nothing explicit is configured.
"""
import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

import harness.connection_tester as connection_tester
from harness.metrics import get_agentcore_metrics, get_aws_identity


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


def test_get_aws_identity_uses_caller_region_when_unconfigured(monkeypatch, tmp_path):
    _use_tmp_config(monkeypatch, tmp_path)
    _clear_all_recognized_env_vars(monkeypatch)

    class FakeStsClient:
        def get_caller_identity(self):
            return {"Account": "1", "Arn": "arn", "UserId": "u"}

    captured = {}

    def fake_build_boto3_client(service_name, default_region=None, **kwargs):
        captured["service_name"] = service_name
        captured["default_region"] = default_region
        return FakeStsClient()

    monkeypatch.setattr(connection_tester, "build_boto3_client", fake_build_boto3_client)

    result = get_aws_identity(region="eu-north-1")
    assert result["available"] is True
    assert result["region"] == "eu-north-1"
    assert captured == {"service_name": "sts", "default_region": "eu-north-1"}


def test_get_aws_identity_honors_explicit_saved_region_override(monkeypatch, tmp_path):
    config_path = _use_tmp_config(monkeypatch, tmp_path)
    config_path.write_text('{"connection_tester": {"region": "ap-south-1"}}')
    _clear_all_recognized_env_vars(monkeypatch)

    captured = {}
    monkeypatch.setattr("boto3.client", lambda service_name, **kwargs: captured.update({"service_name": service_name, **kwargs}))

    get_aws_identity(region="eu-north-1")
    assert captured["region_name"] == "ap-south-1"


def test_get_aws_identity_fails_soft_on_error(monkeypatch, tmp_path):
    _use_tmp_config(monkeypatch, tmp_path)

    def boom(*args, **kwargs):
        raise RuntimeError("NoCredentialsError")

    monkeypatch.setattr(connection_tester, "build_boto3_client", boom)

    result = get_aws_identity()
    assert result["available"] is False
    assert "NoCredentialsError" in result["reason"]


def test_get_agentcore_metrics_uses_caller_region_when_unconfigured(monkeypatch, tmp_path):
    _use_tmp_config(monkeypatch, tmp_path)
    _clear_all_recognized_env_vars(monkeypatch)

    captured = {}

    class FakeCloudwatchClient:
        def list_metrics(self, **kwargs):
            return {"Metrics": []}

        def get_metric_data(self, **kwargs):
            return {"MetricDataResults": []}

    def fake_build_boto3_client(service_name, default_region=None, **kwargs):
        captured["service_name"] = service_name
        captured["default_region"] = default_region
        return FakeCloudwatchClient()

    monkeypatch.setattr(connection_tester, "build_boto3_client", fake_build_boto3_client)

    result = get_agentcore_metrics("runtime-1", region="eu-north-1")
    assert result["available"] is True
    assert captured == {"service_name": "cloudwatch", "default_region": "eu-north-1"}


def test_get_agentcore_metrics_no_runtime_configured_is_unavailable_without_touching_boto3(monkeypatch, tmp_path):
    _use_tmp_config(monkeypatch, tmp_path)

    def boom(*args, **kwargs):
        raise AssertionError("build_boto3_client should not be called with no runtime id")

    monkeypatch.setattr(connection_tester, "build_boto3_client", boom)

    result = get_agentcore_metrics(None)
    assert result == {"available": False, "reason": "no AgentCore runtime configured for this agent"}
