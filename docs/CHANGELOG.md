# Changelog

All notable changes to the Data SDLC Framework are documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
