"""
DEMO-mode adapter: used for every execution kind whenever SystemMode.DEMO is
active. Returns deterministic canned output with zero network I/O, matching
the rest of the app's demo-mode behavior (domain/graph.py, domain/evaluation.py).
"""
from typing import Any, Dict

from domain.orchestration import AgentStep


class DemoAdapter:
    def start(self, step: AgentStep) -> Dict[str, Any]:
        return {
            "status": "COMPLETED",
            "output": {
                "demo": True,
                "agent_id": step.agent_id,
                "task_id": step.task_id,
                "message": f"[DEMO] step {step.id} completed for agent {step.agent_id}",
            },
        }
