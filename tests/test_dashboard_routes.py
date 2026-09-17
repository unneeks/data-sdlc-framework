"""Unit tests for apps/api/dashboard_routes.py's project_id handling.

Calls the route functions directly (this repo's convention — no
TestClient anywhere), with harness/project_store._PROJECTS_DIR
monkeypatched to a tmp_path directory.
"""
import asyncio
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

import harness.project_store as project_store
from apps.api import dashboard_routes
from harness.bus import EventBus


def _use_tmp_projects_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(project_store, "_PROJECTS_DIR", tmp_path / "projects")


def test_start_dashboard_with_unknown_project_id_raises_404(monkeypatch, tmp_path):
    _use_tmp_projects_dir(monkeypatch, tmp_path)
    dashboard_routes.configure(EventBus(), agent_runner=object())

    async def scenario():
        with pytest.raises(HTTPException) as exc_info:
            await dashboard_routes.start_dashboard({"live": False, "project_id": "P-nope"})
        assert exc_info.value.status_code == 404

    asyncio.run(scenario())


def test_start_dashboard_with_known_project_id_uses_its_title(monkeypatch, tmp_path):
    _use_tmp_projects_dir(monkeypatch, tmp_path)
    dashboard_routes.configure(EventBus(), agent_runner=object())

    record = project_store.create_project("My Persisted Project", "SOME_TYPE")

    async def scenario():
        result = await dashboard_routes.start_dashboard({"live": False, "project_id": record.project_id})
        session = dashboard_routes._sessions[result["session_id"]]
        assert session.title == "My Persisted Project"
        assert session.phases == [p["key"] for p in record.phases]
        await asyncio.sleep(0.05)  # let the background session.run() task settle before the loop closes

    asyncio.run(scenario())
