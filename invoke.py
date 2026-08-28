"""
Invoke the deployed Data SDLC Framework agent on AgentCore Runtime.

Usage:
    python invoke.py
    python invoke.py --action plan
    python invoke.py --action impact --change-id CHG-001
"""

import argparse
import json
import uuid

import boto3

CONFIG_FILE = "runtime_config.json"


def main():
    parser = argparse.ArgumentParser(description="Invoke the Data SDLC agent")
    parser.add_argument("--action", default="classify", help="Action: classify, plan, impact, twin, agents, evaluate")
    parser.add_argument("--prompt", default="Migrate Teradata data warehouse to cloud lakehouse", help="Prompt text for classify action")
    parser.add_argument("--change-id", default="CHG-001", help="Change ID for impact/evaluate actions")
    args = parser.parse_args()

    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)

    client = boto3.client("bedrock-agentcore", region_name=config["region"])

    payload = {"action": args.action, "prompt": args.prompt, "change_id": args.change_id}

    print(f"Invoking agent: {config['agent_name']}")
    print(f"  Action: {args.action}")
    print(f"  Runtime ARN: {config['runtime_arn']}")
    print()

    response = client.invoke_agent_runtime(
        agentRuntimeArn=config["runtime_arn"],
        runtimeSessionId=str(uuid.uuid4()),
        payload=json.dumps(payload).encode("utf-8"),
    )

    print(f"  Status: {response.get('statusCode')}")
    print()

    body = response.get("response")
    if hasattr(body, "read"):
        raw = body.read().decode("utf-8")
    else:
        raw = str(body)

    try:
        result = json.loads(raw)
        if isinstance(result, str):
            result = json.loads(result)
        print(json.dumps(result, indent=2))
    except (json.JSONDecodeError, TypeError):
        print(raw)


if __name__ == "__main__":
    main()
