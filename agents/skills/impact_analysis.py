"""Impact Analysis skill — traces a change through the dependency graph.

Given a change request (affected files/assets), computes the full blast radius
by traversing the dependency graph forward and backward.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def analyze_impact(
    change_description: str,
    affected_files: list[str],
    dependency_graph: dict[str, list[str]],
    nodes: list[dict],
    project_seed: dict | None = None,
) -> dict[str, Any]:
    """Compute technical and delivery impact of a change.

    Args:
        change_description: natural language description of the change
        affected_files: list of directly affected file paths
        dependency_graph: adjacency list from dependency_analysis
        nodes: node list from dependency_analysis
        project_seed: optional project seed data for asset/pipeline mapping

    Returns:
        {
            "directly_affected": [...],
            "transitively_affected": [...],
            "affected_assets": [...],
            "affected_pipelines": [...],
            "risk_level": "LOW|MEDIUM|HIGH|CRITICAL",
            "regulatory_impact": bool,
        }
    """
    node_by_id = {n["id"]: n for n in nodes}
    path_to_id = {n["path"]: n["id"] for n in nodes}

    reverse_graph: dict[str, list[str]] = {}
    for src, targets in dependency_graph.items():
        for t in targets:
            reverse_graph.setdefault(t, []).append(src)

    direct_ids = set()
    for f in affected_files:
        if f in path_to_id:
            direct_ids.add(path_to_id[f])
        stem = Path(f).stem
        for nid, n in node_by_id.items():
            if stem in nid or stem == Path(n.get("path", "")).stem:
                direct_ids.add(nid)

    transitive_ids = set()
    _traverse(direct_ids, dependency_graph, transitive_ids)
    _traverse(direct_ids, reverse_graph, transitive_ids)
    transitive_ids -= direct_ids

    all_affected_ids = direct_ids | transitive_ids
    all_affected_nodes = [node_by_id[nid] for nid in all_affected_ids if nid in node_by_id]

    affected_assets = _map_to_assets(all_affected_nodes, project_seed)
    affected_pipelines = _map_to_pipelines(all_affected_nodes, project_seed)

    risk_level = _assess_risk(change_description, all_affected_nodes, affected_assets)
    regulatory = _check_regulatory(change_description, all_affected_nodes, affected_assets)

    return {
        "directly_affected": [
            {"id": nid, "path": node_by_id.get(nid, {}).get("path", nid)}
            for nid in direct_ids
        ],
        "transitively_affected": [
            {"id": nid, "path": node_by_id.get(nid, {}).get("path", nid)}
            for nid in transitive_ids
        ],
        "affected_assets": affected_assets,
        "affected_pipelines": affected_pipelines,
        "total_affected_count": len(all_affected_ids),
        "risk_level": risk_level,
        "regulatory_impact": regulatory,
        "provenance": "OBSERVED",
        "confidence": 0.9 if direct_ids else 0.7,
    }


def _traverse(start: set[str], graph: dict[str, list[str]], visited: set[str], max_depth: int = 5) -> None:
    frontier = list(start)
    depth = 0
    while frontier and depth < max_depth:
        next_frontier = []
        for nid in frontier:
            for target in graph.get(nid, []):
                if target not in visited and target not in start:
                    visited.add(target)
                    next_frontier.append(target)
        frontier = next_frontier
        depth += 1


def _map_to_assets(affected_nodes: list[dict], project_seed: dict | None) -> list[dict]:
    if not project_seed:
        return []
    assets = project_seed.get("data_assets", [])
    matched = []
    for node in affected_nodes:
        path = node.get("path", "")
        for asset in assets:
            name = asset.get("name", "")
            short_name = name.split(".")[-1] if "." in name else name
            if short_name.lower() in path.lower() or path.lower() in name.lower():
                if asset not in matched:
                    matched.append(asset)
    return matched


def _map_to_pipelines(affected_nodes: list[dict], project_seed: dict | None) -> list[dict]:
    if not project_seed:
        return []
    pipelines = project_seed.get("pipelines", [])
    matched = []
    for node in affected_nodes:
        path = node.get("path", "")
        for pipe in pipelines:
            name = pipe.get("name", "")
            if name.lower() in path.lower() or Path(path).stem.lower() in name.lower():
                if pipe not in matched:
                    matched.append(pipe)
    return matched


def _assess_risk(description: str, nodes: list[dict], assets: list[dict]) -> str:
    desc_lower = description.lower()
    if any(w in desc_lower for w in ["regulatory", "compliance", "pra", "fca", "basel", "gdpr"]):
        return "CRITICAL"
    if any(w in desc_lower for w in ["production", "migration", "schema change"]):
        return "HIGH"
    if len(nodes) > 10 or len(assets) > 5:
        return "HIGH"
    if len(nodes) > 5 or len(assets) > 2:
        return "MEDIUM"
    return "LOW"


def _check_regulatory(description: str, nodes: list[dict], assets: list[dict]) -> bool:
    indicators = ["regulatory", "compliance", "pra", "fca", "basel", "gdpr", "sox", "ifrs", "pep"]
    combined = description.lower()
    for node in nodes:
        combined += " " + node.get("path", "").lower()
    for asset in assets:
        combined += " " + asset.get("domain", "").lower()
    return any(ind in combined for ind in indicators)
