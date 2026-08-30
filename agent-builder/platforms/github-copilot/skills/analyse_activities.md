# Skill: Analyse Activities

## Purpose

Read delivery model activity files and classify each activity's involvement
level for the target agent role.

## When to Use

After locating the delivery model (Step 2), before evaluating splitting (Step 3.5).

## Process

1. Run the `locate` command to confirm the delivery model exists and list activities.
2. Run the `analyse` command to read all activity files.
3. For each activity, classify involvement using the returned content:

| Code | Meaning | Criteria |
|------|---------|----------|
| `OWNS` | Primary responsible | Agent is listed as owner/responsible in RACI tables |
| `CONTRIBUTES` | Participant | Agent participates but doesn't own |
| `CONSUMES` | Receives outputs | Agent receives deliverables from this activity |
| `OUT_OF_SCOPE` | No involvement | No connection to this agent role |

## CLI Commands

```bash
# Step 1: Locate model
python -m agent_builder.platforms.github_copilot.cli locate \
  --model-root /path/to/delivery/model

# Step 2: Analyse activities
python -m agent_builder.platforms.github_copilot.cli analyse \
  --model-root /path/to/delivery/model \
  --role "Data Engineer" \
  --responsibility "automates data pipeline development"
```

## Output Format

The `analyse` command returns JSON per activity:
```json
{
  "activity_id": "3.2",
  "path": "/path/to/3.2_Design_Data_Solution.md",
  "filename": "3.2_Design_Data_Solution.md",
  "content": "...",
  "sections": [{"heading": "...", "body": "..."}]
}
```

## Classification Signals

Look for these in the activity content:
- **RACI tables**: Responsible (R) = OWNS, Accountable (A) = CONTRIBUTES
- **Task lists**: Tasks under the agent's role = OWNS
- **Input/Output tables**: Receiving output = CONSUMES
- **Stakeholder sections**: Named as participant = CONTRIBUTES

## Save Classifications

Write the classification results to a JSON file for the next step:
```json
[
  {
    "activity_id": "3.2",
    "activity_name": "Design Data Solution",
    "classification": "OWNS",
    "rationale": "Data Engineer responsible for schema design per RACI table"
  }
]
```
