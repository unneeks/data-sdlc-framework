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
from pathlib import Path
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


def _load_harness_config() -> dict:
    """Load per-agent harness ARNs from agentcore_config.json."""
    config_path = Path(__file__).resolve().parent.parent / "agentcore_config.json"
    if config_path.exists():
        data = json.loads(config_path.read_text())
        return {
            agent_key: info["harness_arn"]
            for agent_key, info in data.get("harnesses", {}).items()
            if info.get("status") == "READY"
        }
    return {}


class AgentRunner:
    """Runs metamodel agents against a repository corpus."""

    def __init__(self, repository_root: str, project_seed: dict | None = None,
                 test_scenarios: dict | None = None, mode: str = "DEMO",
                 on_event=None):
        self.repository_root = repository_root
        self.project_seed = project_seed or {}
        self.test_scenarios = test_scenarios or {}
        self.mode = mode
        self.on_event = on_event
        self._context: dict[str, Any] = {}
        self._traces: list[dict] = []
        self._harness_arns: dict[str, str] = _load_harness_config()

    def _emit(self, event_type: str, **kwargs):
        if self.on_event:
            self.on_event(event_type, kwargs)

    def reload_harness_config(self):
        """Reload harness ARNs (call after running setup_agentcore.py)."""
        self._harness_arns = _load_harness_config()

    def run_agent(self, agent_key: str, task_input: dict) -> dict[str, Any]:
        """Run a specific agent with the given task input.

        Args:
            agent_key: metamodel agent key (e.g. "impact-analysis-agent")
            task_input: task-specific input (e.g. change_description, affected_files)

        Returns:
            Structured result from the agent's skill chain.
        """
        logger.info("╔══ run_agent CALLED | agent=%s | mode=%s | input_keys=%s",
                     agent_key, self.mode, list(task_input.keys()))
        config = get_agent_config(agent_key)
        if not config:
            logger.error("║ Unknown agent: %s", agent_key)
            return {"error": f"Unknown agent: {agent_key}"}

        logger.info("║ Config loaded | model=%s | tools=%d | harness_tools=%d",
                     config.get("bedrock_model_id", "?"),
                     len(config.get("tools", [])),
                     len(config.get("harness_tools", [])))

        session_id = str(uuid.uuid4())
        trace = {
            "agent_key": agent_key,
            "session_id": session_id,
            "start_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "mode": self.mode,
            "steps": [],
        }
        logger.info("║ Session: %s", session_id)

        start = time.monotonic()
        try:
            if self.mode == "REAL":
                logger.info("║ Dispatching to _run_harness (REAL mode)")
                logger.info("║ Available harness ARNs: %s", list(self._harness_arns.keys()))
                result = self._run_harness(agent_key, config, task_input, trace)
            else:
                logger.info("║ Dispatching to _run_demo (DEMO mode)")
                result = self._run_demo(agent_key, config, task_input, trace)

            elapsed = time.monotonic() - start
            trace["end_time"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            trace["status"] = "COMPLETED"
            trace["result_summary"] = _summarize(result)
            self._traces.append(trace)
            logger.info("╚══ run_agent COMPLETED | agent=%s | %.1fs | result_keys=%s",
                         agent_key, elapsed, list(result.keys())[:10])
            return result

        except Exception as e:
            elapsed = time.monotonic() - start
            trace["end_time"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            trace["status"] = "FAILED"
            trace["error"] = str(e)
            self._traces.append(trace)
            logger.error("╚══ run_agent FAILED | agent=%s | %.1fs | %s: %s",
                          agent_key, elapsed, type(e).__name__, e)
            return {"error": str(e), "agent_key": agent_key}

    def _run_demo(self, agent_key: str, config: dict, task_input: dict, trace: dict) -> dict:
        """Run agent in demo mode — direct skill execution, no LLM."""
        logger.info("  ├─ DEMO dispatch for %s", agent_key)
        self._emit("thinking", text=f"Planning execution for {agent_key} in DEMO mode...")
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
        """Run agent via AgentCore Harness with tool bridging.

        Uses the per-agent harness ARN from agentcore_config.json, passes
        inline_function tools, and bridges tool_use calls back to local skills.
        """
        import boto3

        harness_arn = self._harness_arns.get(agent_key)
        if not harness_arn:
            raise RuntimeError(
                f"No harness ARN configured for {agent_key}. "
                f"Run setup_agentcore.py first or check agentcore_config.json."
            )

        region = "us-west-2"
        logger.info("  ├─ HARNESS init | arn=%s | region=%s", harness_arn, region)
        client = boto3.client("bedrock-agentcore", region_name=region)

        session_id = trace["session_id"]
        prompt = self._build_prompt(agent_key, task_input)
        harness_tools = config.get("harness_tools", [])

        logger.info("  ├─ Prompt: %.200s", prompt)
        logger.info("  ├─ Model: %s | Tools: %d | System prompt: %d chars",
                     config["bedrock_model_id"], len(harness_tools), len(config["system_prompt"]))

        trace["harness_arn"] = harness_arn
        trace["model"] = config["bedrock_model_id"]

        invoke_kwargs = {
            "harnessArn": harness_arn,
            "runtimeSessionId": session_id,
            "messages": [{"role": "user", "content": [{"text": prompt}]}],
            "model": {"bedrockModelConfig": {"modelId": config["bedrock_model_id"]}},
            "systemPrompt": [{"text": config["system_prompt"]}],
        }
        if harness_tools:
            invoke_kwargs["tools"] = harness_tools

        for turn in range(20):
            logger.info("  ├─ Turn %d | invoking harness...", turn)
            turn_start = time.monotonic()
            response = client.invoke_harness(**invoke_kwargs)
            turn_elapsed = time.monotonic() - turn_start
            logger.info("  │  invoke_harness returned in %.1fs", turn_elapsed)

            content_blocks, stop_reason = self._parse_stream(response)
            logger.info("  │  stop_reason=%s | content_blocks=%d", stop_reason, len(content_blocks))

            reasoning_texts = [b["text"] for b in content_blocks if b.get("type") == "text" and b.get("text", "").strip()]
            tool_calls_in_turn = [b for b in content_blocks if b.get("type") == "toolUse"]

            step_record = {
                "turn": turn,
                "stop_reason": stop_reason,
                "latency_s": round(turn_elapsed, 1),
                "reasoning": reasoning_texts,
                "tool_calls": [{"name": t["name"], "input": t.get("input", {})} for t in tool_calls_in_turn],
            }

            for rt in reasoning_texts:
                self._emit("thinking", text=rt)
                for line in rt.split("\n")[:10]:
                    if line.strip():
                        logger.info("  │  💭 %s", line.strip()[:200])

            if stop_reason == "end_turn":
                text = " ".join(reasoning_texts)
                self._emit("response", text=text[:1000], turn=turn)
                if not text.strip():
                    all_text = " ".join(b.get("text", "") for b in content_blocks if b.get("text"))
                    if all_text.strip():
                        text = all_text
                logger.info("  │  📝 FINAL RESPONSE | length=%d chars", len(text))
                logger.info("  │  📝 Preview: %.500s", text[:500])
                step_record["final_response_length"] = len(text)
                trace["steps"].append(step_record)
                try:
                    Path("/tmp/last_harness_response.txt").write_text(text)
                except Exception:
                    pass
                try:
                    parsed = json.loads(text)
                except json.JSONDecodeError:
                    parsed = self._extract_json_from_text(text)
                if parsed is not None and self._RESULT_KEYS & parsed.keys():
                    return parsed
                structured = self._structure_markdown_response(text, agent_key)
                if structured:
                    return structured
                return {"raw_response": text, "agent_key": agent_key}

            if stop_reason == "tool_use":
                assistant_content = []
                tool_results = []
                tool_executions = []

                trace["steps"].append(step_record)

                for block in content_blocks:
                    if block.get("type") == "toolUse":
                        self._emit("tool_call", name=block["name"], input=block.get("input", {}))
                        logger.info("  │  ┌─ TOOL CALL: %s | input_keys=%s",
                                     block["name"], list(block.get("input", {}).keys()))
                        logger.info("  │  │  input: %.300s", json.dumps(block.get("input", {}))[:300])
                        tool_start = time.monotonic()
                        tool_result_text = self._execute_tool(block["name"], block["input"])
                        tool_elapsed = time.monotonic() - tool_start
                        self._emit("tool_result", name=block["name"],
                                   result=tool_result_text[:500], latency=round(tool_elapsed, 1))
                        logger.info("  │  └─ TOOL DONE: %s | %.1fs | result_len=%d",
                                     block["name"], tool_elapsed, len(tool_result_text))
                        logger.info("  │     result preview: %.300s", tool_result_text[:300])
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
                                "content": [{"text": tool_result_text}],
                                "status": "success",
                            }
                        })
                        tool_executions.append({
                            "tool": block["name"],
                            "input": block.get("input", {}),
                            "result_preview": tool_result_text[:500],
                            "latency_s": round(tool_elapsed, 1),
                        })
                    elif block.get("type") == "text" and block.get("text"):
                        assistant_content.append({"text": block["text"]})

                trace["steps"].append({"turn": turn, "type": "tool_execution", "tools": tool_executions})

                invoke_kwargs = {
                    "harnessArn": harness_arn,
                    "runtimeSessionId": session_id,
                    "messages": [
                        {"role": "assistant", "content": assistant_content},
                        {"role": "user", "content": tool_results},
                    ],
                    "model": {"bedrockModelConfig": {"modelId": config["bedrock_model_id"]}},
                }
                if harness_tools:
                    invoke_kwargs["tools"] = harness_tools

        return {"error": "Max turns exceeded", "agent_key": agent_key}

    _RESULT_KEYS = {
        "risk_level", "regulatory_impact", "affected_assets", "affected_pipelines",
        "directly_affected", "transitively_affected", "confidence", "provenance",
        "overall_status", "test_execution", "test_selection", "test_results",
        "profiles", "quality_indicators", "entities", "entity_count",
        "gate_assessment", "checklist_result", "delivery_process", "blockers",
    }

    @classmethod
    def _extract_json_from_text(cls, text: str) -> dict | None:
        """Extract the agent result JSON from text that may contain prose and embedded snippets."""
        import re

        for pattern in [
            re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL),
            re.compile(r"```\s*(\{.*?\})\s*```", re.DOTALL),
        ]:
            for match in pattern.finditer(text):
                try:
                    candidate = json.loads(match.group(1))
                    if isinstance(candidate, dict) and cls._RESULT_KEYS & candidate.keys():
                        return candidate
                except json.JSONDecodeError:
                    continue

        depth = 0
        start = -1
        candidates = []
        for i, ch in enumerate(text):
            if ch == '{':
                if depth == 0:
                    start = i
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0 and start >= 0:
                    try:
                        obj = json.loads(text[start:i + 1])
                        if isinstance(obj, dict) and cls._RESULT_KEYS & obj.keys():
                            candidates.append(obj)
                    except json.JSONDecodeError:
                        pass
                    start = -1

        if candidates:
            candidates.sort(key=lambda c: len(cls._RESULT_KEYS & c.keys()), reverse=True)
            return candidates[0]

        brace_start = text.find("{")
        brace_end = text.rfind("}")
        if brace_start != -1 and brace_end > brace_start:
            try:
                return json.loads(text[brace_start:brace_end + 1])
            except json.JSONDecodeError:
                pass
        return None

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

    @staticmethod
    def _structure_markdown_response(text: str, agent_key: str) -> dict | None:
        """Extract structured fields from a rich markdown analysis response."""
        import re
        if not text or len(text) < 100:
            return None

        result: dict[str, Any] = {"agent_key": agent_key, "report": text}

        risk_match = re.search(r"Risk Level[^\n]*?\*{0,2}(CRITICAL|HIGH|MEDIUM|LOW)", text, re.IGNORECASE)
        if risk_match:
            result["risk_level"] = risk_match.group(1).upper()

        reg_match = re.search(r"Regulatory Impact[^\n]*?\*{0,2}(YES|NO|TRUE|FALSE)", text, re.IGNORECASE)
        if reg_match:
            val = reg_match.group(1).upper()
            result["regulatory_impact"] = val in ("YES", "TRUE")

        conf_match = re.search(r"Confidence[^\n]*?\*{0,2}(\d+)%", text)
        if conf_match:
            result["confidence"] = int(conf_match.group(1)) / 100

        affected_files = re.findall(r"`([^`]+\.(?:py|sql|yml|yaml|json))`", text)
        if affected_files:
            unique = list(dict.fromkeys(affected_files))
            result["directly_affected"] = unique[:20]
            result["transitively_affected"] = unique[20:]
            result["total_affected_count"] = len(unique)

        assets = set()
        for m in re.finditer(r"(?:table|model|asset|pipeline)[:\s]+`?([a-z_]+(?:\.[a-z_]+)?)`?", text, re.IGNORECASE):
            assets.add(m.group(1))
        result["affected_assets"] = list(assets)[:30]

        pipelines = set()
        for m in re.finditer(r"(?:pipeline|dag|job|ingestion)[:\s]+`?([a-z_]+(?:\.[a-z_]+)?)`?", text, re.IGNORECASE):
            pipelines.add(m.group(1))
        result["affected_pipelines"] = list(pipelines)[:10]

        gate_match = re.search(r"Gate[^\n]*?(READY|BLOCKED|PASSED|FAILED)", text, re.IGNORECASE)
        if gate_match:
            result["gate_status"] = gate_match.group(1).upper()

        status_match = re.search(r"Overall[^\n]*?(PASSED|FAILED|BLOCKED)", text, re.IGNORECASE)
        if status_match:
            result["overall_status"] = status_match.group(1).upper()

        tests_passed = re.search(r"(\d+)\s*(?:tests?\s+)?passed", text, re.IGNORECASE)
        tests_failed = re.search(r"(\d+)\s*(?:tests?\s+)?failed", text, re.IGNORECASE)
        if tests_passed or tests_failed:
            result["test_execution"] = {
                "summary": {
                    "passed": int(tests_passed.group(1)) if tests_passed else 0,
                    "failed": int(tests_failed.group(1)) if tests_failed else 0,
                },
                "overall_status": "FAILED" if (tests_failed and int(tests_failed.group(1)) > 0) else "PASSED",
            }

        blockers = []
        for m in re.finditer(r"(?:🔴|CRITICAL|BLOCKING)[:\s]+(.+?)(?:\n|$)", text):
            blockers.append({"severity": "BLOCKING", "detail": m.group(1).strip()[:200]})
        if blockers:
            result["gate_assessment"] = {
                "ready": False,
                "blockers": blockers[:10],
                "recommendation": "See full report for details",
            }

        return result

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
        self._emit("thinking", text="I need to scan the repository, build the dependency graph, then trace the impact of this change.")

        self._emit("tool_call", name="discover_repository", input={"repository_root": self.repository_root})
        trace["steps"].append({"skill": "discover_repository"})
        self._get_discovered_files()
        self._emit("tool_result", name="discover_repository",
                   result=f"Found {len(self._context.get('discovered_files', []))} files", latency=0.1)

        self._emit("thinking", text="Repository scanned. Now building the dependency graph from imports and references.")
        self._emit("tool_call", name="analyze_dependencies", input={})
        trace["steps"].append({"skill": "analyze_dependencies"})
        deps = self._get_dependencies()
        self._emit("tool_result", name="analyze_dependencies",
                   result=f"{deps.get('summary', {}).get('total_nodes', 0)} nodes, {deps.get('summary', {}).get('total_edges', 0)} edges", latency=0.1)

        self._emit("thinking", text="Dependency graph built. Now tracing impact through affected files.")
        self._emit("tool_call", name="analyze_impact", input={"change_description": task_input.get("change_description", "")})
        trace["steps"].append({"skill": "analyze_impact"})
        result = analyze_impact(
            task_input.get("change_description", ""),
            task_input.get("affected_files", []),
            deps.get("dependency_graph", {}),
            deps.get("nodes", []),
            self.project_seed,
        )
        self._emit("tool_result", name="analyze_impact",
                   result=f"Risk: {result.get('risk_level', '?')}, {result.get('total_affected_count', 0)} affected", latency=0.1)

        result["agent_key"] = "impact-analysis-agent"
        return result

    def _demo_regression(self, task_input: dict, trace: dict) -> dict:
        self._emit("thinking", text="I'll discover the repo, build dependencies, analyze impact, then select and run regression tests.")

        self._emit("tool_call", name="discover_repository", input={"repository_root": self.repository_root})
        trace["steps"].append({"skill": "discover_repository"})
        files = self._get_discovered_files()
        self._emit("tool_result", name="discover_repository",
                   result=f"Found {len(files)} files", latency=0.1)

        self._emit("thinking", text="Building dependency graph to understand what's connected.")
        self._emit("tool_call", name="analyze_dependencies", input={})
        trace["steps"].append({"skill": "analyze_dependencies"})
        deps = self._get_dependencies()
        self._emit("tool_result", name="analyze_dependencies",
                   result=f"{deps.get('summary', {}).get('total_nodes', 0)} nodes", latency=0.1)

        self._emit("thinking", text="Tracing impact of the change through the dependency graph.")
        self._emit("tool_call", name="analyze_impact", input={"change_description": task_input.get("change_description", "")})
        trace["steps"].append({"skill": "analyze_impact"})
        impact = analyze_impact(
            task_input.get("change_description", ""),
            task_input.get("affected_files", []),
            deps.get("dependency_graph", {}),
            deps.get("nodes", []),
            self.project_seed,
        )
        self._emit("tool_result", name="analyze_impact",
                   result=f"Risk: {impact.get('risk_level', '?')}, {impact.get('total_affected_count', 0)} affected", latency=0.1)

        self._emit("thinking", text="Impact identified. Selecting the minimal sufficient test set to cover affected entities.")
        self._emit("tool_call", name="select_tests", input={"affected_count": impact.get("total_affected_count", 0)})
        trace["steps"].append({"skill": "select_tests"})
        selection = select_tests(impact, files, self.test_scenarios)
        self._emit("tool_result", name="select_tests",
                   result=f"Selected {selection.get('total_selected', 0)} tests, coverage {selection.get('coverage_ratio', 0):.0%}", latency=0.1)

        self._emit("thinking", text=f"Running {selection.get('total_selected', 0)} selected tests against the change.")
        self._emit("tool_call", name="execute_tests", input={"test_count": selection.get("total_selected", 0)})
        trace["steps"].append({"skill": "execute_tests"})
        execution = execute_tests(
            selection["selected_tests"],
            task_input.get("change_id", ""),
            self.test_scenarios,
        )
        summary = execution.get("summary", {})
        self._emit("tool_result", name="execute_tests",
                   result=f"{summary.get('passed', 0)} passed, {summary.get('failed', 0)} failed → {execution.get('overall_status', '?')}", latency=0.1)

        return {
            "agent_key": "regression-agent",
            "impact": impact,
            "test_selection": selection,
            "test_execution": execution,
            "overall_status": execution["overall_status"],
        }

    def _demo_data_quality(self, task_input: dict, trace: dict) -> dict:
        self._emit("thinking", text="I'll scan the repository for data assets, then profile schemas and quality indicators.")

        self._emit("tool_call", name="discover_repository", input={"repository_root": self.repository_root})
        trace["steps"].append({"skill": "discover_repository"})
        files = self._get_discovered_files()
        self._emit("tool_result", name="discover_repository",
                   result=f"Found {len(files)} files", latency=0.1)

        self._emit("thinking", text="Profiling data assets — examining schemas, columns, and quality checks.")
        self._emit("tool_call", name="profile_data_assets", input={})
        trace["steps"].append({"skill": "profile_data_assets"})
        profiles = profile_data_assets(self.repository_root, files, self.project_seed)
        self._emit("tool_result", name="profile_data_assets",
                   result=f"{len(profiles.get('profiles', []))} assets profiled", latency=0.1)

        return {
            "agent_key": "data-quality-agent",
            **profiles,
        }

    def _demo_data_model(self, task_input: dict, trace: dict) -> dict:
        self._emit("thinking", text="I'll discover the repository, then profile data assets to build the logical model.")

        self._emit("tool_call", name="discover_repository", input={"repository_root": self.repository_root})
        trace["steps"].append({"skill": "discover_repository"})
        files = self._get_discovered_files()
        self._emit("tool_result", name="discover_repository",
                   result=f"Found {len(files)} files", latency=0.1)

        self._emit("tool_call", name="profile_data_assets", input={})
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
        self._emit("thinking", text="I need to discover the delivery process, validate checklists, assess gate readiness, and verify evidence.")

        self._emit("tool_call", name="discover_repository", input={})
        trace["steps"].append({"skill": "discover_repository"})
        files = self._get_discovered_files()
        self._emit("tool_result", name="discover_repository",
                   result=f"Found {len(files)} files", latency=0.1)

        self._emit("thinking", text="Discovering delivery process — phases, gates, and checklists.")
        self._emit("tool_call", name="discover_delivery_process", input={})
        trace["steps"].append({"skill": "discover_delivery_process"})
        process = discover_delivery_process(self.repository_root, files, self.project_seed)
        self._emit("tool_result", name="discover_delivery_process",
                   result=f"{len(process.get('phases', []))} phases found", latency=0.1)

        evidence = task_input.get("evidence", [])
        checklist_items = process.get("checklists", [])
        if not checklist_items:
            checklist_items = [
                {"name": "Requirements documented", "required": True},
                {"name": "Design reviewed", "required": True},
                {"name": "Tests executed", "required": True},
                {"name": "Security assessment complete", "required": True},
            ]

        self._emit("thinking", text=f"Validating {len(checklist_items)} checklist items against {len(evidence)} evidence items.")
        self._emit("tool_call", name="validate_checklist", input={"items": len(checklist_items)})
        trace["steps"].append({"skill": "validate_checklist"})
        checklist_result = validate_checklist(checklist_items, evidence)
        self._emit("tool_result", name="validate_checklist",
                   result=f"Validated {len(checklist_items)} items", latency=0.1)

        gate_name = task_input.get("gate_name", "Release Readiness Gate")
        self._emit("thinking", text=f"Assessing gate readiness for: {gate_name}")
        self._emit("tool_call", name="assess_gate_readiness", input={"gate": gate_name})
        trace["steps"].append({"skill": "assess_gate_readiness"})
        gate_result = assess_gate_readiness(
            gate_name,
            checklist_result,
            task_input.get("test_result"),
            task_input.get("impact_result"),
        )
        self._emit("tool_result", name="assess_gate_readiness",
                   result=f"Gate: {'READY' if gate_result.get('ready') else 'BLOCKED'}", latency=0.1)

        self._emit("tool_call", name="validate_evidence", input={"evidence_count": len(evidence)})
        trace["steps"].append({"skill": "validate_evidence"})
        ev_result = validate_evidence(evidence)
        self._emit("tool_result", name="validate_evidence",
                   result=f"Validated {len(evidence)} evidence items", latency=0.1)

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

        stream = response.get("stream", response)
        for event in stream:
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
                if not current_block.get("type"):
                    current_block["type"] = "toolUse" if "input_json" in current_block else "text"
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
