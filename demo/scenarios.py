"""
Demo Scenario Execution Manager powering deterministic demo mode and step-by-step playback.
"""
from typing import Dict, Any, List

class ScenarioRunner:
    def __init__(self):
        self.current_scenario = "SCENARIO_2_LAKEHOUSE_MIGRATION"
        self.step_index = 0
        self.steps = [
            {"step": 1, "phase": "Ingestion", "title": "Change Request Received (CR-2026-8942)", "details": "Request: Redirect Salesforce & SAP source feeds to Cloud Lakehouse"},
            {"step": 2, "phase": "Classification", "title": "Delivery Type Classification", "details": "Classified as DATA_PLATFORM_MIGRATION (96% Confidence)"},
            {"step": 3, "phase": "Architecture", "title": "Feasibility & Risk Assessment", "details": "Feasibility Assessment Agent evaluates BigLake/Iceberg storage & cost"},
            {"step": 4, "phase": "Design", "title": "Target Data & Technical Design", "details": "Data Architecture Agent drafts schema mapping matrix dw_staging ➔ lakehouse_raw"},
            {"step": 5, "phase": "Development", "title": "Pipeline & Infrastructure Code Update", "details": "Generated terraform/lakehouse_ingestion.tf and updated salesforce_customer_ingest.py"},
            {"step": 6, "phase": "Testing", "title": "Source-to-Target Data Reconciliation", "details": "Executed 10 test suites; 9 PASSED, 1 FAILED (Timestamp Precision Format Drift)"},
            {"step": 7, "phase": "RCA", "title": "Automated Root Cause Analysis", "details": "Test Failure Analysis Agent isolated timezone offset error in Parquet conversion"},
            {"step": 8, "phase": "Governance", "title": "Delivery Gate Evaluation", "details": "Release Readiness Gate status: BLOCKED due to reconciliation failure & missing runbook"},
            {"step": 9, "phase": "Remediation", "title": "Automated Remediation & PR Creation", "details": "Proposed timestamp fix in dbt model, updated runbook, and generated Pull Request"}
        ]

    def get_scenario_state(self) -> Dict[str, Any]:
        return {
            "scenario": self.current_scenario,
            "current_step": self.step_index + 1,
            "total_steps": len(self.steps),
            "step_details": self.steps[self.step_index] if self.step_index < len(self.steps) else self.steps[-1]
        }

    def next_step(self) -> Dict[str, Any]:
        if self.step_index < len(self.steps) - 1:
            self.step_index += 1
        return self.get_scenario_state()

    def reset_scenario(self) -> Dict[str, Any]:
        self.step_index = 0
        return self.get_scenario_state()
