"""Per-project JSON datastore.

Each project onboarded through the Delivery Intent flow gets a persisted
`ProjectRecord` (domain/project.py) seeded from the one canonical
phases/lanes template in harness/project_dashboard.py
(DEFAULT_PHASES/DEFAULT_LANE_DEFINITIONS) — the same template the
standalone/no-project DEMO dashboard already uses, minus the DEMO-only
`script` field (a freshly onboarded project has produced nothing yet).

One JSON file per project, following the same plain-file convention as
agentcore_config.json / harness/connection_tester.py — no database.
"""
from __future__ import annotations

import copy
import datetime
import json
import uuid
from pathlib import Path
from typing import Optional

from domain.project import ProjectRecord
from harness.project_dashboard import DEFAULT_LANE_DEFINITIONS, DEFAULT_PHASE_LABELS, DEFAULT_PHASES

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_PROJECTS_DIR = _PROJECT_ROOT / "data" / "projects"


def create_project(title: str, delivery_type_id: Optional[str] = None) -> ProjectRecord:
    project_id = f"P-{uuid.uuid4().hex[:8]}"
    phases = [{"key": key, "label": DEFAULT_PHASE_LABELS[key]} for key in DEFAULT_PHASES]
    lanes = [
        {key: value for key, value in copy.deepcopy(lane).items() if key != "script"}
        for lane in DEFAULT_LANE_DEFINITIONS
    ]
    record = ProjectRecord(
        project_id=project_id,
        title=title,
        delivery_type_id=delivery_type_id,
        created_at=datetime.datetime.utcnow().isoformat() + "Z",
        phases=phases,
        lanes=lanes,
    )
    _save(record)
    return record


def load_project(project_id: str) -> Optional[ProjectRecord]:
    path = _PROJECTS_DIR / f"{project_id}.json"
    if not path.exists():
        return None
    try:
        return ProjectRecord.model_validate_json(path.read_text())
    except (json.JSONDecodeError, ValueError, OSError):
        return None


def _save(record: ProjectRecord) -> None:
    _PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    (_PROJECTS_DIR / f"{record.project_id}.json").write_text(record.model_dump_json(indent=2))
