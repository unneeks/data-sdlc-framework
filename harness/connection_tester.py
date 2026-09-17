"""AgentCore Connection Tester.

Validates that this machine's AWS session can reach both AWS in general
(STS) and Bedrock AgentCore specifically (a lightweight control-plane
list call), using settings resolved the same way the rest of this app
resolves configuration (env vars first, then a persisted override in
agentcore_config.json — see harness/repo_sync_config.py for the identical
pattern), with region/project defaulting from environment variables and
everything editable + re-testable from the UI.

Credential source, in priority order:
  1. `credentials_path` pointing at a JSON file (`{"aws_access_key_id",
     "aws_secret_access_key", "aws_session_token"}` or the PascalCase
     shape `aws sts assume-role`/an SSO cache file produces —
     `{"AccessKeyId", "SecretAccessKey", "SessionToken"}`) — read directly
     and passed to boto3 explicitly. Covers "the user token" living in a
     JSON credentials export rather than the standard INI file.
  2. `credentials_path` pointing at a standard INI-format AWS credentials
     file — passed to botocore as its `credentials_file` config variable
     (this is what makes the *path* configurable, not just AWS_PROFILE)
     rather than mutating this process's environment.
  3. Neither configured — boto3's own default chain takes over, which
     already covers AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY/
     AWS_SESSION_TOKEN env vars, AWS_PROFILE, and an IAM role. No
     credentials live in this module beyond what the user explicitly
     configures — same convention as harness/config.py.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_CONFIG_JSON_PATH = _PROJECT_ROOT / "agentcore_config.json"

_DEFAULT_REGION = "ap-southeast-2"
_DEFAULT_PROJECT = "data-sdlc-framework"
_DEFAULT_CREDENTIALS_PATH = "~/.aws/credentials"
_DEFAULT_PROFILE = "default"


@dataclass
class ConnectionSettings:
    credentials_path: str = _DEFAULT_CREDENTIALS_PATH
    profile: str = _DEFAULT_PROFILE
    region: str = _DEFAULT_REGION
    project: str = _DEFAULT_PROJECT

    def to_dict(self) -> dict:
        return asdict(self)


def _read_stored_settings() -> dict:
    if not _CONFIG_JSON_PATH.exists():
        return {}
    try:
        data = json.loads(_CONFIG_JSON_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return {}
    return data.get("connection_tester", {}) or {}


def load_settings() -> ConnectionSettings:
    """Resolve settings: a value the user explicitly saved via the UI wins;
    otherwise fall back to the environment variables the rest of this app
    already uses for region (AGENTCORE_AWS_REGION, matching
    harness/config.py) and a new AGENTCORE_PROJECT for project; finally a
    hardcoded default so the tester is always usable out of the box."""
    stored = _read_stored_settings()

    credentials_path = (
        stored.get("credentials_path")
        or os.getenv("AGENTCORE_CONNECTION_CREDENTIALS_PATH")
        or os.getenv("AWS_SHARED_CREDENTIALS_FILE")
        or _DEFAULT_CREDENTIALS_PATH
    )
    profile = (
        stored.get("profile")
        or os.getenv("AGENTCORE_CONNECTION_PROFILE")
        or os.getenv("AWS_PROFILE")
        or _DEFAULT_PROFILE
    )
    region = (
        stored.get("region")
        or os.getenv("AGENTCORE_AWS_REGION")
        or os.getenv("AWS_DEFAULT_REGION")
        or os.getenv("AWS_REGION")
        or _DEFAULT_REGION
    )
    project = stored.get("project") or os.getenv("AGENTCORE_PROJECT") or _DEFAULT_PROJECT

    return ConnectionSettings(credentials_path=credentials_path, profile=profile, region=region, project=project)


def save_settings(settings: ConnectionSettings) -> None:
    """Persist user-edited settings so they stick across reloads —
    mirrors agents/conventions/provisioner.py's save_convention_config,
    preserving whatever else already lives in agentcore_config.json."""
    existing: dict = {}
    if _CONFIG_JSON_PATH.exists():
        try:
            existing = json.loads(_CONFIG_JSON_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            existing = {}

    existing["connection_tester"] = settings.to_dict()
    _CONFIG_JSON_PATH.write_text(json.dumps(existing, indent=2))


def _load_json_credentials(path: Path) -> Optional[Dict[str, str]]:
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None

    # Support both the AWS CLI's snake_case export shape and the
    # PascalCase shape returned by sts:AssumeRole / SSO cache files.
    access_key = data.get("aws_access_key_id") or data.get("AccessKeyId")
    secret_key = data.get("aws_secret_access_key") or data.get("SecretAccessKey")
    session_token = data.get("aws_session_token") or data.get("SessionToken")
    if not access_key or not secret_key:
        return None
    return {"access_key": access_key, "secret_key": secret_key, "session_token": session_token}


def build_session(settings: ConnectionSettings) -> Any:
    """Construct a boto3.Session honoring a configurable credentials path
    without mutating this process's environment variables."""
    import boto3

    path = Path(settings.credentials_path).expanduser() if settings.credentials_path else None

    if path and path.exists() and path.suffix.lower() == ".json":
        creds = _load_json_credentials(path)
        if creds is None:
            raise ValueError(f"could not find AWS credentials in JSON file: {path}")
        return boto3.Session(
            aws_access_key_id=creds["access_key"],
            aws_secret_access_key=creds["secret_key"],
            aws_session_token=creds.get("session_token"),
            region_name=settings.region or None,
        )

    if path and path.exists():
        import botocore.session

        core_session = botocore.session.Session(profile=settings.profile or None)
        core_session.set_config_variable("credentials_file", str(path))
        return boto3.Session(botocore_session=core_session, region_name=settings.region or None)

    return boto3.Session(profile_name=settings.profile or None, region_name=settings.region or None)


def _explicit_overrides() -> Dict[str, str]:
    """The tiers a human/env actually set explicitly — saved settings or a
    recognized env var — never the hardcoded-default tier below them.
    Empty means the tester has nothing explicit configured, so callers of
    build_boto3_client fall back to their own pre-existing default/
    credential behavior rather than silently adopting this module's
    hardcoded defaults (which, unlike this function, load_settings()
    always returns a concrete value for)."""
    stored = _read_stored_settings()

    credentials_path = (
        stored.get("credentials_path")
        or os.getenv("AGENTCORE_CONNECTION_CREDENTIALS_PATH")
        or os.getenv("AWS_SHARED_CREDENTIALS_FILE")
        or ""
    )
    profile = stored.get("profile") or os.getenv("AGENTCORE_CONNECTION_PROFILE") or os.getenv("AWS_PROFILE") or ""
    region = (
        stored.get("region")
        or os.getenv("AGENTCORE_AWS_REGION")
        or os.getenv("AWS_DEFAULT_REGION")
        or os.getenv("AWS_REGION")
        or ""
    )

    overrides: Dict[str, str] = {}
    if credentials_path:
        overrides["credentials_path"] = credentials_path
    if profile:
        overrides["profile"] = profile
    if region:
        overrides["region"] = region
    return overrides


def build_boto3_client(service_name: str, default_region: Optional[str] = None, **client_kwargs) -> Any:
    """Build a boto3 client for `service_name`, honoring an EXPLICIT
    Connection Tester override (saved via the UI, or a recognized env var)
    for credentials/profile/region. Falls back to `default_region` and
    boto3's untouched default credential chain when nothing explicit is
    configured, so a call site that adopts this helper sees zero behavior
    change on a machine that has never touched the Connection Tester —
    this is what elevates the tester's settings from a page-local
    diagnostic into the app's single connectivity source of truth without
    silently changing anyone's defaults."""
    overrides = _explicit_overrides()
    region = overrides.get("region") or default_region

    if "credentials_path" in overrides or "profile" in overrides:
        settings = ConnectionSettings(
            credentials_path=overrides.get("credentials_path", ""),
            profile=overrides.get("profile", ""),
            region=region or _DEFAULT_REGION,
        )
        session = build_session(settings)
        return session.client(service_name, **client_kwargs)

    import boto3

    if region:
        return boto3.client(service_name, region_name=region, **client_kwargs)
    return boto3.client(service_name, **client_kwargs)


def run_connection_test(settings: ConnectionSettings) -> dict:
    """Run the full connectivity check: build the session, verify AWS
    identity via STS, then verify AgentCore reachability specifically via
    a lightweight ListHarnesses call. Every failure mode returns a
    structured result rather than raising — this is surfaced directly in
    the UI, not logged and swallowed."""
    result: Dict[str, Any] = {"settings": settings.to_dict(), "aws_identity": None, "agentcore": None}

    try:
        session = build_session(settings)
    except Exception as exc:  # noqa: BLE001 - report, never crash the test endpoint
        result["error"] = f"failed to build AWS session: {exc}"
        return result

    try:
        identity = session.client("sts").get_caller_identity()
        result["aws_identity"] = {
            "available": True,
            "account": identity.get("Account"),
            "arn": identity.get("Arn"),
            "user_id": identity.get("UserId"),
        }
    except Exception as exc:  # noqa: BLE001
        result["aws_identity"] = {"available": False, "reason": str(exc)}
        return result  # no point testing AgentCore without valid AWS credentials

    try:
        control = session.client("bedrock-agentcore-control", region_name=settings.region or None)
        response = control.list_harnesses(maxResults=10)
        result["agentcore"] = {
            "available": True,
            "harness_count": len(response.get("harnesses", [])),
            "region": settings.region,
        }
    except Exception as exc:  # noqa: BLE001
        result["agentcore"] = {"available": False, "reason": str(exc)}

    return result
