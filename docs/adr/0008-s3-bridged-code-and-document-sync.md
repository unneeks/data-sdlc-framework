# ADR 0008: S3-Bridged Code/Document Sync Between AgentCore Harness and Orchestrator

## Status

Accepted

## Date

2026-09-17

## Context

The process that bridges AgentCore Harness tool calls to local execution (`agents/runner.py`, `harness/live_session.py`) can run somewhere without outbound network access to `github.com` — the developer's own machine is fine, but a locked-down deployment (VPC endpoint to S3 only, no general internet egress) is not. Without source-control access, an agent has no way to read or write code, or hand a finished document back to a human.

The fix is to route both through S3, which is already reachable: a codebase baseline lives in S3, an agent syncs it into a scratch git workspace, edits and commits there, and pushes the result back. Once pushed, whichever "orchestrator" is watching (the web app backend today; a CLI in future) needs to find out and bring the change into the developer's real local repo — without ever clobbering uncommitted local work — and the same transport should carry a second event, "a document was published," so this becomes a general, reusable messaging capability rather than a one-off hack.

## Decision

**One envelope, closed event-type enum.** `domain/events.py::SdlcEventEnvelope` is the single message shape for every event; only `payload` varies by `event_type` (`domain/events.py::SDLCEventType`, currently `CODE_PUSHED_TO_S3` and `DOCUMENT_PUBLISHED`, additive-only going forward). Kept separate from `domain/orchestration.py::AgentEvent` — that type is an in-process, loosely-typed, ad hoc-string-`event_type` shape for turn-loop visibility (`harness/bus.py`'s asyncio queues); this one must be durably JSON-serializable to S3 and schema-validated on read, which are different concerns.

**S3 as a durable, poll-based event log.** S3 has no true append, so "a stream of events" is one small object per event under a lexicographically sortable key (`harness/s3_event_log.py::build_event_key` — an ISO-8601-basic UTC microsecond timestamp prefix plus a hex suffix of the event id, so `ListObjectsV2` order approximates chronological order across any number of concurrent writers with zero coordination). `SdlcEventPoller` is a **project-wide watcher, independent of any single agent session** — not folded into the existing per-session poll endpoints (`apps/api/live_routes.py`/`dashboard_routes.py`) — because code/document sync isn't scoped to whichever session happens to be open in a browser tab; it watches every session's events.

**Robustness rule: artifact-before-event, cursor-after-handler.** Every write path (`agents/skills/code_sync.py`) uploads the artifact (tarball or document) fully and durably *before* writing the event object that references it, and the event write is always last. `SdlcEventPoller` only advances its local cursor (`harness/s3_event_log.py::_AtomicCursor`, colocated at `<target_repo_root>/.git/agentcore/repo_sync_cursor.json` — deliberately not in S3, since each orchestrator host applies to its own local checkout and needs its own cursor) after a handler returns successfully. A handler exception is retried on the next poll, up to a bounded number of attempts, after which the event is dead-lettered rather than permanently wedging the poller on one poison-pill event.

**Local-branch import, never a working-tree overwrite.** `harness/code_sync_apply.py::apply_code_pushed_to_s3` extracts the incoming tarball into a fresh temp dir, builds a **content-addressed, deterministic commit there** (`git commit-tree` over a fixed tree + fixed author/committer identity and timestamp, rather than `git commit`, so identical content always produces the identical commit sha — this is what makes reprocessing the same event, e.g. after a crash between a handler succeeding and the cursor write persisting, a true git-recognized no-op instead of a redundant new commit), then does `git fetch <temp_dir> HEAD:refs/heads/agentcore/<branch>` against the developer's real repo. This is the actual safety mechanism, not just a convention: `git fetch` only ever writes to `.git/refs` and the object database — there is no code path in it that touches the working tree or the index, verified directly in `tests/test_code_sync_apply.py::test_apply_never_touches_the_working_tree_or_index` against a real repo with staged and untracked changes present. A non-fast-forward is never forced; it retries into a timestamped side branch (`agentcore/<branch>-<epoch>`) and logs a warning, so incoming work is never silently lost or blocked (`test_non_fast_forward_retries_into_a_timestamped_side_branch_instead_of_forcing`).

**Three tools, running in the existing tool-dispatch process, not the developer-machine bridge.** `sync_code_from_s3` / `push_code_to_s3` / `publish_documents` live in `agents/skills/code_sync.py` and are registered as ordinary `agents/tool_registry.yaml` entries — **not** in `harness/client_tools.py`, which is reserved for tools that run on the developer's own machine behind a human-approval bridge (`CLIENT_TOOL_NAMES`). These three run wherever the process bridging every other harness tool call already runs today (`agents/runner.py::AgentRunner._execute_tool_by_name`), which is exactly the "git + S3, no GitHub" environment described above. Because they're ordinary registry tools, `harness/live_session.py::LiveAgentSession._handle_tool_use_turn` needed **zero changes to its turn loop** — anything not in `CLIENT_TOOL_NAMES` already falls through to `self._agent_runner.execute_tool(...)`, and the CLI's `AgentRunner._run_harness` path gets the same tools for free through the same registry.

**Session-scoped scratch workspaces, not `AgentRunner._context`.** `AgentRunner._context` is one dict per `AgentRunner` *instance*, and a single instance is shared across every concurrent `LiveAgentSession` (`apps/api/main.py`'s module-level `agent_runner`). A scratch git workspace keyed there would let two concurrent sessions clobber each other's workspace path. `session_id` is threaded explicitly through `AgentRunner.execute_tool`/`_execute_tool_by_name`'s `context` dict (a required, verified-necessary plumbing change, not an assumption), and `agents/skills/code_sync.py` keeps its own `_SCRATCH_WORKSPACES: dict[session_id, ScratchWorkspace]` registry.

**Exactly three tools — file edits fold into `push_code_to_s3`.** Rather than a fourth low-level `write_file` tool, `push_code_to_s3` takes the full new content of every changed/added file plus a delete list, and does edit + commit + archive + upload + event-emit in one call.

**Configurable bucket, KB-bucket fallback.** `harness/repo_sync_config.py::RepoSyncConfig` resolves the bucket from an env var, then `agentcore_config.json["repo_sync"]["bucket_name"]`, then falls back to the already-provisioned knowledgebase bucket (`agents.conventions.provisioner.find_existing_kb_bucket()`) reused under new prefixes — works out of the box with no extra provisioning, since the harness execution role's S3 policy is already scoped to that bucket's ARN. Reviewing this surfaced a real, pre-existing gap: `setup_agentcore.py`'s `PERMISSIONS_POLICY` had **zero S3 statements** (unlike `agents/conventions/provisioner.py`'s role policy, which already had one) — fixed by adding the equivalent statement there too.

**Bootstrap step.** `sync_code_from_s3` needs a baseline at `{code_prefix}/HEAD/pointer.json` before any session can run, and nothing else in this feature seeds it. `bootstrap_repo_sync.py` (a root-level standalone script, matching `setup_agentcore.py`/`deploy.py`'s existing convention — no `scripts/` directory exists in this repo) archives the developer's current real repo and uploads it once as the initial baseline.

**Agent-facing skill, not just inline system-prompt prose.** `.agentcore/skills/code-sync/skill.md` documents the three tools and the recommended workflow, in the same `skill.md` frontmatter/body convention `agents/conventions/parser.py::parse_skill` already parses for every other skill (verified against its `_extract_tools_from_markdown` regex and the real `impact-scanning` skill for shape). An agent opts in via `skills: [code-sync]` in its `.agent.instructions.md`, exactly like any other skill.

**Web app wiring only, this pass.** `apps/api/main.py`'s startup hook starts one `SdlcEventPoller`; `apps/cli/agent_cli.py` — a separate, fully synchronous legacy REPL that doesn't share `LiveAgentSession`/`EventBus` at all — is left untouched, a clean isolated follow-up.

## Consequences

### Positive

- No parallel tool-dispatch or turn-loop mechanism was built — the three tools are ordinary registry entries, reusing the exact same dispatch path every other skill already uses for both the web app and (for free) the CLI.
- The central safety claim ("never touch the working tree") is verified directly against real git, not just asserted by design — see `tests/test_code_sync_apply.py`.
- Content-addressed, deterministic commits make crash-and-retry redelivery a true no-op rather than a merely-harmless duplicate, closing a gap the initial implementation had (a first pass produced a fresh non-deterministic commit sha on every apply, which `git fetch` correctly treated as a non-fast-forward and routed to an unnecessary side branch on redelivery — fixed via `git commit-tree` over a fixed tree/identity/timestamp).
- Every failure mode (missing baseline, missing prior `sync_code_from_s3` call, path traversal, partial document-upload failure, malformed event object, handler exception, non-fast-forward) returns a clear error or a safe fallback instead of raising past the tool-call boundary or corrupting state — verified in `tests/test_code_sync.py`, `tests/test_s3_event_log.py`, `tests/test_code_sync_apply.py`.

### Negative

- No cross-session conflict handling: two sessions pushing to the same `branch_name` concurrently is last-writer-wins on that branch's `pointer.json`. Acceptable for "one agent editing at a time," not for concurrent collaboration on the same branch.
- Synthetic commit shas in the scratch workspace and in the apply-side extraction never match any real sha in either side's actual history — intentional (a `git archive` tarball carries no commit metadata to replay), but can look like a bug to someone expecting sha continuity.
- Tool calls block the event loop for the duration of their S3 upload/download inside `LiveAgentSession._handle_tool_use_turn` (not wrapped in `asyncio.to_thread`) — consistent with every other existing server-side tool today, not a regression, but worth revisiting if uploads prove slow in practice.
- AWS's own AgentCore Code Interpreter sandbox (`bedrock-agentcore:StartCodeInterpreterSession`/`InvokeCodeInterpreter`, already IAM-permitted in `setup_agentcore.py`'s policy but unused anywhere in this codebase) is a plausible alternative execution site for "the harness's own sandboxed code execution." This ADR deliberately uses the simpler, already-proven "tool bridge executes in our own process" pattern instead.
- CLI wiring is deferred; a developer using only the CLI (no web app running) gets no local branch imports until that follow-up lands.

## Alternatives Considered

- **A single growing NDJSON object as the event log** — rejected: S3 has no true append; concurrent writers would race on a read-modify-write cycle. One object per event under a sortable key needs no coordination between writers.
- **A fourth low-level `write_file`/`run_git` tool** instead of folding edits into `push_code_to_s3` — rejected to keep the tool surface at exactly three and the workflow simple for the agent (sync once, push once or a few times, publish documents once).
- **A parallel client-tool-style bridge** (mirroring `CLIENT_TOOL_NAMES`) for these three tools — rejected once it was confirmed that plain `agents/tool_registry.yaml` registration already routes correctly through the existing non-client-tool path with no turn-loop changes.
- **Raw `git commit` (non-deterministic) for the apply-side synthetic commit** — the initial implementation; replaced with `git commit-tree` over a fixed identity/timestamp after a test caught that redelivery produced an unnecessary side branch instead of a true no-op.
