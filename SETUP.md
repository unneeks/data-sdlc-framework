# Data SDLC Framework -- AgentCore Setup Guide

This guide walks through deploying the Data SDLC Framework's five metamodel agents
into an Amazon Bedrock AgentCore environment using the Harness pattern.

---

## Architecture Overview

The framework provisions **five AgentCore Harnesses**, one per metamodel agent:

| Agent                        | Purpose                                                |
|:-----------------------------|:-------------------------------------------------------|
| `impact-analysis-agent`      | Trace change blast radius through dependency graph      |
| `regression-agent`           | Select and execute minimal sufficient regression tests  |
| `data-quality-agent`         | Profile data assets and identify quality gaps            |
| `data-model-composer`        | Produce logical data models traceable to requirements    |
| `delivery-compliance-agent`  | Evaluate delivery gates, checklists, and evidence        |

Each Harness is a serverless agent endpoint. When invoked, the Harness routes
tool calls back to local deterministic skill implementations (file scanning,
dependency analysis, test selection, etc.) via the tool-bridging loop in
`agents/runner.py`.

**Two boto3 clients are used:**

- `bedrock-agentcore-control` -- control plane (create/get/delete harnesses)
- `bedrock-agentcore` -- data plane (invoke harnesses with messages and tools)

---

## Prerequisites

### AWS Credentials

Ensure valid AWS credentials are available to boto3 (environment variables,
`~/.aws/credentials`, or an IAM instance role):

```bash
aws sts get-caller-identity
```

### Region

Set the region (default: `us-west-2`):

```bash
export AWS_DEFAULT_REGION=us-west-2
```

### IAM Permissions

The caller (your IAM user or role) needs:

- `iam:CreateRole`, `iam:GetRole`, `iam:PutRolePolicy`,
  `iam:UpdateAssumeRolePolicy`, `iam:DeleteRole`, `iam:DeleteRolePolicy`,
  `iam:ListRolePolicies`, `iam:ListAttachedRolePolicies`, `iam:DetachRolePolicy`
- `bedrock-agentcore-control:CreateHarness`, `bedrock-agentcore-control:GetHarness`,
  `bedrock-agentcore-control:DeleteHarness`
- `bedrock-agentcore:InvokeHarness`
- `sts:GetCallerIdentity`

### Python Dependencies

```bash
cd /home/participant/feature-deep-dive/data-sdlc-framework
pip install boto3
```

Or with uv:

```bash
uv pip install boto3
```

### Node.js (for the Web UI)

```bash
cd /home/participant/feature-deep-dive/data-sdlc-framework/apps/web
npm install
```

---

## Step 1: Run the Setup Script

The setup script creates an IAM execution role and five AgentCore Harnesses,
waits for each to reach READY status, and saves the configuration to
`agentcore_config.json`.

```bash
cd /home/participant/feature-deep-dive/data-sdlc-framework
python setup_agentcore.py
```

This takes approximately 3-5 minutes (harness creation can take up to 150
seconds each). The script:

1. Creates the `DataSDLC_HarnessExecutionRole` IAM role with a trust policy
   for `bedrock-agentcore.amazonaws.com`
2. Attaches permissions for Bedrock model invocation, ECR, CloudWatch, and
   AgentCore operations
3. Creates one Harness per agent (5 total)
4. Polls each Harness until it reaches `READY` status
5. Writes `agentcore_config.json` with all harness ARNs

On success you will see:

```
Setup Summary
============================================================
  READY:  5/5
  Config: /home/participant/feature-deep-dive/data-sdlc-framework/agentcore_config.json
```

---

## Step 2: Start the API Server

The FastAPI backend serves both the REST API and the agent invocation endpoints.

### Demo Mode (no AWS required)

Runs agents using local deterministic skills -- no LLM calls, no Harness needed:

```bash
cd /home/participant/feature-deep-dive/data-sdlc-framework
uv run --with-requirements apps/api/requirements.txt python apps/api/main.py
```

### Real Mode (uses AgentCore Harnesses)

Routes agent invocations through the provisioned Harnesses with Claude Sonnet:

```bash
cd /home/participant/feature-deep-dive/data-sdlc-framework
HARNESS_MODE=REAL uv run --with-requirements apps/api/requirements.txt python apps/api/main.py
```

The API server starts on port 8000. Verify it is running:

```bash
curl http://localhost:8000/api/status
```

Expected response:

```json
{
  "system": "Agentic Data Engineering Platform API",
  "status": "ONLINE",
  "mode": "DEMO"
}
```

---

## Step 3: Start the Web UI

In a separate terminal:

```bash
cd /home/participant/feature-deep-dive/data-sdlc-framework/apps/web
npm run dev
```

The React UI starts on port 3000 and proxies `/api` calls to the backend on
port 8000.

If running in the workshop environment, access via:

```bash
echo "Web UI: $WORKSHOP_URL/app/3000/"
echo "API:    $WORKSHOP_URL/app/8000/api/status"
```

---

## Step 4: Invoke Individual Agents

### Via the API

```bash
# Impact Analysis
curl -X POST http://localhost:8000/api/agents/run \
  -H "Content-Type: application/json" \
  -d '{
    "agent_key": "impact-analysis-agent",
    "task_input": {
      "change_description": "Redirect Salesforce CRM feeds from Teradata to Lakehouse",
      "affected_files": ["code/ingestion/spark_jobs/customer_accounts_ingestion.py"]
    }
  }'

# Data Quality Assessment
curl -X POST http://localhost:8000/api/agents/run \
  -H "Content-Type: application/json" \
  -d '{
    "agent_key": "data-quality-agent",
    "task_input": {
      "change_description": "Assess data quality across all assets"
    }
  }'

# Regression Testing
curl -X POST http://localhost:8000/api/agents/run \
  -H "Content-Type: application/json" \
  -d '{
    "agent_key": "regression-agent",
    "task_input": {
      "change_description": "Add new customer_risk_score column",
      "affected_files": ["code/ingestion/spark_jobs/risk_scores_batch.py"],
      "change_id": "ATLAS-CR-003"
    }
  }'

# Data Model Review
curl -X POST http://localhost:8000/api/agents/run \
  -H "Content-Type: application/json" \
  -d '{
    "agent_key": "data-model-composer",
    "task_input": {
      "change_description": "Review logical data model for completeness"
    }
  }'

# Delivery Compliance
curl -X POST http://localhost:8000/api/agents/run \
  -H "Content-Type: application/json" \
  -d '{
    "agent_key": "delivery-compliance-agent",
    "task_input": {
      "gate_name": "Release Readiness Gate",
      "change_description": "Evaluate gate readiness for ATLAS-CR-003"
    }
  }'
```

### Via the CLI

```bash
cd /home/participant/feature-deep-dive/data-sdlc-framework
python apps/cli/cli_main.py --cli gemini list
python apps/cli/cli_main.py --cli gemini run --agent impact-analysis-agent --prompt "Redirect CRM feeds"
```

### Build Context (Digital Twin)

Scan the test-data corpus to build the full digital twin context:

```bash
curl -X POST http://localhost:8000/api/agents/context
```

---

## Step 5: Run the Autonomous Workflow

The workflow runner orchestrates all five agents in sequence for a test scenario,
passing evidence between stages.

### Initialize a Workflow

```bash
curl -X POST http://localhost:8000/api/workflow/initialize \
  -H "Content-Type: application/json" \
  -d '{"scenario_id": "ATLAS-CR-003"}'
```

### Step Through Manually

```bash
# Execute one step at a time
curl -X POST http://localhost:8000/api/workflow/next

# Check state after each step
curl http://localhost:8000/api/workflow/state
```

### Run All Steps Autonomously

```bash
curl -X POST http://localhost:8000/api/workflow/run-all
```

### Inspect Step Results

```bash
# Get result for step 0 (Discovery), step 1 (Impact Analysis), etc.
curl http://localhost:8000/api/workflow/step/0
curl http://localhost:8000/api/workflow/step/1
```

### Workflow Stages

The autonomous workflow progresses through six steps:

1. **Discovery & Context Build** -- scans the repository to build the digital twin
2. **Impact Analysis** -- traces change blast radius through the dependency graph
3. **Data Quality Assessment** -- profiles data assets and identifies quality gaps
4. **Data Model Review** -- reviews entity relationships and naming conformance
5. **Regression Testing** -- selects and executes minimal sufficient test set
6. **Delivery Compliance Check** -- evaluates gate readiness with collected evidence

### Available Scenarios

```bash
curl http://localhost:8000/api/scenarios
```

---

## Step 6: View Execution Traces

```bash
# Agent execution traces (skill-level detail)
curl http://localhost:8000/api/agents/traces

# AgentCore runtime invocation traces (API-level detail)
curl http://localhost:8000/api/traces
```

---

## Step 7: Switch Between Demo and Real Modes

Toggle the system mode at runtime via the API:

```bash
# Switch to REAL mode (uses AgentCore Harnesses + LLM)
curl -X POST http://localhost:8000/api/harness/mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "REAL"}'

# Switch back to DEMO mode (deterministic local skills)
curl -X POST http://localhost:8000/api/harness/mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "DEMO"}'

# Check current mode
curl http://localhost:8000/api/harness/mode
```

---

## Cleanup

Delete all provisioned harnesses, the IAM role, and the config file:

```bash
cd /home/participant/feature-deep-dive/data-sdlc-framework
python setup_agentcore.py --cleanup
```

This deletes:

- All five AgentCore Harnesses
- The `DataSDLC_HarnessExecutionRole` IAM role and its inline policies
- The `agentcore_config.json` file

---

## Troubleshooting

### Harness stuck in CREATING

Harnesses typically take 60-150 seconds to reach READY. The setup script waits
up to 600 seconds. If it times out, check the AWS console for the harness status
and any failure reasons.

### CREATE_FAILED

Usually caused by IAM role propagation delay or missing permissions. The setup
script waits 10 seconds after creating the role, but in some cases you may need
to re-run `python setup_agentcore.py` after a minute.

### "No runtime_config.json found"

This error appears when the API server cannot find a deployed AgentCore Runtime.
For Harness-based invocation (the pattern used here), ensure you are running in
DEMO mode or that `agentcore_config.json` exists with valid harness ARNs.

### Import errors

Ensure you are running from the project root directory so Python can resolve
the `agents`, `domain`, `harness`, and other packages:

```bash
cd /home/participant/feature-deep-dive/data-sdlc-framework
```

### Region mismatch

Ensure `AWS_DEFAULT_REGION` matches where your harnesses were created. The setup
script defaults to `us-west-2`.

---

## File Reference

| File | Purpose |
|:-----|:--------|
| `setup_agentcore.py` | Creates IAM role + 5 Harnesses, saves config |
| `agentcore_config.json` | Generated config with harness ARNs (git-ignored) |
| `agents/harness_agents/registry.py` | Agent configs: system prompts, model, tool mapping |
| `agents/tools/definitions.py` | Tool schemas in AgentCore Harness inline format |
| `agents/runner.py` | Agent runner with REAL/DEMO mode and tool bridging |
| `agents/workflow.py` | Autonomous workflow orchestration across all agents |
| `apps/api/main.py` | FastAPI backend server |
| `apps/web/` | React frontend (Vite + Tailwind) |
| `apps/cli/cli_main.py` | CLI interface for agent invocation |
| `harness/config.py` | Runtime config (mode, region, ARN) |
| `test-data/` | Sample repository corpus for agent analysis |
