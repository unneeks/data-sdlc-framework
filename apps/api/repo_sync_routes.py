"""API routes for the S3-bridged code/document sync watcher (docs/adr/0008).

Wired the same way as apps/api/live_routes.py / dashboard_routes.py:
`configure()` is called once from apps/api/main.py's startup handler,
which starts one project-wide SdlcEventPoller — independent of any single
LiveAgentSession or dashboard lane — that applies incoming events to this
process's own local checkout.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException

from harness.code_sync_apply import apply_code_pushed_to_s3
from harness.document_sync_apply import apply_document_published
from harness.repo_sync_config import repo_sync_config
from harness.s3_event_log import SdlcEventPoller
from domain.events import SDLCEventType

router = APIRouter(prefix="/api/repo-sync", tags=["repo-sync"])

_poller: Optional[SdlcEventPoller] = None


def configure(target_repo_root: Path) -> Optional[asyncio.Task]:
    """Called once from apps/api/main.py's startup handler. Returns the
    background poll task (or None if no bucket is configured yet — the
    poller simply doesn't start rather than failing app startup)."""
    global _poller

    if not repo_sync_config.configured:
        return None

    import boto3

    s3_client = boto3.client("s3", region_name=repo_sync_config.region)

    handlers = {}
    if repo_sync_config.apply_code_locally:
        handlers[SDLCEventType.CODE_PUSHED_TO_S3] = lambda e: apply_code_pushed_to_s3(e, target_repo_root, s3_client)
        handlers[SDLCEventType.DOCUMENT_PUBLISHED] = lambda e: apply_document_published(
            e, target_repo_root / repo_sync_config.local_docs_dir, s3_client,
        )

    _poller = SdlcEventPoller(
        repo_sync_config,
        cursor_path=target_repo_root / ".git" / "agentcore" / "repo_sync_cursor.json",
        handlers=handlers,
    )
    return asyncio.create_task(_poller.run_forever())


@router.get("/status")
def get_status():
    if _poller is None:
        return {"configured": False, "reason": "no repo_sync bucket configured"}
    return _poller.status()


@router.get("/events")
def get_events(since: int = 0):
    if _poller is None:
        raise HTTPException(status_code=503, detail="repo-sync watcher not configured")
    return {"events": _poller.history[since:], "next_cursor": len(_poller.history)}
