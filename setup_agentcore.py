#!/usr/bin/env python3
"""
AgentCore Harness Setup for Data SDLC Framework.

Creates an IAM execution role and one AgentCore Harness per metamodel agent,
then saves the harness ARNs to agentcore_config.json.

Usage:
    python setup_agentcore.py              # Create all harnesses
    python setup_agentcore.py --cleanup    # Delete all harnesses and role

Prerequisites:
    - AWS credentials configured (aws configure / env vars / IAM role)
    - Region set via AWS_DEFAULT_REGION or AWS_REGION (default: us-west-2)
    - Permissions: iam:CreateRole, iam:PutRolePolicy, iam:GetRole,
      iam:DeleteRole, iam:DeleteRolePolicy, bedrock-agentcore-control:*
"""

import argparse
import json
import os
import sys
import time
import uuid
from pathlib import Path

import boto3

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent

ROLE_NAME = "DataSDLC_HarnessExecutionRole"
POLICY_NAME = "DataSDLC_HarnessExecutionPolicy"
CONFIG_FILE = PROJECT_ROOT / "agentcore_config.json"

REGION = os.environ.get("AWS_DEFAULT_REGION") or os.environ.get("AWS_REGION") or "us-west-2"

MODEL_ID = "global.anthropic.claude-sonnet-4-6"

# The five metamodel agents to provision
AGENT_KEYS = [
    "impact-analysis-agent",
    "regression-agent",
    "data-quality-agent",
    "data-model-composer",
    "delivery-compliance-agent",
]

# Harness polling
POLL_INTERVAL = 5       # seconds between status checks
POLL_TIMEOUT = 600      # max seconds to wait for READY
FAILURE_STATUSES = ("CREATE_FAILED", "UPDATE_FAILED", "DELETE_FAILED")

# ---------------------------------------------------------------------------
# IAM helpers (adapted from agentcore-features/01-harness/utils/iam.py)
# ---------------------------------------------------------------------------

def get_account_id() -> str:
    return boto3.client("sts", region_name=REGION).get_caller_identity()["Account"]


def _build_trust_policy() -> dict:
    """Trust policy allowing the AgentCore service principal to assume the role."""
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": ["bedrock-agentcore.amazonaws.com"]},
                "Action": "sts:AssumeRole",
                "Condition": {
                    "StringEquals": {"aws:SourceAccount": get_account_id()}
                },
            }
        ],
    }


PERMISSIONS_POLICY = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "BedrockInvokeModel",
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream",
            ],
            "Resource": [
                "arn:aws:bedrock:*::foundation-model/*",
                "arn:aws:bedrock:*:*:inference-profile/*",
            ],
        },
        {
            "Sid": "ECRPull",
            "Effect": "Allow",
            "Action": [
                "ecr:GetDownloadUrlForLayer",
                "ecr:BatchGetImage",
                "ecr:BatchCheckLayerAvailability",
                "ecr:GetAuthorizationToken",
            ],
            "Resource": "*",
        },
        {
            "Sid": "EcrPublicPull",
            "Effect": "Allow",
            "Action": ["ecr-public:GetAuthorizationToken"],
            "Resource": "*",
        },
        {
            "Sid": "StsForEcrPublicPull",
            "Effect": "Allow",
            "Action": ["sts:GetServiceBearerToken"],
            "Resource": "*",
        },
        {
            "Sid": "XRay",
            "Effect": "Allow",
            "Action": ["xray:PutTraceSegments", "xray:PutTelemetryRecords"],
            "Resource": "*",
        },
        {
            "Sid": "CloudWatchLogs",
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents",
            ],
            "Resource": [
                "arn:aws:logs:*:*:log-group:/aws/bedrock-agentcore/runtimes/*",
                "arn:aws:logs:*:*:log-group:/aws/bedrock-agentcore/runtimes/*:log-stream:*",
            ],
        },
        {
            "Sid": "AgentCore",
            "Effect": "Allow",
            "Action": [
                "bedrock-agentcore:CreateMemory",
                "bedrock-agentcore:GetMemory",
                "bedrock-agentcore:ListMemories",
                "bedrock-agentcore:DeleteMemory",
                "bedrock-agentcore:RetrieveMemoryRecords",
                "bedrock-agentcore:CreateEvent",
                "bedrock-agentcore:ListEvents",
                "bedrock-agentcore:GetEvent",
                "bedrock-agentcore:StartCodeInterpreterSession",
                "bedrock-agentcore:StopCodeInterpreterSession",
                "bedrock-agentcore:GetCodeInterpreterSession",
                "bedrock-agentcore:InvokeCodeInterpreter",
                "bedrock-agentcore:InvokeGateway",
            ],
            "Resource": "*",
        },
        {
            "Sid": "GetAgentCoreApiKeys",
            "Effect": "Allow",
            "Action": ["bedrock-agentcore:GetResourceApiKey"],
            "Resource": "*",
        },
    ],
}


def create_harness_role() -> str:
    """Create (or update) the IAM execution role. Returns the role ARN.

    Idempotent: re-running updates the trust policy and permissions in place.
    """
    iam = boto3.client("iam", region_name=REGION)
    trust_policy = json.dumps(_build_trust_policy())

    try:
        existing = iam.get_role(RoleName=ROLE_NAME)
        arn = existing["Role"]["Arn"]
        print(f"  Role already exists: {arn}")
        iam.update_assume_role_policy(RoleName=ROLE_NAME, PolicyDocument=trust_policy)
    except iam.exceptions.NoSuchEntityException:
        resp = iam.create_role(
            RoleName=ROLE_NAME,
            AssumeRolePolicyDocument=trust_policy,
            Description="Execution role for Data SDLC Framework AgentCore Harnesses",
        )
        arn = resp["Role"]["Arn"]
        print(f"  Created role: {arn}")

    iam.put_role_policy(
        RoleName=ROLE_NAME,
        PolicyName=POLICY_NAME,
        PolicyDocument=json.dumps(PERMISSIONS_POLICY),
    )
    print(f"  Attached policy: {POLICY_NAME}")
    return arn


def delete_harness_role() -> None:
    """Delete the IAM execution role and all attached policies."""
    iam = boto3.client("iam", region_name=REGION)

    try:
        for page in iam.get_paginator("list_role_policies").paginate(RoleName=ROLE_NAME):
            for name in page["PolicyNames"]:
                iam.delete_role_policy(RoleName=ROLE_NAME, PolicyName=name)
                print(f"  Deleted inline policy: {name}")
        for page in iam.get_paginator("list_attached_role_policies").paginate(RoleName=ROLE_NAME):
            for policy in page["AttachedPolicies"]:
                iam.detach_role_policy(RoleName=ROLE_NAME, PolicyArn=policy["PolicyArn"])
                print(f"  Detached managed policy: {policy['PolicyName']}")
    except iam.exceptions.NoSuchEntityException:
        print(f"  Role {ROLE_NAME} not found — nothing to delete")
        return

    try:
        iam.delete_role(RoleName=ROLE_NAME)
        print(f"  Deleted role: {ROLE_NAME}")
    except iam.exceptions.NoSuchEntityException:
        print(f"  Role {ROLE_NAME} already gone")
    except iam.exceptions.DeleteConflictException as e:
        print(f"  Could not delete role {ROLE_NAME}: {e}")
        print("  Remove whatever still references it, then delete manually.")


# ---------------------------------------------------------------------------
# Harness lifecycle (adapted from agentcore-features/01-harness/utils/harness.py)
# ---------------------------------------------------------------------------

def poll_harness_status(control, harness_id: str, target_status: str = "READY") -> dict:
    """Block until a Harness reaches target_status. Returns the describe response.

    Raises RuntimeError on failure states, TimeoutError on timeout.
    """
    deadline = time.monotonic() + POLL_TIMEOUT
    while True:
        resp = control.get_harness(harnessId=harness_id)
        status = resp["harness"]["status"]
        print(f"    Status: {status}")
        if status == target_status:
            return resp
        if status in FAILURE_STATUSES:
            reason = resp["harness"].get("failureReason", "")
            raise RuntimeError(f"Harness entered {status}. {reason}".strip())
        if time.monotonic() > deadline:
            raise TimeoutError(
                f"Harness not {target_status} after {POLL_TIMEOUT}s (current: {status})"
            )
        time.sleep(POLL_INTERVAL)


def create_harness(control, agent_key: str, role_arn: str) -> dict:
    """Create a single AgentCore Harness for the given agent key.

    Returns a dict with harnessId, arn, and name.
    """
    suffix = uuid.uuid4().hex[:8]
    harness_name = f"DataSDLC_{agent_key}_{suffix}"

    print(f"\n  Creating harness: {harness_name}")
    resp = control.create_harness(
        harnessName=harness_name,
        executionRoleArn=role_arn,
    )
    harness = resp["harness"]
    print(f"    Harness ID:  {harness['harnessId']}")
    print(f"    Harness ARN: {harness['arn']}")

    return {
        "harnessId": harness["harnessId"],
        "arn": harness["arn"],
        "name": harness_name,
        "agent_key": agent_key,
    }


# ---------------------------------------------------------------------------
# Setup (create all harnesses)
# ---------------------------------------------------------------------------

def setup():
    """Provision the IAM role and create one Harness per metamodel agent."""
    print("=" * 60)
    print("Data SDLC Framework — AgentCore Harness Setup")
    print("=" * 60)

    account_id = get_account_id()
    print(f"\nAccount:  {account_id}")
    print(f"Region:   {REGION}")
    print(f"Agents:   {len(AGENT_KEYS)}")
    print(f"Model:    {MODEL_ID}")

    # Step 1: IAM role
    print("\n--- Step 1: IAM Execution Role ---")
    role_arn = create_harness_role()
    print(f"  Role ARN: {role_arn}")
    print("  Waiting 10s for IAM propagation...")
    time.sleep(10)

    # Step 2: Create harnesses
    print("\n--- Step 2: Create Harnesses ---")
    control = boto3.client("bedrock-agentcore-control", region_name=REGION)

    harnesses = []
    for agent_key in AGENT_KEYS:
        info = create_harness(control, agent_key, role_arn)
        harnesses.append(info)

    # Step 3: Wait for all to become READY
    print("\n--- Step 3: Wait for Harnesses to become READY ---")
    for info in harnesses:
        print(f"\n  Polling: {info['agent_key']} ({info['harnessId']})")
        try:
            poll_harness_status(control, info["harnessId"])
            info["status"] = "READY"
            print(f"    READY")
        except (RuntimeError, TimeoutError) as e:
            info["status"] = "FAILED"
            info["error"] = str(e)
            print(f"    FAILED: {e}")

    # Step 4: Save config
    print("\n--- Step 4: Save Configuration ---")
    config = {
        "account_id": account_id,
        "region": REGION,
        "role_name": ROLE_NAME,
        "role_arn": role_arn,
        "model_id": MODEL_ID,
        "harnesses": {},
    }
    for info in harnesses:
        config["harnesses"][info["agent_key"]] = {
            "harness_id": info["harnessId"],
            "harness_arn": info["arn"],
            "harness_name": info["name"],
            "status": info.get("status", "UNKNOWN"),
        }

    CONFIG_FILE.write_text(json.dumps(config, indent=2))
    print(f"  Saved to: {CONFIG_FILE}")

    # Summary
    print("\n" + "=" * 60)
    print("Setup Summary")
    print("=" * 60)
    ready = sum(1 for h in harnesses if h.get("status") == "READY")
    failed = sum(1 for h in harnesses if h.get("status") == "FAILED")
    print(f"  READY:  {ready}/{len(harnesses)}")
    if failed:
        print(f"  FAILED: {failed}/{len(harnesses)}")
    print(f"\n  Config: {CONFIG_FILE}")
    print(f"  Role:   {role_arn}")

    for info in harnesses:
        status_marker = "OK" if info.get("status") == "READY" else "FAIL"
        print(f"  [{status_marker}] {info['agent_key']}: {info['arn']}")

    if ready == len(harnesses):
        print("\nAll harnesses are ready. You can now start the API server:")
        print(f"  cd {PROJECT_ROOT}")
        print("  HARNESS_MODE=REAL python apps/api/main.py")
    else:
        print("\nSome harnesses failed. Check the errors above.")
        print("You can still run in DEMO mode (no LLM required):")
        print(f"  cd {PROJECT_ROOT}")
        print("  python apps/api/main.py")


# ---------------------------------------------------------------------------
# Cleanup (delete all harnesses and role)
# ---------------------------------------------------------------------------

def cleanup():
    """Delete all harnesses from agentcore_config.json and the IAM role."""
    print("=" * 60)
    print("Data SDLC Framework — AgentCore Harness Cleanup")
    print("=" * 60)

    if not CONFIG_FILE.exists():
        print(f"\nNo config file found at {CONFIG_FILE}")
        print("Nothing to clean up. Attempting to delete the IAM role anyway...")
        delete_harness_role()
        return

    config = json.loads(CONFIG_FILE.read_text())
    print(f"\nAccount: {config.get('account_id', 'unknown')}")
    print(f"Region:  {config.get('region', REGION)}")

    region = config.get("region", REGION)
    control = boto3.client("bedrock-agentcore-control", region_name=region)

    # Step 1: Delete harnesses
    print("\n--- Step 1: Delete Harnesses ---")
    harnesses = config.get("harnesses", {})
    for agent_key, info in harnesses.items():
        harness_id = info.get("harness_id")
        if not harness_id:
            continue
        print(f"\n  Deleting: {agent_key} ({harness_id})")
        try:
            control.delete_harness(harnessId=harness_id)
            print(f"    Deleted")
        except control.exceptions.ResourceNotFoundException:
            print(f"    Already gone")
        except Exception as e:
            print(f"    Warning: {e}")

    # Step 2: Delete IAM role
    print("\n--- Step 2: Delete IAM Role ---")
    delete_harness_role()

    # Step 3: Remove config file
    print("\n--- Step 3: Remove Config File ---")
    CONFIG_FILE.unlink(missing_ok=True)
    print(f"  Removed: {CONFIG_FILE}")

    print("\nCleanup complete.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="AgentCore Harness setup/cleanup for Data SDLC Framework"
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Delete all harnesses and the IAM role instead of creating them",
    )
    args = parser.parse_args()

    if args.cleanup:
        cleanup()
    else:
        setup()


if __name__ == "__main__":
    main()
