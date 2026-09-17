"""Unit tests for harness/project_store.py.

_PROJECTS_DIR is always monkeypatched to a tmp_path directory — never the
real project's data/projects/, matching the same monkeypatch convention
tests/test_connection_tester.py uses for _CONFIG_JSON_PATH.
"""
import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

import harness.project_store as project_store
from apps.api import project_routes
from harness.project_dashboard import DEFAULT_LANE_DEFINITIONS, DEFAULT_PHASES


def _use_tmp_projects_dir(monkeypatch, tmp_path):
    projects_dir = tmp_path / "projects"
    monkeypatch.setattr(project_store, "_PROJECTS_DIR", projects_dir)
    return projects_dir


def test_create_project_seeds_from_default_template(monkeypatch, tmp_path):
    _use_tmp_projects_dir(monkeypatch, tmp_path)

    record = project_store.create_project("My Project", "DATA_PLATFORM_MIGRATION")

    assert record.project_id.startswith("P-")
    assert record.title == "My Project"
    assert record.delivery_type_id == "DATA_PLATFORM_MIGRATION"
    assert len(record.phases) == len(DEFAULT_PHASES)
    assert len(record.lanes) == len(DEFAULT_LANE_DEFINITIONS)
    assert all("script" not in lane for lane in record.lanes)


def test_create_project_writes_a_json_file(monkeypatch, tmp_path):
    projects_dir = _use_tmp_projects_dir(monkeypatch, tmp_path)

    record = project_store.create_project("Another Project")

    assert (projects_dir / f"{record.project_id}.json").exists()


def test_load_project_round_trips(monkeypatch, tmp_path):
    _use_tmp_projects_dir(monkeypatch, tmp_path)

    created = project_store.create_project("Round Trip Project", "SOME_TYPE")
    loaded = project_store.load_project(created.project_id)

    assert loaded is not None
    assert loaded == created


def test_load_project_returns_none_for_unknown_id(monkeypatch, tmp_path):
    _use_tmp_projects_dir(monkeypatch, tmp_path)

    assert project_store.load_project("P-nonexistent") is None


def test_load_project_returns_none_for_malformed_json(monkeypatch, tmp_path):
    projects_dir = _use_tmp_projects_dir(monkeypatch, tmp_path)
    projects_dir.mkdir(parents=True)
    (projects_dir / "P-badjson.json").write_text("{not valid json")

    assert project_store.load_project("P-badjson") is None


def test_create_project_endpoint_round_trips(monkeypatch, tmp_path):
    _use_tmp_projects_dir(monkeypatch, tmp_path)

    created = project_routes.create_project({"title": "X", "delivery_type_id": "Y"})
    assert created["title"] == "X"
    assert created["delivery_type_id"] == "Y"

    fetched = project_routes.get_project(created["project_id"])
    assert fetched == created


def test_create_project_endpoint_defaults_title_when_missing(monkeypatch, tmp_path):
    _use_tmp_projects_dir(monkeypatch, tmp_path)

    created = project_routes.create_project({})
    assert created["title"] == "Untitled Project"
    assert created["delivery_type_id"] is None
