# Skill: Render Design

## Purpose

Generate the 13-section agent design document and the agent-template.yaml
manifest from structured design data.

## When to Use

After deriving skills (Step 4), as the final production step (Steps 5-6).

## CLI Command

```bash
python -m agent_builder.platforms.github_copilot.cli render \
  --design-file /tmp/design.json
```

## Input Format

The design file is a JSON object matching the AgentDesign structure:

```json
{
  "role_name": "Data Engineer",
  "role_id": "data_engineer",
  "primary_responsibility": "automates data pipeline development",
  "delivery_model_root": "/path/to/model",
  "classifications": [
    {"activity_id": "3.2", "activity_name": "Design Data Solution", "classification": "OWNS", "rationale": "..."}
  ],
  "responsibilities": [
    {"name": "Schema design", "description": "Design data schemas", "automatable": true, "source": "3.2"}
  ],
  "inputs": [
    {"name": "Business requirements", "source": "Product Owner", "mandatory": true}
  ],
  "outputs": [
    {"name": "Data model", "consuming_activity": "4.4 Develop Data Solution"}
  ],
  "decisions": [
    {"name": "Schema breaking changes", "human_reserved": true, "rationale": "Requires stakeholder sign-off"}
  ],
  "tools": [
    {"name": "dbt", "purpose": "Data transformation and testing"}
  ],
  "knowledge": [
    {"name": "Data modelling standards", "type": "standard"}
  ],
  "skills": [
    {"skill_id": "schema_design", "description": "Design data schemas", "layer": 2, "applicable_when": "always", "is_existing": false, "responsibilities_covered": ["Schema design"]}
  ],
  "workflow_steps": [
    {"name": "Analyse requirements", "description": "Read and parse requirements", "human_gate": false}
  ],
  "handoffs": [
    {"direction": "FROM", "agent": "Product Owner", "trigger": "Requirements approved", "artefact": "Requirements doc"}
  ],
  "evaluation_metrics": [
    {"name": "Schema coverage", "metric": "% of data sources with defined schemas"}
  ],
  "constraints": [
    "Must not modify production schemas without approval"
  ]
}
```

## Output Files

Two files are written to `agent-builder/agent-designs/`:

1. **`<role_id>_Agent_Design.md`** — 13-section Markdown design document
2. **`<role_id>_agent-template.yaml`** — Starter agent manifest

## The 13 Sections

| # | Section | Content |
|---|---------|---------|
| 1 | Identity | Role name, ID, primary responsibility |
| 2 | Responsibilities | Numbered list with automatable flags |
| 3 | Scope | In-scope (OWNS/CONTRIBUTES), out-of-scope, human-reserved |
| 4 | Inputs | Table of inputs with source and mandatory flag |
| 5 | Outputs | Table of outputs with consuming activity |
| 6 | Skills | Skill mappings with layer and coverage |
| 7 | Knowledge | Knowledge sources with types |
| 8 | Tools | Tool table with purpose |
| 9 | Workflow | Ordered steps with human gates |
| 10 | Human Interaction | Details on human-reserved decisions |
| 11 | Handoffs | From/to other agents with triggers |
| 12 | Evaluation Metrics | Measurable quality criteria |
| 13 | Constraints & Guardrails | Boundaries and rules |

## Quality Checks Before Rendering

- Every responsibility has at least one skill
- Every OWNS activity has a workflow step
- Every human decision has a `▶ HUMAN GATE` marker
- No duplicate skill IDs
- All gaps listed in Summary of Information Gaps
