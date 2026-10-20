from __future__ import annotations

import asyncio
import copy
import json

import httpx
import pytest
from mcp.server.fastmcp.exceptions import ToolError

from lineup_oracle.api import create_app
from lineup_oracle.events import generate_fixtures, generate_match_events
from lineup_oracle.mcp_server import _default_client, create_server
from lineup_oracle.roster import CLUB_NAMES, generate_synthetic_roster
from lineup_oracle.state import State

ROSTER = generate_synthetic_roster(42)
EVENTS = generate_match_events(ROSTER, generate_fixtures(CLUB_NAMES), seed=42)


def _server():
    app = create_app(State(ROSTER, copy.deepcopy(EVENTS)))
    return create_server(lambda: httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://api"))


def _data(result):
    """call_tool returns content, or (content, structured) where a list result is wrapped as {"result": ...}."""
    if isinstance(result, tuple):
        structured = result[1]
        return structured.get("result", structured)
    return json.loads(result[0].text)


def test_exactly_four_tools_with_descriptions():
    tools = asyncio.run(_server().list_tools())
    assert sorted(t.name for t in tools) == ["get_match_xi", "list_matches", "predict_lineup", "submit_team_news"]
    assert all(t.description for t in tools)


def test_tools_forward_and_flow_through_mcp():
    async def run():
        server = _server()
        matches = _data(await server.call_tool("list_matches", {}))
        match = next(m for m in matches if m["matchday"] == 4)
        args = {"match_id": match["match_id"], "club": match["home_club"]}
        xi = _data(await server.call_tool("get_match_xi", {"match_id": match["match_id"]}))
        assert len(xi["clubs"][0]["players"]) == 11
        before = _data(await server.call_tool("predict_lineup", args))
        starter = before["players"][3]["id"]
        news = _data(await server.call_tool("submit_team_news", {**args, "player_id": starter, "kind": "injury"}))
        after = _data(await server.call_tool("predict_lineup", args))
        assert news == after
        assert starter not in {p["id"] for p in after["players"]}

    asyncio.run(run())


def test_api_errors_become_tool_errors():
    async def run():
        with pytest.raises(ToolError, match="Unknown match"):
            await _server().call_tool("get_match_xi", {"match_id": "nope"})

    asyncio.run(run())


def test_api_url_from_environment(monkeypatch):
    monkeypatch.setenv("LINEUP_API_URL", "http://example.test:9")
    assert str(_default_client().base_url) == "http://example.test:9"
    monkeypatch.delenv("LINEUP_API_URL")
    assert str(_default_client().base_url) == "http://127.0.0.1:8000"
