"""Unit tests for agents/skills/code_sync.py — the three tools an
AgentCore Harness agent uses to sync code/documents through S3.

Git operations run against the real `git` binary in a tmp_path fixture
(safe, fast, no network); only the S3 boundary is faked, injected via the
module's `_s3_client_override` test seam.
"""
import gzip
import io
import json
import sys
import tarfile
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

import pytest

import agents.skills.code_sync as code_sync
from domain.events import SdlcEventEnvelope
from harness.repo_sync_config import RepoSyncConfig


class FakeS3Client:
    def __init__(self):
        self.objects: dict[str, bytes] = {}

    def put_object(self, Bucket, Key, Body):
        self.objects[Key] = Body if isinstance(Body, bytes) else Body.encode()

    def get_object(self, Bucket, Key):
        return {"Body": io.BytesIO(self.objects[Key])}

    def head_object(self, Bucket, Key):
        if Key not in self.objects:
            raise KeyError(Key)
        return {}


def _make_config() -> RepoSyncConfig:
    config = RepoSyncConfig.__new__(RepoSyncConfig)
    config.region = "us-west-2"
    config.bucket_name = "test-bucket"
    config.code_prefix = "repo-sync/code"
    config.events_prefix = "repo-sync/events"
    config.docs_prefix = "repo-sync/docs"
    config.local_docs_dir = ".agentcore/synced-documents"
    config.apply_code_locally = True
    config.project_key = "test-project"
    return config


def _seed_baseline(client: FakeS3Client, config: RepoSyncConfig) -> None:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tf:
        content = b"# hello\n"
        info = tarfile.TarInfo(name="README.md")
        info.size = len(content)
        tf.addfile(info, io.BytesIO(content))
    tarball_bytes = gzip.compress(buf.getvalue())

    tarball_key = f"{config.code_prefix}/HEAD/seed.tar.gz"
    client.put_object(Bucket=config.bucket_name, Key=tarball_key, Body=tarball_bytes)
    client.put_object(
        Bucket=config.bucket_name, Key=f"{config.code_prefix}/HEAD/pointer.json",
        Body=json.dumps({"commit_sha": "seed", "tarball_key": tarball_key}).encode(),
    )


@pytest.fixture(autouse=True)
def _isolate(monkeypatch):
    config = _make_config()
    client = FakeS3Client()
    monkeypatch.setattr(code_sync, "repo_sync_config", config)
    monkeypatch.setattr(code_sync, "_s3_client_override", client)
    yield config, client
    code_sync._SCRATCH_WORKSPACES.clear()


def _events_of_type(client: FakeS3Client, prefix: str):
    for key, body in client.objects.items():
        if key.startswith(prefix):
            yield key, SdlcEventEnvelope.model_validate_json(body)


def test_sync_without_baseline_returns_clear_error(_isolate):
    result = code_sync.sync_code_from_s3(session_id="s-no-baseline")
    assert "error" in result
    assert "baseline" in result["error"]


def test_sync_creates_scratch_workspace_and_branch(_isolate):
    config, client = _isolate
    _seed_baseline(client, config)

    result = code_sync.sync_code_from_s3(session_id="s1", agent_id="a1")
    assert result["is_new_workspace"] is True
    assert result["branch_name"] == "agentcore/a1/s1"
    assert (Path(result["workspace_path"]) / "README.md").exists()


def test_sync_is_idempotent_without_force(_isolate):
    config, client = _isolate
    _seed_baseline(client, config)

    first = code_sync.sync_code_from_s3(session_id="s1")
    second = code_sync.sync_code_from_s3(session_id="s1")
    assert first["workspace_path"] == second["workspace_path"]
    assert second["is_new_workspace"] is False


def test_push_without_sync_first_returns_clear_error(_isolate):
    result = code_sync.push_code_to_s3(session_id="s-never-synced", files=[{"relative_path": "a.txt", "content": "x"}])
    assert "error" in result
    assert "sync_code_from_s3" in result["error"]


def test_push_with_no_actual_changes_is_a_noop(_isolate):
    config, client = _isolate
    _seed_baseline(client, config)
    code_sync.sync_code_from_s3(session_id="s1")

    result = code_sync.push_code_to_s3(session_id="s1", files=[])
    assert result == {"no_changes": True, "branch_name": "agentcore/session/s1"}


def test_push_commits_uploads_tarball_and_emits_event(_isolate):
    config, client = _isolate
    _seed_baseline(client, config)
    code_sync.sync_code_from_s3(session_id="s1", agent_id="a1")

    result = code_sync.push_code_to_s3(
        session_id="s1",
        files=[{"relative_path": "notes.md", "content": "hello world"}],
        commit_message="add notes",
    )
    assert result["no_changes"] is False
    assert result["commit_sha"]
    assert result["tarball_key"] in client.objects
    assert result["event_key"] in client.objects

    events = list(_events_of_type(client, config.events_prefix))
    assert len(events) == 1
    key, envelope = events[0]
    assert envelope.event_type.value == "CODE_PUSHED_TO_S3"
    assert envelope.payload.commit_sha == result["commit_sha"]
    assert envelope.payload.files_changed >= 1


def test_push_respects_delete_files(_isolate):
    config, client = _isolate
    _seed_baseline(client, config)
    sync_result = code_sync.sync_code_from_s3(session_id="s1")

    code_sync.push_code_to_s3(session_id="s1", delete_files=["README.md"], commit_message="remove readme")
    assert not (Path(sync_result["workspace_path"]) / "README.md").exists()


def test_push_rejects_path_traversal(_isolate):
    config, client = _isolate
    _seed_baseline(client, config)
    code_sync.sync_code_from_s3(session_id="s1")

    result = code_sync.push_code_to_s3(
        session_id="s1", files=[{"relative_path": "../../etc/evil", "content": "x"}],
    )
    assert "error" in result


def test_publish_documents_requires_at_least_one(_isolate):
    result = code_sync.publish_documents(session_id="s1", documents=[])
    assert "error" in result


def test_publish_documents_uploads_and_emits_one_event(_isolate):
    config, client = _isolate

    result = code_sync.publish_documents(
        session_id="s1", agent_id="a1",
        documents=[
            {"name": "spec.md", "content": "# spec"},
            {"name": "plan.md", "content": "# plan"},
        ],
    )
    assert len(result["uploaded"]) == 2
    assert result["failed"] == []
    assert result["event_key"] in client.objects

    events = list(_events_of_type(client, config.events_prefix))
    assert len(events) == 1
    _, envelope = events[0]
    assert envelope.event_type.value == "DOCUMENT_PUBLISHED"
    assert len(envelope.payload.documents) == 2


def test_publish_documents_partial_failure_still_publishes_the_rest(_isolate, monkeypatch):
    config, client = _isolate

    real_put_object = client.put_object
    call_count = {"n": 0}

    def flaky_put_object(Bucket, Key, Body):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("simulated upload failure")
        real_put_object(Bucket=Bucket, Key=Key, Body=Body)

    monkeypatch.setattr(client, "put_object", flaky_put_object)

    result = code_sync.publish_documents(
        session_id="s1",
        documents=[{"name": "bad.md", "content": "x"}, {"name": "good.md", "content": "y"}],
    )
    assert len(result["uploaded"]) == 1
    assert len(result["failed"]) == 1
    assert result["failed"][0]["name"] == "bad.md"


if __name__ == "__main__":
    print("Run with pytest — this suite relies on the autouse _isolate fixture.")
