"""
System-wide Demo/Real toggle and AWS AgentCore configuration.

No credentials live here. AWS credentials are left entirely to boto3's
standard resolution chain (env vars, shared credentials file, or an IAM
role) — this module only reads non-secret ARN/region configuration.
"""
import os

from domain.orchestration import SystemMode


class HarnessConfig:
    def __init__(self) -> None:
        self.mode: SystemMode = SystemMode.DEMO
        self.aws_region: str = os.getenv("AGENTCORE_AWS_REGION", "us-east-1")
        self.agent_runtime_arn: str = os.getenv("AGENTCORE_RUNTIME_ARN", "")


# Module-level singleton, matching the existing pattern of module-level
# service instances in apps/api/main.py (classifier, graph_engine, etc.).
harness_config = HarnessConfig()
