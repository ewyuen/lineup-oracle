from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .events import Event, generate_fixtures, generate_match_events
from .roster import Player, Roster, generate_synthetic_roster, load_roster

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
SEED = 42


def _load_events(path: Path) -> list[Event]:
    with path.open(encoding="utf-8") as handle:
        return [Event(**json.loads(line)) for line in handle if line.strip()]


@dataclass
class State:
    """Everything the API serves: roster, events and the availability submitted so far."""

    roster: Roster
    events: list[Event]
    metadata: dict[str, Event] = field(init=False)
    players: dict[str, Player] = field(init=False)
    # (match_id, club) -> {player_id: "out" | "doubt"}; in memory only, lost on restart
    availability: dict[tuple[str, str], dict[str, str]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.metadata = {e.match_id: e for e in self.events if e.type == "match_metadata"}
        self.players = {p.id: p for club in self.roster.clubs.values() for p in club.players}

    @classmethod
    def load(cls, data_dir: Path = DATA_DIR) -> State:
        """Use the data files when present, otherwise generate the same data in memory."""
        roster_file, events_file = data_dir / "roster.json", data_dir / "events.jsonl"
        roster = load_roster(roster_file) if roster_file.exists() else generate_synthetic_roster(SEED)
        if events_file.exists():
            events = _load_events(events_file)
        else:
            events = generate_match_events(roster, generate_fixtures(sorted(roster.clubs)), seed=SEED)
        return cls(roster, events)

    def matches(self) -> list[dict]:
        rows = [
            {
                "match_id": e.match_id,
                "matchday": e.payload["matchday"],
                "home_club": e.payload["home_club"],
                "away_club": e.payload["away_club"],
            }
            for e in self.metadata.values()
        ]
        return sorted(rows, key=lambda r: (r["matchday"], r["match_id"]))

    def reset(self) -> None:
        self.availability.clear()
