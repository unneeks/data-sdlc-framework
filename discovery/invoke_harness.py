"""Invoke the discovery harness and handle inline function tool calls.

This script bridges the AgentCore Harness (which runs the LLM loop)
with our local deterministic tools (walk_repository, read_file, etc.).

The Harness calls tools as inline functions — when it needs a tool result,
it returns stopReason="tool_use" and we execute the tool locally, then
send the result back.

Usage:
    python -m discovery.invoke_harness /path/to/repo project-id

    # Or import and call programmatically:
    from discovery.invoke_harness import run_discovery_harness
    report = run_discovery_harness("/path/to/repo", "my-project")
"""

from __future__ import annotations

import json
import sys
import uuid

import boto3

from discovery.tools.walk import walk_repository
from discovery.tools.read import read_file
from discovery.tools.deep_walk import deep_walk_repository
from discovery.tools.ingest import ingest_entities, ingest_relationships, get_graph_state

HARNESS_ARN = "arn:aws:bedrock-agentcore:us-west-2:981956186421:harness/discovery_agent-7j9EL4p1Db"
REGION = "us-west-2"


def _execute_tool(tool_name: str, tool_input: dict) -> str:
    """Execute a tool locally and return JSON result."""
    if tool_name == "walk_repository":
        result = walk_repository(
            tool_input["repository_root"],
            extra_exclude_dirs=tool_input.get("extra_exclude_dirs", []),
        )
    elif tool_name == "read_file":
        result = read_file(
            tool_input["repository_root"],
            tool_input["relative_path"],
        )
    elif tool_name == "ingest_entities":
        result = ingest_entities(
            tool_input["project_id"],
            tool_input["entities"],
        )
    elif tool_name == "ingest_relationships":
        result = ingest_relationships(
            tool_input["project_id"],
            tool_input["relationships"],
        )
    elif tool_name == "deep_walk_repository":
        result = deep_walk_repository(
            tool_input["repository_root"],
            extra_exclude_dirs=tool_input.get("extra_exclude_dirs", []),
        )
    else:
        result = {"error": f"Unknown tool: {tool_name}"}

    return json.dumps(result, default=str)


def _parse_stream(response) -> tuple[list[dict], str, dict | None]:
    """Parse a streaming response, collecting content blocks.

    Returns (content_blocks, stop_reason, metadata).
    """
    content_blocks: list[dict] = []
    current_block: dict = {}
    stop_reason = ""
    metadata = None
    text_output = ""

    for event in response["stream"]:
        if "contentBlockStart" in event:
            start = event["contentBlockStart"].get("start", {})
            idx = event["contentBlockStart"].get("contentBlockIndex", len(content_blocks))
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

        elif "metadata" in event:
            metadata = event["metadata"]

        elif "runtimeClientError" in event:
            print(f"  ERROR: {event['runtimeClientError']['message']}", file=sys.stderr)

    if text_output:
        print(f"  Agent: {text_output[:200]}{'...' if len(text_output) > 200 else ''}")

    return content_blocks, stop_reason, metadata


def run_discovery_harness(
    repository_root: str,
    project_id: str,
    *,
    harness_arn: str = HARNESS_ARN,
    region: str = REGION,
    max_turns: int = 30,
) -> dict:
    """Run the discovery harness against a repository.

    The harness LLM decides the sequencing; we execute tools locally.
    Returns the final graph state.
    """
    client = boto3.client("bedrock-agentcore", region_name=region)
    session_id = str(uuid.uuid4())

    messages = [{
        "role": "user",
        "content": [{"text": (
            f"Discover the repository at {repository_root} for project '{project_id}'. "
            f"Walk the repo, extract all technical and delivery entities, "
            f"resolve relationships, and ingest everything into the graph."
        )}],
    }]

    print(f"Starting discovery harness session: {session_id}")
    print(f"  Repository: {repository_root}")
    print(f"  Project: {project_id}")
    print()

    for turn in range(max_turns):
        print(f"--- Turn {turn + 1} ---")

        response = client.invoke_harness(
            harnessArn=harness_arn,
            runtimeSessionId=session_id,
            messages=messages,
        )

        content_blocks, stop_reason, metadata = _parse_stream(response)

        if stop_reason == "end_turn":
            print("\nDiscovery complete.")
            break

        if stop_reason == "tool_use":
            # Find tool calls and execute them
            assistant_content = []
            tool_results = []

            for block in content_blocks:
                if block.get("type") == "toolUse":
                    tool_name = block["name"]
                    tool_input = block["input"]
                    tool_use_id = block["toolUseId"]

                    print(f"  Tool call: {tool_name}({json.dumps(tool_input)[:100]})")

                    result_text = _execute_tool(tool_name, tool_input)
                    print(f"  Result: {result_text[:100]}{'...' if len(result_text) > 100 else ''}")

                    assistant_content.append({
                        "toolUse": {
                            "toolUseId": tool_use_id,
                            "name": tool_name,
                            "input": tool_input,
                        }
                    })
                    tool_results.append({
                        "toolResult": {
                            "toolUseId": tool_use_id,
                            "content": [{"text": result_text}],
                            "status": "success",
                        }
                    })
                elif block.get("type") == "text" and block.get("text"):
                    assistant_content.append({"text": block["text"]})

            # Send assistant message + tool results back
            messages = [
                {"role": "assistant", "content": assistant_content},
                {"role": "user", "content": tool_results},
            ]
        else:
            print(f"  Unexpected stop reason: {stop_reason}")
            break

    # Return graph state
    state = get_graph_state(project_id)
    print(f"\nFinal graph: {state['entity_count']} entities, {state['relationship_count']} relationships")
    return state


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python -m discovery.invoke_harness <repository_root> <project_id>")
        sys.exit(1)

    repo_root = sys.argv[1]
    proj_id = sys.argv[2]
    result = run_discovery_harness(repo_root, proj_id)
    print(json.dumps(result, indent=2, default=str)[:2000])
