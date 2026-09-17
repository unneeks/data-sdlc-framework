"""AWS-backed observability for the Live Agent Orchestrator UI.

Two things live here:
  - `get_aws_identity()` — proves the app is acting as the operator's own
    logged-in AWS identity (SSO/CLI credentials via boto3's default chain,
    see harness/config.py), not a hardcoded service credential.
  - `get_agentcore_metrics()` — pulls the built-in CloudWatch metrics AWS
    publishes for Bedrock AgentCore Runtime invocations (namespace
    "AWS/Bedrock-AgentCore": Invocations, Latency, SessionCount, and related
    error/duration metrics — see AWS's AgentCore observability docs). Metric
    names are discovered via ListMetrics rather than hardcoded, so this
    degrades gracefully (empty series, not a hard failure) for a runtime
    that hasn't emitted any of them yet, or if the exact published metric
    names differ from what we expect in a given AWS region/release.

Every function here fails soft: missing credentials, no configured runtime,
or a CloudWatch permissions gap all come back as
{"available": False, "reason": ...} instead of raising, matching this
codebase's existing "REAL mode never hard-fails" convention (see
docs/adr/0003-dual-mode-demo-and-real.md).
"""
from __future__ import annotations

import time
from typing import Any, Dict, List

_NAMESPACE = "AWS/Bedrock-AgentCore"
_EXPECTED_METRICS = ["Invocations", "Latency", "SessionCount", "Errors", "Throttles"]


def get_aws_identity(region: str = "us-west-2") -> Dict[str, Any]:
    try:
        import boto3

        sts = boto3.client("sts", region_name=region)
        identity = sts.get_caller_identity()
        return {
            "available": True,
            "account": identity.get("Account"),
            "arn": identity.get("Arn"),
            "user_id": identity.get("UserId"),
            "region": region,
        }
    except Exception as exc:  # noqa: BLE001 - no AWS creds active is an expected DEMO-mode state
        return {"available": False, "reason": str(exc)}


def get_agentcore_metrics(agent_runtime_id: str | None, region: str = "us-west-2", lookback_minutes: int = 60) -> Dict[str, Any]:
    if not agent_runtime_id:
        return {"available": False, "reason": "no AgentCore runtime configured for this agent"}

    try:
        import boto3

        cloudwatch = boto3.client("cloudwatch", region_name=region)
        dimension = {"Name": "AgentRuntimeId", "Value": agent_runtime_id}

        published = cloudwatch.list_metrics(Namespace=_NAMESPACE, Dimensions=[dimension])
        available_names = sorted({m["MetricName"] for m in published.get("Metrics", [])}) or _EXPECTED_METRICS

        end = int(time.time())
        start = end - lookback_minutes * 60
        queries = [
            {
                "Id": f"m{i}",
                "MetricStat": {
                    "Metric": {"Namespace": _NAMESPACE, "MetricName": name, "Dimensions": [dimension]},
                    "Period": max(60, lookback_minutes * 60 // 30),
                    "Stat": "Sum" if name in ("Invocations", "Errors", "Throttles") else "Average",
                },
                "Label": name,
                "ReturnData": True,
            }
            for i, name in enumerate(available_names)
        ]

        result = cloudwatch.get_metric_data(MetricDataQueries=queries, StartTime=start, EndTime=end)
        series: List[Dict[str, Any]] = []
        for r in result.get("MetricDataResults", []):
            series.append({
                "metric": r.get("Label"),
                "timestamps": [t.isoformat() for t in r.get("Timestamps", [])],
                "values": r.get("Values", []),
                "total": round(sum(r.get("Values", [])), 3) if r.get("Values") else 0,
            })

        return {
            "available": True,
            "namespace": _NAMESPACE,
            "agent_runtime_id": agent_runtime_id,
            "region": region,
            "lookback_minutes": lookback_minutes,
            "series": series,
        }
    except Exception as exc:  # noqa: BLE001 - missing IAM perms / no data yet are expected states, not failures
        return {"available": False, "reason": str(exc)}
