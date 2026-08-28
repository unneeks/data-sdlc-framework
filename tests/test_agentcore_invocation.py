"""
Test cases for AgentCore Runtime invocation.

Covers:
  - Unit tests: adapter behavior with stubbed boto3 clients (no network)
  - Contract tests: request/response shape validation
  - Error handling: timeouts, malformed responses, missing config
  - Integration tests: live invocation against the deployed runtime (requires AWS creds)

Run unit tests (no AWS needed):
    uv run --with-requirements apps/api/requirements.txt pytest tests/test_agentcore_invocation.py -v -k "not integration"

Run integration tests (requires deployed runtime + AWS creds):
    AWS_DEFAULT_REGION=us-west-2 uv run --with-requirements apps/api/requirements.txt pytest tests/test_agentcore_invocation.py -v -k "integration"

Run all:
    AWS_DEFAULT_REGION=us-west-2 uv run --with-requirements apps/api/requirements.txt pytest tests/test_agentcore_invocation.py -v
"""
import json
import sys
import uuid
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from domain.orchestration import AgentRuntimeKind, AgentStep, StepStatus, SystemMode
from harness.adapters.agentcore_adapter import ServerRunAdapter
from harness.config import HarnessConfig


# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def config():
    c = HarnessConfig()
    c.mode = SystemMode.REAL
    c.aws_region = "us-west-2"
    c.agent_runtime_arn = "arn:aws:bedrock-agentcore:us-west-2:553644760112:runtime/test-runtime-id"
    return c


@pytest.fixture
def sample_step():
    return AgentStep(
        agent_id="impact-analysis-agent",
        task_id="task-001",
        session_id=str(uuid.uuid4()),
        execution_kind=AgentRuntimeKind.SERVER_RUN,
        input_payload={"action": "classify", "prompt": "Migrate to lakehouse"},
    )


@pytest.fixture
def runtime_config():
    config_path = root_dir / "runtime_config.json"
    if config_path.exists():
        with open(config_path) as f:
            return json.load(f)
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# Unit Tests — Stubbed Client (no network)
# ═══════════════════════════════════════════════════════════════════════════════


class TestServerRunAdapterUnit:
    """Tests for ServerRunAdapter with fake boto3 clients."""

    def test_successful_invocation(self, config, sample_step):
        """Adapter returns COMPLETED with parsed JSON output on success."""
        fake_client = MagicMock()
        fake_client.invoke_agent_runtime.return_value = {
            "payload": json.dumps({"result": "classified"}).encode(),
        }

        adapter = ServerRunAdapter(config, client=fake_client)
        result = adapter.start(sample_step)

        assert result["status"] == "COMPLETED"
        assert result["output"] == {"result": "classified"}
        fake_client.invoke_agent_runtime.assert_called_once()

    def test_invocation_sends_correct_parameters(self, config, sample_step):
        """Adapter passes the correct ARN, session ID, and payload."""
        fake_client = MagicMock()
        fake_client.invoke_agent_runtime.return_value = {
            "payload": b'{"ok": true}'
        }

        adapter = ServerRunAdapter(config, client=fake_client)
        adapter.start(sample_step)

        call_kwargs = fake_client.invoke_agent_runtime.call_args[1]
        assert call_kwargs["agentRuntimeArn"] == config.agent_runtime_arn
        assert call_kwargs["runtimeSessionId"] == sample_step.session_id
        payload = json.loads(call_kwargs["payload"].decode())
        assert payload == sample_step.input_payload

    def test_invocation_failure_returns_failed_status(self, config, sample_step):
        """Adapter returns FAILED with error details when boto3 raises."""
        fake_client = MagicMock()
        fake_client.invoke_agent_runtime.side_effect = Exception("Connection timeout")

        adapter = ServerRunAdapter(config, client=fake_client)
        result = adapter.start(sample_step)

        assert result["status"] == "FAILED"
        assert "Connection timeout" in result["output"]["error"]

    def test_empty_payload_response(self, config, sample_step):
        """Adapter handles empty response payload gracefully."""
        fake_client = MagicMock()
        fake_client.invoke_agent_runtime.return_value = {"payload": b""}

        adapter = ServerRunAdapter(config, client=fake_client)
        result = adapter.start(sample_step)

        assert result["status"] == "COMPLETED"
        assert result["output"] == {}

    def test_malformed_json_response(self, config, sample_step):
        """Adapter returns FAILED when response is not valid JSON."""
        fake_client = MagicMock()
        fake_client.invoke_agent_runtime.return_value = {
            "payload": b"not-json-{{"
        }

        adapter = ServerRunAdapter(config, client=fake_client)
        result = adapter.start(sample_step)

        # The adapter wraps JSON decode errors as failures
        assert result["status"] == "FAILED"

    def test_bytes_payload_decoded(self, config, sample_step):
        """Adapter decodes bytes payload correctly."""
        fake_client = MagicMock()
        response_data = {"primary_delivery_type": "DATA_PLATFORM_MIGRATION", "confidence": 0.96}
        fake_client.invoke_agent_runtime.return_value = {
            "payload": json.dumps(response_data).encode("utf-8")
        }

        adapter = ServerRunAdapter(config, client=fake_client)
        result = adapter.start(sample_step)

        assert result["status"] == "COMPLETED"
        assert result["output"]["confidence"] == 0.96

    def test_streaming_body_response(self, config, sample_step):
        """Adapter handles StreamingBody-like response objects."""
        response_data = {"agents": ["agent-1", "agent-2"]}

        fake_client = MagicMock()
        fake_client.invoke_agent_runtime.return_value = {
            "statusCode": 200,
            "response": BytesIO(json.dumps(response_data).encode()),
        }

        adapter = ServerRunAdapter(config, client=fake_client)
        result = adapter.start(sample_step)

        assert result["status"] == "COMPLETED"


# ═══════════════════════════════════════════════════════════════════════════════
# Contract Tests — Request/Response Shape Validation
# ═══════════════════════════════════════════════════════════════════════════════


class TestInvocationContract:
    """Validates the contract between the API layer and AgentCore."""

    VALID_ACTIONS = ["classify", "plan", "impact", "twin", "agents", "evaluate"]

    @pytest.mark.parametrize("action", VALID_ACTIONS)
    def test_all_actions_produce_valid_payload(self, config, action):
        """Each supported action produces a valid JSON payload for AgentCore."""
        fake_client = MagicMock()
        fake_client.invoke_agent_runtime.return_value = {"payload": b'{"ok":true}'}

        adapter = ServerRunAdapter(config, client=fake_client)
        step = AgentStep(
            agent_id="test-agent",
            task_id="task-001",
            session_id=str(uuid.uuid4()),
            execution_kind=AgentRuntimeKind.SERVER_RUN,
            input_payload={"action": action, "prompt": "test", "change_id": "CHG-001"},
        )
        adapter.start(step)

        call_kwargs = fake_client.invoke_agent_runtime.call_args[1]
        payload = json.loads(call_kwargs["payload"].decode())
        assert payload["action"] == action

    def test_session_id_meets_minimum_length(self, config, sample_step):
        """AgentCore requires runtimeSessionId to be at least 33 chars."""
        fake_client = MagicMock()
        fake_client.invoke_agent_runtime.return_value = {"payload": b'{}'}

        adapter = ServerRunAdapter(config, client=fake_client)
        adapter.start(sample_step)

        call_kwargs = fake_client.invoke_agent_runtime.call_args[1]
        session_id = call_kwargs["runtimeSessionId"]
        assert len(session_id) >= 33, f"Session ID too short: {len(session_id)} chars"

    def test_classify_response_has_required_fields(self, config):
        """Classify response must include primary_delivery_type and confidence."""
        expected_response = {
            "primary_delivery_type": "DATA_PLATFORM_MIGRATION",
            "confidence": 0.96,
            "evidence_reasoning": ["reason1"],
            "secondary_delivery_types": [],
            "available_types": ["DATA_PLATFORM_MIGRATION"],
        }

        fake_client = MagicMock()
        fake_client.invoke_agent_runtime.return_value = {
            "payload": json.dumps(expected_response).encode()
        }

        adapter = ServerRunAdapter(config, client=fake_client)
        step = AgentStep(
            agent_id="test", task_id="t1", session_id=str(uuid.uuid4()),
            execution_kind=AgentRuntimeKind.SERVER_RUN,
            input_payload={"action": "classify", "prompt": "migrate"},
        )
        result = adapter.start(step)

        output = result["output"]
        assert "primary_delivery_type" in output
        assert "confidence" in output
        assert isinstance(output["confidence"], (int, float))
        assert 0 <= output["confidence"] <= 1

    def test_impact_response_has_required_fields(self, config):
        """Impact response must include technical_impact and delivery_impact."""
        expected_response = {
            "technical_impact": {"change_id": "CHG-001", "affected_pipelines_count": 14},
            "delivery_impact": {"affected_delivery_tasks": []},
        }

        fake_client = MagicMock()
        fake_client.invoke_agent_runtime.return_value = {
            "payload": json.dumps(expected_response).encode()
        }

        adapter = ServerRunAdapter(config, client=fake_client)
        step = AgentStep(
            agent_id="test", task_id="t1", session_id=str(uuid.uuid4()),
            execution_kind=AgentRuntimeKind.SERVER_RUN,
            input_payload={"action": "impact", "change_id": "CHG-001"},
        )
        result = adapter.start(step)

        output = result["output"]
        assert "technical_impact" in output
        assert "delivery_impact" in output


# ═══════════════════════════════════════════════════════════════════════════════
# Error Handling Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestErrorHandling:
    """Tests for various failure scenarios."""

    def test_access_denied_error(self, config, sample_step):
        """Adapter handles AccessDeniedException gracefully."""
        from botocore.exceptions import ClientError

        fake_client = MagicMock()
        fake_client.invoke_agent_runtime.side_effect = ClientError(
            {"Error": {"Code": "AccessDeniedException", "Message": "Not authorized"}},
            "InvokeAgentRuntime",
        )

        adapter = ServerRunAdapter(config, client=fake_client)
        result = adapter.start(sample_step)

        assert result["status"] == "FAILED"
        assert "Not authorized" in result["output"]["error"]

    def test_resource_not_found_error(self, config, sample_step):
        """Adapter handles ResourceNotFoundException when runtime doesn't exist."""
        from botocore.exceptions import ClientError

        fake_client = MagicMock()
        fake_client.invoke_agent_runtime.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException", "Message": "Runtime not found"}},
            "InvokeAgentRuntime",
        )

        adapter = ServerRunAdapter(config, client=fake_client)
        result = adapter.start(sample_step)

        assert result["status"] == "FAILED"
        assert "not found" in result["output"]["error"].lower()

    def test_throttling_error(self, config, sample_step):
        """Adapter handles ThrottlingException."""
        from botocore.exceptions import ClientError

        fake_client = MagicMock()
        fake_client.invoke_agent_runtime.side_effect = ClientError(
            {"Error": {"Code": "ThrottlingException", "Message": "Rate exceeded"}},
            "InvokeAgentRuntime",
        )

        adapter = ServerRunAdapter(config, client=fake_client)
        result = adapter.start(sample_step)

        assert result["status"] == "FAILED"
        assert "Rate exceeded" in result["output"]["error"]

    def test_missing_runtime_arn(self, sample_step):
        """Adapter fails gracefully when runtime ARN is not configured."""
        config = HarnessConfig()
        config.agent_runtime_arn = ""

        fake_client = MagicMock()
        fake_client.invoke_agent_runtime.side_effect = Exception(
            "Parameter validation failed: Invalid ARN"
        )

        adapter = ServerRunAdapter(config, client=fake_client)
        result = adapter.start(sample_step)

        assert result["status"] == "FAILED"

    def test_network_timeout(self, config, sample_step):
        """Adapter handles network timeouts."""
        from botocore.exceptions import ReadTimeoutError

        fake_client = MagicMock()
        fake_client.invoke_agent_runtime.side_effect = ReadTimeoutError(
            endpoint_url="https://bedrock-agentcore.us-west-2.amazonaws.com"
        )

        adapter = ServerRunAdapter(config, client=fake_client)
        result = adapter.start(sample_step)

        assert result["status"] == "FAILED"
        assert "timeout" in result["output"]["error"].lower() or "Timeout" in result["output"]["error"]


# ═══════════════════════════════════════════════════════════════════════════════
# API Layer Tests — invoke_agentcore() function
# ═══════════════════════════════════════════════════════════════════════════════


class TestAPIInvokeAgentcore:
    """Tests for the invoke_agentcore() helper in apps/api/main.py."""

    def test_invoke_returns_parsed_json(self):
        """invoke_agentcore returns a parsed dict, not raw bytes."""
        sys.path.insert(0, str(root_dir / "apps" / "api"))
        # Patch boto3 client before importing
        with patch("boto3.client") as mock_boto:
            mock_client = MagicMock()
            mock_client.invoke_agent_runtime.return_value = {
                "statusCode": 200,
                "response": BytesIO(json.dumps({"confidence": 0.96}).encode()),
                "ResponseMetadata": {"RequestId": "abc"},
            }
            mock_boto.return_value = mock_client

            # Import after patching
            from apps.api.main import invoke_agentcore, _runtime_config

            if _runtime_config:
                result = invoke_agentcore("classify", prompt="test")
                assert isinstance(result, dict)

    def test_invoke_logs_trace_entry(self):
        """invoke_agentcore appends to the _invocation_log."""
        with patch("boto3.client") as mock_boto:
            mock_client = MagicMock()
            mock_client.invoke_agent_runtime.return_value = {
                "statusCode": 200,
                "response": BytesIO(b'{"ok":true}'),
                "ResponseMetadata": {"RequestId": "abc"},
            }
            mock_boto.return_value = mock_client

            from apps.api.main import invoke_agentcore, _invocation_log, _runtime_config

            if _runtime_config:
                before_count = len(_invocation_log)
                invoke_agentcore("classify", prompt="trace test")
                assert len(_invocation_log) == before_count + 1
                assert _invocation_log[-1]["action"] == "classify"
                assert "latency_ms" in _invocation_log[-1]


# ═══════════════════════════════════════════════════════════════════════════════
# Integration Tests — Live AgentCore Runtime (requires AWS creds + deployment)
# ═══════════════════════════════════════════════════════════════════════════════


class TestAgentCoreIntegration:
    """
    Live integration tests against the deployed AgentCore Runtime.
    These hit real AWS infrastructure and verify end-to-end behavior.

    Skip if runtime_config.json doesn't exist or AWS creds are missing.
    """

    @pytest.fixture(autouse=True)
    def skip_if_no_runtime(self, runtime_config):
        if runtime_config is None:
            pytest.skip("No runtime_config.json — agent not deployed")

    def _invoke(self, runtime_config, action, **kwargs):
        """Helper to invoke the live runtime."""
        import boto3

        client = boto3.client("bedrock-agentcore", region_name=runtime_config["region"])
        payload = {"action": action, **kwargs}

        response = client.invoke_agent_runtime(
            agentRuntimeArn=runtime_config["runtime_arn"],
            runtimeSessionId=str(uuid.uuid4()),
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
        return response, result

    @pytest.mark.integration
    def test_classify_migration_prompt(self, runtime_config):
        """Live: classify a migration request returns DATA_PLATFORM_MIGRATION."""
        response, result = self._invoke(
            runtime_config, "classify",
            prompt="Migrate Teradata data warehouse to cloud lakehouse"
        )

        assert response.get("statusCode") == 200
        assert result["primary_delivery_type"] == "DATA_PLATFORM_MIGRATION"
        assert result["confidence"] >= 0.9

    @pytest.mark.integration
    def test_classify_amendment_prompt(self, runtime_config):
        """Live: classify an amendment request."""
        response, result = self._invoke(
            runtime_config, "classify",
            prompt="Amend customer profile to add risk score column"
        )

        assert response.get("statusCode") == 200
        assert result["primary_delivery_type"] == "DATA_PRODUCT_AMENDMENT"

    @pytest.mark.integration
    def test_classify_source_change_prompt(self, runtime_config):
        """Live: classify a source change request."""
        response, result = self._invoke(
            runtime_config, "classify",
            prompt="Schema change in SAP source feed - status char field extended"
        )

        assert response.get("statusCode") == 200
        assert result["primary_delivery_type"] == "DATA_SOURCE_CHANGE"

    @pytest.mark.integration
    def test_impact_analysis(self, runtime_config):
        """Live: impact analysis returns technical and delivery impacts."""
        response, result = self._invoke(
            runtime_config, "impact", change_id="CHG-001"
        )

        assert response.get("statusCode") == 200
        assert "technical_impact" in result
        assert "delivery_impact" in result
        assert result["technical_impact"]["affected_pipelines_count"] == 14
        assert len(result["delivery_impact"]["affected_delivery_tasks"]) > 0

    @pytest.mark.integration
    def test_plan_generation(self, runtime_config):
        """Live: plan action returns a delivery plan with phases."""
        response, result = self._invoke(
            runtime_config, "plan",
            primary_delivery_type="DATA_PLATFORM_MIGRATION"
        )

        assert response.get("statusCode") == 200
        assert "phases" in result
        assert len(result["phases"]) > 0
        assert result["primary_delivery_type"] == "DATA_PLATFORM_MIGRATION"

    @pytest.mark.integration
    def test_digital_twin(self, runtime_config):
        """Live: twin action returns project state."""
        response, result = self._invoke(runtime_config, "twin")

        assert response.get("statusCode") == 200
        assert "project" in result or "data_assets" in result

    @pytest.mark.integration
    def test_agents_list(self, runtime_config):
        """Live: agents action returns marketplace agents."""
        response, result = self._invoke(runtime_config, "agents")

        assert response.get("statusCode") == 200
        assert isinstance(result, list)
        if len(result) > 0:
            assert "id" in result[0]
            assert "name" in result[0]

    @pytest.mark.integration
    def test_evaluate_action(self, runtime_config):
        """Live: evaluate action runs test suite."""
        response, result = self._invoke(
            runtime_config, "evaluate", change_id="CHG-001"
        )

        assert response.get("statusCode") == 200
        assert "total_selected" in result
        assert result["passed"] + result["failed"] == result["total_selected"]

    @pytest.mark.integration
    def test_unknown_action_returns_error(self, runtime_config):
        """Live: unknown action returns error with available actions list."""
        response, result = self._invoke(runtime_config, "nonexistent_action")

        assert response.get("statusCode") == 200
        assert "error" in result
        assert "available_actions" in result

    @pytest.mark.integration
    def test_response_latency_under_threshold(self, runtime_config):
        """Live: AgentCore response time should be under 10 seconds."""
        import time

        start = time.time()
        self._invoke(runtime_config, "classify", prompt="test")
        elapsed = time.time() - start

        assert elapsed < 10, f"Response took {elapsed:.1f}s — exceeds 10s threshold"

    @pytest.mark.integration
    def test_concurrent_invocations(self, runtime_config):
        """Live: multiple concurrent invocations all succeed."""
        import concurrent.futures

        def invoke_one(i):
            _, result = self._invoke(
                runtime_config, "classify",
                prompt=f"Test prompt {i} for concurrent invocation"
            )
            return result

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(invoke_one, i) for i in range(3)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert len(results) == 3
        for r in results:
            assert "primary_delivery_type" in r


# ═══════════════════════════════════════════════════════════════════════════════
# Main runner
# ═══════════════════════════════════════════════════════════════════════════════


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
