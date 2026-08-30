"""Delivery Process skills — discover processes, validate checklists, assess gates.

Covers three related skills from the metamodel:
- delivery-process-discovery
- checklist-validation
- gate-readiness-assessment
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def discover_delivery_process(
    repository_root: str,
    discovered_files: list[dict],
    project_seed: dict | None = None,
) -> dict[str, Any]:
    """Discover the delivery process from documentation and project seed.

    Returns:
        {
            "phases": [...],
            "tasks": [...],
            "gates": [...],
            "checklists": [...],
        }
    """
    root = Path(repository_root)
    doc_files = [f for f in discovered_files if f.get("entity_type") == "documentation"]

    phases = []
    tasks = []
    gates = []
    checklists = []

    for df in doc_files:
        try:
            content = (root / df["path"]).read_text(errors="replace")[:20_000]
        except OSError:
            continue

        phase = _extract_phase(df["path"], content)
        if phase:
            phases.append(phase)
            tasks.extend(phase.get("tasks", []))
            if phase.get("gate"):
                gates.append(phase["gate"])
            checklists.extend(phase.get("checklists", []))

    if project_seed:
        for phase_data in project_seed.get("delivery_phases", []):
            seed_phase = {
                "phase_number": phase_data.get("phase"),
                "name": phase_data.get("name"),
                "status": phase_data.get("status"),
                "gate": {
                    "name": phase_data.get("gate"),
                    "status": phase_data.get("status"),
                },
                "source": "project_seed",
                "provenance": "OBSERVED",
            }
            existing = [p for p in phases if p.get("name") == phase_data.get("name")]
            if not existing:
                phases.append(seed_phase)

    return {
        "phases": phases,
        "tasks": tasks,
        "gates": gates,
        "checklists": checklists,
        "summary": {
            "total_phases": len(phases),
            "total_tasks": len(tasks),
            "total_gates": len(gates),
        },
    }


def validate_checklist(
    checklist_items: list[dict],
    evidence: list[dict],
    delivery_model: dict | None = None,
) -> dict[str, Any]:
    """Validate checklist items against available evidence.

    Returns:
        {
            "items": [...],
            "summary": {"satisfied": N, "unsatisfied": N, "total": N},
            "overall_status": "PASSED|FAILED|PARTIAL",
        }
    """
    results = []
    for item in checklist_items:
        item_id = item.get("id", item.get("name", ""))
        matched_evidence = _match_evidence(item, evidence)
        status = "SATISFIED" if matched_evidence else "UNSATISFIED"
        results.append({
            "item_id": item_id,
            "name": item.get("name", item_id),
            "required": item.get("required", True),
            "status": status,
            "evidence": matched_evidence,
            "provenance": "OBSERVED" if matched_evidence else "INFERRED",
        })

    satisfied = sum(1 for r in results if r["status"] == "SATISFIED")
    unsatisfied = sum(1 for r in results if r["status"] == "UNSATISFIED" and r["required"])

    if unsatisfied == 0:
        overall = "PASSED"
    elif satisfied > 0:
        overall = "PARTIAL"
    else:
        overall = "FAILED"

    return {
        "items": results,
        "summary": {
            "total": len(results),
            "satisfied": satisfied,
            "unsatisfied": len(results) - satisfied,
            "required_unsatisfied": unsatisfied,
        },
        "overall_status": overall,
    }


def assess_gate_readiness(
    gate_name: str,
    checklist_result: dict,
    test_result: dict | None = None,
    impact_result: dict | None = None,
) -> dict[str, Any]:
    """Assess readiness for a delivery gate.

    Returns:
        {
            "gate": str,
            "ready": bool,
            "blockers": [...],
            "evidence_summary": {...},
            "recommendation": str,
        }
    """
    blockers = []

    if checklist_result.get("overall_status") == "FAILED":
        blockers.append({
            "type": "checklist_failure",
            "detail": f"{checklist_result['summary']['required_unsatisfied']} required items unsatisfied",
            "severity": "BLOCKING",
        })
    elif checklist_result.get("overall_status") == "PARTIAL":
        unsatisfied = [
            i for i in checklist_result.get("items", [])
            if i["status"] == "UNSATISFIED" and i["required"]
        ]
        for item in unsatisfied:
            blockers.append({
                "type": "missing_evidence",
                "detail": f"No evidence for required item: {item['name']}",
                "severity": "BLOCKING",
            })

    if test_result:
        if test_result.get("overall_status") == "FAILED":
            failed_count = test_result.get("summary", {}).get("failed", 0)
            blockers.append({
                "type": "test_failure",
                "detail": f"{failed_count} tests failed",
                "severity": "BLOCKING",
            })

    if impact_result:
        risk = impact_result.get("risk_level", "LOW")
        if risk in ("CRITICAL", "HIGH") and impact_result.get("regulatory_impact"):
            if not any(b["type"] == "checklist_failure" for b in blockers):
                blockers.append({
                    "type": "risk_advisory",
                    "detail": f"Risk level {risk} with regulatory impact — requires additional sign-off",
                    "severity": "ADVISORY",
                })

    ready = not any(b["severity"] == "BLOCKING" for b in blockers)

    if ready and not blockers:
        recommendation = f"Gate '{gate_name}' is ready to proceed."
    elif ready:
        recommendation = f"Gate '{gate_name}' can proceed with advisories noted."
    else:
        recommendation = f"Gate '{gate_name}' is BLOCKED. {len(blockers)} issue(s) must be resolved."

    return {
        "gate": gate_name,
        "ready": ready,
        "blockers": blockers,
        "evidence_summary": {
            "checklist_status": checklist_result.get("overall_status"),
            "test_status": test_result.get("overall_status") if test_result else "NOT_RUN",
            "risk_level": impact_result.get("risk_level") if impact_result else "UNKNOWN",
        },
        "recommendation": recommendation,
        "provenance": "OBSERVED",
    }


def _extract_phase(path: str, content: str) -> dict | None:
    match = re.match(r"(\d+)-(.+?)(?:/|$)", path.split("docs/")[-1] if "docs/" in path else path)
    if not match:
        return None

    phase_num = int(match.group(1))
    phase_name = match.group(2).replace("-", " ").replace("_", " ").title()

    tasks = []
    for m in re.finditer(r"^#{2,3}\s+(.+)", content, re.MULTILINE):
        heading = m.group(1).strip()
        if len(heading) > 5 and not heading.startswith("#"):
            tasks.append({"name": heading, "source": path, "provenance": "OBSERVED"})

    gate = None
    for m in re.finditer(r"(?:gate|approval|sign.?off|review)[:.\s]+(.+)", content, re.IGNORECASE):
        gate = {"name": m.group(1).strip()[:100], "source": path, "provenance": "OBSERVED"}
        break

    checklist_items = []
    for m in re.finditer(r"[-*]\s*\[[ x]\]\s*(.+)", content):
        checklist_items.append({
            "name": m.group(1).strip(),
            "required": True,
            "source": path,
            "provenance": "OBSERVED",
        })

    return {
        "phase_number": phase_num,
        "name": phase_name,
        "tasks": tasks,
        "gate": gate,
        "checklists": checklist_items,
        "source": path,
        "provenance": "OBSERVED",
    }


def _match_evidence(item: dict, evidence: list[dict]) -> list[dict]:
    matched = []
    item_name = item.get("name", "").lower()
    item_keywords = set(item_name.split())

    for ev in evidence:
        ev_desc = (ev.get("test_path", "") + " " + ev.get("description", "")).lower()
        ev_kind = ev.get("evidence_kind", "")
        if any(kw in ev_desc for kw in item_keywords if len(kw) > 3):
            matched.append(ev)
        elif ev_kind in ("test_result", "checklist_result") and "test" in item_name:
            matched.append(ev)
    return matched
