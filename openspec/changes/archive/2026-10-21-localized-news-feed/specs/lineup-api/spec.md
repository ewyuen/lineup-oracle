# Spec Delta

## MODIFIED Requirements

### Requirement: Poll the news
The service SHALL return the recent news log for a caller that sends the last sequence number it saw and, optionally, a match and club. The caller MAY send a language (`en`, `es` or `zh-Hant`); when omitted, the service SHALL use `en`, and an unsupported value SHALL be rejected with 422. The response SHALL contain entries whose `text` field holds only the selected language's text, the latest sequence number, and whether anything new concerns that match and club. A poll SHALL only read the log and SHALL NOT process any item. An entry that is a restart marker SHALL count as concerning every match and club. Without a last-seen number the response SHALL carry the recent entries and report nothing changed.

#### Scenario: New news for the displayed club
- **WHEN** an applied item for the caller's match and club was delivered after its last-seen number
- **THEN** the response contains it and says the displayed club changed

#### Scenario: News for another club
- **WHEN** the only new entries are for other matches or clubs
- **THEN** the response contains them and says the displayed club did not change

#### Scenario: Not applied
- **WHEN** the only new entry for the caller's club was not applied
- **THEN** the entry is returned marked not applied and the displayed club is reported unchanged

#### Scenario: Restart marker
- **WHEN** the feed restarted after the caller's last-seen number
- **THEN** the response says the displayed club changed

#### Scenario: First poll
- **WHEN** a caller polls without a last-seen number
- **THEN** it receives the recent entries and nothing is reported changed

#### Scenario: Selected language
- **WHEN** a caller polls with `language=es` or `language=zh-Hant`
- **THEN** each news entry contains only its Spanish or Traditional Chinese text, respectively, while sequence and change fields retain their usual meaning

#### Scenario: Default language
- **WHEN** a caller omits the language
- **THEN** each news entry contains English text

#### Scenario: Unsupported language
- **WHEN** a caller supplies an unsupported language
- **THEN** the service rejects the poll with 422

### Requirement: In-memory state with no database
The service SHALL load the roster and events at startup, from `data/roster.json` and `data/events.jsonl` when present, otherwise generating them in memory from seed 42. A stored events file whose team-news items lack a non-empty `payload.text` or a non-empty Spanish or Traditional Chinese translation SHALL be rejected with an error that says to regenerate the events. Submitted availability SHALL live in memory and be lost on restart.

#### Scenario: Missing events file
- **WHEN** the service starts and `data/events.jsonl` does not exist
- **THEN** it generates the events in memory and serves normally

#### Scenario: Deterministic prediction
- **WHEN** the same prediction is requested twice with no news in between
- **THEN** the two responses are identical

#### Scenario: Outdated or invalid localized event data
- **WHEN** the service loads an events file whose team-news item lacks `payload.text` or has a missing or empty Spanish or Traditional Chinese translation
- **THEN** startup fails with an error instructing the operator to regenerate the events file
