from __future__ import annotations

import argparse
import json
import random
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .roster import Player, Roster, load_roster


def _new_id(prefix: str, seq: int) -> str:
    return f"{prefix}-{seq:04d}"


@dataclass
class Event:
    id: str
    match_id: str
    type: str
    minute: float
    club: str
    player: str | None
    payload: dict[str, Any] = field(default_factory=dict)
    simulated: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _fixture_round_robin(clubs: list[str], matchdays: int = 10) -> list[list[tuple[str, str]]]:
    rotation = clubs[:]
    schedule: list[list[tuple[str, str]]] = []
    for _ in range(matchdays):
        pairings: list[tuple[str, str]] = []
        for idx in range(0, len(rotation), 2):
            home = rotation[idx]
            away = rotation[(idx + 1) % len(rotation)]
            if idx + 1 >= len(rotation):
                away = rotation[0]
            if home != away:
                pairings.append((home, away))
        if len(pairings) == 3:
            schedule.append(pairings)
        rotation = [rotation[0]] + [rotation[-1]] + rotation[1:-1]
    return schedule


def generate_fixtures(clubs: Iterable[str], matchdays: int = 10) -> list[list[tuple[str, str]]]:
    club_list = list(clubs)
    if len(club_list) != 6:
        raise ValueError("Fixture generation expects exactly 6 clubs")
    return _fixture_round_robin(club_list, matchdays)


def _pick_true_xi(club_name: str, players: list[Player], rng: random.Random) -> list[Player]:
    available = [player for player in players if player.position == "GK"] + [player for player in players if player.position == "DEF"] + [player for player in players if player.position == "MID"] + [player for player in players if player.position == "FWD"]
    chosen: list[Player] = []
    positions = {"GK": 1, "DEF": 4, "MID": 4, "FWD": 2}
    for position, count in positions.items():
        pos_players = [p for p in available if p.position == position]
        rng.shuffle(pos_players)
        chosen.extend(pos_players[:count])
    return chosen


def _sample_count(rng: random.Random, mean: float, spread: float) -> int:
    return max(0, int(round(rng.gauss(mean, spread))))


def generate_team_news(roster: Roster, seed: int = 42) -> list[Event]:
    rng = random.Random(seed)
    events: list[Event] = []
    position_ids = {club_name: [player.id for player in club.players] for club_name, club in roster.clubs.items()}
    for club_name, club in roster.clubs.items():
        candidates = club.players[:]
        rng.shuffle(candidates)
        for offset, kind in [(48.0, "injury"), (24.0, "suspension"), (1.0, "doubt")]:
            player = candidates.pop(0)
            text = f"{club_name} have a {kind} concern around {player.name} ahead of the next match."
            events.append(
                Event(
                    id=_new_id("teamnews", len(events) + 1),
                    match_id=f"match-{club_name.lower()}-{offset}",
                    type="team_news",
                    minute=-offset,
                    club=club_name,
                    player=None,
                    payload={"kind": kind, "text": text, "player_name": player.name},
                    simulated=True,
                )
            )
    return events


def generate_match_metadata(ref_match_id: str, home_club: str, away_club: str, rng: random.Random, roster: Roster) -> dict[str, Any]:
    home_players = _pick_true_xi(home_club, roster.clubs[home_club].players, rng)
    away_players = _pick_true_xi(away_club, roster.clubs[away_club].players, rng)
    return {
        "id": ref_match_id,
        "match_id": ref_match_id,
        "schema_version": 1,
        "type": "match_metadata",
        "minute": 0.0,
        "club": "match",
        "player": None,
        "payload": {
            "home_club": home_club,
            "away_club": away_club,
            "home_formation": roster.clubs[home_club].formation,
            "away_formation": roster.clubs[away_club].formation,
            "home_xi": [player.id for player in home_players],
            "away_xi": [player.id for player in away_players],
        },
        "simulated": True,
    }


def generate_match_events(roster: Roster, fixtures: list[list[tuple[str, str]]], seed: int = 42) -> list[Event]:
    rng = random.Random(seed)
    events: list[Event] = []
    match_index = 1
    for matchday in fixtures:
        for home_club, away_club in matchday:
            match_id = f"match-{match_index:03d}"
            metadata = generate_match_metadata(match_id, home_club, away_club, rng, roster)
            events.append(Event(**{k: v for k, v in metadata.items() if k in {"id", "match_id", "type", "minute", "club", "player", "payload", "simulated"}}))
            for club in (home_club, away_club):
                club_players = roster.clubs[club].players
                pass_count = _sample_count(rng, 440, 80)
                shot_count = _sample_count(rng, 15, 5)
                tackle_count = _sample_count(rng, 16, 5)
                possession_count = _sample_count(rng, 8, 3)
                pressure_count = _sample_count(rng, 14, 4)
                for minute in range(0, 91, 9):
                    if minute == 0:
                        continue
                    for _ in range(pass_count // 10):
                        player = rng.choice(club_players)
                        events.append(Event(
                            id=_new_id(f"{club}-{match_id}-pass", len(events) + 1),
                            match_id=match_id,
                            type="pass",
                            minute=float(minute + rng.uniform(0.0, 8.9)),
                            club=club,
                            player=player.id,
                            payload={"success": True, "recipient": rng.choice([p.id for p in club_players])},
                            simulated=True,
                        ))
                    for _ in range(shot_count // 10):
                        player = rng.choice(club_players)
                        events.append(Event(
                            id=_new_id(f"{club}-{match_id}-shot", len(events) + 1),
                            match_id=match_id,
                            type="shot",
                            minute=float(minute + rng.uniform(0.0, 8.9)),
                            club=club,
                            player=player.id,
                            payload={"on_target": rng.choice([True, False]), "xg": round(rng.uniform(0.02, 0.4), 3)},
                            simulated=True,
                        ))
                    for _ in range(tackle_count // 10):
                        player = rng.choice(club_players)
                        events.append(Event(
                            id=_new_id(f"{club}-{match_id}-tackle", len(events) + 1),
                            match_id=match_id,
                            type="tackle",
                            minute=float(minute + rng.uniform(0.0, 8.9)),
                            club=club,
                            player=player.id,
                            payload={"won": rng.choice([True, False])},
                            simulated=True,
                        ))
                    for _ in range(possession_count // 10):
                        events.append(Event(
                            id=_new_id(f"{club}-{match_id}-possession", len(events) + 1),
                            match_id=match_id,
                            type="possession_change",
                            minute=float(minute + rng.uniform(0.0, 8.9)),
                            club=club,
                            player=None,
                            payload={"team": club, "value": rng.choice(["won", "lost"])},
                            simulated=True,
                        ))
                    for _ in range(pressure_count // 10):
                        events.append(Event(
                            id=_new_id(f"{club}-{match_id}-pressure", len(events) + 1),
                            match_id=match_id,
                            type="pressure",
                            minute=float(minute + rng.uniform(0.0, 8.9)),
                            club=club,
                            player=None,
                            payload={"phase": "build-up", "intensity": rng.randint(1, 5)},
                            simulated=True,
                        ))
            match_index += 1
    return events


def write_events(path: str | Path, events: list[Event]) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event.to_dict(), separators=(",", ":")) + "\n")


def generate_seeded_dataset(seed: int = 42) -> tuple[list[Event], list[list[tuple[str, str]]]]:
    roster = load_roster(Path(__file__).resolve().parent / "data" / "roster.json")
    fixtures = generate_fixtures(sorted(roster.clubs.keys()), matchdays=10)
    events = generate_match_events(roster, fixtures, seed=seed)
    return events, fixtures


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic event data")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=str, default=str(Path(__file__).resolve().parent / "data" / "events.jsonl"))
    args = parser.parse_args()
    roster = load_roster(Path(__file__).resolve().parent / "data" / "roster.json")
    fixtures = generate_fixtures(sorted(roster.clubs.keys()), matchdays=10)
    events = generate_match_events(roster, fixtures, seed=args.seed)
    write_events(args.out, events)
    print(f"Wrote {len(events)} events to {args.out}")


if __name__ == "__main__":
    main()
