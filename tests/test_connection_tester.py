"""Unit tests for harness/connection_tester.py.

_CONFIG_JSON_PATH is always monkeypatched to a tmp_path file — never the
real project's agentcore_config.json, which is a real, git-tracked file
in this repo with actual (workshop) harness config in it.
"""
import json
import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

import harness.connection_tester as connection_tester
from harness.connection_tester import ConnectionSettings, build_session, load_settings, run_connection_test, save_settings


def _use_tmp_config(monkeypatch, tmp_path, existing: dict | None = None):
    config_path = tmp_path / "agentcore_config.json"
    if existing is not None:
        config_path.write_text(json.dumps(existing))
    monkeypatch.setattr(connection_tester, "_CONFIG_JSON_PATH", config_path)
    return config_path


def test_load_settings_defaults_from_env_vars(monkeypatch, tmp_path):
    _use_tmp_config(monkeypatch, tmp_path)
    monkeypatch.setenv("AGENTCORE_AWS_REGION", "eu-west-1")
    monkeypatch.setenv("AGENTCORE_PROJECT", "my-project")
    monkeypatch.setenv("AWS_PROFILE", "my-profile")
    monkeypatch.delenv("AGENTCORE_CONNECTION_CREDENTIALS_PATH", raising=False)
    monkeypatch.delenv("AWS_SHARED_CREDENTIALS_FILE", raising=False)

    settings = load_settings()
    assert settings.region == "eu-west-1"
    assert settings.project == "my-project"
    assert settings.profile == "my-profile"
    assert settings.credentials_path == ""


def test_load_settings_falls_back_to_hardcoded_defaults(monkeypatch, tmp_path):
    _use_tmp_config(monkeypatch, tmp_path)
    for var in ["AGENTCORE_AWS_REGION", "AWS_DEFAULT_REGION", "AWS_REGION", "AGENTCORE_PROJECT", "AWS_PROFILE"]:
        monkeypatch.delenv(var, raising=False)

    settings = load_settings()
    assert settings.region == "us-west-2"
    assert settings.project == "data-sdlc-framework"
    assert settings.profile == ""


def test_saved_settings_take_priority_over_env_vars(monkeypatch, tmp_path):
    _use_tmp_config(monkeypatch, tmp_path)
    monkeypatch.setenv("AGENTCORE_AWS_REGION", "eu-west-1")

    save_settings(ConnectionSettings(credentials_path="/tmp/creds.json", profile="saved-profile", region="ap-south-1", project="saved-project"))

    settings = load_settings()
    assert settings.region == "ap-south-1"  # saved value wins over the env var
    assert settings.profile == "saved-profile"
    assert settings.project == "saved-project"
    assert settings.credentials_path == "/tmp/creds.json"


def test_save_settings_preserves_other_config_keys(monkeypatch, tmp_path):
    config_path = _use_tmp_config(monkeypatch, tmp_path, existing={"account_id": "123", "harnesses": {"a": {}}})

    save_settings(ConnectionSettings(region="us-east-1"))

    on_disk = json.loads(config_path.read_text())
    assert on_disk["account_id"] == "123"
    assert on_disk["harnesses"] == {"a": {}}
    assert on_disk["connection_tester"]["region"] == "us-east-1"


def test_build_session_from_json_credentials_file(tmp_path, monkeypatch):
    creds_file = tmp_path / "creds.json"
    creds_file.write_text(json.dumps({
        "aws_access_key_id": "AKIA_TEST", "aws_secret_access_key": "secret", "aws_session_token": "token",
    }))

    captured = {}

    class FakeSession:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr("boto3.Session", FakeSession)

    build_session(ConnectionSettings(credentials_path=str(creds_file), region="us-west-2"))

    assert captured["aws_access_key_id"] == "AKIA_TEST"
    assert captured["aws_secret_access_key"] == "secret"
    assert captured["aws_session_token"] == "token"
    assert captured["region_name"] == "us-west-2"


def test_build_session_from_pascal_case_json_credentials(tmp_path, monkeypatch):
    creds_file = tmp_path / "creds.json"
    creds_file.write_text(json.dumps({"AccessKeyId": "AKIA2", "SecretAccessKey": "s2", "SessionToken": "t2"}))

    captured = {}
    monkeypatch.setattr("boto3.Session", lambda **kwargs: captured.update(kwargs))

    build_session(ConnectionSettings(credentials_path=str(creds_file)))
    assert captured["aws_access_key_id"] == "AKIA2"


def test_build_session_raises_on_json_file_missing_credentials(tmp_path):
    creds_file = tmp_path / "creds.json"
    creds_file.write_text(json.dumps({"not_a_credential_field": "x"}))

    try:
        build_session(ConnectionSettings(credentials_path=str(creds_file)))
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "credentials" in str(exc)


def test_build_session_falls_back_to_default_chain_when_no_path_configured(monkeypatch):
    captured = {}
    monkeypatch.setattr("boto3.Session", lambda **kwargs: captured.update(kwargs) or object())

    build_session(ConnectionSettings(credentials_path="", profile="myprofile", region="us-east-1"))
    assert captured == {"profile_name": "myprofile", "region_name": "us-east-1"}


def test_connection_happy_path(monkeypatch):
    class FakeClient:
        def __init__(self, service_name):
            self.service_name = service_name

        def get_caller_identity(self):
            return {"Account": "123456789012", "Arn": "arn:aws:iam::123456789012:user/dev", "UserId": "AID123"}

        def list_harnesses(self, maxResults=10):
            return {"harnesses": [{"id": "h1"}, {"id": "h2"}]}

    class FakeSession:
        def client(self, service_name, region_name=None):
            return FakeClient(service_name)

    monkeypatch.setattr(connection_tester, "build_session", lambda settings: FakeSession())

    result = run_connection_test(ConnectionSettings(region="us-west-2", project="p"))
    assert result["aws_identity"]["available"] is True
    assert result["aws_identity"]["account"] == "123456789012"
    assert result["agentcore"]["available"] is True
    assert result["agentcore"]["harness_count"] == 2


def test_connection_reports_aws_identity_failure_and_skips_agentcore(monkeypatch):
    class FakeClient:
        def get_caller_identity(self):
            raise RuntimeError("InvalidClientTokenId")

    class FakeSession:
        def client(self, service_name, region_name=None):
            return FakeClient()

    monkeypatch.setattr(connection_tester, "build_session", lambda settings: FakeSession())

    result = run_connection_test(ConnectionSettings())
    assert result["aws_identity"]["available"] is False
    assert "InvalidClientTokenId" in result["aws_identity"]["reason"]
    assert result["agentcore"] is None  # never attempted


def test_connection_reports_agentcore_failure_separately_from_valid_aws_identity(monkeypatch):
    class FakeStsClient:
        def get_caller_identity(self):
            return {"Account": "1", "Arn": "arn", "UserId": "u"}

    class FakeAgentCoreClient:
        def list_harnesses(self, maxResults=10):
            raise RuntimeError("AccessDeniedException")

    class FakeSession:
        def client(self, service_name, region_name=None):
            return FakeStsClient() if service_name == "sts" else FakeAgentCoreClient()

    monkeypatch.setattr(connection_tester, "build_session", lambda settings: FakeSession())

    result = run_connection_test(ConnectionSettings())
    assert result["aws_identity"]["available"] is True
    assert result["agentcore"]["available"] is False
    assert "AccessDeniedException" in result["agentcore"]["reason"]


def test_connection_reports_session_build_failure(monkeypatch):
    def boom(settings):
        raise RuntimeError("bad profile")

    monkeypatch.setattr(connection_tester, "build_session", boom)

    result = run_connection_test(ConnectionSettings())
    assert "error" in result
    assert "bad profile" in result["error"]


if __name__ == "__main__":
    print("Run with pytest — this suite relies on monkeypatch fixtures.")
