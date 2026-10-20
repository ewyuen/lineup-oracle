from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

VALID_POSITIONS = {"GK", "DEF", "MID", "FWD"}
SUPPORTED_FORMATIONS = {"4-3-3", "4-4-2", "3-5-2", "4-2-3-1", "3-4-3", "5-3-2"}
CLUB_NAMES = [
    "Harbor City",
    "Northmere",
    "Ravenside",
    "Stonebridge",
    "Summit Vale",
    "Westbrook",
]
CLUB_FORMATIONS = {
    "Harbor City": "4-3-3",
    "Northmere": "4-4-2",
    "Ravenside": "3-5-2",
    "Stonebridge": "4-2-3-1",
    "Summit Vale": "3-4-3",
    "Westbrook": "5-3-2",
}
CLUB_STYLES = {
    "Harbor City": "pressing",
    "Northmere": "balanced",
    "Ravenside": "counter",
    "Stonebridge": "direct",
    "Summit Vale": "possession",
    "Westbrook": "aggressive",
}
FIRST_NAMES = [
    "Ari", "Bren", "Cai", "Dax", "Evan", "Finn", "Gale", "Hugo", "Ivo", "Jai",
    "Kian", "Luca", "Milo", "Nico", "Oren", "Pax", "Quill", "Rafi", "Soren", "Taro",
    "Umar", "Vega", "Wren", "Yuri", "Zane", "Liam", "Mira", "Nora", "Oona", "Pia",
    "Rune", "Tess", "Vale", "Willa", "Xena", "Yara", "Zuri",
]
LAST_NAMES = [
    "Ash", "Bale", "Crest", "Dune", "Ellis", "Fenn", "Gale", "Hale", "Iris", "Jett",
    "Kite", "Lark", "Morrow", "Noble", "Oak", "Pine", "Quinn", "Rook", "Stone", "Thorne",
    "Vale", "Wren", "Yarrow", "Zed", "Briar", "Clover", "Drift", "Eden", "Fern", "Haven",
]


@dataclass
class Player:
    id: str
    club: str
    name: str
    number: int
    position: str
    archetype: str
    rating: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Club:
    name: str
    formation: str
    style: str
    players: list[Player] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "formation": self.formation,
            "style": self.style,
            "players": [player.to_dict() for player in self.players],
        }


@dataclass
class Roster:
    clubs: dict[str, Club]

    def to_dict(self) -> dict[str, Any]:
        return {"clubs": [club.to_dict() for club in self.clubs.values()]}


def _validate_player(club_name: str, player_data: dict[str, Any]) -> Player:
    position = str(player_data.get("position") or "").strip()
    if not position:
        raise ValueError(f"Missing position for player '{player_data.get('name', 'unknown')}' in club '{club_name}'")
    if position not in VALID_POSITIONS:
        raise ValueError(f"Unsupported position '{position}' for player '{player_data.get('name', 'unknown')}' in club '{club_name}'")

    player = Player(
        id=str(player_data.get("id") or f"{club_name.lower()}-{player_data.get('number', 'player')}"),
        club=club_name,
        name=str(player_data["name"]),
        number=int(player_data["number"]),
        position=position,
        archetype=str(player_data.get("archetype", "balanced")),
        rating=dict(player_data.get("rating", {})),
    )
    return player


def load_roster(path: str | Path) -> Roster:
    file_path = Path(path)
    payload = json.loads(file_path.read_text(encoding="utf-8"))
    clubs_data = payload.get("clubs") if isinstance(payload, dict) and "clubs" in payload else payload
    if not isinstance(clubs_data, list):
        raise ValueError("Roster file must contain a top-level list of clubs or a 'clubs' object")

    clubs: dict[str, Club] = {}
    for club_data in clubs_data:
        club_name = str(club_data["name"])
        formation = str(club_data.get("formation", "4-3-3"))
        if formation not in SUPPORTED_FORMATIONS:
            raise ValueError(f"Club '{club_name}' has unsupported formation '{formation}'")

        players: list[Player] = []
        seen_numbers: set[int] = set()
        for player_data in club_data.get("players", []):
            player_name = str(player_data.get("name", "unknown"))
            number = int(player_data["number"])
            if number in seen_numbers:
                raise ValueError(f"Duplicate shirt number {number} for club '{club_name}' player '{player_name}'")
            seen_numbers.add(number)
            player = _validate_player(club_name, player_data)
            players.append(player)

        clubs[club_name] = Club(name=club_name, formation=formation, style=str(club_data.get("style", "balanced")), players=players)

    if len(clubs) != 6:
        raise ValueError(f"Expected 6 clubs in roster, found {len(clubs)}")
    for club_name, club in clubs.items():
        if len(club.players) < 20:
            raise ValueError(f"Club '{club_name}' has fewer than 20 players")
    return Roster(clubs=clubs)


def _build_player_name(rng: random.Random, club_name: str, index: int, used_names: set[str]) -> str:
    while True:
        first = rng.choice(FIRST_NAMES)
        last = rng.choice(LAST_NAMES)
        candidate = f"{first} {last}"
        if candidate not in used_names:
            used_names.add(candidate)
            return candidate


ARCHETYPES = {"GK": "keeper", "DEF": "defender", "MID": "playmaker", "FWD": "finisher"}


def _make_player(rng: random.Random, club_name: str, number: int, position: str, used_names: set[str]) -> Player:
    name = _build_player_name(rng, club_name, number, used_names)  # name first: keeps the seeded stream stable
    rating = {skill: rng.randint(55, 92) for skill in ("pace", "passing", "dribbling", "defending", "shooting")}
    return Player(
        id=f"{club_name.lower().replace(' ', '-')}-{number}",
        club=club_name,
        name=name,
        number=number,
        position=position,
        archetype=ARCHETYPES[position],
        rating=rating,
    )


def alias_roster(rows: list[dict[str, str]], seed: int = 42) -> tuple[Roster, dict[str, Any]]:
    """Build a synthetic roster from private rows (real_club, real_player, number, position).

    Real clubs map to CLUB_NAMES in order of first appearance. Returns the roster and the
    real-to-synthetic mapping, which must only be written under private/.
    """
    rng = random.Random(seed)
    used_names: set[str] = set()
    by_club: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_club.setdefault(row["real_club"].strip(), []).append(row)
    if len(by_club) != len(CLUB_NAMES):
        raise ValueError(f"Expected {len(CLUB_NAMES)} clubs in private input, found {len(by_club)}")

    clubs: dict[str, Club] = {}
    mapping: dict[str, Any] = {"seed": seed, "clubs": {}, "players": {}}
    for (real_club, club_rows), club_name in zip(by_club.items(), CLUB_NAMES):
        mapping["clubs"][real_club] = club_name
        players = []
        for row in club_rows:
            player = _make_player(rng, club_name, int(row["number"]), row["position"].strip(), used_names)
            players.append(player)
            mapping["players"][f"{real_club}/{row['real_player'].strip()}"] = f"{club_name}/{player.name}"
        clubs[club_name] = Club(name=club_name, formation=CLUB_FORMATIONS[club_name], style=CLUB_STYLES[club_name], players=players)
    return Roster(clubs=clubs), mapping


def generate_synthetic_roster(seed: int = 42) -> Roster:
    rng = random.Random(seed)
    used_names: set[str] = set()
    clubs: dict[str, Club] = {}
    for club_name in CLUB_NAMES:
        formation = CLUB_FORMATIONS[club_name]
        players: list[Player] = []
        position_order = ["GK", "DEF", "MID", "FWD"]
        counts = {"GK": 2, "DEF": 6, "MID": 7, "FWD": 5}
        number = 1
        for position in ["GK", "DEF", "MID", "FWD"]:
            for _ in range(counts[position]):
                players.append(_make_player(rng, club_name, number, position, used_names))
                number += 1
        clubs[club_name] = Club(name=club_name, formation=formation, style=CLUB_STYLES[club_name], players=players)
    return Roster(clubs=clubs)


def write_roster(path: str | Path, roster: Roster) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(roster.to_dict(), indent=2), encoding="utf-8")
