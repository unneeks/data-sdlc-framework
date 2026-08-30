# ADR 0002: Deterministic Skills with LLM Orchestration

## Status

Accepted

## Date

2026-08-30

## Context

Each metamodel agent performs a sequence of operations: scan a repository, build a dependency graph, trace impact, select tests, execute them, and so on. These operations can be implemented as:

1. **Fully LLM-driven** -- the model reads files, parses SQL, builds graphs, and reasons about impact in a single prompt chain. No separate tool functions.
2. **Fully deterministic** -- a hardcoded pipeline of function calls with no LLM involvement.
3. **Hybrid** -- deterministic functions (skills) for the mechanical work, with an LLM deciding which skills to invoke and how to synthesize their outputs.

The metamodel itself declares 14 skills with explicit dependency chains (e.g., `impact-analysis` depends on `dependency-analysis` which depends on `repository-discovery`). Each skill has a `deterministic` flag and `risk_level`.

## Decision

Implement tools as deterministic Python functions. Delegate orchestration (which tools to call, in what order, and how to interpret results) to the LLM via the AgentCore Harness.

Specifically:
- Each tool in `agents/tools/definitions.py` is backed by a pure Python function in `agents/skills/`.
- Skills perform mechanical work: walk file trees, parse imports, build graphs, match patterns, compute coverage. They produce structured JSON, not prose.
- The LLM (via Harness) reads the tool outputs and decides the next action. It synthesizes findings, assigns risk levels, and generates human-readable summaries.
- In DEMO mode, the skill chain is called directly in a fixed order, proving the skills produce correct output without LLM involvement.

## Consequences

### Positive

- **Reproducibility.** Given the same repository state, a skill always returns the same output. This makes testing straightforward -- the DEMO mode skill chain is fully deterministic and can be validated without API calls or LLM variability.
- **Debuggability.** When an agent produces unexpected results, you can isolate whether the problem is in a skill's output or in the LLM's interpretation. Run the skill directly, inspect its JSON, and compare.
- **Testability.** Skills can be unit-tested independently. The 13-group test suite (`test_workflow.sh`) exercises skills via API endpoints without requiring LLM access.
- **Cost control.** LLM tokens are spent on orchestration decisions and synthesis, not on parsing SQL or walking file trees. The expensive operations are mechanical and run locally.
- **Provenance clarity.** Skill outputs carry `provenance: "OBSERVED"` because they are derived from direct inspection of artifacts. LLM synthesis carries `provenance: "INFERRED"`. This separation is enforced by the architecture, not by convention.

### Negative

- **Rigid skill boundaries.** A skill must have a well-defined input/output contract. Ad-hoc analysis that does not fit an existing skill requires adding a new one.
- **LLM still needed for synthesis.** The DEMO mode produces raw structured data but lacks the LLM's ability to prioritize findings, explain risk in context, or adapt language to the audience. DEMO and REAL outputs are structurally equivalent but differ in interpretive depth.
- **Dual maintenance.** The DEMO mode skill chains in `agents/runner.py` must mirror the tool sequences the LLM would naturally choose. If the LLM discovers a better ordering, the DEMO chains must be updated manually.

## Alternatives Considered

- **Fully LLM-driven tools** -- rejected because LLM output for mechanical tasks (file tree walking, import parsing, graph traversal) is nondeterministic, slower, and harder to validate. It also consumes significantly more tokens.
- **Fully deterministic pipeline** -- rejected because the value of agents lies in adaptive orchestration: the LLM can skip unnecessary steps, ask for more detail on risky areas, and synthesize cross-cutting findings that a fixed pipeline cannot.
