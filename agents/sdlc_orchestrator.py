"""SDLC Orchestrator — reads a state machine from orchestrator.md and
delegates agent execution to AgentRunner.

The orchestrator does NOT run agents itself.  It decides WHICH agent to
invoke based on the current state and the incoming event, then hands off
to the runner.  This keeps the runner as a generic execution engine and
the orchestrator as the decision layer.
"""
from __future__ import annotations

import re
import time
import uuid
from pathlib import Path
from typing import Any

from agents.runner import AgentRunner

_AGENTS_DIR = Path(__file__).resolve().parent


class Document:
    """A mock SDLC document that moves through DRAFT -> APPROVED -> FINALIZED."""

    def __init__(self, doc_id: str, title: str, status: str = "DRAFT", content: str = ""):
        self.id = doc_id
        self.title = title
        self.status = status
        self.content = content
        self.created_at = _now()
        self.updated_at = _now()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "content": self.content,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class SDLCOrchestrator:
    """Manages an SDLC workflow driven by a state machine declared in orchestrator.md."""

    def __init__(self, agent_runner: AgentRunner):
        self.agent_runner = agent_runner
        self.id = str(uuid.uuid4())[:8]
        self.state = "INIT"
        self.state_machine = _parse_orchestrator_md()
        self.documents: dict[str, Document] = {}
        self.artifacts: dict[str, dict] = {}
        self.history: list[dict] = []
        self.created_at = _now()
        self.agent_result: dict | None = None

    def get_status(self) -> dict:
        state_def = self.state_machine.get(self.state, {})
        return {
            "orchestrator_id": self.id,
            "current_state": self.state,
            "state_description": state_def.get("description", ""),
            "is_terminal": state_def.get("terminal", False),
            "documents": {k: v.to_dict() for k, v in self.documents.items()},
            "artifacts": self.artifacts,
            "history": self.history,
            "available_events": self._available_events(),
            "created_at": self.created_at,
        }

    def trigger_event(self, event: str, payload: dict | None = None) -> dict:
        """Process an event against the state machine.

        Returns the new status plus any agent result if an agent was invoked.
        """
        payload = payload or {}
        state_def = self.state_machine.get(self.state, {})

        if state_def.get("terminal"):
            return {"error": "Workflow already completed", **self.get_status()}

        transition = self._match_transition(state_def, event, payload)
        if not transition:
            return {
                "error": f"No valid transition for event '{event}' in state '{self.state}'",
                **self.get_status(),
            }

        prev_state = self.state
        target = transition["target"]
        action = transition.get("action", "")
        agent_key = transition.get("agent")
        agent_task = transition.get("task", "")

        record = {
            "timestamp": _now(),
            "from_state": prev_state,
            "event": event,
            "to_state": target,
            "action": action,
            "payload": payload,
        }

        # Execute the action
        agent_result = None
        if action == "initialize_documents":
            self.state = target
            self._init_documents_for_state(target)
        elif action == "finalize_document":
            doc_id = payload.get("document_id", "")
            if doc_id in self.documents:
                self.documents[doc_id].status = "APPROVED"
                self.documents[doc_id].updated_at = _now()
            self.state = target
            self._init_documents_for_state(target)
        elif action == "invoke_agent":
            doc_id = payload.get("document_id", "")
            if doc_id in self.documents:
                self.documents[doc_id].status = "APPROVED"
                self.documents[doc_id].updated_at = _now()
            self.state = target
            agent_result = self._invoke_agent(agent_key, agent_task, payload)
            record["agent_key"] = agent_key
            record["agent_result_summary"] = _summarize_result(agent_result)
            # _invoke_agent may auto-advance state via agent_completed
        elif action == "present_draft":
            artifact_key = transition.get("artifact", "")
            if self.agent_result:
                self.artifacts[artifact_key] = self.agent_result
            self.state = target
            self._init_documents_for_state(target)
        else:
            self.state = target

        self.history.append(record)

        status = self.get_status()
        if agent_result is not None:
            status["agent_result"] = agent_result
        return status

    def _invoke_agent(self, agent_key: str, task_description: str, payload: dict) -> dict:
        """Delegate agent execution to the runner.

        In DEMO mode, returns a pre-built test plan directly.
        In REAL mode, passes the approved documents as context and
        invokes only the test-plan agent — no discovery chain.
        """
        if self.agent_runner.mode == "DEMO":
            result = self._build_demo_agent_result(agent_key)
        else:
            approved_docs = {
                k: v.to_dict() for k, v in self.documents.items()
                if v.status in ("APPROVED", "FINALIZED")
            }

            doc_context = "\n\n".join(
                f"=== {doc['title']} (status: {doc['status']}) ===\n{doc['content']}"
                for doc in approved_docs.values()
            )

            task_input = {
                "change_description": task_description,
                "prompt": (
                    f"{task_description}\n\n"
                    f"The following documents have been approved. "
                    f"Use them as the basis for your output.\n\n"
                    f"{doc_context}"
                ),
            }

            # No discovery tools — the agent receives documents directly
            result = self.agent_runner.run_agent(
                agent_key, task_input, tools_override=[],
            )

        self.agent_result = result
        self._find_transition_target(agent_key)
        return result

    def _build_demo_agent_result(self, agent_key: str) -> dict:
        """Produce the expected agent output directly for DEMO mode."""
        if agent_key == "test-planner-agent":
            return {
                "agent_key": agent_key,
                "test_plan": {
                    "title": "Migration Regression Test Plan",
                    "version": "1.0-DRAFT",
                    "strategy": "Risk-based testing with full reconciliation coverage",
                    "scope": "All affected pipelines and data assets from lakehouse migration",
                },
                "test_cases": [
                    {"id": "TC-01", "name": "Salesforce feed ingestion completeness", "priority": "P1", "category": "Integration", "requirement_trace": "FR-01"},
                    {"id": "TC-02", "name": "SAP feed ingestion completeness", "priority": "P1", "category": "Integration", "requirement_trace": "FR-02"},
                    {"id": "TC-03", "name": "Schema mapping validation", "priority": "P1", "category": "Unit", "requirement_trace": "FR-01, FR-02"},
                    {"id": "TC-04", "name": "Timestamp precision across Parquet conversion", "priority": "P1", "category": "Data Quality", "requirement_trace": "NFR-01"},
                    {"id": "TC-05", "name": "Customer 360 model output consistency", "priority": "P2", "category": "Regression", "requirement_trace": "FR-03"},
                    {"id": "TC-06", "name": "Reconciliation match rate >= 99.95%", "priority": "P1", "category": "Reconciliation", "requirement_trace": "FR-03"},
                    {"id": "TC-07", "name": "Rollback procedure validation", "priority": "P1", "category": "Operational", "requirement_trace": "NFR-03"},
                ],
                "exit_criteria": [
                    "All P1 test cases pass",
                    "No critical defects open",
                    "Reconciliation match rate >= 99.95%",
                    "Rollback tested successfully",
                ],
                "risk_assessment": {
                    "overall_risk": "MEDIUM",
                    "key_risks": [
                        {"risk": "Timestamp precision drift in Parquet conversion", "mitigation": "Dedicated TC-04 with microsecond validation"},
                        {"risk": "Data volume impact on reconciliation performance", "mitigation": "Staged reconciliation with sampling for large tables"},
                    ],
                },
            }
        return {"agent_key": agent_key, "status": "COMPLETED"}

    def _find_transition_target(self, agent_key: str) -> str:
        """After invoking an agent, find and auto-trigger the agent_completed transition."""
        # Look for agent_completed transition in the target state
        for state_name, state_def in self.state_machine.items():
            if state_def.get("agent") == agent_key:
                for t in state_def.get("transitions", []):
                    if t["event"] == "agent_completed":
                        # Auto-advance
                        target = t["target"]
                        self.state = state_name
                        record = {
                            "timestamp": _now(),
                            "from_state": state_name,
                            "event": "agent_completed",
                            "to_state": target,
                            "action": t.get("action", ""),
                        }
                        self.history.append(record)

                        if t.get("action") == "present_draft":
                            artifact_key = t.get("artifact", "test-plan-draft")
                            if self.agent_result:
                                self.artifacts[artifact_key] = self.agent_result
                            self._init_documents_for_state(target)

                        self.state = target
                        return target
        return self.state

    def _match_transition(self, state_def: dict, event: str, payload: dict) -> dict | None:
        for t in state_def.get("transitions", []):
            if t["event"] != event:
                continue
            condition = t.get("condition", "")
            if condition and not self._eval_condition(condition, payload):
                continue
            return t
        return None

    def _eval_condition(self, condition: str, payload: dict) -> bool:
        match = re.match(r'(\w+)\s*==\s*"([^"]+)"', condition)
        if match:
            key, value = match.group(1), match.group(2)
            return payload.get(key) == value
        return True

    def _init_documents_for_state(self, state_name: str):
        state_def = self.state_machine.get(state_name, {})
        for doc_def in state_def.get("documents", []):
            doc_id = doc_def["id"]
            if doc_id not in self.documents:
                self.documents[doc_id] = Document(
                    doc_id=doc_id,
                    title=doc_def["title"],
                    status=doc_def.get("status", "DRAFT"),
                    content=_generate_mock_content(doc_id),
                )

    def _available_events(self) -> list[dict]:
        state_def = self.state_machine.get(self.state, {})
        events = []
        for t in state_def.get("transitions", []):
            events.append({
                "event": t["event"],
                "condition": t.get("condition", ""),
                "target": t["target"],
                "description": t.get("action", ""),
            })
        return events


def _parse_orchestrator_md() -> dict[str, dict]:
    """Parse orchestrator.md into a state machine dict."""
    md_path = _AGENTS_DIR / "orchestrator.md"
    if not md_path.exists():
        return {}

    text = md_path.read_text()
    states: dict[str, dict] = {}
    current_state: str | None = None
    current_transition: dict | None = None
    in_transitions = False
    in_documents = False
    current_doc: dict | None = None

    for line in text.split("\n"):
        stripped = line.strip()

        # State header: ### STATE_NAME
        state_match = re.match(r"^###\s+(\w+)$", stripped)
        if state_match:
            current_state = state_match.group(1)
            states[current_state] = {"transitions": [], "documents": []}
            in_transitions = False
            in_documents = False
            current_transition = None
            current_doc = None
            continue

        if not current_state:
            continue

        state = states[current_state]

        # Top-level state properties
        if stripped.startswith("- description:"):
            state["description"] = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("- terminal:"):
            state["terminal"] = stripped.split(":", 1)[1].strip().lower() == "true"
        elif stripped.startswith("- agent:"):
            state["agent"] = stripped.split(":", 1)[1].strip()

        # Sections
        if stripped == "- transitions:":
            in_transitions = True
            in_documents = False
            continue
        if stripped == "- documents:":
            in_documents = True
            in_transitions = False
            continue

        # Transition entries
        if in_transitions:
            if stripped.startswith("- event:"):
                current_transition = {"event": stripped.split(":", 1)[1].strip()}
                state["transitions"].append(current_transition)
            elif current_transition:
                for key in ("target", "action", "condition", "agent", "task", "artifact"):
                    if stripped.startswith(f"{key}:"):
                        current_transition[key] = stripped.split(":", 1)[1].strip()

        # Document entries
        if in_documents:
            if stripped.startswith("- id:"):
                current_doc = {"id": stripped.split(":", 1)[1].strip()}
                state["documents"].append(current_doc)
            elif current_doc:
                for key in ("title", "status"):
                    if stripped.startswith(f"{key}:"):
                        current_doc[key] = stripped.split(":", 1)[1].strip()

    return states


def _generate_mock_content(doc_id: str) -> str:
    """Generate realistic mock content for SDLC documents."""
    content_map = {
        "requirements-doc": (
            "# Requirements Specification\n\n"
            "## 1. Business Context\n"
            "Migrate Salesforce and SAP source feeds from legacy data warehouse to "
            "cloud lakehouse architecture to reduce operational costs and improve "
            "data freshness.\n\n"
            "## 2. Functional Requirements\n"
            "- FR-01: Redirect all Salesforce CRM feeds to lakehouse ingestion layer\n"
            "- FR-02: Redirect SAP ERP feeds to lakehouse ingestion layer\n"
            "- FR-03: Maintain data reconciliation parity (99.95% match rate)\n"
            "- FR-04: Support both batch and near-real-time ingestion patterns\n\n"
            "## 3. Non-Functional Requirements\n"
            "- NFR-01: End-to-end latency must not exceed 15 minutes for batch feeds\n"
            "- NFR-02: Zero data loss during migration cutover\n"
            "- NFR-03: Rollback capability within 4 hours of cutover\n\n"
            "## 4. Acceptance Criteria\n"
            "- All 14 affected pipelines pass regression tests\n"
            "- Data reconciliation report shows >= 99.95% match\n"
            "- Operational runbook updated and reviewed\n"
        ),
        "design-doc": (
            "# System Design Document\n\n"
            "## 1. Architecture Overview\n"
            "The migration uses a dual-write pattern during transition, with "
            "lakehouse as primary after validation gate passes.\n\n"
            "## 2. Data Flow\n"
            "```\n"
            "Salesforce API -> Cloud Functions -> Lakehouse Raw Layer\n"
            "SAP CDC -> Kafka -> Lakehouse Raw Layer\n"
            "Lakehouse Raw -> dbt Models -> Lakehouse Curated -> BI Tools\n"
            "```\n\n"
            "## 3. Schema Mapping\n"
            "- dw_staging.customer_events -> lakehouse_raw.customer_events\n"
            "- dw_staging.order_transactions -> lakehouse_raw.order_transactions\n"
            "- dw_curated.customer_360 -> lakehouse_curated.customer_360\n\n"
            "## 4. Infrastructure\n"
            "- Storage: BigLake with Iceberg table format\n"
            "- Compute: Spark on Dataproc for batch, Cloud Functions for streaming\n"
            "- Orchestration: Cloud Composer (Airflow)\n"
        ),
        "test-plan": (
            "# Test Plan\n\n"
            "## 1. Scope\n"
            "Regression and integration testing for lakehouse migration.\n\n"
            "## 2. Test Strategy\n"
            "- Unit tests for all modified dbt models\n"
            "- Integration tests for pipeline end-to-end flows\n"
            "- Data reconciliation tests comparing source-to-target\n\n"
            "## 3. Test Cases\n"
            "- TC-01: Salesforce feed ingestion completeness\n"
            "- TC-02: SAP feed ingestion completeness\n"
            "- TC-03: Schema mapping validation\n"
            "- TC-04: Timestamp precision across Parquet conversion\n"
            "- TC-05: Customer 360 model output consistency\n"
            "- TC-06: Reconciliation match rate >= 99.95%\n"
            "- TC-07: Rollback procedure validation\n\n"
            "## 4. Exit Criteria\n"
            "- All critical test cases pass\n"
            "- No P1 defects open\n"
            "- Reconciliation match rate >= 99.95%\n"
        ),
    }
    return content_map.get(doc_id, f"# {doc_id}\n\nDocument content pending.")


def _summarize_result(result: dict) -> dict:
    summary = {}
    for key in ["overall_status", "risk_level", "agent_key", "test_selection", "test_execution"]:
        if key in result:
            val = result[key]
            if isinstance(val, dict) and "summary" in val:
                summary[key] = val["summary"]
            else:
                summary[key] = val
    return summary


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
