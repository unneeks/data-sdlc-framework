# How to Use the Data SDLC Framework

## Quick Start

Five steps to get the full system running:

```bash
# 1. Navigate to the project root
cd /home/participant/feature-deep-dive/data-sdlc-framework

# 2. Install Python dependencies
pip install -r requirements-deploy.txt

# 3. Build the web UI
cd apps/web && npm install && npm run build && cd ../..

# 4. Start the API server
uvicorn apps.api.main:app --host 0.0.0.0 --port 8000

# 5. Run the test suite (in a separate terminal)
./test_workflow.sh
```

The API starts in DEMO mode by default -- no AWS credentials or AgentCore access required.

To switch to REAL mode (AgentCore Harness with LLM orchestration):

```bash
# Provision harnesses (requires AWS credentials)
python setup_agentcore.py

# Switch mode via API
curl -X POST http://localhost:8000/api/harness/mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "REAL"}'
```


## Running Individual Agents

Each agent can be invoked independently via the `/api/agents/run` endpoint.

### Impact Analysis Agent

```bash
curl -s -X POST http://localhost:8000/api/agents/run \
  -H "Content-Type: application/json" \
  -d '{
    "agent_key": "impact-analysis-agent",
    "task_input": {
      "change_description": "Add a new PEP classification flag to customer_accounts",
      "affected_files": [
        "code/ingestion/spark_jobs/customer_accounts_ingestion.py",
        "code/transformation/models/staging/stg_customer_accounts.sql"
      ],
      "change_id": "ATLAS-CR-001"
    }
  }'
```

Returns: `risk_level`, `regulatory_impact`, `directly_affected`, `transitively_affected`, `affected_assets`, `affected_pipelines`, `confidence`, `provenance`.

### Regression Agent

```bash
curl -s -X POST http://localhost:8000/api/agents/run \
  -H "Content-Type: application/json" \
  -d '{
    "agent_key": "regression-agent",
    "task_input": {
      "change_description": "Fix timestamp precision drift in transaction reconciliation",
      "affected_files": [
        "code/ingestion/spark_jobs/transactions_streaming.py",
        "code/transformation/models/staging/stg_transactions.sql"
      ],
      "change_id": "ATLAS-CR-003"
    }
  }'
```

Returns: `impact`, `test_selection`, `test_execution` (with `summary`, `evidence`), `overall_status`.

### Data Quality Agent

```bash
curl -s -X POST http://localhost:8000/api/agents/run \
  -H "Content-Type: application/json" \
  -d '{
    "agent_key": "data-quality-agent",
    "task_input": {
      "change_description": "Profile all data assets in the corpus"
    }
  }'
```

Returns: `profiles`, `quality_indicators`, `gaps`, `recommendations`.

### Data Model Composer

```bash
curl -s -X POST http://localhost:8000/api/agents/run \
  -H "Content-Type: application/json" \
  -d '{
    "agent_key": "data-model-composer",
    "task_input": {
      "change_description": "Review logical data model for the banking platform"
    }
  }'
```

Returns: `entities`, `entity_count`, `profiles`.

### Delivery Compliance Agent

```bash
curl -s -X POST http://localhost:8000/api/agents/run \
  -H "Content-Type: application/json" \
  -d '{
    "agent_key": "delivery-compliance-agent",
    "task_input": {
      "change_description": "Assess release readiness",
      "gate_name": "Release Readiness Gate"
    }
  }'
```

Returns: `delivery_process`, `checklist_result`, `gate_assessment` (with `ready`, `blockers`, `recommendation`), `evidence_validation`.


## Running the Autonomous Workflow

The workflow orchestrates all 6 agents in sequence for a given change scenario.

### Step-by-step execution

```bash
# 1. Initialize from a scenario
curl -s -X POST http://localhost:8000/api/workflow/initialize \
  -H "Content-Type: application/json" \
  -d '{"scenario_id": "ATLAS-CR-003"}'

# 2. Execute steps one at a time
curl -s -X POST http://localhost:8000/api/workflow/next
curl -s -X POST http://localhost:8000/api/workflow/next
# ... repeat for all 6 steps

# 3. Check state at any point
curl -s http://localhost:8000/api/workflow/state

# 4. Inspect a specific step's detailed result
curl -s http://localhost:8000/api/workflow/step/1
```

### Autonomous execution

```bash
# Initialize and run all steps in one call
curl -s -X POST http://localhost:8000/api/workflow/initialize \
  -H "Content-Type: application/json" \
  -d '{"scenario_id": "ATLAS-CR-001"}'

curl -s -X POST http://localhost:8000/api/workflow/run-all
```

### Via the Web UI

Open the application in a browser, navigate to the Workflow Simulation page, select a scenario from the dropdown, click Initialize, then use Next (step-by-step) or Run All (autonomous).


## Understanding the Test Scenarios

Five change scenarios are provided in `test-data/atlas_test_scenarios.json`, modeled on Project ATLAS -- a banking platform migration from Oracle DWH to an Iceberg lakehouse:

| ID | Title | Risk | Regulatory |
|----|-------|------|------------|
| ATLAS-CR-001 | Add PEP flag to customer accounts | HIGH | Yes |
| ATLAS-CR-002 | Migrate FX Rates domain Oracle to Iceberg | CRITICAL | Yes |
| ATLAS-CR-003 | Fix timestamp precision drift in reconciliation | HIGH | Yes |
| ATLAS-CR-004 | Add IBAN format compliance checks | MEDIUM | No |
| ATLAS-CR-005 | Onboard new counterparty risk data feed | HIGH | Yes |

Each scenario includes: expected classification, affected files/assets/pipelines, risk level, a test plan (unit, integration, regression, acceptance criteria), and expected agent behavior.

The test-data corpus at `test-data/agent-demo-de/` contains a synthetic repository with Spark ingestion jobs, dbt transformation models, Airflow DAGs, Great Expectations suites, Soda checks, Terraform modules, CI/CD pipelines, and documentation.


## Reading Agent Results

All agent results follow a consistent pattern:

- **provenance**: either `OBSERVED` (directly read from artifacts) or `INFERRED` (concluded by analysis). See ADR 0005.
- **confidence**: a 0.0-1.0 score on INFERRED findings.
- **evidence**: structured items that can be traced to specific files, checks, or tool invocations.
- **risk_level**: one of `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`.
- **overall_status**: `PASSED` or `FAILED` for agents that produce verdicts.

The gate assessment in the delivery compliance agent produces:
- `ready`: boolean indicating whether the gate can proceed.
- `blockers`: list of items preventing passage, each with `severity` (BLOCKING or ADVISORY) and `detail`.
- `recommendation`: human-readable summary of what to do next.

Key rule: INFERRED findings cannot produce BLOCKING severity. Only OBSERVED, HUMAN_VERIFIED, or CERTIFIED evidence can block delivery.


## Extending with New Agents or Skills

### Adding a new skill

1. Create a new Python file in `agents/skills/` (e.g., `security_scan.py`).
2. Implement a function with typed inputs and a dict return value.
3. Export it from `agents/skills/__init__.py`.
4. Add a tool definition in `agents/tools/definitions.py` with JSON Schema.
5. Map the tool name to the skill function in `AgentRunner._dispatch_tool()` (`agents/runner.py`).

### Adding a new agent

1. Define the agent in `AGENT_CONFIGS` in `agents/harness_agents/registry.py`: system prompt, model, execution model.
2. Add the agent's tool list to `agent_tool_map` in `agents/tools/definitions.py`.
3. Add a DEMO mode skill chain method in `AgentRunner._run_demo()` (`agents/runner.py`).
4. Add the agent key to `AGENT_KEYS` in `setup_agentcore.py` for Harness provisioning.
5. Optionally add a workflow step in `WorkflowRunner.initialize_from_scenario()` (`agents/workflow.py`).


## Architecture Overview

The system is a three-layer architecture: a React web UI, a FastAPI backend with 11 agent endpoints, and a set of 5 metamodel agents backed by 8 deterministic Python skills. Agents execute through a runner that supports both local (DEMO) and AgentCore Harness (REAL) modes. A workflow runner chains agents sequentially with dependency tracking and evidence accumulation, producing a final gate assessment. All findings carry four-state provenance (OBSERVED/INFERRED/HUMAN_VERIFIED/CERTIFIED) to ensure that LLM inferences never silently block delivery.

```
+------------------+     +---------------------+     +-------------------+
|   React Web UI   |---->|   FastAPI Backend    |---->|  AgentCore        |
| WorkflowSim,     |     |  /api/agents/run     |     |  Harness (REAL)   |
| scenario select, |     |  /api/workflow/*      |     |  or               |
| log console      |     |  /api/scenarios       |     |  Local Skills     |
+------------------+     +---------------------+     |  (DEMO)           |
                                  |                   +-------------------+
                                  |                           |
                                  v                           v
                         +------------------+     +---------------------+
                         | Workflow Runner   |     | 8 Skills:           |
                         | 6-step chain,    |     |  discover_repository|
                         | dependency track, |     |  analyze_deps       |
                         | evidence accum.  |     |  analyze_impact     |
                         +------------------+     |  select_tests       |
                                                  |  execute_tests      |
                                                  |  profile_data       |
                                                  |  delivery_process   |
                                                  |  validate_evidence  |
                                                  +---------------------+
                                                          |
                                                          v
                                                  +---------------------+
                                                  | test-data/ corpus   |
                                                  | Project ATLAS       |
                                                  | 5 change scenarios  |
                                                  +---------------------+
```
