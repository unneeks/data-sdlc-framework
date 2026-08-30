"""Test Selection skill — selects the minimal sufficient test set for a change.

Given impact analysis results, identifies which tests cover the affected assets
and selects the smallest set that provides adequate coverage.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any


def select_tests(
    impact_result: dict[str, Any],
    discovered_files: list[dict],
    test_scenarios: dict | None = None,
) -> dict[str, Any]:
    """Select tests that cover the impacted entities.

    Args:
        impact_result: output of analyze_impact()
        discovered_files: output of discover_repository()["files"]
        test_scenarios: optional atlas_test_scenarios.json data

    Returns:
        {
            "selected_tests": [...],
            "coverage_map": {...},
            "uncovered_entities": [...],
            "selection_rationale": str,
        }
    """
    all_affected = (
        impact_result.get("directly_affected", []) +
        impact_result.get("transitively_affected", [])
    )
    affected_paths = {item.get("path", item.get("id", "")) for item in all_affected}

    test_files = [f for f in discovered_files if f.get("entity_type") == "test"]
    quality_files = [f for f in discovered_files if f.get("entity_type") == "data_quality"]

    selected = []
    coverage_map: dict[str, list[str]] = {}

    for tf in test_files:
        covers = _test_covers(tf["path"], affected_paths)
        if covers:
            selected.append({
                "path": tf["path"],
                "type": "unit_test" if "test_" in tf["path"] else "integration_test",
                "covers": covers,
                "priority": "HIGH" if len(covers) > 2 else "MEDIUM",
            })
            for c in covers:
                coverage_map.setdefault(c, []).append(tf["path"])

    for qf in quality_files:
        covers = _quality_covers(qf["path"], affected_paths)
        if covers:
            selected.append({
                "path": qf["path"],
                "type": "data_quality_check",
                "covers": covers,
                "priority": "HIGH",
            })
            for c in covers:
                coverage_map.setdefault(c, []).append(qf["path"])

    if test_scenarios:
        scenario_tests = _match_scenario_tests(impact_result, test_scenarios)
        selected.extend(scenario_tests)

    covered = set(coverage_map.keys())
    uncovered = [p for p in affected_paths if p not in covered]

    return {
        "selected_tests": selected,
        "coverage_map": coverage_map,
        "uncovered_entities": uncovered,
        "total_selected": len(selected),
        "coverage_ratio": len(covered) / max(len(affected_paths), 1),
        "selection_rationale": (
            f"Selected {len(selected)} tests covering {len(covered)}/{len(affected_paths)} "
            f"affected entities. {len(uncovered)} entities lack direct test coverage."
        ),
    }


def _test_covers(test_path: str, affected_paths: set[str]) -> list[str]:
    covers = []
    test_stem = Path(test_path).stem.replace("test_", "").replace("_test", "")
    for ap in affected_paths:
        ap_stem = Path(ap).stem
        if test_stem in ap_stem or ap_stem in test_stem:
            covers.append(ap)
        elif _domain_overlap(test_path, ap):
            covers.append(ap)
    return covers


def _quality_covers(quality_path: str, affected_paths: set[str]) -> list[str]:
    covers = []
    qstem = Path(quality_path).stem.lower()
    for ap in affected_paths:
        ap_lower = ap.lower()
        domain_keywords = ["customer", "transaction", "risk", "fx", "counterpart"]
        for kw in domain_keywords:
            if kw in qstem and kw in ap_lower:
                covers.append(ap)
                break
    return covers


def _domain_overlap(path_a: str, path_b: str) -> bool:
    domains = ["customer", "transaction", "risk", "fx_rate", "counterpart", "reconciliation"]
    a_lower = path_a.lower()
    b_lower = path_b.lower()
    for d in domains:
        if d in a_lower and d in b_lower:
            return True
    return False


def _match_scenario_tests(impact_result: dict, test_scenarios: dict) -> list[dict]:
    tests = []
    scenarios = test_scenarios.get("scenarios", [])
    for scenario in scenarios:
        expected_files = set(
            f.replace(" (NEW)", "") for f in scenario.get("impact", {}).get("affected_files", [])
        )
        affected_paths = {
            item.get("path", "") for item in
            impact_result.get("directly_affected", []) + impact_result.get("transitively_affected", [])
        }
        overlap = expected_files & affected_paths
        if overlap:
            plan = scenario.get("test_plan", {})
            for test_type in ["unit_tests", "integration_tests", "regression_tests", "performance_tests"]:
                for t in plan.get(test_type, []):
                    tests.append({
                        "path": f"scenario:{scenario['id']}",
                        "type": test_type.rstrip("s"),
                        "description": t,
                        "covers": list(overlap)[:3],
                        "priority": "HIGH" if "regression" in test_type else "MEDIUM",
                    })
    return tests
