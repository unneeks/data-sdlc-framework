"""Deterministic file discovery and classification.

Walks a directory tree and classifies each file by name/extension/path
into a source_kind. Never opens a file — content interpretation belongs
to the extraction step (strategy-dependent).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_EXCLUDE_DIRS = frozenset(
    {".git", "__pycache__", "target", "dbt_packages", "node_modules",
     ".venv", "venv", "dist", ".next", "build", ".terraform"}
)

# Source kinds this module can classify
SQL = "sql"
PYTHON = "python"
DOCKERFILE = "dockerfile"
COMPOSE = "compose"
CI_WORKFLOW = "ci_workflow"
TERRAFORM = "terraform"
MARKDOWN = "markdown"
YAML_CONFIG = "yaml_config"
JSON_CONFIG = "json_config"

TECHNICAL_SOURCE_KINDS = frozenset(
    {SQL, PYTHON, DOCKERFILE, COMPOSE, CI_WORKFLOW, TERRAFORM, YAML_CONFIG, JSON_CONFIG}
)
DELIVERY_SOURCE_KINDS = frozenset({MARKDOWN})

# What entity types each source kind can produce
SOURCE_KIND_ENTITY_TYPES: dict[str, tuple[str, ...]] = {
    SQL: ("Pipeline", "DataAsset", "SchemaDefinition"),
    PYTHON: ("Pipeline", "CodeArtifact", "Infrastructure"),
    DOCKERFILE: ("Infrastructure",),
    COMPOSE: ("Infrastructure",),
    CI_WORKFLOW: ("Pipeline",),
    TERRAFORM: ("Infrastructure", "DataAsset"),
    YAML_CONFIG: ("Pipeline", "DataAsset"),
    JSON_CONFIG: ("DataAsset", "SchemaDefinition"),
    MARKDOWN: ("Task", "Checklist", "Gate", "DeliveryArtifact", "EvidenceRequirement"),
}


@dataclass(frozen=True)
class CandidateFile:
    """One file the walk found and classified."""
    path: str
    absolute_path: str
    source_kind: str
    entity_types: tuple[str, ...]


def classify_file(relative_path: str) -> str | None:
    """Classify one file by its name/extension/path. None = not a candidate."""
    p = Path(relative_path)
    name = p.name
    posix = p.as_posix()

    if name == "Dockerfile" or name.endswith(".dockerfile"):
        return DOCKERFILE
    if name in ("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"):
        return COMPOSE
    if ".github/workflows/" in posix and p.suffix in (".yml", ".yaml"):
        return CI_WORKFLOW
    if p.suffix == ".tf":
        return TERRAFORM
    if p.suffix == ".sql":
        return SQL
    if p.suffix == ".py" and "dag" in name.lower():
        return PYTHON
    if p.suffix == ".py" and any(kw in posix for kw in ("ingestion", "pipeline", "spark", "etl")):
        return PYTHON
    if p.suffix == ".md":
        return MARKDOWN
    if name in ("dbt_project.yml", "profiles.yml", "packages.yml"):
        return YAML_CONFIG
    if p.suffix in (".yml", ".yaml") and any(
        kw in posix for kw in ("quality", "expectations", "soda", "checks")
    ):
        return YAML_CONFIG
    if p.suffix == ".json" and any(
        kw in posix for kw in ("governance", "metadata", "connector", "glossary", "policy")
    ):
        return JSON_CONFIG
    return None


def walk_repository(
    repository_root: str,
    extra_exclude_dirs: list[str] | None = None,
) -> dict[str, Any]:
    """Walk a repository and return classified candidate files.

    This is the tool interface — returns a serializable dict suitable
    for use as an MCP/Lambda tool response.
    """
    root = Path(repository_root)
    exclude = DEFAULT_EXCLUDE_DIRS | frozenset(extra_exclude_dirs or [])
    candidates: list[CandidateFile] = []

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in exclude for part in relative.parts):
            continue
        kind = classify_file(relative.as_posix())
        if kind is not None:
            entity_types = SOURCE_KIND_ENTITY_TYPES.get(kind, ())
            candidates.append(CandidateFile(
                path=relative.as_posix(),
                absolute_path=str(path),
                source_kind=kind,
                entity_types=entity_types,
            ))

    by_kind: dict[str, int] = {}
    for c in candidates:
        by_kind[c.source_kind] = by_kind.get(c.source_kind, 0) + 1

    return {
        "repository_root": str(root),
        "total_candidates": len(candidates),
        "by_source_kind": by_kind,
        "technical": [
            {"path": c.path, "source_kind": c.source_kind, "entity_types": list(c.entity_types)}
            for c in candidates if c.source_kind in TECHNICAL_SOURCE_KINDS
        ],
        "delivery": [
            {"path": c.path, "source_kind": c.source_kind, "entity_types": list(c.entity_types)}
            for c in candidates if c.source_kind in DELIVERY_SOURCE_KINDS
        ],
    }
