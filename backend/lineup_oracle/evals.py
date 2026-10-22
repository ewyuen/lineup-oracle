from __future__ import annotations

import argparse

from .checks import failed_rules, parse_correct
from .explain import explain
from .picking import STATUS_OF_KIND, pick
from .optimizer import pick_xi
from .pipeline import NewsRejected, Pipeline
from .scoring import p_start_scores, recent_xis
from .state import State

FIRST_MATCHDAY = 3  # needs at least two earlier matches of history


def _news(state: State):
    return [e for e in state.events if e.type == "team_news"]


def _player_id(state: State, club: str, name: str) -> str:
    return next(p.id for p in state.roster.clubs[club].players if p.name == name)


def _applied_news(state: State) -> dict[tuple[str, str], dict[str, str]]:
    """Each match's recorded team news as structured availability (its answer labels): (match, club) -> {player: status}."""
    news: dict[tuple[str, str], dict[str, str]] = {}
    for e in _news(state):
        news.setdefault((e.match_id, e.club), {})[_player_id(state, e.club, e.payload["player_name"])] = STATUS_OF_KIND[e.payload["kind"]]
    return news


def lineup_scores(state: State) -> dict[str, float]:
    """Mean starters correct out of 11: the pipeline versus 'same XI as the previous match'.

    The match's recorded team news is applied as structured availability (its answer labels), so this
    scores the picker; the parser has its own score. Only earlier matchdays feed the scores."""
    news = _applied_news(state)
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
        club = state.roster.clubs[e.club]
        try:
            got = pipeline.interpret(e.payload["text"], club)
        except NewsRejected as err:
            got = f"rejected: {err}"
        if not isinstance(got, str) and parse_correct(e, club, *got):
            right += 1
        else:
            expected = (_player_id(state, e.club, e.payload["player_name"]), e.payload["kind"])
            failures.append((e.payload["text"], expected, got))
    return {"accuracy": right / len(events), "events": len(events), "failures": failures}


def _club_match_facts(state: State):
    """(club, facts) for every club-match from matchday 3 on, picked with the match's recorded team news."""
    news = _applied_news(state)
    for match_id, meta in state.metadata.items():
        if meta.payload["matchday"] < FIRST_MATCHDAY:
            continue
        for side in ("home", "away"):
            club = meta.payload[f"{side}_club"]
            yield club, pick(state, match_id, club, news.get((match_id, club), {}))[1]


def explanation_grounding(state: State, texts_for, mode: str) -> dict:
    """Share of explanations grounded in their facts. `texts_for(facts)` returns {player id: text}, or None when the
    explanations fell back (those club-matches are counted, not scored)."""
    total, fallbacks, failures = 0, 0, []
    for club, facts in _club_match_facts(state):
        texts = texts_for(facts)
        if texts is None:
            fallbacks += 1
            continue
        names = [p.name for p in state.roster.clubs[club].players]
        for fact in facts:
            failed = failed_rules(texts[fact["id"]], fact, mode, names)
            total += 1
            if failed:
                failures.append((fact["name"], texts[fact["id"]], failed))
    return {"grounded": (total - len(failures)) / total if total else 0.0, "explanations": total, "fallbacks": fallbacks, "failures": failures}


def template_grounding(state: State, mode: str) -> dict:
    return explanation_grounding(
        state,
        lambda facts: {f["id"]: explain(state.players[f["id"]], f["p_start"], f["starts"], f["played"], f["status"], mode) for f in facts},
        mode,
    )


def model_grounding(state: State, pipeline: Pipeline, mode: str, language: str) -> dict:
    if not pipeline.enabled:
        return {"skipped": "model not configured (set LINEUP_LLM_ENDPOINT and LINEUP_LLM_DEPLOYMENT)"}
    return explanation_grounding(state, lambda facts: pipeline.explain(facts, mode, language), mode)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the lineup pipeline on the seeded synthetic data.")
    parser.add_argument("--parser", action="store_true", help="also score the news parser (calls the model once per news event)")
    parser.add_argument("--explanations", action="store_true", help="also score the model's explanations against the facts (calls the model once per club-match)")
    parser.add_argument("--mode", choices=["analyst", "fan"], default="analyst", help="mode of the explanations scored with --explanations")
    parser.add_argument("--language", choices=["en", "es", "zh-Hant"], default="en", help="language of the explanations scored with --explanations")
    args = parser.parse_args()
    state = State.load()
    scores = lineup_scores(state)
    print(f"Lineup: pipeline {scores['pipeline']:.2f} / 11, same-XI-as-last-match baseline {scores['baseline']:.2f} / 11, over {scores['matches']} club-matches (matchday {FIRST_MATCHDAY} on)")
    for mode in ("analyst", "fan"):
        result = template_grounding(state, mode)
        print(f"Template explanations ({mode}): {result['grounded']:.0%} of {result['explanations']} grounded in the facts")
    if args.explanations:
        result = model_grounding(state, Pipeline.from_env(), args.mode, args.language)
        if "skipped" in result:
            print("Model explanations: skipped,", result["skipped"])
        else:
            print(f"Model explanations ({args.mode}, {args.language}): {result['grounded']:.0%} of {result['explanations']} grounded in the facts"
                  f" ({result['fallbacks']} club-matches fell back to templates and were not scored)")
            for name, text, failed in result["failures"]:
                print(f"  FAIL {name} [{', '.join(failed)}]: {text!r}")
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
