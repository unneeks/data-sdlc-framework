# ADR 0003: Dual Mode -- DEMO and REAL Execution

## Status

Accepted

## Date

2026-08-30

## Context

The Data SDLC Framework is both a workshop/demo tool and a production-path system. Users need to:

1. **Run the full pipeline without AWS credentials or AgentCore access** -- for local development, demos, testing, and environments where provisioning is not available.
2. **Run the same pipeline through AgentCore Harness** -- for production use where LLM orchestration adds adaptive reasoning, risk synthesis, and natural language explanations.

Both modes must produce the same structured output format so that the API, the workflow runner, the UI, and downstream consumers work identically regardless of mode.

## Decision

Support two execution modes in `AgentRunner`, selectable at construction time:

- **DEMO mode** (default): calls the agent's skill chain directly in a fixed order. No LLM, no AWS API calls. Deterministic and fast.
- **REAL mode**: invokes the AgentCore Harness with the agent's system prompt, tools, and model. The Harness runs the LLM, which calls tools via the runner's bridge. Falls back to DEMO mode if no harness ARN is configured.

The mode is set on the `AgentRunner` instance and affects all agent invocations through it. The API exposes `GET/POST /api/harness/mode` for runtime switching.

## Consequences

### Positive

- **Zero-dependency demo path.** The entire agent pipeline, workflow, and UI work out of the box with `mode=DEMO`. No AWS credentials, no IAM roles, no harness provisioning.
- **Same output contract.** Both modes return the same JSON structure (risk_level, affected_assets, test_results, gate_assessment, etc.). The workflow runner and UI do not branch on mode.
- **Graceful degradation.** REAL mode falls back to DEMO if no harness ARN is found, so the system never hard-fails due to missing infrastructure.
- **Test suite portability.** The 13-group test suite runs identically in both modes, validating the full pipeline without cloud dependencies.

### Negative

- **DEMO output lacks LLM reasoning.** DEMO mode returns structured data from skills but does not include the LLM's risk explanations, prioritization, or cross-cutting synthesis. Users may not realize what they are missing until they switch to REAL mode.
- **Behavioral divergence risk.** The DEMO skill chains are manually coded sequences. If the LLM in REAL mode discovers a better tool ordering or skips a step, DEMO mode will not reflect that. Keeping them in sync is a manual process.
- **Mode confusion.** The API switches mode globally for a single `AgentRunner` instance. Concurrent requests all see the same mode. Per-request mode selection would require a different design.

## Alternatives Considered

- **REAL mode only** -- rejected because it makes the system unusable without AWS access. The workshop context demands a functional offline path.
- **Mock LLM responses** -- rejected because canned responses are brittle, hard to maintain, and give a false impression of LLM behavior. Direct skill execution is honest about what it provides.
- **Separate codepaths per mode** -- rejected in favor of a single `AgentRunner` with an internal branch. This keeps the API layer and workflow runner mode-agnostic.
