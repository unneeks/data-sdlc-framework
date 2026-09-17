"""Unit tests for the Project Dashboard: DEMO lane simulation, the
work-product review pause/resume gate (built on the same EventBus
wait_for/resolve_callback primitive as the client-tool bridge, applied at
work-product grain across several concurrent lanes), per-lane token/cost
metrics, and graceful per-lane failure in LIVE mode.
"""
import asyncio
import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from domain.project import LaneStatus, WorkProductStatus
from harness.agentcore_invocation_metrics import InvocationMetricsTracker, TokenUsage
from harness.bus import EventBus
from harness.project_dashboard import ProjectDashboardSession


def test_demo_dashboard_matches_reference_snapshot_shape():
    """DEMO mode should settle into the same in-flight state the reference
    screenshot shows: two lanes still RUNNING while producing other work
    products, release-lead parked WAITING_FOR_APPROVAL on its last scripted
    item, and both review-gated work products visible in
    human_attention_required."""
    bus = EventBus()
    session = ProjectDashboardSession(session_id="demo1", live=False, bus=bus, agent_runner=None, github_backend=None)

    async def scenario():
        run_task = asyncio.create_task(session.run())
        await asyncio.sleep(1.3)  # let every lane's scripted transitions land (cumulative delays, not per-step)

        snap = session.snapshot()
        lanes = {l["key"]: l for l in snap["lanes"]}

        assert lanes["release-lead"]["status"] == LaneStatus.WAITING_FOR_APPROVAL.value
        assert lanes["data-analyst"]["status"] == LaneStatus.RUNNING.value
        assert lanes["data-engineer"]["status"] == LaneStatus.RUNNING.value
        assert lanes["test-engineer"]["status"] == LaneStatus.RUNNING.value

        pending_keys = {h["work_product_key"] for h in snap["human_attention_required"]}
        assert pending_keys == {"solution-requirements", "deployment-checklist"}

        assert snap["work_products_total"] == 28  # 7 + 8 + 7 + 6, matching the four lane definitions
        assert snap["work_products_done"] > 0
        assert snap["total_tokens"] > 0
        assert snap["token_cost_usd"] > 0

        # resolve both pending reviews so the background _await_review tasks don't outlive the test
        assert await session.review("release-lead", "deployment-checklist", approve=True, version="v1.0")
        assert await session.review("data-analyst", "solution-requirements", approve=True, version="v1.0")
        await asyncio.sleep(0.05)
        run_task.cancel()
        try:
            await run_task
        except asyncio.CancelledError:
            pass

    asyncio.run(scenario())


def test_reviewing_a_gated_work_product_unblocks_its_lane():
    bus = EventBus()
    session = ProjectDashboardSession(session_id="demo2", live=False, bus=bus, agent_runner=None, github_backend=None)

    async def scenario():
        run_task = asyncio.create_task(session.run())
        await asyncio.sleep(0.6)

        lane = session.lanes["release-lead"]
        assert lane.status == LaneStatus.WAITING_FOR_APPROVAL

        approved = await session.review("release-lead", "deployment-checklist", approve=True, version="v1.2")
        assert approved is True

        await asyncio.sleep(0.05)
        assert lane.status == LaneStatus.RUNNING
        wp = lane.work_products["deployment-checklist"]
        assert wp.status == WorkProductStatus.COMPLETED
        assert wp.version == "v1.2"

        assert await session.review("data-analyst", "solution-requirements", approve=True, version="v1.0")
        await asyncio.sleep(0.05)
        run_task.cancel()
        try:
            await run_task
        except asyncio.CancelledError:
            pass

    asyncio.run(scenario())


def test_denying_a_review_marks_it_in_progress_not_completed():
    bus = EventBus()
    session = ProjectDashboardSession(session_id="demo3", live=False, bus=bus, agent_runner=None, github_backend=None)

    async def scenario():
        run_task = asyncio.create_task(session.run())
        await asyncio.sleep(0.6)

        assert await session.review("release-lead", "deployment-checklist", approve=False)
        await asyncio.sleep(0.05)
        wp = session.lanes["release-lead"].work_products["deployment-checklist"]
        assert wp.status == WorkProductStatus.IN_PROGRESS

        assert await session.review("data-analyst", "solution-requirements", approve=True, version="v1.0")
        await asyncio.sleep(0.05)
        run_task.cancel()
        try:
            await run_task
        except asyncio.CancelledError:
            pass

    asyncio.run(scenario())


def test_reviewing_unknown_work_product_returns_false():
    bus = EventBus()
    session = ProjectDashboardSession(session_id="demo4", live=False, bus=bus, agent_runner=None, github_backend=None)

    async def scenario():
        assert await session.review("release-lead", "no-such-key", approve=True) is False
        assert await session.review("no-such-lane", "deployment-checklist", approve=True) is False

    asyncio.run(scenario())


def test_live_lane_failure_is_isolated_per_lane():
    """A lane whose mapped AgentCore agent can't be invoked (no harness ARN,
    bad credentials, etc.) must fail only that lane, not the whole session."""
    bus = EventBus()

    class ExplodingAgentRunner:
        def get_agent_config(self, agent_id):
            raise RuntimeError("boom")

    session = ProjectDashboardSession(session_id="live1", live=True, bus=bus, agent_runner=ExplodingAgentRunner(), github_backend=None)

    asyncio.run(session.run())

    snap = session.snapshot()
    assert all(l["status"] == LaneStatus.FAILED.value for l in snap["lanes"])
    assert all("boom" in l["current_activity"] for l in snap["lanes"])


def test_invocation_metrics_tracker_aggregates_across_lanes():
    tracker = InvocationMetricsTracker()
    tracker.start_lane("lane-a", source="AGENTCORE")
    tracker.record("lane-a", TokenUsage(input_tokens=1000, output_tokens=500))
    tracker.record("lane-a", TokenUsage(input_tokens=200, output_tokens=100))
    tracker.start_lane("lane-b", source="GITHUB_COPILOT")
    tracker.record("lane-b", TokenUsage(input_tokens=300, output_tokens=300))

    lane_a = tracker.lane_snapshot("lane-a")
    assert lane_a["total_tokens"] == 1800
    assert lane_a["invocation_count"] == 2
    assert lane_a["source"] == "AGENTCORE"

    project = tracker.project_snapshot()
    assert project["total_tokens"] == 1800 + 600
    assert project["token_cost_usd"] > 0


def test_unknown_lane_metrics_snapshot_is_zeroed_not_missing():
    tracker = InvocationMetricsTracker()
    snap = tracker.lane_snapshot("never-started")
    assert snap == {"elapsed_seconds": 0.0, "token_cost_usd": 0.0, "total_tokens": 0, "invocation_count": 0, "source": "PENDING"}


def test_dashboard_session_loads_from_project_overrides():
    """A persisted project's phases/lanes (no `script` key, unlike the
    DEMO template) should drive the session instead of the defaults, and
    DEMO mode on it should leave every work product NOT_STARTED rather
    than crashing on the missing `script` field."""
    bus = EventBus()
    phases = ["intake"]
    phase_labels = {"intake": "Intake"}
    lane_definitions = [
        {
            "key": "solo-lane", "name": "Solo Lane", "role": "Do the one thing", "color": "blue",
            "agentcore_agent_id": "", "copilot_agent_id": "", "prompt": "",
            "work_products": [{"key": "only-wp", "name": "Only Work Product", "phase": "intake"}],
        },
    ]
    session = ProjectDashboardSession(
        session_id="proj1", live=False, bus=bus, agent_runner=None, github_backend=None,
        title="A Real Project", phases=phases, phase_labels=phase_labels, lane_definitions=lane_definitions,
    )

    async def scenario():
        run_task = asyncio.create_task(session.run())
        await asyncio.sleep(0.05)
        run_task.cancel()
        try:
            await run_task
        except asyncio.CancelledError:
            pass

    asyncio.run(scenario())

    snap = session.snapshot()
    assert snap["title"] == "A Real Project"
    assert snap["phases"] == [{"key": "intake", "label": "Intake", "done": 0, "total": 1}]
    lane = snap["lanes"][0]
    assert lane["key"] == "solo-lane"
    assert lane["work_products"][0]["status"] == "NOT_STARTED"


if __name__ == "__main__":
    test_demo_dashboard_matches_reference_snapshot_shape()
    test_reviewing_a_gated_work_product_unblocks_its_lane()
    test_denying_a_review_marks_it_in_progress_not_completed()
    test_reviewing_unknown_work_product_returns_false()
    test_live_lane_failure_is_isolated_per_lane()
    test_invocation_metrics_tracker_aggregates_across_lanes()
    test_unknown_lane_metrics_snapshot_is_zeroed_not_missing()
    test_dashboard_session_loads_from_project_overrides()
    print("All project dashboard unit tests passed successfully!")
