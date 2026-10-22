# Tasks

## 1. Branch

- [x] 1.1 Create branch `feature/observable-evals` from the latest `origin/main`. Verify: `git branch --show-current` prints it.

## 2. Checks

- [x] 2.1 Add `backend/lineup_oracle/checks.py` with `failed_rules(text, fact, mode, club_names)` (rules `numbers`, `availability`, `names`, `fan`; en, es, zh-Hant) and `parse_correct(event, club, player_id, kind)`. Verify: tests 2.2 and 2.3.
- [x] 2.2 Test `failed_rules` with canned good and bad texts per rule and per language: wrong count, count that matches, `p_start` as a percentage within one point, doubt claimed for a fit player, doubt missing for a doubtful player, a teammate's name, `%` in fan mode, and the same input twice.
- [x] 2.3 Test `parse_correct`: right player and kind, wrong kind, player outside the club.

## 3. Offline evals

- [x] 3.1 In `evals.py`, make `parser_accuracy` use `parse_correct` and move the news-building loop of `lineup_scores` into a helper. Verify: the existing `test_evals.py` tests pass unchanged.
- [x] 3.2 Add the template grounding pass (always runs) and `--explanations` with `--mode` and `--language` (model pass; skipped with a reason when no model is configured). Verify: tests 3.3.
- [x] 3.3 Tests: the template pass is 100% on the seeded data; `--explanations` with a fake client that returns a wrong count reports a share below 100% and lists the player, text and rule; with no model it prints the skip and the lineup scores still print.

## 4. Live spans

- [x] 4.1 In `api.py` `_render`, when the model wrote the texts, set `explanation.grounded_ratio` and `explanation.failed_rules` on the current span; set nothing for template texts. Verify: tests 4.2.
- [x] 4.2 Span tests (in-memory exporter): grounded fake model gives ratio 1 and an empty list; a fake model with one wrong count gives a ratio below 1, `numbers` listed, and the same 200 response and text; template fallback has no `explanation.*` attributes.
- [x] 4.3 In `ingest.py` wrap the body of `Feed.step` in a `news.step` root span with `match_id`, `club`, `news.applied` and `news.parse_correct`, and update the label comment. Verify: tests 4.4.
- [x] 4.4 Feed span tests: a correct parse gives `news.parse_correct` true and `news.applied` true; a wrong kind, a player outside the club and a model error give false and the feed goes on; the client payload has no labels; the span has no news text.

## 5. Docs

- [x] 5.1 Update ARCHITECTURE.md: the Evaluation section (grounding, `--explanations`), the Telemetry bullet (the `news.step` span and the `explanation.*` attributes), and the data note on labels. Also add the `--explanations` command to `backend/README.md`. Verify: no remaining "No custom telemetry" or "the parser must not read them" text that is now out of date.

## 6. Verify and approve

- [x] 6.1 Run the full backend suite (`python -m pytest -q` in `backend/`) and `openspec validate observable-evals`. Verify: both pass.
- [ ] 6.2 (Not run: the user accepted the deployed span results instead; 48 model calls.) With a configured model, run `python -m lineup_oracle.evals --explanations` once and read the failures. If they are false alarms (for example numbers written as words), adjust the rules and add a test for each. Verify: the report is attached to the PR description.
- [x] 6.3 Ask the user to deploy the branch (deploy-latest skill), then in Application Insights find a `news.step` row and a `lineup.predict` row with `explanation.grounded_ratio` in `customDimensions`. Verify: both found, or report that they were not.
- [x] 6.4 Human approval gate: summarize the results and stop for the user's approval. After approval, run the OpenSpec archive, then open a PR and merge it.
