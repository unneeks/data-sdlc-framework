# ADR 0007: Project Dashboard — Concurrent Agent Lanes with Work-Product Review Gates

## Status

Accepted

## Date

2026-09-17

## Context

ADR 0006 introduced `LiveAgentSession` and a per-tool-call client bridge for a single-agent console. A second, higher-level workflow UI was requested: a project status dashboard (Data Analyst / Data Engineer / Test Engineer / Release Lead agents running concurrently, producing named work products through Requirements → Design → Build → Test → Release, with a human review gate on selected work products, and live AgentCore cost/token metrics).

This is a different interaction shape from the single-agent console: several agents run **at once**, each producing **several named deliverables** (not one final answer), and the thing a human is asked to approve is a **work product**, not a tool call.

## Decision

- Model each concurrent agent as a `ProjectLane` (`harness/project_dashboard.py`), holding its own work products (`domain/project.py::WorkProduct`, with a `NOT_STARTED → IN_PROGRESS → AWAITING_REVIEW → COMPLETED` lifecycle) and its own activity feed.
- Every LIVE lane runs through the **existing** `LiveAgentSession`, not a bespoke one-shot invocation — this keeps the dashboard's LIVE path exercising the same AgentCore Harness / GitHub Copilot code path, tool dispatch, and client-tool bridge as the single-agent console. A lane maps to a best-effort real agent (`LANE_DEFINITIONS`); a lane whose mapped agent isn't provisioned or reachable fails only that lane (`asyncio.gather` over per-lane coroutines that each catch their own exceptions), never the whole dashboard.
- A work product's human review step reuses the **same** `EventBus.wait_for`/`resolve_callback` pause-resume primitive the client-tool bridge already uses (ADR 0006), keyed as `"{lane_key}:{work_product_key}"` instead of a tool call id. This is the same mechanism at a different grain, not a new one.
- `InvocationMetricsTracker` (`harness/agentcore_invocation_metrics.py`) aggregates real per-turn token usage `LiveAgentSession` now reports (via a new `metadata.usage` extraction in `agents/runner.py::parse_harness_stream`) into per-lane and per-project cost/elapsed/token figures — this is what drives the dashboard's stat tiles for LIVE runs, independent of CloudWatch's multi-minute aggregation delay (CloudWatch, `harness/metrics.py`, remains the ops-level source for account/runtime aggregates).
- DEMO mode is a fully scripted, offline simulation (`ProjectLane._run_demo`) whose lane statuses and pending reviews reproduce the reference screenshot's in-flight snapshot deterministically (fixed per-transition token costs, not random), so the review pause/resume UX is demoable with no AWS access.

### Metamodel/ontology alignment

Reviewing the UI's elements against the existing metamodel (`apps/web/src/data/metamodel.json`) and ontology (`ontology/data-sdlc.{owl,rdfs}`) surfaced that the ontology already modelled everything this dashboard needed — `DeliveryPhase`, `DeliveryArtifact`, `ApprovalGate`, `DeliveryRole`, `Agent`, and the `hasPhase`/`hasArtifact`/`hasGate`/`hasRole` relationships — but `metamodel.json` had **zero data instances** of `DeliveryPhase` or `DeliveryArtifact`, and `test-planner-agent` (already provisioned in `agentcore_config.json` and used by `agents/sdlc_orchestrator.py`) was missing from the `agents` registry the Metamodel/Agent Explorer UIs read from. No ontology schema change was needed — it was a data gap the dashboard was the first feature to actually need filled. Fixed by:

- Populating `delivery_phases` with the canonical 10-phase sequence (Discovery‥Transition to BAU, matching `test-data/docs/01-discovery`‥`10-transition-to-bau`).
- Populating `delivery_artifacts` with the 28 work products `LANE_DEFINITIONS` produces, each linked to its producing agent and phase.
- Adding `artifact_lifecycle_states`, mirroring the existing `provenance_states`/`risk_classes` JSON-layer enum pattern (deliberately *not* an OWL datatype property — the ontology has no precedent for modelling enumerated status as a class/property, only as structural classes and object properties; status enums live in the metamodel JSON layer in this codebase).
- Registering `test-planner-agent`.
- Renaming the dashboard's internal phase keys from `build`/`test` to the canonical `development`/`testing` (the UI labels stay "Build"/"Test", matching the reference screenshot; only the machine-readable key changed) so this data lines up with the rest of the metamodel instead of inventing parallel terminology.

## Consequences

### Positive

- No parallel "mini orchestrator" was built for the dashboard — it is `LiveAgentSession` plus `EventBus` plus a coarser-grained state model on top, same as ADR 0006 predicted this primitive would generalize.
- Per-lane failure isolation means a demo audience sees three lanes succeed and one show a clear AWS error, instead of the whole page breaking.
- The Metamodel/Agent Explorer UIs, which already render any top-level key in `metamodel.json` generically, immediately picked up the new sections and agent with no frontend code change.

### Negative

- `LANE_DEFINITIONS`'s AgentCore/Copilot agent mapping per lane is a best-effort product-persona-to-registered-agent mapping (e.g. "Test Engineer Agent" → `test-planner-agent`), not a formal, enforced one — it lives only in `harness/project_dashboard.py`, not in the metamodel's agent records themselves.
- DEMO mode's per-transition token cost is a fixed placeholder, not derived from anything — it exists purely to make the stat tiles look populated offline, same caveat as `harness/agentcore_invocation_metrics.py`'s pricing constants.

## Alternatives Considered

- **A bespoke one-shot invocation helper for LIVE lanes** instead of reusing `LiveAgentSession` — rejected because it would have duplicated the AgentCore turn loop, tool dispatch, and client-tool bridge a second time for no benefit.
- **Modelling artifact lifecycle status as an OWL datatype property** on `DeliveryArtifact` — rejected because no other enumerated state in this codebase (provenance, risk) is modelled that way in the ontology; keeping the convention consistent (structural ontology, enums in the metamodel JSON layer) was judged more valuable than technically-possible OWL modelling.
