from __future__ import annotations

import asyncio
import json
from collections.abc import Callable

from agent_framework import ChatResponse, Message


class FakeClient:
    """Chat client stand-in: `handler(payload)` gets the JSON the agent sent and returns the model's answer
    (a dict, a string, or an Exception to raise). Records every payload in `calls`."""

    additional_properties: dict = {}

    def __init__(self, handler: Callable[[dict], object], delay: float | Callable[[dict], float] = 0.0) -> None:
        self.handler = handler
        self.delay = delay
        self.calls: list[dict] = []

    def get_response(self, messages, *, stream=False, options=None, **kwargs):
        async def run():
            payload = json.loads(messages[-1].text)
            self.calls.append(payload)
            wait = self.delay(payload) if callable(self.delay) else self.delay
            if wait:
                await asyncio.sleep(wait)
            answer = self.handler(payload)
            if isinstance(answer, Exception):
                raise answer
            text = answer if isinstance(answer, str) else json.dumps(answer, ensure_ascii=False)
            return ChatResponse(messages=[Message("assistant", [text])])

        return run()


def explain_all(payload: dict, text: str = "Starts often.") -> dict:
    return {"explanations": [{"id": p["id"], "text": text} for p in payload["players"]]}
