from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from pathlib import Path

from .events import Event, generate_fixtures, generate_match_events
from .roster import Player, Roster, generate_synthetic_roster, load_roster

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
SEED = 42
TRANSLATED_LANGUAGES = ("es", "zh-Hant")


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
    # (session_id, match_id, club) -> {player_id: (news kind, feed seq when submitted)}; in memory only, lost on restart
    # shortcut: sessions are never evicted; add a cap or expiry if the API stays public for long
    availability: dict[tuple[str, str, str], dict[str, tuple[str, int]]] = field(default_factory=dict)
    # (session_id, match_id, club) -> player ids the analyst put in the alternatives, oldest first; replaced, never edited in place
    selections: dict[tuple[str, str, str], tuple[str, ...]] = field(default_factory=dict)
    lock: threading.Lock = field(default_factory=threading.Lock)  # held while news is checked and saved

    def __post_init__(self) -> None:
        self.metadata = {e.match_id: e for e in self.events if e.type == "match_metadata"}
        self.players = {p.id: p for club in self.roster.clubs.values() for p in club.players}
        for e in self.events:
            if e.type != "team_news":
                continue
            translations = e.payload.get("translations")
            if not e.payload.get("text") or not isinstance(translations, dict) or not all(translations.get(lang) for lang in TRANSLATED_LANGUAGES):
                raise ValueError(f"Team news {e.id} lacks its text or a Spanish or Traditional Chinese translation; regenerate the events file")
        for match_id, e in self.metadata.items():
            xi = e.payload.get("home_xi", []) + e.payload.get("away_xi", [])
            if "matchday" not in e.payload or not set(xi) <= self.players.keys():
                raise ValueError(f"Events file is out of date or does not match the roster (match {match_id}); regenerate it")

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
        self.selections.clear()
