# ADR 0001: AgentCore Harness Over Runtime for Agent Execution

## Status

Accepted

## Date

2026-08-30

## Context

Amazon Bedrock AgentCore offers two deployment models for running agents:

1. **AgentCore Runtime** -- package agent code (Strands, LangGraph, CrewAI, etc.) into a container, upload to S3/ECR, deploy to a managed runtime endpoint. The runtime hosts your code, scales it, and exposes an HTTP endpoint. You own the orchestration loop.

2. **AgentCore Harness** -- a serverless, stateless API where you send a system prompt, tool definitions, and messages. The service runs the model + tool loop for you. Your code only implements the tools and bridges tool calls back to local functions.

The Data SDLC Framework needs to execute five metamodel agents (impact analysis, regression, data quality, data model composition, delivery compliance). Each agent's logic is a chain of deterministic skills (repository discovery, dependency analysis, etc.) orchestrated by an LLM that decides which skills to call and how to interpret their output.

## Decision

Use AgentCore Harness as the execution model for all five agents.

## Consequences

### Positive

- **No container packaging or deployment pipeline.** Each agent is defined as a system prompt + tool list + model ID. Provisioning is a single `create_harness` API call per agent (see `setup_agentcore.py`). No S3 buckets, ECR repos, or Dockerfiles needed.
- **Tool bridging keeps skills local.** The Harness calls tools by name; our runner (`agents/runner.py`) intercepts those calls and dispatches them to local Python skill implementations. This means skills can read the local filesystem, access test-data corpora, and run without network round-trips to external services.
- **Rapid iteration.** Changing an agent's system prompt, tool set, or model requires no redeployment. The Harness accepts these parameters per-invocation.
- **DEMO mode falls out naturally.** Because skills are local functions, we can bypass the Harness entirely and call the skill chain directly. This gives us a deterministic, LLM-free execution path for testing and offline demos.
- **Lower blast radius.** No long-running infrastructure to manage, monitor, or pay for when idle.

### Negative

- **No custom orchestration logic.** The Harness owns the model-tool loop. We cannot inject custom routing, caching, or retry logic between turns (beyond the 20-turn cap in our runner).
- **Stateless between invocations.** Each Harness call starts fresh. Session continuity (if needed) must be managed client-side.
- **Latency per turn.** Each tool call requires a round-trip: Harness streams the model response, our runner executes the tool locally, then sends the result back. For agents with 4-6 tool calls this is acceptable; for deep chains it could add up.
- **Vendor coupling.** The Harness API is specific to Amazon Bedrock AgentCore. Migrating to another provider would require rewriting the runner's `_run_harness` method, though the skill implementations are provider-agnostic.

## Alternatives Considered

- **AgentCore Runtime** -- rejected because it requires container packaging, S3 upload, and a deploy/wait/poll cycle per agent. The overhead is disproportionate for agents whose tools are local Python functions.
- **Direct Bedrock Converse API** -- rejected because we would have to implement the full tool-use loop ourselves (message assembly, stop-reason handling, multi-turn state). The Harness provides this out of the box.
- **Strands Agents SDK** -- considered for its built-in tool management and agent lifecycle. Rejected because it introduces a framework dependency and its own orchestration opinions, while the Harness pattern keeps the boundary between LLM orchestration and deterministic skills cleanest.
