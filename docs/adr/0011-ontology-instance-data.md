# ADR 0011: Populate the Ontology with Real Delivery-Twin Instance Data

## Status

Accepted

## Date

2026-09-17

## Context

`ontology/data-sdlc.owl` and `ontology/data-sdlc.rdfs` define the `DeliveryPhase`/`DeliveryArtifact`/`DeliveryRole` classes and their relationships (`hasArtifact`, `hasPhase`, `hasRole`, etc.), but until this change contained **zero individuals for any of them** — only an abstract TBox (classes and properties) plus a handful of unrelated enum-style `owl:oneOf` collections (risk levels, task statuses, and a `DeliveryPhaseName` enum that names the 10 canonical phases as bare string-like individuals, not full `DeliveryPhase` instances with order/description).

Meanwhile `apps/web/src/data/metamodel.json` already has real instance data for exactly this: 10 `delivery_phases` and 28 `delivery_artifacts` (the same 28 work products `harness/project_dashboard.py`'s `DEFAULT_LANE_DEFINITIONS` produces — its own changelog entry says it was populated *from* that dashboard file). So the "options" the user expects to find (work products like "Infrastructure (Terraform)", "dbt Models", etc.) already existed in the metamodel and in the persisted-project seed (`harness/project_store.py::create_project`, added in ADR 0010) — confirmed by inspection, they were never missing from either. The actual gap was narrower: the ontology files, despite defining the relevant classes, carried no matching instance data at all, so they didn't actually "have" these options as data — only as abstract shapes.

Note: neither `.owl` nor `.rdfs` file is parsed by any application code — `apps/web/src/components/OntologyExplorer.tsx` renders its own independent, hardcoded TypeScript mirror of the class/property schema for the UI, and does not read these XML files. This change is therefore a documentation/data-completeness fix, not a functional/runtime change.

## Decision

Add real named individuals to both ontology files, mirroring `metamodel.json`'s `delivery_phases` and `delivery_artifacts` exactly:

- **10 `DeliveryPhase` individuals** (`discovery` → `transition-to-bau`), each with `identifier`, `name`, `sequence`, `description` — all properties that already existed in the schema with matching domain.
- **4 `DeliveryRole` individuals**, one per dashboard lane (Data Analyst/Data Engineer/Test Engineer/Release Lead Agent), using the existing `identifier`/`name`/`description` properties. These correspond 1:1 to `harness/project_dashboard.py`'s `DEFAULT_LANE_DEFINITIONS` lane keys.
- **28 `DeliveryArtifact` individuals**, one per metamodel work product, using the existing `identifier`/`name`/`artifactType` properties plus two new properties described below.

**Two small, justified schema additions**, since no existing property could carry this data without misrepresenting it:
- `dsdlc:reviewGate` (datatype, boolean, domain `DeliveryArtifact`) — mirrors `review_gate`. No existing boolean property fit (`mandatory`'s domain is `Standard`, a different concept).
- `dsdlc:artifactInPhase` (object property, `DeliveryArtifact` → `DeliveryPhase`) and `dsdlc:producedByRole` (object property, `DeliveryArtifact` → `DeliveryRole`) — mirror `phase_key`/`produced_by_lane`. The existing `hasArtifact` property's domain is `DeliveryTask`, and this app has no `DeliveryTask` individuals at all (there's no per-artifact task-level data anywhere, real or modeled) — inventing 28 placeholder tasks just to satisfy `hasArtifact`'s domain would have fabricated structure the real data doesn't have. A direct `DeliveryArtifact → DeliveryPhase`/`DeliveryRole` property matches what's actually known.

**`artifactType` values were newly assigned** (metamodel.json has no such field) by categorizing each artifact's name into one of the six types the ontology's own `DeliveryArtifact` comment already lists (document, model, code, report, specification, runbook) — e.g. "Infrastructure (Terraform)" → `code`, "Test Execution Report" → `report`, "Runbook" → `runbook`. This is a light, low-stakes categorization with no effect on any running code.

`produced_by_agent` (e.g. `"data-quality-agent"`) was **not** modeled as a new object property to an `Agent` individual — the ontology's `Agent` class has no individuals either, and populating a second unrelated instance set (the full agent registry) was out of scope for this change.

**`tests/test_ontology_delivery_artifacts.py`** parses both XML files and `metamodel.json` and asserts every phase/artifact/role identifier, name, phase assignment, lane assignment, and `review_gate` flag matches exactly across all three — regression protection against future drift, the same concern the metamodel's own changelog entry already flagged for its relationship to `project_dashboard.py`.

## Consequences

### Positive

- The ontology genuinely contains the same "options" (work products, phases, roles) the rest of the app already uses, instead of only describing their shape abstractly.
- A single automated test (`test_ontology_delivery_artifacts.py`) now catches drift between `metamodel.json`, `project_dashboard.py`'s `DEFAULT_LANE_DEFINITIONS`, and both ontology files, closing a three-way consistency gap that previously had no check at all.

### Negative / Explicit non-goals

- **This does not make work products vary by delivery type.** All 28 artifacts still apply identically to every project regardless of its `delivery_type_id`, exactly as ADR 0010 already flagged as a deferred v2 follow-up — this change only populates instance data for the existing, delivery-type-agnostic set. A user-facing evaluation of this exact option (delivery-type-specific filtering) was deliberately deferred again in favor of this bounded, mechanical change.
- The ontology files remain unconsumed by any code — this is a documentation improvement, not new application behavior. A future step (out of scope here) could have `OntologyExplorer.tsx` actually parse and render these individuals instead of maintaining its own separate hardcoded class list.
- `artifactType` categorizations are a best-effort, one-time judgment call, not derived from any authoritative source.

## Alternatives Considered

- **Modeling `DeliveryTask` individuals to satisfy `hasArtifact`'s existing domain** — rejected: this app has no per-artifact task-level granularity anywhere in its real data; inventing 28 tasks purely to satisfy a property's stated domain would add fictitious structure rather than real instance data.
- **Modeling `produced_by_agent` via new `Agent` individuals** — deferred: doing this properly means populating the full agent registry from `metamodel.json`'s `agents` section, a materially larger, separate piece of work with its own judgment calls (agent IDs referenced by `marketplace/delivery_types.json`'s `default_agents` don't even match the registered agent namespace — a pre-existing data-quality gap noted in passing, not fixed here).
- **Filtering artifacts by delivery type at the same time** — considered and explicitly declined per the user's own choice between the two options; kept as ADR 0010's still-open follow-up.
