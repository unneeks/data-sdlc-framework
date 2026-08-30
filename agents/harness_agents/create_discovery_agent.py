#!/usr/bin/env python3
"""Create (or update) the Discovery Agent harness in AgentCore.

The Discovery Agent walks a codebase, extracts technical and delivery entities,
and populates a knowledge graph. It uses 5 inline function tools that execute
locally while the Harness LLM (Opus 4.6) orchestrates the sequencing.

Usage:
    python -m agents.harness_agents.create_discovery_agent
    python -m agents.harness_agents.create_discovery_agent --role-arn arn:aws:iam::123:role/MyRole
    python -m agents.harness_agents.create_discovery_agent --region us-east-1

Environment:
    AWS credentials must be configured. The execution role must have:
    - bedrock:InvokeModel (for the LLM)
    - bedrock-agentcore:InvokeHarness (for self-invocation)
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import boto3


HARNESS_NAME = "discovery_agent"
DEFAULT_REGION = "us-west-2"
DEFAULT_ROLE_ARN = "arn:aws:iam::553644760112:role/HarnessExecutionRole"
MODEL_ID = "global.anthropic.claude-opus-4-6-v1"

SKILLS_DIR = Path(__file__).resolve().parent.parent.parent / "discovery" / "skills"


def _load_system_prompt() -> str:
    """Build the system prompt from the repository-discovery skill."""
    skill_path = SKILLS_DIR / "repository-discovery.md"
    if skill_path.exists():
        skill_text = skill_path.read_text(encoding="utf-8")
    else:
        skill_text = "(Skill file not found — using minimal instructions)"

    return (
        "You are a repository discovery agent. Walk a codebase, extract technical "
        "and delivery entities, and populate a knowledge graph using the tools provided.\n\n"
        "Tools available:\n"
        "1. walk_repository — Walk directory tree and classify files by type\n"
        "2. read_file — Read a file's content\n"
        "3. ingest_entities — Validate and ingest entities into the knowledge graph\n"
        "4. ingest_relationships — Ingest relationships between entities\n"
        "5. deep_walk_repository — Deep analysis: module structure, code responsibilities, "
        "execution/behavior patterns, SBOM, and architecture style inference. "
        "Use this AFTER the basic walk to build a high-level abstraction of the codebase. "
        "Returns modules, responsibilities, patterns, sbom, entry_points, and architecture_style.\n\n"
        f"Follow these instructions:\n\n{skill_text}"
    )


def _build_tools() -> list[dict]:
    """Build the 4 inline function tool definitions."""
    return [
        {
            "type": "inline_function",
            "name": "walk_repository",
            "config": {"inlineFunction": {
                "description": (
                    "Walk a repository directory tree and classify files by type. "
                    "Returns technical (SQL, Python, Terraform, Docker, CI) and "
                    "delivery (Markdown, docs) file candidates."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "repository_root": {
                            "type": "string",
                            "description": "Absolute path to the repository root",
                        },
                        "extra_exclude_dirs": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Additional directories to exclude from walk",
                        },
                    },
                    "required": ["repository_root"],
                },
            }},
        },
        {
            "type": "inline_function",
            "name": "read_file",
            "config": {"inlineFunction": {
                "description": "Read a file's content from the repository. Returns content and metadata.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "repository_root": {
                            "type": "string",
                            "description": "Absolute path to repository root",
                        },
                        "relative_path": {
                            "type": "string",
                            "description": "Path relative to repository root",
                        },
                    },
                    "required": ["repository_root", "relative_path"],
                },
            }},
        },
        {
            "type": "inline_function",
            "name": "ingest_entities",
            "config": {"inlineFunction": {
                "description": (
                    "Validate and ingest discovered entities into the knowledge graph. "
                    "Assigns identity (entity_id) and provenance metadata."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Project identifier"},
                        "entities": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "entity_type": {
                                        "type": "string",
                                        "enum": [
                                            "Pipeline", "DataAsset", "Infrastructure",
                                            "CodeArtifact", "SchemaDefinition",
                                            "Task", "Checklist", "Gate",
                                            "DeliveryArtifact", "EvidenceRequirement",
                                        ],
                                    },
                                    "name": {"type": "string"},
                                    "source_document": {"type": "string"},
                                    "confidence": {"type": "number"},
                                    "provenance": {"type": "string", "enum": ["OBSERVED", "INFERRED"]},
                                    "attributes": {"type": "object"},
                                },
                                "required": ["entity_type", "name"],
                            },
                        },
                    },
                    "required": ["project_id", "entities"],
                },
            }},
        },
        {
            "type": "inline_function",
            "name": "ingest_relationships",
            "config": {"inlineFunction": {
                "description": (
                    "Ingest relationships between entities. Both source and target "
                    "are resolved by name or entity_id against the graph store."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string"},
                        "relationships": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "relationship_type": {
                                        "type": "string",
                                        "enum": [
                                            "DEPENDS_ON", "PRODUCES", "HAS_SCHEMA",
                                            "CONTAINS", "DESCRIBES", "GOVERNS", "VALIDATED_BY",
                                        ],
                                    },
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
            }},
        },
        {
            "type": "inline_function",
            "name": "deep_walk_repository",
            "config": {"inlineFunction": {
                "description": (
                    "Deep analysis of a repository. Reads file content, parses ASTs, "
                    "and produces: module structure (packages, classes, functions, imports), "
                    "code responsibilities (grouped areas of concern), execution/behavior "
                    "patterns (entry points, orchestration style, error handling, logging, "
                    "API routes, testing patterns), SBOM (software bill of materials from "
                    "all dependency manifests), and an inferred architecture style. "
                    "Use AFTER walk_repository for a high-level codebase abstraction."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "repository_root": {
                            "type": "string",
                            "description": "Absolute path to the repository root",
                        },
                        "extra_exclude_dirs": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Additional directories to exclude",
                        },
                    },
                    "required": ["repository_root"],
                },
            }},
        },
    ]


def create_or_update(region: str = DEFAULT_REGION, role_arn: str = DEFAULT_ROLE_ARN) -> dict:
    """Create the discovery agent harness, or update if it already exists."""
    client = boto3.client("bedrock-agentcore-control", region_name=region)

    system_prompt = [{"text": _load_system_prompt()}]
    tools = _build_tools()
    model = {"bedrockModelConfig": {"modelId": MODEL_ID}}

    # Try create first
    try:
        response = client.create_harness(
            harnessName=HARNESS_NAME,
            executionRoleArn=role_arn,
            systemPrompt=system_prompt,
            tools=tools,
            model=model,
        )
        harness = response.get("harness", response)
        harness_id = harness["harnessId"]
        action = "CREATED"
        print(f"Created harness: {HARNESS_NAME} ({harness_id})")

    except client.exceptions.ConflictException:
        # Already exists — find and update
        harnesses = client.list_harnesses()
        harness_id = None
        for h in harnesses.get("harnesses", []):
            if h["harnessName"] == HARNESS_NAME:
                harness_id = h["harnessId"]
                break

        if not harness_id:
            raise RuntimeError(f"Harness '{HARNESS_NAME}' conflict but not found in list")

        response = client.update_harness(
            harnessId=harness_id,
            systemPrompt=system_prompt,
            tools=tools,
            model=model,
        )
        harness = response.get("harness", response)
        action = "UPDATED"
        print(f"Updated harness: {HARNESS_NAME} ({harness_id})")

    # Wait for READY
    print("Waiting for READY...", end="", flush=True)
    for i in range(30):
        time.sleep(5)
        r = client.get_harness(harnessId=harness_id)
        status = r["harness"]["status"]
        print(".", end="", flush=True)
        if status == "READY":
            print(f" READY ({(i + 1) * 5}s)")
            break
        if status in ("FAILED", "CREATE_FAILED"):
            print(f" FAILED")
            return {"error": f"Harness creation failed: {status}", "harness": r["harness"]}
    else:
        print(f" TIMEOUT (still {status})")

    arn = r["harness"]["arn"]

    result = {
        "action": action,
        "name": HARNESS_NAME,
        "id": harness_id,
        "arn": arn,
        "region": region,
        "model": MODEL_ID,
        "status": status,
        "tools": ["walk_repository", "read_file", "ingest_entities", "ingest_relationships", "deep_walk_repository"],
    }

    print(f"\n{'='*60}")
    print(f"Discovery Agent Harness")
    print(f"{'='*60}")
    print(f"  Action:  {action}")
    print(f"  Name:    {HARNESS_NAME}")
    print(f"  ID:      {harness_id}")
    print(f"  ARN:     {arn}")
    print(f"  Region:  {region}")
    print(f"  Model:   {MODEL_ID}")
    print(f"  Status:  {status}")
    print(f"  Tools:   walk_repository, read_file, ingest_entities, ingest_relationships,")
    print(f"           deep_walk_repository")
    print(f"\nInvoke with:")
    print(f"  python -m discovery.invoke_harness /path/to/repo my-project-id")
    print(f"{'='*60}")

    return result


def main():
    parser = argparse.ArgumentParser(description="Create the Discovery Agent harness in AgentCore")
    parser.add_argument("--region", default=DEFAULT_REGION, help=f"AWS region (default: {DEFAULT_REGION})")
    parser.add_argument("--role-arn", default=DEFAULT_ROLE_ARN, help="IAM execution role ARN")
    args = parser.parse_args()

    result = create_or_update(region=args.region, role_arn=args.role_arn)
    print(f"\n{json.dumps(result, indent=2)}")


if __name__ == "__main__":
    main()
