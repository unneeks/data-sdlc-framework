"""Test Execution skill — runs or simulates test execution.

In demo mode, produces deterministic results matching the test scenarios.
In real mode, would invoke actual pytest/dbt test runners.
"""
from __future__ import annotations

import hashlib
from typing import Any


def execute_tests(
    selected_tests: list[dict],
    change_id: str = "",
    scenario_data: dict | None = None,
) -> dict[str, Any]:
    """Execute (or simulate) the selected tests.

    Args:
        selected_tests: output of select_tests()["selected_tests"]
        change_id: identifier for the change being tested
        scenario_data: optional scenario data for deterministic results

    Returns:
        {
            "results": [...],
            "summary": {"passed": N, "failed": N, "skipped": N},
            "overall_status": "PASSED|FAILED",
            "evidence": [...],
        }
    """
    results = []
    for test in selected_tests:
        result = _simulate_test(test, change_id, scenario_data)
        results.append(result)

    passed = sum(1 for r in results if r["status"] == "PASSED")
    failed = sum(1 for r in results if r["status"] == "FAILED")
    skipped = sum(1 for r in results if r["status"] == "SKIPPED")

    evidence = []
    for r in results:
        evidence.append({
            "evidence_kind": "test_result",
            "test_path": r["path"],
            "status": r["status"],
            "provenance": "OBSERVED",
            "confidence": 1.0,
        })

    return {
        "results": results,
        "summary": {
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        },
        "overall_status": "PASSED" if failed == 0 else "FAILED",
        "evidence": evidence,
        "change_id": change_id,
    }


def _simulate_test(test: dict, change_id: str, scenario_data: dict | None) -> dict:
    path = test.get("path", "unknown")
    test_type = test.get("type", "unknown")

    if scenario_data and change_id:
        return _scenario_result(test, change_id, scenario_data)

    h = hashlib.md5(f"{path}:{change_id}".encode()).hexdigest()
    fail_probability = int(h[:2], 16) / 255

    if "reconciliation" in path.lower() and "timestamp" in (test.get("description", "").lower()):
        status = "FAILED"
        message = "Timestamp precision drift: microsecond truncation to millisecond"
    elif fail_probability < 0.05:
        status = "FAILED"
        message = f"Assertion error in {path}"
    else:
        status = "PASSED"
        message = None

    return {
        "path": path,
        "type": test_type,
        "status": status,
        "message": message,
        "duration_ms": int(h[2:6], 16) % 5000 + 100,
    }


def _scenario_result(test: dict, change_id: str, scenario_data: dict) -> dict:
    scenarios = scenario_data.get("scenarios", [])
    for scenario in scenarios:
        if scenario["id"] == change_id:
            if "timestamp" in test.get("description", "").lower() and change_id == "ATLAS-CR-003":
                return {
                    "path": test["path"],
                    "type": test["type"],
                    "status": "FAILED",
                    "message": "Reconciliation breach: 0.3% records fail timestamp precision check",
                    "duration_ms": 2400,
                    "rca_hint": "Parquet writer truncates timestamps to ms; Oracle stores μs",
                }
            break

    return {
        "path": test["path"],
        "type": test["type"],
        "status": "PASSED",
        "message": None,
        "duration_ms": 350,
    }
