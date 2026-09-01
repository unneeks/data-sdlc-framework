"""
FastAPI Backend Server for Agentic Data Engineering Engineering System.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import uuid
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent.parent
sys_path_added = str(root_dir)
import sys
if sys_path_added not in sys.path:
    sys.path.insert(0, sys_path_added)

from domain.classifier import DeliveryTypeClassifier
from domain.graph import DigitalTwinGraph
from domain.evaluation import EvaluationEngine
from demo.scenarios import ScenarioRunner
from domain.orchestration import AgentEvent, StepStatus, SystemMode
from harness.bus import EventBus
from harness.config import harness_config
from harness.orchestrator import Orchestrator
from harness import store as harness_store

from agents.runner import AgentRunner
from agents.workflow import WorkflowRunner
from agents.harness_agents.registry import list_agents as list_harness_agents, get_skill_metadata

app = FastAPI(
    title="Agentic Data Engineering Platform API",
    description="Digital Engineering Twin & Continuous Delivery Platform API",
    version="1.0.0"
)

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load JSON catalogs
def load_json(rel_path: str):
    path = root_dir / rel_path
    if path.exists():
        with open(path, "r") as f:
            return json.load(f)
    return []

delivery_types_data = load_json("marketplace/delivery_types.json")
agents_data = load_json("marketplace/agents.json")
project_seed = load_json("demo/project_seed.json")

# AgentCore invocation helper
import boto3

_runtime_config_path = root_dir / "runtime_config.json"
_runtime_config = {}
if _runtime_config_path.exists():
    with open(_runtime_config_path) as f:
        _runtime_config = json.load(f)


import time as _time
import logging

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger("agentcore_trace")

_invocation_log = []  # in-memory trace log for the UI


def invoke_agentcore(action: str, **kwargs) -> dict:
    """Invoke the deployed AgentCore runtime and return parsed response."""
    if not _runtime_config:
        return {"error": "No runtime_config.json found — agent not deployed"}
    client = boto3.client("bedrock-agentcore", region_name=_runtime_config["region"])
    payload = {"action": action, **kwargs}
    session_id = str(uuid.uuid4())

    trace_entry = {
        "timestamp": _time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime()),
        "session_id": session_id,
        "action": action,
        "runtime_arn": _runtime_config["runtime_arn"],
        "request_payload": payload,
    }

    _logger.info("→ AgentCore INVOKE | action=%s | session=%s | arn=%s",
                 action, session_id, _runtime_config["runtime_arn"])

    start = _time.time()
    response = client.invoke_agent_runtime(
        agentRuntimeArn=_runtime_config["runtime_arn"],
        runtimeSessionId=session_id,
        payload=json.dumps(payload).encode("utf-8"),
    )
    elapsed_ms = int((_time.time() - start) * 1000)

    body = response.get("response")
    if hasattr(body, "read"):
        raw = body.read().decode("utf-8")
    else:
        raw = str(body)

    status_code = response.get("statusCode", 0)
    trace_entry["status_code"] = status_code
    trace_entry["latency_ms"] = elapsed_ms
    trace_entry["response_metadata"] = response.get("ResponseMetadata", {})

    _logger.info("← AgentCore RESPONSE | action=%s | status=%s | latency=%dms",
                 action, status_code, elapsed_ms)

    try:
        result = json.loads(raw)
        if isinstance(result, str):
            result = json.loads(result)
        trace_entry["response_payload"] = result
    except (json.JSONDecodeError, TypeError):
        result = {"raw": raw}
        trace_entry["response_payload"] = raw

    _invocation_log.append(trace_entry)
    # Keep only last 50 traces
    if len(_invocation_log) > 50:
        _invocation_log.pop(0)

    return result

# Instantiate domain services
classifier = DeliveryTypeClassifier(delivery_types_data, [
    {"id": "BP-MIG-01", "delivery_type_id": "DATA_PLATFORM_MIGRATION", "phases": [
        {"id": "PH-01", "name": "Architecture & Feasibility", "tasks": [{"name": "Feasibility Assessment & Risk Analysis"}]},
        {"id": "PH-02", "name": "Data & Schema Design", "tasks": [{"name": "Target Data & Schema Design"}]},
        {"id": "PH-03", "name": "Technical Design", "tasks": [{"name": "Pipeline Technical Spec & Infrastructure Plan"}]},
        {"id": "PH-04", "name": "Development", "tasks": [{"name": "Source Feed Endpoint Modification"}]},
        {"id": "PH-05", "name": "Testing & Reconciliation", "tasks": [{"name": "Source-to-Target Data Reconciliation"}]},
        {"id": "PH-06", "name": "Governance & Operations", "tasks": [{"name": "Lakehouse Operational Runbook Update"}]}
    ]}
])

graph_engine = DigitalTwinGraph(project_seed if isinstance(project_seed, dict) else {})
eval_engine = EvaluationEngine()
scenario_runner = ScenarioRunner()

# Agent Core Harness wiring: the bus + orchestrator are created at startup
# (they need a running event loop). Regular agent loops are only ever handed
# `event_bus.publish`; only the Orchestrator instance holds the full bus.
event_bus: EventBus = None
orchestrator: Orchestrator = None


@app.on_event("startup")
async def start_harness():
    global event_bus, orchestrator
    event_bus = EventBus()
    orchestrator = Orchestrator(event_bus, harness_config)
    app.state.orchestrator_task = asyncio.create_task(orchestrator.run())


@app.get("/api/status")
def read_root():
    return {
        "system": "Agentic Data Engineering Platform API",
        "status": "ONLINE",
        "mode": harness_config.mode,
        "agentcore_runtime": _runtime_config.get("runtime_arn", "NOT CONFIGURED"),
        "agentcore_connected": bool(_runtime_config),
    }

@app.get("/api/delivery-types")
def get_delivery_types():
    return delivery_types_data

@app.post("/api/classify")
def classify_prompt(payload: dict):
    prompt = payload.get("prompt", "Move data warehouse to cloud lakehouse")
    if harness_config.mode == SystemMode.REAL:
        result = invoke_agentcore("classify", prompt=prompt)
        result["_source"] = "AGENTCORE_RUNTIME"
        result["_runtime_arn"] = _runtime_config.get("runtime_arn", "")
        return result
    result = classifier.classify_request(prompt)
    result["_source"] = "LOCAL_DEMO"
    return result

@app.post("/api/plan")
def create_delivery_plan(payload: dict):
    primary_type = payload.get("primary_delivery_type", "DATA_PLATFORM_MIGRATION")
    secondary_types = payload.get("secondary_delivery_types", [])
    return classifier.instantiate_plan(primary_type, secondary_types)

@app.get("/api/agents")
def get_agents():
    return agents_data

@app.get("/api/digital-twin")
def get_digital_twin():
    return {
        "project": project_seed.get("project") if isinstance(project_seed, dict) else {},
        "data_assets": project_seed.get("data_assets", []) if isinstance(project_seed, dict) else [],
        "pipelines": project_seed.get("pipelines", []) if isinstance(project_seed, dict) else []
    }

@app.get("/api/impact/{change_id}")
def get_impact_analysis(change_id: str):
    if harness_config.mode == SystemMode.REAL:
        result = invoke_agentcore("impact", change_id=change_id)
        result["_source"] = "AGENTCORE_RUNTIME"
        result["_runtime_arn"] = _runtime_config.get("runtime_arn", "")
        return result
    return {
        "technical_impact": graph_engine.compute_technical_impact(change_id),
        "delivery_impact": graph_engine.compute_delivery_impact(change_id),
        "_source": "LOCAL_DEMO",
    }

@app.get("/api/testing/{change_id}")
def get_test_results(change_id: str):
    return eval_engine.run_test_suite(change_id)

@app.get("/api/rca/{test_id}")
def get_rca_analysis(test_id: str):
    return eval_engine.analyze_test_failure(test_id)

@app.get("/api/demo/state")
def get_demo_state():
    return scenario_runner.get_scenario_state()

@app.post("/api/demo/next")
def next_demo_step():
    return scenario_runner.next_step()

@app.post("/api/demo/reset")
def reset_demo():
    return scenario_runner.reset_scenario()

@app.get("/api/cli/commands")
def get_cli_commands():
    return {
        "gemini_cli": [
            "gemini-agent list",
            "gemini-agent run --agent impact-analysis-agent --prompt 'Redirect Salesforce CRM feeds to Lakehouse'",
            "gemini-agent run --agent regression-test-agent --contract CONTRACT-001",
            "gemini-agent run --agent delivery-compliance-agent --contract CONTRACT-001",
            "gemini-agent classify 'Move Teradata data warehouse tables to BigLake Iceberg lakehouse'"
        ],
        "copilot_cli": [
            "gh copilot agent list",
            "gh copilot agent run --agent impact-analysis-agent --prompt 'Calculate delivery impact'",
            "gh copilot agent run --agent test-failure-analysis-agent --prompt 'Analyze reconciliation drift'",
            "gh copilot agent run --agent migration-architect-agent --prompt 'Generate storage mapping'"
        ]
    }

@app.get("/api/traces")
def get_traces():
    """Returns the last 50 AgentCore invocation traces."""
    return {"mode": harness_config.mode, "traces": list(reversed(_invocation_log))}


@app.get("/api/harness/mode")
def get_harness_mode():
    return {"mode": harness_config.mode}

@app.post("/api/harness/mode")
def set_harness_mode(payload: dict):
    harness_config.mode = SystemMode(payload["mode"])
    return {"mode": harness_config.mode}

@app.get("/api/harness/steps/{session_id}")
def get_harness_session_steps(session_id: str):
    return harness_store.get_session_steps(session_id)

@app.post("/api/harness/callback")
async def harness_client_callback(payload: dict):
    step_id = payload["step_id"]
    step = harness_store.get_step(step_id)
    if step is None or step.status != StepStatus.AWAITING_CALLBACK:
        return JSONResponse(status_code=409, content={"error": "no step awaiting callback for this step_id"})

    step.status = StepStatus(payload["status"])
    step.output_payload = payload.get("output")

    event = AgentEvent(
        event_type="CLIENT_CALLBACK_RECEIVED",
        source_agent_id=step.agent_id,
        session_id=step.session_id,
        payload={"step_id": step.id, "status": step.status, "output": step.output_payload},
    )
    resolved = await event_bus.resolve_callback(step_id, event)
    if not resolved:
        return JSONResponse(status_code=409, content={"error": "no loop is currently awaiting this step_id"})
    return {"step_id": step.id, "status": step.status}

# --- AgentCore Harness Agent Runner & Workflow ---
_test_data_root = str(root_dir / "test-data")
_project_seed_path = root_dir / "test-data" / "atlas_project_seed.json"
_test_scenarios_path = root_dir / "test-data" / "atlas_test_scenarios.json"

_project_seed_data = {}
if _project_seed_path.exists():
    with open(_project_seed_path) as f:
        _project_seed_data = json.load(f)

_test_scenarios_data = {}
if _test_scenarios_path.exists():
    with open(_test_scenarios_path) as f:
        _test_scenarios_data = json.load(f)

agent_runner = AgentRunner(
    repository_root=_test_data_root,
    project_seed=_project_seed_data,
    test_scenarios=_test_scenarios_data,
    mode="DEMO",
)

_active_workflow: WorkflowRunner | None = None


@app.post("/api/agents/mode")
def set_agent_mode(payload: dict):
    """Switch agent runner between DEMO and REAL modes."""
    new_mode = payload.get("mode", "DEMO").upper()
    if new_mode not in ("DEMO", "REAL"):
        return JSONResponse(status_code=400, content={"error": "mode must be DEMO or REAL"})
    agent_runner.mode = new_mode
    if new_mode == "REAL":
        agent_runner.reload_harness_config()
    return {
        "mode": agent_runner.mode,
        "harness_arns": dict(agent_runner._harness_arns) if new_mode == "REAL" else {},
    }


@app.get("/api/agents/harness")
def get_harness_agents():
    """List all metamodel agents with harness implementation status."""
    return list_harness_agents()


@app.get("/api/agents/skills")
def get_skills():
    """List all metamodel skill metadata."""
    return get_skill_metadata()


_async_tasks: dict[str, dict] = {}


def _run_in_thread(task_id: str, fn, *args, **kwargs):
    """Run a function in a thread and store the result."""
    import threading
    def worker():
        try:
            result = fn(*args, **kwargs)
            _async_tasks[task_id]["result"] = result
            _async_tasks[task_id]["status"] = "DONE"
        except Exception as e:
            _async_tasks[task_id]["result"] = {"error": str(e)}
            _async_tasks[task_id]["status"] = "FAILED"
    t = threading.Thread(target=worker, daemon=True)
    t.start()


@app.post("/api/agents/run")
def run_agent(payload: dict):
    """Run a specific agent against the test-data corpus."""
    agent_key = payload.get("agent_key", "")
    task_input = payload.get("task_input", {})
    result = agent_runner.run_agent(agent_key, task_input)
    return result


@app.post("/api/agents/context")
def build_context():
    """Build full digital twin context by scanning the corpus."""
    ctx = agent_runner.build_context()
    summary = {
        "files_discovered": ctx.get("discovery", {}).get("summary", {}).get("total_files", 0),
        "capabilities_detected": ctx.get("discovery", {}).get("capabilities_detected", []),
        "dependency_nodes": ctx.get("dependencies", {}).get("summary", {}).get("total_nodes", 0),
        "dependency_edges": ctx.get("dependencies", {}).get("summary", {}).get("total_edges", 0),
        "profiles_count": len(ctx.get("profiles", {}).get("profiles", [])),
        "delivery_phases": len(ctx.get("delivery_process", {}).get("phases", [])),
    }
    return {"summary": summary, "context": ctx}


@app.get("/api/agents/traces")
def get_agent_traces():
    """Get execution traces from agent runs."""
    return {"traces": agent_runner.get_traces()}


@app.post("/api/workflow/initialize")
def initialize_workflow(payload: dict):
    """Initialize a workflow from a test scenario."""
    global _active_workflow
    scenario_id = payload.get("scenario_id", "ATLAS-CR-003")
    _active_workflow = WorkflowRunner(agent_runner, scenario=_test_scenarios_data)
    result = _active_workflow.initialize_from_scenario(scenario_id)
    return result


@app.post("/api/workflow/next")
def workflow_next_step():
    """Kick off the next step asynchronously. Returns immediately."""
    if _active_workflow is None:
        return JSONResponse(status_code=400, content={"error": "No active workflow. Call /api/workflow/initialize first."})
    task_id = f"wf-next-{uuid.uuid4().hex[:8]}"
    _async_tasks[task_id] = {"status": "RUNNING", "result": None}
    _run_in_thread(task_id, _active_workflow.next_step)
    return {"task_id": task_id, "status": "ACCEPTED"}


@app.post("/api/workflow/run-all")
def workflow_run_all():
    """Kick off all remaining steps asynchronously. Returns immediately."""
    if _active_workflow is None:
        return JSONResponse(status_code=400, content={"error": "No active workflow. Call /api/workflow/initialize first."})
    task_id = f"wf-all-{uuid.uuid4().hex[:8]}"
    _async_tasks[task_id] = {"status": "RUNNING", "result": None}
    _run_in_thread(task_id, _active_workflow.run_all)
    return {"task_id": task_id, "status": "ACCEPTED"}


@app.get("/api/workflow/poll/{task_id}")
def poll_task(task_id: str):
    """Poll for async task completion."""
    task = _async_tasks.get(task_id)
    if not task:
        return JSONResponse(status_code=404, content={"error": "Unknown task_id"})
    if task["status"] == "RUNNING":
        state = _active_workflow.get_state() if _active_workflow else {}
        return {"status": "RUNNING", "workflow": state}
    return {"status": task["status"], "result": task["result"]}


@app.get("/api/workflow/state")
def get_workflow_state():
    """Get current workflow state."""
    if _active_workflow is None:
        return {"status": "NO_WORKFLOW", "steps": []}
    return _active_workflow.get_state()


@app.get("/api/workflow/step/{step_index}")
def get_workflow_step_result(step_index: int):
    """Get detailed result for a specific workflow step."""
    if _active_workflow is None:
        return {"error": "No active workflow"}
    result = _active_workflow.get_step_result(step_index)
    if result is None:
        return {"error": f"Step {step_index} not found or not yet executed"}
    return result


@app.get("/api/scenarios")
def get_test_scenarios():
    """List available test scenarios."""
    scenarios = _test_scenarios_data.get("scenarios", [])
    return [
        {
            "id": s["id"],
            "title": s["title"],
            "prompt": s["prompt"],
            "expected_classification": s["expected_classification"],
            "risk_level": s.get("impact", {}).get("risk_level", "UNKNOWN"),
        }
        for s in scenarios
    ]


from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

dist_dir = Path(__file__).resolve().parent.parent / "web" / "dist"
if dist_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(dist_dir / "assets")), name="static-assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        file_path = dist_dir / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(dist_dir / "index.html"), headers={"Cache-Control": "no-cache"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
