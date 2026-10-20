from __future__ import annotations

from dataclasses import replace

import pytest

from lineup_oracle.events import _formation_counts, generate_fixtures, generate_match_events
from lineup_oracle.optimizer import POSITIONS, pick_xi, solve_formation
from lineup_oracle.roster import CLUB_NAMES, SUPPORTED_FORMATIONS, generate_synthetic_roster
from lineup_oracle.scoring import DOUBT_FACTOR, NEUTRAL_RECENT_SHARE, p_start_scores, quality, recent_xis

ROSTER = generate_synthetic_roster(42)
EVENTS = generate_match_events(ROSTER, generate_fixtures(CLUB_NAMES), seed=42)
CLUB = ROSTER.clubs["Harbor City"]


def _by_position(club, pos):
    return [p for p in club.players if p.position == pos]


def _with_rating(player, value):
    return replace(player, rating={k: value for k in player.rating})


def _club_with(player_swaps):
    """Copy of CLUB with some players replaced (by id)."""
    return replace(CLUB, players=[player_swaps.get(p.id, p) for p in CLUB.players])


# --- scoring -----------------------------------------------------------


def test_score_range():
    history = recent_xis(EVENTS, CLUB.name, 6)
    scores = p_start_scores(CLUB, history, {CLUB.players[0].id: "doubt"})
    assert all(0 <= s <= 1 for s in scores.values())


def test_better_ratings_score_higher():
    a, b = _by_position(CLUB, "MID")[:2]
    club = _club_with({a.id: _with_rating(a, 90), b.id: _with_rating(b, 60)})
    scores = p_start_scores(club, [])
    assert scores[a.id] > scores[b.id]


def test_recent_starts_raise_score():
    a, b = _by_position(CLUB, "FWD")[:2]
    club = _club_with({a.id: _with_rating(a, 70), b.id: _with_rating(b, 70)})
    scores = p_start_scores(club, [[a.id], [a.id], [b.id]])
    assert scores[a.id] > scores[b.id]


def test_no_history_uses_neutral_share():
    a, b = _by_position(CLUB, "DEF")[:2]
    club = _club_with({a.id: _with_rating(a, 70), b.id: _with_rating(b, 70)})
    scores = p_start_scores(club, [])
    assert scores[a.id] == scores[b.id] == pytest.approx(0.7 * 0.7 + 0.3 * NEUTRAL_RECENT_SHARE)


def test_out_and_doubt():
    a, b = CLUB.players[:2]
    base = p_start_scores(CLUB, [])
    scores = p_start_scores(CLUB, [], {a.id: "out", b.id: "doubt"})
    assert scores[a.id] == 0
    assert scores[b.id] == pytest.approx(base[b.id] * DOUBT_FACTOR)


def test_recent_xis_only_earlier_matchdays():
    xis = recent_xis(EVENTS, CLUB.name, 4)
    assert len(xis) == 3
    own = next(e for e in EVENTS if e.type == "match_metadata" and e.payload["matchday"] == 4 and CLUB.name in (e.payload["home_club"], e.payload["away_club"]))
    side = "home" if own.payload["home_club"] == CLUB.name else "away"
    assert own.payload[f"{side}_xi"] not in xis
    assert recent_xis(EVENTS, CLUB.name, 1) == []


def test_scoring_deterministic():
    history = recent_xis(EVENTS, CLUB.name, 6)
    assert p_start_scores(CLUB, history) == p_start_scores(CLUB, history)


# --- optimizer ---------------------------------------------------------


@pytest.mark.parametrize("formation", sorted(SUPPORTED_FORMATIONS))
def test_position_counts_and_best_players(formation):
    scores = p_start_scores(CLUB, recent_xis(EVENTS, CLUB.name, 6))
    xi = solve_formation(CLUB, scores, formation)
    counts = _formation_counts(formation)
    assert len({p.id for p in xi}) == 11
    for pos in POSITIONS:
        got = sorted(p.id for p in xi if p.position == pos)
        greedy = sorted(p.id for p in sorted(_by_position(CLUB, pos), key=lambda p: (-scores[p.id], p.id))[: counts[pos]])
        assert got == greedy


def test_out_players_never_picked():
    out = {p.id: "out" for pos in ("DEF", "MID", "FWD") for p in _by_position(CLUB, pos)[:2]}
    xi = pick_xi(CLUB, p_start_scores(CLUB, [], out))
    assert not {p.id for p, _ in xi.players} & set(out)


def test_usual_formation_wins_when_all_available():
    for club in ROSTER.clubs.values():
        history = recent_xis(EVENTS, club.name, 6)
        assert pick_xi(club, p_start_scores(club, history)).formation == club.formation


def test_shortage_changes_formation():
    out = {p.id: "out" for p in _by_position(CLUB, "DEF")[:3]}  # 4-3-3 needs 4 DEF, 3 left
    xi = pick_xi(CLUB, p_start_scores(CLUB, [], out))
    assert xi.formation != CLUB.formation
    counts = _formation_counts(xi.formation)
    assert {pos: sum(p.position == pos for p, _ in xi.players) for pos in POSITIONS} == counts


def test_alternatives_are_bench_players():
    scores = p_start_scores(CLUB, [])
    xi = pick_xi(CLUB, scores)
    picked = {p.id for p, _ in xi.players}
    for pos, alts in xi.alternatives.items():
        assert len(alts) <= 2
        assert all(p.position == pos and p.id not in picked for p, _ in alts)


def test_error_names_club():
    out = {p.id: "out" for p in _by_position(CLUB, "GK")}
    with pytest.raises(ValueError, match="Harbor City"):
        pick_xi(CLUB, p_start_scores(CLUB, [], out))


def test_ties_go_to_lower_id_and_repeat():
    scores = {p.id: 0.5 for p in CLUB.players}
    first = [p.id for p in solve_formation(CLUB, scores, "4-3-3")]
    assert first == [p.id for p in solve_formation(CLUB, scores, "4-3-3")]
    for pos, count in _formation_counts("4-3-3").items():
        lowest = sorted(p.id for p in _by_position(CLUB, pos))[:count]
        assert sorted(i for i in first if i in {p.id for p in _by_position(CLUB, pos)}) == lowest


# --- generator ---------------------------------------------------------


def test_true_xi_reproducible():
    again = generate_match_events(ROSTER, generate_fixtures(CLUB_NAMES), seed=42)
    xis = lambda evs: [e.payload for e in evs if e.type == "match_metadata"]
    assert xis(EVENTS) == xis(again)


def test_better_players_start_more():
    starts = {p.id: 0 for c in ROSTER.clubs.values() for p in c.players}
    for e in EVENTS:
        if e.type == "match_metadata":
            for key in ("home_xi", "away_xi"):
                for pid in e.payload[key]:
                    starts[pid] += 1
    top, bottom = [], []
    for club in ROSTER.clubs.values():
        for pos in POSITIONS:
            ranked = sorted(_by_position(club, pos), key=quality)
            third = max(1, len(ranked) // 3)
            bottom += [starts[p.id] for p in ranked[:third]]
            top += [starts[p.id] for p in ranked[-third:]]
    assert sum(top) / len(top) > sum(bottom) / len(bottom)
