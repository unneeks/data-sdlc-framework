"""
FastAPI Backend Server for Agentic Data Engineering Engineering System.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import json
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

@app.get("/api/status")
def read_root():
    return {"system": "Agentic Data Engineering Platform API", "status": "ONLINE"}

@app.get("/api/delivery-types")
def get_delivery_types():
    return delivery_types_data

@app.post("/api/classify")
def classify_prompt(payload: dict):
    prompt = payload.get("prompt", "Move data warehouse to cloud lakehouse")
    return classifier.classify_request(prompt)

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
    return {
        "technical_impact": graph_engine.compute_technical_impact(change_id),
        "delivery_impact": graph_engine.compute_delivery_impact(change_id)
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

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

dist_dir = Path(__file__).resolve().parent.parent / "web" / "dist"
if dist_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(dist_dir / "assets")), name="static-assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        file_path = dist_dir / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(dist_dir / "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
