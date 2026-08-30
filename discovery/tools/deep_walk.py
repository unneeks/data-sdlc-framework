"""Deep repository walker — builds a high-level abstraction of a codebase.

Unlike the basic ``walk_repository`` (which classifies files by extension),
deep_walk reads file content, parses ASTs, and produces:

- **Module structure** — packages, classes, functions, imports, exports
- **Responsibilities** — grouped areas of concern inferred from names/docstrings
- **Patterns** — entry points, orchestration style, error handling, logging, API, testing
- **SBOM** — full software bill of materials from dependency manifests

The deterministic pass uses AST + regex + heuristics (no LLM).
Optionally, an LLM enrichment pass uses AgentCore to reason about
semantic responsibilities, architecture rationale, hidden dependencies,
risk/complexity, and business context.

Usage::

    from discovery.tools.deep_walk import deep_walk_repository

    # Deterministic only
    report = deep_walk_repository("/path/to/repo")

    # With LLM enrichment via Bedrock
    report = deep_walk_repository("/path/to/repo", llm_enrich=True)

    # With LLM enrichment via AgentCore Harness
    report = deep_walk_repository("/path/to/repo", llm_enrich=True,
                                   harness_arn="arn:aws:bedrock-agentcore:...")
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from discovery.tools.analysers.module_analyser import analyse_modules
from discovery.tools.analysers.pattern_analyser import analyse_patterns
from discovery.tools.analysers.responsibility_analyser import analyse_responsibilities
from discovery.tools.analysers.sbom_analyser import analyse_sbom

MAX_FILE_SIZE = 500_000

DEFAULT_EXCLUDE_DIRS = frozenset(
    {".git", "__pycache__", "target", "dbt_packages", "node_modules",
     ".venv", "venv", "dist", ".next", "build", ".terraform"}
)

# Language detection by extension
_EXT_LANG: dict[str, str] = {
    ".py": "python", ".pyi": "python",
    ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript",
    ".ts": "typescript", ".tsx": "typescript",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".sql": "sql",
    ".tf": "hcl",
    ".sh": "shell", ".bash": "shell",
    ".yml": "yaml", ".yaml": "yaml",
    ".json": "json",
    ".md": "markdown",
    ".html": "html", ".htm": "html",
    ".css": "css", ".scss": "css",
    ".xml": "xml",
    ".toml": "toml",
    ".cfg": "ini",
    ".ini": "ini",
    ".r": "r", ".R": "r",
    ".scala": "scala",
    ".kt": "kotlin",
    ".swift": "swift",
    ".c": "c", ".h": "c",
    ".cpp": "cpp", ".hpp": "cpp", ".cc": "cpp",
}


def _count_repo_stats(
    root: Path, exclude: frozenset[str],
) -> dict[str, Any]:
    """Count files and lines per language."""
    languages: dict[str, dict[str, int]] = defaultdict(lambda: {"files": 0, "lines": 0})
    total_files = 0
    total_lines = 0

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if any(part in exclude for part in rel.parts):
            continue
        if path.stat().st_size > MAX_FILE_SIZE:
            continue

        lang = _EXT_LANG.get(path.suffix.lower())
        if not lang:
            continue

        total_files += 1
        try:
            line_count = path.read_text(encoding="utf-8", errors="replace").count("\n") + 1
        except OSError:
            line_count = 0

        total_lines += line_count
        languages[lang]["files"] += 1
        languages[lang]["lines"] += line_count

    primary = max(languages, key=lambda k: languages[k]["lines"]) if languages else "unknown"

    return {
        "total_files": total_files,
        "total_lines": total_lines,
        "languages": dict(languages),
        "primary_language": primary,
    }


def _infer_architecture(patterns: dict[str, Any], modules: list[dict]) -> str:
    """Infer the overall architecture style from patterns and module structure."""
    orch = patterns.get("execution", {}).get("orchestration", "script")
    api = patterns.get("behavior", {}).get("api", {}).get("framework")
    entry_points = patterns.get("execution", {}).get("entry_points", [])

    ep_types = {ep.get("type") for ep in entry_points}

    if orch == "dag":
        return "data_pipeline"
    if api and "web" in ep_types:
        if orch in ("dag", "task_queue"):
            return "web_plus_pipeline"
        return "web_application"
    if orch == "task_queue":
        return "distributed_task_queue"
    if orch == "event_driven":
        return "event_driven"
    if orch == "mixed":
        return "mixed_architecture"

    # Check module count for complexity signal
    pkg_count = sum(1 for m in modules if m.get("type") == "package")
    if pkg_count >= 5:
        return "modular_monolith"
    if pkg_count >= 2:
        return "layered_application"

    if "cli" in ep_types:
        return "cli_tool"

    return "script_collection"


def deep_walk_repository(
    repository_root: str,
    extra_exclude_dirs: list[str] | None = None,
    *,
    llm_enrich: bool = False,
    llm_steps: list[str] | None = None,
    model_id: str = "global.anthropic.claude-sonnet-4-6",
    harness_arn: str | None = None,
    region: str = "us-west-2",
) -> dict[str, Any]:
    """Perform a deep analysis of a repository.

    Returns a comprehensive report including module structure, code
    responsibilities, execution/behaviour patterns, SBOM, and an
    inferred architecture style.

    When *llm_enrich* is True, also runs LLM reasoning steps via
    AgentCore (Bedrock Converse or Harness) to analyse:
    - Semantic responsibilities (refined descriptions, design patterns, cohesion)
    - Architecture rationale (style, boundaries, fragility, deployment model)
    - Hidden dependencies (implicit contracts, runtime deps, convention coupling)
    - Risk and complexity (hotspots, tech debt, security, maintainability score)
    - Business context (domain, entities, workflows, data flow, stakeholders)

    Results appear under ``report["llm_reasoning"]``.
    """
    root = Path(repository_root)
    exclude = DEFAULT_EXCLUDE_DIRS | frozenset(extra_exclude_dirs or [])

    if not root.exists():
        return {"error": f"Repository root does not exist: {repository_root}"}

    # Step 1: Basic stats
    summary = _count_repo_stats(root, exclude)

    # Step 2: Module structure (AST-based)
    modules = analyse_modules(str(root), exclude)

    # Step 3: Execution & behaviour patterns
    patterns = analyse_patterns(str(root), exclude)

    # Step 4: High-level responsibilities (clusters modules)
    responsibilities = analyse_responsibilities(modules, str(root))

    # Step 5: SBOM
    sbom = analyse_sbom(str(root), exclude)

    # Step 6: Infer architecture style
    architecture_style = _infer_architecture(patterns, modules)

    # Extract entry points for top-level convenience
    entry_points = patterns.get("execution", {}).get("entry_points", [])

    report = {
        "repository_root": str(root),
        "summary": summary,
        "modules": modules,
        "responsibilities": responsibilities,
        "patterns": patterns,
        "sbom": sbom,
        "entry_points": entry_points,
        "architecture_style": architecture_style,
    }

    # Step 7 (optional): LLM reasoning enrichment
    if llm_enrich:
        from discovery.tools.analysers.llm_reasoning import run_reasoning_steps
        print("Running LLM reasoning enrichment...")
        report["llm_reasoning"] = run_reasoning_steps(
            report,
            steps=llm_steps,
            model_id=model_id,
            harness_arn=harness_arn,
            region=region,
        )

    return report
