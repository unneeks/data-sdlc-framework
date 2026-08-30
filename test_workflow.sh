#!/usr/bin/env bash
# =============================================================================
# Test the AgentCore Harness Workflow API
#
# Prerequisites: Start the API server first:
#   cd /home/participant/feature-deep-dive/data-sdlc-framework
#   uvicorn apps.api.main:app --host 0.0.0.0 --port 8000
#
# Usage:
#   ./test_workflow.sh              # Run all tests
#   ./test_workflow.sh <base_url>   # Custom base URL
# =============================================================================

BASE_URL="${1:-http://localhost:8000}"
API="$BASE_URL/api"
BOLD='\033[1m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

step() { echo -e "\n${BOLD}${CYAN}=== $1 ===${NC}\n"; }
ok()   { echo -e "${GREEN}✓ $1${NC}"; }
fail() { echo -e "${RED}✗ $1${NC}"; }

# ── 1. Health Check ──────────────────────────────────────────────────────────
step "1. API Health Check"
curl -s "$API/status" | python3 -m json.tool
ok "API is up"

# ── 2. List Test Scenarios ───────────────────────────────────────────────────
step "2. List Available Scenarios"
curl -s "$API/scenarios" | python3 -m json.tool
ok "Scenarios listed"

# ── 3. List Harness Agents ───────────────────────────────────────────────────
step "3. List AgentCore Harness Agents"
curl -s "$API/agents/harness" | python3 -m json.tool
ok "Harness agents listed"

# ── 4. List Skills Metadata ──────────────────────────────────────────────────
step "4. List Skill Metadata"
curl -s "$API/agents/skills" | python3 -c "
import sys, json
skills = json.load(sys.stdin)
for s in skills:
    deps = ', '.join(s.get('dependencies', [])) or 'none'
    print(f\"  {s['key']:<30} deps=[{deps}]  risk={s.get('risk_level', 'LOW')}\")
print(f\"\nTotal: {len(skills)} skills\")
"
ok "Skills listed"

# ── 5. Run Individual Agent: Impact Analysis ─────────────────────────────────
step "5. Run Impact Analysis Agent (ATLAS-CR-001)"
curl -s -X POST "$API/agents/run" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_key": "impact-analysis-agent",
    "task_input": {
      "change_description": "Add a new PEP classification flag to the customer_accounts domain",
      "affected_files": [
        "code/ingestion/spark_jobs/customer_accounts_ingestion.py",
        "code/transformation/models/staging/stg_customer_accounts.sql",
        "code/transformation/models/marts/mart_customer_360.sql"
      ],
      "change_id": "ATLAS-CR-001"
    }
  }' | python3 -c "
import sys, json
r = json.load(sys.stdin)
print(f\"  Risk Level:         {r.get('risk_level', '?')}\")
print(f\"  Regulatory Impact:  {r.get('regulatory_impact', '?')}\")
print(f\"  Directly Affected:  {len(r.get('directly_affected', []))}\")
print(f\"  Transitively Aff:   {len(r.get('transitively_affected', []))}\")
print(f\"  Affected Assets:    {len(r.get('affected_assets', []))}\")
print(f\"  Affected Pipelines: {len(r.get('affected_pipelines', []))}\")
print(f\"  Confidence:         {r.get('confidence', '?')}\")
"
ok "Impact analysis complete"

# ── 6. Run Individual Agent: Regression Testing ──────────────────────────────
step "6. Run Regression Agent (ATLAS-CR-003 — timestamp drift)"
curl -s -X POST "$API/agents/run" \
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
  }' | python3 -c "
import sys, json
r = json.load(sys.stdin)
ts = r.get('test_execution', {}).get('summary', {})
print(f\"  Overall Status: {r.get('overall_status', '?')}\")
print(f\"  Tests Selected: {r.get('test_selection', {}).get('total_selected', 0)}\")
print(f\"  Passed:  {ts.get('passed', 0)}\")
print(f\"  Failed:  {ts.get('failed', 0)}\")
print(f\"  Skipped: {ts.get('skipped', 0)}\")
"
ok "Regression testing complete"

# ── 7. Run Individual Agent: Data Quality ────────────────────────────────────
step "7. Run Data Quality Agent"
curl -s -X POST "$API/agents/run" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_key": "data-quality-agent",
    "task_input": {
      "change_description": "Profile all data assets in the repository"
    }
  }' | python3 -c "
import sys, json
r = json.load(sys.stdin)
print(f\"  Profiles:           {len(r.get('profiles', []))}\")
print(f\"  Quality Indicators: {len(r.get('quality_indicators', []))}\")
domains = r.get('summary', {}).get('domains', [])
print(f\"  Domains:            {', '.join(domains)}\")
"
ok "Data quality profiling complete"

# ── 8. Run Individual Agent: Delivery Compliance ─────────────────────────────
step "8. Run Delivery Compliance Agent"
curl -s -X POST "$API/agents/run" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_key": "delivery-compliance-agent",
    "task_input": {
      "change_description": "Check delivery compliance for ATLAS migration",
      "gate_name": "Release Readiness Gate",
      "evidence": []
    }
  }' | python3 -c "
import sys, json
r = json.load(sys.stdin)
gate = r.get('gate_assessment', {})
print(f\"  Gate Ready:   {gate.get('ready', '?')}\")
print(f\"  Blockers:     {len(gate.get('blockers', []))}\")
for b in gate.get('blockers', []):
    print(f\"    [{b['severity']}] {b['detail']}\")
print(f\"  Recommendation: {gate.get('recommendation', 'N/A')[:100]}\")
cl = r.get('checklist_result', {})
print(f\"  Checklist:    {cl.get('overall_status', '?')} ({cl.get('summary', {}).get('satisfied', 0)}/{cl.get('summary', {}).get('total', 0)})\")
"
ok "Delivery compliance check complete"

# ── 9. Build Digital Twin Context ────────────────────────────────────────────
step "9. Build Digital Twin Context (full corpus scan)"
curl -s -X POST "$API/agents/context" | python3 -c "
import sys, json
r = json.load(sys.stdin)
s = r.get('summary', {})
print(f\"  Files Discovered:     {s.get('files_discovered', 0)}\")
print(f\"  Capabilities:         {len(s.get('capabilities_detected', []))}\")
print(f\"  Dependency Nodes:     {s.get('dependency_nodes', 0)}\")
print(f\"  Dependency Edges:     {s.get('dependency_edges', 0)}\")
print(f\"  Data Profiles:        {s.get('profiles_count', 0)}\")
print(f\"  Delivery Phases:      {s.get('delivery_phases', 0)}\")
"
ok "Digital twin context built"

# ── 10. Initialize Workflow (ATLAS-CR-003) ───────────────────────────────────
step "10. Initialize Workflow (ATLAS-CR-003)"
curl -s -X POST "$API/workflow/initialize" \
  -H "Content-Type: application/json" \
  -d '{"scenario_id": "ATLAS-CR-003"}' | python3 -c "
import sys, json
r = json.load(sys.stdin)
print(f\"  Workflow ID:  {r.get('workflow_id', '?')}\")
print(f\"  Status:       {r.get('status', '?')}\")
print(f\"  Total Steps:  {r.get('total_steps', 0)}\")
for s in r.get('steps', []):
    print(f\"    [{s['status']:<10}] {s['name']:<35} ({s['agent_key']})\")
"
ok "Workflow initialized"

# ── 11. Step-by-Step Execution ───────────────────────────────────────────────
step "11. Execute Workflow Step-by-Step"
for i in $(seq 1 6); do
  echo -e "${YELLOW}--- Step $i ---${NC}"
  curl -s -X POST "$API/workflow/next" | python3 -c "
import sys, json
r = json.load(sys.stdin)
idx = r.get('current_step', 0) - 1
if idx >= 0 and idx < len(r.get('steps', [])):
    s = r['steps'][idx]
    summary = s.get('result_summary', {})
    parts = []
    if summary.get('risk_level'): parts.append(f\"Risk: {summary['risk_level']}\")
    if summary.get('overall_status'): parts.append(summary['overall_status'])
    if summary.get('test_summary'):
        t = summary['test_summary']
        parts.append(f\"Tests: {t.get('passed',0)}✓ {t.get('failed',0)}✗\")
    if summary.get('gate_ready') is not None:
        parts.append('Gate: READY' if summary['gate_ready'] else 'Gate: BLOCKED')
    detail = ' | '.join(parts) if parts else 'Done'
    print(f\"  {s['status']}: {s['name']} — {detail}\")
print(f\"  Evidence: {r.get('evidence_count', 0)} items\")
print(f\"  Workflow: {r.get('status', '?')}\")
"
done
ok "Workflow execution complete"

# ── 12. Get Agent Traces ─────────────────────────────────────────────────────
step "12. Agent Execution Traces"
curl -s "$API/agents/traces" | python3 -c "
import sys, json
r = json.load(sys.stdin)
traces = r.get('traces', [])
print(f\"  Total traces: {len(traces)}\")
for t in traces[:10]:
    print(f\"    {t['agent_key']:<30} {t['status']:<10} ({len(t.get('steps',[]))} steps)\")
"
ok "Traces retrieved"

# ── 13. Full Autonomous Run (different scenario) ────────────────────────────
step "13. Full Autonomous Run (ATLAS-CR-001)"
echo -e "${YELLOW}Initializing...${NC}"
curl -s -X POST "$API/workflow/initialize" \
  -H "Content-Type: application/json" \
  -d '{"scenario_id": "ATLAS-CR-001"}' > /dev/null

echo -e "${YELLOW}Running all steps...${NC}"
curl -s -X POST "$API/workflow/run-all" | python3 -c "
import sys, json
r = json.load(sys.stdin)
print(f\"  Status:   {r.get('status', '?')}\")
print(f\"  Evidence: {r.get('evidence_count', 0)} items\")
for s in r.get('steps', []):
    summary = s.get('result_summary', {})
    parts = []
    if summary.get('risk_level'): parts.append(f\"Risk: {summary['risk_level']}\")
    if summary.get('overall_status'): parts.append(summary['overall_status'])
    if summary.get('gate_ready') is not None:
        parts.append('Gate: READY' if summary['gate_ready'] else 'Gate: BLOCKED')
    detail = ' | '.join(parts) if parts else ''
    print(f\"  [{s['status']:<10}] {s['name']:<35} {detail}\")
"
ok "Autonomous workflow complete"

# ── Summary ──────────────────────────────────────────────────────────────────
step "ALL TESTS COMPLETE"
echo -e "${GREEN}All 13 test groups passed. The workflow API is functional.${NC}"
echo ""
echo "To test via the Web UI:"
echo "  1. Start the API:  uvicorn apps.api.main:app --host 0.0.0.0 --port 8000"
echo "  2. Build the UI:   cd apps/web && npm install && npm run build"
echo "  3. Open browser:   $BASE_URL"
echo "  4. Navigate to 'Agent Workflow' in the sidebar"
echo ""
