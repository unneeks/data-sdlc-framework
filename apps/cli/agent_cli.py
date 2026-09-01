#!/usr/bin/env python3
"""
Interactive CLI for Data SDLC Framework agents.

Any text you type is a prompt sent to the active agent.
Slash commands control the session:

    /agents          List available agents
    /skills          List metamodel skills
    /select          Pick a different agent
    /workflow        Run full SDLC workflow
    /traces          Show execution traces
    /mode            Toggle DEMO / REAL
    /model           Show current model info
    /verbose         Toggle verbose logging
    /clear           Clear screen
    /help            Show commands
    /quit            Exit

Direct invocation:
    python agent_cli.py                                    # Interactive
    python agent_cli.py agents                             # List agents
    python agent_cli.py skills                             # List skills
    python agent_cli.py run <agent-key> --change "..."     # One-shot run
    python agent_cli.py workflow --scenario ATLAS-CR-003   # Full workflow
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import readline
import sys
import time
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root_dir))

from agents.runner import AgentRunner
from agents.workflow import WorkflowRunner
from agents.harness_agents.registry import AGENT_CONFIGS, list_agents, get_agent_config, get_skill_metadata

BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
MAGENTA = "\033[35m"
BLUE = "\033[34m"

_test_data_root = str(root_dir / "test-data")

_project_seed_path = root_dir / "test-data" / "atlas_project_seed.json"
_project_seed = json.loads(_project_seed_path.read_text()) if _project_seed_path.exists() else {}

_scenarios_path = root_dir / "test-data" / "atlas_test_scenarios.json"
_scenarios = json.loads(_scenarios_path.read_text()) if _scenarios_path.exists() else {}


def _pick(prompt: str, options: list[dict], key_field: str = "key", display_field: str = "name") -> dict | None:
    print()
    for i, opt in enumerate(options, 1):
        label = opt.get(display_field, opt.get(key_field, str(i)))
        extra = opt.get("mission", opt.get("title", ""))
        if extra:
            print(f"  {CYAN}{i}{RESET}) {BOLD}{label}{RESET} {DIM}— {extra}{RESET}")
        else:
            print(f"  {CYAN}{i}{RESET}) {BOLD}{label}{RESET}")
    print()
    while True:
        choice = input(f"{prompt} [1-{len(options)}]: ").strip()
        if choice.lower() in ("q", "quit", "exit", ""):
            return None
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                return options[idx]
        except ValueError:
            for opt in options:
                if choice == opt.get(key_field):
                    return opt
        print(f"  {RED}Invalid choice. Try again or 'q' to cancel.{RESET}")


def _print_result(result: dict, indent: int = 0):
    prefix = "  " * indent
    if "error" in result:
        print(f"{prefix}{RED}ERROR: {result['error']}{RESET}")
        return
    for key, value in result.items():
        if key in ("raw_response", "report"):
            print(f"{prefix}{BOLD}{key}:{RESET}")
            for line in str(value)[:2000].split("\n"):
                print(f"{prefix}  {line}")
            if len(str(value)) > 2000:
                print(f"{prefix}  {DIM}... ({len(str(value))} chars total){RESET}")
        elif isinstance(value, dict):
            print(f"{prefix}{BOLD}{key}:{RESET}")
            _print_result(value, indent + 1)
        elif isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
            print(f"{prefix}{BOLD}{key}:{RESET} ({len(value)} items)")
            for item in value[:5]:
                print(f"{prefix}  - {json.dumps(item, default=str)[:200]}")
            if len(value) > 5:
                print(f"{prefix}  {DIM}... and {len(value) - 5} more{RESET}")
        elif isinstance(value, list):
            print(f"{prefix}{BOLD}{key}:{RESET} {value[:10]}")
        else:
            color = ""
            if key == "risk_level":
                color = RED if value in ("HIGH", "CRITICAL") else YELLOW if value == "MEDIUM" else GREEN
            elif key == "overall_status":
                color = GREEN if value == "PASSED" else RED
            elif key == "regulatory_impact" and value:
                color = RED
            print(f"{prefix}{BOLD}{key}:{RESET} {color}{value}{RESET}")


def _print_trace(traces: list[dict]):
    if not traces:
        return
    trace = traces[0]
    print(f"\n{DIM}{'─'*50}{RESET}")
    print(f"  {DIM}session {trace['session_id'][:12]}... | {trace['mode']} | {trace['status']} | {len(trace['steps'])} steps{RESET}")
    for step in trace["steps"]:
        if "reasoning" in step:
            for r in step["reasoning"][:3]:
                print(f"  {DIM}💭 {r[:150]}{RESET}")
        if "tools" in step:
            for t in step["tools"]:
                print(f"  {CYAN}🔧 {t['name']}{RESET}")
        if step.get("type") == "tool_execution":
            for t in step.get("tools", []):
                print(f"  {CYAN}🔧 {t['tool']}{RESET} ({t.get('latency_s', '?')}s)")


# ── Slash command handlers ──────────────────────────────────

def cmd_agents():
    print(f"\n{BOLD}  Agents{RESET}")
    print(f"  {'─'*50}\n")
    agents = list_agents()
    if not agents:
        agents = [{"key": k, "name": k, "mission": v["system_prompt"][:80] + "...", "has_harness": True}
                  for k, v in AGENT_CONFIGS.items()]
    for a in agents:
        badge = f"{GREEN}●{RESET}" if a.get("has_harness") else f"{RED}○{RESET}"
        print(f"  {badge} {CYAN}{a['key']}{RESET}")
        if a.get("mission"):
            print(f"    {DIM}{a['mission'][:100]}{RESET}")
    print()
    return agents


def cmd_skills():
    print(f"\n{BOLD}  Skills{RESET}")
    print(f"  {'─'*50}\n")
    skills = get_skill_metadata()
    if not skills:
        print(f"  {DIM}No skills found in metamodel.{RESET}")
        return skills
    for s in skills:
        risk_color = RED if s["risk_level"] in ("HIGH", "CRITICAL") else YELLOW if s["risk_level"] == "MEDIUM" else GREEN
        det = f"{GREEN}det{RESET}" if s.get("deterministic") else f"{YELLOW}non-det{RESET}"
        print(f"  {CYAN}{s['key']}{RESET}  {risk_color}[{s['risk_level']}]{RESET} {det}")
        if s.get("dependencies"):
            print(f"    {DIM}← {', '.join(s['dependencies'])}{RESET}")
        if s.get("required_tools"):
            print(f"    {DIM}tools: {', '.join(s['required_tools'])}{RESET}")
        if s.get("discharges_checklist_items"):
            print(f"    {DIM}discharges: {', '.join(s['discharges_checklist_items'])}{RESET}")
    print()
    return skills


def _match_scenario(prompt_text: str) -> dict | None:
    """Try to match the prompt to a known test scenario for richer input."""
    prompt_lower = prompt_text.lower()
    for sc in _scenarios.get("scenarios", []):
        sc_id = sc["id"].lower()
        sc_title = sc.get("title", "").lower()
        sc_prompt = sc.get("prompt", "").lower()
        if sc_id in prompt_lower or sc_title in prompt_lower:
            return sc
        words = [w for w in prompt_lower.split() if len(w) > 3]
        matches = sum(1 for w in words if w in sc_title or w in sc_prompt)
        if matches >= 3:
            return sc
    return None


def _stream_event(event_type: str, data: dict):
    """Print agent events to the CLI as they happen."""
    if event_type == "thinking":
        text = data.get("text", "")
        for line in text.split("\n"):
            if line.strip():
                print(f"  {DIM}💭 {line.strip()}{RESET}", flush=True)
    elif event_type == "tool_call":
        name = data.get("name", "?")
        print(f"  {CYAN}⚡ {name}{RESET}", end="", flush=True)
    elif event_type == "tool_result":
        name = data.get("name", "?")
        result = data.get("result", "")
        latency = data.get("latency", 0)
        print(f" {DIM}→ {result} ({latency}s){RESET}", flush=True)
    elif event_type == "response":
        text = data.get("text", "")[:200]
        if text.strip():
            print(f"  {DIM}📝 {text.strip()[:150]}...{RESET}", flush=True)


def cmd_run_prompt(prompt_text: str, agent_key: str, mode: str, runner: AgentRunner):
    """Send a free-form prompt to the active agent."""
    task_input = {"change_description": prompt_text}

    scenario = _match_scenario(prompt_text)
    if scenario:
        affected = [f.replace(" (NEW)", "") for f in scenario.get("impact", {}).get("affected_files", [])]
        if affected:
            task_input["affected_files"] = affected
        task_input["change_id"] = scenario["id"]
        print(f"\n  {MAGENTA}{agent_key}{RESET} {DIM}({mode}) — matched scenario {scenario['id']}{RESET}\n")
    else:
        print(f"\n  {MAGENTA}{agent_key}{RESET} {DIM}({mode}){RESET}\n")

    prev_handler = runner.on_event
    runner.on_event = _stream_event

    start = time.monotonic()
    result = runner.run_agent(agent_key, task_input)
    elapsed = time.monotonic() - start

    runner.on_event = prev_handler

    print(f"\n{'─'*50}")
    _print_result(result)
    print(f"\n  {DIM}⏱ {elapsed:.1f}s{RESET}")
    return result


def cmd_workflow(mode: str):
    scenarios_list = [
        {"key": s["id"], "name": s["id"], "title": s["title"]}
        for s in _scenarios.get("scenarios", [])
    ]
    if not scenarios_list:
        print(f"  {RED}No scenarios found.{RESET}")
        return

    print(f"\n{BOLD}  Select scenario:{RESET}")
    chosen = _pick("Scenario", scenarios_list, display_field="key")
    if not chosen:
        return

    runner = AgentRunner(
        repository_root=_test_data_root,
        project_seed=_project_seed,
        test_scenarios=_scenarios,
        mode=mode,
    )
    wf = WorkflowRunner(runner, scenario=_scenarios)
    state = wf.initialize_from_scenario(chosen["key"])

    if "error" in state:
        print(f"  {RED}{state['error']}{RESET}")
        return

    print(f"\n  Workflow {BOLD}{state['workflow_id']}{RESET} | {state['total_steps']} steps | {YELLOW}{mode}{RESET}")
    for s in state["steps"]:
        print(f"    {DIM}{s['id']}{RESET} {s['name']} ({CYAN}{s['agent_key']}{RESET})")

    print()
    choice = input(f"  Run {BOLD}[a]ll{RESET} or {BOLD}[s]tep{RESET}-by-step? (a/s): ").strip().lower()
    run_all = choice != "s"

    total_start = time.monotonic()
    step_idx = 0

    while step_idx < state["total_steps"]:
        step_info = state["steps"][step_idx]
        print(f"\n  {BOLD}[{step_idx+1}/{state['total_steps']}]{RESET} {MAGENTA}{step_info['name']}{RESET} → {CYAN}{step_info['agent_key']}{RESET}")

        if not run_all:
            go = input(f"  Press Enter to run (or 'q' to stop): ").strip()
            if go.lower() in ("q", "quit"):
                break

        step_start = time.monotonic()
        state = wf.next_step()
        step_elapsed = time.monotonic() - step_start

        completed_step = state["steps"][step_idx]
        sc = GREEN if completed_step["status"] == "COMPLETED" else RED
        print(f"  {sc}{completed_step['status']}{RESET} {DIM}({step_elapsed:.1f}s){RESET}")

        if completed_step.get("result_summary"):
            for k, v in completed_step["result_summary"].items():
                print(f"    {BOLD}{k}:{RESET} {v}")

        step_idx = state["current_step"]

    total_elapsed = time.monotonic() - total_start
    completed = sum(1 for s in state["steps"] if s["status"] == "COMPLETED")
    failed = sum(1 for s in state["steps"] if s["status"] == "FAILED")
    print(f"\n  {BOLD}{state['status']}{RESET} in {total_elapsed:.1f}s | {GREEN}{completed} passed{RESET} {RED}{failed} failed{RESET} | {state['evidence_count']} evidence")


def cmd_traces(runner: AgentRunner):
    traces = runner.get_traces()
    if not traces:
        print(f"  {DIM}No traces yet. Send a prompt first.{RESET}")
        return
    print()
    for t in traces[:10]:
        sc = GREEN if t["status"] == "COMPLETED" else RED
        print(f"  {DIM}{t['start_time']}{RESET} {CYAN}{t['agent_key']}{RESET} {sc}{t['status']}{RESET} {DIM}{t['mode']} | {len(t['steps'])} steps{RESET}")


def cmd_help():
    print(f"""
  {BOLD}Slash Commands{RESET}
  {'─'*40}
  {CYAN}/agents{RESET}     List available agents
  {CYAN}/skills{RESET}     List metamodel skills
  {CYAN}/select{RESET}     Pick a different agent
  {CYAN}/workflow{RESET}   Run full SDLC workflow
  {CYAN}/traces{RESET}     Show execution traces
  {CYAN}/mode{RESET}       Toggle DEMO / REAL
  {CYAN}/model{RESET}      Show current model & agent info
  {CYAN}/verbose{RESET}    Toggle verbose logging
  {CYAN}/clear{RESET}      Clear screen
  {CYAN}/help{RESET}       Show this help
  {CYAN}/quit{RESET}       Exit

  {BOLD}Everything else is a prompt{RESET} sent to the
  active agent. Just type and press Enter.
""")


# ── Interactive REPL ────────────────────────────────────────

def interactive(mode: str, scenario_id: str):
    agent_key = "impact-analysis-agent"
    verbose = False

    runner = AgentRunner(
        repository_root=_test_data_root,
        project_seed=_project_seed,
        test_scenarios=_scenarios,
        mode=mode,
    )

    print(f"""
{BOLD}╔{'═'*58}╗
║  Data SDLC Framework — Agent CLI{' '*25}║
╚{'═'*58}╝{RESET}

  Active agent: {CYAN}{agent_key}{RESET}
  Mode: {YELLOW}{mode}{RESET}

  Type a prompt to send it to the agent.
  Type {CYAN}/help{RESET} for commands, {CYAN}/quit{RESET} to exit.
""")

    while True:
        try:
            prompt_label = f"{CYAN}{agent_key.split('-')[0]}{RESET}"
            mode_label = f"{GREEN}●{RESET}" if mode == "REAL" else f"{YELLOW}●{RESET}"
            user_input = input(f"{mode_label} {prompt_label} {BOLD}>{RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{DIM}Goodbye.{RESET}\n")
            break

        if not user_input:
            continue

        # ── Slash commands ──
        if user_input.startswith("/"):
            cmd = user_input.split()[0][1:].lower()
            cmd_args = user_input[len(cmd)+2:].strip()

            if cmd in ("q", "quit", "exit"):
                print(f"\n{DIM}Goodbye.{RESET}\n")
                break

            elif cmd == "help":
                cmd_help()

            elif cmd == "agents":
                cmd_agents()

            elif cmd == "skills":
                cmd_skills()

            elif cmd == "select":
                agents_list = [{"key": k, "name": k} for k in AGENT_CONFIGS.keys()]
                chosen = _pick("Select agent", agents_list)
                if chosen:
                    agent_key = chosen["key"]
                    print(f"\n  Active agent: {CYAN}{agent_key}{RESET}\n")

            elif cmd == "workflow":
                cmd_workflow(mode)

            elif cmd == "traces":
                cmd_traces(runner)

            elif cmd == "mode":
                mode = "REAL" if mode == "DEMO" else "DEMO"
                runner.mode = mode
                if mode == "REAL":
                    runner.reload_harness_config()
                print(f"\n  Mode: {YELLOW}{mode}{RESET}\n")

            elif cmd == "model":
                config = get_agent_config(agent_key)
                print(f"\n  Agent:  {CYAN}{agent_key}{RESET}")
                print(f"  Mode:   {YELLOW}{mode}{RESET}")
                if config:
                    print(f"  Model:  {config['bedrock_model_id']}")
                    print(f"  Tools:  {len(config.get('tools', []))}")
                    print(f"  Exec:   {config.get('execution_model', '?')}")
                print()

            elif cmd == "verbose":
                verbose = not verbose
                level = logging.DEBUG if verbose else logging.WARNING
                logging.getLogger("agents.runner").setLevel(level)
                print(f"\n  Verbose: {GREEN}ON{RESET}\n" if verbose else f"\n  Verbose: {DIM}OFF{RESET}\n")

            elif cmd == "clear":
                os.system("clear")

            else:
                print(f"  {RED}Unknown command: /{cmd}{RESET} — type {CYAN}/help{RESET}")

            continue

        # ── Everything else is a prompt ──
        cmd_run_prompt(user_input, agent_key, mode, runner)


# ── Direct CLI entry points ─────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Data SDLC Framework — Agent CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Run without arguments for interactive mode. Any text is a prompt.",
    )
    parser.add_argument("command", nargs="?", choices=["agents", "skills", "run", "workflow", "traces"],
                        help="Command to execute (omit for interactive mode)")
    parser.add_argument("agent_key", nargs="?", help="Agent key (for 'run' command)")
    parser.add_argument("--mode", default=os.environ.get("AGENT_MODE", "DEMO"),
                        choices=["DEMO", "REAL"], help="Execution mode (default: DEMO)")
    parser.add_argument("--scenario", default="ATLAS-CR-003", help="Scenario ID for workflow")
    parser.add_argument("--change", type=str, help="Change description for agent run")
    parser.add_argument("--files", type=str, help="Comma-separated affected files")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(name)s %(message)s")
    else:
        logging.basicConfig(level=logging.WARNING, format="%(name)s %(message)s")

    if args.command is None:
        interactive(args.mode, args.scenario)
    elif args.command == "agents":
        cmd_agents()
    elif args.command == "skills":
        cmd_skills()
    elif args.command == "run":
        if not args.agent_key:
            print(f"{RED}Usage: agent_cli.py run <agent-key>{RESET}")
            print(f"Available: {', '.join(AGENT_CONFIGS.keys())}")
            sys.exit(1)
        task_input = {}
        if args.change:
            task_input["change_description"] = args.change
        if args.files:
            task_input["affected_files"] = [f.strip() for f in args.files.split(",")]
        logging.basicConfig(level=logging.INFO, format="%(name)s %(message)s", force=True)
        runner = AgentRunner(
            repository_root=_test_data_root,
            project_seed=_project_seed,
            test_scenarios=_scenarios,
            mode=args.mode,
        )
        cmd_run_prompt(
            task_input.get("change_description", "Analyze repository"),
            args.agent_key, args.mode, runner,
        )
    elif args.command == "workflow":
        cmd_workflow(args.mode)
    elif args.command == "traces":
        runner = AgentRunner(
            repository_root=_test_data_root,
            project_seed=_project_seed,
            test_scenarios=_scenarios,
            mode=args.mode,
        )
        cmd_traces(runner)


if __name__ == "__main__":
    main()
