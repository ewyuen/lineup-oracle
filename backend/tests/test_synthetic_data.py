from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from lineup_oracle.events import (
    generate_fixtures,
    generate_match_events,
    generate_team_news,
)
from lineup_oracle.replay import ReplaySession
from lineup_oracle.roster import CLUB_NAMES, load_roster


ROSTER_PATH = Path(__file__).resolve().parents[1] / "data" / "roster.json"


def test_roster_validation_rejects_bad_data(tmp_path: Path) -> None:
    bad_path = tmp_path / "invalid_roster.json"
    bad_path.write_text(
        json.dumps(
            {
                "clubs": [
                    {
                        "name": "Harbor City",
                        "formation": "4-3-3",
                        "style": "pressing",
                        "players": [
                            {"id": "hc-1", "name": "Ari Ash", "number": 1, "position": "GK"},
                            {"id": "hc-2", "name": "Bren Bale", "number": 1, "position": "DEF"},
                        ],
                    }
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Duplicate shirt number"):
        load_roster(bad_path)

    missing_position = tmp_path / "missing_position.json"
    missing_position.write_text(
        json.dumps(
            {
                "clubs": [
                    {
                        "name": "Northmere",
                        "formation": "4-4-2",
                        "style": "balanced",
                        "players": [
                            {"id": "nm-1", "name": "Cai Morrow", "number": 1, "position": ""},
                        ],
                    }
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Missing position"):
        load_roster(missing_position)

    roster = load_roster(ROSTER_PATH)
    assert len(roster.clubs) == 6
    assert all(len(club.players) >= 20 for club in roster.clubs.values())


def test_fixture_generation_and_seeded_determinism() -> None:
    roster = load_roster(ROSTER_PATH)
    fixtures = generate_fixtures(sorted(roster.clubs.keys()), matchdays=10)

    assert len(fixtures) == 10
    assert all(len(day) == 3 for day in fixtures)
    for day in fixtures:
        clubs = []
        for home, away in day:
            clubs.extend((home, away))
        assert len(clubs) == 6
        assert len(set(clubs)) == 6

    a = generate_match_events(roster, fixtures, seed=42)
    b = generate_match_events(roster, fixtures, seed=42)
    assert a == b

    c = generate_team_news(roster, seed=42)
    d = generate_team_news(roster, seed=42)
    assert c == d


def test_match_metadata_uses_true_xi_without_unavailable_players() -> None:
    roster = load_roster(ROSTER_PATH)
    fixtures = generate_fixtures(sorted(roster.clubs.keys()), matchdays=10)
    events = generate_match_events(roster, fixtures, seed=42)

    metadata_events = [event for event in events if event.type == "match_metadata"]
    assert metadata_events

    for event in metadata_events:
        payload = event.payload
        home_xi = payload["home_xi"]
        away_xi = payload["away_xi"]
        assert len(home_xi) == 11
        assert len(set(home_xi)) == 11
        assert len(away_xi) == 11
        assert len(set(away_xi)) == 11

        home_players = {player.id for player in roster.clubs[payload["home_club"]].players}
        away_players = {player.id for player in roster.clubs[payload["away_club"]].players}
        assert set(home_xi).issubset(home_players)
        assert set(away_xi).issubset(away_players)

        for club_name, club_events in [(payload["home_club"], [e for e in events if e.club == payload["home_club"] and e.type == "team_news"]), (payload["away_club"], [e for e in events if e.club == payload["away_club"] and e.type == "team_news"])]:
            unavailable = {
                player_name for event in club_events for player_name in [event.payload.get("player_name")]
                if player_name is not None
            }
            if unavailable:
                assert not any(
                    roster.clubs[club_name].players_by_id[pid].name in unavailable
                    for pid in payload["home_xi" if club_name == payload["home_club"] else "away_xi"]
                )


def test_team_news_mentions_club_and_player() -> None:
    roster = load_roster(ROSTER_PATH)
    team_news = generate_team_news(roster, seed=42)

    assert len(team_news) == 18
    for event in team_news:
        assert event.type == "team_news"
        assert event.club in CLUB_NAMES
        assert event.player is None
        assert "payload" in event.to_dict()
        text = event.payload["text"]
        assert event.club in text
        assert event.payload["player_name"] in text


def test_plausible_distribution_across_many_matches() -> None:
    roster = load_roster(ROSTER_PATH)
    fixtures = generate_fixtures(sorted(roster.clubs.keys()), matchdays=10)

    totals = {"pass": [], "shot": []}
    for seed in range(100):
        match_events = generate_match_events(roster, fixtures, seed=seed)
        per_team = {}
        for event in match_events:
            if event.type not in {"pass", "shot"}:
                continue
            key = (event.match_id, event.club)
            per_team.setdefault(key, {"pass": 0, "shot": 0})
            per_team[key][event.type] += 1
        totals["pass"].extend(stats["pass"] for stats in per_team.values())
        totals["shot"].extend(stats["shot"] for stats in per_team.values())

    mean_passes = sum(totals["pass"]) / len(totals["pass"])
    mean_shots = sum(totals["shot"]) / len(totals["shot"])
    assert 300 <= mean_passes <= 600
    assert 8 <= mean_shots <= 20


def test_replay_order_instant_delivery_and_injection() -> None:
    async def _run() -> None:
        events = [
            {"id": "e-1", "minute": 10.0, "payload": {"kind": "pass"}},
            {"id": "e-2", "minute": 20.0, "payload": {"kind": "shot"}},
            {"id": "e-3", "minute": 30.0, "payload": {"kind": "tackle"}},
        ]
        session = ReplaySession(events, speed=0)
        queue = await session.subscribe()
        delivered = await session.run()
        assert [e["minute"] for e in delivered] == [10.0, 20.0, 30.0]
        assert [queue.get_nowait()["id"] for _ in range(queue.qsize())] == ["e-1", "e-2", "e-3"]

        injection_session = ReplaySession(
            [
                {"id": "base-1", "minute": 5.0, "payload": {"kind": "pass"}},
                {"id": "base-2", "minute": 40.0, "payload": {"kind": "shot"}},
            ],
            speed=0,
        )
        second_queue = await injection_session.subscribe()
        async def _inject_later() -> None:
            await asyncio.sleep(0)
            await injection_session.inject({"id": "late-injury", "minute": 12.0, "payload": {"kind": "injury"}})

        task = asyncio.create_task(_inject_later())
        delivered_injected = await injection_session.run()
        await task
        assert [event["id"] for event in delivered_injected] == ["base-1", "late-injury", "base-2"]
        assert [second_queue.get_nowait()["id"] for _ in range(second_queue.qsize())] == ["base-1", "late-injury", "base-2"]

    asyncio.run(_run())


def test_replay_under_two_minutes_for_demo_speed() -> None:
    async def _run() -> None:
        session = ReplaySession(
            [
                {"id": f"evt-{minute:02d}", "minute": float(minute), "payload": {"kind": "pass"}}
                for minute in range(0, 91, 1)
            ],
            speed=60.0,
        )
        start = asyncio.get_running_loop().time()
        await session.run()
        elapsed = asyncio.get_running_loop().time() - start
        assert elapsed < 120

    asyncio.run(_run())
