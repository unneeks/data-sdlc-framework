"""LLM reasoning enrichment via AgentCore Harness.

Takes the deterministic output of deep_walk and sends structured
reasoning prompts to an AgentCore Harness (or direct Bedrock model)
to fill gaps that AST/regex cannot:

1. **Semantic responsibilities** — what does this code *actually* do
   beyond what names and docstrings suggest?
2. **Architecture rationale** — why is the code organized this way?
   What design patterns are in play?
3. **Hidden dependencies** — runtime dependencies, implicit contracts,
   shared state, convention-based coupling.
4. **Risk and complexity** — code smells, technical debt signals,
   complexity hotspots.
5. **Business context** — what business domain does this serve?
   What workflows does it support?

Each reasoning step is a focused prompt with structured output.
The LLM sees only summaries — never raw file content — to stay
within token limits.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import boto3

REGION = "us-west-2"
DEFAULT_MODEL_ID = "global.anthropic.claude-sonnet-4-6"
DEFAULT_REASONING_HARNESS = (
    "arn:aws:bedrock-agentcore:us-west-2:981956186421:harness/code_reasoning-cdIPrL5T1l"
)


# ---------------------------------------------------------------------------
# Reasoning step definitions
# ---------------------------------------------------------------------------

REASONING_STEPS: list[dict[str, str]] = [
    {
        "id": "semantic_responsibilities",
        "name": "Semantic Responsibility Analysis",
        "prompt_template": (
            "You are a senior software architect analysing a codebase.\n\n"
            "Below is a deterministic analysis of modules and their inferred responsibilities.\n"
            "For each responsibility area, provide:\n"
            "1. A refined description (what the code *actually* does, not just what names suggest)\n"
            "2. The primary design pattern in use (e.g., repository pattern, factory, strategy, observer)\n"
            "3. The cohesion level (HIGH / MEDIUM / LOW) — how well the modules fit together\n"
            "4. Coupling assessment — what other areas this is tightly coupled to\n"
            "5. Missing abstractions — things that should be there but aren't\n\n"
            "Respond as a JSON array of objects with keys: area, refined_description, "
            "design_pattern, cohesion, coupled_to, missing_abstractions.\n\n"
            "--- ANALYSIS DATA ---\n{data}"
        ),
    },
    {
        "id": "architecture_rationale",
        "name": "Architecture Rationale",
        "prompt_template": (
            "You are a senior software architect.\n\n"
            "Given the following module structure, entry points, and patterns,\n"
            "explain the architecture:\n\n"
            "1. What is the dominant architectural style? (layered, hexagonal, pipes-and-filters, "
            "microservices, monolith, event-sourced, CQRS, etc.)\n"
            "2. What are the architectural boundaries? Where are the seams?\n"
            "3. What would break if you changed module X? (fragility assessment)\n"
            "4. What's the deployment model? (single process, multi-service, serverless, etc.)\n"
            "5. What architectural decisions are visible in the code structure?\n\n"
            "Respond as JSON: {{ architecture_style, boundaries: [], fragility_hotspots: [], "
            "deployment_model, architectural_decisions: [] }}\n\n"
            "--- ANALYSIS DATA ---\n{data}"
        ),
    },
    {
        "id": "hidden_dependencies",
        "name": "Hidden Dependency Detection",
        "prompt_template": (
            "You are a dependency analyst.\n\n"
            "Given the module imports and SBOM below, identify:\n\n"
            "1. **Implicit contracts** — modules that share conventions without explicit imports "
            "(e.g., naming conventions, shared config keys, database table names)\n"
            "2. **Runtime dependencies** — things that only connect at runtime "
            "(environment variables, service discovery, dynamic imports)\n"
            "3. **Convention coupling** — where changes in one module silently break another "
            "because they share a convention rather than an interface\n"
            "4. **Missing dependency declarations** — packages used in code but not in manifests\n"
            "5. **Circular dependency risks** — import cycles or mutual dependencies\n\n"
            "Respond as JSON: {{ implicit_contracts: [], runtime_dependencies: [], "
            "convention_coupling: [], missing_declarations: [], circular_risks: [] }}\n\n"
            "--- ANALYSIS DATA ---\n{data}"
        ),
    },
    {
        "id": "risk_complexity",
        "name": "Risk and Complexity Assessment",
        "prompt_template": (
            "You are a code quality analyst.\n\n"
            "Based on the module structure, patterns, and error handling below, assess:\n\n"
            "1. **Complexity hotspots** — modules with too many responsibilities, classes, or "
            "functions. Rank top 5 by risk.\n"
            "2. **Technical debt signals** — inconsistent patterns, missing tests, "
            "commented-out code indicators, TODO/FIXME density.\n"
            "3. **Error handling gaps** — areas with no try/except in critical paths, "
            "missing custom exceptions for domain errors.\n"
            "4. **Security concerns** — hardcoded config, missing input validation patterns, "
            "overly broad exception catching.\n"
            "5. **Maintainability score** — overall 1-10 with justification.\n\n"
            "Respond as JSON: {{ complexity_hotspots: [{{module, risk, reason}}], "
            "tech_debt_signals: [], error_handling_gaps: [], security_concerns: [], "
            "maintainability_score: N, justification: str }}\n\n"
            "--- ANALYSIS DATA ---\n{data}"
        ),
    },
    {
        "id": "business_context",
        "name": "Business Context Inference",
        "prompt_template": (
            "You are a business analyst reviewing a codebase.\n\n"
            "From the module names, class names, function names, responsibilities, "
            "and API endpoints below, infer:\n\n"
            "1. **Business domain** — what industry/business this serves\n"
            "2. **Key business entities** — the nouns this system manages "
            "(e.g., customers, orders, transactions, pipelines)\n"
            "3. **Business workflows** — the end-to-end processes this code supports\n"
            "4. **Data flow** — how data moves through the system from input to output\n"
            "5. **Stakeholder map** — who uses this system and for what purpose\n\n"
            "Respond as JSON: {{ business_domain, key_entities: [], workflows: [], "
            "data_flow: [{{from, to, data}}], stakeholders: [{{role, purpose}}] }}\n\n"
            "--- ANALYSIS DATA ---\n{data}"
        ),
    },
]


# ---------------------------------------------------------------------------
# Data preparation (compress deep_walk output for LLM context)
# ---------------------------------------------------------------------------

def _prepare_responsibilities_data(deep_report: dict) -> str:
    """Compress responsibilities + modules for the LLM."""
    lines = []
    for r in deep_report.get("responsibilities", []):
        lines.append(f"Area: {r['area']} ({r['layer']}, {r['total_lines']} lines, {r['module_count']} modules)")
        lines.append(f"  Description: {r['description']}")
        lines.append(f"  Key classes: {', '.join(r.get('key_classes', [])[:10])}")
        lines.append(f"  Key functions: {', '.join(r.get('key_functions', [])[:10])}")
        lines.append(f"  Modules: {', '.join(r.get('modules', [])[:5])}")
        lines.append("")
    return "\n".join(lines)


def _prepare_architecture_data(deep_report: dict) -> str:
    """Compress architecture-relevant data for the LLM."""
    lines = []
    summary = deep_report.get("summary", {})
    lines.append(f"Total files: {summary.get('total_files', 0)}")
    lines.append(f"Total lines: {summary.get('total_lines', 0)}")
    lines.append(f"Primary language: {summary.get('primary_language', 'unknown')}")
    lines.append(f"Languages: {json.dumps(summary.get('languages', {}))}")
    lines.append(f"Inferred architecture: {deep_report.get('architecture_style', 'unknown')}")
    lines.append("")

    lines.append("Entry points:")
    for ep in deep_report.get("entry_points", []):
        lines.append(f"  [{ep.get('type')}] {ep.get('file')} — {ep.get('detail')}")
    lines.append("")

    lines.append("Top modules by size:")
    mods = sorted(deep_report.get("modules", []), key=lambda m: m.get("lines", 0), reverse=True)
    for m in mods[:20]:
        cls_names = ", ".join(c["name"] for c in m.get("classes", [])[:5])
        lines.append(f"  {m['path']} ({m.get('lines', 0)}L, {len(m.get('classes', []))}C) — {cls_names}")
    lines.append("")

    patterns = deep_report.get("patterns", {})
    lines.append(f"Orchestration: {patterns.get('execution', {}).get('orchestration', 'unknown')}")
    lines.append(f"Error style: {patterns.get('behavior', {}).get('error_handling', {}).get('style', 'unknown')}")
    lines.append(f"API framework: {patterns.get('behavior', {}).get('api', {}).get('framework', 'none')}")
    lines.append(f"Test framework: {patterns.get('behavior', {}).get('testing', {}).get('framework', 'none')}")

    api_endpoints = patterns.get("behavior", {}).get("api", {}).get("endpoints", [])
    if api_endpoints:
        lines.append(f"API endpoints: {json.dumps(api_endpoints[:10])}")

    return "\n".join(lines)


def _prepare_dependency_data(deep_report: dict) -> str:
    """Compress dependency data for the LLM."""
    lines = []

    lines.append("Module imports (internal dependency graph):")
    for m in deep_report.get("modules", [])[:30]:
        ext = m.get("imports", {}).get("external", [])
        if ext:
            lines.append(f"  {m['path']} imports: {', '.join(ext[:10])}")
    lines.append("")

    sbom = deep_report.get("sbom", {})
    lines.append(f"SBOM: {sbom.get('summary', {}).get('total_components', 0)} components")
    for comp in sbom.get("components", [])[:30]:
        lines.append(f"  [{comp.get('scope')}] {comp['name']} {comp.get('version', '*')} ({comp.get('language')})")
    lines.append("")

    lines.append("Dependency files:")
    for df in sbom.get("dependency_files", []):
        lines.append(f"  {df['path']} ({df['type']}, {df['components']} deps)")

    return "\n".join(lines)


def _prepare_risk_data(deep_report: dict) -> str:
    """Compress risk-relevant data for the LLM."""
    lines = []
    patterns = deep_report.get("patterns", {})
    err = patterns.get("behavior", {}).get("error_handling", {})

    lines.append(f"Error handling: {err.get('style', 'unknown')}")
    lines.append(f"Try/except blocks: {err.get('try_except_count', 0)}")
    lines.append(f"Raise statements: {err.get('raise_count', 0)}")
    lines.append(f"Custom exceptions: {len(err.get('custom_exceptions', []))}")
    for exc in err.get("custom_exceptions", [])[:15]:
        lines.append(f"  {exc.get('name')} in {exc.get('file')}")
    lines.append("")

    lines.append("Module complexity (by class/function count):")
    mods = sorted(
        deep_report.get("modules", []),
        key=lambda m: len(m.get("classes", [])) + len(m.get("functions", [])),
        reverse=True,
    )
    for m in mods[:15]:
        lines.append(
            f"  {m['path']}: {len(m.get('classes', []))}C {len(m.get('functions', []))}F "
            f"{m.get('lines', 0)}L"
        )
    lines.append("")

    testing = patterns.get("behavior", {}).get("testing", {})
    lines.append(f"Test framework: {testing.get('framework', 'none')}")
    lines.append(f"Fixtures: {len(testing.get('fixtures', []))}")
    lines.append(f"Patterns: {testing.get('patterns', [])}")

    return "\n".join(lines)


def _prepare_business_data(deep_report: dict) -> str:
    """Compress business-relevant signals for the LLM."""
    lines = []
    for r in deep_report.get("responsibilities", []):
        lines.append(f"{r['area']}: {r['description']}")
        lines.append(f"  Classes: {', '.join(r.get('key_classes', [])[:10])}")
        lines.append(f"  Functions: {', '.join(r.get('key_functions', [])[:10])}")
    lines.append("")

    patterns = deep_report.get("patterns", {})
    api_endpoints = patterns.get("behavior", {}).get("api", {}).get("endpoints", [])
    if api_endpoints:
        lines.append("API endpoints:")
        for ep in api_endpoints[:15]:
            lines.append(f"  {ep.get('path', '')} ({ep.get('file', '')})")

    entry_points = deep_report.get("entry_points", [])
    if entry_points:
        lines.append("\nEntry points:")
        for ep in entry_points:
            lines.append(f"  [{ep.get('type')}] {ep.get('file')} — {ep.get('detail')}")

    return "\n".join(lines)


_DATA_PREPARERS = {
    "semantic_responsibilities": _prepare_responsibilities_data,
    "architecture_rationale": _prepare_architecture_data,
    "hidden_dependencies": _prepare_dependency_data,
    "risk_complexity": _prepare_risk_data,
    "business_context": _prepare_business_data,
}


# ---------------------------------------------------------------------------
# LLM invocation — Bedrock Converse API
# ---------------------------------------------------------------------------

def _invoke_bedrock(
    prompt: str,
    model_id: str = DEFAULT_MODEL_ID,
    region: str = REGION,
) -> str:
    """Call Bedrock Converse API and return the text response."""
    client = boto3.client("bedrock-runtime", region_name=region)

    response = client.converse(
        modelId=model_id,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": 4096, "temperature": 0.1},
    )

    output = response.get("output", {}).get("message", {}).get("content", [])
    text_parts = [block["text"] for block in output if "text" in block]
    return "\n".join(text_parts)


def _invoke_harness(
    prompt: str,
    harness_arn: str,
    region: str = REGION,
) -> str:
    """Call AgentCore Harness and return the text response (single turn, no tools)."""
    client = boto3.client("bedrock-agentcore", region_name=region)
    session_id = str(uuid.uuid4())

    response = client.invoke_harness(
        harnessArn=harness_arn,
        runtimeSessionId=session_id,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
    )

    text_output = ""
    for event in response.get("stream", []):
        if "contentBlockDelta" in event:
            delta = event["contentBlockDelta"].get("delta", {})
            if "text" in delta:
                text_output += delta["text"]

    return text_output


def _parse_json_response(text: str) -> Any:
    """Extract JSON from LLM response, handling markdown code blocks."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        start = 1
        end = len(lines)
        for i, line in enumerate(lines[1:], 1):
            if line.strip() == "```":
                end = i
                break
        text = "\n".join(lines[start:end])

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw_response": text, "parse_error": "Could not parse JSON from LLM response"}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_reasoning_steps(
    deep_report: dict[str, Any],
    *,
    steps: list[str] | None = None,
    model_id: str = DEFAULT_MODEL_ID,
    harness_arn: str | None = None,
    region: str = REGION,
) -> dict[str, Any]:
    """Run LLM reasoning steps to enrich a deep_walk report.

    Args:
        deep_report: Output of ``deep_walk_repository()``.
        steps: Which reasoning steps to run. None = all.
            Options: semantic_responsibilities, architecture_rationale,
            hidden_dependencies, risk_complexity, business_context.
        model_id: Bedrock model ID for direct invocation.
        harness_arn: If set, use AgentCore Harness instead of direct Bedrock.
            Defaults to the code_reasoning harness.
        region: AWS region.

    Returns:
        Dict with one key per completed reasoning step, plus a
        ``reasoning_metadata`` key with timing and model info.
    """
    if harness_arn is None:
        harness_arn = DEFAULT_REASONING_HARNESS

    available = {s["id"]: s for s in REASONING_STEPS}
    requested = steps or list(available.keys())

    results: dict[str, Any] = {}
    errors: list[dict[str, str]] = []

    for step_id in requested:
        if step_id not in available:
            errors.append({"step": step_id, "error": f"Unknown reasoning step: {step_id}"})
            continue

        step_def = available[step_id]
        data_preparer = _DATA_PREPARERS.get(step_id)
        if not data_preparer:
            errors.append({"step": step_id, "error": "No data preparer for this step"})
            continue

        data_text = data_preparer(deep_report)
        prompt = step_def["prompt_template"].format(data=data_text)

        print(f"  Running reasoning step: {step_def['name']}...")

        try:
            if harness_arn:
                raw_response = _invoke_harness(prompt, harness_arn, region)
            else:
                raw_response = _invoke_bedrock(prompt, model_id, region)

            parsed = _parse_json_response(raw_response)
            results[step_id] = {
                "name": step_def["name"],
                "result": parsed,
            }
            print(f"    Done: {step_def['name']}")

        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            errors.append({"step": step_id, "error": error_msg})
            print(f"    Failed: {error_msg}")

    results["reasoning_metadata"] = {
        "steps_requested": requested,
        "steps_completed": [s for s in requested if s in results],
        "steps_failed": [e["step"] for e in errors],
        "model_id": model_id,
        "harness_arn": harness_arn,
        "errors": errors,
    }

    return results


def enrich_deep_walk(
    deep_report: dict[str, Any],
    *,
    steps: list[str] | None = None,
    model_id: str = DEFAULT_MODEL_ID,
    harness_arn: str | None = None,
    region: str = REGION,
) -> dict[str, Any]:
    """Enrich a deep_walk report with LLM reasoning.

    Returns a copy of the deep_report with an added ``llm_reasoning``
    key containing all reasoning results.
    """
    reasoning = run_reasoning_steps(
        deep_report,
        steps=steps,
        model_id=model_id,
        harness_arn=harness_arn,
        region=region,
    )

    enriched = dict(deep_report)
    enriched["llm_reasoning"] = reasoning
    return enriched
