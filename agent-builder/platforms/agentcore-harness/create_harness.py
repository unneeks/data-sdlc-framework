"""Create and publish the Agent Builder as an AgentCore Harness.

The harness uses inline function tools for deterministic operations
(locate model, read activities, evaluate splitting, render documents)
while the LLM handles classification, extraction, and reasoning.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import boto3

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SYSTEM_PROMPT = (PROJECT_ROOT / "prompts" / "agent-builder.prompt.md").read_text(encoding="utf-8")

HARNESS_NAME = "agent_builder"
REGION = "us-west-2"

TOOLS = [
    {
        "type": "inline_function",
        "name": "locate_delivery_model",
        "config": {"inlineFunction": {
            "description": "Check if a delivery model exists at the given path. Returns model info including activity files found.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "delivery_model_root": {"type": "string", "description": "Path to delivery model Markdown files"},
                },
                "required": ["delivery_model_root"],
            },
        }},
    },
    {
        "type": "inline_function",
        "name": "read_activity",
        "config": {"inlineFunction": {
            "description": "Read a delivery model activity file by ID. Returns content and extracted sections.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "delivery_model_root": {"type": "string"},
                    "activity_id": {"type": "string", "description": "Activity ID like '3.2' or '4.4'"},
                },
                "required": ["delivery_model_root", "activity_id"],
            },
        }},
    },
    {
        "type": "inline_function",
        "name": "evaluate_splitting",
        "config": {"inlineFunction": {
            "description": "Evaluate whether an agent should be split into sub-agents based on the 7 criteria. Returns split/keep recommendation.",
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
                                "classification": {"type": "string", "enum": ["OWNS", "CONTRIBUTES", "CONSUMES", "OUT_OF_SCOPE"]},
                                "rationale": {"type": "string"},
                            },
                            "required": ["activity_id", "activity_name", "classification"],
                        },
                    },
                    "criteria_results": {
                        "type": "array",
                        "description": "Optional: LLM-evaluated criteria. If omitted, heuristic evaluation is used.",
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
            "description": "Check the skill catalogue for existing skills. Returns list of existing skills and whether proposed IDs are duplicates.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "proposed_skill_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Skill IDs to check for duplicates",
                    },
                },
                "required": [],
            },
        }},
    },
    {
        "type": "inline_function",
        "name": "render_design",
        "config": {"inlineFunction": {
            "description": "Render the 13-section agent design Markdown document and agent-template.yaml from structured data.",
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


def create_harness(execution_role_arn: str) -> dict:
    """Create the Agent Builder harness in AgentCore."""
    client = boto3.client("bedrock-agentcore-control", region_name=REGION)

    system_prompt = (
        "You are an Agent Design Analyst. Your job is to bootstrap AI agent designs "
        "by reading delivery model frameworks and analysing which activities belong to "
        "the requested agent role.\n\n"
        "You have tools for: locating delivery models, reading activities, evaluating "
        "agent splitting, checking skill catalogues, and rendering design documents.\n\n"
        "Follow the 8-step process:\n"
        "1. Receive agent role\n"
        "2. Locate delivery model\n"
        "3. Analyse and classify activities (OWNS/CONTRIBUTES/CONSUMES/OUT_OF_SCOPE)\n"
        "3.5. Evaluate splitting (7 criteria)\n"
        "4. Derive skills\n"
        "5. Draft design document\n"
        "6. Draft agent manifest\n"
        "7. Confirm with user\n"
        "8. Offer configurator\n\n"
        f"Full instructions:\n\n{SYSTEM_PROMPT[:6000]}"
    )

    response = client.create_harness(
        harnessName=HARNESS_NAME,
        executionRoleArn=execution_role_arn,
        systemPrompt=[{"text": system_prompt}],
        tools=TOOLS,
        model={"bedrockModelConfig": {"modelId": "global.anthropic.claude-opus-4-6-v1"}},
    )

    harness = response.get("harness", response)
    return {
        "name": harness.get("harnessName"),
        "id": harness.get("harnessId"),
        "arn": harness.get("arn"),
        "status": harness.get("status"),
    }


if __name__ == "__main__":
    role_arn = sys.argv[1] if len(sys.argv) > 1 else "arn:aws:iam::553644760112:role/HarnessExecutionRole"
    result = create_harness(role_arn)
    print(json.dumps(result, indent=2))
