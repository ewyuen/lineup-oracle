# Proposal

## Why

The evals run only as an offline command, so a deployed demo gives no sign of how well the parser and the explanations are doing, and nothing scores whether an explanation matches its facts. Two of them need no hidden answer at runtime: the explanation can be checked against the facts the API already computed, and the shared news feed's generated events carry the answer labels for the parser.

## What Changes

- Add a rule-based explanation grounding check (no model call): each explanation's numbers, availability claim, player name and fan-mode rule are checked against that player's facts, in en, es and zh-Hant.
- `python -m lineup_oracle.evals` always scores the template explanations (they must be 100%) and, with `--explanations` and a configured model, scores the model's explanations and lists the failures. Parser accuracy stays as it is, but shares its answer comparison with the live check below.
- Live, observe-only: when the model wrote the explanations, `lineup.predict` and `lineup.team_news` carry `explanation.grounded_ratio` and `explanation.failed_rules`. The response and the XI never change.
- Live: each news item the shared feed delivers gets a `news.step` span (its own root span, since the feed runs on a background thread) with `news.parse_correct`, comparing the parser's answer with the event's labels after the parse. The parser still never sees the labels.
- Relax the telemetry spec from "two custom spans" to these three spans and the two new attributes; custom metrics, events and dashboards stay out.

Out of scope: an LLM-as-judge faithfulness score, rejecting or replacing ungrounded explanations at runtime, exporting the lineup score (it needs the true XI, which a live request must not use), and the UI.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `lineup-evaluation`: adds explanation grounding as a third evaluation, offline for templates and for the model.
- `telemetry`: adds the `news.step` span and the `explanation.*` attributes, and widens the allowed custom spans.

## Impact

- Code: a new `backend/lineup_oracle/checks.py` (the grounding check and the parser-answer comparison), `evals.py`, `api.py` (`_render`), `ingest.py` (`Feed.step`); tests in `backend/tests/`.
- Contracts: ARCHITECTURE.md Evaluation section and Telemetry bullet change, and the data note that the parser must not read the labels now says the feed compares them after parsing. No API request or response change.
- Cost: no extra model calls at runtime. The offline `--explanations` run makes one model call per club-match (48 on seed 42).
