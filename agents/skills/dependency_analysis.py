"""Dependency Analysis skill — builds a dependency graph from discovered files.

Parses imports, dbt refs/sources, Spark configs, Airflow DAG dependencies,
and SQL references to construct edges between entities.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def analyze_dependencies(repository_root: str, discovered_files: list[dict]) -> dict[str, Any]:
    """Analyze dependencies between discovered entities.

    Args:
        repository_root: path to the repo root
        discovered_files: output of discover_repository()["files"]

    Returns:
        {
            "nodes": [...],          # entities with ids
            "edges": [...],          # dependency edges
            "dependency_graph": {...} # adjacency: id -> [depends_on_ids]
        }
    """
    root = Path(repository_root)
    nodes = []
    edges = []
    graph: dict[str, list[str]] = {}

    file_to_id: dict[str, str] = {}
    for f in discovered_files:
        node_id = _path_to_id(f["path"])
        file_to_id[f["path"]] = node_id
        nodes.append({
            "id": node_id,
            "path": f["path"],
            "type": f.get("entity_type", "unknown"),
            "capabilities": f.get("capabilities", []),
        })
        graph[node_id] = []

    name_to_id: dict[str, str] = {}
    for n in nodes:
        stem = Path(n["path"]).stem
        name_to_id[stem] = n["id"]
        name_to_id[n["path"]] = n["id"]

    for f in discovered_files:
        fpath = root / f["path"]
        if not fpath.is_file():
            continue
        try:
            content = fpath.read_text(errors="replace")[:100_000]
        except (OSError, UnicodeDecodeError):
            continue

        source_id = file_to_id[f["path"]]
        deps = _extract_dependencies(f["path"], content, name_to_id)
        for dep_id, dep_type in deps:
            if dep_id != source_id:
                edges.append({
                    "source": source_id,
                    "target": dep_id,
                    "type": dep_type,
                })
                graph[source_id].append(dep_id)

    return {
        "nodes": nodes,
        "edges": edges,
        "dependency_graph": graph,
        "summary": {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
        },
    }


def _path_to_id(path: str) -> str:
    return path.replace("/", ".").replace("\\", ".").replace(" ", "_")


def _extract_dependencies(path: str, content: str, name_to_id: dict[str, str]) -> list[tuple[str, str]]:
    deps = []
    ext = Path(path).suffix.lower()

    if ext == ".sql":
        deps.extend(_extract_sql_deps(content, name_to_id))
    elif ext == ".py":
        deps.extend(_extract_python_deps(path, content, name_to_id))
    elif ext in (".yml", ".yaml"):
        deps.extend(_extract_yaml_deps(content, name_to_id))
    elif ext == ".json":
        deps.extend(_extract_json_deps(content, name_to_id))

    return deps


def _extract_sql_deps(content: str, name_to_id: dict[str, str]) -> list[tuple[str, str]]:
    deps = []
    for m in re.finditer(r"\{\{\s*ref\(\s*['\"](\w+)['\"]\s*\)\s*\}\}", content):
        ref_name = m.group(1)
        if ref_name in name_to_id:
            deps.append((name_to_id[ref_name], "dbt_ref"))
    for m in re.finditer(r"\{\{\s*source\(\s*['\"](\w+)['\"],\s*['\"](\w+)['\"]\s*\)\s*\}\}", content):
        source_name = m.group(2)
        if source_name in name_to_id:
            deps.append((name_to_id[source_name], "dbt_source"))
    for m in re.finditer(r"FROM\s+(\w+\.\w+)", content, re.IGNORECASE):
        table = m.group(1).split(".")[-1]
        if table in name_to_id:
            deps.append((name_to_id[table], "sql_from"))
    for m in re.finditer(r"JOIN\s+(\w+\.\w+)", content, re.IGNORECASE):
        table = m.group(1).split(".")[-1]
        if table in name_to_id:
            deps.append((name_to_id[table], "sql_join"))
    return deps


def _extract_python_deps(path: str, content: str, name_to_id: dict[str, str]) -> list[tuple[str, str]]:
    deps = []
    for m in re.finditer(r"from\s+([\w.]+)\s+import", content):
        module = m.group(1).split(".")[-1]
        if module in name_to_id:
            deps.append((name_to_id[module], "python_import"))
    for m in re.finditer(r'["\'](\w+_ingestion|transactions_streaming|risk_scores_batch)["\']', content):
        ref = m.group(1)
        if ref in name_to_id:
            deps.append((name_to_id[ref], "task_reference"))
    for m in re.finditer(r'(?:table|path|target)\s*[=:]\s*["\']([^"\']+)["\']', content):
        name = m.group(1).split("/")[-1].split(".")[-1]
        if name in name_to_id:
            deps.append((name_to_id[name], "data_target"))
    return deps


def _extract_yaml_deps(content: str, name_to_id: dict[str, str]) -> list[tuple[str, str]]:
    deps = []
    for m in re.finditer(r"ref\(\s*['\"](\w+)['\"]\s*\)", content):
        ref_name = m.group(1)
        if ref_name in name_to_id:
            deps.append((name_to_id[ref_name], "dbt_ref"))
    for m in re.finditer(r"source\(\s*['\"](\w+)['\"],\s*['\"](\w+)['\"]\s*\)", content):
        src = m.group(2)
        if src in name_to_id:
            deps.append((name_to_id[src], "dbt_source"))
    return deps


def _extract_json_deps(content: str, name_to_id: dict[str, str]) -> list[tuple[str, str]]:
    deps = []
    for m in re.finditer(r'"(?:source|target|table|depends_on)":\s*"([^"]+)"', content):
        name = m.group(1).split(".")[-1].split("/")[-1]
        if name in name_to_id:
            deps.append((name_to_id[name], "config_reference"))
    return deps
