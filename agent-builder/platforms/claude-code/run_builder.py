"""Claude Code Agent Builder — programmatic entry point.

Claude Code can run this directly via `python -m agent_builder.platforms.claude_code.run_builder`
or the skill instructions in agent-builder.md guide Claude Code interactively.

In interactive mode, Claude Code:
- Has native file access (Read, Bash, Edit)
- Can reason across files and ask the user questions
- Uses the skill .md as its instruction set

In programmatic mode, this script drives the core logic:
- Walks the delivery model deterministically
- Builds prompts for Claude Code to classify/extract
- Renders output documents
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from agent_builder.core.analyser import DeliveryModelAnalyser
from agent_builder.core.models import AgentDesign, AgentRole, ActivityClassification, InvolvementCode
from agent_builder.core.renderer import render_design_document, render_agent_manifest
from agent_builder.core.skills import SkillCatalogue
from agent_builder.core.splitter import evaluate_splitting


def build_agent_design(
    role_name: str,
    primary_responsibility: str,
    delivery_model_path: str,
    phase_scope: list[str] | None = None,
) -> dict[str, str]:
    """Build agent design documents from delivery model.

    Returns dict with paths to generated files + prompts for LLM steps.
    In Claude Code, the interactive skill handles the LLM parts.
    This function prepares all the deterministic pieces.
    """
    role = AgentRole(
        role_name=role_name,
        primary_responsibility=primary_responsibility,
        phase_scope=phase_scope or [],
    )

    analyser = DeliveryModelAnalyser(delivery_model_path)
    model_info = analyser.locate_model()

    if not model_info["found"]:
        return {
            "error": f"Delivery model not found at {delivery_model_path}",
            "suggestion": "Provide a valid path to delivery model Markdown files",
        }

    activities = analyser.read_all_activities()

    classification_prompts = []
    for activity in activities:
        prompt = analyser.build_classification_prompt(activity, role)
        classification_prompts.append({
            "activity_id": activity["activity_id"],
            "activity_name": activity["filename"],
            "prompt": prompt,
        })

    extraction_prompts = []
    for activity in activities:
        prompt = analyser.build_extraction_prompt(activity, role)
        extraction_prompts.append({
            "activity_id": activity["activity_id"],
            "prompt": prompt,
        })

    skills_root = PROJECT_ROOT / "agent-builder" / "agent-skills"
    catalogue = SkillCatalogue(skills_root)

    output_dir = PROJECT_ROOT / "agent-builder" / "agent-designs"
    output_dir.mkdir(exist_ok=True)

    return {
        "role": {
            "role_id": role.role_id,
            "role_name": role.role_name,
            "primary_responsibility": role.primary_responsibility,
        },
        "model_info": model_info,
        "activity_count": len(activities),
        "classification_prompts": classification_prompts,
        "extraction_prompts": extraction_prompts,
        "existing_skills": catalogue.existing_skills,
        "output_dir": str(output_dir),
        "design_file": str(output_dir / f"{role.role_id}_Agent_Design.md"),
        "manifest_file": str(output_dir / f"{role.role_id}_agent-template.yaml"),
        "next_step": (
            "Claude Code should now:\n"
            "1. Use classification_prompts to classify each activity\n"
            "2. Use extraction_prompts for OWNS activities to extract fields\n"
            "3. Run evaluate_splitting() with results\n"
            "4. Map skills using SkillCatalogue\n"
            "5. Build AgentDesign and render with render_design_document()"
        ),
    }


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python run_builder.py <role_name> <primary_responsibility> <delivery_model_path>")
        print("Example: python run_builder.py 'Data Engineer' 'automates pipeline development' docs/knowledge-base/")
        sys.exit(1)

    result = build_agent_design(sys.argv[1], sys.argv[2], sys.argv[3])
    print(json.dumps(result, indent=2, default=str))
