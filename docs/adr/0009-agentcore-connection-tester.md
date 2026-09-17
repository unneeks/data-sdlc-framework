# ADR 0009: AgentCore Connection Tester

## Status

Accepted

## Date

2026-09-17

## Context

Every AgentCore-calling code path in this app (`harness/live_session.py`, `agents/runner.py`, `harness/metrics.py`) already assumes boto3's default credential chain and env-var-driven region resolution (`harness/config.py`). When that assumption doesn't hold on a given machine — wrong profile, a credentials file the app isn't looking at, no AgentCore permissions on an otherwise-valid AWS identity — the failure surfaces deep inside whatever feature happened to be running, with no dedicated place to diagnose it. A standalone connection tester was requested: pick up the user's own local AWS session (a credentials file, a profile, or plain env vars), let the region/project be overridden from what environment variables already default to, surface the result in the UI, and let the operator edit and re-test.

## Decision

`harness/connection_tester.py` resolves `ConnectionSettings` (`credentials_path`, `profile`, `region`, `project`) with the same precedence `harness/repo_sync_config.py` already established: a value the user explicitly saved via the UI wins, otherwise fall back to environment variables (`AGENTCORE_AWS_REGION`/`AWS_DEFAULT_REGION`/`AWS_REGION` for region — the exact chain `harness/config.py` already uses — and a new `AGENTCORE_PROJECT` for project), otherwise a hardcoded default. Saved settings persist to `agentcore_config.json["connection_tester"]`, the same file `agents/conventions/provisioner.py` already writes `knowledgebase`/`repo_sync` sections into.

**The credentials path supports two shapes, covering "a JSON file and/or environment variables":**
1. A JSON file (`{"aws_access_key_id", "aws_secret_access_key", "aws_session_token"}` or the PascalCase shape an `sts:AssumeRole` response or an SSO cache file produces) — parsed directly and passed to `boto3.Session(...)` explicitly.
2. A standard INI-format AWS credentials file at a **configurable path** — passed to botocore as its `credentials_file` config variable (`botocore.session.Session().set_config_variable("credentials_file", path)`) rather than mutating this process's `AWS_SHARED_CREDENTIALS_FILE` environment variable, which would leak into every other AWS call this process makes for the lifetime of the request.
3. Neither configured — boto3's own default chain takes over unmodified, which already covers plain environment variables and an IAM role.

**Two-stage test, not just "can I reach AWS":** `run_connection_test` first calls `sts.get_caller_identity()` (proves the AWS session itself is valid) and, only if that succeeds, calls `bedrock-agentcore-control.list_harnesses()` (proves the identity specifically has AgentCore access in the configured region — the thing this app actually needs, not just generic AWS reachability). The two results are reported separately so "your AWS credentials are fine but this identity has no AgentCore permission" is distinguishable from "your credentials don't work at all."

## Consequences

### Positive

- Diagnosing a broken AgentCore connection no longer requires triggering some other feature and reading a stack trace out of its logs.
- The credentials-path mechanism is reusable: any future feature needing a non-default AWS session can call `build_session(settings)` directly.
- Every failure mode (bad profile, missing file, malformed JSON, valid AWS identity but no AgentCore access) returns a structured result rather than raising, verified in `tests/test_connection_tester.py` against faked `boto3.Session`/client objects — never against the real, git-tracked `agentcore_config.json` this repo ships with sample harness config in (tests always monkeypatch the config path to a `tmp_path` file).

### Negative

- `project` has no AWS-side meaning — it's a free-form label persisted for display/context, matching `harness/repo_sync_config.py::project_key`'s existing precedent. It doesn't scope or filter anything AgentCore-side.
- Settings persist into the same `agentcore_config.json` every other convention/provisioning write already targets, so a "Save" from this UI is a mutation of that shared file, not an isolated per-feature setting.
- No secrets are ever written back to that file — only the path to where they live, a profile name, a region, and a label — but the path itself is still operator-supplied free text with no validation beyond "does this file exist."

## Alternatives Considered

- **Only supporting the standard AWS credentials/config file format** — rejected: the request explicitly named a JSON credential source (matching an `aws sts assume-role` export or an SSO cache file) as a first-class case, not just the INI format.
- **Mutating `AWS_SHARED_CREDENTIALS_FILE` in `os.environ` for the duration of the test** — rejected in favor of `botocore.session.Session().set_config_variable(...)`, which scopes the override to one session object instead of this process's entire environment.
