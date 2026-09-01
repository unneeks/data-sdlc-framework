#!/usr/bin/env python3
"""Create all AgentCore Harness agents.

Usage:
    python -m agents.harness_agents.create_all
    python -m agents.harness_agents.create_all --region us-east-1
    python -m agents.harness_agents.create_all --role-arn arn:aws:iam::123:role/MyRole
"""

from __future__ import annotations

import argparse
import json

from agents.harness_agents.create_discovery_agent import create_or_update as create_discovery
from agents.harness_agents.create_agent_builder import create_or_update as create_builder


def main():
    parser = argparse.ArgumentParser(description="Create all AgentCore Harness agents")
    parser.add_argument("--region", default="us-west-2")
    parser.add_argument("--role-arn", default="arn:aws:iam::981956186421:role/HarnessExecutionRole")
    args = parser.parse_args()

    results = {}

    print("=" * 60)
    print("Creating Discovery Agent...")
    print("=" * 60)
    results["discovery_agent"] = create_discovery(region=args.region, role_arn=args.role_arn)

    print()

    print("=" * 60)
    print("Creating Agent Builder...")
    print("=" * 60)
    results["agent_builder"] = create_builder(region=args.region, role_arn=args.role_arn)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for name, r in results.items():
        status = r.get("status", r.get("error", "UNKNOWN"))
        arn = r.get("arn", "N/A")
        action = r.get("action", "ERROR")
        print(f"  {name:25s} {action:8s} {status:8s} {arn}")

    print(f"\n{json.dumps(results, indent=2)}")


if __name__ == "__main__":
    main()
