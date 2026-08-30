"""Repository discovery — walks a codebase and corpus to populate a knowledge graph.

Supports multiple orchestration strategies (local Python, AgentCore Harness,
AgentCore Runtime, Claude Code) while sharing the same deterministic tools.
The strategy is swappable; the tools are constant; the skill is the strategy's
sub-variable.
"""

from discovery.strategy import DiscoveryConfig, DiscoveryStrategy
from discovery.result import DiscoveryReport, DiscoveryFailure, DiscoverySkip
from discovery.registry import STRATEGIES, get_strategy

__all__ = [
    "DiscoveryConfig",
    "DiscoveryFailure",
    "DiscoveryReport",
    "DiscoverySkip",
    "DiscoveryStrategy",
    "STRATEGIES",
    "get_strategy",
]
