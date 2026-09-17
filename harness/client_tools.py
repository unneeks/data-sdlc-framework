"""Tools the LLM can ask to run on the developer's machine.

These are advertised to the harness/Copilot backend alongside the normal
server-side skill tools (see agents/tools/definitions.py), but tagged
CLIENT in CLIENT_TOOL_NAMES. When the model calls one, LiveAgentSession does
not execute it inline — it pauses the turn loop and hands it to the UI for
approval (harness/live_session.py), because these tools touch the local
filesystem/shell rather than the sandboxed repository corpus the server-side
skills already operate on.

Kept intentionally small and read-mostly for the MVP: no arbitrary shell
execution. Every path argument is resolved and confined under the
repository root to prevent path traversal outside the project the operator
is working on.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Dict, List

CLIENT_TOOL_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "toolSpec": {
            "name": "client_list_directory",
            "description": (
                "List files and subdirectories at a path on the developer's local machine, "
                "relative to the repository root. Runs locally, not in the cloud."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "relative_path": {
                            "type": "string",
                            "description": "Path relative to the repository root (default '.')",
                        },
                    },
                },
            },
        },
    },
    {
        "toolSpec": {
            "name": "client_read_file",
            "description": (
                "Read a text file from the developer's local checkout. Runs locally, not in the cloud."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "relative_path": {"type": "string", "description": "Path relative to the repository root"},
                        "max_bytes": {"type": "integer", "description": "Truncate output to this many bytes (default 20000)"},
                    },
                    "required": ["relative_path"],
                },
            },
        },
    },
    {
        "toolSpec": {
            "name": "client_git_status",
            "description": "Run `git status --short` in the local checkout. Runs locally, not in the cloud.",
            "inputSchema": {"json": {"type": "object", "properties": {}}},
        },
    },
    {
        "toolSpec": {
            "name": "client_git_diff",
            "description": "Run `git diff` (optionally for one path) in the local checkout. Runs locally, not in the cloud.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "relative_path": {"type": "string", "description": "Optional path to scope the diff to"},
                    },
                },
            },
        },
    },
    {
        "toolSpec": {
            "name": "client_run_tests",
            "description": (
                "Run the local test suite (pytest) against a target path on the developer's "
                "machine and return pass/fail counts and captured output. Runs locally, not in the cloud."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "target_path": {"type": "string", "description": "Path relative to the repository root to test (default 'tests')"},
                    },
                },
            },
        },
    },
]

CLIENT_TOOL_NAMES = {t["toolSpec"]["name"] for t in CLIENT_TOOL_DEFINITIONS}

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_COMMAND_TIMEOUT_S = 60


def _resolve_under_root(relative_path: str) -> Path:
    candidate = (_PROJECT_ROOT / (relative_path or ".")).resolve()
    if _PROJECT_ROOT not in candidate.parents and candidate != _PROJECT_ROOT:
        raise ValueError(f"path escapes repository root: {relative_path}")
    return candidate


def build_client_tool_advertisement() -> List[Dict[str, Any]]:
    """Harness inline_function tool defs for every client-side tool, so the
    system prompt setup can advertise what the developer machine offers
    (see harness/live_session.py::_build_system_prompt)."""
    return [
        {
            "type": "inline_function",
            "name": t["toolSpec"]["name"],
            "config": {
                "inlineFunction": {
                    "description": t["toolSpec"]["description"],
                    "inputSchema": t["toolSpec"]["inputSchema"]["json"],
                },
            },
        }
        for t in CLIENT_TOOL_DEFINITIONS
    ]


def dispatch_client_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Execute one client tool on this machine and return a JSON-safe result.

    Called only after a human has approved the pending ClientToolCallRequest
    (see POST /api/live/session/{id}/tool-calls/{call_id}/approve).
    """
    handler = _HANDLERS.get(tool_name)
    if handler is None:
        return {"error": f"Unknown client tool: {tool_name}"}
    try:
        return handler(arguments or {})
    except Exception as exc:  # noqa: BLE001 - surface any local failure to the model
        return {"error": str(exc)}


def _list_directory(args: Dict[str, Any]) -> Dict[str, Any]:
    path = _resolve_under_root(args.get("relative_path", "."))
    if not path.exists():
        return {"error": f"path does not exist: {args.get('relative_path', '.')}"}
    entries = sorted(
        {"name": p.name, "type": "dir" if p.is_dir() else "file"} for p in path.iterdir()
    )
    return {"path": str(path.relative_to(_PROJECT_ROOT)), "entries": entries}


def _read_file(args: Dict[str, Any]) -> Dict[str, Any]:
    path = _resolve_under_root(args["relative_path"])
    if not path.is_file():
        return {"error": f"not a file: {args['relative_path']}"}
    max_bytes = int(args.get("max_bytes") or 20000)
    content = path.read_text(errors="replace")[:max_bytes]
    return {"path": str(path.relative_to(_PROJECT_ROOT)), "content": content}


def _run_git(args_list: List[str]) -> Dict[str, Any]:
    proc = subprocess.run(
        ["git", *args_list], cwd=_PROJECT_ROOT, capture_output=True, text=True, timeout=_COMMAND_TIMEOUT_S,
    )
    return {"returncode": proc.returncode, "stdout": proc.stdout[-8000:], "stderr": proc.stderr[-2000:]}


def _git_status(args: Dict[str, Any]) -> Dict[str, Any]:
    return _run_git(["status", "--short"])


def _git_diff(args: Dict[str, Any]) -> Dict[str, Any]:
    rel = args.get("relative_path")
    git_args = ["diff"]
    if rel:
        git_args.append(str(_resolve_under_root(rel).relative_to(_PROJECT_ROOT)))
    return _run_git(git_args)


def _run_tests(args: Dict[str, Any]) -> Dict[str, Any]:
    target = args.get("target_path", "tests")
    resolved = _resolve_under_root(target)
    proc = subprocess.run(
        ["python3", "-m", "pytest", str(resolved), "-q"],
        cwd=_PROJECT_ROOT, capture_output=True, text=True, timeout=_COMMAND_TIMEOUT_S,
    )
    return {
        "returncode": proc.returncode,
        "passed": proc.returncode == 0,
        "output": (proc.stdout + proc.stderr)[-8000:],
    }


_HANDLERS = {
    "client_list_directory": _list_directory,
    "client_read_file": _read_file,
    "client_git_status": _git_status,
    "client_git_diff": _git_diff,
    "client_run_tests": _run_tests,
}
