# Changelog

All notable changes to the Data SDLC Framework are documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
