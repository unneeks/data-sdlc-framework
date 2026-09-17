"""Tool definitions for AgentCore Harness inline functions.

Each tool is defined as a JSON Schema that the Harness API accepts.
The local executor maps tool names to skill implementations.
"""
from __future__ import annotations

TOOL_DEFINITIONS = [
    {
        "toolSpec": {
            "name": "discover_repository",
            "description": (
                "Walk a repository's file tree and classify all files by type "
                "(code, config, docs, infrastructure). Returns a structured inventory "
                "with detected capabilities (streaming, batch ingestion, etc.)."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "repository_root": {
                            "type": "string",
                            "description": "Absolute path to the repository root directory",
                        },
                    },
                    "required": ["repository_root"],
                },
            },
        },
    },
    {
        "toolSpec": {
            "name": "read_file",
            "description": "Read the contents of a specific file for deeper analysis.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "repository_root": {
                            "type": "string",
                            "description": "Absolute path to the repository root",
                        },
                        "relative_path": {
                            "type": "string",
                            "description": "Path relative to repository root",
                        },
                    },
                    "required": ["repository_root", "relative_path"],
                },
            },
        },
    },
    {
        "toolSpec": {
            "name": "analyze_dependencies",
            "description": (
                "Build a dependency graph from discovered files. Parses imports, "
                "dbt refs/sources, Spark configs, and SQL references to find edges."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "repository_root": {
                            "type": "string",
                            "description": "Absolute path to the repository root",
                        },
                        "discovered_files": {
                            "type": "array",
                            "description": "File inventory from discover_repository",
                            "items": {"type": "object"},
                        },
                    },
                    "required": ["repository_root", "discovered_files"],
                },
            },
        },
    },
    {
        "toolSpec": {
            "name": "analyze_impact",
            "description": (
                "Given a change description and affected files, trace through the "
                "dependency graph to compute full blast radius including affected "
                "assets, pipelines, risk level, and regulatory impact."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "change_description": {
                            "type": "string",
                            "description": "Natural language description of the change",
                        },
                        "affected_files": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of directly affected file paths",
                        },
                    },
                    "required": ["change_description", "affected_files"],
                },
            },
        },
    },
    {
        "toolSpec": {
            "name": "select_tests",
            "description": (
                "Given impact analysis results, select the minimal sufficient "
                "test set that covers all affected entities."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "impact_result": {
                            "type": "object",
                            "description": "Output of analyze_impact",
                        },
                    },
                    "required": ["impact_result"],
                },
            },
        },
    },
    {
        "toolSpec": {
            "name": "execute_tests",
            "description": "Execute (or simulate) the selected tests and return results with evidence.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "selected_tests": {
                            "type": "array",
                            "items": {"type": "object"},
                            "description": "Tests from select_tests output",
                        },
                        "change_id": {
                            "type": "string",
                            "description": "Identifier for the change being tested",
                        },
                    },
                    "required": ["selected_tests"],
                },
            },
        },
    },
    {
        "toolSpec": {
            "name": "profile_data_assets",
            "description": (
                "Profile data assets by analyzing schemas, quality checks, and code. "
                "Returns column statistics, quality indicators, and domain mappings."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "repository_root": {
                            "type": "string",
                            "description": "Absolute path to the repository root",
                        },
                    },
                    "required": ["repository_root"],
                },
            },
        },
    },
    {
        "toolSpec": {
            "name": "discover_delivery_process",
            "description": (
                "Discover the delivery process from documentation: phases, tasks, "
                "gates, and checklists."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "repository_root": {
                            "type": "string",
                            "description": "Absolute path to the repository root",
                        },
                    },
                    "required": ["repository_root"],
                },
            },
        },
    },
    {
        "toolSpec": {
            "name": "validate_checklist",
            "description": "Validate checklist items against available evidence.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "checklist_items": {
                            "type": "array",
                            "items": {"type": "object"},
                            "description": "List of checklist items to validate",
                        },
                        "evidence": {
                            "type": "array",
                            "items": {"type": "object"},
                            "description": "Available evidence items",
                        },
                    },
                    "required": ["checklist_items", "evidence"],
                },
            },
        },
    },
    {
        "toolSpec": {
            "name": "assess_gate_readiness",
            "description": "Assess whether a delivery gate is ready to proceed.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "gate_name": {
                            "type": "string",
                            "description": "Name of the gate to assess",
                        },
                        "checklist_result": {
                            "type": "object",
                            "description": "Output of validate_checklist",
                        },
                        "test_result": {
                            "type": "object",
                            "description": "Output of execute_tests (optional)",
                        },
                        "impact_result": {
                            "type": "object",
                            "description": "Output of analyze_impact (optional)",
                        },
                    },
                    "required": ["gate_name", "checklist_result"],
                },
            },
        },
    },
    {
        "toolSpec": {
            "name": "validate_evidence",
            "description": (
                "Validate that evidence items carry proper provenance, "
                "are complete, and satisfy delivery requirements."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "evidence": {
                            "type": "array",
                            "items": {"type": "object"},
                            "description": "Evidence items to validate",
                        },
                        "requirements": {
                            "type": "array",
                            "items": {"type": "object"},
                            "description": "Required evidence specifications (optional)",
                        },
                    },
                    "required": ["evidence"],
                },
            },
        },
    },
    {
        "toolSpec": {
            "name": "sync_code_from_s3",
            "description": (
                "Fetch the current code baseline from S3 into a scratch git workspace and "
                "create a working branch. Call this ONCE at the start of a coding task, before "
                "any edits. Safe to call again in the same session — it returns the existing "
                "workspace instead of recreating it. Use this when the environment has no "
                "direct network access to source control."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "branch_hint": {
                            "type": "string",
                            "description": "Optional branch name to resume/create. Omit to start a new branch from the latest baseline.",
                        },
                        "force": {
                            "type": "boolean",
                            "description": "Recreate the workspace even if one already exists for this session (default false).",
                        },
                    },
                },
            },
        },
    },
    {
        "toolSpec": {
            "name": "push_code_to_s3",
            "description": (
                "Write file changes into the scratch workspace created by sync_code_from_s3, "
                "commit them, archive the result, and upload it to S3, then notify the "
                "orchestrator watching for changes. Pass the full new content of every "
                "changed/added file. Call this once at the end of a coding task, or more than "
                "once for incremental checkpoints. Requires sync_code_from_s3 to have been "
                "called first in this session."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "files": {
                            "type": "array",
                            "description": "Files to write, with their full new content.",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "relative_path": {"type": "string"},
                                    "content": {"type": "string"},
                                },
                                "required": ["relative_path", "content"],
                            },
                        },
                        "delete_files": {
                            "type": "array",
                            "description": "Paths (relative to the workspace root) to delete.",
                            "items": {"type": "string"},
                        },
                        "commit_message": {
                            "type": "string",
                            "description": "Commit message describing the change.",
                        },
                    },
                },
            },
        },
    },
    {
        "toolSpec": {
            "name": "publish_documents",
            "description": (
                "Publish one or more finished documents (specs, reports, test plans, etc.) "
                "produced this session to durable S3 storage, and notify the orchestrator. "
                "Pass all documents produced so far in a single call when possible."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "documents": {
                            "type": "array",
                            "minItems": 1,
                            "description": "One or more documents to publish.",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "content": {"type": "string"},
                                    "content_type": {"type": "string", "description": "e.g. text/markdown"},
                                    "description": {"type": "string"},
                                },
                                "required": ["name", "content"],
                            },
                        },
                    },
                    "required": ["documents"],
                },
            },
        },
    },
]


def _load_agent_tool_map() -> dict[str, list[str]]:
    """Load agent→tool mappings from agent_configs.yaml, falling back to defaults."""
    import yaml as _yaml
    from pathlib import Path as _Path
    cfg_path = _Path(__file__).resolve().parent.parent / "agent_configs.yaml"
    if cfg_path.exists():
        data = _yaml.safe_load(cfg_path.read_text()) or {}
        return {
            key: agent.get("tools", [])
            for key, agent in data.get("agents", {}).items()
        }
    return {}


_AGENT_TOOL_MAP: dict[str, list[str]] = _load_agent_tool_map()


def get_tools_for_agent(agent_key: str) -> list[dict]:
    """Return the tool definitions relevant to a specific agent (Converse format)."""
    allowed_names = set(_AGENT_TOOL_MAP.get(agent_key, []))
    return [t for t in TOOL_DEFINITIONS if t["toolSpec"]["name"] in allowed_names]


def get_tools_by_names(tool_names: list[str]) -> list[dict]:
    """Return tool definitions for an explicit list of tool names (Converse format)."""
    name_set = set(tool_names)
    return [t for t in TOOL_DEFINITIONS if t["toolSpec"]["name"] in name_set]


def _to_inline_function(tool_spec_def: dict) -> dict:
    """Convert a Converse toolSpec definition to Harness inline_function format."""
    spec = tool_spec_def["toolSpec"]
    schema = spec["inputSchema"]["json"]
    return {
        "type": "inline_function",
        "name": spec["name"],
        "config": {
            "inlineFunction": {
                "description": spec["description"],
                "inputSchema": schema,
            }
        },
    }


def get_tools_for_agent_harness(agent_key: str) -> list[dict]:
    """Return tool definitions in AgentCore Harness inline_function format."""
    allowed_names = set(_AGENT_TOOL_MAP.get(agent_key, []))
    return [
        _to_inline_function(t)
        for t in TOOL_DEFINITIONS
        if t["toolSpec"]["name"] in allowed_names
    ]
