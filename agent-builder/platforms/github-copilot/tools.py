"""CLI tool wrappers — bridge between terminal commands and core Python modules.

Each function accepts simple arguments, calls the core module, and returns JSON.
Designed to be invoked from the CLI or from GitHub Copilot's terminal tool.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from agent_builder.core.analyser import DeliveryModelAnalyser
from agent_builder.core.models import (
    ActivityClassification,
    AgentDesign,
    AgentRole,
    InvolvementCode,
    SkillMapping,
)
from agent_builder.core.renderer import render_design_document, render_agent_manifest
from agent_builder.core.skills import SkillCatalogue
from agent_builder.core.splitter import evaluate_splitting


def locate_delivery_model(model_root: str) -> dict[str, Any]:
    """Check if a delivery model exists and list its activities."""
    analyser = DeliveryModelAnalyser(model_root)
    return analyser.locate_model()


def analyse_activities(
    model_root: str,
    role_name: str,
    primary_responsibility: str,
) -> dict[str, Any]:
    """Read all activities and return content for classification."""
    analyser = DeliveryModelAnalyser(model_root)
    model_info = analyser.locate_model()

    if not model_info.get("found"):
        return {"error": f"Delivery model not found at {model_root}", "model_info": model_info}

    activities = analyser.read_all_activities()
    role = AgentRole(role_name, primary_responsibility)

    result = {
        "role": {"name": role_name, "role_id": role.role_id, "responsibility": primary_responsibility},
        "model": model_info,
        "activities": [],
    }

    for activity in activities:
        if "error" in activity:
            continue
        prompt = analyser.build_classification_prompt(activity, role)
        result["activities"].append({
            "activity_id": activity["activity_id"],
            "filename": activity.get("filename", ""),
            "sections": activity.get("sections", []),
            "classification_prompt": prompt,
            "content_preview": activity.get("content", "")[:500],
        })

    return result


def run_splitting_evaluation(
    role_name: str,
    primary_responsibility: str,
    classifications: list[dict[str, str]],
    criteria_results: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Evaluate whether the agent should be split into sub-agents."""
    role = AgentRole(role_name, primary_responsibility)
    parsed_classifications = [
        ActivityClassification(
            activity_id=c["activity_id"],
            activity_name=c["activity_name"],
            classification=InvolvementCode(c["classification"]),
            rationale=c.get("rationale", ""),
        )
        for c in classifications
    ]

    result = evaluate_splitting(role, parsed_classifications, criteria_results)

    return {
        "decision": result.decision.value,
        "rationale": result.rationale,
        "split_score": result.split_score,
        "keep_score": result.keep_score,
        "criteria": [
            {"name": c.name, "recommendation": c.recommendation, "rationale": c.rationale}
            for c in result.criteria
        ],
        "proposed_subagents": result.proposed_subagents,
    }


def check_skills(proposed_skill_ids: list[str]) -> dict[str, Any]:
    """Check the skill catalogue for existing skills and duplicates."""
    catalogue = SkillCatalogue(PROJECT_ROOT / "agent-builder" / "agent-skills")
    return {
        "existing_skills": catalogue.existing_skills,
        "duplicates": [sid for sid in proposed_skill_ids if catalogue.check_duplicate(sid)],
        "proposed_count": len(proposed_skill_ids),
        "duplicate_count": sum(1 for sid in proposed_skill_ids if catalogue.check_duplicate(sid)),
    }


def render_design(design_data: dict[str, Any]) -> dict[str, Any]:
    """Render design document and agent manifest from structured data."""
    role = AgentRole(
        role_name=design_data["role_name"],
        primary_responsibility=design_data["primary_responsibility"],
        role_id=design_data.get("role_id", ""),
    )

    classifications = [
        ActivityClassification(
            activity_id=c.get("activity_id", ""),
            activity_name=c.get("activity_name", ""),
            classification=InvolvementCode(c.get("classification", "OUT_OF_SCOPE")),
            rationale=c.get("rationale", ""),
            source_file=c.get("source_file", ""),
        )
        for c in design_data.get("classifications", [])
    ]

    skills = [
        SkillMapping(
            skill_id=s.get("skill_id", ""),
            description=s.get("description", ""),
            layer=s.get("layer", 2),
            applicable_when=s.get("applicable_when", "always"),
            is_existing=s.get("is_existing", False),
            responsibilities_covered=s.get("responsibilities_covered", []),
        )
        for s in design_data.get("skills", [])
    ]

    design = AgentDesign(
        role=role,
        classifications=classifications,
        responsibilities=design_data.get("responsibilities", []),
        inputs=design_data.get("inputs", []),
        outputs=design_data.get("outputs", []),
        decisions=design_data.get("decisions", []),
        tools=design_data.get("tools", []),
        knowledge=design_data.get("knowledge", []),
        skills=skills,
        workflow_steps=design_data.get("workflow_steps", []),
        handoffs=design_data.get("handoffs", []),
        evaluation_metrics=design_data.get("evaluation_metrics", []),
        constraints=design_data.get("constraints", []),
        delivery_model_root=design_data.get("delivery_model_root", ""),
    )

    doc = render_design_document(design)
    manifest = render_agent_manifest(design)

    output_dir = PROJECT_ROOT / "agent-builder" / "agent-designs"
    output_dir.mkdir(exist_ok=True)

    design_path = output_dir / f"{role.role_id}_Agent_Design.md"
    manifest_path = output_dir / f"{role.role_id}_agent-template.yaml"
    design_path.write_text(doc, encoding="utf-8")
    manifest_path.write_text(manifest, encoding="utf-8")

    return {
        "design_file": str(design_path),
        "manifest_file": str(manifest_path),
        "design_preview": doc[:500],
        "manifest_preview": manifest[:500],
    }


def run_full_pipeline(
    model_root: str,
    role_name: str,
    primary_responsibility: str,
    classifications: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Run the complete pipeline: locate → analyse → split → render.

    If classifications are not provided, only locate + analyse are run
    (the LLM must classify activities before split and render can proceed).
    """
    results: dict[str, Any] = {"steps": []}

    # Step 2: Locate
    model_info = locate_delivery_model(model_root)
    results["steps"].append({"step": "locate", "result": model_info})
    if not model_info.get("found"):
        results["error"] = "Delivery model not found"
        return results

    # Step 3: Analyse
    analysis = analyse_activities(model_root, role_name, primary_responsibility)
    results["steps"].append({
        "step": "analyse",
        "activity_count": len(analysis.get("activities", [])),
        "role": analysis.get("role"),
    })

    if not classifications:
        results["status"] = "paused_at_classification"
        results["next_step"] = "Classify activities and re-run with --classifications-file"
        results["activities"] = analysis.get("activities", [])
        return results

    # Step 3.5: Split evaluation
    split_result = run_splitting_evaluation(role_name, primary_responsibility, classifications)
    results["steps"].append({"step": "split", "result": split_result})

    # Step 4: Skills check
    skills_result = check_skills([])
    results["steps"].append({"step": "skills", "result": skills_result})

    # Steps 5-6: Render (minimal design from classifications)
    design_data = {
        "role_name": role_name,
        "primary_responsibility": primary_responsibility,
        "delivery_model_root": model_root,
        "classifications": classifications,
    }
    render_result = render_design(design_data)
    results["steps"].append({"step": "render", "result": render_result})

    results["status"] = "complete"
    return results
