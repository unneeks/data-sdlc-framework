"""The S3-backed event log: the "streaming log" transport for SdlcEventEnvelope.

S3 has no true append, so "a stream of events" is one small object per
event under a lexicographically sortable key — see build_event_key(). This
module owns that key format (both the writer in agents/skills/code_sync.py
and the reader here import it from one place) plus SdlcEventPoller, the
project-wide, session-independent watcher that lists new event objects
since a durable local cursor, parses them, and dispatches to per-event-type
handlers.

Robustness contract (see docs/adr/0008):
  - The cursor only advances after a handler returns successfully, so a
    crash mid-handler simply means "redo this one event" on the next call
    — every handler this module dispatches to must be idempotent.
  - A handler exception does not advance the cursor and is retried on the
    next poll_once() call, up to max_retries times, after which the event
    is dead-lettered (skipped, loudly) so one poison-pill event can never
    permanently wedge the poller.
  - An event object that fails to parse (malformed JSON, schema mismatch)
    is dead-lettered immediately — there is nothing to retry.
  - An event_type with no registered handler is skipped (forward
    compatible with event types a future release of this module doesn't
    know about yet).
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import secrets
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from pydantic import ValidationError

from domain.events import SDLCEventType, SdlcEventEnvelope
from harness.repo_sync_config import RepoSyncConfig

logger = logging.getLogger(__name__)

EventHandler = Callable[[SdlcEventEnvelope], None]


def build_event_key(now, event_id: str, events_prefix: str) -> str:
    """Sortable, collision-safe S3 key for one event object.

    An ISO-8601-basic UTC microsecond timestamp prefix makes plain
    ListObjectsV2 lexicographic order approximate chronological order
    across any number of concurrent writers with zero coordination; the
    trailing 12 hex chars of the event id guarantee uniqueness even if two
    events land in the same microsecond. Exact ordering under clock skew
    across writers isn't guaranteed — acceptable because every handler is
    idempotent and order-independent between event types; ordering only
    matters for this poller's own resumability, not for correctness of
    what gets applied.
    """
    ts = now.strftime("%Y%m%dT%H%M%S") + f"{now.microsecond:06d}Z"
    short_id = event_id.replace("-", "")[:12]
    return f"{events_prefix}/{ts}_{short_id}.json"


class _AtomicCursor:
    """A durable local cursor, deliberately not stored in S3.

    Each orchestrator host applies changes to its own local git checkout /
    local docs directory, so cursors are inherently per-host — like
    independent consumer groups. Colocated under the target repo's own
    .git/ dir so it survives restarts of that host and stays scoped to the
    checkout it advances.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def read(self) -> Optional[str]:
        if not self.path.exists():
            return None
        try:
            return json.loads(self.path.read_text()).get("last_processed_key")
        except (json.JSONDecodeError, OSError):
            logger.warning("repo_sync: cursor file %s unreadable, treating as empty", self.path)
            return None

    def write(self, last_processed_key: str) -> None:
        tmp_path = self.path.with_suffix(f".tmp{secrets.token_hex(4)}")
        tmp_path.write_text(json.dumps({"last_processed_key": last_processed_key, "updated_at": time.time()}))
        os.replace(tmp_path, self.path)


class SdlcEventPoller:
    def __init__(
        self,
        config: RepoSyncConfig,
        cursor_path: Path,
        handlers: Dict[SDLCEventType, EventHandler],
        poll_interval_s: float = 5.0,
        max_retries: int = 5,
        s3_client: Any = None,
        history_limit: int = 200,
    ) -> None:
        self._config = config
        self._cursor = _AtomicCursor(cursor_path)
        self._handlers = handlers
        self.poll_interval_s = poll_interval_s
        self.max_retries = max_retries
        self._s3_client = s3_client
        self._retry_counts: Dict[str, int] = {}
        self.history: List[dict] = []
        self._history_limit = history_limit
        self.last_error: Optional[str] = None

    def _get_client(self) -> Any:
        if self._s3_client is None:
            import boto3

            self._s3_client = boto3.client("s3", region_name=self._config.region)
        return self._s3_client

    def status(self) -> dict:
        return {
            "configured": self._config.configured,
            "bucket_name": self._config.bucket_name,
            "events_prefix": self._config.events_prefix,
            "last_cursor_key": self._cursor.read(),
            "last_error": self.last_error,
            "history_size": len(self.history),
        }

    def poll_once(self) -> List[SdlcEventEnvelope]:
        if not self._config.configured:
            return []

        client = self._get_client()
        cursor = self._cursor.read()
        list_kwargs: Dict[str, Any] = {
            "Bucket": self._config.bucket_name,
            "Prefix": f"{self._config.events_prefix}/",
        }
        if cursor:
            list_kwargs["StartAfter"] = cursor

        processed: List[SdlcEventEnvelope] = []
        try:
            response = client.list_objects_v2(**list_kwargs)
        except Exception as exc:  # noqa: BLE001 - surface, never crash the poll loop
            self.last_error = str(exc)
            logger.exception("repo_sync: list_objects_v2 failed")
            return processed

        for obj in sorted(response.get("Contents", []), key=lambda o: o["Key"]):
            key = obj["Key"]
            envelope = self._fetch_and_parse(client, key)
            if envelope is None:
                # Malformed object: nothing to retry, dead-letter and move on.
                self._cursor.write(key)
                continue

            handler = self._handlers.get(envelope.event_type)
            if handler is None:
                logger.info("repo_sync: no handler for %s, skipping %s", envelope.event_type, key)
                self._cursor.write(key)
                continue

            try:
                handler(envelope)
            except Exception as exc:  # noqa: BLE001 - retry policy handled below
                retries = self._retry_counts.get(key, 0) + 1
                self._retry_counts[key] = retries
                self.last_error = f"{key}: {exc}"
                if retries >= self.max_retries:
                    logger.error(
                        "repo_sync: handler for %s failed %d times, dead-lettering %s: %s",
                        envelope.event_type, retries, key, exc,
                    )
                    self._cursor.write(key)
                    self._retry_counts.pop(key, None)
                else:
                    logger.warning(
                        "repo_sync: handler for %s failed (attempt %d/%d) on %s: %s",
                        envelope.event_type, retries, self.max_retries, key, exc,
                    )
                    break  # stop this poll pass; retry this same key next poll_once()
            else:
                self._retry_counts.pop(key, None)
                self._cursor.write(key)
                processed.append(envelope)
                self._record_history(key, envelope)

        return processed

    def _fetch_and_parse(self, client: Any, key: str) -> Optional[SdlcEventEnvelope]:
        try:
            body = client.get_object(Bucket=self._config.bucket_name, Key=key)["Body"].read()
            return SdlcEventEnvelope.model_validate_json(body)
        except (ValidationError, json.JSONDecodeError, KeyError) as exc:
            logger.error("repo_sync: malformed event object %s, dead-lettering: %s", key, exc)
            return None
        except Exception:
            logger.exception("repo_sync: failed to fetch event object %s", key)
            return None

    def _record_history(self, key: str, envelope: SdlcEventEnvelope) -> None:
        self.history.append({
            "key": key,
            "event_id": envelope.event_id,
            "event_type": envelope.event_type.value,
            "session_id": envelope.session_id,
            "created_at": envelope.created_at.isoformat(),
        })
        if len(self.history) > self._history_limit:
            self.history = self.history[-self._history_limit :]

    async def run_forever(self) -> None:
        while True:
            try:
                self.poll_once()
            except Exception:  # noqa: BLE001 - the watcher must never die
                logger.exception("repo_sync: poll_once raised unexpectedly")
            await asyncio.sleep(self.poll_interval_s)
