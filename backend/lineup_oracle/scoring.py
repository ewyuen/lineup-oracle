from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING

from .roster import Club, Player

if TYPE_CHECKING:  # events imports quality() from here
    from .events import Event

QUALITY_WEIGHT = 0.7
RECENT_WEIGHT = 0.3
DOUBT_FACTOR = 0.5
NEUTRAL_RECENT_SHARE = 0.5
RECENT_MATCHES = 5
AVAILABILITY_FACTOR = {"available": 1.0, "doubt": DOUBT_FACTOR, "out": 0.0}
# Which ratings matter for each position.
POSITION_RATINGS = {
    "GK": ("defending", "passing"),
    "DEF": ("defending", "pace", "passing"),
    "MID": ("passing", "dribbling", "defending"),
    "FWD": ("shooting", "pace", "dribbling"),
}


def quality(player: Player) -> float:
    """Mean of the position-relevant ratings, 0 to 1."""
    keys = POSITION_RATINGS[player.position]
    return sum(player.rating[k] for k in keys) / (100 * len(keys))


def recent_xis(events: Iterable[Event], club: str, matchday: int) -> list[list[str]]:
    """The club's starting XIs from matchdays before `matchday`, oldest first."""
    found: list[tuple[int, list[str]]] = []
    for e in events:
        if e.type != "match_metadata" or e.payload["matchday"] >= matchday:
            continue
        for side in ("home", "away"):
            if e.payload[f"{side}_club"] == club:
                found.append((e.payload["matchday"], e.payload[f"{side}_xi"]))
    return [xi for _, xi in sorted(found, key=lambda item: item[0])]


def p_start_scores(club: Club, recent: list[list[str]], availability: Mapping[str, str] | None = None) -> dict[str, float]:
    """P(start) per player id: availability * (0.7 * quality + 0.3 * share of last 5 starts)."""
    availability = availability or {}
    last = recent[-RECENT_MATCHES:]
    scores: dict[str, float] = {}
    for p in club.players:
        share = sum(p.id in xi for xi in last) / len(last) if last else NEUTRAL_RECENT_SHARE
        base = QUALITY_WEIGHT * quality(p) + RECENT_WEIGHT * share
        scores[p.id] = AVAILABILITY_FACTOR[availability.get(p.id, "available")] * base
    return scores
