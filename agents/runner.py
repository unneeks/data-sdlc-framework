"""Generic Agent Runner — executes any agent via YAML-driven configuration.

All agent-specific logic is externalised to:
    agents/agent_configs.yaml  — agent definitions, demo chains, result keys
    agents/tool_registry.yaml  — tool-to-skill mapping and argument resolution

In REAL mode: invokes the AgentCore Harness with tool bridging.
In DEMO mode: executes the agent's demo_chain from config (no LLM required).

New agents (including .agentcore/ convention agents) work without code changes —
add a YAML entry or an .agentcore/ instruction file.
"""
from __future__ import annotations

import importlib
import json
import logging
import re
import time
import uuid
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_AGENTS_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _AGENTS_DIR.parent
AGENTCORE_DIR = ".agentcore"


# ── Config loading ─────────────────────────────────────────

def _load_yaml(path: Path) -> dict:
    if path.exists():
        return yaml.safe_load(path.read_text()) or {}
    return {}


def _load_tool_registry() -> dict:
    return _load_yaml(_AGENTS_DIR / "tool_registry.yaml").get("tools", {})


def _load_agent_configs() -> dict:
    data = _load_yaml(_AGENTS_DIR / "agent_configs.yaml")
    return data.get("agents", {}), data.get("model_map", {}), set(data.get("result_keys", []))


def _load_convention_agents() -> dict[str, dict]:
    """Merge .agentcore/ convention agents into the config namespace."""
    try:
        from agents.conventions.parser import discover_conventions
    except ImportError:
        return {}

    conv = discover_conventions(_PROJECT_ROOT)
    if not conv:
        return {}

    merged = {}
    for agent in conv.agents:
        tool_names = []
        for skill_name in agent.skills_used:
            skill = conv.skills.get(skill_name)
            if skill:
                tool_names.extend(skill.required_tools)
            else:
                tool_names.append(skill_name)
        tool_names = list(dict.fromkeys(tool_names))

        merged[agent.key] = {
            "system_prompt": agent.system_prompt,
            "user_prompt": agent.user_prompt,
            "model": agent.model,
            "execution_model": agent.execution_model,
            "tools": tool_names,
            "source": "convention",
            "source_path": agent.source_path,
        }
    return merged


def _load_harness_config() -> dict[str, str]:
    config_path = _PROJECT_ROOT / "agentcore_config.json"
    if config_path.exists():
        data = json.loads(config_path.read_text())
        return {
            agent_key: info["harness_arn"]
            for agent_key, info in data.get("harnesses", {}).items()
            if info.get("status") == "READY"
        }
    return {}


# ── Argument resolution ────────────────────────────────────

def _resolve_arg(spec: dict, tool_input: dict, task_input: dict, context: dict, cache: dict) -> Any:
    """Resolve a single argument using the spec from tool_registry.yaml."""
    source = spec.get("source", "input")
    default = spec.get("default")

    if source == "input":
        return tool_input.get(spec.get("key", spec.get("input_key", "")), default)

    if source == "context":
        return context.get(spec.get("key", ""), default)

    if source == "cache":
        return _deep_get(cache, spec.get("cache_key", ""), default)

    if source == "input_or_context":
        key = spec.get("key", "")
        return tool_input.get(key, context.get(key, default))

    if source == "input_or_cache":
        input_key = spec.get("input_key", spec.get("key", ""))
        val = tool_input.get(input_key)
        if val is not None:
            return val
        return _deep_get(cache, spec.get("cache_key", ""), default)

    if source == "input_or_task":
        key = spec.get("key", "")
        val = tool_input.get(key)
        if val is not None:
            return val
        return task_input.get(key, default)

    return default


def _deep_get(d: dict, dotted_key: str, default: Any = None) -> Any:
    """Get a value from a nested dict using dot-separated keys."""
    keys = dotted_key.split(".")
    current = d
    for k in keys:
        if isinstance(current, dict) and k in current:
            current = current[k]
        else:
            return default
    return current


def _format_template(template: str, result: dict) -> str:
    """Simple {key} and {key.subkey} template formatting against a result dict."""
    def replacer(m):
        path = m.group(1)
        val = _deep_get(result, path, "?")
        if isinstance(val, float):
            return f"{val:.0%}"
        return str(val)
    try:
        return re.sub(r"\{([a-zA-Z_.]+)\}", replacer, template)
    except Exception:
        return template


# ── Dynamic tool import ────────────────────────────────────

_IMPORT_CACHE: dict[str, Any] = {}


def _import_function(module_path: str, function_name: str):
    cache_key = f"{module_path}.{function_name}"
    if cache_key not in _IMPORT_CACHE:
        mod = importlib.import_module(module_path)
        _IMPORT_CACHE[cache_key] = getattr(mod, function_name)
    return _IMPORT_CACHE[cache_key]


# ── Generic tool definitions (Converse + Harness formats) ──

def _build_tool_definitions(tool_names: list[str], registry: dict) -> list[dict]:
    """Build Converse-format tool definitions from the registry."""
    from agents.tools.definitions import TOOL_DEFINITIONS
    name_set = set(tool_names)
    return [t for t in TOOL_DEFINITIONS if t["toolSpec"]["name"] in name_set]


def _build_harness_tools(tool_names: list[str], registry: dict) -> list[dict]:
    """Build Harness inline_function tool definitions from the registry."""
    from agents.tools.definitions import TOOL_DEFINITIONS
    name_set = set(tool_names)
    harness_tools = []
    for t in TOOL_DEFINITIONS:
        spec = t["toolSpec"]
        if spec["name"] in name_set:
            harness_tools.append({
                "type": "inline_function",
                "name": spec["name"],
                "config": {
                    "inlineFunction": {
                        "description": spec["description"],
                        "inputSchema": spec["inputSchema"]["json"],
                    },
                },
            })
    return harness_tools


# ── The generic runner ─────────────────────────────────────

class AgentRunner:
    """Runs any agent against a repository corpus, driven entirely by YAML config."""

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

        self._tool_registry = _load_tool_registry()
        agents_cfg, self._model_map, self._result_keys = _load_agent_configs()
        self._agent_configs = agents_cfg

        convention_agents = _load_convention_agents()
        for key, conv_cfg in convention_agents.items():
            if key not in self._agent_configs:
                self._agent_configs[key] = conv_cfg
            else:
                existing = self._agent_configs[key]
                if conv_cfg.get("system_prompt"):
                    existing["system_prompt"] = conv_cfg["system_prompt"]
                if conv_cfg.get("user_prompt"):
                    existing["user_prompt"] = conv_cfg["user_prompt"]
                existing["source"] = "convention"
                existing["source_path"] = conv_cfg.get("source_path", "")

    def _emit(self, event_type: str, **kwargs):
        if self.on_event:
            self.on_event(event_type, kwargs)

    def reload_harness_config(self):
        self._harness_arns = _load_harness_config()

    # ── Public interface ───────────────────────────────────

    def run_agent(self, agent_key: str, task_input: dict,
                  tools_override: list[str] | None = None) -> dict[str, Any]:
        """Run an agent.  Pass *tools_override* (a list of tool names)
        to restrict the tools available to the agent for this invocation."""
        logger.info("╔══ run_agent CALLED | agent=%s | mode=%s | input_keys=%s",
                     agent_key, self.mode, list(task_input.keys()))

        config = self._resolve_agent_config(agent_key)
        if not config:
            logger.error("║ Unknown agent: %s", agent_key)
            return {"error": f"Unknown agent: {agent_key}"}

        if tools_override is not None:
            config = {
                **config,
                "tools": _build_tool_definitions(tools_override, self._tool_registry),
                "harness_tools": _build_harness_tools(tools_override, self._tool_registry),
                "tool_names": tools_override,
            }

        logger.info("║ Config loaded | model=%s | tools=%d | source=%s",
                     config.get("bedrock_model_id", "?"),
                     len(config.get("tools", [])),
                     config.get("source", "yaml"))

        # Validate human prompt upfront so it appears in traces
        human_prompt = task_input.get("human_prompt", "") or task_input.get("prompt", "")
        prompt_validation = self._validate_human_prompt(human_prompt, agent_key, config)

        session_id = str(uuid.uuid4())
        trace = {
            "agent_key": agent_key,
            "session_id": session_id,
            "start_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "mode": self.mode,
            "prompt_validation": {
                "human_prompt_present": bool(human_prompt),
                "valid": prompt_validation["valid"],
                "warnings": prompt_validation["warnings"],
                "rejected_reason": prompt_validation["rejected_reason"],
            },
            "steps": [],
        }

        if not prompt_validation["valid"]:
            logger.warning("║ Human prompt REJECTED for %s: %s",
                           agent_key, prompt_validation["rejected_reason"])

        start = time.monotonic()
        try:
            if self.mode == "REAL":
                result = self._run_harness(agent_key, config, task_input, trace)
            else:
                result = self._run_demo(agent_key, config, task_input, trace)

            elapsed = time.monotonic() - start
            trace["end_time"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            trace["status"] = "COMPLETED"
            trace["result_summary"] = _summarize(result)
            self._traces.append(trace)
            logger.info("╚══ run_agent COMPLETED | agent=%s | %.1fs", agent_key, elapsed)
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

    def get_traces(self) -> list[dict]:
        return list(reversed(self._traces))

    def build_context(self) -> dict[str, Any]:
        self._ensure_cache("discovered_files")
        self._ensure_cache("dependencies")
        profiles = self._execute_tool_by_name(
            "profile_data_assets", {}, {}, use_cache=True,
        )
        process = self._execute_tool_by_name(
            "discover_delivery_process", {}, {}, use_cache=True,
        )
        return {
            "discovery": self._context.get("discovered_files_result", {}),
            "dependencies": self._context.get("dependencies", {}),
            "profiles": profiles,
            "delivery_process": process,
            "project_seed": self.project_seed,
        }

    # ── Config resolution ──────────────────────────────────

    def _resolve_agent_config(self, agent_key: str) -> dict | None:
        cfg = self._agent_configs.get(agent_key)
        if not cfg:
            cfg = self._detect_convention_agent(agent_key)
            if cfg:
                self._agent_configs[agent_key] = cfg
            else:
                return None

        if cfg.get("source") == "convention":
            source_path = cfg.get("source_path", "")
            if source_path:
                self._reload_convention_instructions(agent_key, source_path, cfg)
            logger.info("║ Using convention instructions from %s", source_path or ".agentcore/")

        model_key = cfg.get("model", "claude-sonnet")
        bedrock_model_id = self._model_map.get(model_key, model_key)
        tool_names = cfg.get("tools", [])

        return {
            **cfg,
            "bedrock_model_id": bedrock_model_id,
            "tools": _build_tool_definitions(tool_names, self._tool_registry),
            "harness_tools": _build_harness_tools(tool_names, self._tool_registry),
            "tool_names": tool_names,
        }

    def _detect_convention_agent(self, agent_key: str) -> dict | None:
        """Check if a convention file exists for this agent at runtime."""
        instruction_file = _PROJECT_ROOT / AGENTCORE_DIR / f"{agent_key}.agent.instructions.md"
        if not instruction_file.exists():
            return None

        try:
            from agents.conventions.parser import parse_agent_instructions
            agent = parse_agent_instructions(instruction_file)
        except Exception as e:
            logger.warning("Failed to parse convention file %s: %s", instruction_file, e)
            return None

        try:
            from agents.conventions.parser import discover_conventions
            conv = discover_conventions(_PROJECT_ROOT)
            tool_names = []
            if conv:
                for skill_name in agent.skills_used:
                    skill = conv.skills.get(skill_name)
                    if skill:
                        tool_names.extend(skill.required_tools)
                    else:
                        tool_names.append(skill_name)
            tool_names = list(dict.fromkeys(tool_names))
        except Exception:
            tool_names = []

        logger.info("║ Auto-detected convention agent: %s from %s", agent_key, instruction_file)
        return {
            "system_prompt": agent.system_prompt,
            "user_prompt": agent.user_prompt,
            "model": agent.model,
            "execution_model": agent.execution_model,
            "tools": tool_names,
            "source": "convention",
            "source_path": str(instruction_file),
        }

    def _reload_convention_instructions(self, agent_key: str, source_path: str, cfg: dict):
        """Re-read the convention file to pick up live edits."""
        p = Path(source_path)
        if not p.exists():
            return
        try:
            from agents.conventions.parser import parse_agent_instructions
            agent = parse_agent_instructions(p)
            cfg["system_prompt"] = agent.system_prompt
            cfg["user_prompt"] = agent.user_prompt
        except Exception as e:
            logger.warning("Failed to reload convention file %s: %s", source_path, e)

    def get_agent_config(self, agent_key: str) -> dict | None:
        return self._resolve_agent_config(agent_key)

    def list_agents(self) -> list[str]:
        return sorted(self._agent_configs.keys())

    # ── DEMO mode: generic skill chain executor ────────────

    def _run_demo(self, agent_key: str, config: dict, task_input: dict, trace: dict) -> dict:
        chain = config.get("demo_chain", [])
        if not chain:
            return {"error": f"No demo_chain configured for {agent_key}", "agent_key": agent_key}

        demo_cache: dict[str, Any] = {}
        final_result: dict[str, Any] = {"agent_key": agent_key}

        for step in chain:
            tool_name = step["tool"]

            thinking = step.get("emit_thinking", "")
            if thinking:
                self._emit("thinking", text=thinking)

            self._emit("tool_call", name=tool_name, input={})
            trace["steps"].append({"skill": tool_name})

            tool_result = self._execute_tool_by_name(tool_name, {}, task_input, use_cache=True)

            cache_as = step.get("cache_as")
            if cache_as:
                demo_cache[cache_as] = tool_result
                self._context[cache_as] = tool_result

            store_field = step.get("store_field")
            store_key = step.get("store_key")
            if store_field and store_key:
                if isinstance(tool_result, dict) and store_field in tool_result:
                    self._context[store_key] = tool_result[store_field]

            result_text = step.get("emit_result", "Done")
            if isinstance(tool_result, dict):
                result_text = _format_template(result_text, tool_result)
            self._emit("tool_result", name=tool_name, result=result_text, latency=0.1)

            if step.get("merge_result") and isinstance(tool_result, dict):
                final_result.update(tool_result)

        compose = config.get("demo_result_compose")
        if compose:
            for key, ref in compose.items():
                if isinstance(ref, str) and ref.startswith("{cache."):
                    cache_path = ref[7:-1]
                    final_result[key] = _deep_get(demo_cache, cache_path, _deep_get(self._context, cache_path))
                else:
                    final_result[key] = ref

        post = config.get("demo_post_process")
        if post:
            final_result = self._demo_post_process(post, final_result, demo_cache)

        return final_result

    def _demo_post_process(self, name: str, result: dict, cache: dict) -> dict:
        """Pluggable post-processors for demo mode (kept minimal)."""
        if name == "build_entity_model":
            profiles = cache.get("profiles", {})
            profile_list = profiles.get("profiles", []) if isinstance(profiles, dict) else profiles
            entities = []
            for p in (profile_list if isinstance(profile_list, list) else []):
                entities.append({
                    "name": p.get("asset_name", ""),
                    "domain": p.get("domain", "Unknown"),
                    "columns": p.get("columns", []),
                    "source": p.get("source", ""),
                    "provenance": "OBSERVED",
                })
            result["entities"] = entities
            result["entity_count"] = len(entities)
            result["profiles"] = profiles
        return result

    # ── REAL mode: AgentCore Harness ───────────────────────

    def _run_harness(self, agent_key: str, config: dict, task_input: dict, trace: dict) -> dict:
        import boto3

        harness_arn = self._harness_arns.get(agent_key)
        if not harness_arn:
            raise RuntimeError(
                f"No harness ARN configured for {agent_key}. "
                f"Run setup_agentcore.py first or check agentcore_config.json."
            )

        region = "us-west-2"
        client = boto3.client("bedrock-agentcore", region_name=region)

        session_id = trace["session_id"]

        # Layer 1: System prompt — convention instructions are the immutable identity
        system_prompt = config.get("system_prompt", "")
        if not system_prompt:
            system_prompt = f"You are the {agent_key} agent."

        # Layers 2+3: Convention user prompt + validated human prompt
        prompt = self._build_prompt(agent_key, config, task_input)

        harness_tools = config.get("harness_tools", [])

        trace["harness_arn"] = harness_arn
        trace["model"] = config["bedrock_model_id"]
        trace["prompt_layers"] = {
            "system_prompt_length": len(system_prompt),
            "convention_user_prompt_length": len(config.get("user_prompt", "")),
            "human_prompt_present": bool(task_input.get("human_prompt") or task_input.get("prompt")),
        }

        invoke_kwargs = {
            "harnessArn": harness_arn,
            "runtimeSessionId": session_id,
            "messages": [{"role": "user", "content": [{"text": prompt}]}],
            "model": {"bedrockModelConfig": {"modelId": config["bedrock_model_id"]}},
            "systemPrompt": [{"text": system_prompt}],
        }
        if harness_tools:
            invoke_kwargs["tools"] = harness_tools

        for turn in range(20):
            logger.info("  ├─ Turn %d | invoking harness...", turn)
            turn_start = time.monotonic()
            response = client.invoke_harness(**invoke_kwargs)
            turn_elapsed = time.monotonic() - turn_start

            content_blocks, stop_reason = self._parse_stream(response)

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

            if stop_reason == "end_turn":
                text = " ".join(reasoning_texts)
                self._emit("response", text=text[:1000], turn=turn)
                if not text.strip():
                    all_text = " ".join(b.get("text", "") for b in content_blocks if b.get("text"))
                    if all_text.strip():
                        text = all_text
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
                if parsed is not None and self._result_keys & parsed.keys():
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
                        tool_start = time.monotonic()
                        tool_result_text = self._execute_tool(block["name"], block["input"], task_input)
                        tool_elapsed = time.monotonic() - tool_start
                        self._emit("tool_result", name=block["name"],
                                   result=tool_result_text[:500], latency=round(tool_elapsed, 1))
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

    # ── Generic tool dispatch ──────────────────────────────

    def _execute_tool(self, tool_name: str, tool_input: dict, task_input: dict | None = None) -> str:
        result = self._execute_tool_by_name(tool_name, tool_input, task_input or {})
        return json.dumps(result, default=str)

    def _execute_tool_by_name(
        self, tool_name: str, tool_input: dict, task_input: dict, use_cache: bool = False,
    ) -> Any:
        """Dispatch a tool call using the YAML tool registry."""
        spec = self._tool_registry.get(tool_name)
        if not spec:
            return {"error": f"Unknown tool: {tool_name}"}

        context = {
            "repository_root": self.repository_root,
            "project_seed": self.project_seed,
            "test_scenarios": self.test_scenarios,
        }

        self._ensure_cache("discovered_files")
        if tool_name in ("analyze_dependencies", "analyze_impact", "select_tests"):
            self._ensure_cache("dependencies")

        args_spec = spec.get("args", {})
        resolved_args = {}
        for arg_name, arg_spec in args_spec.items():
            resolved_args[arg_name] = _resolve_arg(
                arg_spec, tool_input, task_input, context, self._context,
            )

        fn = _import_function(spec["module"], spec["function"])
        return fn(**resolved_args)

    def _ensure_cache(self, key: str):
        """Lazily populate cache entries that other tools depend on."""
        if key == "discovered_files" and "discovered_files" not in self._context:
            from agents.skills.repository_discovery import discover_repository
            result = discover_repository(self.repository_root)
            self._context["discovered_files"] = result.get("files", [])
            self._context["discovered_files_result"] = result
        elif key == "dependencies" and "dependencies" not in self._context:
            self._ensure_cache("discovered_files")
            from agents.skills.dependency_analysis import analyze_dependencies
            self._context["dependencies"] = analyze_dependencies(
                self.repository_root, self._context["discovered_files"],
            )

    # ── Prompt layering ──────────────────────────────────────
    #
    # Override order (highest → lowest priority for shaping the message):
    #   Layer 1 — System prompt      (from convention .agent.instructions.md)
    #   Layer 2 — Convention user prompt (from convention .agent.instructions.md)
    #   Layer 3 — Human user prompt  (submitted via API task_input)
    #
    # The human prompt is validated before inclusion: it must not attempt
    # to override the system prompt or change the agent's fundamental
    # objective.

    # Patterns that signal an attempt to override agent identity/objective
    _PROMPT_OVERRIDE_PATTERNS = [
        re.compile(r"ignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions?", re.I),
        re.compile(r"forget\s+(?:all\s+)?(?:your|previous|prior)\s+(?:instructions?|rules?|prompts?)", re.I),
        re.compile(r"you\s+are\s+(?:now|no\s+longer)\s+", re.I),
        re.compile(r"your\s+(?:new\s+)?(?:role|mission|objective|purpose)\s+is", re.I),
        re.compile(r"disregard\s+(?:all\s+)?(?:previous|prior|system)", re.I),
        re.compile(r"override\s+(?:the\s+)?(?:system|original)\s+prompt", re.I),
        re.compile(r"act\s+as\s+(?:a\s+)?(?:different|new)\s+(?:agent|assistant|role)", re.I),
        re.compile(r"do\s+not\s+follow\s+(?:your|the)\s+(?:system|original)\s+(?:prompt|instructions?)", re.I),
        re.compile(r"pretend\s+(?:you\s+are|to\s+be)\s+", re.I),
        re.compile(r"new\s+system\s*(?:prompt|instructions?)\s*:", re.I),
    ]

    # Keywords that, when present, signal the human is trying to redefine scope
    _SCOPE_OVERRIDE_KEYWORDS = [
        "system prompt", "system instructions", "meta-prompt", "jailbreak",
        "prompt injection", "DAN", "developer mode",
    ]

    def _validate_human_prompt(self, human_text: str, agent_key: str, config: dict) -> dict:
        """Validate the human-submitted prompt before applying.

        Returns:
            {
                "valid": bool,
                "sanitized": str,         # the text to use (may be original or stripped)
                "warnings": list[str],    # non-blocking concerns
                "rejected_reason": str,   # if valid=False, why it was rejected
            }
        """
        if not human_text or not human_text.strip():
            return {"valid": True, "sanitized": "", "warnings": [], "rejected_reason": ""}

        warnings: list[str] = []
        text = human_text.strip()

        # Check for prompt-override patterns
        for pattern in self._PROMPT_OVERRIDE_PATTERNS:
            match = pattern.search(text)
            if match:
                reason = f"Human prompt contains override pattern: '{match.group()}'"
                logger.warning("║ REJECTED human prompt for %s: %s", agent_key, reason)
                return {
                    "valid": False,
                    "sanitized": "",
                    "warnings": [],
                    "rejected_reason": reason,
                }

        # Check for scope-override keywords (case-insensitive)
        text_lower = text.lower()
        for keyword in self._SCOPE_OVERRIDE_KEYWORDS:
            if keyword.lower() in text_lower:
                reason = f"Human prompt references restricted concept: '{keyword}'"
                logger.warning("║ REJECTED human prompt for %s: %s", agent_key, reason)
                return {
                    "valid": False,
                    "sanitized": "",
                    "warnings": [],
                    "rejected_reason": reason,
                }

        # Check length — excessively long human prompts may be trying to
        # overwhelm the convention instructions
        system_prompt = config.get("system_prompt", "")
        convention_user_prompt = config.get("user_prompt", "")
        convention_length = len(system_prompt) + len(convention_user_prompt)
        if convention_length > 0 and len(text) > convention_length * 3:
            warnings.append(
                f"Human prompt ({len(text)} chars) is significantly longer than "
                f"convention instructions ({convention_length} chars) — may dilute agent focus"
            )

        # Check for embedded role/system markers that mimic prompt structure
        if re.search(r"(?m)^##\s*System\s*Prompt", text, re.I):
            return {
                "valid": False,
                "sanitized": "",
                "warnings": [],
                "rejected_reason": "Human prompt contains embedded system prompt section header",
            }
        if text.startswith("---") and "\n---" in text[3:]:
            warnings.append("Human prompt contains YAML frontmatter-like markers — stripped")
            _, text = text.split("---", 2)[0], text.split("---", 2)[-1].strip()

        for w in warnings:
            logger.info("║ Human prompt warning for %s: %s", agent_key, w)

        return {"valid": True, "sanitized": text, "warnings": warnings, "rejected_reason": ""}

    def _build_prompt(self, agent_key: str, config: dict, task_input: dict) -> str:
        """Build the final user message applying the three-layer override order.

        Layer 1 (system prompt) is handled separately in systemPrompt.
        This method composes Layer 2 (convention user prompt) + Layer 3 (human input).
        """
        convention_user_prompt = config.get("user_prompt", "")

        # Extract the human-submitted prompt from task_input
        human_prompt = task_input.get("human_prompt", "") or task_input.get("prompt", "")

        # Validate the human prompt before applying
        human_validation = self._validate_human_prompt(human_prompt, agent_key, config)

        parts: list[str] = []

        # Layer 2: Convention user prompt (always applied when present)
        if convention_user_prompt:
            parts.append(convention_user_prompt)
            parts.append(f"\nRepository: {self.repository_root}")
        else:
            parts.append(f"Execute the {agent_key} workflow against repository: {self.repository_root}")

        # Structured task parameters (always included)
        if task_input.get("change_description"):
            parts.append(f"\nChange: {task_input['change_description']}")
        if task_input.get("affected_files"):
            parts.append(f"\nAffected files: {json.dumps(task_input['affected_files'])}")
        if task_input.get("change_id"):
            parts.append(f"\nChange ID: {task_input['change_id']}")
        if task_input.get("gate_name"):
            parts.append(f"\nGate: {task_input['gate_name']}")

        # Layer 3: Human user prompt (validated — sandboxed in a clearly marked section)
        if human_validation["valid"] and human_validation["sanitized"]:
            parts.append("\n--- Additional context from user ---")
            parts.append(human_validation["sanitized"])
            parts.append("--- End of user context ---")
            if human_validation["warnings"]:
                self._emit("prompt_warning", warnings=human_validation["warnings"])
        elif not human_validation["valid"]:
            parts.append(
                f"\n[Note: A user-submitted prompt was rejected because it attempted "
                f"to modify agent behaviour. Reason: {human_validation['rejected_reason']}]"
            )
            self._emit("prompt_rejected", reason=human_validation["rejected_reason"])

        return "\n".join(parts)

    # ── Response parsing ───────────────────────────────────

    def _extract_json_from_text(self, text: str) -> dict | None:
        for pattern in [
            re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL),
            re.compile(r"```\s*(\{.*?\})\s*```", re.DOTALL),
        ]:
            for match in pattern.finditer(text):
                try:
                    candidate = json.loads(match.group(1))
                    if isinstance(candidate, dict) and self._result_keys & candidate.keys():
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
                        if isinstance(obj, dict) and self._result_keys & obj.keys():
                            candidates.append(obj)
                    except json.JSONDecodeError:
                        pass
                    start = -1

        if candidates:
            candidates.sort(key=lambda c: len(self._result_keys & c.keys()), reverse=True)
            return candidates[0]

        brace_start = text.find("{")
        brace_end = text.rfind("}")
        if brace_start != -1 and brace_end > brace_start:
            try:
                return json.loads(text[brace_start:brace_end + 1])
            except json.JSONDecodeError:
                pass
        return None

    @staticmethod
    def _structure_markdown_response(text: str, agent_key: str) -> dict | None:
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

    # ── Stream parsing ─────────────────────────────────────

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


def _summarize(result: dict) -> dict:
    summary = {}
    for key in ["overall_status", "risk_level", "total_affected_count", "entity_count",
                 "agent_key", "coverage_ratio"]:
        if key in result:
            summary[key] = result[key]
    if "test_execution" in result:
        summary["test_summary"] = result["test_execution"].get("summary", {})
    if "gate_assessment" in result:
        summary["gate_ready"] = result["gate_assessment"].get("ready", False)
    return summary
