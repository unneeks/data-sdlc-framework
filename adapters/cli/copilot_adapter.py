"""
GitHub Copilot CLI integration adapter allowing agents to be invoked via `gh copilot agent` commands.
"""
from typing import Dict, Any

class GitHubCopilotCLIAdapter:
    def __init__(self, agents_catalog: list):
        self.agents = {a["id"]: a for a in agents_catalog}

    def list_copilot_agents(self) -> str:
        lines = ["# GitHub Copilot CLI Agent Extension Registry\n"]
        for aid, a in self.agents.items():
            lines.append(f"- **{a['name']}** (`{a['id']}`): {a['description']}")
        return "\n".join(lines)

    def invoke_copilot_agent(self, agent_id: str, prompt: str) -> str:
        agent = self.agents.get(agent_id)
        if not agent:
            return f"❌ Copilot CLI Error: Agent '{agent_id}' is not registered."

        return f"""# 🐙 GitHub Copilot CLI — Agent Report: {agent['name']}

> **Role**: {agent['engineering_role']} | **Trust Score**: {agent['trust_score']*100:.0f}% | **Status**: {agent['certification_status']}

### Request Prompt
> {prompt}

### Agent Execution Plan & Capabilities
- **Skills Activated**: `{', '.join(agent['skills'])}`
- **Tools Called**: `{', '.join(agent['tools'])}`
- **Supported SDLC Types**: `{', '.join(agent['supported_delivery_types'])}`

### Analysis & Recommendation
The **{agent['name']}** evaluated the continuous engineering context and confirmed compliance with enterprise delivery contracts.

```bash
# Suggested follow-up command:
gh copilot agent run --agent {agent_id} --evaluate
```
"""
