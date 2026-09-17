"""API routes for the AgentCore Connection Tester.

No configure() wiring needed here (unlike live_routes.py/dashboard_routes.py)
— harness/connection_tester.py has no session/bus dependency, it reads its
settings from agentcore_config.json + env vars on every call.
"""
from __future__ import annotations

from fastapi import APIRouter

from harness.connection_tester import ConnectionSettings, load_settings, save_settings, run_connection_test

router = APIRouter(prefix="/api/connection-tester", tags=["connection-tester"])


@router.get("/settings")
def get_settings():
    return load_settings().to_dict()


@router.post("/settings")
def update_settings(payload: dict):
    current = load_settings()
    updated = ConnectionSettings(
        credentials_path=payload.get("credentials_path", current.credentials_path),
        profile=payload.get("profile", current.profile),
        region=payload.get("region", current.region),
        project=payload.get("project", current.project),
    )
    save_settings(updated)
    return updated.to_dict()


@router.post("/test")
def run_test(payload: dict | None = None):
    """Test with the given settings if provided (without persisting them
    — a dry run), otherwise test with whatever is currently saved."""
    if payload:
        current = load_settings()
        settings = ConnectionSettings(
            credentials_path=payload.get("credentials_path", current.credentials_path),
            profile=payload.get("profile", current.profile),
            region=payload.get("region", current.region),
            project=payload.get("project", current.project),
        )
    else:
        settings = load_settings()
    return run_connection_test(settings)
