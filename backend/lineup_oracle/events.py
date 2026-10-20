from __future__ import annotations

import argparse
import json
import random
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .roster import Club, Player, Roster, load_roster
from .scoring import quality

STARTER_POWER = 4  # higher = the best players start more reliably


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


def generate_fixtures(clubs: Iterable[str], matchdays: int = 10) -> list[list[tuple[str, str]]]:
    """Circle-method round robin for 6 clubs: 5 matchdays per cycle, home and away swapped each cycle."""
    club_list = list(clubs)
    if len(club_list) != 6:
        raise ValueError("Fixture generation expects exactly 6 clubs")
    rotation = club_list[:]
    schedule: list[list[tuple[str, str]]] = []
    for day in range(matchdays):
        pairings = [(rotation[i], rotation[5 - i]) for i in range(3)]
        schedule.append(pairings if (day // 5) % 2 == 0 else [(away, home) for home, away in pairings])
        rotation = [rotation[0], rotation[-1]] + rotation[1:-1]
    return schedule


def _formation_counts(formation: str) -> dict[str, int]:
    """'4-2-3-1' -> 4 DEF, 5 MID (2+3), 1 FWD: middle bands count as midfield."""
    bands = [int(n) for n in formation.split("-")]
    return {"GK": 1, "DEF": bands[0], "MID": sum(bands[1:-1]), "FWD": bands[-1]}


def _pick_true_xi(players: list[Player], rng: random.Random, unavailable: set[str], formation: str) -> list[Player]:
    available = [player for player in players if player.id not in unavailable]
    chosen: list[Player] = []
    for position, count in _formation_counts(formation).items():
        pool = [p for p in available if p.position == position]
        # Weighted draw without replacement: better players start more often, but not always.
        for _ in range(min(count, len(pool))):
            pick = rng.choices(pool, weights=[quality(p) ** STARTER_POWER for p in pool])[0]
            pool.remove(pick)
            chosen.append(pick)
    return chosen


def _sample_count(rng: random.Random, mean: float, spread: float) -> int:
    return max(0, int(round(rng.gauss(mean, spread))))


TEAM_NEWS_TEMPLATES: dict[str, list[str]] = {
    "injury": [
        "{club} have an injury doubt over {player} ahead of the next match.",
        "{player} is sidelined with a knock, {club} confirm.",
        "{club} medical staff have ruled out {player} for now.",
    ],
    "suspension": [
        "{player} serves a suspension for {club} this weekend.",
        "{club} will be without {player} after a card ban.",
        "{player} misses the next match for {club} through suspension.",
    ],
    "doubt": [
        "{club} are monitoring {player} after a late fitness check.",
        "{player} is a fitness doubt for {club} ahead of kick-off.",
        "{club} say {player} trained lightly and remains in doubt.",
    ],
}
TEAM_NEWS_OFFSETS: list[tuple[float, str]] = [(48.0, "injury"), (24.0, "suspension"), (1.0, "doubt")]
UNAVAILABLE_KINDS = {"injury", "suspension"}


def _append_club_team_news(events: list[Event], club: Club, match_id: str, rng: random.Random) -> set[str]:
    candidates = club.players[:]
    rng.shuffle(candidates)
    unavailable: set[str] = set()
    for offset, kind in TEAM_NEWS_OFFSETS:
        need = _formation_counts(club.formation)

        def keeps_xi_possible(c: Player) -> bool:  # an absence must leave enough players for the formation
            have = sum(1 for q in club.players if q.position == c.position and q.id not in unavailable)
            return kind not in UNAVAILABLE_KINDS or have - 1 >= need[c.position]

        player = candidates.pop(next(i for i, c in enumerate(candidates) if keeps_xi_possible(c)))
        text = rng.choice(TEAM_NEWS_TEMPLATES[kind]).format(club=club.name, player=player.name)
        events.append(
            Event(
                id=_new_id(f"{club.name}-{match_id}-news", len(events) + 1),
                match_id=match_id,
                type="team_news",
                minute=-offset,
                club=club.name,
                player=None,
                payload={"kind": kind, "text": text, "player_name": player.name},
                simulated=True,
            )
        )
        if kind in UNAVAILABLE_KINDS:
            unavailable.add(player.id)
    return unavailable


def generate_match_metadata(match_id: str, matchday: int, home_club: str, away_club: str, rng: random.Random, roster: Roster, unavailable: dict[str, set[str]]) -> Event:
    home, away = (roster.clubs[c] for c in (home_club, away_club))
    return Event(
        id=match_id,
        match_id=match_id,
        type="match_metadata",
        minute=0.0,
        club="match",
        player=None,
        payload={
            "schema_version": 1,
            "matchday": matchday,
            "home_club": home_club,
            "away_club": away_club,
            "home_formation": home.formation,
            "away_formation": away.formation,
            "home_xi": [p.id for p in _pick_true_xi(home.players, rng, unavailable.get(home_club, set()), home.formation)],
            "away_xi": [p.id for p in _pick_true_xi(away.players, rng, unavailable.get(away_club, set()), away.formation)],
        },
    )


# (type, mean per club per match, spread, has a player, payload builder)
EVENT_KINDS = [
    ("pass", 440, 80, True, lambda rng, club, ids: {"success": True, "recipient": rng.choice(ids)}),
    ("shot", 15, 5, True, lambda rng, club, ids: {"on_target": rng.choice([True, False]), "xg": round(rng.uniform(0.02, 0.4), 3)}),
    ("tackle", 16, 5, True, lambda rng, club, ids: {"won": rng.choice([True, False])}),
    ("possession_change", 8, 3, False, lambda rng, club, ids: {"team": club, "value": rng.choice(["won", "lost"])}),
    ("pressure", 14, 4, False, lambda rng, club, ids: {"phase": "build-up", "intensity": rng.randint(1, 5)}),
]


def generate_match_events(roster: Roster, fixtures: list[list[tuple[str, str]]], seed: int = 42) -> list[Event]:
    rng = random.Random(seed)
    events: list[Event] = []
    match_index = 1
    for matchday, pairings in enumerate(fixtures, start=1):
        for home_club, away_club in pairings:
            match_id = f"match-{match_index:03d}"
            unavailable = {club: _append_club_team_news(events, roster.clubs[club], match_id, rng) for club in (home_club, away_club)}
            events.append(generate_match_metadata(match_id, matchday, home_club, away_club, rng, roster, unavailable))
            for club in (home_club, away_club):
                club_players = roster.clubs[club].players
                player_ids = [p.id for p in club_players]
                for kind, mean, spread, with_player, make_payload in EVENT_KINDS:
                    for _ in range(_sample_count(rng, mean, spread)):
                        events.append(Event(
                            id=_new_id(f"{club}-{match_id}-{kind}", len(events) + 1),
                            match_id=match_id,
                            type=kind,
                            minute=rng.uniform(0.5, 90.0),
                            club=club,
                            player=rng.choice(player_ids) if with_player else None,
                            payload=make_payload(rng, club, player_ids),
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic event data")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=str, default=str(Path(__file__).resolve().parents[1] / "data" / "events.jsonl"))
    args = parser.parse_args()
    roster = load_roster(Path(__file__).resolve().parents[1] / "data" / "roster.json")
    fixtures = generate_fixtures(sorted(roster.clubs.keys()), matchdays=10)
    events = generate_match_events(roster, fixtures, seed=args.seed)
    write_events(args.out, events)
    print(f"Wrote {len(events)} events to {args.out}")


if __name__ == "__main__":
    main()
