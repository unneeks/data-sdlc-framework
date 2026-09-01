"""Parse .agentcore/ convention directory into agent configurations.

Convention structure:
    .agentcore/
    ├── my-agent.agent.instructions.md       # Agent definition
    ├── skills/
    │   ├── my-skill/
    │   │   ├── skill.yaml                   # Skill metadata
    │   │   └── handler.py                   # Skill implementation
    │   └── ...
    ├── memory/
    │   └── <agent-name>/                    # Per-agent memory namespace
    ├── knowledgebase/
    │   ├── doc1.md                          # Shared knowledge (→ S3 knowledgebase)
    │   └── ...
    └── agentcore.yaml                       # Optional project-level config
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


AGENT_FILE_PATTERN = re.compile(r"^(.+)\.agent\.instructions\.md$")
AGENTCORE_DIR = ".agentcore"


@dataclass
class SkillConfig:
    name: str
    description: str = ""
    handler_path: str | None = None
    input_schema: dict = field(default_factory=dict)
    output_schema: dict = field(default_factory=dict)
    risk_level: str = "LOW"
    deterministic: bool = False
    dependencies: list[str] = field(default_factory=list)
    required_tools: list[str] = field(default_factory=list)

    @property
    def tool_spec(self) -> dict:
        return {
            "toolSpec": {
                "name": self.name.replace("-", "_"),
                "description": self.description or f"Execute the {self.name} skill",
                "inputSchema": {
                    "json": self.input_schema or {
                        "type": "object",
                        "properties": {
                            "input": {"type": "string", "description": "Input for the skill"},
                        },
                    },
                },
            },
        }

    @property
    def harness_tool_spec(self) -> dict:
        spec = self.tool_spec["toolSpec"]
        return {
            "type": "inline_function",
            "name": spec["name"],
            "config": {
                "inlineFunction": {
                    "description": spec["description"],
                    "inputSchema": spec["inputSchema"]["json"],
                },
            },
        }


@dataclass
class AgentConfig:
    name: str
    key: str
    description: str = ""
    model: str = "claude-sonnet"
    execution_model: str = "PLANNER_EXECUTOR"
    system_prompt: str = ""
    user_prompt: str = ""
    skills_used: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    risk_level: str = "MEDIUM"
    autonomy_level: str = "SEMI_AUTOMATIC"
    source_path: str = ""

    @property
    def agent_key(self) -> str:
        return self.key


@dataclass
class KnowledgebaseConfig:
    path: str
    files: list[str] = field(default_factory=list)
    total_size_bytes: int = 0


@dataclass
class ProjectConventions:
    root: str
    agentcore_dir: str
    agents: list[AgentConfig] = field(default_factory=list)
    skills: dict[str, SkillConfig] = field(default_factory=dict)
    knowledgebase: KnowledgebaseConfig | None = None
    memory_agents: list[str] = field(default_factory=list)
    project_config: dict = field(default_factory=dict)


def find_agentcore_dir(project_root: str | Path) -> Path | None:
    agentcore = Path(project_root) / AGENTCORE_DIR
    if agentcore.is_dir():
        return agentcore
    return None


def parse_agent_instructions(filepath: Path) -> AgentConfig:
    """Parse a *.agent.instructions.md file into an AgentConfig."""
    text = filepath.read_text(encoding="utf-8")

    match = AGENT_FILE_PATTERN.match(filepath.name)
    if not match:
        raise ValueError(f"Invalid agent file name: {filepath.name}")
    agent_key = match.group(1)

    frontmatter, body = _split_frontmatter(text)

    system_prompt, user_prompt = _split_prompts(body)

    skills_used = frontmatter.get("skills", [])
    if isinstance(skills_used, str):
        skills_used = [s.strip() for s in skills_used.split(",")]

    return AgentConfig(
        name=frontmatter.get("name", agent_key.replace("-", " ").title()),
        key=agent_key,
        description=frontmatter.get("description", ""),
        model=frontmatter.get("model", "claude-sonnet"),
        execution_model=frontmatter.get("execution_model", "PLANNER_EXECUTOR"),
        system_prompt=system_prompt.strip(),
        user_prompt=user_prompt.strip(),
        skills_used=skills_used,
        capabilities=frontmatter.get("capabilities", []),
        risk_level=frontmatter.get("risk_level", "MEDIUM"),
        autonomy_level=frontmatter.get("autonomy_level", "SEMI_AUTOMATIC"),
        source_path=str(filepath),
    )


def parse_skill(skill_dir: Path) -> SkillConfig:
    """Parse a skill directory into a SkillConfig.

    The primary convention is a skill.md file (markdown with YAML frontmatter)
    that describes the skill and references the tools it uses.

    Fallbacks: skill.yaml, skill.yml, skill.json.
    """
    skill_name = skill_dir.name
    meta: dict[str, Any] = {}
    body_text = ""

    skill_md = skill_dir / "skill.md"
    if skill_md.exists():
        text = skill_md.read_text(encoding="utf-8")
        fm, body = _split_frontmatter(text)
        meta = fm
        body_text = body.strip()
        if not meta.get("description") and body_text:
            first_para = body_text.split("\n\n")[0].replace("\n", " ").strip()
            meta.setdefault("description", first_para[:300])
        tools_from_body = _extract_tools_from_markdown(body_text)
        if tools_from_body:
            existing_tools = meta.get("tools", [])
            meta["tools"] = list(dict.fromkeys(existing_tools + tools_from_body))
    else:
        for fallback in ["skill.yaml", "skill.yml", "skill.json"]:
            fb_path = skill_dir / fallback
            if fb_path.exists():
                import json as _json
                if fb_path.suffix == ".json":
                    meta = _json.loads(fb_path.read_text())
                else:
                    meta = yaml.safe_load(fb_path.read_text()) or {}
                break

    handler_path = None
    for candidate in ["handler.py", f"{skill_name.replace('-', '_')}.py", "main.py"]:
        hp = skill_dir / candidate
        if hp.exists():
            handler_path = str(hp)
            break

    return SkillConfig(
        name=meta.get("name", skill_name),
        description=meta.get("description", ""),
        handler_path=handler_path,
        input_schema=meta.get("input_schema", meta.get("inputSchema", {})),
        output_schema=meta.get("output_schema", meta.get("outputSchema", {})),
        risk_level=meta.get("risk_level", "LOW"),
        deterministic=meta.get("deterministic", False),
        dependencies=meta.get("dependencies", []),
        required_tools=meta.get("tools", meta.get("required_tools", [])),
    )


def _extract_tools_from_markdown(body: str) -> list[str]:
    """Extract tool references from skill.md body.

    Recognizes:
    - YAML list under a ## Tools heading
    - Bullet list items like `- tool_name`
    - Inline backtick references like `tool_name`
    """
    tools: list[str] = []

    tools_section = re.search(
        r"(?m)^##\s*Tools?\s*\n(.*?)(?=\n##\s|\Z)",
        body,
        re.DOTALL | re.IGNORECASE,
    )
    if tools_section:
        section = tools_section.group(1)
        for line in section.strip().split("\n"):
            line = line.strip()
            m = re.match(r"^[-*]\s+`?([a-z_][a-z0-9_]*)`?", line)
            if m:
                tools.append(m.group(1))

    return tools


def discover_knowledgebase(agentcore_dir: Path) -> KnowledgebaseConfig | None:
    kb_dir = agentcore_dir / "knowledgebase"
    if not kb_dir.is_dir():
        return None

    files = []
    total_size = 0
    for f in sorted(kb_dir.rglob("*")):
        if f.is_file() and not f.name.startswith("."):
            files.append(str(f.relative_to(kb_dir)))
            total_size += f.stat().st_size

    if not files:
        return None

    return KnowledgebaseConfig(
        path=str(kb_dir),
        files=files,
        total_size_bytes=total_size,
    )


def discover_memory_agents(agentcore_dir: Path) -> list[str]:
    memory_dir = agentcore_dir / "memory"
    if not memory_dir.is_dir():
        return []
    return sorted(d.name for d in memory_dir.iterdir() if d.is_dir() and not d.name.startswith("."))


def parse_project_config(agentcore_dir: Path) -> dict:
    config_path = agentcore_dir / "agentcore.yaml"
    if not config_path.exists():
        config_path = agentcore_dir / "agentcore.yml"
    if config_path.exists():
        return yaml.safe_load(config_path.read_text()) or {}
    return {}


def discover_conventions(project_root: str | Path) -> ProjectConventions | None:
    """Discover all .agentcore/ conventions in a project."""
    project_root = Path(project_root)
    agentcore_dir = find_agentcore_dir(project_root)
    if not agentcore_dir:
        return None

    agents = []
    for f in sorted(agentcore_dir.iterdir()):
        if f.is_file() and AGENT_FILE_PATTERN.match(f.name):
            try:
                agents.append(parse_agent_instructions(f))
            except Exception as e:
                print(f"  Warning: failed to parse {f.name}: {e}")

    skills: dict[str, SkillConfig] = {}
    skills_dir = agentcore_dir / "skills"
    if skills_dir.is_dir():
        for d in sorted(skills_dir.iterdir()):
            if d.is_dir() and not d.name.startswith("."):
                try:
                    skills[d.name] = parse_skill(d)
                except Exception as e:
                    print(f"  Warning: failed to parse skill {d.name}: {e}")

    knowledgebase = discover_knowledgebase(agentcore_dir)
    memory_agents = discover_memory_agents(agentcore_dir)
    project_config = parse_project_config(agentcore_dir)

    return ProjectConventions(
        root=str(project_root),
        agentcore_dir=str(agentcore_dir),
        agents=agents,
        skills=skills,
        knowledgebase=knowledgebase,
        memory_agents=memory_agents,
        project_config=project_config,
    )


def validate_conventions(conventions: ProjectConventions) -> list[str]:
    """Validate convention consistency. Returns list of warning messages."""
    warnings = []

    for agent in conventions.agents:
        if not agent.system_prompt:
            warnings.append(f"Agent '{agent.key}' has no system prompt")
        for skill_name in agent.skills_used:
            if skill_name not in conventions.skills:
                warnings.append(f"Agent '{agent.key}' references skill '{skill_name}' not found in skills/")
        if agent.key not in conventions.memory_agents:
            warnings.append(f"Agent '{agent.key}' has no memory directory (memory/{agent.key}/)")

    for skill_name, skill in conventions.skills.items():
        if not skill.handler_path:
            warnings.append(f"Skill '{skill_name}' has no handler implementation")
        if not skill.description:
            warnings.append(f"Skill '{skill_name}' has no description")
        used_by = [a.key for a in conventions.agents if skill_name in a.skills_used]
        if not used_by:
            warnings.append(f"Skill '{skill_name}' is not referenced by any agent")

    return warnings


def _split_frontmatter(text: str) -> tuple[dict, str]:
    """Split YAML frontmatter from markdown body."""
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            try:
                fm = yaml.safe_load(parts[1]) or {}
                return fm, parts[2]
            except yaml.YAMLError:
                pass
    return {}, text


def _split_prompts(body: str) -> tuple[str, str]:
    """Split body into system prompt and user prompt sections."""
    system_prompt = body
    user_prompt = ""

    patterns = [
        (r"(?m)^##\s*System\s*Prompt\s*$", r"(?m)^##\s*User\s*Prompt\s*$"),
        (r"(?m)^#\s*System\s*Prompt\s*$", r"(?m)^#\s*User\s*Prompt\s*$"),
        (r"(?m)^---\s*system\s*---\s*$", r"(?m)^---\s*user\s*---\s*$"),
    ]

    for sys_pat, usr_pat in patterns:
        sys_match = re.search(sys_pat, body, re.IGNORECASE)
        usr_match = re.search(usr_pat, body, re.IGNORECASE)
        if sys_match:
            start = sys_match.end()
            if usr_match and usr_match.start() > sys_match.start():
                system_prompt = body[start:usr_match.start()]
                user_prompt = body[usr_match.end():]
            else:
                system_prompt = body[start:]
            break

    return system_prompt, user_prompt
