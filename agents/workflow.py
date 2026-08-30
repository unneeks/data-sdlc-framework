"""Workflow Runner — orchestrates the full SDLC workflow autonomously.

Progresses through metamodel workflow steps, dispatching agents at each stage,
collecting evidence, evaluating gates, and advancing to the next phase.
"""
from __future__ import annotations

import json
import time
import uuid
from typing import Any

from agents.runner import AgentRunner


class WorkflowStep:
    def __init__(self, step_id: str, name: str, agent_key: str,
                 task_input: dict, phase: str = "", depends_on: list[str] | None = None):
        self.id = step_id
        self.name = name
        self.agent_key = agent_key
        self.task_input = task_input
        self.phase = phase
        self.depends_on = depends_on or []
        self.status = "PENDING"
        self.result: dict | None = None
        self.started_at: str | None = None
        self.completed_at: str | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "agent_key": self.agent_key,
            "phase": self.phase,
            "status": self.status,
            "depends_on": self.depends_on,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "result_summary": _summarize(self.result) if self.result else None,
        }


class WorkflowRunner:
    """Manages a full SDLC workflow with agent orchestration."""

    def __init__(self, agent_runner: AgentRunner, scenario: dict | None = None):
        self.agent_runner = agent_runner
        self.scenario = scenario or {}
        self.id = str(uuid.uuid4())[:8]
        self.steps: list[WorkflowStep] = []
        self.current_step_index = 0
        self.status = "NOT_STARTED"
        self.evidence: list[dict] = []
        self.created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def initialize_from_scenario(self, scenario_id: str) -> dict:
        """Build workflow steps from a test scenario."""
        scenarios = self.scenario.get("scenarios", [])
        target = None
        for s in scenarios:
            if s["id"] == scenario_id:
                target = s
                break

        if not target:
            return {"error": f"Scenario {scenario_id} not found"}

        change_desc = target.get("prompt", "")
        affected_files = [
            f.replace(" (NEW)", "")
            for f in target.get("impact", {}).get("affected_files", [])
        ]
        change_id = target["id"]

        self.steps = [
            WorkflowStep(
                f"WF-{self.id}-01", "Discovery & Context Build",
                "impact-analysis-agent",
                {"change_description": "Scan repository to build digital twin context"},
                phase="Discovery",
            ),
            WorkflowStep(
                f"WF-{self.id}-02", "Impact Analysis",
                "impact-analysis-agent",
                {"change_description": change_desc, "affected_files": affected_files, "change_id": change_id},
                phase="Analysis",
                depends_on=[f"WF-{self.id}-01"],
            ),
            WorkflowStep(
                f"WF-{self.id}-03", "Data Quality Assessment",
                "data-quality-agent",
                {"change_description": change_desc, "change_id": change_id},
                phase="Quality",
                depends_on=[f"WF-{self.id}-01"],
            ),
            WorkflowStep(
                f"WF-{self.id}-04", "Data Model Review",
                "data-model-composer",
                {"change_description": change_desc, "change_id": change_id},
                phase="Design",
                depends_on=[f"WF-{self.id}-01"],
            ),
            WorkflowStep(
                f"WF-{self.id}-05", "Regression Testing",
                "regression-agent",
                {"change_description": change_desc, "affected_files": affected_files, "change_id": change_id},
                phase="Testing",
                depends_on=[f"WF-{self.id}-02"],
            ),
            WorkflowStep(
                f"WF-{self.id}-06", "Delivery Compliance Check",
                "delivery-compliance-agent",
                {
                    "change_description": change_desc,
                    "gate_name": "Release Readiness Gate",
                    "change_id": change_id,
                },
                phase="Governance",
                depends_on=[f"WF-{self.id}-05"],
            ),
        ]
        self.status = "READY"
        return self.get_state()

    def next_step(self) -> dict:
        """Execute the next ready step in the workflow."""
        if self.status == "NOT_STARTED":
            return {"error": "Workflow not initialized. Call initialize_from_scenario first."}

        if self.current_step_index >= len(self.steps):
            self.status = "COMPLETED"
            return self.get_state()

        step = self.steps[self.current_step_index]

        for dep_id in step.depends_on:
            dep_step = next((s for s in self.steps if s.id == dep_id), None)
            if dep_step and dep_step.status != "COMPLETED":
                return {"error": f"Step {step.name} depends on {dep_step.name} which is not complete"}

        step.status = "RUNNING"
        step.started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.status = "IN_PROGRESS"

        task_input = dict(step.task_input)
        if step.agent_key == "delivery-compliance-agent":
            task_input["evidence"] = self.evidence
            prev_test = self._find_step_result("regression-agent")
            if prev_test:
                task_input["test_result"] = prev_test.get("test_execution", prev_test)
            prev_impact = self._find_step_result("impact-analysis-agent")
            if prev_impact:
                task_input["impact_result"] = prev_impact

        result = self.agent_runner.run_agent(step.agent_key, task_input)

        step.result = result
        step.status = "COMPLETED" if "error" not in result else "FAILED"
        step.completed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        new_evidence = self._extract_evidence(step, result)
        self.evidence.extend(new_evidence)

        self.current_step_index += 1

        if self.current_step_index >= len(self.steps):
            self.status = "COMPLETED"

        return self.get_state()

    def run_all(self) -> dict:
        """Run all steps autonomously to completion."""
        while self.current_step_index < len(self.steps) and self.status != "COMPLETED":
            state = self.next_step()
            if "error" in state:
                break
        return self.get_state()

    def get_state(self) -> dict:
        return {
            "workflow_id": self.id,
            "status": self.status,
            "current_step": self.current_step_index,
            "total_steps": len(self.steps),
            "steps": [s.to_dict() for s in self.steps],
            "evidence_count": len(self.evidence),
            "created_at": self.created_at,
        }

    def get_step_result(self, step_index: int) -> dict | None:
        if 0 <= step_index < len(self.steps):
            return self.steps[step_index].result
        return None

    def _find_step_result(self, agent_key: str) -> dict | None:
        for step in self.steps:
            if step.agent_key == agent_key and step.result:
                return step.result
        return None

    def _extract_evidence(self, step: WorkflowStep, result: dict) -> list[dict]:
        evidence = []
        if "test_execution" in result:
            for ev in result["test_execution"].get("evidence", []):
                evidence.append(ev)
        if "evidence_validation" in result:
            for ev in result["evidence_validation"].get("validated", []):
                evidence.append(ev)
        if "risk_level" in result:
            evidence.append({
                "evidence_kind": "impact_analysis",
                "agent_key": step.agent_key,
                "risk_level": result["risk_level"],
                "provenance": "OBSERVED",
                "confidence": result.get("confidence", 0.9),
            })
        if "profiles" in result:
            profiles = result["profiles"]
            if isinstance(profiles, dict):
                count = len(profiles.get("profiles", []))
            elif isinstance(profiles, list):
                count = len(profiles)
            else:
                count = 0
            evidence.append({
                "evidence_kind": "data_profile",
                "agent_key": step.agent_key,
                "profile_count": count,
                "provenance": "OBSERVED",
            })
        return evidence


def _summarize(result: dict | None) -> dict:
    if not result:
        return {}
    s = {}
    for key in ["overall_status", "risk_level", "total_affected_count", "entity_count",
                 "agent_key", "coverage_ratio"]:
        if key in result:
            s[key] = result[key]
    if "test_execution" in result:
        s["test_summary"] = result["test_execution"].get("summary", {})
    if "gate_assessment" in result:
        s["gate_ready"] = result["gate_assessment"].get("ready", False)
    return s
