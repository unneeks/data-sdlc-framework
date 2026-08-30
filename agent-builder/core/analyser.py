"""Delivery Model Analyser — reads delivery model files and extracts design fields.

This is deterministic logic shared across all platforms. The LLM-dependent
parts (classifying activities, extracting entities from prose) are delegated
to the platform-specific agent via callback/tool patterns.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from agent_builder.core.models import (
    ActivityClassification,
    AgentDesign,
    AgentRole,
    ExtractedField,
    InvolvementCode,
)


class DeliveryModelAnalyser:
    """Reads delivery model files and prepares data for LLM classification."""

    def __init__(self, delivery_model_root: str):
        self.root = Path(delivery_model_root)
        self._activity_files: dict[str, Path] = {}
        self._index_content: str = ""

    def locate_model(self) -> dict[str, Any]:
        """Step 2: Check if delivery model exists locally."""
        if not self.root.exists():
            return {"found": False, "path": str(self.root)}

        index_candidates = list(self.root.glob("**/0.0_Delivery_Model*"))
        if not index_candidates:
            index_candidates = list(self.root.glob("**/README.md"))

        activity_files = sorted(
            f for f in self.root.rglob("*.md")
            if re.match(r"\d+\.\d+", f.stem)
        )

        self._activity_files = {f.stem.split("_")[0]: f for f in activity_files}

        if index_candidates:
            self._index_content = index_candidates[0].read_text(encoding="utf-8")

        return {
            "found": True,
            "path": str(self.root),
            "index_file": str(index_candidates[0]) if index_candidates else None,
            "activity_count": len(activity_files),
            "activity_ids": list(self._activity_files.keys()),
            "activity_files": [str(f) for f in activity_files],
        }

    def read_activity(self, activity_id: str) -> dict[str, Any]:
        """Read a single activity file and return its content + metadata."""
        path = self._activity_files.get(activity_id)
        if not path:
            for aid, p in self._activity_files.items():
                if activity_id in aid or aid in activity_id:
                    path = p
                    break
        if not path:
            return {"error": f"Activity {activity_id} not found", "available": list(self._activity_files.keys())}

        content = path.read_text(encoding="utf-8")
        return {
            "activity_id": activity_id,
            "path": str(path),
            "filename": path.name,
            "content": content,
            "sections": self._extract_sections(content),
        }

    def read_all_activities(self) -> list[dict[str, Any]]:
        """Read all activity files."""
        return [self.read_activity(aid) for aid in sorted(self._activity_files.keys())]

    def build_classification_prompt(self, activity: dict[str, Any], role: AgentRole) -> str:
        """Build a prompt for the LLM to classify one activity."""
        return (
            f"Classify this delivery model activity for the **{role.role_name}** agent.\n"
            f"Primary responsibility: {role.primary_responsibility}\n\n"
            f"Activity: {activity['activity_id']} — {activity['filename']}\n\n"
            f"Scan for:\n"
            f"- Responsible/owner role in RACI or stakeholder tables\n"
            f"- Tasks listed under this agent's role\n"
            f"- Inputs received from or outputs sent to this agent\n\n"
            f"Classify as: OWNS | CONTRIBUTES | CONSUMES | OUT_OF_SCOPE\n\n"
            f"Respond with JSON: {{\"classification\": \"...\", \"rationale\": \"...\"}}\n\n"
            f"---\n\n{activity['content'][:8000]}"
        )

    def build_extraction_prompt(self, activity: dict[str, Any], role: AgentRole) -> str:
        """Build a prompt to extract design fields from an OWNS activity."""
        return (
            f"Extract agent design fields from this delivery model activity.\n"
            f"Agent: {role.role_name} ({role.primary_responsibility})\n"
            f"Activity: {activity['activity_id']}\n\n"
            f"Extract as JSON:\n"
            f"{{\n"
            f'  "tasks": [{{"name": "", "description": "", "automatable": true}}],\n'
            f'  "inputs": [{{"name": "", "source": "", "mandatory": true}}],\n'
            f'  "outputs": [{{"name": "", "consuming_activity": ""}}],\n'
            f'  "decisions": [{{"name": "", "human_reserved": false, "rationale": ""}}],\n'
            f'  "tools": [{{"name": "", "purpose": ""}}],\n'
            f'  "knowledge_sources": [{{"name": "", "type": ""}}],\n'
            f'  "quality_checks": [{{"name": "", "metric": ""}}]\n'
            f"}}\n\n"
            f"---\n\n{activity['content'][:8000]}"
        )

    def _extract_sections(self, content: str) -> list[dict[str, str]]:
        """Extract section headings and their content."""
        sections = []
        lines = content.split("\n")
        current_heading = ""
        current_body: list[str] = []

        for line in lines:
            if line.startswith("#"):
                if current_heading:
                    sections.append({"heading": current_heading, "body": "\n".join(current_body).strip()})
                current_heading = line.lstrip("#").strip()
                current_body = []
            else:
                current_body.append(line)

        if current_heading:
            sections.append({"heading": current_heading, "body": "\n".join(current_body).strip()})

        return sections

    def get_index_content(self) -> str:
        return self._index_content

    def get_activity_ids(self) -> list[str]:
        return sorted(self._activity_files.keys())
