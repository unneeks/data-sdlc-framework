"""LiveAgentSession — the orchestrator behind the Agent Orchestrator workflow UI.

Reuses, rather than reinvents, three patterns already established elsewhere
in this codebase:

  - EventBus / AgentEvent (harness/bus.py, harness/orchestrator.py) for
    publishing everything that happens during a run.
  - The AWAITING_CALLBACK "pause the loop, let an external actor resolve a
    future, then resume" mechanism from harness/adapters/client_handoff_adapter.py
    and bus.wait_for/resolve_callback — applied here per tool call instead of
    per agent step, since one AgentCore turn loop may need zero, one, or
    several developer-machine tool calls before it can answer.
  - agents/runner.py's tool_registry.yaml-driven dispatch (via the new public
    `AgentRunner.execute_tool`) and its Bedrock AgentCore stream parsing (via
    the new module-level `parse_harness_stream`), so server-side tool
    execution and the wire format are identical to the existing AgentRunner
    path — this module only adds the client-tool bridge and backend choice
    on top.

Two backends (domain.orchestration.AgentBackend): AGENTCORE (AWS Bedrock
AgentCore Harness) and GITHUB_COPILOT (GitHub Copilot CLI agents). Two modes:
DEMO (fully scripted, zero network calls, matches harness/adapters/demo_adapter.py's
philosophy) and LIVE (real backend calls, using whatever AWS credentials are
already active on this machine via boto3's default chain — see harness/config.py).
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from domain.orchestration import (
    AgentBackend,
    AgentEvent,
    ClientToolCallRequest,
    ClientToolCallResult,
    ClientToolCallStatus,
)
from harness.bus import EventBus
from harness.client_tools import CLIENT_TOOL_NAMES, build_client_tool_advertisement, dispatch_client_tool

logger = logging.getLogger(__name__)

_MAX_TURNS = 20


class LiveAgentSession:
    def __init__(
        self,
        session_id: str,
        agent_id: str,
        backend: AgentBackend,
        live: bool,
        bus: EventBus,
        agent_runner: Any,
        agent_config: Dict[str, Any],
        github_backend: Any = None,
    ) -> None:
        self.session_id = session_id
        self.agent_id = agent_id
        self.backend = backend
        self.live = live  # False => DEMO: fully scripted, no network calls
        self.status = "RUNNING"
        self.final_text: Optional[str] = None
        self.events: List[dict] = []

        self._bus = bus
        self._agent_runner = agent_runner
        self._agent_config = agent_config
        self._github_backend = github_backend
        self._pending_calls: Dict[str, ClientToolCallRequest] = {}

    # ── event plumbing ──────────────────────────────────────

    def _emit(self, event_type: str, **payload: Any) -> None:
        event = AgentEvent(
            event_type=event_type, source_agent_id=self.agent_id,
            session_id=self.session_id, payload=payload,
        )
        self.events.append(json.loads(event.model_dump_json()))
        asyncio.ensure_future(self._bus.publish(event))

    def pending_calls(self) -> List[dict]:
        return [json.loads(c.model_dump_json()) for c in self._pending_calls.values()]

    # ── entry point ─────────────────────────────────────────

    async def run(self, prompt: str) -> None:
        try:
            if not self.live:
                await self._run_demo(prompt)
            elif self.backend == AgentBackend.GITHUB_COPILOT:
                await self._run_github_copilot(prompt)
            else:
                await self._run_agentcore(prompt)
        except Exception as exc:  # noqa: BLE001 - surface any failure to the UI, never crash the task
            logger.exception("live session %s failed", self.session_id)
            self.status = "FAILED"
            self._emit("SESSION_FAILED", error=str(exc))

    # ── GitHub Copilot backend ──────────────────────────────

    async def _run_github_copilot(self, prompt: str) -> None:
        self._emit("SESSION_STARTED", backend=AgentBackend.GITHUB_COPILOT.value, mode="LIVE")
        result = await asyncio.to_thread(self._github_backend.run_turn, self.agent_id, prompt)
        self.status = result["status"]
        self.final_text = result["text"]
        self._emit("SESSION_RESPONSE", text=result["text"])
        self._emit(
            "SESSION_COMPLETED" if self.status == "COMPLETED" else "SESSION_FAILED",
            text=result["text"],
        )

    # ── AgentCore Harness backend (live) ────────────────────

    async def _run_agentcore(self, prompt: str) -> None:
        import boto3
        from agents.runner import parse_harness_stream

        harness_arn = self._agent_config.get("harness_arn")
        if not harness_arn:
            raise RuntimeError(
                f"No harness ARN configured for {self.agent_id}. "
                f"Run setup_agentcore.py first or check agentcore_config.json."
            )

        region = self._agent_config.get("region", "us-west-2")
        client = boto3.client("bedrock-agentcore", region_name=region)

        system_prompt = self._build_system_prompt()
        harness_tools = list(self._agent_config.get("harness_tools", [])) + build_client_tool_advertisement()

        self._emit("SESSION_STARTED", backend=AgentBackend.AGENTCORE.value, mode="LIVE", harness_arn=harness_arn)

        invoke_kwargs: Dict[str, Any] = {
            "harnessArn": harness_arn,
            "runtimeSessionId": self.session_id,
            "messages": [{"role": "user", "content": [{"text": prompt}]}],
            "model": {"bedrockModelConfig": {"modelId": self._agent_config["bedrock_model_id"]}},
            "systemPrompt": [{"text": system_prompt}],
        }
        if harness_tools:
            invoke_kwargs["tools"] = harness_tools

        for turn in range(_MAX_TURNS):
            response = await asyncio.to_thread(client.invoke_harness, **invoke_kwargs)
            content_blocks, stop_reason = parse_harness_stream(response)

            for block in content_blocks:
                if block.get("type") == "text" and block.get("text", "").strip():
                    self._emit("THINKING", text=block["text"], turn=turn)

            if stop_reason == "end_turn":
                text = " ".join(b.get("text", "") for b in content_blocks if b.get("type") == "text")
                self.final_text = text
                self.status = "COMPLETED"
                self._emit("SESSION_RESPONSE", text=text, turn=turn)
                self._emit("SESSION_COMPLETED", text=text)
                return

            if stop_reason != "tool_use":
                continue

            assistant_content, tool_results = await self._handle_tool_use_turn(content_blocks, turn)

            invoke_kwargs = {
                "harnessArn": harness_arn,
                "runtimeSessionId": self.session_id,
                "messages": [
                    {"role": "assistant", "content": assistant_content},
                    {"role": "user", "content": tool_results},
                ],
                "model": {"bedrockModelConfig": {"modelId": self._agent_config["bedrock_model_id"]}},
            }
            if harness_tools:
                invoke_kwargs["tools"] = harness_tools

        self.status = "FAILED"
        self._emit("SESSION_FAILED", error="Max turns exceeded")

    async def _handle_tool_use_turn(self, content_blocks: List[dict], turn: int) -> tuple[list, list]:
        assistant_content: List[dict] = []
        tool_results: List[dict] = []
        pending_futures: Dict[str, asyncio.Future] = {}

        for block in content_blocks:
            if block.get("type") != "toolUse":
                if block.get("type") == "text" and block.get("text"):
                    assistant_content.append({"text": block["text"]})
                continue

            name = block["name"]
            tool_input = block.get("input", {})
            assistant_content.append(
                {"toolUse": {"toolUseId": block["toolUseId"], "name": name, "input": tool_input}}
            )

            if name in CLIENT_TOOL_NAMES:
                call = ClientToolCallRequest(
                    session_id=self.session_id, turn=turn, tool_name=name, arguments=tool_input,
                )
                self._pending_calls[call.call_id] = call
                self._emit("CLIENT_TOOL_CALL_REQUESTED", **json.loads(call.model_dump_json()))
                pending_futures[block["toolUseId"]] = self._bus.wait_for(call.call_id)
            else:
                self._emit("TOOL_CALL", name=name, input=tool_input)
                result = self._agent_runner.execute_tool(name, tool_input, {})
                self._emit("TOOL_RESULT", name=name, result=_truncate(result))
                tool_results.append({
                    "toolResult": {
                        "toolUseId": block["toolUseId"],
                        "content": [{"text": json.dumps(result, default=str)}],
                        "status": "success",
                    }
                })

        if pending_futures:
            resolved = await asyncio.gather(*pending_futures.values())
            for tool_use_id, event in zip(pending_futures.keys(), resolved):
                output = event.payload.get("output") or {}
                status = "success" if event.payload.get("status") == ClientToolCallStatus.COMPLETED.value else "error"
                if status == "error" and event.payload.get("error"):
                    output = {"error": event.payload["error"]}
                tool_results.append({
                    "toolResult": {
                        "toolUseId": tool_use_id,
                        "content": [{"text": json.dumps(output, default=str)}],
                        "status": status,
                    }
                })

        return assistant_content, tool_results

    # ── resolving a pending client tool call (called from the API layer) ──

    async def resolve_client_tool_call(self, call_id: str, approve: bool) -> ClientToolCallResult:
        """Execute (or deny) a pending client tool call and unblock the
        turn loop that is waiting on it via bus.wait_for(call_id)."""
        call = self._pending_calls.get(call_id)
        if call is None:
            raise KeyError(f"no pending client tool call: {call_id}")

        if not approve:
            result = ClientToolCallResult(call_id=call_id, status=ClientToolCallStatus.DENIED, error="Denied by operator")
        else:
            self._emit("CLIENT_TOOL_CALL_APPROVED", call_id=call_id, tool_name=call.tool_name)
            output = await asyncio.to_thread(dispatch_client_tool, call.tool_name, call.arguments)
            if isinstance(output, dict) and "error" in output:
                result = ClientToolCallResult(call_id=call_id, status=ClientToolCallStatus.FAILED, error=str(output["error"]))
            else:
                result = ClientToolCallResult(call_id=call_id, status=ClientToolCallStatus.COMPLETED, output=output)

        resolved_event = AgentEvent(
            event_type="CLIENT_TOOL_CALL_RESOLVED",
            source_agent_id=self.agent_id,
            session_id=self.session_id,
            payload={
                "call_id": call_id, "tool_name": call.tool_name,
                "status": result.status.value, "output": result.output, "error": result.error,
            },
        )
        self.events.append(json.loads(resolved_event.model_dump_json()))
        resolved = await self._bus.resolve_callback(call_id, resolved_event)
        if not resolved:
            logger.warning("client tool call %s resolved but no loop was waiting on it", call_id)
        self._pending_calls.pop(call_id, None)
        return result

    def _build_system_prompt(self) -> str:
        base = self._agent_config.get("system_prompt") or f"You are the {self.agent_id} agent."
        client_names = ", ".join(sorted(CLIENT_TOOL_NAMES))
        return (
            f"{base}\n\n"
            f"--- Tool execution sites ---\n"
            f"Most of your tools run in this cloud session. The following tools instead run "
            f"on the developer's own local machine and require a human to approve them before "
            f"they execute: {client_names}. When you call one of these, expect a pause before "
            f"the result comes back — that is expected, not an error. Only reach for them when "
            f"the task genuinely needs the developer's local filesystem, git working tree, or a "
            f"local test run that this cloud session cannot see."
        )

    # ── DEMO mode: fully scripted, zero network calls ───────

    async def _run_demo(self, prompt: str) -> None:
        self._emit("SESSION_STARTED", backend=self.backend.value, mode="DEMO")
        self._emit("THINKING", text=f"Reviewing request against {self.agent_id}'s scope of work…")
        await asyncio.sleep(0.05)

        self._emit("TOOL_CALL", name="discover_repository", input={})
        await asyncio.sleep(0.05)
        self._emit("TOOL_RESULT", name="discover_repository", result="[DEMO] 42 files discovered across 6 domains")

        call = ClientToolCallRequest(session_id=self.session_id, turn=1, tool_name="client_git_status", arguments={})
        self._pending_calls[call.call_id] = call
        self._emit("CLIENT_TOOL_CALL_REQUESTED", **json.loads(call.model_dump_json()))

        # resolve_client_tool_call() (invoked by the API layer once the operator
        # approves) publishes the CLIENT_TOOL_CALL_RESOLVED event itself and
        # pops the pending call; this just unblocks once that happens.
        await self._bus.wait_for(call.call_id)

        self._emit("THINKING", text="Incorporating local working-tree state into the recommendation…")
        await asyncio.sleep(0.05)

        text = (
            f"[DEMO] {self.agent_id} completed its review using {call.tool_name} output pulled "
            f"from the developer machine. No blocking findings for: {prompt[:120]}"
        )
        self.final_text = text
        self.status = "COMPLETED"
        self._emit("SESSION_RESPONSE", text=text)
        self._emit("SESSION_COMPLETED", text=text)


def _truncate(result: Any, limit: int = 500) -> str:
    text = json.dumps(result, default=str)
    return text if len(text) <= limit else text[:limit] + "…"
