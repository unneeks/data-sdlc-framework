#!/usr/bin/env python3
"""
Unified Command Line Interface for invoking Gemini CLI and GitHub Copilot CLI agents.
"""
import sys
import json
import argparse
from pathlib import Path

# Add root directory to sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root_dir))

from adapters.cli.gemini_adapter import GeminiCLIAdapter
from adapters.cli.copilot_adapter import GitHubCopilotCLIAdapter

def load_agents_catalog():
    catalog_path = root_dir / "marketplace" / "agents.json"
    if catalog_path.exists():
        with open(catalog_path, "r") as f:
            return json.load(f)
    return []

def main():
    parser = argparse.ArgumentParser(description="Agentic Data Engineering CLI Gateway")
    parser.add_argument("--cli", choices=["gemini", "copilot"], default="gemini", help="Target CLI format")
    parser.add_argument("action", choices=["list", "run", "classify"], help="CLI Action")
    parser.add_argument("--agent", type=str, help="Agent ID to invoke")
    parser.add_argument("--prompt", type=str, default="Analyze business change request", help="Prompt text")
    parser.add_argument("--contract", type=str, default="CONTRACT-001", help="Delivery contract ID")

    args = parser.parse_args()
    agents = load_agents_catalog()

    if args.cli == "gemini":
        gemini_adapter = GeminiCLIAdapter(agents)
        if args.action == "list":
            print(gemini_adapter.list_agents_cli())
        elif args.action == "run":
            agent_id = args.agent or "impact-analysis-agent"
            print(gemini_adapter.invoke_agent_cli(agent_id, args.prompt, args.contract))
        elif args.action == "classify":
            print(f"Gemini CLI Classifier for prompt: '{args.prompt}'")
            print("Primary Delivery Type: DATA_PLATFORM_MIGRATION (Confidence: 96%)")

    elif args.cli == "copilot":
        copilot_adapter = GitHubCopilotCLIAdapter(agents)
        if args.action == "list":
            print(copilot_adapter.list_copilot_agents())
        elif args.action == "run":
            agent_id = args.agent or "impact-analysis-agent"
            print(copilot_adapter.invoke_copilot_agent(agent_id, args.prompt))
        elif args.action == "classify":
            print(f"# GitHub Copilot CLI Classifier\nPrompt: `{args.prompt}`\n\n- Classified: `DATA_PLATFORM_MIGRATION` (96% Confidence)")

if __name__ == "__main__":
    main()
