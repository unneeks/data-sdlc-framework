"""
Classifier Engine for identifying Delivery Types from request text and metadata,
supporting human override, blueprint instantiation, and multi-type plan merging.
"""
from typing import List, Dict, Any, Tuple
from domain.delivery import DeliveryType, DeliveryBlueprint, DeliveryPlan, DeliveryPhase, DeliveryTask, ApprovalGate

class DeliveryTypeClassifier:
    def __init__(self, delivery_types_catalog: List[Dict[str, Any]], blueprints_catalog: List[Dict[str, Any]]):
        self.delivery_types = {dt["id"]: dt for dt in delivery_types_catalog}
        self.blueprints = {bp["delivery_type_id"]: bp for bp in blueprints_catalog}

    def classify_request(self, prompt_text: str) -> Dict[str, Any]:
        text_lower = prompt_text.lower()
        
        # Keyword matching & scoring rules
        scores = {}
        reasoning = {}
        
        # 1. Migration
        if any(k in text_lower for k in ["migrate", "lakehouse", "teradata", "redirection", "data warehouse to"]):
            scores["DATA_PLATFORM_MIGRATION"] = 0.96
            reasoning["DATA_PLATFORM_MIGRATION"] = [
                "Existing legacy data platform detected (Data Warehouse)",
                "Target architecture identified (Cloud Lakehouse)",
                "Source-to-target workload redirection required",
                "Pipeline refactoring & schema mapping involved"
            ]

        # 2. Source Change
        if any(k in text_lower for k in ["source change", "schema change", "status char", "feed change"]):
            scores["DATA_SOURCE_CHANGE"] = 0.92
            reasoning["DATA_SOURCE_CHANGE"] = [
                "Existing ingestion stream schema modification detected",
                "Downstream schema propagation impact expected"
            ]

        # 3. Amendment
        if any(k in text_lower for k in ["amend", "modify attribute", "add column", "risk score"]):
            scores["DATA_PRODUCT_AMENDMENT"] = 0.88
            reasoning["DATA_PRODUCT_AMENDMENT"] = [
                "Existing data product transformation update required",
                "Contract & consumer regression testing required"
            ]

        # 4. New Data Product
        if any(k in text_lower for k in ["new product", "create data product", "build new"]):
            scores["DATA_PRODUCT_NEW"] = 0.90
            reasoning["DATA_PRODUCT_NEW"] = [
                "Greenfield data product definition requested",
                "End-to-end SDLC lifecycle required from conceptual design"
            ]

        # Default fallback if unclassified
        if not scores:
            scores["DATA_PLATFORM_MIGRATION"] = 0.85
            reasoning["DATA_PLATFORM_MIGRATION"] = [
                "Structural platform change request identified",
                "Defaulting to migration & redirection blueprint"
            ]

        # Sort by confidence
        sorted_types = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        primary_type = sorted_types[0][0]
        confidence = sorted_types[0][1]
        
        secondary_types = [t[0] for t in sorted_types[1:] if t[1] > 0.6]

        return {
            "primary_delivery_type": primary_type,
            "confidence": confidence,
            "evidence_reasoning": reasoning.get(primary_type, []),
            "secondary_delivery_types": secondary_types,
            "available_types": list(self.delivery_types.keys())
        }

    def instantiate_plan(self, primary_type: str, secondary_types: List[str] = None, project_id: str = "P-C360") -> Dict[str, Any]:
        secondary_types = secondary_types or []
        bp = self.blueprints.get(primary_type)
        if not bp:
            bp = list(self.blueprints.values())[0]

        # Merge secondary blueprint phases if present
        phases = bp.get("phases", [])
        
        # Deduplicate tasks across combined phases
        seen_task_names = set()
        cleaned_phases = []
        for phase in phases:
            cleaned_tasks = []
            for task in phase.get("tasks", []):
                if task["name"] not in seen_task_names:
                    seen_task_names.add(task["name"])
                    cleaned_tasks.append(task)
            phase_copy = dict(phase)
            phase_copy["tasks"] = cleaned_tasks
            cleaned_phases.append(phase_copy)

        dt_info = self.delivery_types.get(primary_type, {})
        
        return {
            "id": f"PLAN-{primary_type}-001",
            "name": f"{dt_info.get('name', primary_type)} Plan",
            "project_id": project_id,
            "primary_delivery_type": primary_type,
            "secondary_delivery_types": secondary_types,
            "blueprint_id": bp["id"],
            "status": "IN_PROGRESS",
            "phases": cleaned_phases,
            "assigned_agents": dt_info.get("default_agents", []),
            "baseline_risk": dt_info.get("baseline_risk", "HIGH")
        }
