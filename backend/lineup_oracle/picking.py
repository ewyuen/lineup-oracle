from __future__ import annotations

from .explain import best_rating
from .optimizer import POSITIONS, pick_xi
from .scoring import RECENT_MATCHES, p_start_scores, recent_xis
from .state import State

STATUS_OF_KIND = {"injury": "out", "suspension": "out", "doubt": "doubt", "recovered": "available", "cleared": "available", "fit": "available"}


def pick(state: State, match_id: str, club_name: str, availability: dict[str, str]):
    """The XI and the facts about each listed player; fast, no model call.

    Raises LookupError for an unknown match and ValueError for a club outside the match or no legal XI."""
    if match_id not in state.metadata:
        raise LookupError(f"Unknown match {match_id!r}")
    meta = state.metadata[match_id].payload
    if club_name not in (meta["home_club"], meta["away_club"]):
        raise ValueError(f"Club {club_name!r} does not play in match {match_id!r}")
    club = state.roster.clubs[club_name]
    recent = recent_xis(state.metadata.values(), club_name, meta["matchday"])  # earlier matchdays only
    last = recent[-RECENT_MATCHES:]
    xi = pick_xi(club, p_start_scores(club, recent, availability))
    listed = list(xi.players) + [ps for pos in POSITIONS for ps in xi.alternatives[pos]]
    facts = [
        {
            "id": p.id, "name": p.name, "position": p.position, "p_start": round(s, 2),
            "starts": sum(p.id in x for x in last), "played": len(last),
            "status": availability.get(p.id, "available"), "best_rating": best_rating(p),
        }
        for p, s in listed
    ]
    return xi, facts
