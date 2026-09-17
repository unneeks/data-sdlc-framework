"""Orchestrator-side handler for CODE_PUSHED_TO_S3 — imports the incoming
change into the developer's real local repo as a new local branch, never
touching the working tree or the index.

The mechanism, not just convention, is what makes this safe: `git fetch
<path> HEAD:refs/heads/<branch>` only ever writes to .git/refs and the
object database. It cannot touch the working tree or staged changes even
if it wanted to — there is no code path in `git fetch` that does that.
"""
from __future__ import annotations

import io
import logging
import os
import subprocess
import tarfile
import tempfile
import time
from pathlib import Path
from typing import Any

from domain.events import SdlcEventEnvelope

logger = logging.getLogger(__name__)

_GIT_TIMEOUT_S = 60


def _run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, timeout=_GIT_TIMEOUT_S,
    )


def _extraction_dir_from_tarball(tarball_bytes: bytes) -> Path:
    extract_dir = Path(tempfile.mkdtemp(prefix="agentcore-apply-"))
    with tarfile.open(fileobj=io.BytesIO(tarball_bytes), mode="r:gz") as tf:
        tf.extractall(extract_dir, filter="data")  # py3.12+ safe-extraction filter
    return extract_dir


# Fixed, content-independent identity/timestamp so that _commit_extraction
# is a pure function of tree content: identical tarball bytes always
# produce the identical commit sha. That determinism is what makes
# reprocessing the same CODE_PUSHED_TO_S3 event (e.g. after a crash between
# a handler succeeding and the poller's cursor write persisting) a true
# git-recognized no-op fetch instead of a harmless-but-redundant new commit
# that `git fetch` would otherwise see as an unrelated non-fast-forward.
_DETERMINISTIC_COMMIT_ENV = {
    "GIT_AUTHOR_NAME": "agentcore-repo-sync", "GIT_AUTHOR_EMAIL": "repo-sync@agentcore.local",
    "GIT_AUTHOR_DATE": "2000-01-01T00:00:00Z",
    "GIT_COMMITTER_NAME": "agentcore-repo-sync", "GIT_COMMITTER_EMAIL": "repo-sync@agentcore.local",
    "GIT_COMMITTER_DATE": "2000-01-01T00:00:00Z",
}


def _commit_extraction(extract_dir: Path) -> None:
    _run_git(["init"], cwd=extract_dir)
    _run_git(["add", "-A"], cwd=extract_dir)
    tree_result = _run_git(["write-tree"], cwd=extract_dir)
    if tree_result.returncode != 0:
        raise RuntimeError(f"git write-tree failed in extraction dir: {tree_result.stderr}")
    tree_sha = tree_result.stdout.strip()

    commit_result = subprocess.run(
        ["git", "commit-tree", tree_sha, "-m", "apply import (content-addressed)"],
        cwd=extract_dir, capture_output=True, text=True, timeout=_GIT_TIMEOUT_S,
        env={**os.environ, **_DETERMINISTIC_COMMIT_ENV},
    )
    if commit_result.returncode != 0:
        raise RuntimeError(f"git commit-tree failed in extraction dir: {commit_result.stderr}")

    # Point HEAD's current branch at the deterministic commit so the caller
    # can fetch it via the ordinary `HEAD:refs/heads/<branch>` refspec.
    update_ref_result = _run_git(["update-ref", "HEAD", commit_result.stdout.strip()], cwd=extract_dir)
    if update_ref_result.returncode != 0:
        raise RuntimeError(f"git update-ref HEAD failed in extraction dir: {update_ref_result.stderr}")


def _local_branch_name(branch_name: str) -> str:
    return branch_name if branch_name.startswith("agentcore/") else f"agentcore/{branch_name}"


def apply_code_pushed_to_s3(envelope: SdlcEventEnvelope, target_repo_root: Path, s3_client: Any) -> dict:
    payload = envelope.payload  # CodePushedToS3Payload, validated by SdlcEventEnvelope on parse

    tarball_bytes = s3_client.get_object(Bucket=payload.bucket, Key=payload.tarball_key)["Body"].read()
    extract_dir = _extraction_dir_from_tarball(tarball_bytes)

    try:
        _commit_extraction(extract_dir)

        local_branch = _local_branch_name(payload.branch_name)
        result = _run_git(["fetch", str(extract_dir), f"HEAD:refs/heads/{local_branch}"], cwd=target_repo_root)

        if result.returncode != 0:
            # Non-fast-forward or any other fetch failure: never force. Retry
            # into a timestamped side branch so incoming work is never lost
            # or silently blocked; the developer reconciles manually.
            side_branch = f"{local_branch}-{int(time.time())}"
            logger.warning(
                "repo_sync: fast-forward fetch into %s failed (%s), retrying as %s",
                local_branch, result.stderr.strip(), side_branch,
            )
            retry = _run_git(["fetch", str(extract_dir), f"HEAD:refs/heads/{side_branch}"], cwd=target_repo_root)
            if retry.returncode != 0:
                raise RuntimeError(f"git fetch failed even into a fresh side branch: {retry.stderr}")
            return {"branch": side_branch, "forced_side_branch": True}

        return {"branch": local_branch, "forced_side_branch": False}
    finally:
        import shutil

        shutil.rmtree(extract_dir, ignore_errors=True)
