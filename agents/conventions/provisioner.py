"""Provision AgentCore resources from convention-based configurations.

Handles:
- Harness creation per agent
- Memory namespace creation per agent
- Skills registration
- S3 knowledgebase creation and upload
- Config persistence to agentcore_config.json
"""
from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any

from agents.conventions.parser import (
    AgentConfig,
    KnowledgebaseConfig,
    ProjectConventions,
    SkillConfig,
)

REGION = os.environ.get("AWS_DEFAULT_REGION") or os.environ.get("AWS_REGION") or "us-west-2"
MODEL_MAP = {
    "claude-opus": "us.anthropic.claude-opus-4-6-v1",
    "claude-sonnet": "us.anthropic.claude-opus-4-6-v1",
    "claude-haiku": "us.anthropic.claude-opus-4-6-v1",
}
POLL_INTERVAL = 5
POLL_TIMEOUT = 600
FAILURE_STATUSES = ("CREATE_FAILED", "UPDATE_FAILED", "DELETE_FAILED")


class ProvisionResult:
    def __init__(self):
        self.harnesses: dict[str, dict] = {}
        self.skills: dict[str, dict] = {}
        self.memories: dict[str, dict] = {}
        self.knowledgebase: dict | None = None
        self.errors: list[str] = []
        self.warnings: list[str] = []

    @property
    def success(self) -> bool:
        return len(self.errors) == 0

    def summary(self) -> dict:
        return {
            "harnesses": {k: v.get("status", "UNKNOWN") for k, v in self.harnesses.items()},
            "skills_registered": len(self.skills),
            "memories_created": len(self.memories),
            "knowledgebase": self.knowledgebase.get("status") if self.knowledgebase else "NOT_CONFIGURED",
            "errors": self.errors,
            "warnings": self.warnings,
        }


def _get_account_id(region: str = REGION) -> str:
    import boto3
    return boto3.client("sts", region_name=region).get_caller_identity()["Account"]


def _get_or_create_role(region: str = REGION) -> str:
    """Get or create the HarnessExecutionRole. Returns role ARN."""
    import boto3

    iam = boto3.client("iam", region_name=region)
    role_name = "HarnessExecutionRole"

    try:
        resp = iam.get_role(RoleName=role_name)
        return resp["Role"]["Arn"]
    except iam.exceptions.NoSuchEntityException:
        pass

    account_id = _get_account_id(region)
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": ["bedrock-agentcore.amazonaws.com"]},
            "Action": "sts:AssumeRole",
            "Condition": {"StringEquals": {"aws:SourceAccount": account_id}},
        }],
    }

    permissions_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
                "Resource": ["arn:aws:bedrock:*::foundation-model/*", "arn:aws:bedrock:*:*:inference-profile/*"],
            },
            {
                "Effect": "Allow",
                "Action": [
                    "bedrock-agentcore:CreateMemory", "bedrock-agentcore:GetMemory",
                    "bedrock-agentcore:ListMemories", "bedrock-agentcore:DeleteMemory",
                    "bedrock-agentcore:RetrieveMemoryRecords", "bedrock-agentcore:CreateEvent",
                    "bedrock-agentcore:ListEvents", "bedrock-agentcore:GetEvent",
                    "bedrock-agentcore:InvokeGateway", "bedrock-agentcore:GetResourceApiKey",
                    "bedrock-agentcore:StartCodeInterpreterSession",
                    "bedrock-agentcore:StopCodeInterpreterSession",
                    "bedrock-agentcore:GetCodeInterpreterSession",
                    "bedrock-agentcore:InvokeCodeInterpreter",
                ],
                "Resource": "*",
            },
            {
                "Effect": "Allow",
                "Action": ["s3:GetObject", "s3:PutObject", "s3:ListBucket", "s3:GetBucketLocation"],
                "Resource": ["arn:aws:s3:::agentcore-kb-*", "arn:aws:s3:::agentcore-kb-*/*"],
            },
            {
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents",
                ],
                "Resource": [
                    "arn:aws:logs:*:*:log-group:/aws/bedrock-agentcore/runtimes/*",
                    "arn:aws:logs:*:*:log-group:/aws/bedrock-agentcore/runtimes/*:log-stream:*",
                ],
            },
            {
                "Effect": "Allow",
                "Action": ["xray:PutTraceSegments", "xray:PutTelemetryRecords"],
                "Resource": "*",
            },
        ],
    }

    resp = iam.create_role(
        RoleName=role_name,
        AssumeRolePolicyDocument=json.dumps(trust_policy),
        Description="Execution role for AgentCore convention-based harnesses",
    )
    role_arn = resp["Role"]["Arn"]

    iam.put_role_policy(
        RoleName=role_name,
        PolicyName="HarnessExecutionPolicy",
        PolicyDocument=json.dumps(permissions_policy),
    )

    return role_arn


def _poll_harness(control, harness_id: str, on_status=None) -> dict:
    deadline = time.monotonic() + POLL_TIMEOUT
    while True:
        resp = control.get_harness(harnessId=harness_id)
        status = resp["harness"]["status"]
        if on_status:
            on_status(status)
        if status == "READY":
            return resp
        if status in FAILURE_STATUSES:
            reason = resp["harness"].get("failureReason", "")
            raise RuntimeError(f"Harness entered {status}. {reason}")
        if time.monotonic() > deadline:
            raise TimeoutError(f"Harness not READY after {POLL_TIMEOUT}s (current: {status})")
        time.sleep(POLL_INTERVAL)


def _load_existing_config(project_root: str | Path | None = None) -> dict:
    """Load existing agentcore_config.json if present."""
    paths = []
    if project_root:
        paths.append(Path(project_root) / "agentcore_config.json")
    paths.append(Path(__file__).resolve().parent.parent.parent / "agentcore_config.json")
    for p in paths:
        if p.exists():
            return json.loads(p.read_text())
    return {}


def check_agent_harness_exists(agent_key: str, project_root: str | Path | None = None) -> dict | None:
    """Check if a harness already exists for this agent. Returns harness info or None."""
    config = _load_existing_config(project_root)
    harness_info = config.get("harnesses", {}).get(agent_key)
    if harness_info and harness_info.get("harness_id"):
        return harness_info
    return None


def check_agent_memory_exists(agent_key: str, project_root: str | Path | None = None) -> dict | None:
    """Check if memory already exists for this agent. Returns memory info or None."""
    config = _load_existing_config(project_root)
    mem_info = config.get("memories", {}).get(agent_key)
    if mem_info and mem_info.get("memory_id"):
        return mem_info
    return None


def provision_harness(
    agent: AgentConfig,
    skills: dict[str, SkillConfig],
    role_arn: str,
    region: str = REGION,
    on_status=None,
    force: bool = False,
    project_root: str | Path | None = None,
) -> dict:
    """Create an AgentCore Harness for a convention-based agent.

    If the agent already has a READY harness and force=False, returns
    the existing harness info with status EXISTING.
    """
    import boto3

    if not force:
        existing = check_agent_harness_exists(agent.key, project_root)
        if existing and existing.get("status") == "READY":
            return {
                "harness_id": existing.get("harness_id", ""),
                "harness_arn": existing.get("harness_arn", ""),
                "harness_name": existing.get("harness_name", ""),
                "agent_key": agent.key,
                "model_id": MODEL_MAP.get(agent.model, "us.anthropic.claude-opus-4-6-v1"),
                "execution_model": agent.execution_model,
                "skills": agent.skills_used,
                "status": "EXISTING",
            }

    control = boto3.client("bedrock-agentcore-control", region_name=region)

    suffix = uuid.uuid4().hex[:6]
    safe_key = agent.key.replace("-", "_")
    harness_name = f"conv_{safe_key}_{suffix}"

    resp = control.create_harness(
        harnessName=harness_name,
        executionRoleArn=role_arn,
    )
    harness = resp["harness"]

    result = {
        "harness_id": harness["harnessId"],
        "harness_arn": harness["arn"],
        "harness_name": harness_name,
        "agent_key": agent.key,
        "model_id": MODEL_MAP.get(agent.model, "us.anthropic.claude-opus-4-6-v1"),
        "execution_model": agent.execution_model,
        "skills": agent.skills_used,
    }

    try:
        _poll_harness(control, harness["harnessId"], on_status=on_status)
        result["status"] = "READY"
    except (RuntimeError, TimeoutError) as e:
        result["status"] = "FAILED"
        result["error"] = str(e)

    return result


def provision_memory(agent_key: str, region: str = REGION) -> dict:
    """Create an AgentCore memory namespace for the agent."""
    import boto3
    client = boto3.client("bedrock-agentcore", region_name=region)

    memory_id = f"conv-memory-{agent_key.replace('-', '_')}"

    try:
        resp = client.create_memory(
            memoryId=memory_id,
            memoryStrategies=[{
                "semanticMemoryStrategy": {
                    "name": f"{agent_key}-semantic",
                    "description": f"Semantic memory for {agent_key}",
                    "model": "us.anthropic.claude-sonnet-4-20250514",
                    "embeddingModel": "cohere.embed-english-v3",
                }
            }],
        )
        return {
            "memory_id": memory_id,
            "status": "CREATED",
            "arn": resp.get("memoryArn", ""),
        }
    except client.exceptions.ConflictException:
        return {
            "memory_id": memory_id,
            "status": "EXISTS",
        }
    except Exception as e:
        return {
            "memory_id": memory_id,
            "status": "FAILED",
            "error": str(e),
        }


def provision_knowledgebase(
    kb_config: KnowledgebaseConfig,
    project_name: str,
    region: str = REGION,
) -> dict:
    """Create an S3 bucket and upload knowledgebase files."""
    import boto3

    account_id = _get_account_id(region)
    bucket_name = f"agentcore-kb-{account_id}-{region}-{uuid.uuid4().hex[:6]}"

    s3 = boto3.client("s3", region_name=region)

    try:
        create_args: dict[str, Any] = {"Bucket": bucket_name}
        if region != "us-east-1":
            create_args["CreateBucketConfiguration"] = {"LocationConstraint": region}
        s3.create_bucket(**create_args)
    except Exception as e:
        return {"status": "FAILED", "error": f"Failed to create S3 bucket: {e}"}

    s3.put_bucket_tagging(
        Bucket=bucket_name,
        Tagging={"TagSet": [
            {"Key": "agentcore:project", "Value": project_name},
            {"Key": "agentcore:type", "Value": "knowledgebase"},
            {"Key": "agentcore:managed-by", "Value": "convention-cli"},
        ]},
    )

    uploaded = 0
    errors = []
    kb_path = Path(kb_config.path)
    for rel_file in kb_config.files:
        file_path = kb_path / rel_file
        s3_key = f"knowledgebase/{rel_file}"
        try:
            s3.upload_file(str(file_path), bucket_name, s3_key)
            uploaded += 1
        except Exception as e:
            errors.append(f"{rel_file}: {e}")

    return {
        "bucket_name": bucket_name,
        "s3_uri": f"s3://{bucket_name}/knowledgebase/",
        "files_uploaded": uploaded,
        "total_files": len(kb_config.files),
        "total_size_bytes": kb_config.total_size_bytes,
        "errors": errors,
        "status": "READY" if not errors else "PARTIAL",
    }


def register_skill(skill: SkillConfig, agent_key: str) -> dict:
    """Register a skill in the local skill registry for an agent."""
    return {
        "skill_name": skill.name,
        "agent_key": agent_key,
        "tool_spec": skill.tool_spec,
        "harness_tool_spec": skill.harness_tool_spec,
        "handler_path": skill.handler_path,
        "status": "REGISTERED",
    }


def provision_all(
    conventions: ProjectConventions,
    region: str = REGION,
    dry_run: bool = False,
    on_progress=None,
    force: bool = False,
) -> ProvisionResult:
    """Provision all AgentCore resources from conventions.

    Args:
        conventions: Parsed project conventions
        region: AWS region
        dry_run: If True, validate only without creating resources
        on_progress: Callback for progress updates: on_progress(stage, message)
        force: If True, recreate even if already exists
    """
    result = ProvisionResult()
    project_root = conventions.root

    def _progress(stage: str, msg: str):
        if on_progress:
            on_progress(stage, msg)

    if not conventions.agents:
        result.errors.append("No agents found in .agentcore/ directory")
        return result

    if dry_run:
        _progress("validate", "Dry run — validating conventions only")
        from agents.conventions.parser import validate_conventions
        warnings = validate_conventions(conventions)
        result.warnings = warnings
        for agent in conventions.agents:
            result.harnesses[agent.key] = {"status": "DRY_RUN", "agent_key": agent.key}
        return result

    _progress("iam", "Ensuring IAM execution role exists...")
    try:
        role_arn = _get_or_create_role(region)
        _progress("iam", f"Role ARN: {role_arn}")
    except Exception as e:
        result.errors.append(f"IAM role creation failed: {e}")
        return result

    _progress("iam", "Waiting for IAM propagation...")
    time.sleep(10)

    for agent in conventions.agents:
        existing_harness = check_agent_harness_exists(agent.key, project_root)
        if existing_harness and existing_harness.get("status") == "READY" and not force:
            _progress("harness", f"Harness for {agent.key} already exists (READY) — skipping")
            result.warnings.append(f"Harness for {agent.key} already exists — skipped (use force=True to recreate)")
            result.harnesses[agent.key] = {**existing_harness, "status": "EXISTING"}
            continue

        if existing_harness and force:
            _progress("harness", f"Harness for {agent.key} exists — recreating (force=True)...")

        _progress("harness", f"Creating harness for {agent.key}...")
        agent_skills = {
            name: conventions.skills[name]
            for name in agent.skills_used
            if name in conventions.skills
        }
        try:
            harness_info = provision_harness(
                agent, agent_skills, role_arn, region,
                on_status=lambda s: _progress("harness", f"  {agent.key}: {s}"),
                force=force,
                project_root=project_root,
            )
            result.harnesses[agent.key] = harness_info
            if harness_info["status"] not in ("READY", "EXISTING"):
                result.warnings.append(f"Harness for {agent.key} is {harness_info['status']}")
        except Exception as e:
            result.errors.append(f"Harness creation failed for {agent.key}: {e}")
            result.harnesses[agent.key] = {"status": "FAILED", "error": str(e)}

    for skill_name, skill in conventions.skills.items():
        agents_using = [a.key for a in conventions.agents if skill_name in a.skills_used]
        for agent_key in agents_using:
            _progress("skills", f"Registering {skill_name} for {agent_key}...")
            reg = register_skill(skill, agent_key)
            result.skills[f"{agent_key}/{skill_name}"] = reg

    for agent in conventions.agents:
        _progress("memory", f"Creating memory for {agent.key}...")
        try:
            mem = provision_memory(agent.key, region)
            result.memories[agent.key] = mem
        except Exception as e:
            result.warnings.append(f"Memory creation for {agent.key}: {e}")
            result.memories[agent.key] = {"status": "FAILED", "error": str(e)}

    if conventions.knowledgebase:
        project_name = Path(conventions.root).name
        _progress("knowledgebase", f"Creating S3 knowledgebase ({len(conventions.knowledgebase.files)} files)...")
        try:
            kb = provision_knowledgebase(conventions.knowledgebase, project_name, region)
            result.knowledgebase = kb
            if kb.get("errors"):
                result.warnings.extend(kb["errors"])
        except Exception as e:
            result.errors.append(f"Knowledgebase creation failed: {e}")
            result.knowledgebase = {"status": "FAILED", "error": str(e)}

    return result


def save_convention_config(
    conventions: ProjectConventions,
    provision_result: ProvisionResult,
    region: str = REGION,
) -> Path:
    """Save provisioned resources to agentcore_config.json."""
    config_path = Path(conventions.root) / "agentcore_config.json"

    existing = {}
    if config_path.exists():
        existing = json.loads(config_path.read_text())

    try:
        account_id = _get_account_id(region)
    except Exception:
        account_id = existing.get("account_id", "unknown")

    config = {
        "account_id": account_id,
        "region": region,
        "role_name": "HarnessExecutionRole",
        "role_arn": existing.get("role_arn", ""),
        "model_id": "us.anthropic.claude-opus-4-6-v1",
        "convention_source": conventions.agentcore_dir,
        "harnesses": {**existing.get("harnesses", {})},
        "skills_registry": {},
        "memories": {},
    }

    for agent_key, harness_info in provision_result.harnesses.items():
        config["harnesses"][agent_key] = {
            "harness_id": harness_info.get("harness_id", ""),
            "harness_arn": harness_info.get("harness_arn", ""),
            "harness_name": harness_info.get("harness_name", ""),
            "status": harness_info.get("status", "UNKNOWN"),
            "model_id": harness_info.get("model_id", ""),
            "execution_model": harness_info.get("execution_model", ""),
            "skills": harness_info.get("skills", []),
            "source": "convention",
        }

    for key, reg in provision_result.skills.items():
        config["skills_registry"][key] = {
            "skill_name": reg["skill_name"],
            "handler_path": reg.get("handler_path", ""),
            "status": reg["status"],
        }

    for agent_key, mem in provision_result.memories.items():
        config["memories"][agent_key] = {
            "memory_id": mem.get("memory_id", ""),
            "status": mem.get("status", "UNKNOWN"),
        }

    if provision_result.knowledgebase:
        config["knowledgebase"] = {
            "bucket_name": provision_result.knowledgebase.get("bucket_name", ""),
            "s3_uri": provision_result.knowledgebase.get("s3_uri", ""),
            "files_uploaded": provision_result.knowledgebase.get("files_uploaded", 0),
            "status": provision_result.knowledgebase.get("status", "UNKNOWN"),
        }

    config_path.write_text(json.dumps(config, indent=2))
    return config_path
