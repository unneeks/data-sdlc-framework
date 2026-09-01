"""Handler for the impact-scanning skill."""
from __future__ import annotations

from typing import Any


def execute(input_data: dict[str, Any]) -> dict[str, Any]:
    """Execute the impact-scanning skill — delegates to built-in tools."""
    from agents.skills.repository_discovery import discover_repository
    from agents.skills.dependency_analysis import analyze_dependencies
    from agents.skills.impact_analysis import analyze_impact

    repo = input_data.get("repository_root", ".")
    discovery = discover_repository(repo)
    files = discovery.get("files", [])
    deps = analyze_dependencies(repo, files)

    result = analyze_impact(
        input_data.get("change_description", ""),
        input_data.get("affected_files", []),
        deps.get("dependency_graph", {}),
        deps.get("nodes", []),
        {},
    )
    return result
