"""Repository Discovery skill — walks a project's file tree and classifies assets.

This is the foundational skill: every other skill depends on its output.
Produces a structured inventory of code, config, docs, and infrastructure files
with their detected capabilities and entity types.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any


_EXTENSION_MAP = {
    ".py": "python",
    ".sql": "sql",
    ".yml": "yaml_config",
    ".yaml": "yaml_config",
    ".json": "json_config",
    ".tf": "terraform",
    ".md": "markdown",
    ".properties": "config",
    ".cfg": "config",
    ".toml": "config",
}

_CAPABILITY_HINTS = {
    "batch-ingestion": ["cron", "bulk_load", "COPY INTO", "bq load", "glue_job", "s3://", "gs://"],
    "streaming": ["kafka", "kinesis", "pubsub", "dataflow", "event_hub", "spark.readStream", "writeStream"],
    "change-data-capture": ["debezium", "datastream", "binlog", "cdc", "_is_deleted"],
    "transformation": ["dbt", "spark", "pandas", "dataform", "pyspark", "SparkSession"],
    "orchestration": ["airflow", "dagster", "prefect", "composer", "DAG(", "schedule_interval"],
    "data-quality": ["great_expectations", "dbt test", "soda", "not_null", "unique", "expect_"],
    "data-profiling": ["pandas_profiling", "profile", "statistics", "describe()"],
    "testing": ["pytest", "unittest", "assert", "test_"],
    "regression-testing": ["baseline", "snapshot", "golden", "regression", "reconciliation"],
    "metadata-management": ["dataplex", "glue catalog", "schema.yml", "data catalog", "openmetadata"],
    "lineage": ["lineage", "ref(", "manifest.json", "upstream", "downstream", "source("],
    "governance": ["policy_tag", "data_owner", "steward", "classification"],
    "security": ["iam", "kms", "secret", "encryption", "service_account"],
    "monitoring": ["alert", "logging", "prometheus", "sla", "freshness"],
    "documentation": ["README", "docs/"],
    "ci-cd": [".github/workflows", "gitlab-ci", "cloudbuild", "jenkinsfile"],
    "infrastructure-as-code": ["terraform", ".tf", "pulumi", "cloudformation"],
    "data-serving": ["mart", "api", "view", "dashboard", "looker", "trino", "superset"],
    "cost-management": ["slot", "partition by", "cluster by", "cost", "budget"],
}

_EXCLUDE_DIRS = {".git", "__pycache__", "node_modules", ".pytest_cache", ".venv", "venv", ".tox", ".mypy_cache"}


def discover_repository(repository_root: str, extra_exclude_dirs: list[str] | None = None) -> dict[str, Any]:
    """Walk a repository and return a structured inventory.

    Returns:
        {
            "files": [...],          # list of file descriptors
            "summary": {...},        # counts by type, capability hits
            "capabilities_detected": [...],
            "entity_count": int,
        }
    """
    root = Path(repository_root)
    if not root.is_dir():
        return {"error": f"Not a directory: {repository_root}"}

    excludes = _EXCLUDE_DIRS | set(extra_exclude_dirs or [])
    files = []
    capability_hits: dict[str, list[str]] = {}
    type_counts: dict[str, int] = {}

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in excludes]
        for fname in filenames:
            full = Path(dirpath) / fname
            rel = str(full.relative_to(root))
            ext = full.suffix.lower()
            file_type = _EXTENSION_MAP.get(ext, "other")

            entity_type = _classify_entity(rel, file_type)
            type_counts[entity_type] = type_counts.get(entity_type, 0) + 1

            content_snippet = ""
            detected_caps = []
            try:
                if full.stat().st_size < 200_000 and ext in _EXTENSION_MAP:
                    content_snippet = full.read_text(errors="replace")[:5000]
                    detected_caps = _detect_capabilities(rel, content_snippet)
                    for cap in detected_caps:
                        capability_hits.setdefault(cap, []).append(rel)
            except (OSError, UnicodeDecodeError):
                pass

            files.append({
                "path": rel,
                "type": file_type,
                "entity_type": entity_type,
                "size": full.stat().st_size if full.exists() else 0,
                "capabilities": detected_caps,
            })

    return {
        "files": files,
        "summary": {
            "total_files": len(files),
            "type_counts": type_counts,
            "capabilities_detected": sorted(capability_hits.keys()),
            "capability_file_counts": {k: len(v) for k, v in capability_hits.items()},
        },
        "capabilities_detected": sorted(capability_hits.keys()),
        "capability_details": {k: v[:5] for k, v in capability_hits.items()},
        "entity_count": len(files),
    }


def read_file(repository_root: str, relative_path: str) -> dict[str, Any]:
    """Read a file's contents for deeper analysis."""
    full = Path(repository_root) / relative_path
    if not full.is_file():
        return {"error": f"Not a file: {relative_path}"}
    try:
        content = full.read_text(errors="replace")
        if len(content) > 100_000:
            content = content[:100_000] + "\n... [truncated]"
        return {"path": relative_path, "content": content, "size": len(content)}
    except Exception as e:
        return {"error": str(e)}


def _classify_entity(rel_path: str, file_type: str) -> str:
    rel_lower = rel_path.lower()
    if "test" in rel_lower and file_type == "python":
        return "test"
    if "dag" in rel_lower or "orchestration" in rel_lower:
        return "pipeline_orchestration"
    if "ingestion" in rel_lower or "spark_job" in rel_lower:
        return "pipeline_ingestion"
    if "transformation" in rel_lower or "models/" in rel_lower:
        return "transformation"
    if "quality" in rel_lower or "expectations" in rel_lower or "soda" in rel_lower:
        return "data_quality"
    if "infrastructure" in rel_lower or "terraform" in rel_lower:
        return "infrastructure"
    if "serving" in rel_lower or "trino" in rel_lower:
        return "data_serving"
    if "governance" in rel_lower or "openmetadata" in rel_lower:
        return "governance"
    if file_type == "markdown":
        return "documentation"
    if file_type == "sql":
        return "transformation"
    if file_type == "python":
        return "code"
    return "config" if file_type in ("yaml_config", "json_config", "config") else "other"


def _detect_capabilities(rel_path: str, content: str) -> list[str]:
    detected = []
    combined = rel_path.lower() + "\n" + content.lower()
    for cap, hints in _CAPABILITY_HINTS.items():
        for hint in hints:
            if hint.lower() in combined:
                detected.append(cap)
                break
    return detected
