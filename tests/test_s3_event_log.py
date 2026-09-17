"""Unit tests for harness/s3_event_log.py: the sortable event-key builder
and SdlcEventPoller's dispatch/retry/cursor-persistence/restart behavior,
against an in-memory fake S3 client (mirrors tests/test_harness.py's
FakeBedrockAgentCoreClient convention rather than pulling in moto).
"""
import datetime
import io
import json
import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from domain.events import CodePushedToS3Payload, SDLCEventType, SdlcEventEnvelope
from harness.repo_sync_config import RepoSyncConfig
from harness.s3_event_log import SdlcEventPoller, build_event_key


class FakeS3Client:
    def __init__(self):
        self._objects: dict[str, bytes] = {}

    def put_object(self, Bucket, Key, Body):
        self._objects[Key] = Body if isinstance(Body, bytes) else Body.encode()

    def get_object(self, Bucket, Key):
        return {"Body": io.BytesIO(self._objects[Key])}

    def list_objects_v2(self, Bucket, Prefix, StartAfter=None):
        keys = sorted(k for k in self._objects if k.startswith(Prefix))
        if StartAfter:
            keys = [k for k in keys if k > StartAfter]
        return {"Contents": [{"Key": k} for k in keys]}


def _make_config(bucket="test-bucket") -> RepoSyncConfig:
    config = RepoSyncConfig.__new__(RepoSyncConfig)
    config.region = "us-west-2"
    config.bucket_name = bucket
    config.code_prefix = "repo-sync/code"
    config.events_prefix = "repo-sync/events"
    config.docs_prefix = "repo-sync/docs"
    config.local_docs_dir = ".agentcore/synced-documents"
    config.apply_code_locally = True
    config.project_key = "test-project"
    return config


def _put_event(client, config, session_id="s1") -> str:
    envelope = SdlcEventEnvelope(
        event_type=SDLCEventType.CODE_PUSHED_TO_S3,
        project_key="test-project", session_id=session_id, agent_id="a1",
        payload=CodePushedToS3Payload(
            bucket=config.bucket_name, code_prefix=config.code_prefix, tarball_key="k.tar.gz",
            branch_name="agentcore/a1/s1", commit_sha="sha1", base_commit_sha="base1",
            session_id=session_id, agent_id="a1",
        ),
    )
    key = build_event_key(envelope.created_at, envelope.event_id, config.events_prefix)
    client.put_object(Bucket=config.bucket_name, Key=key, Body=envelope.model_dump_json().encode())
    return key


def test_build_event_key_is_unique_and_sortable_at_same_microsecond():
    now = datetime.datetime(2026, 9, 17, 12, 0, 0, 123456)
    key_a = build_event_key(now, "aaaaaaaa-1111-1111-1111-111111111111", "events")
    key_b = build_event_key(now, "bbbbbbbb-2222-2222-2222-222222222222", "events")
    assert key_a != key_b
    assert key_a.startswith("events/20260917T120000123456Z_")


def test_poller_dispatches_events_in_key_order(tmp_path):
    client = FakeS3Client()
    config = _make_config()
    _put_event(client, config, session_id="first")
    _put_event(client, config, session_id="second")

    seen = []
    poller = SdlcEventPoller(
        config, cursor_path=tmp_path / "cursor.json",
        handlers={SDLCEventType.CODE_PUSHED_TO_S3: lambda e: seen.append(e.session_id)},
        s3_client=client,
    )
    poller.poll_once()
    assert seen == ["first", "second"]


def test_handler_failure_does_not_advance_cursor_and_is_retried(tmp_path):
    client = FakeS3Client()
    config = _make_config()
    _put_event(client, config, session_id="s1")

    attempts = []

    def flaky_handler(envelope):
        attempts.append(1)
        if len(attempts) < 2:
            raise RuntimeError("simulated transient failure")

    poller = SdlcEventPoller(
        config, cursor_path=tmp_path / "cursor.json",
        handlers={SDLCEventType.CODE_PUSHED_TO_S3: flaky_handler},
        s3_client=client,
    )
    poller.poll_once()
    assert len(attempts) == 1
    assert poller.status()["last_cursor_key"] is None  # not advanced past the failing event

    poller.poll_once()
    assert len(attempts) == 2
    assert poller.status()["last_cursor_key"] is not None  # succeeded on retry, now advanced


def test_poison_pill_is_dead_lettered_after_max_retries(tmp_path):
    client = FakeS3Client()
    config = _make_config()
    key = _put_event(client, config, session_id="s1")

    def always_fails(envelope):
        raise RuntimeError("permanently broken")

    poller = SdlcEventPoller(
        config, cursor_path=tmp_path / "cursor.json",
        handlers={SDLCEventType.CODE_PUSHED_TO_S3: always_fails},
        s3_client=client, max_retries=3,
    )
    for _ in range(3):
        poller.poll_once()

    assert poller.status()["last_cursor_key"] == key  # dead-lettered, cursor moved past it


def test_missing_handler_for_event_type_is_skipped_not_stuck(tmp_path):
    client = FakeS3Client()
    config = _make_config()
    key = _put_event(client, config, session_id="s1")

    poller = SdlcEventPoller(config, cursor_path=tmp_path / "cursor.json", handlers={}, s3_client=client)
    poller.poll_once()
    assert poller.status()["last_cursor_key"] == key


def test_malformed_event_object_is_dead_lettered(tmp_path):
    client = FakeS3Client()
    config = _make_config()
    bad_key = f"{config.events_prefix}/20260101T000000000000Z_deadbeef0000.json"
    client.put_object(Bucket=config.bucket_name, Key=bad_key, Body=b"{not valid json")

    called = []
    poller = SdlcEventPoller(
        config, cursor_path=tmp_path / "cursor.json",
        handlers={SDLCEventType.CODE_PUSHED_TO_S3: lambda e: called.append(e)},
        s3_client=client,
    )
    poller.poll_once()
    assert called == []
    assert poller.status()["last_cursor_key"] == bad_key


def test_fresh_poller_resumes_after_process_restart(tmp_path):
    """A freshly constructed poller against the same bucket + cursor file
    (simulating a process restart) must not reprocess already-applied events."""
    client = FakeS3Client()
    config = _make_config()
    _put_event(client, config, session_id="s1")
    cursor_path = tmp_path / "cursor.json"

    seen_first_run = []
    poller1 = SdlcEventPoller(
        config, cursor_path=cursor_path,
        handlers={SDLCEventType.CODE_PUSHED_TO_S3: lambda e: seen_first_run.append(e.session_id)},
        s3_client=client,
    )
    poller1.poll_once()
    assert seen_first_run == ["s1"]

    _put_event(client, config, session_id="s2")
    seen_second_run = []
    poller2 = SdlcEventPoller(
        config, cursor_path=cursor_path,
        handlers={SDLCEventType.CODE_PUSHED_TO_S3: lambda e: seen_second_run.append(e.session_id)},
        s3_client=client,
    )
    poller2.poll_once()
    assert seen_second_run == ["s2"]  # not ["s1", "s2"] — s1 was already applied


def test_unconfigured_poller_polls_are_no_ops(tmp_path):
    config = _make_config(bucket="")
    poller = SdlcEventPoller(config, cursor_path=tmp_path / "cursor.json", handlers={}, s3_client=FakeS3Client())
    assert poller.poll_once() == []


if __name__ == "__main__":
    import tempfile

    test_build_event_key_is_unique_and_sortable_at_same_microsecond()
    for fn in [
        test_poller_dispatches_events_in_key_order,
        test_handler_failure_does_not_advance_cursor_and_is_retried,
        test_poison_pill_is_dead_lettered_after_max_retries,
        test_missing_handler_for_event_type_is_skipped_not_stuck,
        test_malformed_event_object_is_dead_lettered,
        test_fresh_poller_resumes_after_process_restart,
        test_unconfigured_poller_polls_are_no_ops,
    ]:
        with tempfile.TemporaryDirectory() as d:
            fn(Path(d))
    print("All s3_event_log tests passed successfully!")
