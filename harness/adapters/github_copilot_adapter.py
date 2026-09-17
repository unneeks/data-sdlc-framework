"""GitHub Copilot backend adapter.

Wraps the existing `GitHubCopilotCLIAdapter` (adapters/cli/copilot_adapter.py)
behind the same shape LiveAgentSession expects from an AgentCore turn: given
a prompt, produce assistant text. GitHub Copilot CLI agents don't expose a
tool-use/toolResult protocol the way AgentCore Harness does, so a Copilot
turn always ends the session in one turn — there is nothing to bridge a
client tool call into. Kept as a distinct backend (domain.orchestration.
AgentBackend.GITHUB_COPILOT) rather than folded into ServerRunAdapter's
Bedrock-specific `start()` shape, since the two APIs are not compatible.
"""
from __future__ import annotations

from typing import Any, Dict, List

from adapters.cli.copilot_adapter import GitHubCopilotCLIAdapter


class GithubCopilotBackend:
    def __init__(self, agents_catalog: List[Dict[str, Any]]) -> None:
        self._cli = GitHubCopilotCLIAdapter(agents_catalog)

    def list_agents(self) -> List[str]:
        return list(self._cli.agents.keys())

    def run_turn(self, agent_id: str, prompt: str) -> Dict[str, Any]:
        """Single-turn invocation — GitHub Copilot CLI agents have no
        tool-use loop of their own, so this always terminates the session."""
        text = self._cli.invoke_copilot_agent(agent_id, prompt)
        if text.startswith("❌"):
            return {"status": "FAILED", "text": text}
        return {"status": "COMPLETED", "text": text}
