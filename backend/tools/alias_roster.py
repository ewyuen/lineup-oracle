from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from lineup_oracle.roster import CLUB_NAMES, CLUB_FORMATIONS, CLUB_STYLES, generate_synthetic_roster, write_roster


def _read_template_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _create_mapping(seed: int, rows: list[dict[str, str]]) -> dict[str, Any]:
    roster = generate_synthetic_roster(seed=seed)
    mapping: dict[str, Any] = {"seed": seed, "source": "private/real_roster.csv.example", "clubs": {}}
    for club_name in CLUB_NAMES:
        club = roster.clubs[club_name]
        mapping["clubs"][club_name] = {
            "formation": club.formation,
            "style": club.style,
            "players": {player.number: player.name for player in club.players},
        }
    for row in rows:
        club_name = str(row.get("club") or "").strip()
        if not club_name:
            continue
        mapping["clubs"].setdefault(club_name, {"formation": CLUB_FORMATIONS.get(club_name, "4-3-3"), "style": CLUB_STYLES.get(club_name, "balanced"), "players": {}})
    return mapping


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a committed synthetic roster from a private source template.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--csv", type=str, default="")
    parser.add_argument("--roster-out", type=str, default="backend/data/roster.json")
    parser.add_argument("--mapping-out", type=str, default="private/mapping.json")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    csv_path = Path(args.csv) if args.csv else repo_root / "private" / "real_roster.csv"
    if not csv_path.exists():
        csv_path = repo_root / "private" / "real_roster.csv.example"

    rows = _read_template_csv(csv_path)
    roster = generate_synthetic_roster(seed=args.seed)
    write_roster(repo_root / args.roster_out, roster)

    mapping = _create_mapping(seed=args.seed, rows=rows)
    mapping_path = repo_root / args.mapping_out
    mapping_path.parent.mkdir(parents=True, exist_ok=True)
    mapping_path.write_text(json.dumps(mapping, indent=2), encoding="utf-8")

    print(f"Wrote roster to {repo_root / args.roster_out}")
    print(f"Wrote mapping to {mapping_path}")


if __name__ == "__main__":
    main()
