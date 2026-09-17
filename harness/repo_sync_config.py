"""Configuration for the S3-bridged code/document sync feature.

No credentials live here, same convention as harness/config.py — AWS
credentials are left entirely to boto3's standard resolution chain.

Resolution order for the bucket name:
  1. AGENTCORE_REPO_SYNC_BUCKET env var
  2. agentcore_config.json["repo_sync"]["bucket_name"]
  3. Fall back to the already-provisioned knowledgebase bucket
     (agents.conventions.provisioner.find_existing_kb_bucket()), reused
     under this module's own prefixes — works out of the box with zero
     extra provisioning, since the harness execution role's S3 policy is
     already scoped to that bucket's ARN.

A bucket resolved from step 3 is not persisted back to agentcore_config.json
here — RepoSyncConfig is re-evaluated at process start, and the KB bucket
lookup itself is already cheap and cached-friendly (agents/conventions/
provisioner.py checks the config file before hitting S3).
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


class RepoSyncConfig:
    def __init__(self) -> None:
        self.region = (
            os.getenv("AGENTCORE_REPO_SYNC_REGION")
            or os.getenv("AGENTCORE_AWS_REGION")
            or "us-west-2"
        )
        self.bucket_name = os.getenv("AGENTCORE_REPO_SYNC_BUCKET", "")
        self.code_prefix = os.getenv("AGENTCORE_REPO_SYNC_CODE_PREFIX", "repo-sync/code")
        self.events_prefix = os.getenv("AGENTCORE_REPO_SYNC_EVENTS_PREFIX", "repo-sync/events")
        self.docs_prefix = os.getenv("AGENTCORE_REPO_SYNC_DOCS_PREFIX", "repo-sync/docs")
        self.local_docs_dir = os.getenv(
            "AGENTCORE_REPO_SYNC_LOCAL_DOCS_DIR", ".agentcore/synced-documents"
        )
        # A remotely-deployed orchestrator has no local checkout of "the
        # developer's real repo" to apply CODE_PUSHED_TO_S3 into — same
        # assumption harness/client_tools.py already makes for
        # client_git_status/client_git_diff. Set to "false" there so the
        # poller keeps running (for /api/repo-sync/status visibility)
        # without attempting a git fetch into a repo that isn't present.
        self.apply_code_locally = os.getenv("AGENTCORE_REPO_SYNC_APPLY_LOCALLY", "true").lower() != "false"
        self.project_key = os.getenv("AGENTCORE_REPO_SYNC_PROJECT_KEY", "data-sdlc-framework")

        if not self.bucket_name:
            self.bucket_name = self._load_bucket_from_config_json() or ""
        if not self.bucket_name:
            self.bucket_name = self._fallback_to_kb_bucket() or ""

    @property
    def configured(self) -> bool:
        return bool(self.bucket_name)

    def _load_bucket_from_config_json(self) -> Optional[str]:
        config_path = _PROJECT_ROOT / "agentcore_config.json"
        if not config_path.exists():
            return None
        try:
            data = json.loads(config_path.read_text())
        except (json.JSONDecodeError, OSError):
            return None
        return (data.get("repo_sync") or {}).get("bucket_name") or None

    def _fallback_to_kb_bucket(self) -> Optional[str]:
        try:
            from agents.conventions.provisioner import find_existing_kb_bucket

            kb = find_existing_kb_bucket(region=self.region, project_root=_PROJECT_ROOT)
            if kb and kb.get("bucket_name"):
                logger.info(
                    "repo_sync: no bucket configured, reusing knowledgebase bucket %s "
                    "under prefixes %s/%s/%s",
                    kb["bucket_name"], self.code_prefix, self.events_prefix, self.docs_prefix,
                )
                return kb["bucket_name"]
        except Exception as exc:  # noqa: BLE001 - fallback is best-effort, never fatal at import time
            logger.warning("repo_sync: knowledgebase bucket fallback failed: %s", exc)
        return None


# Module-level singleton, matching harness/config.py's harness_config pattern.
repo_sync_config = RepoSyncConfig()
