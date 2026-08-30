"""Runtime strategy — delegates discovery to a deployed AgentCore Runtime agent.

The runtime agent has its own tool access and orchestration loop. This
strategy just invokes it and parses the response. Useful when discovery
is a service, not a local operation.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from discovery.result import DiscoveryFailure, DiscoveryReport
from discovery.strategy import DiscoveryConfig


class RuntimeStrategy:
    """Delegates to a deployed AgentCore Runtime agent."""

    name = "runtime"

    def __init__(self, *, runtime_arn: str, region: str = "us-west-2"):
        self._runtime_arn = runtime_arn
        self._region = region

    def discover(self, config: DiscoveryConfig) -> DiscoveryReport:
        import boto3

        client = boto3.client("bedrock-agentcore", region_name=self._region)
        session_id = str(uuid.uuid4())

        payload = {
            "action": "discover",
            "project_id": config.project_id,
            "repository_root": str(config.repository_root),
            "repository_id": config.repository_id,
            "skill": config.skill,
            "on_error": config.on_error,
        }

        try:
            response = client.invoke_agent_runtime(
                agentRuntimeArn=self._runtime_arn,
                runtimeSessionId=session_id,
                payload=json.dumps(payload).encode("utf-8"),
            )

            body = response.get("response")
            if hasattr(body, "read"):
                raw = body.read().decode("utf-8")
            else:
                raw = str(body)

            result = json.loads(raw)
            if isinstance(result, str):
                result = json.loads(result)

        except Exception as e:
            return DiscoveryReport(
                project_id=config.project_id,
                strategy=self.name,
                skill=config.skill,
                failed=[DiscoveryFailure(
                    kind="runtime_invocation_failed",
                    detail=str(e),
                    source=self._runtime_arn,
                )],
            )

        return DiscoveryReport(
            project_id=config.project_id,
            strategy=self.name,
            skill=config.skill,
            entities_discovered=result.get("entities_discovered", 0),
            relationships_discovered=result.get("relationships_discovered", 0),
            entities_by_type=result.get("entities_by_type", {}),
            skipped=[],
            failed=[],
        )
