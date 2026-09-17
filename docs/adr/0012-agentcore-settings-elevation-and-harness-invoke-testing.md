# ADR 0012: Elevate AgentCore Connection Settings App-Wide + Harness Invoke / Local-Callback Testing + Live Status Bar

## Status

Accepted

## Date

2026-09-17

## Context

ADR 0009's AgentCore Connection Tester resolved `ConnectionSettings` (`credentials_path`, `profile`, `region`, `project`) and exposed `build_session(settings)`, but nothing else in the app used it: 5 real call sites (`harness/live_session.py`, `agents/runner.py`, `harness/metrics.py`'s two functions, `harness/adapters/agentcore_adapter.py`) each built their own `boto3.client(...)` independently, three of them ignoring the tester entirely — `agents/runner.py` even hardcoded `region = "us-west-2"` as a bare literal, worse than the others. The user proved out working values against a real AWS account (`~/.aws/credentials`, profile `default`, region `ap-southeast-2`) and asked for three things: these become the new defaults; the settings stop being a page-local diagnostic and become the single source every AgentCore-calling path defers to, including the app's top status bar (which should show real connectivity and turn red on failure); and the Connection Tester page itself grows two new interactive tests — invoking a selected harness with a prompt and watching it stream, and a "local callback" test proving the client-tool-call pause/resume bridge (ADR 0006) round-trips end to end.

## Decision

**New defaults.** `_DEFAULT_REGION` becomes `"ap-southeast-2"`; two new constants, `_DEFAULT_CREDENTIALS_PATH = "~/.aws/credentials"` and `_DEFAULT_PROFILE = "default"`, feed both `ConnectionSettings`' dataclass field defaults and `load_settings()`'s lowest fallback tier (below saved settings and recognized env vars, per ADR 0009's existing precedence).

**Elevation via `build_boto3_client()`, not a module rename.** Added to `harness/connection_tester.py` — ADR 0009 itself predicted this ("any future feature needing a non-default AWS session can call `build_session(settings)` directly"). A literal rename to something like `agentcore_settings.py` was considered and declined: the module's exports already serve this role, and renaming would only add churn to every new call site without changing behavior. `build_boto3_client(service_name, default_region=None, **client_kwargs)` calls a new `_explicit_overrides()` helper that returns only the tiers a human or a recognized env var actually set — **never** the hardcoded-default tier. This distinction matters because the new defaults mean `load_settings()` now *always* returns a concrete, non-empty value for every field; naively wiring every call site straight to `load_settings()` would silently change everyone's default region the moment this ADR shipped, even on a machine that never touched the Connection Tester. `_explicit_overrides()` stops one tier short of that, so nothing changes until a user actually saves settings or sets a recognized env var — verified directly in `tests/test_connection_tester.py` (unconfigured → plain `boto3.client` + the caller's own `default_region`; an explicit saved region overrides it; an explicit saved `credentials_path` routes through `build_session()`).

All 5 call sites now call `build_boto3_client(..., default_region=<their own existing fallback>)`, preserving today's behavior when unconfigured. `agents/runner.py`'s `_run_harness` additionally now reads its `default_region` from `harness.metrics.get_agentcore_runtime_info(agent_key)` — the deployed harness's own configured region — instead of a hardcoded literal, bringing it in line with `harness/live_session.py`'s already-correct pattern. `apps/api/main.py`'s `invoke_agentcore()`/`_runtime_config` path (driven by a separate `runtime_config.json`, not `agentcore_config.json`) is confirmed unused by the current frontend and deliberately left untouched — a documented non-goal, not an oversight.

**Top status bar reflects real connectivity.** A new `_agentcore_connectivity_snapshot()` in `apps/api/main.py` reuses `load_settings()`/`run_connection_test()` — the exact settings/test the Connection Tester page itself uses. In DEMO mode it reports `checked: false` (no AWS call made — DEMO doesn't need one). In REAL mode it actually runs the test and reports `reachable`/`reason`. Both `GET /api/status` (polled once on app mount) and `POST /api/harness/mode` (the toggle) now return this snapshot, so flipping to REAL gets a real answer in the same round trip rather than a second fetch. The frontend banner (`App.tsx`) becomes a three-way state: DEMO stays amber; REAL with `reachable !== false` stays emerald but now shows the settings' region in its text; REAL with `reachable === false` turns a new rose/red state naming the failure reason, with the toggle button still available to bail back to DEMO.

**"Invoke Harness" and "Test Local Callback" need zero new backend endpoints.** The existing Live Agent Orchestrator (`apps/api/live_routes.py` + `harness/live_session.py`) already implements everything both need: `GET /api/live/agents` for the harness dropdown (filtered client-side to `backend === 'AGENTCORE'`), `POST /api/live/session/start` to invoke, `GET /api/live/session/{id}/poll` for this codebase's established poll-based "streaming" (~700ms, matching `AgentOrchestratorWorkflow.tsx` — no true SSE/websocket exists anywhere in this app), and the `CLIENT_TOOL_CALL_REQUESTED`/`CLIENT_TOOL_CALL_RESOLVED` bridge for pending tool calls. `formatLog()` was exported from `AgentOrchestratorWorkflow.tsx` (zero behavior change) and reused rather than duplicating its event-label switch statement.

"Test Local Callback" sends a fixed engineered prompt instructing the harness to call the existing `client_git_status` client tool (already in `CLIENT_TOOL_NAMES`, already the DEMO-mode smoke-test tool) — this is "the json message with structure implemented in earlier iteration" the request referred to: the `ClientToolCallRequest`/`CLIENT_TOOL_CALL_REQUESTED` envelope from ADR 0006. On receipt, a new popup shows "Tool call message received" and — per the user's explicit choice — **immediately auto-approves and executes** the call, then updates the same popup with the result, proving the whole round trip in one click with no dangling pending state. No existing popup/modal pattern existed anywhere in this codebase; `ToolCallPopup` is a new small local component.

**"Invoke Harness" deliberately does *not* auto-approve.** Discovered during manual verification: some DEMO-scripted harnesses (unrelated to the local-callback test's specific prompt) also request a client tool call as part of their own scripted flow — without any way to resolve it, the session simply hangs forever. "Invoke Harness" is a general-purpose "send any prompt to any harness" console, not a pre-vetted single-purpose test, so blanket auto-approval there would execute an arbitrary tool call without operator review. Instead it gained the same inline Approve/Deny card pattern `AgentOrchestratorWorkflow.tsx` already established, reusing `approveClientToolCall`/`denyClientToolCall` directly.

## Consequences

### Positive
- Every real AgentCore-calling code path now defers to one configurable settings source instead of five independent, partially-hardcoded ones.
- The top bar tells the truth about connectivity instead of assuming REAL mode means reachable.
- Both new interactive tests work fully in DEMO mode with zero AWS setup, and reuse (rather than duplicate) the Live Agent Orchestrator's session/streaming/tool-call machinery.

### Negative / non-goals
- `apps/api/main.py`'s legacy `invoke_agentcore()` path is untouched — still using its own separate `runtime_config.json`, unrelated to this settings source.
- The status bar's connectivity check runs a real STS + AgentCore call on every mount/toggle in REAL mode — no caching/interval was added; acceptable given the Connection Tester page already does the same on its own mount, but a future optimization if this proves slow.
- "Invoke Harness"'s manual approve/deny (vs. "Test Local Callback"'s auto-approve) is an intentional asymmetry, not an inconsistency — the two features have different risk profiles (arbitrary prompt vs. one pre-vetted read-only tool).

## Alternatives Considered

- **Renaming `connection_tester.py` to `agentcore_settings.py`** — declined as unnecessary churn; see Decision above.
- **Wiring every call site straight to `load_settings()`** — rejected: would silently change default region/credentials app-wide the moment new defaults shipped, even for users who never opened the Connection Tester. `_explicit_overrides()` avoids this.
- **Auto-approving client tool calls in "Invoke Harness" too** — rejected after the DEMO-hang discovery above; manual approve/deny matches this feature's general-purpose, arbitrary-prompt nature.
