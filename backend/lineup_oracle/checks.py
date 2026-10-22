"""Rule-based checks shared by the offline evals and the live spans: no model call, same answer every time."""
from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
# Words from all three languages are checked in every text: a mixed-language answer is wrong either way.
DOUBT_WORDS = ("doubt", "duda", "疑")
OUT_WORDS = ("injur", "suspen", "banned", "ruled out", "lesi", "sanci", "傷", "停賽", "禁賽")


def failed_rules(text: str, fact: dict[str, Any], mode: str, other_names: Iterable[str]) -> list[str]:
    """Names of the rules this explanation breaks, sorted; empty when it is grounded in the fact.

    `fact` is one entry of `picking.pick`'s facts; `other_names` are the club's other players.
    shortcut: numbers written as words ("four", "四") are not read, add digit-word handling if a model run shows it matters."""
    failed = set()
    allowed = (fact["starts"], fact["played"])
    for token in NUMBER.findall(text):
        value = float(token.replace(",", "."))
        if value not in allowed and abs(value - fact["p_start"] * 100) > 1 and abs(value - fact["p_start"]) > 0.01:
            failed.add("numbers")
    lowered = text.casefold()
    doubtful = any(w in lowered for w in DOUBT_WORDS)
    in_doubt = fact["status"] == "doubt"
    if doubtful != in_doubt or (not in_doubt and any(w in lowered for w in OUT_WORDS)):
        failed.add("availability")
    if any(name != fact["name"] and name in text for name in other_names):
        failed.add("names")
    if mode == "fan" and ("%" in text or "p(start)" in lowered):
        failed.add("fan")
    return sorted(failed)


def parse_correct(event, club, player_id: str | None, kind: str | None) -> bool:
    """Whether the parser's answer equals the event's answer labels (used for scoring, never as parser input)."""
    names = {p.id: p.name for p in club.players}
    return names.get(player_id) == event.payload["player_name"] and kind == event.payload["kind"]
