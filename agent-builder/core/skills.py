"""Skill catalogue management — check existing, propose new."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agent_builder.core.models import SkillMapping


class SkillCatalogue:
    """Manages the agent-skills catalogue."""

    def __init__(self, skills_root: str | Path):
        self.root = Path(skills_root)
        self._existing: list[dict[str, Any]] = []
        self._load()

    def _load(self):
        readme = self.root / "README.md"
        if not readme.exists():
            return

        content = readme.read_text(encoding="utf-8")
        import re
        for match in re.finditer(r"\|\s*`(\w+)`\s*\|\s*(.+?)\s*\|", content):
            self._existing.append({
                "skill_id": match.group(1),
                "description": match.group(2).strip(),
            })

    @property
    def existing_skills(self) -> list[dict[str, Any]]:
        return self._existing

    def find_matching(self, responsibility: str) -> list[dict[str, Any]]:
        """Find existing skills that might cover a responsibility."""
        resp_lower = responsibility.lower()
        matches = []
        for skill in self._existing:
            words = skill["skill_id"].replace("_", " ").lower().split()
            if any(w in resp_lower for w in words if len(w) > 3):
                matches.append(skill)
        return matches

    def check_duplicate(self, proposed_id: str) -> bool:
        """Check if a proposed skill ID already exists."""
        return any(s["skill_id"] == proposed_id for s in self._existing)

    def build_skill_check_prompt(self, responsibilities: list[dict[str, Any]]) -> str:
        """Build a prompt for the LLM to map responsibilities to skills."""
        existing_list = "\n".join(
            f"  - `{s['skill_id']}`: {s['description']}" for s in self._existing
        ) or "  (no existing skills found)"

        resp_list = "\n".join(
            f"  {i+1}. {r.get('name', r.get('description', str(r)))}"
            for i, r in enumerate(responsibilities)
        )

        return (
            f"Map these responsibilities to skills.\n\n"
            f"Existing skills (reuse if applicable, do NOT duplicate):\n{existing_list}\n\n"
            f"Responsibilities:\n{resp_list}\n\n"
            f"For each responsibility, respond with JSON array:\n"
            f'[{{"responsibility": "...", "skill_id": "...", "is_existing": true/false, '
            f'"description": "...", "layer": 2 or 3, "applicable_when": "..."}}]'
        )
