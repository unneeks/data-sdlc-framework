"""In-process aggregation of AgentCore Harness invocation usage.

This is the adapter that feeds the Project Dashboard's live cost/token/
elapsed-time tiles. It exists as a distinct concern from harness/metrics.py's
CloudWatch adapter:

  - harness/metrics.py (CloudWatch) reports account/runtime-level aggregates,
    lags by minutes, and cannot be scoped to "this project run" or "this
    lane" — it is the right tool for ops-level observability of a deployed
    runtime.
  - This module records each AgentCore Harness turn's *own* response usage
    the moment it happens (agents/runner.py's parse_harness_stream extracts
    a `metadata` stream event's `usage` block, when the Harness includes
    one — the same shape Bedrock's Converse streaming API uses:
    {"usage": {"inputTokens", "outputTokens", "totalTokens"}}), so the
    dashboard reflects this project's actual invocations in real time,
    independent of CloudWatch's delay.

Pricing is a placeholder estimate (see PRICE_PER_1K_*) — not a billing
source of truth. AWS Cost Explorer / Bedrock invocation logs remain the
source of record for real spend; this exists to give operators a live
order-of-magnitude signal while a project run is in flight.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Dict

# Approximate blended Claude Sonnet-class pricing (USD per 1K tokens).
PRICE_PER_1K_INPUT_USD = 0.003
PRICE_PER_1K_OUTPUT_USD = 0.015


@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def estimated_cost_usd(self) -> float:
        return round(
            self.input_tokens / 1000 * PRICE_PER_1K_INPUT_USD
            + self.output_tokens / 1000 * PRICE_PER_1K_OUTPUT_USD,
            4,
        )

    def __add__(self, other: "TokenUsage") -> "TokenUsage":
        return TokenUsage(self.input_tokens + other.input_tokens, self.output_tokens + other.output_tokens)


@dataclass
class _LaneMetrics:
    started_at: float = field(default_factory=time.monotonic)
    usage: TokenUsage = field(default_factory=TokenUsage)
    invocation_count: int = 0
    source: str = "DEMO"  # "AGENTCORE" | "GITHUB_COPILOT" | "DEMO" — how this usage was derived

    def elapsed_seconds(self) -> float:
        return time.monotonic() - self.started_at


class InvocationMetricsTracker:
    """One instance per ProjectDashboardSession (harness/project_dashboard.py)."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._project_started_at = time.monotonic()
        self._lanes: Dict[str, _LaneMetrics] = {}

    def start_lane(self, lane_key: str, source: str = "DEMO") -> None:
        with self._lock:
            self._lanes.setdefault(lane_key, _LaneMetrics(source=source))

    def record(self, lane_key: str, usage: TokenUsage) -> None:
        with self._lock:
            lane = self._lanes.setdefault(lane_key, _LaneMetrics())
            lane.usage = lane.usage + usage
            lane.invocation_count += 1

    def lane_snapshot(self, lane_key: str) -> dict:
        with self._lock:
            lane = self._lanes.get(lane_key)
            if lane is None:
                return {"elapsed_seconds": 0.0, "token_cost_usd": 0.0, "total_tokens": 0, "invocation_count": 0, "source": "PENDING"}
            return {
                "elapsed_seconds": round(lane.elapsed_seconds(), 1),
                "token_cost_usd": lane.usage.estimated_cost_usd,
                "total_tokens": lane.usage.total_tokens,
                "invocation_count": lane.invocation_count,
                "source": lane.source,
            }

    def project_snapshot(self) -> dict:
        with self._lock:
            total_usage = TokenUsage()
            for lane in self._lanes.values():
                total_usage = total_usage + lane.usage
            return {
                "elapsed_seconds": round(time.monotonic() - self._project_started_at, 1),
                "token_cost_usd": total_usage.estimated_cost_usd,
                "total_tokens": total_usage.total_tokens,
            }
