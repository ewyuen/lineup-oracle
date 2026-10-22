from __future__ import annotations

import os
from collections.abc import Callable

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

DEFAULT_API_URL = "http://127.0.0.1:8000"


def _default_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=os.environ.get("LINEUP_API_URL", DEFAULT_API_URL), timeout=30)


def create_server(client_factory: Callable[[], httpx.AsyncClient] = _default_client) -> FastMCP:
    """Thin adapter: every tool is one HTTP call to the API, with no logic of its own."""
    server = FastMCP("lineup-oracle")

    async def call(method: str, path: str, body: dict | None = None):
        async with client_factory() as client:
            try:
                response = await client.request(method, path, json=body)
            except httpx.HTTPError as err:
                raise ToolError(f"Lineup API unreachable: {err}") from err
        if response.is_error:
            try:
                message = response.json()["detail"]
            except (ValueError, KeyError, TypeError):
                message = response.text
            raise ToolError(f"{response.status_code}: {message}")
        return response.json()

    @server.tool()
    async def predict_lineup(match_id: str, club: str, mode: str = "analyst", language: str = "en", session_id: str = "default") -> dict:
        """Predict a club's starting XI for a match: formation, 11 players with p_start and explanation, alternatives."""
        return await call("POST", "/predict_lineup", {"match_id": match_id, "club": club, "mode": mode, "language": language, "session_id": session_id})

    @server.tool()
    async def submit_team_news(
        match_id: str, club: str, player_id: str | None = None, kind: str | None = None, text: str | None = None,
        mode: str = "analyst", language: str = "en", session_id: str = "default",
    ) -> dict:
        """Submit team news and get the lineup: a player id and a kind (injury, suspension or doubt), or a text of at most 100 characters (a status, or a line posted to the shared news; see `news` in the answer)."""
        body = {"match_id": match_id, "club": club, "player_id": player_id, "kind": kind, "text": text, "mode": mode, "language": language, "session_id": session_id}
        return await call("POST", "/team_news", body)

    @server.tool()
    async def list_matches() -> list[dict]:
        """List the season's matches with match id, matchday, home club and away club."""
        return await call("GET", "/matches")

    @server.tool()
    async def get_match_xi(match_id: str) -> dict:
        """Get the actual starting XI and formation of both clubs for a match."""
        return await call("GET", f"/matches/{match_id}/xi")

    @server.tool()
    async def ask_player_history(
        question: str | None = None, player: str | None = None, types: list[str] | None = None,
        start: str | None = None, end: str | None = None, match_id: str | None = None,
    ) -> dict:
        """What happened to a player (shots, tackles, team news, starts), with the events and their ids. Give either a free-text question, or a player (id or exact name) with optional types (shot, tackle, team_news, started), start and end (ISO 8601) and a match id."""
        body: dict = {}
        if question is not None:
            body["question"] = question
        if any(v is not None for v in (player, types, start, end, match_id)):
            body["filters"] = {"player": player, "types": types, "from": start, "to": end, "match": match_id}
        return await call("POST", "/player_history", body)

    return server


if __name__ == "__main__":
    create_server().run()
