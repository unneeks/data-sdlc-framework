# Skill: Evaluate Agent Splitting

## Purpose

Determine whether the agent should be split into multiple sub-agents using
the 7-criteria evaluation framework.

## When to Use

After classifying activities (Step 3), before deriving skills (Step 4).

## The 7 Criteria

| # | Criterion | Split Signal |
|---|-----------|-------------|
| 1 | **Context Boundaries** | OWNS activities need different repos, standards, or domains |
| 2 | **Tool Permissions** | Different service accounts or access profiles needed |
| 3 | **Independent Verification** | Separate review/gatekeeping processes needed |
| 4 | **Parallelism Value** | Responsibilities can/should run in parallel |
| 5 | **Development & Test Ease** | Large scope benefits from isolation |
| 6 | **Task Count** | More than 8 core responsibilities (strong signal) |
| 7 | **Team Scaling** | Splitting enables parallel development across teams |

## CLI Command

```bash
python -m agent_builder.platforms.github_copilot.cli split \
  --role "Data Engineer" \
  --responsibility "automates data pipeline development" \
  --classifications-file /tmp/classifications.json
```

## Input Format

The classifications file must be JSON array:
```json
[
  {
    "activity_id": "3.2",
    "activity_name": "Design Data Solution",
    "classification": "OWNS",
    "rationale": "Data Engineer responsible for schema design"
  }
]
```

## Output Format

```json
{
  "decision": "KEEP_AS_ONE",
  "rationale": "Score: 0 split vs 1 keep. Manageable scope.",
  "split_score": 0,
  "keep_score": 1,
  "criteria": [
    {"name": "task_count", "recommendation": "KEEP", "rationale": "3 responsibilities"}
  ],
  "proposed_subagents": []
}
```

## Decision Rules

- **`split_score > keep_score`** → Recommend `SPLIT_INTO_SUBAGENTS`
- **`keep_score >= split_score`** → Recommend `KEEP_AS_ONE`
- **Heuristic mode** (no LLM criteria): uses activity count and phase span
- **LLM mode**: provide `criteria_results` in the classifications file

## If SPLIT Recommended

Restart the process for each proposed sub-agent:
1. Each sub-agent gets its own role name and subset of OWNS activities
2. Create separate design documents for each
3. Optionally create a parent coordination agent
