# Skill: Derive Skills

## Purpose

Map agent responsibilities to skills from the existing catalogue, and propose
new skills for any gaps.

## When to Use

After splitting evaluation (Step 3.5), before rendering the design (Step 5).

## CLI Command

```bash
# Check for duplicates against existing catalogue
python -m agent_builder.platforms.github_copilot.cli skills \
  --proposed schema_validation,pipeline_orchestration,data_quality_check
```

## Process

1. **Check existing catalogue**: Run the `skills` command with proposed IDs.
2. **Review duplicates**: If any proposed ID matches an existing skill, reuse it.
3. **Propose new skills** for uncovered responsibilities:
   - `skill_id`: snake_case identifier
   - `description`: one sentence
   - `layer`: 2 (core — always active) or 3 (conditional on context)
   - `applicable_when`: condition or "always"

## Output Format

```json
{
  "existing_skills": [
    {"skill_id": "delivery_model_analysis", "description": "Analyse delivery model activities"},
    {"skill_id": "activity_classification", "description": "Classify activity involvement"}
  ],
  "duplicates": ["delivery_model_analysis"]
}
```

## Skill Layers

| Layer | Name | Meaning |
|-------|------|---------|
| 2 | Core | Always active — fundamental to the agent's purpose |
| 3 | Conditional | Activated when specific context conditions are met |

## Quality Checks

- Every responsibility must have at least one skill
- No duplicate skill IDs in the catalogue
- Every skill must cite its delivery model source
- Reuse existing skills before inventing new ones
