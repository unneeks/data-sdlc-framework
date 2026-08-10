"""
Unit tests for domain metamodel, classifier, graph engine, and evaluation harness.
"""
import sys
from pathlib import Path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from domain.classifier import DeliveryTypeClassifier
from domain.graph import DigitalTwinGraph
from domain.evaluation import EvaluationEngine
import json

def test_classifier():
    delivery_types = [
        {"id": "DATA_PLATFORM_MIGRATION", "name": "Migration", "baseline_risk": "HIGH", "default_agents": ["Migration Architect Agent"]},
        {"id": "DATA_PRODUCT_AMENDMENT", "name": "Amendment", "baseline_risk": "MEDIUM", "default_agents": ["Impact Analysis Agent"]}
    ]
    blueprints = [
        {"id": "BP-MIG", "delivery_type_id": "DATA_PLATFORM_MIGRATION", "phases": [{"name": "Architecture", "tasks": [{"name": "Feasibility"}]}]}
    ]
    classifier = DeliveryTypeClassifier(delivery_types, blueprints)
    result = classifier.classify_request("Migrate Teradata DW to Cloud Lakehouse")
    assert result["primary_delivery_type"] == "DATA_PLATFORM_MIGRATION"
    assert result["confidence"] >= 0.90

    plan = classifier.instantiate_plan("DATA_PLATFORM_MIGRATION")
    assert plan["primary_delivery_type"] == "DATA_PLATFORM_MIGRATION"
    assert len(plan["phases"]) > 0

def test_graph_engine():
    graph = DigitalTwinGraph({"project": {"name": "Test Project"}})
    impact = graph.compute_technical_impact("CR-001")
    assert "terraform/lakehouse_ingestion.tf" in impact["root_changed_files"]
    assert impact["status_classification"]["Impacted"] > 0

def test_evaluation_engine():
    engine = EvaluationEngine()
    test_run = engine.run_test_suite("CR-001")
    assert test_run["failed"] == 1
    
    rca = engine.analyze_test_failure("T-05")
    assert rca["confidence"] == 0.93
    assert len(rca["evidence"]) > 0

if __name__ == "__main__":
    test_classifier()
    test_graph_engine()
    test_evaluation_engine()
    print("All unit tests passed successfully!")
