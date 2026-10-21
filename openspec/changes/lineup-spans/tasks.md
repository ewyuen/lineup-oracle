# Tasks

## 1. Branch

- [ ] 1.1 Create branch `feature/lineup-spans` from main. Verify: `git branch --show-current` prints it.

## 2. Spans

- [ ] 2.1 In `backend/lineup_oracle/api.py` add a module `tracer` and set `formation`, `llm_used`, `mode` and `language` on the current span in `_render`. Verify: existing API tests still pass.
- [ ] 2.2 Wrap `predict_lineup` in a `lineup.predict` span with `match_id`, `club` and `lineup.source` (`stored` or `personal`). Verify: test 3.2.
- [ ] 2.3 Wrap `team_news` in a `lineup.team_news` span with `match_id`, `club`, `news.input` and `news.kind`; a 422 marks the span as an error. Verify: test 3.3.

## 3. Tests

- [ ] 3.1 In `backend/tests/test_telemetry.py` add a fixture giving an in-memory span exporter on a private tracer provider.
- [ ] 3.2 Test predict: one `lineup.predict` span with the expected attributes, `lineup.source` `stored`, then `personal` after news; `llm_used` false with the model off.
- [ ] 3.3 Test team_news: structured news gives `news.input` `structured`; text news with the fake parser gives `text` and the parsed kind; news naming no player gives an error-status span and 422.
- [ ] 3.4 Test the model-failure path: fake model raises, response 200, `llm_used` false on the span. Test that no span attribute holds explanation text or the session id.

## 4. Docs

- [ ] 4.1 Update the Telemetry bullet in ARCHITECTURE.md to describe the two spans and their attributes instead of "No custom telemetry". Verify: no remaining "No custom telemetry" text.

## 5. Verify and approve

- [ ] 5.1 Run the full backend suite (`python -m pytest -q` in `backend/`) and `openspec validate lineup-spans`. Verify: both pass.
- [ ] 5.2 Deploy the branch to Azure (deploy-latest skill), make one prediction and one team-news submit through the UI, then in Application Insights confirm a `lineup.predict` and a `lineup.team_news` row in `dependencies` (type `InProc`) with `club` and `llm_used` in `customDimensions`, under the same operation as the UI request. Allow a few minutes for ingestion. Verify: both rows found, or report that they were not.
- [ ] 5.3 Human approval gate: summarize the results and stop for the user's approval. After approval, run the OpenSpec archive, then open a PR and merge it.
