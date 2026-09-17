"""Code Sync skill — the three tools an AgentCore Harness agent uses to
read/write source code and publish documents when it has no direct network
access to source control, only to S3 (see docs/adr/0008).

Runs in the same process that already bridges every other harness tool
call today (agents/runner.py::AgentRunner._execute_tool_by_name) — not in
harness/client_tools.py, which is reserved for tools that run on the
*developer's* machine behind a human-approval bridge. These three run
wherever the tool-dispatch process itself runs (a developer's machine, or
a deployed backend without github.com egress), operating on an ephemeral
scratch git workspace populated from S3 rather than `git clone`.

Every function here catches its own errors and returns an {"error": ...}
dict rather than raising — a raised exception here would propagate up
through LiveAgentSession._handle_tool_use_turn uncaught and fail the whole
agent session over what should be a single recoverable tool-call failure
(see harness/live_session.py:224, which does not wrap execute_tool in a
try/except; harness/client_tools.py::dispatch_client_tool follows the same
catch-and-report convention for the same reason).
"""
from __future__ import annotations

import gzip
import io
import json
import logging
import re
import subprocess
import tarfile
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from domain.events import (
    CodePushedToS3Payload,
    DocumentDescriptor,
    DocumentPublishedPayload,
    SDLCEventType,
    SdlcEventEnvelope,
)
from harness.repo_sync_config import repo_sync_config
from harness.s3_event_log import build_event_key

logger = logging.getLogger(__name__)

_GIT_TIMEOUT_S = 60


@dataclass
class ScratchWorkspace:
    session_id: str
    path: Path
    branch_name: str
    base_commit_sha: str
    created_at: float = field(default_factory=time.time)


# Session-scoped, process-lifetime. Deliberately NOT AgentRunner._context —
# that dict belongs to one AgentRunner *instance*, which is shared across
# every concurrent LiveAgentSession (see apps/api/main.py's single
# module-level `agent_runner`); keying scratch workspaces there would let
# two concurrent sessions clobber each other's workspace path.
_SCRATCH_WORKSPACES: Dict[str, ScratchWorkspace] = {}

_s3_client_override: Any = None  # test seam — see _get_s3_client()


def _get_s3_client() -> Any:
    if _s3_client_override is not None:
        return _s3_client_override
    import boto3

    return boto3.client("s3", region_name=repo_sync_config.region)


def _require_bucket() -> str:
    if not repo_sync_config.configured:
        raise RuntimeError(
            "repo_sync bucket is not configured — set AGENTCORE_REPO_SYNC_BUCKET, "
            "agentcore_config.json['repo_sync']['bucket_name'], or provision a "
            "knowledgebase bucket to fall back to."
        )
    return repo_sync_config.bucket_name


def _run_git(args: List[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, timeout=_GIT_TIMEOUT_S,
    )


def _resolve_under_workspace(workspace_path: Path, relative_path: str) -> Path:
    candidate = (workspace_path / relative_path).resolve()
    if workspace_path.resolve() not in candidate.parents and candidate != workspace_path.resolve():
        raise ValueError(f"path escapes scratch workspace: {relative_path}")
    return candidate


def _default_branch_name(agent_id: str, session_id: str) -> str:
    return f"agentcore/{agent_id or 'session'}/{session_id[:8]}"


# ── sync_code_from_s3 ───────────────────────────────────────────────────

def sync_code_from_s3(
    session_id: str, agent_id: str = "", branch_hint: Optional[str] = None, force: bool = False,
) -> dict:
    """Fetch the current code baseline into a fresh scratch workspace and
    create a working branch. Idempotent per session unless force=True."""
    try:
        existing = _SCRATCH_WORKSPACES.get(session_id)
        if existing is not None and not force:
            return {
                "workspace_path": str(existing.path),
                "branch_name": existing.branch_name,
                "base_commit_sha": existing.base_commit_sha,
                "is_new_workspace": False,
            }

        bucket = _require_bucket()
        client = _get_s3_client()

        pointer_key = f"{repo_sync_config.code_prefix}/HEAD/pointer.json"
        if branch_hint:
            branch_pointer_key = f"{repo_sync_config.code_prefix}/branches/{branch_hint}/pointer.json"
            if _object_exists(client, bucket, branch_pointer_key):
                pointer_key = branch_pointer_key

        pointer = _read_json_object(client, bucket, pointer_key)
        if pointer is None:
            return {
                "error": (
                    f"no code baseline found at s3://{bucket}/{pointer_key} — run the "
                    "repo-sync bootstrap step (scripts/bootstrap_repo_sync.py) before the "
                    "first agent session."
                )
            }

        tarball_bytes = client.get_object(Bucket=bucket, Key=pointer["tarball_key"])["Body"].read()
        workspace_path = Path(tempfile.mkdtemp(prefix=f"agentcore-{session_id[:8]}-"))
        with tarfile.open(fileobj=io.BytesIO(tarball_bytes), mode="r:gz") as tf:
            tf.extractall(workspace_path, filter="data")

        _run_git(["init"], cwd=workspace_path)
        _run_git(["add", "-A"], cwd=workspace_path)
        commit_result = _run_git(["commit", "-m", f"baseline import {pointer['tarball_key']}"], cwd=workspace_path)
        if commit_result.returncode != 0 and "nothing to commit" not in commit_result.stdout:
            return {"error": f"failed to commit baseline: {commit_result.stderr}"}

        base_commit_sha = _run_git(["rev-parse", "HEAD"], cwd=workspace_path).stdout.strip()

        branch_name = branch_hint or _default_branch_name(agent_id, session_id)
        checkout_result = _run_git(["checkout", "-b", branch_name], cwd=workspace_path)
        if checkout_result.returncode != 0:
            return {"error": f"failed to create branch {branch_name}: {checkout_result.stderr}"}

        workspace = ScratchWorkspace(
            session_id=session_id, path=workspace_path, branch_name=branch_name, base_commit_sha=base_commit_sha,
        )
        _SCRATCH_WORKSPACES[session_id] = workspace

        return {
            "workspace_path": str(workspace_path),
            "branch_name": branch_name,
            "base_commit_sha": base_commit_sha,
            "is_new_workspace": True,
        }
    except Exception as exc:  # noqa: BLE001 - never raise across the tool boundary
        logger.exception("sync_code_from_s3 failed for session %s", session_id)
        return {"error": str(exc)}


# ── push_code_to_s3 ─────────────────────────────────────────────────────

def push_code_to_s3(
    session_id: str,
    files: Optional[List[dict]] = None,
    delete_files: Optional[List[str]] = None,
    commit_message: str = "Agent update",
) -> dict:
    """Apply file edits/deletes in the scratch workspace, commit, archive,
    upload to S3, and emit a CODE_PUSHED_TO_S3 event — in that order, so a
    failure at any step leaves nothing half-applied for a consumer to see."""
    try:
        workspace = _SCRATCH_WORKSPACES.get(session_id)
        if workspace is None:
            return {"error": "no scratch workspace for this session — call sync_code_from_s3 first"}

        for f in files or []:
            dest = _resolve_under_workspace(workspace.path, f["relative_path"])
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(f.get("content", ""))
        for rel_path in delete_files or []:
            dest = _resolve_under_workspace(workspace.path, rel_path)
            if dest.exists():
                dest.unlink()

        _run_git(["add", "-A"], cwd=workspace.path)
        status = _run_git(["status", "--porcelain"], cwd=workspace.path)
        if not status.stdout.strip():
            return {"no_changes": True, "branch_name": workspace.branch_name}

        commit_result = _run_git(["commit", "-m", commit_message], cwd=workspace.path)
        if commit_result.returncode != 0:
            return {"error": f"git commit failed: {commit_result.stderr}"}
        commit_sha = _run_git(["rev-parse", "HEAD"], cwd=workspace.path).stdout.strip()

        files_changed = len([line for line in status.stdout.splitlines() if line.strip()])

        bucket = _require_bucket()
        client = _get_s3_client()

        archive_result = subprocess.run(
            ["git", "archive", commit_sha], cwd=workspace.path, capture_output=True, timeout=_GIT_TIMEOUT_S,
        )
        if archive_result.returncode != 0:
            return {"error": f"git archive failed: {archive_result.stderr.decode(errors='replace')}"}
        tarball_bytes = gzip.compress(archive_result.stdout)

        code_prefix = repo_sync_config.code_prefix
        tarball_key = f"{code_prefix}/branches/{workspace.branch_name}/{commit_sha}.tar.gz"
        client.put_object(Bucket=bucket, Key=tarball_key, Body=tarball_bytes)

        pointer_key = f"{code_prefix}/branches/{workspace.branch_name}/pointer.json"
        client.put_object(
            Bucket=bucket, Key=pointer_key,
            Body=json.dumps({"commit_sha": commit_sha, "tarball_key": tarball_key, "updated_at": time.time()}).encode(),
        )

        payload = CodePushedToS3Payload(
            bucket=bucket, code_prefix=code_prefix, tarball_key=tarball_key,
            branch_name=workspace.branch_name, commit_sha=commit_sha,
            base_commit_sha=workspace.base_commit_sha, session_id=session_id,
            agent_id="", files_changed=files_changed,
        )
        event_key = _write_event(client, bucket, SDLCEventType.CODE_PUSHED_TO_S3, session_id, "", payload)

        return {
            "commit_sha": commit_sha, "branch_name": workspace.branch_name,
            "tarball_key": tarball_key, "event_key": event_key, "no_changes": False,
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("push_code_to_s3 failed for session %s", session_id)
        return {"error": str(exc)}


# ── publish_documents ───────────────────────────────────────────────────

def publish_documents(session_id: str, agent_id: str = "", documents: Optional[List[dict]] = None) -> dict:
    """Upload every document fully first; only then write one
    DOCUMENT_PUBLISHED event listing the ones that actually landed. If all
    fail, no event is written."""
    try:
        if not documents:
            return {"error": "documents must contain at least one entry"}

        bucket = _require_bucket()
        client = _get_s3_client()
        docs_prefix = repo_sync_config.docs_prefix

        uploaded: List[DocumentDescriptor] = []
        failed: List[dict] = []
        for doc in documents:
            try:
                name = doc["name"]
                content = doc.get("content", "")
                content_bytes = content.encode() if isinstance(content, str) else content
                descriptor = DocumentDescriptor(
                    name=name, s3_key="", bucket=bucket,
                    content_type=doc.get("content_type", "text/markdown"),
                    description=doc.get("description", ""), size_bytes=len(content_bytes),
                )
                s3_key = f"{docs_prefix}/{session_id}/{descriptor.document_id}/{_sanitize_name(name)}"
                client.put_object(Bucket=bucket, Key=s3_key, Body=content_bytes)
                descriptor.s3_key = s3_key
                uploaded.append(descriptor)
            except Exception as exc:  # noqa: BLE001 - one bad document must not sink the rest
                failed.append({"name": doc.get("name", "?"), "error": str(exc)})

        event_key = None
        if uploaded:
            payload = DocumentPublishedPayload(session_id=session_id, agent_id=agent_id, documents=uploaded)
            event_key = _write_event(client, bucket, SDLCEventType.DOCUMENT_PUBLISHED, session_id, agent_id, payload)

        return {
            "uploaded": [json.loads(d.model_dump_json()) for d in uploaded],
            "failed": failed, "event_key": event_key,
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("publish_documents failed for session %s", session_id)
        return {"error": str(exc)}


# ── shared helpers ───────────────────────────────────────────────────────

_UNSAFE_CHARS = re.compile(r"[^A-Za-z0-9_.\-]")


def _sanitize_name(name: str) -> str:
    return _UNSAFE_CHARS.sub("_", name) or "document"


def _object_exists(client: Any, bucket: str, key: str) -> bool:
    try:
        client.head_object(Bucket=bucket, Key=key)
        return True
    except Exception:
        return False


def _read_json_object(client: Any, bucket: str, key: str) -> Optional[dict]:
    try:
        body = client.get_object(Bucket=bucket, Key=key)["Body"].read()
        return json.loads(body)
    except Exception:
        return None


def _write_event(client: Any, bucket: str, event_type: SDLCEventType, session_id: str, agent_id: str, payload: Any) -> str:
    """Write the event object last, per the robustness rule: only ever
    called after the artifact(s) it references are already durable in S3."""
    envelope = SdlcEventEnvelope(
        event_type=event_type, project_key=repo_sync_config.project_key,
        session_id=session_id, agent_id=agent_id, payload=payload,
    )
    event_key = build_event_key(envelope.created_at, envelope.event_id, repo_sync_config.events_prefix)
    client.put_object(Bucket=bucket, Key=event_key, Body=envelope.model_dump_json().encode())
    return event_key
