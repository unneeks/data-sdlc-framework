"""Invoke the Agent Builder harness and handle inline function tool calls.

Bridges AgentCore Harness (LLM loop) with local deterministic tools.
Same pattern as discovery/invoke_harness.py.
"""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

import boto3

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from agent_builder.core.analyser import DeliveryModelAnalyser
from agent_builder.core.models import (
    ActivityClassification,
    AgentDesign,
    AgentRole,
    InvolvementCode,
    SkillMapping,
)
from agent_builder.core.renderer import render_design_document, render_agent_manifest
from agent_builder.core.skills import SkillCatalogue
from agent_builder.core.splitter import evaluate_splitting

REGION = "us-west-2"

_analysers: dict[str, DeliveryModelAnalyser] = {}


def _get_analyser(root: str) -> DeliveryModelAnalyser:
    if root not in _analysers:
        _analysers[root] = DeliveryModelAnalyser(root)
        _analysers[root].locate_model()
    return _analysers[root]


def _execute_tool(tool_name: str, tool_input: dict) -> str:
    """Execute a tool locally and return JSON result."""

    if tool_name == "locate_delivery_model":
        analyser = _get_analyser(tool_input["delivery_model_root"])
        result = analyser.locate_model()

    elif tool_name == "read_activity":
        analyser = _get_analyser(tool_input["delivery_model_root"])
        result = analyser.read_activity(tool_input["activity_id"])

    elif tool_name == "evaluate_splitting":
        role = AgentRole(
            role_name=tool_input["role_name"],
            primary_responsibility=tool_input["primary_responsibility"],
            role_id=tool_input.get("role_id", ""),
        )
        classifications = [
            ActivityClassification(
                activity_id=c["activity_id"],
                activity_name=c["activity_name"],
                classification=InvolvementCode(c["classification"]),
                rationale=c.get("rationale", ""),
            )
            for c in tool_input["classifications"]
        ]
        criteria = tool_input.get("criteria_results")
        eval_result = evaluate_splitting(role, classifications, criteria)
        result = {
            "decision": eval_result.decision.value,
            "rationale": eval_result.rationale,
            "split_score": eval_result.split_score,
            "keep_score": eval_result.keep_score,
            "criteria": [{"name": c.name, "recommendation": c.recommendation, "rationale": c.rationale} for c in eval_result.criteria],
            "proposed_subagents": eval_result.proposed_subagents,
        }

    elif tool_name == "check_existing_skills":
        catalogue = SkillCatalogue(PROJECT_ROOT / "agent-builder" / "agent-skills")
        proposed = tool_input.get("proposed_skill_ids", [])
        result = {
            "existing_skills": catalogue.existing_skills,
            "duplicates": [sid for sid in proposed if catalogue.check_duplicate(sid)],
        }

    elif tool_name == "render_design":
        role = AgentRole(
            role_name=tool_input["role_name"],
            primary_responsibility=tool_input["primary_responsibility"],
            role_id=tool_input.get("role_id", ""),
        )
        classifications = [
            ActivityClassification(
                activity_id=c.get("activity_id", ""),
                activity_name=c.get("activity_name", ""),
                classification=InvolvementCode(c.get("classification", "OUT_OF_SCOPE")),
                rationale=c.get("rationale", ""),
                source_file=c.get("source_file", ""),
            )
            for c in tool_input.get("classifications", [])
        ]
        skills = [
            SkillMapping(
                skill_id=s.get("skill_id", ""),
                description=s.get("description", ""),
                layer=s.get("layer", 2),
                applicable_when=s.get("applicable_when", "always"),
                is_existing=s.get("is_existing", False),
                responsibilities_covered=s.get("responsibilities_covered", []),
            )
            for s in tool_input.get("skills", [])
        ]
        design = AgentDesign(
            role=role,
            classifications=classifications,
            responsibilities=tool_input.get("responsibilities", []),
            inputs=tool_input.get("inputs", []),
            outputs=tool_input.get("outputs", []),
            decisions=tool_input.get("decisions", []),
            tools=tool_input.get("tools", []),
            knowledge=tool_input.get("knowledge", []),
            skills=skills,
            workflow_steps=tool_input.get("workflow_steps", []),
            handoffs=tool_input.get("handoffs", []),
            evaluation_metrics=tool_input.get("evaluation_metrics", []),
            constraints=tool_input.get("constraints", []),
            delivery_model_root=tool_input.get("delivery_model_root", ""),
        )
        doc = render_design_document(design)
        manifest = render_agent_manifest(design)

        output_dir = PROJECT_ROOT / "agent-builder" / "agent-designs"
        output_dir.mkdir(exist_ok=True)

        design_path = output_dir / f"{role.role_id}_Agent_Design.md"
        manifest_path = output_dir / f"{role.role_id}_agent-template.yaml"
        design_path.write_text(doc, encoding="utf-8")
        manifest_path.write_text(manifest, encoding="utf-8")

        result = {
            "design_file": str(design_path),
            "manifest_file": str(manifest_path),
            "design_preview": doc[:500],
            "manifest_preview": manifest[:500],
        }

    else:
        result = {"error": f"Unknown tool: {tool_name}"}

    return json.dumps(result, default=str)


def _parse_stream(response) -> tuple[list[dict], str]:
    content_blocks: list[dict] = []
    current_block: dict = {}
    stop_reason = ""
    text_output = ""

    for event in response["stream"]:
        if "contentBlockStart" in event:
            start = event["contentBlockStart"].get("start", {})
            if "toolUse" in start:
                current_block = {
                    "type": "toolUse",
                    "toolUseId": start["toolUse"]["toolUseId"],
                    "name": start["toolUse"]["name"],
                    "input_json": "",
                }
            else:
                current_block = {"type": "text", "text": ""}
        elif "contentBlockDelta" in event:
            delta = event["contentBlockDelta"].get("delta", {})
            if "text" in delta:
                current_block.setdefault("type", "text")
                current_block.setdefault("text", "")
                current_block["text"] += delta["text"]
                text_output += delta["text"]
            elif "toolUse" in delta:
                current_block.setdefault("input_json", "")
                current_block["input_json"] += delta["toolUse"].get("input", "")
        elif "contentBlockStop" in event:
            if current_block.get("type") == "toolUse":
                try:
                    current_block["input"] = json.loads(current_block.get("input_json", "{}"))
                except json.JSONDecodeError:
                    current_block["input"] = {}
            if current_block:
                content_blocks.append(current_block)
            current_block = {}
        elif "messageStop" in event:
            stop_reason = event["messageStop"].get("stopReason", "")

    if text_output:
        print(f"  Agent: {text_output[:300]}{'...' if len(text_output) > 300 else ''}")

    return content_blocks, stop_reason


def run_agent_builder(
    role_name: str,
    primary_responsibility: str,
    delivery_model_path: str,
    harness_arn: str,
    max_turns: int = 20,
) -> dict:
    """Run the agent builder harness."""
    client = boto3.client("bedrock-agentcore", region_name=REGION)
    session_id = str(uuid.uuid4())

    messages = [{
        "role": "user",
        "content": [{"text": (
            f"Bootstrap an agent design for:\n"
            f"- Role: {role_name}\n"
            f"- Primary responsibility: {primary_responsibility}\n"
            f"- Delivery model path: {delivery_model_path}\n\n"
            f"Follow the 8-step process to produce the design document and agent manifest."
        )}],
    }]

    print(f"Agent Builder session: {session_id}")
    print(f"  Role: {role_name}")
    print(f"  Delivery model: {delivery_model_path}\n")

    for turn in range(max_turns):
        print(f"--- Turn {turn + 1} ---")
        response = client.invoke_harness(
            harnessArn=harness_arn,
            runtimeSessionId=session_id,
            messages=messages,
        )
        content_blocks, stop_reason = _parse_stream(response)

        if stop_reason == "end_turn":
            print("\nAgent builder complete.")
            break

        if stop_reason == "tool_use":
            assistant_content = []
            tool_results = []

            for block in content_blocks:
                if block.get("type") == "toolUse":
                    name = block["name"]
                    inp = block["input"]
                    tid = block["toolUseId"]
                    print(f"  Tool: {name}({json.dumps(inp)[:100]})")
                    result_text = _execute_tool(name, inp)
                    print(f"  Result: {result_text[:100]}...")

                    assistant_content.append({"toolUse": {"toolUseId": tid, "name": name, "input": inp}})
                    tool_results.append({"toolResult": {"toolUseId": tid, "content": [{"text": result_text}], "status": "success"}})
                elif block.get("type") == "text" and block.get("text"):
                    assistant_content.append({"text": block["text"]})

            messages = [
                {"role": "assistant", "content": assistant_content},
                {"role": "user", "content": tool_results},
            ]
        else:
            print(f"  Stop: {stop_reason}")
            break

    return {"session_id": session_id, "turns": turn + 1}


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python invoke_builder.py <role_name> <responsibility> <model_path> <harness_arn>")
        sys.exit(1)
    run_agent_builder(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
