# Design

## Context

The offline evals live in `backend/lineup_oracle/evals.py` (`lineup_scores`, `parser_accuracy`). Both live paths already hold what a check needs: `_render` in `api.py` has `facts` (from `picking.pick`) and the model's texts; `Feed.step` in `ingest.py` has the parsed `(player_id, kind)` and the event with its answer labels. The lineup spans from the earlier change are the parents for the explanation attributes. See proposal.md for motivation. ARCHITECTURE.md's Evaluation and Telemetry text and its note that the parser must not read the labels all change with this.

## Goals / Non-Goals

**Goals:**
- One grounding check and one parse comparison, each used by both the offline command and the live span.
- Live results are observe-only: no behavior change, no extra model calls.

**Non-Goals:**
- An LLM judge, runtime rejection or fallback on a failed check, a live lineup score (the true XI would leak), custom metrics.

## Decisions

- **New `checks.py`, two pure functions.** `failed_rules(text, fact, mode, club_names) -> list[str]` and `parse_correct(event, club, player_id, kind) -> bool`. Pure code, so pytest runs them with canned strings and both callers share one definition. Alternative: put them in `evals.py`; rejected because `api.py` and `ingest.py` would then import the CLI module.
- **Rules and their limits.**
  - `numbers`: every digit run in the text must be in `{starts, played, round(p_start*100) ± 1}`. Numbers written as words ("four", "四") are not read; this is a known limit, revisited after the first model run.
  - `availability`: per-language word lists (doubt: en `doubt`, es `duda`, zh-Hant `疑`; out: injury and suspension stems in each language; the words are checked in every text regardless of its language). `doubt` status needs a doubt word; `available` forbids doubt, injury and suspension words. "Fitness" and "físic" are not doubt words, so a fit player described as being in good fitness is not flagged. Negations ("no fitness doubt") are not parsed.
  - `names`: another player's full name from the same club appearing in the text.
  - `fan`: `%` or `P(start)` in fan mode (the runtime already rejects this, so here it is a guard, not new behavior).
- **Live explanation attributes in `_render`, only when `texts` came from the model.** The check runs over every listed player (XI and alternatives, the same ones validated today). `explanation.grounded_ratio` is passed/total; `explanation.failed_rules` is the sorted distinct rule names. Observe-only: a failed check changes nothing in the response. Alternative: reject and fall back to templates; rejected here because it changes live behavior and the `llm-explanations` spec, and is a separate decision.
- **Cache hits are checked again.** `Pipeline.explain` caches by facts, mode and language. The check is a few regex scans per player, so it runs on every response and needs no cache of its own.
- **`news.step` is a root span around the body of `Feed.step`.** The ticker runs on its own thread with no request, so there is no parent. `news.parse_correct` is set after `interpret` returns or raises; a raise or an unknown player sets it false. The stale-lap early return still ends the span. Labels are read only for the comparison, so the existing comment in `step` changes from "not read here" to "compared after the parse".
- **CLI.** `parser_accuracy` calls the shared `parse_correct`. The new `--explanations` flag (with `--mode` and `--language`, defaults analyst and en) runs `pick` for every club-match with the match's recorded news applied as in `lineup_scores`, passes the facts to `Pipeline.explain`, and scores the texts. The template pass uses `explain.explain` with the same facts and always runs. The news-building loop in `lineup_scores` moves into a small helper so both use it.
- **Tests:** unit tests for each rule in each language with canned good and bad text; the CLI template pass is 100%; `--explanations` with a fake client that returns a wrong count lists the failure; span tests use the in-memory exporter as in the lineup-spans tests; a feed test checks `news.parse_correct` true and false and that the client call has no labels.

## Risks / Trade-offs

- [A correct text is flagged because the model wrote numbers as words or a name in a different form] → the failures list names the rule and the text; run once with a real model and adjust the rules, or add digit-word handling, before trusting the number.
- [A legitimate sentence has a doubt word for a fit player, such as "no fitness doubt"] → negations are not parsed. The live ratio is a signal, not a gate.
- [`news.step` runs on a thread with no request context] → it is a root span by design; its trace is separate from request traces.
- [The feed now reads the labels] → only after the parse and only for the span attribute; a test asserts the parser input has no labels.
