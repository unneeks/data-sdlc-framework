# ADR 0006: Live Agent Orchestrator with a Per-Tool-Call Client Bridge

## Status

Accepted

## Date

2026-09-17

## Context

The existing agent surfaces (`agents/runner.py` REAL mode, `agents/sdlc_orchestrator.py`) invoke AWS Bedrock AgentCore Harness and execute every tool call inline, in the same process that talks to the Harness. That process is, by design, running on the operator's own machine (see `harness/config.py`: "No credentials live here... left entirely to boto3's standard resolution chain"), so this has always implicitly meant "tools execute locally."

The new Agent Orchestrator workflow UI needs three things the existing surfaces don't provide:

1. A single UI that can drive **either** an AgentCore Harness agent **or** a GitHub Copilot CLI agent, with a Live/Demo toggle per ADR 0003's dual-mode philosophy.
2. An explicit, visible distinction between "this tool call is answered inline by server-side skills" and "this tool call needs the developer's local filesystem/git state/local test run" — with a human approval step before the latter runs, since these tools are more powerful (shell/test execution) than the read-only repository-corpus skills AgentRunner already exposes.
3. A way for the harness to pause mid-turn, wait for that approval + local execution, and resume the same AgentCore session afterward — without inventing a new communication protocol from scratch.

## Decision

- Model the LLM's request for a local tool call as a strongly-typed Pydantic envelope, `ClientToolCallRequest`/`ClientToolCallResult` (`domain/orchestration.py`), rather than passing the harness's raw `toolUse` JSON block around untyped.
- Reuse the **existing** `EventBus.wait_for(id)` / `resolve_callback(id, event)` primitive (`harness/bus.py`) that `harness/adapters/client_handoff_adapter.py` already uses to pause a whole agent step until `POST /api/harness/callback` resolves it — but apply it **per tool call** instead of per step, via a new `LiveAgentSession` (`harness/live_session.py`). One AgentCore turn loop may need zero, one, or several developer-machine tool calls before it can answer; per-step granularity would be too coarse.
- Advertise every client-side tool to the model in the system prompt at session setup (`LiveAgentSession._build_system_prompt`), naming which tools require local approval, so the model treats a pause as expected rather than as a failure.
- Reuse `agents/runner.py`'s tool_registry.yaml-driven dispatch (via the new public `AgentRunner.execute_tool`) for every tool that isn't tagged client-side, and its Bedrock stream parsing (via the new module-level `parse_harness_stream`), so the live session's wire format for the AgentCore Harness is identical to the one `AgentRunner` REAL mode already uses — this ADR only adds the client-tool bridge and the backend choice on top of that, not a second implementation of the Harness protocol.
- Treat GitHub Copilot CLI agents as a second backend (`AgentBackend.GITHUB_COPILOT`) behind the same `LiveAgentSession.run()` entry point, wrapping the existing `GitHubCopilotCLIAdapter` rather than replacing it. Copilot CLI agents have no tool-use/toolResult protocol of their own, so a Copilot turn always completes in one shot — there is nothing to bridge a client tool call into for that backend today.
- Keep DEMO mode's client-tool pause fully scripted and network-free (an actual local `git status` call, no AWS/network calls) so the pause/approve/resume UX is demonstrable without any AWS setup, consistent with ADR 0003.

## Consequences

### Positive

- **No new pause/resume mechanism.** The tool-call bridge is the same `bus.wait_for`/`resolve_callback` future-based handshake already proven by `test_client_run_step_awaits_callback` in `tests/test_harness.py`, just invoked at a different grain.
- **No duplicated Harness protocol.** `parse_harness_stream` and `AgentRunner.execute_tool` are single-sourced; a future change to AgentCore's streaming format only needs updating in one place.
- **Explicit trust boundary.** The distinction between "runs against the sandboxed repository corpus" (existing skills) and "runs on the operator's real machine" (client tools) is a first-class, typed concept instead of an implicit property of where the process happens to be running.
- **Graceful degradation carries through.** AWS identity and AgentCore CloudWatch metrics (`harness/metrics.py`) fail soft, matching the rest of the app's "REAL mode never hard-fails" convention.

### Negative

- **Per-call approval adds latency.** Every client tool call requires a UI round-trip before the turn can resume; there is no "trust this tool for the rest of the session" mechanism yet.
- **Client tool set is small and curated by necessity.** No arbitrary shell execution is exposed (see `harness/client_tools.py`), which limits what a live agent can ask the developer machine to do without a code change to add a new tool.
- **GitHub Copilot backend cannot use the client-tool bridge.** Because Copilot CLI agents are single-turn, the pause/resume mechanism only applies to the AgentCore backend today.

## Alternatives Considered

- **Browser-executed tools (WebSocket to the browser tab).** Rejected because the web app's backend already runs on the operator's own machine (per `harness/config.py`'s credential model) — the backend process itself *is* "the developer machine," so routing through the browser would add a hop without adding capability.
- **A generic unrestricted "run shell command" tool.** Rejected for the MVP: the blast radius of letting an LLM run arbitrary commands on a real developer machine, even with approval, is large enough to warrant a narrower, purpose-built tool set first.
- **Batching all pending tool calls into a single approval prompt only after the whole turn completes.** Rejected because AgentCore's tool_use turns can (and do) request several tools before ending the turn; approving them individually as they're requested keeps the UI's pending-approval state accurate to what the model actually asked for.
