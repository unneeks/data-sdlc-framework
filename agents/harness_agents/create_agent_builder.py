#!/usr/bin/env python3
"""Create (or update) the Agent Builder harness in AgentCore.

The Agent Builder bootstraps AI agent designs from delivery model frameworks.
It analyses activities, classifies involvement, evaluates agent splitting,
maps skills, and produces 13-section design documents + agent manifests.

Uses 5 inline function tools that execute locally while the Harness LLM
(Opus 4.6) orchestrates the 8-step design process.

Usage:
    python -m agents.harness_agents.create_agent_builder
    python -m agents.harness_agents.create_agent_builder --role-arn arn:aws:iam::123:role/MyRole
    python -m agents.harness_agents.create_agent_builder --region us-east-1
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import boto3


HARNESS_NAME = "agent_builder"
DEFAULT_REGION = "us-west-2"
DEFAULT_ROLE_ARN = "arn:aws:iam::553644760112:role/HarnessExecutionRole"
MODEL_ID = "global.anthropic.claude-opus-4-6-v1"

PROMPT_FILE = Path(__file__).resolve().parent.parent.parent / "prompts" / "agent-builder.prompt.md"


def _load_system_prompt() -> str:
    """Build the system prompt from the agent-builder prompt file."""
    if PROMPT_FILE.exists():
        full_prompt = PROMPT_FILE.read_text(encoding="utf-8")
    else:
        full_prompt = "(Prompt file not found — using minimal instructions)"

    return (
        "You are an Agent Design Analyst. Your job is to bootstrap AI agent designs "
        "by reading delivery model frameworks and analysing which activities belong to "
        "the requested agent role.\n\n"
        "You have 5 inline function tools:\n"
        "1. locate_delivery_model — Check if delivery model files exist at a path\n"
        "2. read_activity — Read a specific delivery model activity file\n"
        "3. evaluate_splitting — Run the 7-criteria agent splitting evaluation\n"
        "4. check_existing_skills — Check skill catalogue for duplicates\n"
        "5. render_design — Render the design document and agent manifest\n\n"
        "Follow the 8-step process:\n"
        "1. Receive agent role (name, responsibility, phase scope)\n"
        "2. Locate delivery model (check path, list activity files)\n"
        "3. Analyse & classify activities (OWNS/CONTRIBUTES/CONSUMES/OUT_OF_SCOPE)\n"
        "3.5. Evaluate splitting (7 criteria — context, tools, verification, parallelism, testing, count, scaling)\n"
        "4. Derive skills (reuse existing, propose new for gaps)\n"
        "5. Draft 13-section design document\n"
        "6. Draft agent-template.yaml manifest\n"
        "7. Confirm with user before writing\n"
        "8. Offer configurator agent for use-case onboarding\n\n"
        f"Full instructions:\n\n{full_prompt[:8000]}"
    )


def _build_tools() -> list[dict]:
    """Build the 5 inline function tool definitions."""
    return [
        {
            "type": "inline_function",
            "name": "locate_delivery_model",
            "config": {"inlineFunction": {
                "description": (
                    "Check if a delivery model exists at the given path. Returns model info "
                    "including activity files found, their IDs, and the index file."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "delivery_model_root": {
                            "type": "string",
                            "description": "Path to directory containing delivery model Markdown files",
                        },
                    },
                    "required": ["delivery_model_root"],
                },
            }},
        },
        {
            "type": "inline_function",
            "name": "read_activity",
            "config": {"inlineFunction": {
                "description": (
                    "Read a delivery model activity file by ID. Returns the file content, "
                    "extracted sections (headings + body), and metadata."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "delivery_model_root": {"type": "string"},
                        "activity_id": {
                            "type": "string",
                            "description": "Activity ID like '3.2' or '4.4'",
                        },
                    },
                    "required": ["delivery_model_root", "activity_id"],
                },
            }},
        },
        {
            "type": "inline_function",
            "name": "evaluate_splitting",
            "config": {"inlineFunction": {
                "description": (
                    "Evaluate whether an agent should be split into sub-agents "
                    "using the 7 criteria: context boundaries, tool permissions, "
                    "independent verification, parallelism, dev/test ease, task count, team scaling."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "role_name": {"type": "string"},
                        "role_id": {"type": "string"},
                        "primary_responsibility": {"type": "string"},
                        "classifications": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "activity_id": {"type": "string"},
                                    "activity_name": {"type": "string"},
                                    "classification": {
                                        "type": "string",
                                        "enum": ["OWNS", "CONTRIBUTES", "CONSUMES", "OUT_OF_SCOPE"],
                                    },
                                    "rationale": {"type": "string"},
                                },
                                "required": ["activity_id", "activity_name", "classification"],
                            },
                        },
                        "criteria_results": {
                            "type": "array",
                            "description": "Optional LLM-evaluated criteria. Omit for heuristic evaluation.",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "recommendation": {"type": "string", "enum": ["SPLIT", "KEEP"]},
                                    "rationale": {"type": "string"},
                                },
                            },
                        },
                    },
                    "required": ["role_name", "role_id", "primary_responsibility", "classifications"],
                },
            }},
        },
        {
            "type": "inline_function",
            "name": "check_existing_skills",
            "config": {"inlineFunction": {
                "description": (
                    "Check the skill catalogue for existing skills and detect duplicates. "
                    "Returns existing skill list and which proposed IDs are duplicates."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "proposed_skill_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Skill IDs to check for duplicates",
                        },
                    },
                },
            }},
        },
        {
            "type": "inline_function",
            "name": "render_design",
            "config": {"inlineFunction": {
                "description": (
                    "Render the 13-section agent design Markdown document and "
                    "agent-template.yaml from structured data. Writes files to "
                    "agent-builder/agent-designs/."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "role_name": {"type": "string"},
                        "role_id": {"type": "string"},
                        "primary_responsibility": {"type": "string"},
                        "delivery_model_root": {"type": "string"},
                        "classifications": {"type": "array", "items": {"type": "object"}},
                        "responsibilities": {"type": "array", "items": {"type": "object"}},
                        "inputs": {"type": "array", "items": {"type": "object"}},
                        "outputs": {"type": "array", "items": {"type": "object"}},
                        "decisions": {"type": "array", "items": {"type": "object"}},
                        "tools": {"type": "array", "items": {"type": "object"}},
                        "knowledge": {"type": "array", "items": {"type": "object"}},
                        "skills": {"type": "array", "items": {"type": "object"}},
                        "workflow_steps": {"type": "array", "items": {"type": "object"}},
                        "handoffs": {"type": "array", "items": {"type": "object"}},
                        "evaluation_metrics": {"type": "array", "items": {"type": "object"}},
                        "constraints": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["role_name", "role_id", "primary_responsibility"],
                },
            }},
        },
    ]


def create_or_update(region: str = DEFAULT_REGION, role_arn: str = DEFAULT_ROLE_ARN) -> dict:
    """Create the agent builder harness, or update if it already exists."""
    client = boto3.client("bedrock-agentcore-control", region_name=region)

    system_prompt = [{"text": _load_system_prompt()}]
    tools = _build_tools()
    model = {"bedrockModelConfig": {"modelId": MODEL_ID}}

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
        "tools": [
            "locate_delivery_model", "read_activity",
            "evaluate_splitting", "check_existing_skills", "render_design",
        ],
    }

    print(f"\n{'='*60}")
    print(f"Agent Builder Harness")
    print(f"{'='*60}")
    print(f"  Action:  {action}")
    print(f"  Name:    {HARNESS_NAME}")
    print(f"  ID:      {harness_id}")
    print(f"  ARN:     {arn}")
    print(f"  Region:  {region}")
    print(f"  Model:   {MODEL_ID}")
    print(f"  Status:  {status}")
    print(f"  Tools:   locate_delivery_model, read_activity, evaluate_splitting,")
    print(f"           check_existing_skills, render_design")
    print(f"\nInvoke with:")
    print(f"  python -m agent_builder.platforms.agentcore_harness.invoke_builder \\")
    print(f"    'Data Engineer' 'automates pipeline dev' /path/to/model {arn}")
    print(f"{'='*60}")

    return result


def main():
    parser = argparse.ArgumentParser(description="Create the Agent Builder harness in AgentCore")
    parser.add_argument("--region", default=DEFAULT_REGION, help=f"AWS region (default: {DEFAULT_REGION})")
    parser.add_argument("--role-arn", default=DEFAULT_ROLE_ARN, help="IAM execution role ARN")
    args = parser.parse_args()

    result = create_or_update(region=args.region, role_arn=args.role_arn)
    print(f"\n{json.dumps(result, indent=2)}")


if __name__ == "__main__":
    main()
