"""Interactive agent creation wizard — similar to GitHub Copilot's convention flow.

Walks the user through:
1. Agent naming and description
2. Role and capabilities
3. System prompt authoring
4. Skills selection / creation
5. Memory configuration
6. Knowledgebase setup
7. Convention file generation
8. (Optional) Provisioning to AgentCore
"""
from __future__ import annotations

import os
import re
import textwrap
from pathlib import Path

import yaml

BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
MAGENTA = "\033[35m"
BLUE = "\033[34m"


def _ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    try:
        val = input(f"  {prompt}{suffix}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return default
    return val or default


def _ask_yn(prompt: str, default: bool = True) -> bool:
    hint = "Y/n" if default else "y/N"
    try:
        val = input(f"  {prompt} ({hint}): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return default
    if not val:
        return default
    return val in ("y", "yes")


def _ask_choice(prompt: str, options: list[str], default: int = 0) -> int:
    print()
    for i, opt in enumerate(options):
        marker = f"{GREEN}>{RESET}" if i == default else " "
        print(f"  {marker} {CYAN}{i + 1}{RESET}) {opt}")
    print()
    while True:
        try:
            val = input(f"  {prompt} [1-{len(options)}]: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return default
        if not val:
            return default
        try:
            idx = int(val) - 1
            if 0 <= idx < len(options):
                return idx
        except ValueError:
            pass
        print(f"  {RED}Invalid choice.{RESET}")


def _ask_multi(prompt: str, options: list[str]) -> list[int]:
    print()
    for i, opt in enumerate(options):
        print(f"    {CYAN}{i + 1}{RESET}) {opt}")
    print()
    try:
        val = input(f"  {prompt} (comma-separated, e.g. 1,3,4): ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return []
    if not val:
        return []
    indices = []
    for part in val.split(","):
        part = part.strip()
        if part.isdigit():
            idx = int(part) - 1
            if 0 <= idx < len(options):
                indices.append(idx)
    return indices


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if not slug.endswith("-agent"):
        slug += "-agent"
    return slug


def _header(title: str):
    print(f"\n  {BOLD}{'─' * 56}{RESET}")
    print(f"  {BOLD}{title}{RESET}")
    print(f"  {BOLD}{'─' * 56}{RESET}\n")


def _banner():
    print(f"""
{BOLD}╔{'═' * 58}╗
║  AgentCore Convention Creator                            ║
║  {DIM}Create agents from .agentcore/ conventions{RESET}{BOLD}              ║
╚{'═' * 58}╝{RESET}

  This wizard creates convention-based agent configurations
  in your project's {CYAN}.agentcore/{RESET} directory, similar to how
  GitHub Copilot uses {CYAN}.github/copilot-instructions.md{RESET}.
""")


def run_create_agent_wizard(project_root: str | Path) -> dict | None:
    """Run the interactive agent creation wizard. Returns agent config dict or None if cancelled."""
    project_root = Path(project_root)
    agentcore_dir = project_root / ".agentcore"

    _banner()

    # ── Step 1: Agent identity ──
    _header("Step 1/7 — Agent Identity")

    agent_name = _ask("Agent name", "my-custom-agent")
    if not agent_name:
        print(f"\n  {RED}Cancelled.{RESET}\n")
        return None

    agent_key = _slugify(agent_name)
    print(f"  {DIM}Agent key: {CYAN}{agent_key}{RESET}")

    # ── Check for existing agent ──
    conflict = _check_agent_exists(project_root, agentcore_dir, agent_key)
    if conflict:
        print(f"\n  {YELLOW}⚠  Agent '{agent_key}' already exists:{RESET}")
        for source in conflict:
            print(f"    {YELLOW}• {source}{RESET}")

        action_options = [
            "Overwrite (recreate from scratch)",
            "Skip (cancel wizard)",
        ]
        action_idx = _ask_choice("What would you like to do?", action_options, default=1)
        if action_idx == 1:
            print(f"\n  {DIM}Skipped.{RESET}\n")
            return None
        print(f"\n  {YELLOW}Will overwrite existing agent '{agent_key}'.{RESET}")

    description = _ask("Description", f"A custom AgentCore agent for {agent_name}")

    # ── Step 2: Role and capabilities ──
    _header("Step 2/7 — Role & Capabilities")

    role_options = [
        "Impact Analysis Engineer",
        "Data Quality Engineer",
        "Regression Engineer",
        "Data Model Engineer",
        "Delivery Compliance Engineer",
        "Custom role...",
    ]
    role_idx = _ask_choice("Engineering role", role_options, default=0)
    if role_idx == len(role_options) - 1:
        role = _ask("Custom role name")
    else:
        role = role_options[role_idx]

    capability_options = [
        "impact-analysis",
        "data-quality",
        "regression-testing",
        "data-modelling",
        "governance",
        "testing",
        "lineage",
        "metadata-management",
    ]
    print(f"\n  {BOLD}Select capabilities:{RESET}")
    cap_indices = _ask_multi("Capabilities", capability_options)
    capabilities = [capability_options[i] for i in cap_indices]
    if not capabilities:
        capabilities = ["impact-analysis"]
    print(f"  {DIM}Selected: {', '.join(capabilities)}{RESET}")

    # ── Step 3: Model & execution ──
    _header("Step 3/7 — Model & Execution")

    model_options = [
        "claude-sonnet (Recommended — balanced speed/quality)",
        "claude-opus (Highest quality, slower)",
        "claude-haiku (Fastest, simpler tasks)",
    ]
    model_idx = _ask_choice("Model", model_options, default=0)
    model_keys = ["claude-sonnet", "claude-opus", "claude-haiku"]
    model = model_keys[model_idx]

    exec_options = [
        "PLANNER_EXECUTOR (Recommended — plan then execute)",
        "ITERATIVE (Iterative refinement loop)",
    ]
    exec_idx = _ask_choice("Execution model", exec_options, default=0)
    exec_model = "PLANNER_EXECUTOR" if exec_idx == 0 else "ITERATIVE"

    risk_options = ["LOW", "MEDIUM (Recommended)", "HIGH", "CRITICAL"]
    risk_idx = _ask_choice("Risk level", risk_options, default=1)
    risk_keys = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    risk_level = risk_keys[risk_idx]

    autonomy_options = [
        "SEMI_AUTOMATIC (Recommended — human approval for key steps)",
        "AUTOMATIC (Fully autonomous execution)",
        "APPROVAL_REQUIRED (Human approval for every action)",
    ]
    auto_idx = _ask_choice("Autonomy level", autonomy_options, default=0)
    auto_keys = ["SEMI_AUTOMATIC", "AUTOMATIC", "APPROVAL_REQUIRED"]
    autonomy = auto_keys[auto_idx]

    # ── Step 4: System prompt ──
    _header("Step 4/7 — System Prompt")

    print(f"  {DIM}A system prompt defines the agent's personality, mission,")
    print(f"  constraints, and workflow. You can edit it later in the")
    print(f"  .agentcore/{agent_key}.agent.instructions.md file.{RESET}\n")

    prompt_options = [
        "Generate a template (Recommended)",
        "Enter custom system prompt",
        "Start with minimal prompt",
    ]
    prompt_idx = _ask_choice("System prompt", prompt_options, default=0)

    if prompt_idx == 0:
        system_prompt = _generate_system_prompt(agent_name, role, capabilities, description)
        print(f"\n  {DIM}Generated system prompt ({len(system_prompt)} chars):{RESET}")
        for line in system_prompt.split("\n")[:8]:
            print(f"  {DIM}  {line}{RESET}")
        print(f"  {DIM}  ...{RESET}")
    elif prompt_idx == 1:
        print(f"\n  {DIM}Enter your system prompt (empty line to finish):{RESET}")
        lines = []
        while True:
            try:
                line = input("  > ")
            except (EOFError, KeyboardInterrupt):
                break
            if line == "":
                break
            lines.append(line)
        system_prompt = "\n".join(lines) if lines else _generate_system_prompt(agent_name, role, capabilities, description)
    else:
        system_prompt = f"You are {agent_name}. {description}"

    # ── Step 5: Skills ──
    _header("Step 5/7 — Skills")

    existing_skills = _discover_existing_skills(agentcore_dir)
    builtin_skills = [
        "discover_repository",
        "read_file",
        "analyze_dependencies",
        "analyze_impact",
        "select_tests",
        "execute_tests",
        "profile_data_assets",
        "discover_delivery_process",
        "validate_checklist",
        "assess_gate_readiness",
        "validate_evidence",
    ]

    print(f"  {BOLD}Built-in skills:{RESET}")
    all_skills = [f"{s} {DIM}(built-in){RESET}" for s in builtin_skills]
    if existing_skills:
        all_skills.extend(f"{s} {GREEN}(custom){RESET}" for s in existing_skills)

    skill_indices = _ask_multi("Select skills for this agent", all_skills)
    skills_used = []
    new_custom_skills = []
    for idx in skill_indices:
        if idx < len(builtin_skills):
            skills_used.append(builtin_skills[idx])
        else:
            skills_used.append(existing_skills[idx - len(builtin_skills)])

    if _ask_yn("Create a new custom skill?", default=False):
        while True:
            skill_name = _ask("Skill name (or empty to stop)")
            if not skill_name:
                break
            skill_desc = _ask("Skill description", f"Custom skill: {skill_name}")
            skill_risk = _ask("Risk level (LOW/MEDIUM/HIGH)", "LOW")

            print(f"\n  {DIM}Select tools this skill references (from built-in tools):{RESET}")
            tool_indices = _ask_multi("Tools for this skill", builtin_skills)
            skill_tools = [builtin_skills[i] for i in tool_indices]
            if skill_tools:
                print(f"  {DIM}Tools: {', '.join(skill_tools)}{RESET}")

            new_custom_skills.append({
                "name": skill_name,
                "description": skill_desc,
                "risk_level": skill_risk.upper(),
                "tools": skill_tools,
            })
            skills_used.append(skill_name)
            print(f"  {GREEN}✓{RESET} Skill '{skill_name}' will be created (skill.md + handler.py)\n")

    if not skills_used:
        skills_used = ["discover_repository", "read_file"]
        print(f"  {DIM}Defaulting to: {', '.join(skills_used)}{RESET}")

    print(f"\n  {BOLD}Skills:{RESET} {', '.join(skills_used)}")

    # ── Step 6: Memory ──
    _header("Step 6/7 — Memory")

    enable_memory = _ask_yn("Enable agent memory?", default=True)
    if enable_memory:
        print(f"  {GREEN}✓{RESET} Memory will be created at {CYAN}.agentcore/memory/{agent_key}/{RESET}")

    # ── Step 7: Knowledgebase ──
    _header("Step 7/7 — Knowledgebase")

    kb_dir = agentcore_dir / "knowledgebase"
    if kb_dir.is_dir():
        kb_files = [f.name for f in kb_dir.rglob("*") if f.is_file() and not f.name.startswith(".")]
        print(f"  {GREEN}Found existing knowledgebase:{RESET} {len(kb_files)} files in .agentcore/knowledgebase/")
        for f in kb_files[:5]:
            print(f"    {DIM}• {f}{RESET}")
        if len(kb_files) > 5:
            print(f"    {DIM}• ... and {len(kb_files) - 5} more{RESET}")
        use_kb = _ask_yn("Use shared knowledgebase?", default=True)
    else:
        use_kb = _ask_yn("Create a knowledgebase directory?", default=False)
        if use_kb:
            print(f"  {DIM}Add documents to {CYAN}.agentcore/knowledgebase/{RESET}{DIM} for S3 upload{RESET}")

    # ── Summary ──
    _header("Summary")

    print(f"  {BOLD}Agent:{RESET}        {CYAN}{agent_key}{RESET}")
    print(f"  {BOLD}Name:{RESET}         {agent_name}")
    print(f"  {BOLD}Description:{RESET}  {description}")
    print(f"  {BOLD}Role:{RESET}         {role}")
    print(f"  {BOLD}Capabilities:{RESET} {', '.join(capabilities)}")
    print(f"  {BOLD}Model:{RESET}        {model}")
    print(f"  {BOLD}Execution:{RESET}    {exec_model}")
    print(f"  {BOLD}Risk:{RESET}         {risk_level}")
    print(f"  {BOLD}Autonomy:{RESET}     {autonomy}")
    print(f"  {BOLD}Skills:{RESET}       {', '.join(skills_used)}")
    print(f"  {BOLD}Memory:{RESET}       {'Enabled' if enable_memory else 'Disabled'}")
    print(f"  {BOLD}Knowledgebase:{RESET}{'Shared' if use_kb else 'None'}")

    print(f"\n  {BOLD}Files to create:{RESET}")
    print(f"    {CYAN}.agentcore/{agent_key}.agent.instructions.md{RESET}")
    if new_custom_skills:
        for s in new_custom_skills:
            print(f"    {CYAN}.agentcore/skills/{s['name']}/skill.md{RESET}")
            print(f"    {CYAN}.agentcore/skills/{s['name']}/handler.py{RESET}")
    if enable_memory:
        print(f"    {CYAN}.agentcore/memory/{agent_key}/.gitkeep{RESET}")
    if use_kb and not kb_dir.is_dir():
        print(f"    {CYAN}.agentcore/knowledgebase/.gitkeep{RESET}")

    print()
    if not _ask_yn("Create these files?", default=True):
        print(f"\n  {YELLOW}Cancelled.{RESET}\n")
        return None

    # ── Write files ──
    _write_convention_files(
        agentcore_dir=agentcore_dir,
        agent_key=agent_key,
        agent_name=agent_name,
        description=description,
        role=role,
        capabilities=capabilities,
        model=model,
        exec_model=exec_model,
        risk_level=risk_level,
        autonomy=autonomy,
        system_prompt=system_prompt,
        skills_used=skills_used,
        new_custom_skills=new_custom_skills,
        enable_memory=enable_memory,
        create_kb=use_kb and not kb_dir.is_dir(),
    )

    print(f"\n  {GREEN}✓ Agent '{agent_key}' created successfully!{RESET}\n")

    provision_now = _ask_yn("Provision to AgentCore now?", default=False)

    result = {
        "agent_key": agent_key,
        "agent_name": agent_name,
        "description": description,
        "role": role,
        "capabilities": capabilities,
        "model": model,
        "execution_model": exec_model,
        "risk_level": risk_level,
        "autonomy": autonomy,
        "skills": skills_used,
        "memory": enable_memory,
        "knowledgebase": use_kb,
        "provision_now": provision_now,
        "agentcore_dir": str(agentcore_dir),
    }

    if provision_now:
        _provision_interactive(project_root, agent_key)

    return result


def _check_agent_exists(project_root: Path, agentcore_dir: Path, agent_key: str) -> list[str]:
    """Check if an agent already exists across all sources. Returns list of conflict descriptions."""
    conflicts = []

    instruction_file = agentcore_dir / f"{agent_key}.agent.instructions.md"
    if instruction_file.exists():
        conflicts.append(f".agentcore/{agent_key}.agent.instructions.md (convention file)")

    import yaml as _yaml
    cfg_path = project_root / "agents" / "agent_configs.yaml"
    if cfg_path.exists():
        data = _yaml.safe_load(cfg_path.read_text()) or {}
        if agent_key in data.get("agents", {}):
            conflicts.append(f"agents/agent_configs.yaml (YAML config)")

    config_path = project_root / "agentcore_config.json"
    if config_path.exists():
        import json
        config = json.loads(config_path.read_text())
        harness_info = config.get("harnesses", {}).get(agent_key, {})
        if harness_info.get("status") == "READY":
            arn = harness_info.get("harness_arn", "")
            conflicts.append(f"agentcore_config.json (harness READY: {arn})")
        elif harness_info.get("harness_id"):
            conflicts.append(f"agentcore_config.json (harness {harness_info.get('status', 'UNKNOWN')})")

    memory_dir = agentcore_dir / "memory" / agent_key
    if memory_dir.exists() and any(memory_dir.iterdir()):
        conflicts.append(f".agentcore/memory/{agent_key}/ (memory directory)")

    return conflicts


def _discover_existing_skills(agentcore_dir: Path) -> list[str]:
    skills_dir = agentcore_dir / "skills"
    if not skills_dir.is_dir():
        return []
    return sorted(d.name for d in skills_dir.iterdir() if d.is_dir() and not d.name.startswith("."))


def _generate_system_prompt(name: str, role: str, capabilities: list[str], description: str) -> str:
    caps = ", ".join(capabilities) if capabilities else "general"
    return textwrap.dedent(f"""\
        You are {name}, an AI agent in the Data Engineering Digital Twin platform.

        MISSION: {description}

        ROLE: {role}
        CAPABILITIES: {caps}

        WORKFLOW:
        1. Analyze the incoming request and determine the scope of work
        2. Use available tools to gather data and evidence
        3. Apply your domain expertise to produce structured findings
        4. Report results with provenance and confidence scores

        CONSTRAINTS:
        - Every finding must carry provenance (OBSERVED or INFERRED) and confidence
        - INFERRED findings cannot block delivery
        - Cite the evidence behind each claim
        - Return structured JSON results

        OUTPUT FORMAT:
        Return your findings as structured JSON with clear keys for each aspect
        of your analysis. Include confidence scores and provenance for all claims.""")


def _write_convention_files(
    agentcore_dir: Path,
    agent_key: str,
    agent_name: str,
    description: str,
    role: str,
    capabilities: list[str],
    model: str,
    exec_model: str,
    risk_level: str,
    autonomy: str,
    system_prompt: str,
    skills_used: list[str],
    new_custom_skills: list[dict],
    enable_memory: bool,
    create_kb: bool,
):
    agentcore_dir.mkdir(parents=True, exist_ok=True)

    frontmatter = {
        "name": agent_name,
        "description": description,
        "model": model,
        "execution_model": exec_model,
        "risk_level": risk_level,
        "autonomy_level": autonomy,
        "capabilities": capabilities,
        "skills": skills_used,
    }

    md_content = "---\n"
    md_content += yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
    md_content += "---\n\n"
    md_content += "## System Prompt\n\n"
    md_content += system_prompt + "\n\n"
    md_content += "## User Prompt\n\n"
    md_content += f"Execute the {agent_key} workflow and return structured results.\n"

    agent_file = agentcore_dir / f"{agent_key}.agent.instructions.md"
    agent_file.write_text(md_content)
    print(f"  {GREEN}✓{RESET} Created {CYAN}{agent_file.relative_to(agentcore_dir.parent)}{RESET}")

    skills_dir = agentcore_dir / "skills"
    for skill_info in new_custom_skills:
        skill_name = skill_info["name"]
        skill_dir = skills_dir / skill_name
        skill_dir.mkdir(parents=True, exist_ok=True)

        skill_tools = skill_info.get("tools", [])
        tools_section = ""
        if skill_tools:
            tools_list = "\n".join(f"- `{t}`" for t in skill_tools)
            tools_section = f"\n## Tools\n\n{tools_list}\n"

        skill_md = textwrap.dedent(f"""\
            ---
            name: {skill_name}
            description: {skill_info.get('description', '')}
            risk_level: {skill_info.get('risk_level', 'LOW')}
            deterministic: false
            dependencies: []
            tools: {yaml.dump(skill_tools, default_flow_style=True).strip() if skill_tools else '[]'}
            input_schema:
              type: object
              properties:
                input:
                  type: string
                  description: Input for the skill
              required:
                - input
            output_schema:
              type: object
              properties:
                result:
                  type: object
                  description: Skill output
            ---

            # {skill_name}

            {skill_info.get('description', f'Custom skill: {skill_name}')}
            {tools_section}
            ## Usage

            This skill is invoked by agents that reference it in their
            `skills` attribute in the agent instructions file.
        """)
        (skill_dir / "skill.md").write_text(skill_md)

        handler_py = textwrap.dedent(f'''\
            """Handler for the {skill_name} skill."""
            from __future__ import annotations

            from typing import Any


            def execute(input_data: dict[str, Any]) -> dict[str, Any]:
                """Execute the {skill_name} skill.

                Args:
                    input_data: Input parameters from the agent.

                Returns:
                    Structured result dict.
                """
                # TODO: Implement your skill logic here
                return {{
                    "skill": "{skill_name}",
                    "status": "executed",
                    "input": input_data,
                    "result": {{}},
                }}
        ''')
        (skill_dir / "handler.py").write_text(handler_py)
        print(f"  {GREEN}✓{RESET} Created skill {CYAN}{skill_dir.relative_to(agentcore_dir.parent)}/{RESET}")

    if enable_memory:
        memory_dir = agentcore_dir / "memory" / agent_key
        memory_dir.mkdir(parents=True, exist_ok=True)
        (memory_dir / ".gitkeep").touch()
        print(f"  {GREEN}✓{RESET} Created memory dir {CYAN}{memory_dir.relative_to(agentcore_dir.parent)}/{RESET}")

    if create_kb:
        kb_dir = agentcore_dir / "knowledgebase"
        kb_dir.mkdir(parents=True, exist_ok=True)
        (kb_dir / ".gitkeep").touch()
        print(f"  {GREEN}✓{RESET} Created knowledgebase dir {CYAN}{kb_dir.relative_to(agentcore_dir.parent)}/{RESET}")

    _ensure_agentcore_yaml(agentcore_dir)


def _ensure_agentcore_yaml(agentcore_dir: Path):
    config_path = agentcore_dir / "agentcore.yaml"
    if config_path.exists():
        return

    config = {
        "version": "1.0",
        "project": {
            "name": agentcore_dir.parent.name,
            "description": "AgentCore convention-based project",
        },
        "defaults": {
            "model": "claude-sonnet",
            "region": os.environ.get("AWS_DEFAULT_REGION", "us-west-2"),
            "execution_model": "PLANNER_EXECUTOR",
        },
        "knowledgebase": {
            "type": "s3",
            "shared": True,
        },
    }
    config_path.write_text(yaml.dump(config, default_flow_style=False, sort_keys=False))
    print(f"  {GREEN}✓{RESET} Created {CYAN}{config_path.relative_to(agentcore_dir.parent)}{RESET}")


def _provision_interactive(project_root: Path, agent_key: str):
    from agents.conventions.parser import discover_conventions, validate_conventions
    from agents.conventions.provisioner import provision_all, save_convention_config, REGION

    conventions = discover_conventions(project_root)
    if not conventions:
        print(f"\n  {RED}No .agentcore/ conventions found.{RESET}\n")
        return

    target_agents = [a for a in conventions.agents if a.key == agent_key]
    if not target_agents:
        print(f"\n  {RED}Agent '{agent_key}' not found in conventions.{RESET}\n")
        return

    warnings = validate_conventions(conventions)
    if warnings:
        print(f"\n  {YELLOW}Warnings:{RESET}")
        for w in warnings:
            print(f"    {YELLOW}⚠ {w}{RESET}")
        if not _ask_yn("\n  Continue anyway?", default=True):
            return

    print(f"\n  {BOLD}Provisioning to AgentCore ({REGION})...{RESET}\n")

    def _on_progress(stage: str, msg: str):
        icon = {"iam": "🔑", "harness": "🏗️", "skills": "⚡", "memory": "🧠", "knowledgebase": "📚"}.get(stage, "•")
        print(f"  {icon} {msg}")

    result = provision_all(conventions, region=REGION, on_progress=_on_progress)
    config_path = save_convention_config(conventions, result, region=REGION)

    print(f"\n  {'─' * 50}")
    if result.success:
        print(f"  {GREEN}✓ Provisioning complete!{RESET}")
    else:
        print(f"  {YELLOW}⚠ Provisioning completed with errors:{RESET}")
        for err in result.errors:
            print(f"    {RED}✗ {err}{RESET}")

    print(f"  {DIM}Config saved to: {config_path}{RESET}\n")


def run_provision_all_wizard(project_root: str | Path) -> dict | None:
    """Provision all convention-based agents to AgentCore."""
    from agents.conventions.parser import discover_conventions, validate_conventions
    from agents.conventions.provisioner import provision_all, save_convention_config, REGION

    project_root = Path(project_root)
    conventions = discover_conventions(project_root)
    if not conventions:
        print(f"\n  {RED}No .agentcore/ directory found at {project_root}{RESET}")
        print(f"  {DIM}Run /create-agent first to set up conventions.{RESET}\n")
        return None

    _header("Convention Discovery")
    print(f"  {BOLD}Agents:{RESET}        {len(conventions.agents)}")
    for a in conventions.agents:
        print(f"    {CYAN}• {a.key}{RESET} — {DIM}{a.description or a.name}{RESET}")
    print(f"  {BOLD}Skills:{RESET}        {len(conventions.skills)}")
    for name, s in conventions.skills.items():
        print(f"    {CYAN}• {name}{RESET} — {DIM}{s.description or 'no description'}{RESET}")
    if conventions.knowledgebase:
        print(f"  {BOLD}Knowledgebase:{RESET} {len(conventions.knowledgebase.files)} files ({conventions.knowledgebase.total_size_bytes:,} bytes)")
    print(f"  {BOLD}Memory:{RESET}        {len(conventions.memory_agents)} namespaces")

    warnings = validate_conventions(conventions)
    if warnings:
        print(f"\n  {YELLOW}Validation warnings:{RESET}")
        for w in warnings:
            print(f"    {YELLOW}⚠ {w}{RESET}")

    print()
    if not _ask_yn("Provision all agents to AgentCore?", default=True):
        print(f"\n  {YELLOW}Cancelled.{RESET}\n")
        return None

    print(f"\n  {BOLD}Provisioning to AgentCore ({REGION})...{RESET}\n")

    def _on_progress(stage: str, msg: str):
        icon = {"iam": "🔑", "harness": "🏗️", "skills": "⚡", "memory": "🧠", "knowledgebase": "📚", "validate": "✅"}.get(stage, "•")
        print(f"  {icon} {msg}")

    result = provision_all(conventions, region=REGION, on_progress=_on_progress)
    config_path = save_convention_config(conventions, result, region=REGION)

    _header("Provisioning Summary")
    for agent_key, info in result.harnesses.items():
        status = info.get("status", "UNKNOWN")
        color = GREEN if status == "READY" else RED
        print(f"  {color}[{status}]{RESET} {CYAN}{agent_key}{RESET}")
        if info.get("harness_arn"):
            print(f"    {DIM}ARN: {info['harness_arn']}{RESET}")

    if result.skills:
        print(f"\n  Skills registered: {GREEN}{len(result.skills)}{RESET}")
    if result.memories:
        print(f"  Memory namespaces: {GREEN}{len(result.memories)}{RESET}")
    if result.knowledgebase:
        print(f"  Knowledgebase: {GREEN}{result.knowledgebase.get('status', '?')}{RESET}")
        if result.knowledgebase.get("s3_uri"):
            print(f"    {DIM}{result.knowledgebase['s3_uri']}{RESET}")

    if result.errors:
        print(f"\n  {RED}Errors:{RESET}")
        for err in result.errors:
            print(f"    {RED}✗ {err}{RESET}")

    print(f"\n  {DIM}Config: {config_path}{RESET}\n")
    return result.summary()


def run_list_conventions(project_root: str | Path):
    """List all convention-based agents discovered in .agentcore/."""
    from agents.conventions.parser import discover_conventions, validate_conventions

    conventions = discover_conventions(project_root)
    if not conventions:
        print(f"\n  {DIM}No .agentcore/ directory found.{RESET}")
        print(f"  {DIM}Run /create-agent to get started.{RESET}\n")
        return

    _header("Convention-Based Agents")

    if not conventions.agents:
        print(f"  {DIM}No agent instruction files found.{RESET}")
        print(f"  {DIM}Create one with: /create-agent{RESET}\n")
        return

    for agent in conventions.agents:
        print(f"  {CYAN}{agent.key}{RESET}")
        print(f"    {BOLD}Name:{RESET}       {agent.name}")
        print(f"    {BOLD}Model:{RESET}      {agent.model}")
        print(f"    {BOLD}Execution:{RESET}  {agent.execution_model}")
        print(f"    {BOLD}Skills:{RESET}     {', '.join(agent.skills_used) or 'none'}")
        print(f"    {BOLD}Risk:{RESET}       {agent.risk_level}")
        print(f"    {DIM}Source: {agent.source_path}{RESET}")
        print()

    if conventions.skills:
        print(f"  {BOLD}Custom Skills:{RESET}")
        for name, skill in conventions.skills.items():
            handler = f"{GREEN}✓{RESET}" if skill.handler_path else f"{RED}✗{RESET}"
            print(f"    {handler} {CYAN}{name}{RESET} — {DIM}{skill.description or 'no description'}{RESET}")
        print()

    if conventions.knowledgebase:
        print(f"  {BOLD}Knowledgebase:{RESET} {len(conventions.knowledgebase.files)} files")
        print()

    warnings = validate_conventions(conventions)
    if warnings:
        print(f"  {YELLOW}Warnings:{RESET}")
        for w in warnings[:10]:
            print(f"    {YELLOW}⚠ {w}{RESET}")
        print()
