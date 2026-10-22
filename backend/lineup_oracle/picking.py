from __future__ import annotations

from dataclasses import replace

from .explain import best_rating
from .optimizer import ALTERNATIVES, POSITIONS, pick_xi
from .scoring import RECENT_MATCHES, p_start_scores, recent_xis
from .state import State

STATUS_OF_KIND = {"injury": "out", "suspension": "out", "doubt": "doubt", "recovered": "available", "cleared": "available", "fit": "available"}
SELECTABLE_KINDS = ("injury", "doubt")  # a suspended player cannot be put in the alternatives


def statuses(availability: dict[str, tuple[str, int]]) -> dict[str, str]:
    """Status per player from (kind, seq) entries."""
    return {p: STATUS_OF_KIND[kind] for p, (kind, _) in availability.items()}


def _fact(p, s: float, last: list[list[str]], status: str) -> dict:
    return {
        "id": p.id, "name": p.name, "position": p.position, "p_start": round(s, 2),
        "starts": sum(p.id in x for x in last), "played": len(last),
        "status": status, "best_rating": best_rating(p),
    }


def _context(state: State, match_id: str, club_name: str):
    if match_id not in state.metadata:
        raise LookupError(f"Unknown match {match_id!r}")
    meta = state.metadata[match_id].payload
    if club_name not in (meta["home_club"], meta["away_club"]):
        raise ValueError(f"Club {club_name!r} does not play in match {match_id!r}")
    club = state.roster.clubs[club_name]
    return club, recent_xis(state.metadata.values(), club_name, meta["matchday"])  # earlier matchdays only


def pick(state: State, match_id: str, club_name: str, availability: dict[str, str]):
    """The XI and the facts about each listed player; fast, no model call.

    Raises LookupError for an unknown match and ValueError for a club outside the match or no legal XI."""
    club, recent = _context(state, match_id, club_name)
    last = recent[-RECENT_MATCHES:]
    xi = pick_xi(club, p_start_scores(club, recent, availability))
    listed = list(xi.players) + [ps for pos in POSITIONS for ps in xi.alternatives[pos]]
    return xi, [_fact(p, s, last, availability.get(p.id, "available")) for p, s in listed]


def eligible(club, xi, merged: dict[str, tuple[str, int]]) -> dict:
    """Non-starters whose latest news is an injury or a doubt: the players an analyst may put in the alternatives."""
    starters = {p.id for p, _ in xi.players}
    return {p.id: p for p in club.players if p.id not in starters and merged.get(p.id, ("", 0))[0] in SELECTABLE_KINDS}


def overlay(state: State, match_id: str, club_name: str, xi, facts: list[dict], merged: dict[str, tuple[str, int]], selections):
    """(xi, facts, candidates) with the analyst's selections in the alternatives. Never touches the objects passed in,
    which may be the shared stored prediction.

    Per position at most ALTERNATIVES players are listed: the most recent valid selections first claim the slots,
    the highest-ranked natural alternatives fill the rest. Natural entries are listed in rank order, then the others
    oldest selection first. A selection that is no longer valid is left out here and dropped on the next write."""
    club, recent = _context(state, match_id, club_name)
    last = recent[-RECENT_MATCHES:]
    status = statuses(merged)
    scores = p_start_scores(club, recent, status)
    cands = eligible(club, xi, merged)
    valid = [i for i in selections if i in cands]
    known = {f["id"]: f for f in facts}
    alternatives, included = {}, set()
    for pos in POSITIONS:
        natural = xi.alternatives[pos]
        natural_ids = [p.id for p, _ in natural]
        chosen = [i for i in valid if cands[i].position == pos][-ALTERNATIVES:]
        shown = set(chosen) | set([i for i in natural_ids if i not in chosen][: ALTERNATIVES - len(chosen)])
        alternatives[pos] = [(p, s) for p, s in natural if p.id in shown] + [(cands[i], scores[i]) for i in chosen if i not in natural_ids]
        included.update(chosen)
    new_xi = replace(xi, alternatives=alternatives)
    listed = list(new_xi.players) + [ps for pos in POSITIONS for ps in alternatives[pos]]
    new_facts = [known.get(p.id) or _fact(p, s, last, status.get(p.id, "available")) for p, s in listed]
    candidates = [
        {"id": p.id, "name": p.name, "number": p.number, "position": p.position, "kind": merged[p.id][0], "included": p.id in included}
        for p in sorted(cands.values(), key=lambda p: (POSITIONS.index(p.position), p.id))
    ]
    return new_xi, new_facts, candidates
