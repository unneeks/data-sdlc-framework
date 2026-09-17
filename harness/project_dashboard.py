"""Project Dashboard — a multi-agent SDLC status view.

Runs several agent "lanes" concurrently (Data Analyst, Data Engineer, Test
Engineer, Release Lead), each producing a sequence of work products through
the delivery phases (Requirements -> Design -> Build -> Test -> Release).
Reuses the same building blocks as the single-agent Live Agent Orchestrator
(harness/live_session.py) rather than a parallel implementation:

  - `LiveAgentSession` drives every LIVE lane's actual AgentCore Harness or
    GitHub Copilot invocation — this module does not talk to boto3 or the
    Copilot CLI directly.
  - `EventBus`/`AgentEvent` carries the activity feed shown in "Recent
    Activity", exactly as it does for the single-agent console.
  - The AWAITING_CALLBACK `bus.wait_for`/`resolve_callback` pause-resume
    primitive gates a work product's human review step (the screenshot's
    "Awaiting human review" / "Human Attention Required" panel) — the same
    mechanism `harness/adapters/client_handoff_adapter.py` and
    `LiveAgentSession`'s client-tool bridge already use, applied here at
    the work-product grain.
  - `InvocationMetricsTracker` (harness/agentcore_invocation_metrics.py)
    aggregates the real per-turn token usage `LiveAgentSession` reports in
    LIVE mode into the dashboard's cost/token/elapsed-time tiles.

DEMO mode is a fully scripted, offline simulation matching the reference
screenshot's lane names, work product names, and approval gates — no
network calls, deterministic. LIVE mode maps each lane to a best-effort
real backend agent (see DEFAULT_LANE_DEFINITIONS) and runs one real
`LiveAgentSession` per lane; a lane whose mapped agent isn't provisioned or
reachable fails that lane only (status FAILED, reason shown as its current
activity), it does not take down the rest of the dashboard.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from domain.orchestration import AgentBackend, AgentEvent
from domain.project import LaneStatus, WorkProduct, WorkProductStatus
from harness.agentcore_invocation_metrics import InvocationMetricsTracker, TokenUsage
from harness.bus import EventBus
from harness.live_session import LiveAgentSession

logger = logging.getLogger(__name__)

# Phase keys match the canonical 10-phase DeliveryPhase sequence in
# ontology/data-sdlc.{owl,rdfs} and apps/web/src/data/metamodel.json's
# `delivery_phases` (Discovery..Transition to BAU) — this dashboard only
# surfaces the five phases its four lanes actually produce work for. Labels
# are the shorter product-facing names the reference screenshot uses
# ("Build" for Development, "Test" for Testing); the underlying keys stay
# canonical so this data lines up with the rest of the metamodel.
#
# These are the DEFAULT template: the standalone/no-project DEMO dashboard
# (navigated to directly, without onboarding) uses them as-is; a project
# created at onboarding (harness/project_store.py) seeds its own persisted
# phases/lanes from this same template instead, so this module stays the
# one canonical source either way.
DEFAULT_PHASES = ["requirements", "design", "development", "testing", "release"]
DEFAULT_PHASE_LABELS = {
    "requirements": "Requirements", "design": "Design", "development": "Build",
    "testing": "Test", "release": "Release",
}

# Each lane's `work_products` are exactly what's produced; `script` drives the
# DEMO simulation (work_product_key, delay_seconds, status, version). A key
# with no script entry stays NOT_STARTED for the run — this dashboard depicts
# an in-flight project (status "In Progress"), not a finished one, matching
# the reference screenshot. A persisted project's lane definitions (seeded
# from this template by harness/project_store.py) drop `script` entirely —
# a freshly onboarded project has produced nothing yet, so DEMO mode on one
# just leaves every work product NOT_STARTED (see ProjectLane._run_demo).
DEFAULT_LANE_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "key": "data-analyst",
        "name": "Data Analyst Agent",
        "role": "Elicit, analyse and document requirements",
        "color": "blue",
        "agentcore_agent_id": "impact-analysis-agent",
        "copilot_agent_id": "impact-analysis-agent",
        "prompt": "Elicit, analyse and document the requirements for this data product change.",
        "work_products": [
            {"key": "stakeholder-requirements", "name": "Stakeholder Requirements", "phase": "requirements"},
            {"key": "business-objectives", "name": "Business Objectives", "phase": "requirements"},
            {"key": "solution-requirements", "name": "Solution Requirements", "phase": "requirements", "review_gate": True},
            {"key": "use-cases", "name": "Use Cases", "phase": "requirements"},
            {"key": "data-glossary", "name": "Data Glossary (Initial)", "phase": "requirements"},
            {"key": "jira-features", "name": "JIRA Features", "phase": "requirements"},
            {"key": "requirements-traceability", "name": "Requirements Traceability", "phase": "requirements"},
        ],
        "script": [
            ("stakeholder-requirements", 1.0, "COMPLETED", "v1.1"),
            ("business-objectives", 2.0, "COMPLETED", "v1.0"),
            ("solution-requirements", 3.0, "AWAITING_REVIEW", "v0.3"),
            ("jira-features", 4.0, "COMPLETED", "v1.0"),
        ],
        "activity_text": "Analysing stakeholder feedback and refining acceptance criteria for customer payment data requirements...",
    },
    {
        "key": "data-engineer",
        "name": "Data Engineer Agent",
        "role": "Design, build and test data pipelines",
        "color": "emerald",
        "agentcore_agent_id": "data-quality-agent",
        "copilot_agent_id": "data-quality-agent",
        "prompt": "Design the target data model and build the data pipelines for this change.",
        "work_products": [
            {"key": "data-design", "name": "Data Design (Medallion)", "phase": "design"},
            {"key": "technical-design", "name": "Technical Design", "phase": "design"},
            {"key": "dbt-models", "name": "dbt Models", "phase": "development"},
            {"key": "data-quality-tests", "name": "Data Quality Tests", "phase": "development"},
            {"key": "infrastructure", "name": "Infrastructure (Terraform)", "phase": "development"},
            {"key": "deployment-scripts", "name": "Deployment Scripts", "phase": "development"},
            {"key": "runbook", "name": "Runbook", "phase": "development"},
            {"key": "data-lineage", "name": "Data Lineage Documentation", "phase": "development"},
        ],
        "script": [
            ("data-design", 1.5, "COMPLETED", "v1.0"),
            ("technical-design", 2.5, "IN_PROGRESS", "v0.5"),
            ("dbt-models", 3.5, "IN_PROGRESS", "v0.2"),
        ],
        "activity_text": "Generating dbt models for silver layer and creating data quality tests...",
    },
    {
        "key": "test-engineer",
        "name": "Test Engineer Agent",
        "role": "Create and execute test scenarios",
        "color": "violet",
        "agentcore_agent_id": "test-planner-agent",
        "copilot_agent_id": "regression-test-agent",
        "prompt": "Create system test scenarios based on the functional requirements and data contracts for this change.",
        "work_products": [
            {"key": "test-strategy", "name": "Test Strategy", "phase": "testing"},
            {"key": "test-scenarios", "name": "Test Scenarios", "phase": "testing"},
            {"key": "test-data-sets", "name": "Test Data Sets", "phase": "testing"},
            {"key": "automated-test-scripts", "name": "Automated Test Scripts", "phase": "testing"},
            {"key": "test-execution-report", "name": "Test Execution Report", "phase": "testing"},
            {"key": "defect-log", "name": "Defect Log", "phase": "testing"},
            {"key": "test-summary-report", "name": "Test Summary Report", "phase": "testing"},
        ],
        "script": [
            ("test-strategy", 1.2, "COMPLETED", "v1.0"),
            ("test-scenarios", 2.2, "IN_PROGRESS", "v0.4"),
        ],
        "activity_text": "Generating system test scenarios based on functional requirements and data contracts...",
    },
    {
        "key": "release-lead",
        "name": "Release Lead Agent",
        "role": "Manage release readiness and operations",
        "color": "orange",
        "agentcore_agent_id": "delivery-compliance-agent",
        "copilot_agent_id": "delivery-compliance-agent",
        "prompt": "Assess release readiness and prepare the deployment checklist for this change.",
        "work_products": [
            {"key": "release-plan", "name": "Release Plan", "phase": "release"},
            {"key": "deployment-checklist", "name": "Deployment Checklist", "phase": "release", "review_gate": True},
            {"key": "change-log", "name": "Change Log", "phase": "release"},
            {"key": "release-notes", "name": "Release Notes", "phase": "release"},
            {"key": "go-no-go", "name": "Go/No-Go Assessment", "phase": "release"},
            {"key": "bau-handover", "name": "BAU Handover Pack", "phase": "release"},
        ],
        "script": [
            ("release-plan", 1.3, "IN_PROGRESS", "v0.4"),
            ("deployment-checklist", 2.3, "AWAITING_REVIEW", ""),
        ],
        "activity_text": "Reviewing deployment checklist and waiting for approval of go/no-go criteria...",
    },
]

# Deterministic (not random) per-transition token cost, so DEMO runs are
# reproducible in tests while still looking like real usage.
_DEMO_TOKENS_PER_TRANSITION = TokenUsage(input_tokens=9000, output_tokens=6000)


class ProjectLane:
    def __init__(self, definition: Dict[str, Any], bus: EventBus, metrics: InvocationMetricsTracker) -> None:
        self.key = definition["key"]
        self.name = definition["name"]
        self.role = definition["role"]
        self.color = definition["color"]
        self.definition = definition
        self.status = LaneStatus.RUNNING
        self.current_activity = f"Starting up {definition['name']}…"
        self.work_products: Dict[str, WorkProduct] = {
            wp["key"]: WorkProduct(key=wp["key"], name=wp["name"], phase=wp["phase"], review_gate=wp.get("review_gate", False))
            for wp in definition["work_products"]
        }
        self.events: List[dict] = []
        self._bus = bus
        self._metrics = metrics

    def _emit(self, event_type: str, **payload: Any) -> None:
        event = AgentEvent(event_type=event_type, source_agent_id=self.key, session_id=self.key, payload=payload)
        self.events.append(json.loads(event.model_dump_json()))
        asyncio.ensure_future(self._bus.publish(event))

    def work_products_snapshot(self) -> List[dict]:
        return [json.loads(wp.model_dump_json()) for wp in self.work_products.values()]

    def counts(self) -> Dict[str, int]:
        started = [wp for wp in self.work_products.values() if wp.status != WorkProductStatus.NOT_STARTED]
        return {"done": len(started), "total": len(self.work_products)}

    def pending_reviews(self) -> List[WorkProduct]:
        return [wp for wp in self.work_products.values() if wp.status == WorkProductStatus.AWAITING_REVIEW]

    async def run(self, live: bool, agent_runner: Any, github_backend: Any) -> None:
        # Only pre-register the DEMO source here — LIVE's real backend
        # (AGENTCORE vs GITHUB_COPILOT) is resolved inside _run_live and set
        # there instead, since start_lane's dict entry is created with
        # setdefault and won't overwrite a source recorded this early.
        if not live:
            self._metrics.start_lane(self.key, source="DEMO")
        try:
            if live:
                await self._run_live(agent_runner, github_backend)
            else:
                await self._run_demo()
        except Exception as exc:  # noqa: BLE001 - one lane's failure must not sink the dashboard
            logger.exception("lane %s failed", self.key)
            self.status = LaneStatus.FAILED
            self.current_activity = f"Lane failed: {exc}"
            self._emit("LANE_FAILED", error=str(exc))

    # ── DEMO: fully scripted, offline ───────────────────────

    async def _run_demo(self) -> None:
        self._emit("LANE_STARTED", mode="DEMO")
        script = self.definition.get("script", [])
        for wp_key, delay_s, status, version in script:
            await asyncio.sleep(delay_s / 10)  # compress the schedule for a responsive demo
            wp = self.work_products[wp_key]
            wp.status = WorkProductStatus(status)
            wp.version = version
            wp.touch()
            self._metrics.record(self.key, _DEMO_TOKENS_PER_TRANSITION)
            is_last_scripted = wp_key == script[-1][0]

            if wp.status == WorkProductStatus.AWAITING_REVIEW:
                wp.requested_at = wp.updated_at
                self._emit("WORK_PRODUCT_AWAITING_REVIEW", work_product=wp_key, name=wp.name)
                if is_last_scripted:
                    self.status = LaneStatus.WAITING_FOR_APPROVAL
                    self.current_activity = self.definition["activity_text"]
                asyncio.ensure_future(self._await_review(wp_key))
            else:
                self._emit("WORK_PRODUCT_UPDATED", work_product=wp_key, name=wp.name, status=wp.status.value, version=version)
                if self.status != LaneStatus.WAITING_FOR_APPROVAL:
                    self.current_activity = self.definition["activity_text"]

        if self.status != LaneStatus.WAITING_FOR_APPROVAL:
            self.status = LaneStatus.RUNNING

    async def _await_review(self, wp_key: str) -> None:
        """Parks on the same AWAITING_CALLBACK primitive the client-tool
        bridge uses, keyed by a lane-scoped id so concurrent lanes never
        collide on the same EventBus futures map."""
        call_id = f"{self.key}:{wp_key}"
        event: AgentEvent = await self._bus.wait_for(call_id)
        wp = self.work_products[wp_key]
        approved = event.payload.get("approved", False)
        wp.status = WorkProductStatus.COMPLETED if approved else WorkProductStatus.IN_PROGRESS
        if approved:
            wp.version = event.payload.get("version") or "v1.0"
        wp.touch()
        wp.requested_at = None
        self._emit(
            "WORK_PRODUCT_REVIEWED", work_product=wp_key, name=wp.name,
            approved=approved, status=wp.status.value,
        )
        if self.status == LaneStatus.WAITING_FOR_APPROVAL:
            self.status = LaneStatus.RUNNING
            self.current_activity = f"{wp.name} reviewed — proceeding with remaining work products."

    # ── LIVE: real AgentCore Harness / GitHub Copilot invocation ───

    async def _run_live(self, agent_runner: Any, github_backend: Any) -> None:
        self._emit("LANE_STARTED", mode="LIVE")
        backend, agent_id, agent_config = self._resolve_live_backend(agent_runner)

        session = LiveAgentSession(
            # AgentCore's runtimeSessionId requires >= 33 chars; a full uuid4
            # hex (32 chars) plus this prefix comfortably clears that.
            session_id=f"dash-{self.key}-{uuid.uuid4().hex}",
            agent_id=agent_id, backend=backend, live=True, bus=self._bus,
            agent_runner=agent_runner, agent_config=agent_config, github_backend=github_backend,
            metrics_tracker=self._metrics, metrics_lane_key=self.key,
        )
        self._metrics.start_lane(self.key, source=backend.value)
        await session.run(self.definition["prompt"])

        first_key = self.definition["work_products"][0]["key"]
        first_wp = self.work_products[first_key]

        if session.status != "COMPLETED":
            self.status = LaneStatus.FAILED
            self.current_activity = (session.final_text or "Live invocation failed")[:300]
            return

        first_wp.status = WorkProductStatus.COMPLETED
        first_wp.version = "v1.0 (live)"
        first_wp.touch()
        self.current_activity = (session.final_text or "")[:300] or self.definition["activity_text"]
        self._emit("WORK_PRODUCT_UPDATED", work_product=first_key, name=first_wp.name, status="COMPLETED", version="v1.0 (live)")

        gated = [wp for wp in self.definition["work_products"] if wp.get("review_gate")]
        if gated:
            gate_key = gated[0]["key"]
            gate_wp = self.work_products[gate_key]
            gate_wp.status = WorkProductStatus.AWAITING_REVIEW
            gate_wp.touch()
            gate_wp.requested_at = gate_wp.updated_at
            self._emit("WORK_PRODUCT_AWAITING_REVIEW", work_product=gate_key, name=gate_wp.name)
            self.status = LaneStatus.WAITING_FOR_APPROVAL
            asyncio.ensure_future(self._await_review(gate_key))
        else:
            self.status = LaneStatus.RUNNING

    def _resolve_live_backend(self, agent_runner: Any):
        agentcore_id = self.definition.get("agentcore_agent_id")
        if agentcore_id:
            config = agent_runner.get_agent_config(agentcore_id) or {}
            from harness.metrics import get_agentcore_runtime_info

            runtime_info = get_agentcore_runtime_info(agentcore_id)
            if runtime_info.get("status") == "READY":
                return AgentBackend.AGENTCORE, agentcore_id, {**config, **runtime_info}
        copilot_id = self.definition.get("copilot_agent_id", agentcore_id)
        return AgentBackend.GITHUB_COPILOT, copilot_id, {}


class ProjectDashboardSession:
    def __init__(
        self, session_id: str, live: bool, bus: EventBus, agent_runner: Any, github_backend: Any,
        title: str = "Customer Payments Data Product",
        phases: Optional[List[str]] = None,
        phase_labels: Optional[Dict[str, str]] = None,
        lane_definitions: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        self.session_id = session_id
        self.live = live
        self.title = title
        self.phases = phases or DEFAULT_PHASES
        self.phase_labels = phase_labels or DEFAULT_PHASE_LABELS
        self.started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self._bus = bus
        self._agent_runner = agent_runner
        self._github_backend = github_backend
        self.metrics = InvocationMetricsTracker()
        self.lanes: Dict[str, ProjectLane] = {
            d["key"]: ProjectLane(d, bus, self.metrics) for d in (lane_definitions or DEFAULT_LANE_DEFINITIONS)
        }

    async def run(self) -> None:
        await asyncio.gather(*[
            lane.run(self.live, self._agent_runner, self._github_backend) for lane in self.lanes.values()
        ])

    async def review(self, lane_key: str, work_product_key: str, approve: bool, version: str = "") -> bool:
        lane = self.lanes.get(lane_key)
        if lane is None or work_product_key not in lane.work_products:
            return False
        wp = lane.work_products[work_product_key]
        if wp.status != WorkProductStatus.AWAITING_REVIEW:
            return False
        call_id = f"{lane_key}:{work_product_key}"
        event = AgentEvent(
            event_type="WORK_PRODUCT_REVIEW_SUBMITTED", source_agent_id=lane_key, session_id=lane_key,
            payload={"approved": approve, "version": version},
        )
        return await self._bus.resolve_callback(call_id, event)

    def snapshot(self) -> dict:
        phase_counts = {p: {"done": 0, "total": 0} for p in self.phases}
        lanes_out = []
        recent_activity: List[dict] = []
        human_attention: List[dict] = []
        wp_total = wp_done = 0

        for lane in self.lanes.values():
            for wp in lane.work_products.values():
                bucket = phase_counts[wp.phase]
                bucket["total"] += 1
                if wp.status != WorkProductStatus.NOT_STARTED:
                    bucket["done"] += 1
                wp_total += 1
                if wp.status != WorkProductStatus.NOT_STARTED:
                    wp_done += 1

            lane_metrics = self.metrics.lane_snapshot(lane.key)
            lanes_out.append({
                "key": lane.key, "name": lane.name, "role": lane.role, "color": lane.color,
                "status": lane.status.value, "current_activity": lane.current_activity,
                "work_products": lane.work_products_snapshot(),
                "counts": lane.counts(),
                "elapsed_seconds": lane_metrics["elapsed_seconds"],
                "token_cost_usd": lane_metrics["token_cost_usd"],
                "total_tokens": lane_metrics["total_tokens"],
                "backend": lane_metrics["source"],
                "events": lane.events[-20:],
            })
            recent_activity.extend(lane.events)
            for wp in lane.pending_reviews():
                human_attention.append({
                    "lane_key": lane.key, "lane_name": lane.name,
                    "work_product_key": wp.key, "work_product_name": wp.name,
                    "requested_at": wp.requested_at, "version": wp.version,
                })

        recent_activity.sort(key=lambda e: e.get("timestamp", ""))
        project_metrics = self.metrics.project_snapshot()
        agents_running = sum(1 for lane in self.lanes.values() if lane.status in (LaneStatus.RUNNING, LaneStatus.WAITING_FOR_APPROVAL))

        return {
            "session_id": self.session_id,
            "title": self.title,
            "live": self.live,
            "started_at": self.started_at,
            "elapsed_seconds": project_metrics["elapsed_seconds"],
            "token_cost_usd": project_metrics["token_cost_usd"],
            "total_tokens": project_metrics["total_tokens"],
            "work_products_done": wp_done,
            "work_products_total": wp_total,
            "agents_active": agents_running,
            "agents_total": len(self.lanes),
            "phases": [
                {"key": p, "label": self.phase_labels[p], "done": phase_counts[p]["done"], "total": phase_counts[p]["total"]}
                for p in self.phases
            ],
            "lanes": lanes_out,
            "recent_activity": recent_activity[-30:],
            "human_attention_required": human_attention,
        }
