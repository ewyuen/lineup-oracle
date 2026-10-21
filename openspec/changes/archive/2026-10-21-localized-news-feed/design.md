# Design

## Context

See `proposal.md` for motivation. The synthetic generator currently picks among three English templates for each of three team-news kinds and stores the result in `payload.text`. The feed interprets that English text once and stores it in a shared in-memory log. `GET /news` returns that log unchanged, and the Razor Pages ticker does not send the page's existing `en`, `es`, or `zh-Hant` language selection.

The architecture contracts affected are generated event payloads, the feed log and polling API, and the UI ticker's poll request. The event parser continues to consume English source text; lineup selection and feed processing cadence are unchanged.

## Goals / Non-Goals

**Goals:**

- Make each generated news item available in all three supported languages before it is added to the pollable log.
- Keep the public poll response locale-specific without exposing the other variants.
- Preserve current English clients and the ticker's sequence, change-detection, and restart behavior.
- Fail clearly when stored events predate the required localized text data.

**Non-Goals:**

- Translating arbitrary user-submitted news or lineup explanations.
- Adding runtime translation calls, a translation service, or model dependencies.
- Changing event interpretation, availability updates, XI selection, or polling cadence.

## Decisions

1. **Keep a parallel localized template catalog.** Select the English template index using the existing random choice, then render the matching English, Spanish, and Traditional Chinese templates with the same club and player. Store only the two extra languages as `payload.translations = {es, zh-Hant}` and keep `payload.text` as the English source for the parser, the evals and existing consumers. English then has a single source, so nothing can disagree with it and no equality check is needed. This makes the translation deterministic and complete without adding model calls. Alternatives were a model translation call (adds latency, cost, and a failure mode) or deriving translations later from English text (requires brittle template matching).

2. **Validate event data before serving it.** When loading a stored event file, require every team-news event to have a non-empty `payload.text` and non-empty `payload.translations` entries for `es` and `zh-Hant`. Reject stale files with a clear regeneration message rather than falling back to English or publishing incomplete items. Event generation in memory naturally creates the required format.

3. **Keep complete variants in the shared feed log and project one at the API boundary.** Each log entry retains all three texts (English from `payload.text` plus the translations) so polling does not generate or mutate translations. `GET /news` accepts `language`, defaults it to `en`, and rejects unsupported values with 422. The response keeps the current item shape and puts the selected language's text in the existing `text` field, with no other variants; restart markers retain an empty text field. This preserves callers that omit the new query parameter and avoids exposing unused variants.

4. **Use the page's existing language preference for every news read.** The UI's HTMX poll form sends its selected language, and the API client and page handler pass it through to `GET /news`. The restart handler's follow-up news read uses the same language, and a scenario and test cover it. Language changes already replace the application shell and its ticker, so the newly rendered poll form uses the new language and cursor state.

5. **Do not change feed interpretation or effects.** `Feed.step` continues to pass only the English source text to the parser and to log an item whether it was applied or not. Translation availability is independent of whether the model is configured or whether the news can be applied.

## Risks / Trade-offs

- [A localized template can be accidentally omitted or misaligned with its English template] → Validate both translations at state load and test every kind/template combination. Tests cannot tell that a translation keeps the meaning (injury versus doubt), so the approver reads one Spanish and one Traditional Chinese item per kind before approving.
- [An existing stored event file lacks localized text] → Fail startup with a regeneration instruction; the current repository has no checked-in `events.jsonl`, so its normal startup path generates current-format events in memory.
- [A new client may request a locale unsupported by an older API] → The UI sends only its existing supported values, and omitted API language continues to mean English.

## Migration Plan

No database migration is needed. Regenerate any persisted `data/events.jsonl` with the updated generator before deploying; if an old file is encountered, startup validation reports that it must be regenerated. Rollback remains possible because `payload.text` is retained as English and additional event payload fields do not change the parser input. During rollout, callers that omit `language` continue to receive English.
