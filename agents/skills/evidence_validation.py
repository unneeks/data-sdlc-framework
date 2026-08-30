"""Evidence Validation skill — validates that evidence meets delivery requirements.

Checks that evidence items carry proper provenance, are complete, and
satisfy the requirements of their associated gates/checklists.
"""
from __future__ import annotations

from typing import Any


def validate_evidence(
    evidence: list[dict],
    requirements: list[dict] | None = None,
) -> dict[str, Any]:
    """Validate a set of evidence items.

    Args:
        evidence: list of evidence items (from test execution, profiling, etc.)
        requirements: optional list of what evidence is required

    Returns:
        {
            "validated": [...],
            "issues": [...],
            "summary": {...},
        }
    """
    validated = []
    issues = []

    for ev in evidence:
        ev_issues = _check_evidence(ev)
        validated.append({
            **ev,
            "valid": len(ev_issues) == 0,
            "issues": ev_issues,
        })
        issues.extend(ev_issues)

    if requirements:
        missing = _check_completeness(evidence, requirements)
        issues.extend(missing)

    return {
        "validated": validated,
        "issues": issues,
        "summary": {
            "total_evidence": len(evidence),
            "valid_count": sum(1 for v in validated if v["valid"]),
            "invalid_count": sum(1 for v in validated if not v["valid"]),
            "issue_count": len(issues),
            "completeness": _completeness_score(evidence, requirements) if requirements else 1.0,
        },
    }


def _check_evidence(ev: dict) -> list[dict]:
    issues = []

    if "provenance" not in ev:
        issues.append({
            "type": "missing_provenance",
            "detail": "Evidence item lacks provenance state",
            "severity": "HIGH",
        })
    elif ev["provenance"] == "INFERRED" and ev.get("confidence", 1.0) < 0.5:
        issues.append({
            "type": "low_confidence_inference",
            "detail": f"Inferred evidence with confidence {ev.get('confidence', 0):.2f} — below threshold",
            "severity": "MEDIUM",
        })

    if "evidence_kind" not in ev:
        issues.append({
            "type": "missing_kind",
            "detail": "Evidence item has no evidence_kind",
            "severity": "MEDIUM",
        })

    if ev.get("status") == "FAILED":
        issues.append({
            "type": "failed_evidence",
            "detail": f"Evidence indicates failure: {ev.get('message', 'no message')}",
            "severity": "HIGH",
        })

    return issues


def _check_completeness(evidence: list[dict], requirements: list[dict]) -> list[dict]:
    missing = []
    ev_kinds = {ev.get("evidence_kind", "") for ev in evidence}

    for req in requirements:
        required_kind = req.get("evidence_kind", req.get("kind", ""))
        if required_kind and required_kind not in ev_kinds:
            missing.append({
                "type": "missing_required_evidence",
                "detail": f"Required evidence kind '{required_kind}' not found",
                "requirement": req,
                "severity": "HIGH",
            })

    return missing


def _completeness_score(evidence: list[dict], requirements: list[dict] | None) -> float:
    if not requirements:
        return 1.0
    ev_kinds = {ev.get("evidence_kind", "") for ev in evidence}
    req_kinds = {r.get("evidence_kind", r.get("kind", "")) for r in requirements}
    if not req_kinds:
        return 1.0
    return len(ev_kinds & req_kinds) / len(req_kinds)
