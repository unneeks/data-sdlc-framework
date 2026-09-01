---
name: data-profiling
description: Profile data assets by analyzing schemas, quality checks, and code patterns.
risk_level: LOW
deterministic: false
dependencies: []
tools:
  - discover_repository
  - read_file
  - profile_data_assets
input_schema:
  type: object
  properties:
    repository_root:
      type: string
      description: Absolute path to the repository root directory
  required:
    - repository_root
output_schema:
  type: object
  properties:
    profiles:
      type: array
      description: Profiled data assets with schema and quality info
    quality_indicators:
      type: object
      description: Aggregated quality indicators
---

# Data Profiling

Profiles data assets by analyzing schemas, quality checks, and code
to produce column statistics, quality indicators, and domain mappings.

## Tools

- `discover_repository` — Find all data assets in the repository
- `read_file` — Read schema and transformation files
- `profile_data_assets` — Profile schemas, columns, and quality indicators

## Usage

Referenced by agents with `skills: [data-profiling]` in their instructions file.
