from __future__ import annotations

import argparse

from .api import STATUS_OF_KIND
from .optimizer import pick_xi
from .pipeline import NewsRejected, Pipeline
from .scoring import p_start_scores, recent_xis
from .state import State

FIRST_MATCHDAY = 3  # needs at least two earlier matches of history


def _news(state: State):
    return [e for e in state.events if e.type == "team_news"]


def _player_id(state: State, club: str, name: str) -> str:
    return next(p.id for p in state.roster.clubs[club].players if p.name == name)


def lineup_scores(state: State) -> dict[str, float]:
    """Mean starters correct out of 11: the pipeline versus 'same XI as the previous match'.

    The match's recorded team news is applied as structured availability (its answer labels), so this
    scores the picker; the parser has its own score. Only earlier matchdays feed the scores."""
    news: dict[tuple[str, str], dict[str, str]] = {}
    for e in _news(state):
        news.setdefault((e.match_id, e.club), {})[_player_id(state, e.club, e.payload["player_name"])] = STATUS_OF_KIND[e.payload["kind"]]
    model = baseline = n = 0
    for match_id, meta in state.metadata.items():
        matchday = meta.payload["matchday"]
        if matchday < FIRST_MATCHDAY:
            continue
        for side in ("home", "away"):
            club = meta.payload[f"{side}_club"]
            recent = recent_xis(state.metadata.values(), club, matchday)
            xi = pick_xi(state.roster.clubs[club], p_start_scores(state.roster.clubs[club], recent, news.get((match_id, club), {})))
            truth = set(meta.payload[f"{side}_xi"])
            model += len(truth & {p.id for p, _ in xi.players})
            baseline += len(truth & set(recent[-1]))
            n += 1
    return {"pipeline": model / n, "baseline": baseline / n, "matches": n}


def parser_accuracy(state: State, pipeline: Pipeline) -> dict:
    """Share of generated news lines parsed to the right player and kind. Only the text and the club are sent."""
    if not pipeline.enabled:
        return {"skipped": "model not configured (set LINEUP_LLM_ENDPOINT and LINEUP_LLM_DEPLOYMENT)"}
    right, failures = 0, []
    events = _news(state)
    for e in events:
        expected = (_player_id(state, e.club, e.payload["player_name"]), e.payload["kind"])
        try:
            got = pipeline.interpret(e.payload["text"], state.roster.clubs[e.club])
        except NewsRejected as err:
            got = f"rejected: {err}"
        if got == expected:
            right += 1
        else:
            failures.append((e.payload["text"], expected, got))
    return {"accuracy": right / len(events), "events": len(events), "failures": failures}


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the lineup pipeline on the seeded synthetic data.")
    parser.add_argument("--parser", action="store_true", help="also score the news parser (calls the model once per news event)")
    args = parser.parse_args()
    state = State.load()
    scores = lineup_scores(state)
    print(f"Lineup: pipeline {scores['pipeline']:.2f} / 11, same-XI-as-last-match baseline {scores['baseline']:.2f} / 11, over {scores['matches']} club-matches (matchday {FIRST_MATCHDAY} on)")
    if args.parser:
        result = parser_accuracy(state, Pipeline.from_env())
        if "skipped" in result:
            print("Parser: skipped,", result["skipped"])
        else:
            print(f"Parser: {result['accuracy']:.0%} of {result['events']} news lines parsed to the right player and kind")
            for text, expected, got in result["failures"]:
                print(f"  FAIL {text!r}: expected {expected}, got {got}")


if __name__ == "__main__":
    main()
