"""
AgentCore Runtime entrypoint for Data SDLC Framework.

Exposes the platform's core capabilities (classify, plan, impact analysis,
digital twin, evaluation) as an HTTP agent on Bedrock AgentCore Runtime.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from bedrock_agentcore.runtime import BedrockAgentCoreApp  # noqa: E402

from domain.classifier import DeliveryTypeClassifier
from domain.graph import DigitalTwinGraph
from domain.evaluation import EvaluationEngine
from demo.scenarios import ScenarioRunner

root_dir = Path(__file__).parent

def load_json(rel_path: str):
    path = root_dir / rel_path
    if path.exists():
        with open(path, "r") as f:
            return json.load(f)
    return []

delivery_types_data = load_json("marketplace/delivery_types.json")
agents_data = load_json("marketplace/agents.json")
project_seed = load_json("demo/project_seed.json")

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

app = BedrockAgentCoreApp()


@app.entrypoint
def data_sdlc_agent(payload):
    """
    Main entrypoint for the Data SDLC Framework agent.

    Supported actions:
      - classify: Classify a request into delivery types
      - plan: Generate a delivery plan
      - impact: Compute technical + delivery impact analysis
      - twin: Get the digital engineering twin state
      - agents: List available agents in the marketplace
      - evaluate: Run test suite for a change
    """
    action = payload.get("action", "classify")
    prompt = payload.get("prompt", "")

    if action == "classify":
        result = classifier.classify_request(prompt)
        return json.dumps(result, indent=2)

    elif action == "plan":
        primary_type = payload.get("primary_delivery_type", "DATA_PLATFORM_MIGRATION")
        secondary_types = payload.get("secondary_delivery_types", [])
        result = classifier.instantiate_plan(primary_type, secondary_types)
        return json.dumps(result, indent=2)

    elif action == "impact":
        change_id = payload.get("change_id", "CHG-001")
        result = {
            "technical_impact": graph_engine.compute_technical_impact(change_id),
            "delivery_impact": graph_engine.compute_delivery_impact(change_id),
        }
        return json.dumps(result, indent=2)

    elif action == "twin":
        result = {
            "project": project_seed.get("project") if isinstance(project_seed, dict) else {},
            "data_assets": project_seed.get("data_assets", []) if isinstance(project_seed, dict) else [],
            "pipelines": project_seed.get("pipelines", []) if isinstance(project_seed, dict) else [],
        }
        return json.dumps(result, indent=2)

    elif action == "agents":
        return json.dumps(agents_data, indent=2)

    elif action == "evaluate":
        change_id = payload.get("change_id", "CHG-001")
        result = eval_engine.run_test_suite(change_id)
        return json.dumps(result, indent=2)

    else:
        return json.dumps({
            "error": f"Unknown action: {action}",
            "available_actions": ["classify", "plan", "impact", "twin", "agents", "evaluate"],
        })


if __name__ == "__main__":
    app.run()
