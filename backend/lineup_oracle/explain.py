from __future__ import annotations

from .roster import Player
from .scoring import POSITION_RATINGS


def best_rating(player: Player) -> str:
    return max(POSITION_RATINGS[player.position], key=lambda k: player.rating[k])


def explain(player: Player, p_start: float, starts: int, played: int, status: str, mode: str = "analyst") -> str:
    """Fixed-template English sentence: availability, P(start) (analyst only), recent starts, strongest rating."""
    lead = {"doubt": "Fitness doubt", "out": "Injured or unavailable, not expected to start"}.get(status, "Likely starter")
    recent = f"started {starts} of the last {played}" if played else "no recent matches"
    odds = f" P(start) {p_start:.2f}," if mode == "analyst" else ""
    return f"{lead}:{odds} {recent}, strong {best_rating(player)}."
