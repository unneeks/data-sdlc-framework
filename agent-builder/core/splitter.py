"""Agent splitting evaluation — the 7-criteria analysis from Step 3b.5."""

from __future__ import annotations

from agent_builder.core.models import (
    ActivityClassification,
    AgentRole,
    InvolvementCode,
    SplitCriterion,
    SplitDecision,
    SplitEvaluation,
)


def evaluate_splitting(
    role: AgentRole,
    classifications: list[ActivityClassification],
    criteria_results: list[dict[str, str]] | None = None,
) -> SplitEvaluation:
    """Evaluate whether an agent should be split into sub-agents.

    If criteria_results is provided (from LLM analysis), use those.
    Otherwise, apply heuristic rules based on activity count.
    """
    owns = [c for c in classifications if c.classification == InvolvementCode.OWNS]
    responsibility_count = len(owns)

    if criteria_results:
        return _evaluate_from_llm(role, owns, criteria_results)

    return _evaluate_heuristic(role, owns, responsibility_count)


def _evaluate_heuristic(
    role: AgentRole,
    owns: list[ActivityClassification],
    count: int,
) -> SplitEvaluation:
    """Heuristic evaluation when no LLM criteria analysis is available."""
    criteria = []

    if count <= 5:
        criteria.append(SplitCriterion("task_count", "KEEP", f"{count} responsibilities — under threshold"))
        return SplitEvaluation(
            decision=SplitDecision.KEEP_AS_ONE,
            rationale=f"{count} OWNS activities — manageable as single agent",
            criteria=criteria,
            split_score=0,
            keep_score=1,
        )

    split_score = 0
    keep_score = 0

    if count > 8:
        criteria.append(SplitCriterion("task_count", "SPLIT", f"{count} > 8 threshold"))
        split_score += 1
    else:
        criteria.append(SplitCriterion("task_count", "KEEP", f"{count} <= 8"))
        keep_score += 1

    activity_ids = [o.activity_id for o in owns]
    phases = set()
    for aid in activity_ids:
        phase = aid.split(".")[0] if "." in aid else aid[0]
        phases.add(phase)

    if len(phases) > 1:
        criteria.append(SplitCriterion("context_boundaries", "SPLIT", f"Spans {len(phases)} phases: {sorted(phases)}"))
        split_score += 1
    else:
        criteria.append(SplitCriterion("context_boundaries", "KEEP", "Single phase"))
        keep_score += 1

    if split_score > keep_score:
        proposed = [
            {"name": f"{role.role_id}_phase_{p}", "activities": [o.activity_id for o in owns if o.activity_id.startswith(p)]}
            for p in sorted(phases)
        ]
        return SplitEvaluation(
            decision=SplitDecision.SPLIT_INTO_SUBAGENTS,
            rationale=f"Score: {split_score} split vs {keep_score} keep. {count} responsibilities across {len(phases)} phases.",
            criteria=criteria,
            split_score=split_score,
            keep_score=keep_score,
            proposed_subagents=proposed,
        )

    return SplitEvaluation(
        decision=SplitDecision.KEEP_AS_ONE,
        rationale=f"Score: {split_score} split vs {keep_score} keep. Manageable scope.",
        criteria=criteria,
        split_score=split_score,
        keep_score=keep_score,
    )


def _evaluate_from_llm(
    role: AgentRole,
    owns: list[ActivityClassification],
    criteria_results: list[dict[str, str]],
) -> SplitEvaluation:
    """Evaluation using LLM-provided criteria analysis."""
    criteria = []
    split_score = 0
    keep_score = 0

    for cr in criteria_results:
        rec = cr.get("recommendation", "KEEP").upper()
        criterion = SplitCriterion(
            name=cr.get("name", "unknown"),
            recommendation=rec,
            rationale=cr.get("rationale", ""),
        )
        criteria.append(criterion)
        if rec == "SPLIT":
            split_score += 1
        else:
            keep_score += 1

    if split_score > keep_score:
        return SplitEvaluation(
            decision=SplitDecision.SPLIT_INTO_SUBAGENTS,
            rationale=f"Score: {split_score}/{split_score + keep_score} criteria recommend split",
            criteria=criteria,
            split_score=split_score,
            keep_score=keep_score,
            proposed_subagents=_propose_subagents(role, owns),
        )

    return SplitEvaluation(
        decision=SplitDecision.KEEP_AS_ONE,
        rationale=f"Score: {keep_score}/{split_score + keep_score} criteria recommend keeping together",
        criteria=criteria,
        split_score=split_score,
        keep_score=keep_score,
    )


def _propose_subagents(
    role: AgentRole,
    owns: list[ActivityClassification],
) -> list[dict[str, str]]:
    """Propose sub-agent split based on OWNS activities."""
    return [
        {
            "name": f"{role.role_id}_{o.activity_id.replace('.', '_')}",
            "activity": o.activity_id,
            "activity_name": o.activity_name,
        }
        for o in owns
    ]


SPLITTING_CRITERIA_NAMES = [
    "context_boundaries",
    "tool_permissions",
    "independent_verification",
    "parallelism_value",
    "development_test_ease",
    "task_count",
    "team_scaling",
]

SPLITTING_CRITERIA_PROMPTS = {
    "context_boundaries": "Do all OWNS activities share ~80% of context (repo, standards, domain)? If different contexts → SPLIT.",
    "tool_permissions": "Can one service account handle all responsibilities? If different tool profiles → SPLIT.",
    "independent_verification": "Are author/reviewer separation and gatekeeping needed? If different review processes → SPLIT.",
    "parallelism_value": "Can/should responsibilities run in parallel? If yes → SPLIT (weak signal).",
    "development_test_ease": "Can each sub-agent be tested in isolation? If large scope benefits from isolation → SPLIT.",
    "task_count": "How many core responsibilities? If >8 → SPLIT (strong signal).",
    "team_scaling": "Can splitting enable parallel development across multiple engineers? If yes → SPLIT (strong signal).",
}
