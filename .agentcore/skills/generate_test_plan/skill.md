---
name: generate_test_plan
description: generate a test plan
risk_level: LOW
deterministic: false
dependencies: []
tools: []
input_schema:
  type: object
  properties:
    input:
      type: string
      description: Input for the skill
  required:
    - input
output_schema:
  type: object
  properties:
    result:
      type: object
      description: Skill output
---

# generate_test_plan

generate a test plan

## Usage

This skill is invoked by agents that reference it in their
`skills` attribute in the agent instructions file.
