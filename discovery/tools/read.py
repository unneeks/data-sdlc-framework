"""File reading tools for discovery extraction.

Reads file content for the extraction step. Deterministic — no
interpretation, just I/O. The strategy decides what to do with
the content (send to LLM, parse directly, etc).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


MAX_FILE_SIZE = 100_000  # characters — skip files larger than this


def read_file(repository_root: str, relative_path: str) -> dict[str, Any]:
    """Read one file's content. Returns a serializable dict.

    Tool interface for MCP/Lambda/direct use.
    """
    root = Path(repository_root)
    full_path = root / relative_path

    if not full_path.exists():
        return {"path": relative_path, "error": "file_not_found"}

    if not full_path.is_file():
        return {"path": relative_path, "error": "not_a_file"}

    try:
        content = full_path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return {"path": relative_path, "error": f"read_failed: {e}"}

    if len(content) > MAX_FILE_SIZE:
        return {
            "path": relative_path,
            "error": "file_too_large",
            "size": len(content),
            "max_size": MAX_FILE_SIZE,
            "preview": content[:2000],
        }

    return {
        "path": relative_path,
        "content": content,
        "size": len(content),
        "lines": content.count("\n") + 1,
    }


def read_files_batch(
    repository_root: str,
    relative_paths: list[str],
) -> dict[str, Any]:
    """Read multiple files in one call. Returns results keyed by path."""
    results = {}
    for path in relative_paths:
        results[path] = read_file(repository_root, path)
    return {
        "repository_root": repository_root,
        "requested": len(relative_paths),
        "succeeded": sum(1 for r in results.values() if "error" not in r),
        "files": results,
    }
