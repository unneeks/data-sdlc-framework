# ADR 0004: Workflow as Sequential Agent Chain

## Status

Accepted

## Date

2026-08-30

## Context

The Data SDLC process for a change request involves multiple concerns: impact analysis, data quality, data model review, regression testing, and delivery compliance. Each concern maps to a metamodel agent. The question is how to orchestrate these agents into a coherent workflow.

Options considered:
1. **Parallel execution** -- run all agents concurrently, merge results.
2. **Event-driven choreography** -- agents publish events, other agents subscribe and react.
3. **Sequential chain with dependency tracking** -- run agents one at a time in a defined order, passing outputs forward.
4. **LLM-driven meta-orchestration** -- a "supervisor" LLM decides which agent to call next based on accumulated results.

## Decision

Implement the workflow as a sequential chain of 6 agent invocations with explicit dependency tracking (`agents/workflow.py`).

The chain is:

```
1. Discovery & Context Build     (impact-analysis-agent)   -- no dependencies
2. Impact Analysis               (impact-analysis-agent)   -- depends on [1]
3. Data Quality Assessment       (data-quality-agent)       -- depends on [1]
4. Data Model Review             (data-model-composer)      -- depends on [1]
5. Regression Testing            (regression-agent)         -- depends on [2]
6. Delivery Compliance Check     (delivery-compliance-agent)-- depends on [5]
```

Each step:
- Checks that its dependencies are COMPLETED before executing.
- Receives task input augmented with results from prior steps (e.g., delivery compliance receives test evidence and impact results).
- Extracts evidence from its result and appends it to a shared evidence list.
- Reports COMPLETED or FAILED status.

The workflow supports both step-by-step execution (`next_step()`) and autonomous completion (`run_all()`).

## Consequences

### Positive

- **Predictable execution order.** The UI can display a pipeline with clear progression. Users know exactly which step runs next and what it depends on.
- **Evidence accumulation.** Each step adds evidence that downstream steps consume. The delivery compliance agent receives all prior evidence, enabling it to make an informed gate assessment.
- **Debuggable.** When a workflow fails, the step index, agent key, and dependency state are immediately visible. The `/api/workflow/step/{index}` endpoint exposes the full result for any step.
- **Simple state model.** The workflow state is a list of steps with statuses. No event queues, no pub/sub, no distributed state to manage.
- **UI alignment.** The WorkflowSimulation component maps directly to steps: each card shows a step, its status, and its expandable result. The log console traces step execution in real time.

### Negative

- **No parallelism.** Steps 2, 3, and 4 all depend only on step 1 and could theoretically run in parallel. The sequential model serializes them, adding latency. For the current 5-agent setup this is acceptable (each DEMO step completes in under a second; each REAL step takes a few seconds).
- **Fixed topology.** Adding a new agent or changing the order requires modifying `initialize_from_scenario`. There is no declarative workflow definition -- the chain is coded in Python.
- **Single failure mode.** If a step fails, subsequent steps that depend on it cannot proceed. The workflow reports the failure but does not retry or skip.

## Alternatives Considered

- **Parallel execution** -- rejected because later agents (regression, delivery compliance) need outputs from earlier agents (impact analysis, test results). Parallelizing would require a join/barrier mechanism that adds complexity without benefit for the current agent count.
- **Event-driven choreography** -- rejected because it introduces a message bus, subscription management, and eventual consistency. The existing `EventBus` and `Orchestrator` in `harness/` handle real-time UI events; using them for agent orchestration would conflate two concerns.
- **LLM-driven meta-orchestration** -- rejected because it adds an outer LLM call per step transition, increasing cost and latency. The workflow order is domain-determined (you cannot assess delivery compliance before running tests), not dynamically discoverable.
