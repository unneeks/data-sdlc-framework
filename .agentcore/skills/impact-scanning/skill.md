---
name: impact-scanning
description: Scan a repository, build dependency graph, and trace change impact through the graph.
risk_level: MEDIUM
deterministic: false
dependencies: []
tools:
  - discover_repository
  - read_file
  - analyze_dependencies
  - analyze_impact
input_schema:
  type: object
  properties:
    repository_root:
      type: string
      description: Absolute path to the repository root directory
    change_description:
      type: string
      description: Natural language description of the change
    affected_files:
      type: array
      items:
        type: string
      description: List of directly affected file paths
  required:
    - repository_root
output_schema:
  type: object
  properties:
    affected_assets:
      type: array
      description: Assets affected by the change
    risk_level:
      type: string
      description: Overall risk level (LOW/MEDIUM/HIGH/CRITICAL)
    confidence:
      type: number
      description: Confidence score 0-1
---

# Impact Scanning

Scans a repository, builds a dependency graph from imports and references,
and traces the impact of a proposed change through the graph to determine
the full blast radius.

## Tools

- `discover_repository` — Walk the repository file tree and classify files
- `read_file` — Read specific files for deeper analysis
- `analyze_dependencies` — Build the dependency graph from discovered files
- `analyze_impact` — Trace change impact through the dependency graph

## Workflow

1. Discover repository structure with `discover_repository`
2. Build dependency graph with `analyze_dependencies`
3. Trace change impact with `analyze_impact`
4. Return structured findings with provenance and confidence

## Usage

Referenced by agents with `skills: [impact-scanning]` in their instructions file.
