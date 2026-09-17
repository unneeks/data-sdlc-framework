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

Cost is priced from real, live AWS Price List API rates
(harness/bedrock_pricing.py), applied to these real token counts, for
lanes actually backed by an AgentCore invocation. There is no hardcoded
price table here any more — a lane whose usage can't be confidently
priced (DEMO's synthetic tokens, GitHub Copilot's char-count heuristic, or
an AgentCore lane whose live pricing lookup failed) reports its cost as
unavailable rather than a guessed number; see lane_snapshot()'s
`cost_available` field. AWS Cost Explorer / Bedrock invocation logs remain
the source of record for actual billed spend — it cannot be scoped to a
single lane, so it isn't used here.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Dict, Optional

from harness.bedrock_pricing import BedrockModelPricing, get_bedrock_model_pricing


@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def __add__(self, other: "TokenUsage") -> "TokenUsage":
        return TokenUsage(self.input_tokens + other.input_tokens, self.output_tokens + other.output_tokens)


@dataclass
class _LaneMetrics:
    started_at: float = field(default_factory=time.monotonic)
    usage: TokenUsage = field(default_factory=TokenUsage)
    invocation_count: int = 0
    source: str = "DEMO"  # "AGENTCORE" | "GITHUB_COPILOT" | "DEMO" — how this usage was derived
    pricing: Optional[BedrockModelPricing] = None

    def elapsed_seconds(self) -> float:
        return time.monotonic() - self.started_at

    def cost(self) -> "tuple[Optional[float], bool]":
        if self.pricing is None:
            return None, False
        cost = round(
            self.usage.input_tokens / 1000 * self.pricing.input_price_per_1k_usd
            + self.usage.output_tokens / 1000 * self.pricing.output_price_per_1k_usd,
            4,
        )
        return cost, True


class InvocationMetricsTracker:
    """One instance per ProjectDashboardSession (harness/project_dashboard.py)."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._project_started_at = time.monotonic()
        self._lanes: Dict[str, _LaneMetrics] = {}

    def start_lane(self, lane_key: str, source: str = "DEMO", model_id: str = "") -> None:
        pricing = get_bedrock_model_pricing(model_id) if source == "AGENTCORE" and model_id else None
        with self._lock:
            self._lanes.setdefault(lane_key, _LaneMetrics(source=source, pricing=pricing))

    def record(self, lane_key: str, usage: TokenUsage) -> None:
        with self._lock:
            lane = self._lanes.setdefault(lane_key, _LaneMetrics())
            lane.usage = lane.usage + usage
            lane.invocation_count += 1

    def lane_snapshot(self, lane_key: str) -> dict:
        with self._lock:
            lane = self._lanes.get(lane_key)
            if lane is None:
                return {
                    "elapsed_seconds": 0.0, "token_cost_usd": None, "cost_available": False,
                    "total_tokens": 0, "invocation_count": 0, "source": "PENDING",
                }
            cost, available = lane.cost()
            return {
                "elapsed_seconds": round(lane.elapsed_seconds(), 1),
                "token_cost_usd": cost,
                "cost_available": available,
                "total_tokens": lane.usage.total_tokens,
                "invocation_count": lane.invocation_count,
                "source": lane.source,
            }

    def project_snapshot(self) -> dict:
        with self._lock:
            total_usage = TokenUsage()
            total_cost = 0.0
            all_available = True
            any_usage = False
            for lane in self._lanes.values():
                total_usage = total_usage + lane.usage
                if lane.usage.total_tokens <= 0:
                    continue
                any_usage = True
                cost, available = lane.cost()
                if available:
                    total_cost += cost
                else:
                    all_available = False

            cost_available = any_usage and all_available
            return {
                "elapsed_seconds": round(time.monotonic() - self._project_started_at, 1),
                "token_cost_usd": round(total_cost, 4) if cost_available else None,
                "cost_available": cost_available,
                "total_tokens": total_usage.total_tokens,
            }
