# ADR 0010: Project-Specific Dashboard Datastore

## Status

Accepted

## Date

2026-09-17

## Context

`harness/project_dashboard.py`'s `ProjectDashboardSession` already separates rendering from data — `apps/web/src/components/ProjectDashboard.tsx` is a pure render layer driven by a `DashboardSnapshot` the backend assembles. The actual gap was one level down: that assembly drew from a single hardcoded Python template (`PHASES`, `PHASE_LABELS`, `LANE_DEFINITIONS`) shared by every session, and there was no project entity anywhere in the backend at all — no persistence, no identity, nothing onboarding produced. Meanwhile the app has two separate onboarding screens ("Project Discovery" and "Delivery Intent"), and neither created anything durable: `POST /api/plan` (`domain/classifier.py::instantiate_plan`) exists but is never called from the UI and persists nothing regardless of who calls it.

The request was for the dashboard to be driven by a project-specific datastore/JSON instead of hardcoded data, with phases and artifacts produced at onboarding.

## Decision

**Datastore**: one JSON file per project at `data/projects/{project_id}.json`, written with the same `path.write_text(json.dumps(..., indent=2))` style already used for `agentcore_config.json` — no database. `data/projects/` is runtime-created, unlike the committed `demo/project_seed.json` fixture, so it's gitignored.

**Seed template reuse**: `harness/project_dashboard.py`'s `PHASES`/`PHASE_LABELS`/`LANE_DEFINITIONS` are renamed `DEFAULT_PHASES`/`DEFAULT_PHASE_LABELS`/`DEFAULT_LANE_DEFINITIONS` and become the one canonical seed template every new project gets (`harness/project_store.py::create_project`), minus the DEMO-only `script` field — a freshly onboarded project has produced nothing yet, so it seeds `NOT_STARTED` work products rather than a fake in-flight demo. The standalone/no-project DEMO path (navigating to the dashboard tab directly, skipping onboarding) keeps using the same constants *with* `script` intact, so today's scripted demo experience is unchanged.

**Where project creation is wired**: `DeliveryTypeOnboarding`'s "Accept & Instantiate Plan" button and its catalog-card click, not "Project Discovery". Project Discovery's entire 4-stage pipeline is client-side `setTimeout` simulation with no backend calls today; Delivery Intent is the only onboarding screen that already talks to the backend and the only one that knows a `delivery_type_id` at the moment of acceptance. `POST /api/projects` (new `apps/api/project_routes.py`) mints a `project_id`, seeds phases/lanes from the default template, and persists the record.

**Loading path**: `POST /api/dashboard/start` (`apps/api/dashboard_routes.py`) accepts an optional `project_id`. When present, it loads the persisted `ProjectRecord` and passes its `title`/`phases`/`phase_labels`/`lane_definitions` into `ProjectDashboardSession`, which now accepts these as optional constructor overrides defaulting to the `DEFAULT_*` template. No `project_id` → identical behavior to before this change.

**No circular imports**: `harness/project_store.py` imports the `DEFAULT_*` constants from `harness/project_dashboard.py`; `project_dashboard.py` itself never imports `project_store` — it stays persistence-agnostic, and `dashboard_routes.py` (which already imports both) is the one place that decides whether a session loads a project or falls back to defaults.

## Consequences

### Positive

- The dashboard's phases/artifacts are no longer a single global hardcoded template — every onboarded project gets its own persisted, independently loadable record.
- `ProjectDashboardSession`'s override parameters are generic (`phases`, `phase_labels`, `lane_definitions`), so any future seed source (not just onboarding) can drive a session the same way.
- The standalone DEMO dashboard (no onboarding, no `project_id`) is completely unaffected — verified in `tests/test_project_dashboard.py`, whose existing DEMO-shape assertions needed no changes.

### Negative

- **Seeded phases/artifacts do not vary by `delivery_type_id` (explicit non-goal, v1)**: every project gets the identical canonical template regardless of which delivery type was chosen; `delivery_type_id` is stored on the record purely for display/context. Varying the template per delivery type is a natural follow-up — it only touches `project_store.create_project`'s seeding logic, not the schema or the loading path.
- **"Project Discovery" still creates nothing.** Its simulated pipeline stays untouched in this pass; a project only exists once the user goes through "Delivery Intent". A follow-up could wire it in once that flow has a real backend step to attach a `delivery_type_id` to.
- No project listing/picker UI or `GET /api/projects` list endpoint — the id flows through in-memory React state from the one onboarding session that created it. Refreshing the page or reopening the dashboard tab loses the association (falls back to the standalone DEMO experience), same limitation the rest of this app's session-scoped state already has.
- DEMO mode on a persisted project has no scripted progression at all (no `script` field survives seeding) — every work product simply stays `NOT_STARTED` until reviewed/advanced through other means. This is intentional (a freshly onboarded project has done nothing yet) but is a visibly different DEMO experience from the original hardcoded template's in-flight simulation.

## Alternatives Considered

- **Wiring "Project Discovery" instead of, or in addition to, "Delivery Intent"** — rejected for this pass: Project Discovery has no backend call today, and wiring it in would be a materially larger change than reusing the one screen that already round-trips to the API and already knows a delivery type at its acceptance moment.
- **A database instead of one-JSON-file-per-project** — rejected: this repo has no database anywhere; every other piece of persisted config (`agentcore_config.json`, `harness/connection_tester.py`, `harness/repo_sync_config.py`) already uses plain JSON files, and a project record is small, append-rare data with no query needs beyond "load by id."
- **Filtering the seed template by `delivery_type_id` at creation time** — deferred rather than rejected outright; flagged above as the natural v2 follow-up once there's a second, differentiated template to filter against.
