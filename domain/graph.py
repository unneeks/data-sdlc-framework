"""
Graph engine managing Technical Twin & Delivery Twin nodes and computing impact analysis.
"""
from typing import List, Dict, Any

class DigitalTwinGraph:
    def __init__(self, project_seed: Dict[str, Any]):
        self.project_name = project_seed.get("project", {}).get("name", "Customer 360")
        self.data_assets = project_seed.get("data_assets", [])
        self.pipelines = project_seed.get("pipelines", [])
        self.lineage_edges = project_seed.get("lineage_edges", [])

    def get_technical_twin(self) -> Dict[str, Any]:
        return {
            "project_name": self.project_name,
            "data_assets": self.data_assets,
            "pipelines": self.pipelines
        }

    def compute_technical_impact(self, change_id: str) -> Dict[str, Any]:
        # Hero Demo scenario: Lakehouse Redirection & Source Feed change
        return {
            "change_id": change_id,
            "root_changed_files": [
                "terraform/lakehouse_ingestion.tf",
                "pipelines/salesforce_customer_ingest.py",
                "models/staging/schema.yml"
            ],
            "redirected_assets": [
                {"name": "dw_staging.customer_events", "new_target": "lakehouse_raw.customer_events", "type": "BigLake / Parquet Storage"}
            ],
            "impacted_downstream_models": [
                {"id": "M-01", "name": "stg_lakehouse_customers.sql", "type": "dbt model", "status": "IMPACTED"},
                {"id": "M-02", "name": "customer_profile.sql", "type": "dbt model", "status": "IMPACTED"},
                {"id": "M-03", "name": "customer_360.sql", "type": "dbt model", "status": "IMPACTED"},
                {"id": "M-04", "name": "customer_quality_report.sql", "type": "dbt model", "status": "IMPACTED"}
            ],
            "affected_pipelines_count": 14,
            "affected_assets_count": 25,
            "status_classification": {
                "Changed": 3,
                "Redirected": 2,
                "Impacted": 14,
                "Tested": 10,
                "Safe": 45,
                "Risk": 1
            }
        }

    def compute_delivery_impact(self, change_id: str) -> Dict[str, Any]:
        return {
            "change_id": change_id,
            "affected_delivery_tasks": [
                {"phase": "Architecture", "task": "Feasibility Assessment & Risk Analysis", "status": "COMPLETED"},
                {"phase": "Design", "task": "Target Data & Schema Design", "status": "COMPLETED"},
                {"phase": "Design", "task": "Pipeline Technical Spec & Infrastructure Plan", "status": "COMPLETED"},
                {"phase": "Development", "task": "Source Feed Endpoint Modification", "status": "COMPLETED"},
                {"phase": "Testing", "task": "Source-to-Target Data Reconciliation", "status": "FAILED"},
                {"phase": "Operations", "task": "Lakehouse Operational Runbook Update", "status": "MISSING"}
            ],
            "affected_gates": [
                {"name": "Architectural Feasibility Gate", "status": "PASSED"},
                {"name": "Security & Governance Gate", "status": "PASSED"},
                {"name": "Release Readiness Gate", "status": "BLOCKED"}
            ],
            "required_artifacts": [
                {"name": "Feasibility & Risk Assessment Report", "status": "VERIFIED"},
                {"name": "Target Schema Mapping Specification", "status": "VERIFIED"},
                {"name": "Terraform Execution Plan", "status": "VERIFIED"},
                {"name": "Source-Target Data Reconciliation Report", "status": "FAILED_EVIDENCE"},
                {"name": "Updated Lakehouse Operational Runbook", "status": "MISSING"}
            ]
        }
