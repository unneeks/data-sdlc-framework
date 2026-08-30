"""Strategy registry — the single place to look up a strategy by name."""

from __future__ import annotations

from typing import Any

from discovery.strategy import DiscoveryStrategy


STRATEGIES: dict[str, dict[str, Any]] = {
    "local": {
        "class": "discovery.strategies.local.LocalStrategy",
        "description": "Python loop with ExtractionClient for LLM extraction",
        "requires": ["ExtractionClient (Anthropic/Copilot/Replay)"],
    },
    "harness": {
        "class": "discovery.strategies.harness.HarnessStrategy",
        "description": "AgentCore Harness manages the loop; LLM IS the extractor",
        "requires": ["AWS credentials", "bedrock-agentcore access"],
    },
    "runtime": {
        "class": "discovery.strategies.runtime.RuntimeStrategy",
        "description": "Delegates to a deployed AgentCore Runtime agent",
        "requires": ["Deployed runtime ARN", "AWS credentials"],
    },
    "claude-code": {
        "class": "discovery.strategies.claude_code.ClaudeCodeStrategy",
        "description": "Claude Code walks the repo with native tools (Read, Bash, git)",
        "requires": ["Running inside Claude Code session"],
    },
}


def get_strategy(name: str, **kwargs) -> DiscoveryStrategy:
    """Instantiate a strategy by name with provided kwargs.

    Examples:
        get_strategy("local", client=my_client)
        get_strategy("harness", model_id="anthropic.claude-sonnet-4-5-20250514-v1:0")
        get_strategy("runtime", runtime_arn="arn:aws:bedrock-agentcore:...")
        get_strategy("claude-code", mode="batch")
    """
    if name not in STRATEGIES:
        available = ", ".join(STRATEGIES.keys())
        raise ValueError(f"Unknown strategy '{name}'. Available: {available}")

    entry = STRATEGIES[name]
    module_path, class_name = entry["class"].rsplit(".", 1)

    import importlib
    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)
    return cls(**kwargs)


def list_strategies() -> list[dict[str, str]]:
    """List all available strategies with descriptions."""
    return [
        {"name": name, "description": info["description"], "requires": info["requires"]}
        for name, info in STRATEGIES.items()
    ]
