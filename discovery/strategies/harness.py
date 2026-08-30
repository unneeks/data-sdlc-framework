"""Harness strategy — AgentCore Harness orchestrates the discovery loop.

The Harness LLM IS the extractor. Tools are deterministic; the Harness
decides sequencing based on the loaded skill instructions. Each discovery
run is one Harness session with tool calls traced by AgentCore.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from discovery.result import DiscoveryReport, DiscoveryFailure
from discovery.strategy import DiscoveryConfig
from discovery.tools.ingest import get_graph_state


def _load_skill(skill_name: str) -> str:
    """Load a skill's instruction text from the skills directory."""
    skills_dir = Path(__file__).resolve().parent.parent / "skills"
    skill_path = skills_dir / f"{skill_name}.md"
    if not skill_path.exists():
        raise FileNotFoundError(f"Skill not found: {skill_path}")
    return skill_path.read_text(encoding="utf-8")


def _build_tool_definitions() -> list[dict[str, Any]]:
    """Build tool definitions for the Harness invocation."""
    return [
        {
            "name": "walk_repository",
            "description": "Walk a repository directory tree and classify files by type. Returns technical and delivery file candidates.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "repository_root": {"type": "string", "description": "Absolute path to the repository root"},
                    "extra_exclude_dirs": {"type": "array", "items": {"type": "string"}, "description": "Additional directories to exclude"},
                },
                "required": ["repository_root"],
            },
        },
        {
            "name": "read_file",
            "description": "Read a file's content from the repository.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "repository_root": {"type": "string"},
                    "relative_path": {"type": "string", "description": "Path relative to repository root"},
                },
                "required": ["repository_root", "relative_path"],
            },
        },
        {
            "name": "ingest_entities",
            "description": "Validate and ingest discovered entities into the knowledge graph. Assigns identity and provenance.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string"},
                    "entities": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "entity_type": {"type": "string", "enum": ["Pipeline", "DataAsset", "Infrastructure", "CodeArtifact", "SchemaDefinition", "Task", "Checklist", "Gate", "DeliveryArtifact", "EvidenceRequirement"]},
                                "name": {"type": "string"},
                                "source_document": {"type": "string"},
                                "confidence": {"type": "number"},
                                "attributes": {"type": "object"},
                            },
                            "required": ["entity_type", "name"],
                        },
                    },
                },
                "required": ["project_id", "entities"],
            },
        },
        {
            "name": "ingest_relationships",
            "description": "Ingest resolved relationships between entities in the knowledge graph.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string"},
                    "relationships": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "relationship_type": {"type": "string", "enum": ["DEPENDS_ON", "PRODUCES", "HAS_SCHEMA", "CONTAINS", "DESCRIBES", "GOVERNS", "VALIDATED_BY"]},
                                "source_ref": {"type": "string"},
                                "target_ref": {"type": "string"},
                                "confidence": {"type": "number"},
                            },
                            "required": ["relationship_type", "source_ref", "target_ref"],
                        },
                    },
                },
                "required": ["project_id", "relationships"],
            },
        },
    ]


class HarnessStrategy:
    """AgentCore Harness orchestrates. The LLM IS the extractor.

    Tools are deterministic; the Harness decides sequencing based on
    the loaded skill instructions.
    """

    name = "harness"

    def __init__(
        self,
        *,
        model_id: str = "anthropic.claude-sonnet-4-5-20250514-v1:0",
        region: str = "us-west-2",
    ):
        self._model_id = model_id
        self._region = region

    def discover(self, config: DiscoveryConfig) -> DiscoveryReport:
        import boto3

        skill_instructions = _load_skill(config.skill)
        tools = _build_tool_definitions()
        session_id = str(uuid.uuid4())

        client = boto3.client("bedrock-agentcore", region_name=self._region)

        instructions = (
            f"You are a repository discovery agent. Your task is to walk a codebase, "
            f"extract technical and delivery entities, and populate a knowledge graph.\n\n"
            f"Project ID: {config.project_id}\n"
            f"Repository Root: {config.repository_root}\n\n"
            f"Follow these skill instructions exactly:\n\n{skill_instructions}"
        )

        payload = {
            "task": f"Discover repository at {config.repository_root} for project {config.project_id}",
            "repository_root": str(config.repository_root),
            "project_id": config.project_id,
        }

        try:
            response = client.invoke_harness(
                modelId=self._model_id,
                instructions=instructions,
                tools=tools,
                sessionId=session_id,
                payload=json.dumps(payload).encode("utf-8"),
            )

            body = response.get("response")
            if hasattr(body, "read"):
                raw = json.loads(body.read().decode("utf-8"))
            else:
                raw = json.loads(str(body))

        except Exception as e:
            return DiscoveryReport(
                project_id=config.project_id,
                strategy=self.name,
                skill=config.skill,
                failed=[DiscoveryFailure(
                    kind="harness_invocation_failed",
                    detail=str(e),
                    source="invoke_harness",
                )],
            )

        # Build report from graph state (tools wrote directly during session)
        graph = get_graph_state(config.project_id)
        by_type: dict[str, int] = {}
        for entity in graph.get("entities", []):
            t = entity.get("entity_type", "unknown")
            by_type[t] = by_type.get(t, 0) + 1

        return DiscoveryReport(
            project_id=config.project_id,
            strategy=self.name,
            skill=config.skill,
            entities_discovered=graph["entity_count"],
            relationships_discovered=graph["relationship_count"],
            entities_by_type=by_type,
        )
