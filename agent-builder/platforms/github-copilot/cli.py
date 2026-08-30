#!/usr/bin/env python3
"""Agent Builder CLI — invokable from terminal or GitHub Copilot.

Usage:
    python -m agent_builder.platforms.github_copilot.cli locate --model-root /path/to/model
    python -m agent_builder.platforms.github_copilot.cli analyse --model-root /path --role "Data Engineer" --responsibility "automates pipelines"
    python -m agent_builder.platforms.github_copilot.cli split --role "Data Engineer" --classifications-file results.json
    python -m agent_builder.platforms.github_copilot.cli skills --proposed skill1,skill2
    python -m agent_builder.platforms.github_copilot.cli render --design-file design.json
    python -m agent_builder.platforms.github_copilot.cli full --model-root /path --role "Data Engineer" --responsibility "automates pipelines"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from agent_builder.platforms.github_copilot.tools import (
    analyse_activities,
    check_skills,
    locate_delivery_model,
    render_design,
    run_full_pipeline,
    run_splitting_evaluation,
)


def _output(data: dict, pretty: bool = True) -> None:
    """Print JSON output."""
    indent = 2 if pretty else None
    print(json.dumps(data, indent=indent, default=str))


def cmd_locate(args: argparse.Namespace) -> None:
    """Locate delivery model and list activities."""
    result = locate_delivery_model(args.model_root)
    _output(result)


def cmd_analyse(args: argparse.Namespace) -> None:
    """Analyse delivery model activities."""
    result = analyse_activities(args.model_root, args.role, args.responsibility)
    _output(result)


def cmd_split(args: argparse.Namespace) -> None:
    """Run splitting evaluation."""
    if args.classifications_file:
        with open(args.classifications_file, encoding="utf-8") as f:
            classifications = json.load(f)
    elif args.classifications_json:
        classifications = json.loads(args.classifications_json)
    else:
        print("Error: provide --classifications-file or --classifications-json", file=sys.stderr)
        sys.exit(1)

    result = run_splitting_evaluation(
        args.role,
        args.responsibility,
        classifications,
    )
    _output(result)


def cmd_skills(args: argparse.Namespace) -> None:
    """Check skill catalogue for duplicates."""
    proposed = [s.strip() for s in args.proposed.split(",") if s.strip()] if args.proposed else []
    result = check_skills(proposed)
    _output(result)


def cmd_render(args: argparse.Namespace) -> None:
    """Render design document and manifest."""
    with open(args.design_file, encoding="utf-8") as f:
        design_data = json.load(f)
    result = render_design(design_data)
    _output(result)


def cmd_full(args: argparse.Namespace) -> None:
    """Run complete pipeline."""
    classifications = None
    if args.classifications_file:
        with open(args.classifications_file, encoding="utf-8") as f:
            classifications = json.load(f)

    result = run_full_pipeline(
        args.model_root,
        args.role,
        args.responsibility,
        classifications,
    )
    _output(result)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="agent-builder-cli",
        description="Agent Builder CLI — bootstrap AI agent designs from delivery models",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # locate
    p_locate = subparsers.add_parser("locate", help="Check if delivery model exists")
    p_locate.add_argument("--model-root", required=True, help="Path to delivery model directory")
    p_locate.set_defaults(func=cmd_locate)

    # analyse
    p_analyse = subparsers.add_parser("analyse", help="Analyse delivery model activities")
    p_analyse.add_argument("--model-root", required=True, help="Path to delivery model directory")
    p_analyse.add_argument("--role", required=True, help="Agent role name")
    p_analyse.add_argument("--responsibility", required=True, help="Primary responsibility")
    p_analyse.set_defaults(func=cmd_analyse)

    # split
    p_split = subparsers.add_parser("split", help="Evaluate agent splitting")
    p_split.add_argument("--role", required=True, help="Agent role name")
    p_split.add_argument("--responsibility", default="", help="Primary responsibility")
    p_split.add_argument("--classifications-file", help="Path to classifications JSON file")
    p_split.add_argument("--classifications-json", help="Inline classifications JSON string")
    p_split.set_defaults(func=cmd_split)

    # skills
    p_skills = subparsers.add_parser("skills", help="Check skill catalogue")
    p_skills.add_argument("--proposed", default="", help="Comma-separated proposed skill IDs")
    p_skills.set_defaults(func=cmd_skills)

    # render
    p_render = subparsers.add_parser("render", help="Render design document and manifest")
    p_render.add_argument("--design-file", required=True, help="Path to design JSON file")
    p_render.set_defaults(func=cmd_render)

    # full
    p_full = subparsers.add_parser("full", help="Run complete pipeline")
    p_full.add_argument("--model-root", required=True, help="Path to delivery model directory")
    p_full.add_argument("--role", required=True, help="Agent role name")
    p_full.add_argument("--responsibility", required=True, help="Primary responsibility")
    p_full.add_argument("--classifications-file", help="Path to classifications JSON file")
    p_full.set_defaults(func=cmd_full)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
