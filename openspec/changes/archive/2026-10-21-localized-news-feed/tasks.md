# Tasks

## 1. Setup

- [x] 1.1 Confirm implementation is on `feature/localized-news-feed`; verify `git branch --show-current` reports that branch.

## 2. Generate and validate localized event data

- [x] 2.1 Add Spanish and Traditional Chinese templates aligned with the existing English team-news templates; store them in `payload.translations`, preserve `payload.text` and seeded template selection, and verify `backend/tests/test_synthetic_data.py` covers complete translations and deterministic generation.
- [x] 2.2 Validate loaded team-news events have a non-empty `payload.text` and non-empty `es` and `zh-Hant` translations; add tests for accepted current-format data and a clear regeneration error for stale or invalid files, then verify the relevant tests in `backend/tests/test_api.py` pass.

## 3. Localize the feed and API response

- [x] 3.1 Retain all three texts in each pollable feed entry while continuing to interpret only the English source text; verify `backend/tests/test_ingest.py` covers the locale map, applied and not-applied items, and unchanged one-time processing.
- [x] 3.2 Add validated `language` selection to `GET /news`, default to English, and project only the selected text into the existing `text` field; verify `backend/tests/test_api.py` covers each supported language, the default, invalid-language rejection, and unchanged polling semantics.

## 4. Update the UI and architecture

- [x] 4.1 Pass the selected language through the UI API client and page handler for background polls and the restart follow-up read; add or update tests in `ui/LineupOracle.Ui.Tests/LineupApiClientTests.cs` for the query string and `ui/LineupOracle.Ui.Tests/LineupUiTests.cs` for the language rendered in the HTMX poll form and used by the restart follow-up read.
- [x] 4.2 Update `ARCHITECTURE.md` and `backend/README.md` to document `payload.translations`, locale-filtered `/news` responses, and language-aware ticker polling; verify the documented request and response contracts match the implementation.

## 5. Integration and approval

- [x] 5.1 Run the complete backend suite (`python -m pytest -q` from `backend`) and UI suite (`dotnet test ui` from the repository root); verify both pass.
- [x] 5.2 After implementation and tests pass, summarize the results, include one Spanish and one Traditional Chinese item per kind (injury, suspension, doubt) for the approver to read, and stop for human approval; only after approval, archive the OpenSpec change, open a PR from `feature/localized-news-feed` to `main`, and merge it after approval.
