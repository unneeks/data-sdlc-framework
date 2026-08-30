"""Harness Runner — executes agents in both REAL (AgentCore) and DEMO (local) modes.

In REAL mode: creates/reuses an AgentCore Harness, invokes it with the agent's
system prompt and tools, and bridges tool calls to local skill implementations.

In DEMO mode: runs the agent's skill chain directly (deterministic, no LLM),
producing the same structured output format.
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any

from agents.harness_agents.registry import get_agent_config
from agents.skills.repository_discovery import discover_repository, read_file
from agents.skills.dependency_analysis import analyze_dependencies
from agents.skills.impact_analysis import analyze_impact
from agents.skills.test_selection import select_tests
from agents.skills.test_execution import execute_tests
from agents.skills.data_profiling import profile_data_assets
from agents.skills.delivery_process import discover_delivery_process, validate_checklist, assess_gate_readiness
from agents.skills.evidence_validation import validate_evidence

logger = logging.getLogger(__name__)


class AgentRunner:
    """Runs metamodel agents against a repository corpus."""

    def __init__(self, repository_root: str, project_seed: dict | None = None,
                 test_scenarios: dict | None = None, mode: str = "DEMO"):
        self.repository_root = repository_root
        self.project_seed = project_seed or {}
        self.test_scenarios = test_scenarios or {}
        self.mode = mode
        self._context: dict[str, Any] = {}
        self._traces: list[dict] = []

    def run_agent(self, agent_key: str, task_input: dict) -> dict[str, Any]:
        """Run a specific agent with the given task input.

        Args:
            agent_key: metamodel agent key (e.g. "impact-analysis-agent")
            task_input: task-specific input (e.g. change_description, affected_files)

        Returns:
            Structured result from the agent's skill chain.
        """
        config = get_agent_config(agent_key)
        if not config:
            return {"error": f"Unknown agent: {agent_key}"}

        trace = {
            "agent_key": agent_key,
            "session_id": str(uuid.uuid4()),
            "start_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "mode": self.mode,
            "steps": [],
        }

        try:
            if self.mode == "REAL":
                result = self._run_harness(agent_key, config, task_input, trace)
            else:
                result = self._run_demo(agent_key, config, task_input, trace)

            trace["end_time"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            trace["status"] = "COMPLETED"
            trace["result_summary"] = _summarize(result)
            self._traces.append(trace)
            return result

        except Exception as e:
            trace["end_time"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            trace["status"] = "FAILED"
            trace["error"] = str(e)
            self._traces.append(trace)
            return {"error": str(e), "agent_key": agent_key}

    def _run_demo(self, agent_key: str, config: dict, task_input: dict, trace: dict) -> dict:
        """Run agent in demo mode — direct skill execution, no LLM."""
        if agent_key == "impact-analysis-agent":
            return self._demo_impact_analysis(task_input, trace)
        elif agent_key == "regression-agent":
            return self._demo_regression(task_input, trace)
        elif agent_key == "data-quality-agent":
            return self._demo_data_quality(task_input, trace)
        elif agent_key == "data-model-composer":
            return self._demo_data_model(task_input, trace)
        elif agent_key == "delivery-compliance-agent":
            return self._demo_delivery_compliance(task_input, trace)
        else:
            return {"error": f"No demo implementation for {agent_key}"}

    def _run_harness(self, agent_key: str, config: dict, task_input: dict, trace: dict) -> dict:
        """Run agent via AgentCore Harness with tool bridging."""
        import boto3
        from harness.config import harness_config

        client = boto3.client("bedrock-agentcore", region_name=harness_config.aws_region)

        harness_arn = harness_config.agent_runtime_arn
        if not harness_arn:
            logger.warning("No harness ARN configured, falling back to demo mode")
            return self._run_demo(agent_key, config, task_input, trace)

        session_id = trace["session_id"]
        prompt = self._build_prompt(agent_key, task_input)

        messages = [
            {"role": "user", "content": [{"text": prompt}]},
        ]

        for turn in range(20):
            response = client.invoke_harness(
                harnessArn=harness_arn,
                runtimeSessionId=session_id,
                messages=messages,
                model={"bedrockModelConfig": {"modelId": config["bedrock_model_id"]}},
                systemPrompt=[{"text": config["system_prompt"]}],
                toolConfiguration={"tools": config["tools"]},
            )

            content_blocks, stop_reason = self._parse_stream(response)
            trace["steps"].append({"turn": turn, "stop_reason": stop_reason})

            if stop_reason == "end_turn":
                text = " ".join(b.get("text", "") for b in content_blocks if b.get("type") == "text")
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    return {"raw_response": text, "agent_key": agent_key}

            if stop_reason == "tool_use":
                assistant_content = []
                tool_results = []

                for block in content_blocks:
                    if block.get("type") == "toolUse":
                        result_text = self._execute_tool(block["name"], block["input"])
                        assistant_content.append({
                            "toolUse": {
                                "toolUseId": block["toolUseId"],
                                "name": block["name"],
                                "input": block["input"],
                            }
                        })
                        tool_results.append({
                            "toolResult": {
                                "toolUseId": block["toolUseId"],
                                "content": [{"text": result_text}],
                                "status": "success",
                            }
                        })
                        trace["steps"].append({
                            "tool": block["name"],
                            "input_preview": str(block["input"])[:200],
                        })
                    elif block.get("type") == "text" and block.get("text"):
                        assistant_content.append({"text": block["text"]})

                messages = [
                    {"role": "assistant", "content": assistant_content},
                    {"role": "user", "content": tool_results},
                ]

        return {"error": "Max turns exceeded", "agent_key": agent_key}

    def _build_prompt(self, agent_key: str, task_input: dict) -> str:
        parts = [f"Execute the {agent_key} workflow against repository: {self.repository_root}"]
        if task_input.get("change_description"):
            parts.append(f"\nChange: {task_input['change_description']}")
        if task_input.get("affected_files"):
            parts.append(f"\nAffected files: {json.dumps(task_input['affected_files'])}")
        if task_input.get("change_id"):
            parts.append(f"\nChange ID: {task_input['change_id']}")
        if task_input.get("gate_name"):
            parts.append(f"\nGate: {task_input['gate_name']}")
        return "\n".join(parts)

    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        """Bridge tool calls to local skill implementations."""
        result = self._dispatch_tool(tool_name, tool_input)
        return json.dumps(result, default=str)

    def _dispatch_tool(self, tool_name: str, tool_input: dict) -> Any:
        repo = tool_input.get("repository_root", self.repository_root)

        if tool_name == "discover_repository":
            return discover_repository(repo)
        elif tool_name == "read_file":
            return read_file(repo, tool_input["relative_path"])
        elif tool_name == "analyze_dependencies":
            files = tool_input.get("discovered_files", self._get_discovered_files())
            return analyze_dependencies(repo, files)
        elif tool_name == "analyze_impact":
            return self._run_impact(tool_input)
        elif tool_name == "select_tests":
            return select_tests(
                tool_input["impact_result"],
                self._get_discovered_files(),
                self.test_scenarios,
            )
        elif tool_name == "execute_tests":
            return execute_tests(
                tool_input["selected_tests"],
                tool_input.get("change_id", ""),
                self.test_scenarios,
            )
        elif tool_name == "profile_data_assets":
            return profile_data_assets(repo, self._get_discovered_files(), self.project_seed)
        elif tool_name == "discover_delivery_process":
            return discover_delivery_process(repo, self._get_discovered_files(), self.project_seed)
        elif tool_name == "validate_checklist":
            return validate_checklist(tool_input["checklist_items"], tool_input["evidence"])
        elif tool_name == "assess_gate_readiness":
            return assess_gate_readiness(
                tool_input["gate_name"],
                tool_input["checklist_result"],
                tool_input.get("test_result"),
                tool_input.get("impact_result"),
            )
        elif tool_name == "validate_evidence":
            return validate_evidence(tool_input["evidence"], tool_input.get("requirements"))
        else:
            return {"error": f"Unknown tool: {tool_name}"}

    def _get_discovered_files(self) -> list[dict]:
        if "discovered_files" not in self._context:
            result = discover_repository(self.repository_root)
            self._context["discovered_files"] = result.get("files", [])
            self._context["discovery_result"] = result
        return self._context["discovered_files"]

    def _get_dependencies(self) -> dict:
        if "dependencies" not in self._context:
            files = self._get_discovered_files()
            self._context["dependencies"] = analyze_dependencies(self.repository_root, files)
        return self._context["dependencies"]

    def _run_impact(self, task_input: dict) -> dict:
        deps = self._get_dependencies()
        return analyze_impact(
            task_input.get("change_description", ""),
            task_input.get("affected_files", []),
            deps.get("dependency_graph", {}),
            deps.get("nodes", []),
            self.project_seed,
        )

    # --- Demo mode skill chains ---

    def _demo_impact_analysis(self, task_input: dict, trace: dict) -> dict:
        trace["steps"].append({"skill": "discover_repository"})
        self._get_discovered_files()

        trace["steps"].append({"skill": "analyze_dependencies"})
        deps = self._get_dependencies()

        trace["steps"].append({"skill": "analyze_impact"})
        result = analyze_impact(
            task_input.get("change_description", ""),
            task_input.get("affected_files", []),
            deps.get("dependency_graph", {}),
            deps.get("nodes", []),
            self.project_seed,
        )
        result["agent_key"] = "impact-analysis-agent"
        return result

    def _demo_regression(self, task_input: dict, trace: dict) -> dict:
        trace["steps"].append({"skill": "discover_repository"})
        files = self._get_discovered_files()

        trace["steps"].append({"skill": "analyze_dependencies"})
        deps = self._get_dependencies()

        trace["steps"].append({"skill": "analyze_impact"})
        impact = analyze_impact(
            task_input.get("change_description", ""),
            task_input.get("affected_files", []),
            deps.get("dependency_graph", {}),
            deps.get("nodes", []),
            self.project_seed,
        )

        trace["steps"].append({"skill": "select_tests"})
        selection = select_tests(impact, files, self.test_scenarios)

        trace["steps"].append({"skill": "execute_tests"})
        execution = execute_tests(
            selection["selected_tests"],
            task_input.get("change_id", ""),
            self.test_scenarios,
        )

        return {
            "agent_key": "regression-agent",
            "impact": impact,
            "test_selection": selection,
            "test_execution": execution,
            "overall_status": execution["overall_status"],
        }

    def _demo_data_quality(self, task_input: dict, trace: dict) -> dict:
        trace["steps"].append({"skill": "discover_repository"})
        files = self._get_discovered_files()

        trace["steps"].append({"skill": "profile_data_assets"})
        profiles = profile_data_assets(self.repository_root, files, self.project_seed)

        return {
            "agent_key": "data-quality-agent",
            **profiles,
        }

    def _demo_data_model(self, task_input: dict, trace: dict) -> dict:
        trace["steps"].append({"skill": "discover_repository"})
        files = self._get_discovered_files()

        trace["steps"].append({"skill": "profile_data_assets"})
        profiles = profile_data_assets(self.repository_root, files, self.project_seed)

        entities = []
        for p in profiles.get("profiles", []):
            entities.append({
                "name": p.get("asset_name", ""),
                "domain": p.get("domain", "Unknown"),
                "columns": p.get("columns", []),
                "source": p.get("source", ""),
                "provenance": "OBSERVED",
            })

        return {
            "agent_key": "data-model-composer",
            "entities": entities,
            "entity_count": len(entities),
            "profiles": profiles,
        }

    def _demo_delivery_compliance(self, task_input: dict, trace: dict) -> dict:
        trace["steps"].append({"skill": "discover_repository"})
        files = self._get_discovered_files()

        trace["steps"].append({"skill": "discover_delivery_process"})
        process = discover_delivery_process(self.repository_root, files, self.project_seed)

        evidence = task_input.get("evidence", [])
        checklist_items = process.get("checklists", [])
        if not checklist_items:
            checklist_items = [
                {"name": "Requirements documented", "required": True},
                {"name": "Design reviewed", "required": True},
                {"name": "Tests executed", "required": True},
                {"name": "Security assessment complete", "required": True},
            ]

        trace["steps"].append({"skill": "validate_checklist"})
        checklist_result = validate_checklist(checklist_items, evidence)

        gate_name = task_input.get("gate_name", "Release Readiness Gate")
        trace["steps"].append({"skill": "assess_gate_readiness"})
        gate_result = assess_gate_readiness(
            gate_name,
            checklist_result,
            task_input.get("test_result"),
            task_input.get("impact_result"),
        )

        trace["steps"].append({"skill": "validate_evidence"})
        ev_result = validate_evidence(evidence)

        return {
            "agent_key": "delivery-compliance-agent",
            "delivery_process": process,
            "checklist_result": checklist_result,
            "gate_assessment": gate_result,
            "evidence_validation": ev_result,
        }

    def _parse_stream(self, response) -> tuple[list[dict], str]:
        content_blocks: list[dict] = []
        current_block: dict = {}
        stop_reason = ""

        for event in response.get("stream", []):
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
                    current_block.setdefault("text", "")
                    current_block["text"] += delta["text"]
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

        return content_blocks, stop_reason

    def get_traces(self) -> list[dict]:
        return list(reversed(self._traces))

    def build_context(self) -> dict[str, Any]:
        """Build the full digital twin context by running discovery."""
        files = self._get_discovered_files()
        deps = self._get_dependencies()
        profiles = profile_data_assets(self.repository_root, files, self.project_seed)
        process = discover_delivery_process(self.repository_root, files, self.project_seed)

        self._context["profiles"] = profiles
        self._context["delivery_process"] = process

        return {
            "discovery": self._context.get("discovery_result", {}),
            "dependencies": deps,
            "profiles": profiles,
            "delivery_process": process,
            "project_seed": self.project_seed,
        }


def _summarize(result: dict) -> dict:
    summary = {}
    if "overall_status" in result:
        summary["status"] = result["overall_status"]
    if "risk_level" in result:
        summary["risk"] = result["risk_level"]
    if "total_affected_count" in result:
        summary["affected"] = result["total_affected_count"]
    if "entity_count" in result:
        summary["entities"] = result["entity_count"]
    return summary
