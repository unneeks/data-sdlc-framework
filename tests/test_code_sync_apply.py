"""Unit tests for harness/code_sync_apply.py — the orchestrator-side
handler that imports an incoming CODE_PUSHED_TO_S3 change into the
developer's real local repo. Uses real git repos in tmp_path (fast, no
network) to directly verify the central safety claim of this feature:
the working tree and the index are never touched, only refs/objects.
"""
import gzip
import io
import subprocess
import sys
import tarfile
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from domain.events import CodePushedToS3Payload, SDLCEventType, SdlcEventEnvelope
from harness.code_sync_apply import apply_code_pushed_to_s3


def _run_git(args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True)


def _init_real_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    _run_git(["init"], cwd=path)
    _run_git(["config", "user.email", "test@example.com"], cwd=path)
    _run_git(["config", "user.name", "Test"], cwd=path)
    (path / "existing.txt").write_text("original content\n")
    _run_git(["add", "-A"], cwd=path)
    _run_git(["commit", "-m", "initial"], cwd=path)


def _make_tarball_bytes(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tf:
        for name, content in files.items():
            info = tarfile.TarInfo(name=name)
            info.size = len(content)
            tf.addfile(info, io.BytesIO(content))
    return gzip.compress(buf.getvalue())


class FakeS3Client:
    def __init__(self, objects: dict[str, bytes]):
        self.objects = objects

    def get_object(self, Bucket, Key):
        return {"Body": io.BytesIO(self.objects[Key])}


def _make_envelope(tarball_key: str, branch_name: str = "feature-x") -> SdlcEventEnvelope:
    return SdlcEventEnvelope(
        event_type=SDLCEventType.CODE_PUSHED_TO_S3,
        project_key="p", session_id="s1", agent_id="a1",
        payload=CodePushedToS3Payload(
            bucket="b", code_prefix="repo-sync/code", tarball_key=tarball_key,
            branch_name=branch_name, commit_sha="incoming-sha", base_commit_sha="base-sha",
            session_id="s1", agent_id="a1", files_changed=1,
        ),
    )


def test_apply_creates_a_new_local_branch_with_incoming_content(tmp_path):
    target_repo = tmp_path / "target"
    _init_real_repo(target_repo)

    tarball_bytes = _make_tarball_bytes({"new_file.txt": b"from the agent\n"})
    client = FakeS3Client({"repo-sync/code/branches/feature-x/incoming-sha.tar.gz": tarball_bytes})
    envelope = _make_envelope("repo-sync/code/branches/feature-x/incoming-sha.tar.gz")

    result = apply_code_pushed_to_s3(envelope, target_repo, client)

    assert result["branch"] == "agentcore/feature-x"
    assert result["forced_side_branch"] is False

    branches = _run_git(["branch", "--list"], cwd=target_repo).stdout
    assert "agentcore/feature-x" in branches

    show_result = _run_git(["show", "agentcore/feature-x:new_file.txt"], cwd=target_repo)
    assert show_result.stdout == "from the agent\n"


def test_apply_never_touches_the_working_tree_or_index(tmp_path):
    """The central safety claim: uncommitted local work must be
    byte-for-byte untouched after applying an incoming change."""
    target_repo = tmp_path / "target"
    _init_real_repo(target_repo)

    # Simulate the developer mid-change: a staged edit and an untracked file.
    (target_repo / "existing.txt").write_text("developer's in-progress edit\n")
    _run_git(["add", "existing.txt"], cwd=target_repo)
    (target_repo / "scratch_notes.txt").write_text("untracked scratch notes\n")

    status_before = _run_git(["status", "--porcelain"], cwd=target_repo).stdout
    existing_content_before = (target_repo / "existing.txt").read_text()

    tarball_bytes = _make_tarball_bytes({"unrelated_new_file.py": b"print('hi')\n"})
    client = FakeS3Client({"k.tar.gz": tarball_bytes})
    envelope = _make_envelope("k.tar.gz")

    apply_code_pushed_to_s3(envelope, target_repo, client)

    status_after = _run_git(["status", "--porcelain"], cwd=target_repo).stdout
    existing_content_after = (target_repo / "existing.txt").read_text()

    assert status_after == status_before
    assert existing_content_after == existing_content_before
    assert (target_repo / "scratch_notes.txt").read_text() == "untracked scratch notes\n"
    # The incoming file must exist on the new branch, but not in the working tree.
    assert not (target_repo / "unrelated_new_file.py").exists()


def test_reapplying_the_same_event_is_idempotent(tmp_path):
    target_repo = tmp_path / "target"
    _init_real_repo(target_repo)

    tarball_bytes = _make_tarball_bytes({"f.txt": b"content\n"})
    client = FakeS3Client({"k.tar.gz": tarball_bytes})
    envelope = _make_envelope("k.tar.gz")

    first = apply_code_pushed_to_s3(envelope, target_repo, client)
    second = apply_code_pushed_to_s3(envelope, target_repo, client)

    assert first["branch"] == second["branch"] == "agentcore/feature-x"
    assert second["forced_side_branch"] is False


def test_non_fast_forward_retries_into_a_timestamped_side_branch_instead_of_forcing(tmp_path):
    target_repo = tmp_path / "target"
    _init_real_repo(target_repo)

    # First apply creates agentcore/feature-x pointing at commit A.
    tarball_a = _make_tarball_bytes({"a.txt": b"version A\n"})
    client_a = FakeS3Client({"a.tar.gz": tarball_a})
    apply_code_pushed_to_s3(_make_envelope("a.tar.gz"), target_repo, client_a)

    branch_before = _run_git(["rev-parse", "agentcore/feature-x"], cwd=target_repo).stdout.strip()

    # A second, divergent envelope for the SAME branch name (different tree,
    # not a descendant of A) is a non-fast-forward -> must not overwrite A.
    tarball_b = _make_tarball_bytes({"b.txt": b"version B, unrelated history\n"})
    client_b = FakeS3Client({"b.tar.gz": tarball_b})
    result = apply_code_pushed_to_s3(_make_envelope("b.tar.gz"), target_repo, client_b)

    assert result["forced_side_branch"] is True
    assert result["branch"] != "agentcore/feature-x"
    assert result["branch"].startswith("agentcore/feature-x-")

    # The original branch must be completely untouched.
    branch_after = _run_git(["rev-parse", "agentcore/feature-x"], cwd=target_repo).stdout.strip()
    assert branch_after == branch_before


if __name__ == "__main__":
    print("Run with pytest.")
