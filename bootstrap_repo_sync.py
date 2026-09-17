#!/usr/bin/env python3
"""
Repo-Sync Bootstrap for Data SDLC Framework.

sync_code_from_s3 (agents/skills/code_sync.py) needs a code baseline to
already exist at s3://<bucket>/<code_prefix>/HEAD/pointer.json before any
agent session can run — nothing else in this feature seeds it. This
script archives the *current real repository* (via `git archive HEAD`,
run at the actual project root, not a scratch copy) and uploads it as that
initial baseline. Run it once, manually, before the first agent session
that uses the code-sync skill.

Usage:
    python bootstrap_repo_sync.py              # seed the baseline
    python bootstrap_repo_sync.py --force      # overwrite an existing baseline

Prerequisites:
    - AWS credentials configured (boto3 default chain)
    - A repo_sync bucket resolvable via harness/repo_sync_config.py
      (AGENTCORE_REPO_SYNC_BUCKET, agentcore_config.json["repo_sync"], or
      an existing knowledgebase bucket to fall back to)
"""
import argparse
import gzip
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness.repo_sync_config import repo_sync_config  # noqa: E402

_PROJECT_ROOT = Path(__file__).resolve().parent


def _object_exists(client, bucket: str, key: str) -> bool:
    try:
        client.head_object(Bucket=bucket, Key=key)
        return True
    except Exception:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Overwrite an existing baseline")
    args = parser.parse_args()

    if not repo_sync_config.configured:
        print("ERROR: no repo_sync bucket configured. Set AGENTCORE_REPO_SYNC_BUCKET, "
              "agentcore_config.json['repo_sync']['bucket_name'], or provision a "
              "knowledgebase bucket first (see agents/conventions/provisioner.py).")
        return 1

    import boto3

    client = boto3.client("s3", region_name=repo_sync_config.region)
    bucket = repo_sync_config.bucket_name
    pointer_key = f"{repo_sync_config.code_prefix}/HEAD/pointer.json"

    if _object_exists(client, bucket, pointer_key) and not args.force:
        print(f"A baseline already exists at s3://{bucket}/{pointer_key}. "
              f"Re-run with --force to overwrite it — this can orphan branches "
              f"already synced against the old baseline.")
        return 1

    print(f"Archiving {_PROJECT_ROOT} at HEAD...")
    result = subprocess.run(["git", "archive", "HEAD"], cwd=_PROJECT_ROOT, capture_output=True, timeout=120)
    if result.returncode != 0:
        print(f"ERROR: git archive failed: {result.stderr.decode(errors='replace')}")
        return 1
    commit_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=_PROJECT_ROOT, capture_output=True, text=True,
    ).stdout.strip()

    tarball_bytes = gzip.compress(result.stdout)
    tarball_key = f"{repo_sync_config.code_prefix}/HEAD/{commit_sha}.tar.gz"

    print(f"Uploading baseline tarball to s3://{bucket}/{tarball_key} ({len(tarball_bytes)} bytes)...")
    client.put_object(Bucket=bucket, Key=tarball_key, Body=tarball_bytes)

    print(f"Writing pointer to s3://{bucket}/{pointer_key}...")
    client.put_object(
        Bucket=bucket, Key=pointer_key,
        Body=json.dumps({"commit_sha": commit_sha, "tarball_key": tarball_key, "updated_at": time.time()}).encode(),
    )

    print(f"Done. Baseline commit {commit_sha[:12]} seeded at s3://{bucket}/{repo_sync_config.code_prefix}/HEAD/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
