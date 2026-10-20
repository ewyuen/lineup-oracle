from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

import lineup_oracle.replay as replay_module
from lineup_oracle.events import (
    generate_fixtures,
    generate_match_events,
)
from lineup_oracle.replay import ReplaySession, replay_all_subscribers
from lineup_oracle.roster import CLUB_NAMES, generate_synthetic_roster, load_roster, write_roster


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

    c = [e for e in a if e.type == "team_news"]
    d = [e for e in b if e.type == "team_news"]
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

        assert payload["schema_version"] == 1
        players_by_id = {
            player.id: player
            for player in roster.clubs[payload["home_club"]].players + roster.clubs[payload["away_club"]].players
        }
        news = [e for e in events if e.match_id == event.match_id and e.type == "team_news"]
        assert len(news) == 6
        unavailable_names = {e.payload["player_name"] for e in news if e.payload["kind"] in {"injury", "suspension"}}
        xi_names = {players_by_id[pid].name for pid in home_xi + away_xi}
        assert not (xi_names & unavailable_names)


def test_team_news_mentions_club_and_player() -> None:
    roster = load_roster(ROSTER_PATH)
    fixtures = generate_fixtures(sorted(roster.clubs.keys()), matchdays=10)
    team_news = [e for e in generate_match_events(roster, fixtures, seed=42) if e.type == "team_news"]

    assert len(team_news) == 30 * 6
    assert team_news == [e for e in generate_match_events(roster, fixtures, seed=42) if e.type == "team_news"]
    for event in team_news:
        assert event.club in CLUB_NAMES
        assert event.player is None
        assert event.payload["kind"] in {"injury", "suspension", "doubt"}
        text = event.payload["text"]
        assert event.club in text
        assert event.payload["player_name"] in text


def test_event_schema_fields() -> None:
    roster = load_roster(ROSTER_PATH)
    fixtures = generate_fixtures(sorted(roster.clubs.keys()), matchdays=10)
    for event in generate_match_events(roster, fixtures, seed=42):
        data = event.to_dict()
        assert set(data) == {"id", "match_id", "type", "minute", "club", "player", "payload", "simulated"}
        assert isinstance(data["minute"], float)
        assert data["simulated"] is True


def test_committed_roster_is_reproducible(tmp_path: Path) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    write_roster(first, generate_synthetic_roster(seed=42))
    write_roster(second, generate_synthetic_roster(seed=42))
    assert first.read_bytes() == second.read_bytes()
    assert first.read_bytes() == ROSTER_PATH.read_bytes()


def test_xi_follows_club_formation_and_all_event_types_appear() -> None:
    roster = load_roster(ROSTER_PATH)
    fixtures = generate_fixtures(sorted(roster.clubs), matchdays=10)
    events = generate_match_events(roster, fixtures, seed=3)
    by_id = {p.id: p for club in roster.clubs.values() for p in club.players}
    for event in (e for e in events if e.type == "match_metadata"):
        for side in ("home", "away"):
            bands = [int(n) for n in event.payload[f"{side}_formation"].split("-")]
            positions = [by_id[pid].position for pid in event.payload[f"{side}_xi"]]
            assert [positions.count(x) for x in ("GK", "DEF", "FWD")] == [1, bands[0], bands[-1]]
            assert positions.count("MID") == sum(bands[1:-1])
    club_matches = {(e.match_id, e.club) for e in events if e.type == "pass"}
    for kind in ("shot", "tackle", "pressure", "possession_change"):
        seen = {(e.match_id, e.club) for e in events if e.type == kind}
        assert len(seen) >= 0.9 * len(club_matches), kind
    shots = [sum(1 for e in events if e.type == "shot" and (e.match_id, e.club) == cm) for cm in club_matches]
    assert len({n % 10 for n in shots}) > 1


def test_fixtures_meet_each_pair_home_and_away_with_matchday_recorded() -> None:
    roster = load_roster(ROSTER_PATH)
    fixtures = generate_fixtures(sorted(roster.clubs), matchdays=10)
    games = [g for day in fixtures for g in day]
    assert len(set(games)) == 30  # 15 pairs, each once at home and once away
    assert len({frozenset(g) for g in games}) == 15
    metadata = [e for e in generate_match_events(roster, fixtures, seed=1) if e.type == "match_metadata"]
    assert [e.payload["matchday"] for e in metadata] == [d for d in range(1, 11) for _ in range(3)]


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


def test_replay_under_two_minutes_for_demo_speed(monkeypatch: pytest.MonkeyPatch) -> None:
    waited: list[float] = []

    async def _record_sleep(delay: float) -> None:
        if delay > 0:
            waited.append(delay)

    monkeypatch.setattr(replay_module.asyncio, "sleep", _record_sleep)

    async def _run() -> None:
        session = ReplaySession(
            [
                {"id": f"evt-{minute:02d}", "minute": float(minute), "payload": {"kind": "pass"}}
                for minute in range(0, 91, 1)
            ],
            speed=1.0,
        )
        await session.run()

    asyncio.run(_run())
    assert sum(waited) == pytest.approx(90.0)
    assert sum(waited) < 120


def test_multiple_subscribers_receive_identical_sequences() -> None:
    async def _run() -> None:
        events = [{"id": f"e-{minute:02d}", "minute": float(minute), "payload": {}} for minute in range(20)]
        queues, emitted = await replay_all_subscribers(events, speed=0)
        sequences = [[queue.get_nowait()["id"] for _ in range(queue.qsize())] for queue in queues]
        expected = [event["id"] for event in events]
        assert sequences[0] == sequences[1] == expected
        assert [event["id"] for event in emitted] == expected

    asyncio.run(_run())
