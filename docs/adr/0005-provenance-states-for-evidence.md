# ADR 0005: Provenance States for Evidence

## Status

Accepted

## Date

2026-08-30

## Context

The Data SDLC Framework produces findings at every stage: impacted assets, test results, quality gaps, gate assessments. These findings inform delivery decisions -- whether a change can proceed through a gate, whether it needs human review, whether it can be cited in regulatory reports.

Not all findings carry equal weight. A file path found by scanning the repository is qualitatively different from a risk level inferred by an LLM, which is different from a test result verified by a human engineer.

Without explicit provenance, all findings appear equally authoritative. This creates two risks:
1. **Over-trust**: an LLM inference is treated as established fact and blocks delivery.
2. **Under-trust**: a directly observed finding is dismissed because "an AI said it."

The metamodel defines a four-state provenance model. The question is whether to enforce it in the agent implementation and what the enforcement rules should be.

## Decision

Every finding produced by an agent or skill carries a `provenance` field set to one of four states, as defined in the metamodel:

| State | Meaning | Confidence | May Block | May Cite as Fact |
|-------|---------|------------|-----------|------------------|
| `OBSERVED` | Read directly from a source artifact | Implied 1.0 | Yes | Yes |
| `INFERRED` | Concluded from evidence, not directly seen | Explicit (0.0-1.0) | No | No |
| `HUMAN_VERIFIED` | A named human checked and signed off | Implied 1.0 | Yes | Yes |
| `CERTIFIED` | Human-verified and passed a governance gate | Implied 1.0 | Yes | Yes |

Enforcement rules implemented:

1. **Skills produce OBSERVED findings.** Repository discovery, dependency analysis, test execution, and data profiling read artifacts directly. Their outputs are tagged `provenance: "OBSERVED"`.

2. **LLM synthesis produces INFERRED findings.** When the Harness LLM interprets skill outputs to assign risk levels, predict transitive impact, or recommend actions, those findings are tagged `provenance: "INFERRED"` with an explicit `confidence` value.

3. **INFERRED findings cannot block delivery.** The delivery compliance agent's gate assessment treats INFERRED blockers as advisory. Only OBSERVED or higher-ranked provenance can produce a BLOCKING severity. This is enforced in `agents/skills/delivery_process.py` and stated in the agent's system prompt constraints.

4. **Evidence validation checks provenance.** The `validate_evidence` skill (`agents/skills/evidence_validation.py`) inspects each evidence item's provenance state and flags items that lack it or carry insufficient provenance for their claimed purpose.

5. **Promotion is explicit.** Moving from INFERRED to HUMAN_VERIFIED requires a human action (not yet implemented in the automated pipeline). Moving from HUMAN_VERIFIED to CERTIFIED requires passing a governance gate.

## Consequences

### Positive

- **No silent authority inflation.** An LLM guess cannot block a release. The system structurally prevents the most dangerous failure mode of AI-assisted delivery.
- **Auditability.** Every finding in the evidence chain has a declared provenance. Regulatory reviewers can filter to OBSERVED + CERTIFIED items and ignore inferences.
- **Calibrated trust.** Consumers of agent output (the UI, the workflow runner, downstream APIs) can filter, sort, and weight findings by provenance. The gate assessment already does this.
- **Extensibility.** The four states are a lattice ordered by `rank` (1-4). Adding intermediate states (e.g., PEER_REVIEWED between OBSERVED and HUMAN_VERIFIED) is straightforward.

### Negative

- **Human verification not yet automated.** The HUMAN_VERIFIED and CERTIFIED states exist in the model but require a human-in-the-loop flow that is not implemented. Currently, the pipeline produces only OBSERVED and INFERRED findings.
- **Confidence calibration is approximate.** INFERRED confidence values are set heuristically by skill implementations (e.g., 0.7 for transitive impact). There is no calibration mechanism to verify these values are accurate.
- **Overhead on every finding.** Every data structure returned by a skill must include provenance metadata. This adds verbosity to JSON responses, though it is essential for the trust model to work.

## Alternatives Considered

- **Binary provenance (automated/human)** -- rejected because it conflates "directly observed by code" with "inferred by LLM." Both are automated, but their reliability differs fundamentally.
- **No provenance tracking** -- rejected because the framework's core value proposition is trustworthy delivery decisions. Without provenance, there is no basis for deciding which findings to act on.
- **Confidence scores only** -- rejected because confidence without provenance state is ambiguous. A 0.95 confidence INFERRED finding and a 0.95 confidence OBSERVED finding have different trustworthiness. Provenance state captures this categorical difference.
