"""Handler for the data-profiling skill."""
from __future__ import annotations

from typing import Any


def execute(input_data: dict[str, Any]) -> dict[str, Any]:
    """Execute the data-profiling skill — delegates to built-in tools."""
    from agents.skills.repository_discovery import discover_repository
    from agents.skills.data_profiling import profile_data_assets

    repo = input_data.get("repository_root", ".")
    discovery = discover_repository(repo)
    files = discovery.get("files", [])
    return profile_data_assets(repo, files, {})
