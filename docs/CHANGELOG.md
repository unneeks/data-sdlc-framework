# Changelog

All notable changes to the Data SDLC Framework are documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.10.0] - 2026-09-17

### Changed

- **Project Dashboard token cost is now priced from a real, live AWS Price List rate instead of a hardcoded placeholder** (see `docs/adr/0013-live-bedrock-pricing-for-project-dashboard-cost.md`):
  - New `harness/bedrock_pricing.py::get_bedrock_model_pricing(model_id)` fetches real on-demand $/1K-token input+output pricing per Bedrock model from the AWS Price List API (`pricing` boto3 client, always pinned to `us-east-1`), cached in memory per process. Fails soft to `None` on any ambiguity or error — never guesses, never falls back to a hardcoded rate.
  - `harness/agentcore_invocation_metrics.py`'s `PRICE_PER_1K_INPUT_USD`/`PRICE_PER_1K_OUTPUT_USD` constants and `TokenUsage.estimated_cost_usd` are removed entirely. `InvocationMetricsTracker.start_lane()` now accepts a `model_id` and attempts a live pricing fetch only for AgentCore-backed lanes; `lane_snapshot()`/`project_snapshot()` gain a `cost_available: bool` field, with `token_cost_usd` now `None` (not `0`) whenever cost isn't available.
  - GitHub Copilot fallback lanes and DEMO-mode lanes — which have no real AgentCore invocation to price — now show cost as explicitly unavailable ("N/A" in the UI) rather than a heuristic-based dollar figure. `apps/web/src/components/ProjectDashboard.tsx`'s three cost tiles updated accordingly.
  - 11 new/updated tests across `tests/test_bedrock_pricing.py` (new) and `tests/test_project_dashboard.py`.

## [0.9.0] - 2026-09-17

### Added

- **AgentCore connection settings elevated app-wide** (see `docs/adr/0012-agentcore-settings-elevation-and-harness-invoke-testing.md`):
  - New defaults in `harness/connection_tester.py`: region `ap-southeast-2` (was `us-west-2`), credentials path `~/.aws/credentials`, profile `default`.
  - New `build_boto3_client()` — every real AgentCore-calling code path (`harness/live_session.py`, `agents/runner.py`, `harness/metrics.py`'s two functions, `harness/adapters/agentcore_adapter.py`) now builds its boto3 client through it, honoring an explicit saved Connection Tester setting while preserving each site's own existing fallback when unconfigured. `agents/runner.py`'s `_run_harness` also stopped hardcoding `region = "us-west-2"` and now reads the deployed harness's own configured region, matching `live_session.py`.
  - The top-of-app status bar now reflects real connectivity instead of assuming REAL mode means reachable: `GET /api/status` and `POST /api/harness/mode` both return a live `agentcore_connectivity` snapshot (reusing the same settings/test the Connection Tester page uses), and the banner turns red with a reason when it fails.
- **Two new interactive tests on the AgentCore Connection Tester page**, both built on the existing Live Agent Orchestrator's session/streaming/tool-call machinery with zero new backend endpoints:
  - **Invoke Harness** — pick a harness, submit a prompt, watch the response stream in; pending client-tool-call requests get the same inline Approve/Deny card `AgentOrchestratorWorkflow.tsx` already uses.
  - **Test Local Callback** — sends an engineered prompt that makes the harness call the `client_git_status` client tool (exercising ADR 0006's `CLIENT_TOOL_CALL_REQUESTED`/`RESOLVED` bridge end to end); on receipt, a new popup shows "Tool call message received" and automatically approves + executes it, then shows the result — a full round trip in one click.
- 18 new tests across `tests/test_connection_tester.py` (extended), `tests/test_agentcore_adapter.py`, `tests/test_harness_metrics.py`, `tests/test_agent_runner_harness_region.py`, and `tests/test_agentcore_connectivity_snapshot.py` (all new).

## [0.8.0] - 2026-09-17

### Added

- **Ontology instance data** — `ontology/data-sdlc.owl` and `.rdfs` previously defined the `DeliveryPhase`/`DeliveryArtifact`/`DeliveryRole` classes with zero individuals; they now carry real instance data mirroring `apps/web/src/data/metamodel.json` exactly (see `docs/adr/0011-ontology-instance-data.md`):
  - 10 `DeliveryPhase` individuals (Discovery → Transition to BAU), 4 `DeliveryRole` individuals (one per dashboard lane), 28 `DeliveryArtifact` individuals (Infrastructure (Terraform), dbt Models, and all other work products) — added to both files identically.
  - Two new properties added where none fit: `reviewGate` (boolean, on `DeliveryArtifact`) and `artifactInPhase`/`producedByRole` (linking an artifact directly to its phase/role, since the existing `hasArtifact` property's domain is `DeliveryTask` and this app has no task-level individuals).
  - `tests/test_ontology_delivery_artifacts.py` (4 new tests) — parses both ontology files and `metamodel.json`, asserting they never drift out of sync.
  - Explicit non-goal, unchanged from ADR 0010: work products still don't vary by delivery type; this only populates instance data for the existing, delivery-type-agnostic set.

## [0.7.0] - 2026-09-17

### Added

- **Project-specific dashboard datastore** — the Project Dashboard's phases/lanes/artifacts, previously a single hardcoded Python template shared by every session, are now seeded and persisted per project at onboarding (see `docs/adr/0010-project-specific-dashboard-datastore.md`):
  - `harness/project_store.py` — `create_project()`/`load_project()`, one JSON file per project at `data/projects/{project_id}.json` (gitignored, runtime-created), seeded from `harness/project_dashboard.py`'s `DEFAULT_PHASES`/`DEFAULT_PHASE_LABELS`/`DEFAULT_LANE_DEFINITIONS` (renamed from `PHASES`/`PHASE_LABELS`/`LANE_DEFINITIONS`, which remain the standalone/no-project DEMO template unchanged).
  - `domain/project.py`: new `ProjectRecord` model.
  - New API surface: `apps/api/project_routes.py` — `POST /api/projects`, `GET /api/projects/{project_id}`.
  - `apps/api/dashboard_routes.py`'s `POST /api/dashboard/start` accepts an optional `project_id`; when present, the session loads that project's persisted title/phases/lanes instead of the defaults (404 on an unknown id).
  - `ProjectDashboardSession` now accepts optional `title`/`phases`/`phase_labels`/`lane_definitions` overrides; a persisted project's lanes carry no DEMO `script`, so DEMO mode on one simply leaves every work product `NOT_STARTED` instead of crashing.
  - Frontend: accepting a delivery type (or picking one from the catalog) in the "Delivery Intent" onboarding screen now calls `POST /api/projects` and navigates straight to the dashboard with the real project title, instead of discarding the choice; "Project Discovery" is untouched in this pass.
  - 9 new tests across `tests/test_project_store.py` and `tests/test_dashboard_routes.py`, plus 1 new test in `tests/test_project_dashboard.py`.

## [0.6.0] - 2026-09-17

### Added

- **AgentCore Connection Tester** (`apps/web/src/components/AgentCoreConnectionTester.tsx`, sidebar → Settings & Connectivity) — a dedicated page to diagnose AWS/AgentCore connectivity from the operator's own machine, independent of any other feature (see `docs/adr/0009-agentcore-connection-tester.md`):
  - `harness/connection_tester.py` — resolves a configurable credentials path (a JSON credentials export, or a standard AWS credentials file at a path that doesn't have to be `~/.aws/credentials`), an AWS profile, a region, and a project label, with the same env-var-then-persisted-override precedence `harness/repo_sync_config.py` already established. Region/project default from `AGENTCORE_AWS_REGION`/`AGENTCORE_PROJECT`.
  - Two-stage connectivity test: `sts.get_caller_identity()` to validate the AWS session itself, then `bedrock-agentcore-control.list_harnesses()` to specifically confirm AgentCore access — reported separately so "credentials are fine but no AgentCore permission" is distinguishable from "credentials don't work."
  - New API surface: `GET/POST /api/connection-tester/settings`, `POST /api/connection-tester/test`.
  - Settings persist to `agentcore_config.json["connection_tester"]`, editable and re-testable from the UI without restarting the app.
  - 12 new tests in `tests/test_connection_tester.py`.

## [0.5.0] - 2026-09-17

### Added

- **S3-bridged code/document sync** for AgentCore Harness environments with no direct network access to source control (see `docs/adr/0008-s3-bridged-code-and-document-sync.md`):
  - `domain/events.py` — `SdlcEventEnvelope`, a single message shape for every event (`SDLCEventType.CODE_PUSHED_TO_S3` / `DOCUMENT_PUBLISHED`), durably JSON-serializable to S3.
  - `agents/skills/code_sync.py` — three new tools (`sync_code_from_s3`, `push_code_to_s3`, `publish_documents`), registered as ordinary `agents/tool_registry.yaml`/`agents/tools/definitions.py` entries so both `LiveAgentSession` and the CLI's `AgentRunner` path dispatch them identically, with no turn-loop changes.
  - `harness/s3_event_log.py` — `SdlcEventPoller`, a project-wide watcher (independent of any single agent session) that reads the S3-backed event log (one object per event under a sortable key, since S3 has no true append), with a durable local cursor, bounded-retry handler dispatch, and dead-lettering for malformed events or poison-pill handlers.
  - `harness/code_sync_apply.py` — imports an incoming code change into the developer's real local repo as a new local branch via `git fetch <tmp> HEAD:refs/heads/agentcore/<branch>`, which structurally never touches the working tree or index; never forces a non-fast-forward, retrying into a timestamped side branch instead. Uses a content-addressed, deterministic synthetic commit (`git commit-tree` over a fixed identity/timestamp) so redelivering the same event is a verified no-op.
  - `harness/document_sync_apply.py` — downloads published documents to a local directory.
  - `harness/repo_sync_config.py` — configurable bucket/prefixes, falling back to the existing knowledgebase bucket if unset.
  - `.agentcore/skills/code-sync/skill.md` — the agent-facing skill doc.
  - `bootstrap_repo_sync.py` — one-time script to seed the initial S3 code baseline.
  - `apps/api/repo_sync_routes.py` (`/api/repo-sync/status`, `/api/repo-sync/events`), wired into `apps/api/main.py`'s startup.
  - Fixed a real, pre-existing gap found while wiring this up: `setup_agentcore.py`'s IAM policy had no S3 statements at all (unlike `agents/conventions/provisioner.py`'s).
  - `agents/runner.py`/`harness/live_session.py`: `session_id` is now threaded through tool dispatch, since a scratch git workspace needs to be keyed per session rather than per shared `AgentRunner` instance.
  - 27 new tests across `tests/test_repo_sync_events.py`, `tests/test_s3_event_log.py`, `tests/test_code_sync.py`, `tests/test_code_sync_apply.py` — including a direct verification (real git, not just design intent) that applying an incoming change never touches the developer's working tree or staged changes.

## [0.4.0] - 2026-09-17

### Added

- **Project Dashboard workflow UI** (`apps/web/src/components/ProjectDashboard.tsx`, sidebar tab "Project Dashboard") — a project-status view matching a reference screenshot: header stat tiles (elapsed time, token cost, work products, agents active), a 5-phase progress stepper (Requirements → Design → Build → Test → Release), four concurrent agent lane cards (Data Analyst, Data Engineer, Test Engineer, Release Lead) each with a live activity feed and work-product checklist, a Recent Activity feed, a Human Attention Required queue, and a Project Insights panel.
- **`harness/project_dashboard.py`** — runs the four lanes concurrently. Every LIVE lane drives a real `LiveAgentSession` (AgentCore Harness or GitHub Copilot, best-effort agent mapping per lane); a lane whose mapped agent isn't reachable fails only that lane. A work product's human review step reuses the same `EventBus` pause/resume primitive the client-tool bridge (0.3.0) already uses, applied per work product instead of per tool call. DEMO mode is a fully scripted, deterministic, offline simulation.
- **`harness/agentcore_invocation_metrics.py`** — aggregates real per-turn AgentCore token usage (extracted from a new `metadata.usage` block in `agents/runner.py::parse_harness_stream`, which now returns a 3-tuple) into per-lane/per-project cost, token, and elapsed-time figures — the adapter driving the dashboard's LIVE metrics tiles, distinct from and complementary to the CloudWatch-based `harness/metrics.py`.
- **New API surface** (`apps/api/dashboard_routes.py`, mounted under `/api/dashboard`): `start`, `{id}/snapshot`, `{id}/work-products/{lane}/{key}/review`.
- **Metamodel/ontology data gap fixed**: `apps/web/src/data/metamodel.json` gained `delivery_phases` (canonical 10-phase sequence) and `delivery_artifacts` (the dashboard's 28 work products) instances — the `DeliveryPhase`/`DeliveryArtifact` ontology classes existed since v0.1.0 but had never been populated — plus a new `artifact_lifecycle_states` enum and a missing `test-planner-agent` registration. See `docs/adr/0007-project-dashboard-concurrent-lanes.md`.
- `tests/test_project_dashboard.py`: 7 new tests (DEMO snapshot shape, review approve/deny pause-resume, per-lane LIVE failure isolation, metrics aggregation).

## [0.3.0] - 2026-09-17

### Added

- **Live Agent Orchestrator workflow UI** (`apps/web/src/components/AgentOrchestratorWorkflow.tsx`, sidebar tab "Agent Orchestrator") — a Live/Demo-toggled console for invoking agents through either backend:
  - **AgentCore backend** — real AWS Bedrock AgentCore Harness invocations using whatever AWS credentials are already active on the machine (SSO/CLI, via boto3's default chain — no credentials handled by the app).
  - **GitHub Copilot backend** — invokes agents through the existing GitHub Copilot CLI adapter.
  - **Demo mode** — fully scripted, zero network calls, exercising the same pause/approve/resume UX as Live mode.
- **Developer-machine tool bridge** (`harness/client_tools.py`, `harness/live_session.py`) — a curated set of tools (list directory, read file, git status/diff, run tests) that a live agent can ask to run on the operator's own machine rather than in the cloud. The system prompt setup advertises these tools to the model explicitly. When called, the turn loop pauses, publishes a strongly-typed `ClientToolCallRequest` over the existing `EventBus`, and blocks on `bus.wait_for(call_id)` — the same AWAITING_CALLBACK primitive `harness/adapters/client_handoff_adapter.py` already used for CLIENT_RUN steps, applied here per tool call. Only after a human approves it in the UI does the tool actually execute locally and the harness turn resume with the result.
- **AgentCore observability** (`harness/metrics.py`) — AWS identity (`GetCallerIdentity`) and CloudWatch metrics for a configured AgentCore runtime, both degrading gracefully (not failing) without live AWS access.
- **New API surface** (`apps/api/live_routes.py`, mounted under `/api/live`): `agents`, `tools/client`, `aws/identity`, `metrics`, `session/start`, `session/{id}/poll`, `session/{id}/tool-calls/{call_id}/approve|deny`.
- `agents/runner.py`: `parse_harness_stream()` extracted to module level and `AgentRunner.execute_tool()`/`build_prompt()` made public so the live session reuses the exact tool dispatch and Bedrock stream parsing the existing `AgentRunner` REAL mode already relies on, instead of duplicating it.
- `harness/adapters/github_copilot_adapter.py`: second live backend, wrapping the existing `GitHubCopilotCLIAdapter`.

## [0.2.0] - 2026-08-30

### Added

- **5 AgentCore Harness agents** implementing metamodel agent definitions (`agents/harness_agents/registry.py`):
  - `impact-analysis-agent` -- traces change blast radius through dependency graphs, reports risk level and regulatory impact with provenance
  - `regression-agent` -- selects minimal sufficient test set from impact analysis, executes tests, produces evidence for the test-readiness gate
  - `data-quality-agent` -- profiles data assets (schemas, columns, quality indicators) and identifies coverage gaps
  - `data-model-composer` -- discovers entities from schema files and profiling output, maps them to domains with traceability
  - `delivery-compliance-agent` -- discovers delivery process, validates checklists, assesses gate readiness, validates evidence provenance

- **8 deterministic skill implementations** as pure Python functions (`agents/skills/`):
  - `repository_discovery` -- walks file tree, classifies files by type, detects capabilities
  - `dependency_analysis` -- builds dependency graph from imports, dbt refs, SQL references, Spark configs
  - `impact_analysis` -- traces changes through the dependency graph to compute full blast radius
  - `test_selection` -- selects minimal test set covering all impacted entities
  - `test_execution` -- executes (or simulates) selected tests, produces structured evidence
  - `data_profiling` -- profiles schemas, columns, and quality indicators from discovered files
  - `delivery_process` -- discovers phases/tasks/gates/checklists; validates checklists; assesses gate readiness
  - `evidence_validation` -- validates evidence provenance, completeness, and delivery conformance

- **11 tool definitions** for AgentCore Harness inline functions (`agents/tools/definitions.py`), each with JSON Schema input specs and per-agent tool mappings

- **Harness Runner** (`agents/runner.py`) with dual execution modes:
  - `DEMO` mode -- executes agent skill chains locally (deterministic, no LLM), produces same structured output format
  - `REAL` mode -- creates/reuses an AgentCore Harness, invokes it with the agent's system prompt and tools, bridges tool calls back to local skill implementations via a multi-turn conversation loop (up to 20 turns)
  - Execution tracing with session IDs, timestamps, step-by-step logs

- **Workflow Runner** (`agents/workflow.py`) orchestrating a 6-step sequential agent pipeline:
  1. Discovery and Context Build (impact-analysis-agent)
  2. Impact Analysis (impact-analysis-agent)
  3. Data Quality Assessment (data-quality-agent)
  4. Data Model Review (data-model-composer)
  5. Regression Testing (regression-agent)
  6. Delivery Compliance Check (delivery-compliance-agent)
  - Dependency tracking between steps (e.g., regression depends on impact analysis)
  - Evidence accumulation across steps with provenance
  - Support for step-by-step and autonomous (`run_all`) execution

- **11 new API endpoints** (`apps/api/main.py`):
  - `GET /api/agents/harness` -- list agents with harness implementation status
  - `GET /api/agents/skills` -- list metamodel skill metadata
  - `POST /api/agents/run` -- run a specific agent against the test-data corpus
  - `POST /api/agents/context` -- build full digital twin context
  - `GET /api/agents/traces` -- get execution traces
  - `POST /api/workflow/initialize` -- initialize workflow from a test scenario
  - `POST /api/workflow/next` -- execute next workflow step
  - `POST /api/workflow/run-all` -- run all steps autonomously
  - `GET /api/workflow/state` -- get current workflow state
  - `GET /api/workflow/step/{index}` -- get detailed step result
  - `GET /api/scenarios` -- list available test scenarios

- **WorkflowSimulation UI component** (`apps/web/src/components/WorkflowSimulation.tsx`):
  - Scenario selector, Initialize/Next/Run All/Reset controls
  - Agent execution pipeline visualization with phase icons and status colors
  - Expandable step cards showing impact stats, test results, gate assessment, quality profiles
  - Real-time execution log console with color-coded entries
  - Evidence summary panel

- **AgentCore setup script** (`setup_agentcore.py`):
  - Creates IAM execution role with trust policy for bedrock-agentcore service principal
  - Provisions one AgentCore Harness per metamodel agent
  - Polls for READY status with configurable timeout
  - Saves harness ARNs to `agentcore_config.json`
  - Supports `--cleanup` to tear down all harnesses and the IAM role

- **Test suite** (`test_workflow.sh`) -- 13-group bash test exercising all endpoints:
  health check, scenario listing, agent listing, skill metadata, individual agent runs
  (impact, regression, data quality, delivery compliance), context build, workflow
  initialization, step-by-step execution, trace retrieval, and full autonomous run

- **Project ATLAS test-data corpus** (`test-data/`):
  - `atlas_project_seed.json` -- banking platform migration project with data assets and pipelines
  - `atlas_test_scenarios.json` -- 5 change scenarios:
    - ATLAS-CR-001: Add PEP flag to customer accounts (HIGH risk, regulatory)
    - ATLAS-CR-002: Migrate FX Rates domain Oracle to Iceberg (CRITICAL risk, regulatory)
    - ATLAS-CR-003: Fix timestamp precision drift in transaction reconciliation (HIGH risk, regulatory)
    - ATLAS-CR-004: Add IBAN format compliance checks (MEDIUM risk)
    - ATLAS-CR-005: Onboard new counterparty risk data feed (HIGH risk)
  - `agent-demo-de/` -- synthetic repository with code, docs, infrastructure, and CI/CD files

## [0.1.0] - 2026-08-09

### Added

- **Dual-twin metamodel foundation** (`apps/web/src/data/metamodel.json`):
  - 66 entity types across Technical Twin, Delivery Twin, organization, capability, work, evaluation, platform, and context
  - 63 relationship types (19 cross-twin joins) as first-class provenanced objects
  - Four-state provenance model: OBSERVED, INFERRED, HUMAN_VERIFIED, CERTIFIED with executable invariants
  - Blockable mixin -- INFERRED findings cannot block delivery until verified
  - Four-level role chain via first-class EngineeringResponsibility
  - Technical and delivery capabilities as distinct catalogs
  - 21 capabilities across movement, design, quality, governance, operations, and delivery categories
  - 14 metamodel skills with dependency declarations and risk levels
  - 6 evaluation scenarios and 8 evaluation metrics with thresholds and blocking flags
  - 2 evaluation suites (architecture quality, regression agent certification)
  - 5 knowledge packs (project architecture, testing standards, enterprise data standards, business glossary, delivery model)
  - 6 metamodel agents (5 internal + 1 external Copilot coding agent)

- Domain services: DeliveryTypeClassifier, DigitalTwinGraph, EvaluationEngine
- Demo scenario runner and project seed data
- FastAPI backend with classification, planning, impact, testing, RCA endpoints
- React web UI with digital twin visualization
- Harness event bus and orchestrator infrastructure
