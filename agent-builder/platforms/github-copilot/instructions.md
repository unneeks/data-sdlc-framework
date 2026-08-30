# Agent Builder — CLI Instructions

## Overview

The Agent Builder bootstraps AI agent designs from delivery model frameworks.
It runs as a CLI tool that can be invoked from any terminal, including GitHub
Copilot's terminal integration.

## Quick Start

```bash
# Full pipeline — non-interactive
python -m agent_builder.platforms.github_copilot.cli full \
  --model-root /path/to/delivery/model \
  --role "Data Engineer" \
  --responsibility "automates data pipeline development"

# Step-by-step
python -m agent_builder.platforms.github_copilot.cli locate --model-root /path/to/model
python -m agent_builder.platforms.github_copilot.cli analyse --model-root /path --role "Data Engineer" --responsibility "automates pipelines"
python -m agent_builder.platforms.github_copilot.cli split --role "Data Engineer" --classifications-file /tmp/classifications.json
python -m agent_builder.platforms.github_copilot.cli skills --proposed skill1,skill2
python -m agent_builder.platforms.github_copilot.cli render --design-file /tmp/design.json
```

## The 8-Step Process

### STEP 1 — Parse the Request

Provide:
- **`--role`**: Agent role name (e.g. `"Data Engineer"`)
- **`--responsibility`**: Primary responsibility (one sentence)
- **`--phase-scope`** (optional): Comma-separated phase IDs

### STEP 2 — Locate the Delivery Model

```bash
python -m agent_builder.platforms.github_copilot.cli locate \
  --model-root ./docs/knowledge-base/delivery_model_pages_linked
```

Returns JSON with `found`, `activity_count`, `activity_ids`, and `activity_files`.

### STEP 3 — Analyse Activities

```bash
python -m agent_builder.platforms.github_copilot.cli analyse \
  --model-root ./docs/knowledge-base/delivery_model_pages_linked \
  --role "Data Engineer" \
  --responsibility "automates data pipeline development"
```

Reads all activity files, returns their content and metadata. Classification
is done by the LLM using the returned data — the tool provides the raw material.

### STEP 3.5 — Evaluate Splitting

After classifying activities, evaluate whether to split:

```bash
python -m agent_builder.platforms.github_copilot.cli split \
  --role "Data Engineer" \
  --responsibility "automates data pipeline development" \
  --classifications-file /tmp/classifications.json
```

The classifications file is a JSON array:
```json
[
  {"activity_id": "3.2", "activity_name": "Design Data Solution", "classification": "OWNS", "rationale": "..."},
  {"activity_id": "4.4", "activity_name": "Develop Data Solution", "classification": "OWNS", "rationale": "..."}
]
```

Returns the split decision, score, criteria results, and proposed sub-agents.

### STEP 4 — Derive Skills

```bash
python -m agent_builder.platforms.github_copilot.cli skills \
  --proposed schema_validation,pipeline_orchestration
```

Checks the skill catalogue for duplicates and returns existing skills.

### STEP 5 & 6 — Render Design Document and Manifest

```bash
python -m agent_builder.platforms.github_copilot.cli render \
  --design-file /tmp/design.json
```

The design file contains the full AgentDesign structure. Writes:
- `agent-builder/agent-designs/<role_id>_Agent_Design.md`
- `agent-builder/agent-designs/<role_id>_agent-template.yaml`

### STEP 7 — Confirm

Review the generated files before committing.

### STEP 8 — Offer Configurator

After writing, optionally generate a Configurator Agent for use-case onboarding.

## Integration with GitHub Copilot

When using the `@agent-builder` Copilot agent, it delegates to these CLI tools
via terminal commands. The agent reads the prompt.md for its identity and
invokes skill files for each step.

## Skills Reference

| Skill | File | Purpose |
|-------|------|---------|
| Analyse Activities | `skills/analyse_activities.md` | Classify delivery model activities by involvement |
| Evaluate Splitting | `skills/evaluate_splitting.md` | 7-criteria agent splitting evaluation |
| Derive Skills | `skills/derive_skills.md` | Check catalogue, propose new skills |
| Render Design | `skills/render_design.md` | Generate 13-section document + YAML manifest |
