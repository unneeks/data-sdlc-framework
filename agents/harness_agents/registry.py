"""Agent registry — delegates to the YAML-driven agent_configs.yaml and tool_registry.yaml.

Provides backward-compatible accessors used by the CLI and other modules.
All agent-specific configuration now lives in agents/agent_configs.yaml.
Convention agents from .agentcore/ are auto-discovered and merged.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

_AGENTS_DIR = Path(__file__).resolve().parent.parent
_PROJECT_ROOT = _AGENTS_DIR.parent

_agent_data = yaml.safe_load((_AGENTS_DIR / "agent_configs.yaml").read_text()) or {}
_model_map = _agent_data.get("model_map", {})


def _merge_convention_agents(configs: dict) -> dict:
    """Merge .agentcore/ convention agents into the config namespace.

    Convention instruction files always inject their system_prompt and
    user_prompt, even when the agent already exists in YAML config.
    """
    try:
        from agents.conventions.parser import discover_conventions
    except ImportError:
        return configs
    conv = discover_conventions(_PROJECT_ROOT)
    if not conv:
        return configs
    for agent in conv.agents:
        tool_names = []
        for skill_name in agent.skills_used:
            skill = conv.skills.get(skill_name)
            if skill:
                tool_names.extend(skill.required_tools)
            else:
                tool_names.append(skill_name)
        tool_names = list(dict.fromkeys(tool_names))

        if agent.key not in configs:
            configs[agent.key] = {
                "system_prompt": agent.system_prompt,
                "user_prompt": agent.user_prompt,
                "model": agent.model,
                "execution_model": agent.execution_model,
                "tools": tool_names,
                "source": "convention",
                "source_path": agent.source_path,
            }
        else:
            existing = configs[agent.key]
            if agent.system_prompt:
                existing["system_prompt"] = agent.system_prompt
            if agent.user_prompt:
                existing["user_prompt"] = agent.user_prompt
            existing["source"] = "convention"
            existing["source_path"] = agent.source_path
    return configs


AGENT_CONFIGS: dict[str, dict[str, Any]] = _merge_convention_agents(
    dict(_agent_data.get("agents", {}))
)


def _load_metamodel() -> dict:
    paths = [
        _PROJECT_ROOT / "apps" / "web" / "src" / "data" / "metamodel.json",
    ]
    for p in paths:
        if p.exists():
            return json.loads(p.read_text())
    return {}


_metamodel = _load_metamodel()


def get_agent_config(agent_key: str) -> dict[str, Any] | None:
    from agents.tools.definitions import get_tools_for_agent, get_tools_for_agent_harness

    config = AGENT_CONFIGS.get(agent_key)
    if not config:
        return None

    model_key = config.get("model", "claude-sonnet")
    bedrock_model_id = _model_map.get(model_key, model_key)

    tool_names = config.get("tools", [])
    if isinstance(tool_names, list) and tool_names and isinstance(tool_names[0], str):
        tools = get_tools_for_agent(agent_key)
        harness_tools = get_tools_for_agent_harness(agent_key)
    else:
        tools = tool_names
        harness_tools = []

    return {
        **config,
        "tools": tools,
        "harness_tools": harness_tools,
        "bedrock_model_id": bedrock_model_id,
    }


def list_agents() -> list[dict[str, str]]:
    agents = _metamodel.get("agents", {}).get("agents", [])

    yaml_keys = set(AGENT_CONFIGS.keys())
    result = []

    for a in agents:
        if a.get("execution_model") == "EXTERNAL_AGENT":
            continue
        result.append({
            "key": a["key"],
            "name": a["name"],
            "mission": a["mission"],
            "status": a.get("status", "CANDIDATE"),
            "has_harness": a["key"] in yaml_keys,
        })

    for key, cfg in AGENT_CONFIGS.items():
        if not any(r["key"] == key for r in result):
            result.append({
                "key": key,
                "name": cfg.get("name", key.replace("-", " ").title()),
                "mission": cfg.get("system_prompt", "")[:80] + "...",
                "status": "ACTIVE",
                "has_harness": True,
                "source": cfg.get("source", "yaml"),
            })

    return result


def get_skill_metadata() -> list[dict]:
    skills = _metamodel.get("skills", {}).get("skills", [])
    result = []
    for s in skills:
        result.append({
            "key": s["key"],
            "name": s["name"],
            "dependencies": s.get("dependencies", []),
            "required_tools": s.get("required_tools", []),
            "required_knowledge": s.get("required_knowledge", []),
            "risk_level": s.get("risk_level", "LOW"),
            "deterministic": s.get("deterministic", False),
            "outputs": s.get("outputs", {}),
            "discharges_checklist_items": s.get("discharges_checklist_items", []),
        })
    return result
