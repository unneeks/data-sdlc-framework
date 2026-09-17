"""Orchestrator-side handler for DOCUMENT_PUBLISHED — downloads every
document referenced in the event to a local documents directory.

Idempotent by construction: re-downloading identical bytes over an
existing file is a no-op in effect. Path traversal is guarded the same
way harness/client_tools.py::_resolve_under_root guards developer-machine
tool paths — a document name can never escape target_docs_dir.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from domain.events import SdlcEventEnvelope

logger = logging.getLogger(__name__)

_UNSAFE_CHARS = re.compile(r"[^A-Za-z0-9_.\-]")


def _sanitize_name(name: str) -> str:
    return _UNSAFE_CHARS.sub("_", name) or "document"


def apply_document_published(envelope: SdlcEventEnvelope, target_docs_dir: Path, s3_client: Any) -> dict:
    payload = envelope.payload  # DocumentPublishedPayload
    target_docs_dir.mkdir(parents=True, exist_ok=True)

    saved: list[str] = []
    for doc in payload.documents:
        doc_dir = (target_docs_dir / payload.session_id / doc.document_id).resolve()
        if target_docs_dir.resolve() not in doc_dir.parents and doc_dir != target_docs_dir.resolve():
            logger.error("repo_sync: refusing to write document outside target dir: %s", doc.document_id)
            continue
        doc_dir.mkdir(parents=True, exist_ok=True)

        dest_path = doc_dir / _sanitize_name(doc.name)
        body = s3_client.get_object(Bucket=doc.bucket, Key=doc.s3_key)["Body"].read()

        tmp_path = dest_path.with_suffix(dest_path.suffix + ".tmp")
        tmp_path.write_bytes(body)
        tmp_path.replace(dest_path)
        saved.append(str(dest_path))

    return {"saved": saved}
