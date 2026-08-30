"""Data Profiling skill — profiles data assets from the corpus.

Extracts schema information, column statistics, and data quality indicators
from code and documentation in the test-data corpus.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def profile_data_assets(
    repository_root: str,
    discovered_files: list[dict],
    project_seed: dict | None = None,
) -> dict[str, Any]:
    """Profile data assets by analyzing schemas, configs, and quality checks.

    Returns:
        {
            "profiles": [...],     # per-asset profiles
            "summary": {...},
            "quality_indicators": [...],
        }
    """
    root = Path(repository_root)
    profiles = []
    quality_indicators = []

    schema_files = [f for f in discovered_files if _is_schema_file(f["path"])]
    quality_files = [f for f in discovered_files if f.get("entity_type") == "data_quality"]
    code_files = [f for f in discovered_files if f.get("entity_type") in ("pipeline_ingestion", "transformation")]

    for sf in schema_files:
        profile = _profile_schema(root, sf)
        if profile:
            profiles.append(profile)

    for qf in quality_files:
        indicators = _extract_quality_indicators(root, qf)
        quality_indicators.extend(indicators)

    for cf in code_files:
        profile = _profile_from_code(root, cf)
        if profile:
            profiles.append(profile)

    if project_seed:
        for asset in project_seed.get("data_assets", []):
            seed_profile = _profile_from_seed(asset)
            existing = [p for p in profiles if p.get("asset_name") == asset.get("name")]
            if existing:
                existing[0].update(seed_profile)
            else:
                profiles.append(seed_profile)

    return {
        "profiles": profiles,
        "quality_indicators": quality_indicators,
        "summary": {
            "total_assets_profiled": len(profiles),
            "total_quality_indicators": len(quality_indicators),
            "domains": list({p.get("domain", "unknown") for p in profiles}),
        },
    }


def _is_schema_file(path: str) -> bool:
    lower = path.lower()
    return "schema" in lower and (lower.endswith(".yml") or lower.endswith(".yaml"))


def _profile_schema(root: Path, file_desc: dict) -> dict | None:
    try:
        content = (root / file_desc["path"]).read_text(errors="replace")
    except OSError:
        return None

    columns = []
    for m in re.finditer(r"- name:\s*(\w+)", content):
        col_name = m.group(1)
        col_tests = []
        col_section = content[m.end():m.end() + 500]
        if "not_null" in col_section:
            col_tests.append("not_null")
        if "unique" in col_section:
            col_tests.append("unique")
        if "accepted_values" in col_section:
            col_tests.append("accepted_values")
        columns.append({"name": col_name, "tests": col_tests})

    if not columns:
        return None

    return {
        "source": file_desc["path"],
        "asset_name": Path(file_desc["path"]).stem.replace("schema", ""),
        "columns": columns,
        "column_count": len(columns),
        "has_tests": any(c["tests"] for c in columns),
        "provenance": "OBSERVED",
    }


def _extract_quality_indicators(root: Path, file_desc: dict) -> list[dict]:
    try:
        content = (root / file_desc["path"]).read_text(errors="replace")
    except OSError:
        return []

    indicators = []
    path_lower = file_desc["path"].lower()

    if "expectations" in path_lower or "great_expectations" in path_lower:
        for m in re.finditer(r'"expectation_type":\s*"([^"]+)"', content):
            indicators.append({
                "source": file_desc["path"],
                "type": "great_expectations",
                "check": m.group(1),
                "provenance": "OBSERVED",
            })
    elif "soda" in path_lower:
        for m in re.finditer(r"^\s*-\s+([\w]+\s*.+)", content, re.MULTILINE):
            indicators.append({
                "source": file_desc["path"],
                "type": "soda",
                "check": m.group(1).strip(),
                "provenance": "OBSERVED",
            })
    elif "dbt_project" in path_lower or "schema" in path_lower:
        for m in re.finditer(r"tests:\s*\n((?:\s+-\s+\w+\n)+)", content):
            for t in re.finditer(r"-\s+(\w+)", m.group(1)):
                indicators.append({
                    "source": file_desc["path"],
                    "type": "dbt_test",
                    "check": t.group(1),
                    "provenance": "OBSERVED",
                })

    return indicators


def _profile_from_code(root: Path, file_desc: dict) -> dict | None:
    try:
        content = (root / file_desc["path"]).read_text(errors="replace")[:10_000]
    except OSError:
        return None

    columns = []
    for m in re.finditer(r'StructField\(\s*["\'](\w+)["\']', content):
        columns.append({"name": m.group(1), "source": "spark_schema"})
    for m in re.finditer(r"col\(['\"](\w+)['\"]\)", content):
        if m.group(1) not in [c["name"] for c in columns]:
            columns.append({"name": m.group(1), "source": "spark_col_ref"})

    if not columns:
        return None

    return {
        "source": file_desc["path"],
        "asset_name": Path(file_desc["path"]).stem,
        "columns": columns,
        "column_count": len(columns),
        "domain": _infer_domain(file_desc["path"]),
        "provenance": "OBSERVED",
    }


def _profile_from_seed(asset: dict) -> dict:
    return {
        "asset_name": asset.get("name", ""),
        "asset_id": asset.get("id", ""),
        "asset_type": asset.get("asset_type", ""),
        "platform": asset.get("platform", ""),
        "domain": asset.get("domain", ""),
        "row_count": asset.get("row_count", ""),
        "provenance": "OBSERVED",
        "source": "project_seed",
    }


def _infer_domain(path: str) -> str:
    lower = path.lower()
    if "customer" in lower:
        return "Customer Accounts"
    if "transaction" in lower:
        return "Transactions"
    if "risk" in lower:
        return "Risk Scores"
    if "fx" in lower:
        return "FX Rates"
    if "counterpart" in lower:
        return "Counterparty Data"
    return "Unknown"
