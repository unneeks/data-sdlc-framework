"""API routes for creating and loading persisted projects.

Stateless and file-backed (harness/project_store.py) — unlike
apps/api/dashboard_routes.py, this router needs no configure() step.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException

from harness import project_store

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("")
def create_project(payload: dict):
    title = payload.get("title") or "Untitled Project"
    delivery_type_id = payload.get("delivery_type_id")
    record = project_store.create_project(title, delivery_type_id)
    return json.loads(record.model_dump_json())


@router.get("/{project_id}")
def get_project(project_id: str):
    record = project_store.load_project(project_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"unknown project_id: {project_id}")
    return json.loads(record.model_dump_json())
