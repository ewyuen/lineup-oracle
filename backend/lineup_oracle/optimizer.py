from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

from .events import _formation_counts
from .roster import SUPPORTED_FORMATIONS, Club, Player

USUAL_PRIOR = 1.0
OTHER_PRIOR = 0.85
ALTERNATIVES = 2
POSITIONS = ("GK", "DEF", "MID", "FWD")


@dataclass
class XI:
    formation: str
    players: list[tuple[Player, float]]  # (player, p_start)
    alternatives: dict[str, list[tuple[Player, float]]]


def solve_formation(club: Club, scores: dict[str, float], formation: str) -> list[Player] | None:
    """Best 11 for one formation as a MILP, or None if the squad cannot fill it."""
    # Out players (score 0) are left out, so a shortage is infeasible instead of picking them.
    # Sorted by id, with a tiny penalty per index, so ties go to the lower id.
    # shortcut: score gaps below ~2e-4 (20 players x 1e-5) count as ties; shrink the penalty if the weights ever get finer.
    pool = sorted((p for p in club.players if scores[p.id] > 0), key=lambda p: p.id)
    if not pool:
        return None
    n = len(pool)
    value = np.array([scores[p.id] - 1e-5 * i for i, p in enumerate(pool)])
    counts = _formation_counts(formation)
    rows = np.array([[1.0 if p.position == pos else 0.0 for p in pool] for pos in POSITIONS])
    need = np.array([counts[pos] for pos in POSITIONS], dtype=float)
    result = milp(
        c=-value,
        constraints=LinearConstraint(rows, need, need),
        integrality=np.ones(n),
        bounds=Bounds(0, 1),
        options={"mip_rel_gap": 0},  # exact optimum, so the id tie-break holds
    )
    if not result.success:
        return None
    return [p for p, x in zip(pool, result.x) if x > 0.5]


def pick_xi(club: Club, scores: dict[str, float]) -> XI:
    """Solve every formation, weight by the formation prior, return the best XI."""
    best: tuple[float, str, list[Player]] | None = None
    for formation in sorted(SUPPORTED_FORMATIONS):
        xi = solve_formation(club, scores, formation)
        if xi is None:
            continue
        prior = USUAL_PRIOR if formation == club.formation else OTHER_PRIOR
        total = prior * sum(scores[p.id] for p in xi)
        if best is None or total > best[0]:
            best = (total, formation, xi)
    if best is None:
        raise ValueError(f"No formation can be filled for {club.name}")
    _, formation, xi = best
    picked = {p.id for p in xi}
    alternatives = {
        pos: sorted(
            ((p, scores[p.id]) for p in club.players if p.position == pos and p.id not in picked and scores[p.id] > 0),
            key=lambda item: (-item[1], item[0].id),
        )[:ALTERNATIVES]
        for pos in POSITIONS
    }
    ordered = sorted(xi, key=lambda p: (POSITIONS.index(p.position), -scores[p.id], p.id))
    return XI(formation, [(p, scores[p.id]) for p in ordered], alternatives)
