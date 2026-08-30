"""Execution and behaviour pattern analyser.

Scans code for entry points, orchestration styles, error handling,
logging, retry logic, API frameworks, testing patterns, and configuration
approaches.  Deterministic — regex + AST heuristics, no LLM.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

MAX_FILE_SIZE = 500_000

# ---------------------------------------------------------------------------
# Compiled patterns
# ---------------------------------------------------------------------------

# Entry points
_MAIN_GUARD = re.compile(r"""if\s+__name__\s*==\s*['"]__main__['"]""")
_CONSOLE_SCRIPTS = re.compile(r"""console_scripts\s*=\s*\[""")
_CLICK_CMD = re.compile(r"@(?:\w+\.)?(?:command|group)\s*\(")
_TYPER_CMD = re.compile(r"typer\.Typer\s*\(")
_ARGPARSE = re.compile(r"argparse\.ArgumentParser\s*\(")

# Web frameworks
_FLASK_ROUTE = re.compile(r"@\w+\.route\s*\(")
_FASTAPI_ROUTE = re.compile(r"@\w+\.(?:get|post|put|delete|patch|options|head|websocket)\s*\(")
_DJANGO_URL = re.compile(r"urlpatterns\s*=")
_FLASK_APP = re.compile(r"Flask\s*\(__name__\)")
_FASTAPI_APP = re.compile(r"FastAPI\s*\(")

# DAG / orchestration
_AIRFLOW_DAG = re.compile(r"(?:DAG|dag)\s*\(")
_AIRFLOW_TASK = re.compile(r"(?:PythonOperator|BashOperator|TaskFlow|@task)\s*[\(]")
_CELERY_TASK = re.compile(r"@(?:\w+\.)?task\s*\(")
_PREFECT_FLOW = re.compile(r"@(?:flow|task)\s*\(")

# Scheduling
_CRON_RE = re.compile(r"""['"](\d+[\s*/,-]+\d+[\s*/,-]+\d+[\s*/,-]+\d+[\s*/,-]+\d+(?:\s*/?,\-\d+)*)['"]""")
_SCHEDULE_INTERVAL = re.compile(r"schedule_interval\s*=\s*['\"]([^'\"]+)['\"]")
_SCHEDULE_LIB = re.compile(r"schedule\.every\s*\(")

# Error handling
_CUSTOM_EXCEPTION = re.compile(r"class\s+(\w+(?:Error|Exception))\s*\(")
_TRY_EXCEPT = re.compile(r"^\s*try\s*:", re.MULTILINE)
_RAISE = re.compile(r"^\s*raise\s+", re.MULTILINE)

# Logging
_LOGGING_GETLOGGER = re.compile(r"logging\.getLogger\s*\(")
_STRUCTLOG = re.compile(r"structlog\.")
_LOGURU = re.compile(r"from\s+loguru\s+import")
_LOG_LEVELS = re.compile(r"\.\s*(debug|info|warning|error|critical)\s*\(")

# Retry
_TENACITY = re.compile(r"@retry\s*\(|from\s+tenacity\s+import")
_BACKOFF = re.compile(r"@backoff\.|from\s+backoff\s+import")
_MANUAL_RETRY = re.compile(r"for\s+\w+\s+in\s+range\s*\(.*?retry", re.IGNORECASE)

# Testing
_PYTEST_FIXTURE = re.compile(r"@pytest\.fixture")
_PYTEST_MARK = re.compile(r"@pytest\.mark\.")
_UNITTEST_CLASS = re.compile(r"class\s+\w+\((?:unittest\.)?TestCase\)")
_MOCK_PATCH = re.compile(r"@(?:mock\.)?patch")
_ASSERT_CALL = re.compile(r"assert\s+|self\.assert|pytest\.raises")

# Configuration
_ENV_VAR = re.compile(r"os\.(?:environ|getenv)\s*[\[\(]")
_DOTENV = re.compile(r"(?:load_dotenv|from\s+dotenv)")
_DATACLASS_CONFIG = re.compile(r"@dataclass.*\nclass\s+\w*[Cc]onfig")
_PYDANTIC_SETTINGS = re.compile(r"class\s+\w+\(BaseSettings\)")

# Event / observer
_SIGNAL = re.compile(r"signal\.signal\s*\(|Signal\s*\(")
_EVENT_EMITTER = re.compile(r"EventEmitter|on_event|add_listener|subscribe")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_read(path: Path) -> str | None:
    if path.stat().st_size > MAX_FILE_SIZE:
        return None
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _detect_endpoint_details(content: str) -> list[dict[str, str]]:
    """Extract route paths from decorator arguments."""
    endpoints = []
    for m in re.finditer(r"""@\w+\.(?:route|get|post|put|delete|patch)\s*\(\s*['"]([^'"]+)['"]""", content):
        endpoints.append({"path": m.group(1)})
    return endpoints


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyse_patterns(
    repository_root: str,
    exclude_dirs: frozenset[str] | None = None,
) -> dict[str, Any]:
    """Analyse execution and behaviour patterns across the repository."""
    root = Path(repository_root)
    exclude = exclude_dirs or frozenset(
        {".git", "__pycache__", "node_modules", ".venv", "venv", "dist", "build", ".terraform", "target"}
    )

    entry_points: list[dict[str, str]] = []
    scheduling: list[dict[str, str]] = []
    custom_exceptions: list[dict[str, str]] = []
    error_patterns: list[dict[str, str]] = []
    log_frameworks: set[str] = set()
    log_levels: set[str] = set()
    retry_locations: list[dict[str, str]] = []
    retry_libraries: set[str] = set()
    api_framework: str | None = None
    api_endpoints: list[dict[str, str]] = []
    test_framework: str | None = None
    test_fixtures: list[str] = []
    test_patterns: list[str] = []
    config_style: set[str] = set()
    config_sources: list[str] = []
    has_dag = False
    has_celery = False
    has_prefect = False
    has_events = False
    try_count = 0
    raise_count = 0
    warnings: list[str] = []

    for py_file in sorted(root.rglob("*.py")):
        rel = py_file.relative_to(root)
        if any(part in exclude for part in rel.parts):
            continue
        content = _safe_read(py_file)
        if content is None:
            continue
        rel_str = rel.as_posix()

        # --- Entry points ---
        if _MAIN_GUARD.search(content):
            ep_type = "script"
            detail = "__main__ guard"
            if _ARGPARSE.search(content):
                ep_type = "cli"
                detail = "argparse CLI"
            elif _CLICK_CMD.search(content):
                ep_type = "cli"
                detail = "click CLI"
            elif _TYPER_CMD.search(content):
                ep_type = "cli"
                detail = "typer CLI"
            entry_points.append({"file": rel_str, "type": ep_type, "detail": detail})

        if _FLASK_APP.search(content) or _FASTAPI_APP.search(content):
            fw = "fastapi" if _FASTAPI_APP.search(content) else "flask"
            entry_points.append({"file": rel_str, "type": "web", "detail": f"{fw} application"})
            api_framework = fw

        # --- DAG / orchestration ---
        if _AIRFLOW_DAG.search(content):
            has_dag = True
            entry_points.append({"file": rel_str, "type": "dag", "detail": "Airflow DAG"})
        if _CELERY_TASK.search(content):
            has_celery = True
        if _PREFECT_FLOW.search(content):
            has_prefect = True

        # --- Scheduling ---
        for m in _SCHEDULE_INTERVAL.finditer(content):
            scheduling.append({"file": rel_str, "cron": m.group(1), "description": "Airflow schedule_interval"})
        for m in _CRON_RE.finditer(content):
            scheduling.append({"file": rel_str, "cron": m.group(1), "description": "cron expression"})
        if _SCHEDULE_LIB.search(content):
            scheduling.append({"file": rel_str, "cron": "", "description": "schedule library"})

        # --- API endpoints ---
        if _FLASK_ROUTE.search(content) or _FASTAPI_ROUTE.search(content):
            if not api_framework:
                api_framework = "fastapi" if _FASTAPI_ROUTE.search(content) else "flask"
            endpoints = _detect_endpoint_details(content)
            for ep in endpoints:
                ep["file"] = rel_str
            api_endpoints.extend(endpoints)

        if _DJANGO_URL.search(content):
            api_framework = api_framework or "django"

        # --- Error handling ---
        for m in _CUSTOM_EXCEPTION.finditer(content):
            custom_exceptions.append({"name": m.group(1), "file": rel_str})

        try_count += len(_TRY_EXCEPT.findall(content))
        raise_count += len(_RAISE.findall(content))

        # --- Logging ---
        if _LOGGING_GETLOGGER.search(content):
            log_frameworks.add("stdlib")
        if _STRUCTLOG.search(content):
            log_frameworks.add("structlog")
        if _LOGURU.search(content):
            log_frameworks.add("loguru")
        log_levels.update(_LOG_LEVELS.findall(content))

        # --- Retry ---
        if _TENACITY.search(content):
            retry_libraries.add("tenacity")
            retry_locations.append({"file": rel_str, "library": "tenacity"})
        if _BACKOFF.search(content):
            retry_libraries.add("backoff")
            retry_locations.append({"file": rel_str, "library": "backoff"})
        if _MANUAL_RETRY.search(content):
            retry_locations.append({"file": rel_str, "library": "manual_loop"})

        # --- Testing ---
        if _PYTEST_FIXTURE.search(content):
            test_framework = test_framework or "pytest"
            for m in re.finditer(r"@pytest\.fixture.*\ndef\s+(\w+)", content):
                test_fixtures.append(m.group(1))
        if _PYTEST_MARK.search(content):
            test_framework = test_framework or "pytest"
        if _UNITTEST_CLASS.search(content):
            test_framework = test_framework or "unittest"
        if _MOCK_PATCH.search(content):
            test_patterns.append("mocking")
        if _ASSERT_CALL.search(content):
            test_patterns.append("assertions")

        # --- Configuration ---
        if _ENV_VAR.search(content):
            config_style.add("env")
            config_sources.append(rel_str)
        if _DOTENV.search(content):
            config_style.add("dotenv")
        if _DATACLASS_CONFIG.search(content):
            config_style.add("dataclass")
        if _PYDANTIC_SETTINGS.search(content):
            config_style.add("pydantic_settings")

        # --- Events ---
        if _SIGNAL.search(content) or _EVENT_EMITTER.search(content):
            has_events = True

    # --- Determine orchestration style ---
    orch_signals = []
    if has_dag:
        orch_signals.append("dag")
    if api_framework:
        orch_signals.append("request_response")
    if has_celery:
        orch_signals.append("task_queue")
    if has_prefect:
        orch_signals.append("pipeline")
    if has_events:
        orch_signals.append("event_driven")

    if len(orch_signals) == 0:
        orchestration = "script"
    elif len(orch_signals) == 1:
        orchestration = orch_signals[0]
    else:
        orchestration = "mixed"

    # --- Error handling style ---
    if try_count > 0 and raise_count > 0:
        error_style = "exceptions"
    elif try_count > 0:
        error_style = "defensive"
    else:
        error_style = "minimal"

    # --- Logging framework ---
    log_fw = sorted(log_frameworks)[0] if log_frameworks else "none"

    return {
        "execution": {
            "entry_points": entry_points,
            "orchestration": orchestration,
            "scheduling": scheduling,
        },
        "behavior": {
            "error_handling": {
                "style": error_style,
                "custom_exceptions": custom_exceptions,
                "try_except_count": try_count,
                "raise_count": raise_count,
            },
            "logging": {
                "framework": log_fw,
                "all_frameworks": sorted(log_frameworks),
                "levels_used": sorted(log_levels),
            },
            "retry": {
                "libraries": sorted(retry_libraries),
                "locations": retry_locations,
            },
            "api": {
                "framework": api_framework,
                "endpoints": api_endpoints,
            },
            "testing": {
                "framework": test_framework,
                "fixtures": sorted(set(test_fixtures)),
                "patterns": sorted(set(test_patterns)),
            },
            "config": {
                "styles": sorted(config_style),
                "sources": sorted(set(config_sources)),
            },
        },
        "warnings": warnings,
    }
