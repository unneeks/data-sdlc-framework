"""
In-process asyncio event bus used by the harness loop and the Orchestrator.

Isolation is enforced structurally, not by a runtime permission check:
regular agent loops are only ever given the `publish` bound method (a plain
closure), never this object itself. Only `harness/orchestrator.py` is
constructed with a full `EventBus` instance, so it is the only code with
`subscribe_all` / `resolve_callback` in scope.
"""
from __future__ import annotations

import asyncio
from typing import AsyncIterator, Dict, List

from domain.orchestration import AgentEvent


class EventBus:
    def __init__(self) -> None:
        self._topic_subscribers: Dict[str, List[asyncio.Queue]] = {}
        self._all_subscribers: List[asyncio.Queue] = []
        self._callback_futures: Dict[str, asyncio.Future] = {}

    async def publish(self, event: AgentEvent) -> None:
        for queue in self._topic_subscribers.get(event.event_type, []):
            queue.put_nowait(event)
        for queue in self._all_subscribers:
            queue.put_nowait(event)

    async def subscribe(self, event_type: str) -> AsyncIterator[AgentEvent]:
        queue: asyncio.Queue = asyncio.Queue()
        self._topic_subscribers.setdefault(event_type, []).append(queue)
        while True:
            yield await queue.get()

    async def subscribe_all(self) -> AsyncIterator[AgentEvent]:
        queue: asyncio.Queue = asyncio.Queue()
        self._all_subscribers.append(queue)
        while True:
            yield await queue.get()

    def wait_for(self, step_id: str) -> asyncio.Future:
        """Return a future that resolves when `resolve_callback` is called for this step_id."""
        future = self._callback_futures.get(step_id)
        if future is None:
            future = asyncio.get_event_loop().create_future()
            self._callback_futures[step_id] = future
        return future

    async def resolve_callback(self, step_id: str, event: AgentEvent) -> bool:
        """Called by the /api/harness/callback handler to unblock a waiting agent loop.

        Returns False if no loop is currently awaiting this step_id (stray/replayed callback).
        """
        future = self._callback_futures.pop(step_id, None)
        if future is None or future.done():
            return False
        future.set_result(event)
        await self.publish(event)
        return True
