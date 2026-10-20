from __future__ import annotations

from .roster import Player
from .scoring import POSITION_RATINGS


def explain(player: Player, p_start: float, starts: int, played: int, status: str) -> str:
    """Fixed-template English sentence: availability, P(start), recent starts, strongest rating."""
    lead = "Fitness doubt" if status == "doubt" else "Likely starter"
    recent = f"started {starts} of the last {played}" if played else "no recent matches"
    best = max(POSITION_RATINGS[player.position], key=lambda k: player.rating[k])
    return f"{lead}: P(start) {p_start:.2f}, {recent}, strong {best}."
