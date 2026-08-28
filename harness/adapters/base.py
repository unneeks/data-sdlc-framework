"""
Shared contract for anything the harness loop can call to "act" on a step.

`adapters/cli/gemini_adapter.py` and `adapters/cli/copilot_adapter.py` predate
this and have no shared interface between them; this Protocol is new and
scoped to the harness, not retrofitted onto those CLI-demo adapters.
"""
from typing import Any, Dict, Protocol

from domain.orchestration import AgentStep


class AgentAdapter(Protocol):
    def start(self, step: AgentStep) -> Dict[str, Any]:
        """Begin executing/delegating a step.

        Returns a status dict:
            {"status": "COMPLETED" | "AWAITING_CALLBACK" | "FAILED", "output": {...} | None}
        """
        ...
