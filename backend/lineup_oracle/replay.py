from __future__ import annotations

import asyncio
import heapq
from collections.abc import Iterable
from typing import Any


class ReplaySession:
    def __init__(self, events: list[dict[str, Any]], speed: float = 1.0) -> None:
        self._next_sequence = 0
        self._events: list[tuple[float, int, dict[str, Any]]] = []
        for item in sorted(events, key=lambda item: (float(item.get("minute", 0.0)), str(item.get("id", "")))):
            self._push(item)
        self._speed = max(speed, 0.0)
        self._subscribers: list[asyncio.Queue[dict[str, Any]]] = []

    def _push(self, event: dict[str, Any]) -> None:
        heapq.heappush(self._events, (float(event.get("minute", 0.0)), self._next_sequence, event))
        self._next_sequence += 1

    @property
    def speed(self) -> float:
        return self._speed

    async def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._subscribers.append(queue)
        return queue

    async def inject(self, event: dict[str, Any]) -> None:
        self._push(event)

    async def run(self, *, speed: float | None = None) -> list[dict[str, Any]]:
        effective_speed = self._speed if speed is None else max(speed, 0.0)
        emitted: list[dict[str, Any]] = []
        last: float | None = None
        while self._events:
            await asyncio.sleep(0)
            scheduled_for, _, item = heapq.heappop(self._events)
            if effective_speed > 0 and last is not None:
                wait = max(0.0, (scheduled_for - last) / effective_speed)
                if wait > 0:
                    await asyncio.sleep(wait)
            last = scheduled_for
            emitted.append(item)
            for queue in self._subscribers:
                await queue.put(item)
        return emitted


async def replay(events: Iterable[dict[str, Any]], speed: float = 1.0) -> list[dict[str, Any]]:
    session = ReplaySession(list(events), speed=speed)
    return await session.run()


async def replay_all_subscribers(events: Iterable[dict[str, Any]], speed: float = 1.0) -> tuple[list[asyncio.Queue[dict[str, Any]]], list[dict[str, Any]]]:
    session = ReplaySession(list(events), speed=speed)
    subscribers = [await session.subscribe() for _ in range(2)]
    emitted = await session.run()
    return subscribers, emitted
