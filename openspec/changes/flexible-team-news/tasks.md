## 1. Branch

- [x] 1.1 Create the feature branch `feature/flexible-team-news` (done when proposing)

## 2. Parser and statuses (backend)

- [x] 2.1 Extend `ParsedNews` (`agents.py`) with `persons` and `translations`, and its `kind` with `recovered`, `cleared`, `fit`; update `PARSER_INSTRUCTIONS` (persons as written with the roster id when in the selected club, the club named, the three texts with the original kept verbatim)
- [x] 2.2 Add the three clearing kinds to `STATUS_OF_KIND` (`picking.py`) mapping to `available`
- [x] 2.3 Add `Pipeline.read` (`pipeline.py`): model call, person resolution (selected club, opponent, any club), the outcome rules of the design, all rejections with their messages, and the 200-character cap on each posted text (no translations needed for an applied status); keep `interpret` unchanged for the feed and evals
- [x] 2.4 Unit tests in `test_pipeline.py` with a fake client: injury, each clearing kind, opponent player, player of a club outside the match with a status, two players, unknown person, outsider, club-only post, status with no person, no person and no club, missing or over-long translation on a post, status line with no translations, model off, unreadable answer, `interpret` unchanged

## 3. API and feed

- [x] 3.1 `Feed.post` and `info` handling in `Feed.poll` (`ingest.py`): appended under the lock, no effect on shared availability or predictions, ignored by `changed`
- [x] 3.2 `/team_news` text path (`api.py`): `max_length=100` on `text`, call `Pipeline.read`, apply under `(session, match, resolved_club)` or post, add `news` to `LineupOut`, `news.outcome` span attribute
- [x] 3.3 Per-session post limit (`api.py`): a lock-guarded `{session_id: last_post_time}` map checked and updated just before `Feed.post`, 429 within 10 seconds, with a `shortcut:` comment for the unbounded map
- [x] 3.4 Tests in `test_api.py` and `test_ingest.py`: 100 vs 101 characters, applied and posted responses, recovery overriding a feed "out" for one session only, other sessions unchanged, rejected text leaves state and log unchanged, posted entry visible to another poller in each language, second post after 3 seconds is 429 and after 11 seconds is accepted (fake clock), another session and status lines unaffected, a 429 leaves the log unchanged, `changed` false for `info`, post survives a restart, structured path unchanged
- [x] 3.5 Confirm `submit_team_news` in the MCP adapter passes the new response through (add a test only if it filters fields)

## 4. Evals

- [x] 4.1 Extend the parser eval (`evals.py`) with a small fixed set of free-text cases (clearing kinds, opponent player, club-only line, outsider); keep the existing accuracy number comparable; report the person-listing cases (outsider, player plus club, club only) as their own accuracy figure so a prompt change that stops listing persons shows up; add a test for the new cases that does not need a model

## 5. UI

- [x] 5.1 `maxlength="100"` and updated help and placeholder text in `_TeamNews.cshtml`
- [x] 5.2 Add `News` to `LineupDto` and map it in the client; build the message in `OnPostNews` for applied (with club when not the selected one) and posted; new strings in en, es and zh-Hant, including recovered, cleared and fit
- [x] 5.3 `NewsEntry.From` treats `info` as applied for display; ticker shows posted lines without the not-applied mark
- [x] 5.4 UI tests in `LineupUiTests.cs`: error under the box, applied message, posted message, 100-character limit attribute, posted line without the mark

## 6. Docs and wrap-up

- [x] 6.1 Update ARCHITECTURE.md (`submit_team_news` text path and `news`, feed entry kinds and `changed`, UI section, telemetry `news.outcome`) and the backend README if it lists the text rules
- [x] 6.2 Run the full backend and UI test suites and fix failures
- [ ] 6.3 Human approval gate: summarize results and stop for the user's approval. After approval, run the OpenSpec archive, then open a PR from `feature/flexible-team-news` and merge it
