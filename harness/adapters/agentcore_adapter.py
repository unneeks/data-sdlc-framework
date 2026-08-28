"""
SERVER_RUN adapter: real AWS Bedrock AgentCore integration.

Requires IAM permission `bedrock-agentcore:InvokeAgentRuntime` on the caller.
Note: OAuth-authenticated AgentCore runtimes cannot be invoked via the AWS
SDK and require a raw HTTPS call instead — if that's needed later, add an
`HttpsAgentCoreAdapter` implementing the same `AgentAdapter.start()` contract;
nothing in the harness loop depends on boto3 being used internally.
"""
import json
from typing import Any, Dict, Optional

from domain.orchestration import AgentStep
from harness.config import HarnessConfig


class ServerRunAdapter:
    def __init__(self, config: HarnessConfig, client: Optional[Any] = None) -> None:
        self._config = config
        # Optional injected client keeps this adapter unit-testable without
        # moto/live AWS: tests pass a hand-written fake object here.
        self._client = client

    def _get_client(self) -> Any:
        if self._client is None:
            import boto3

            self._client = boto3.client(
                "bedrock-agentcore", region_name=self._config.aws_region
            )
        return self._client

    def start(self, step: AgentStep) -> Dict[str, Any]:
        try:
            client = self._get_client()
            response = client.invoke_agent_runtime(
                agentRuntimeArn=self._config.agent_runtime_arn,
                runtimeSessionId=step.session_id,
                payload=json.dumps(step.input_payload).encode("utf-8"),
            )
            raw_payload = response.get("payload", b"{}")
            if isinstance(raw_payload, (bytes, bytearray)):
                raw_payload = raw_payload.decode("utf-8")
            output = json.loads(raw_payload) if raw_payload else {}
            return {"status": "COMPLETED", "output": output}
        except Exception as exc:  # noqa: BLE001 - surface any AWS/parsing failure as a failed step
            return {"status": "FAILED", "output": {"error": str(exc)}}
