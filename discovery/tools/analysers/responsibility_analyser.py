"""Responsibility analyser — infers high-level code responsibilities.

Groups modules into responsibility areas by analysing:
- Module-level docstrings
- Class and function names (domain keyword matching)
- Directory structure conventions
- Import relationships

Deterministic: uses keyword dictionaries and heuristics, no LLM.
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Domain keyword → responsibility area mapping
# ---------------------------------------------------------------------------

_KEYWORD_AREAS: list[tuple[str, list[str], str]] = [
    ("Data Ingestion", [
        "ingest", "ingestion", "extract", "etl", "source", "reader",
        "connector", "fetch", "pull", "intake", "loader", "import",
    ], "Handles reading data from external sources into the system"),

    ("Data Transformation", [
        "transform", "transformation", "dbt", "model", "staging",
        "mart", "aggregate", "pivot", "denormalize", "enrich",
        "cleanse", "normalize",
    ], "Transforms, cleans, and reshapes data for consumption"),

    ("Data Quality", [
        "quality", "validation", "validate", "check", "expectation",
        "soda", "great_expectations", "dq", "anomaly", "profiling",
    ], "Validates data quality, runs checks, and detects anomalies"),

    ("Orchestration", [
        "dag", "orchestrat", "workflow", "pipeline", "airflow",
        "prefect", "schedule", "trigger", "coordinator",
    ], "Coordinates and schedules execution of data pipelines"),

    ("Infrastructure", [
        "terraform", "infra", "provision", "deploy", "docker",
        "compose", "kubernetes", "k8s", "helm", "cloudformation",
        "cdk", "pulumi",
    ], "Manages infrastructure provisioning and deployment"),

    ("API / Web", [
        "api", "rest", "endpoint", "route", "handler", "controller",
        "fastapi", "flask", "django", "server", "middleware",
        "graphql", "grpc",
    ], "Exposes HTTP/API endpoints for external consumption"),

    ("Authentication & Authorization", [
        "auth", "login", "token", "jwt", "oauth", "permission",
        "rbac", "credential", "identity", "session",
    ], "Handles authentication, authorization, and identity"),

    ("Configuration & Settings", [
        "config", "setting", "environment", "env", "profile",
        "parameter", "secret",
    ], "Manages application configuration and environment settings"),

    ("Persistence / Storage", [
        "persist", "storage", "store", "repository", "dao",
        "database", "db", "neo4j", "postgres", "redis", "dynamo",
        "s3", "cache",
    ], "Reads and writes data to persistent storage"),

    ("Domain Logic", [
        "domain", "entity", "model", "schema", "business",
        "rule", "policy", "metamodel", "core",
    ], "Core business domain models and logic"),

    ("Agent / LLM", [
        "agent", "llm", "anthropic", "openai", "copilot", "prompt",
        "chat", "completion", "tool_use", "runtime", "loop",
    ], "AI agent orchestration and LLM integration"),

    ("Discovery / Analysis", [
        "discover", "walk", "scan", "analyse", "analyz", "inspect",
        "extract", "parse", "detect", "classify",
    ], "Code and project analysis, entity extraction"),

    ("Testing", [
        "test", "fixture", "mock", "assert", "spec", "conftest",
        "pytest", "unittest",
    ], "Automated testing: unit, integration, and end-to-end"),

    ("CI/CD", [
        "ci", "cd", "github_action", "workflow", "pipeline",
        "build", "release", "deploy",
    ], "Continuous integration and deployment automation"),

    ("Documentation", [
        "doc", "readme", "guide", "manual", "wiki", "adr",
        "changelog", "architecture",
    ], "Project documentation and architectural decision records"),

    ("User Interface", [
        "ui", "frontend", "web", "template", "jinja", "react",
        "component", "view", "page", "layout",
    ], "User-facing interface components"),

    ("Monitoring & Observability", [
        "monitor", "observ", "metric", "trace", "span",
        "otel", "opentelemetry", "cloudwatch", "log", "alarm",
    ], "Monitoring, tracing, and observability infrastructure"),
]

# Layer detection by directory convention
_LAYER_PATTERNS: list[tuple[str, list[str]]] = [
    ("presentation", ["api", "web", "ui", "frontend", "view", "controller", "handler", "route", "webui"]),
    ("business_logic", ["domain", "core", "service", "engine", "rule", "agent", "orchestrat"]),
    ("data_access", ["persist", "storage", "repository", "dao", "db", "store", "cache"]),
    ("infrastructure", ["infra", "terraform", "docker", "deploy", "ci", "config"]),
    ("testing", ["test", "tests", "spec", "fixture"]),
    ("tooling", ["tool", "util", "helper", "lib", "common", "shared"]),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _score_area(text: str, keywords: list[str]) -> float:
    """Score how well text matches a keyword list. 0.0 – 1.0."""
    text_lower = text.lower()
    hits = sum(1 for kw in keywords if kw in text_lower)
    if not hits:
        return 0.0
    return min(1.0, hits / max(3, len(keywords) * 0.3))


def _detect_layer(path_parts: tuple[str, ...]) -> str:
    """Detect architectural layer from directory path."""
    path_str = "/".join(path_parts).lower()
    for layer, patterns in _LAYER_PATTERNS:
        if any(p in path_str for p in patterns):
            return layer
    return "unknown"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyse_responsibilities(
    modules: list[dict[str, Any]],
    repository_root: str = "",
) -> list[dict[str, Any]]:
    """Group modules into high-level responsibility areas.

    Takes the output of ``analyse_modules`` and clusters modules
    by inferred responsibility.

    Returns a list of responsibility area descriptors.
    """
    # Score each module against each area
    module_scores: dict[str, list[tuple[dict, float]]] = defaultdict(list)

    for mod in modules:
        path = mod.get("path", "")
        hint = mod.get("responsibility_hint", "")
        class_names = " ".join(c.get("name", "") for c in mod.get("classes", []))
        func_names = " ".join(f.get("name", "") for f in mod.get("functions", []))
        external_imports = " ".join(mod.get("imports", {}).get("external", []))

        text_blob = f"{path} {hint} {class_names} {func_names} {external_imports}"

        best_area = None
        best_score = 0.0

        for area_name, keywords, _ in _KEYWORD_AREAS:
            score = _score_area(text_blob, keywords)
            if score > best_score:
                best_score = score
                best_area = area_name

        if best_area and best_score >= 0.1:
            module_scores[best_area].append((mod, best_score))

    # Build responsibility areas
    areas: list[dict[str, Any]] = []
    for area_name, keywords, description in _KEYWORD_AREAS:
        scored_modules = module_scores.get(area_name, [])
        if not scored_modules:
            continue

        scored_modules.sort(key=lambda x: x[1], reverse=True)

        mod_paths = [m["path"] for m, _ in scored_modules]
        key_classes = []
        for m, _ in scored_modules:
            for cls in m.get("classes", []):
                if not cls["name"].startswith("_"):
                    key_classes.append(cls["name"])
        key_functions = []
        for m, _ in scored_modules:
            for fn in m.get("functions", []):
                if not fn["name"].startswith("_"):
                    key_functions.append(fn["name"])

        avg_confidence = sum(s for _, s in scored_modules) / len(scored_modules) if scored_modules else 0

        # Detect layer from first module's path
        first_path = mod_paths[0] if mod_paths else ""
        parts = tuple(first_path.split("/"))
        layer = _detect_layer(parts)

        total_lines = sum(m.get("lines", 0) for m, _ in scored_modules)

        areas.append({
            "area": area_name,
            "description": description,
            "modules": mod_paths[:10],
            "module_count": len(mod_paths),
            "key_classes": key_classes[:15],
            "key_functions": key_functions[:15],
            "layer": layer,
            "total_lines": total_lines,
            "confidence": round(min(0.95, avg_confidence + 0.3), 2),
        })

    areas.sort(key=lambda a: a["total_lines"], reverse=True)
    return areas
