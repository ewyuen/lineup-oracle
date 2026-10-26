# Spec Delta

## MODIFIED Requirements

### Requirement: In-memory state with no database
The service SHALL load the roster and events at startup, from `data/roster.json` and `data/events.jsonl` when present, otherwise generating them in memory from seed 42. A stored events file whose team-news items lack a non-empty `payload.text` or a non-empty Spanish or Traditional Chinese translation SHALL be rejected with an error that says to regenerate the events. Submitted availability SHALL live in memory and be lost on restart. Lineup prediction, team news and the read-only match operations SHALL use only this in-memory state and SHALL NOT depend on any database. The service MAY use an optional graph database for player-history reads only, and SHALL start and serve normally when it is absent or down.

#### Scenario: Missing events file
- **WHEN** the service starts and `data/events.jsonl` does not exist
- **THEN** it generates the events in memory and serves normally

#### Scenario: Deterministic prediction
- **WHEN** the same prediction is requested twice with no news in between
- **THEN** the two responses are identical

#### Scenario: Outdated or invalid localized event data
- **WHEN** the service loads an events file whose team-news item lacks `payload.text` or has a missing or empty Spanish or Traditional Chinese translation
- **THEN** startup fails with an error instructing the operator to regenerate the events file

#### Scenario: Prediction without the database
- **WHEN** the graph database is not configured or is unreachable
- **THEN** the service starts, and predictions, team news and match reads behave exactly as without a database

## ADDED Requirements

### Requirement: Player history endpoint
The service SHALL answer `POST /player_history` with a `question` or explicit filters and return the filters used, the retrieved events with their ids, the answer text and whether the LLM was used. A malformed or unanswerable request SHALL be rejected with 422 and a message in the `{"detail": message}` shape.

#### Scenario: History by explicit filters
- **WHEN** `POST /player_history` is sent with a known player id
- **THEN** the response has that player's events in time order, an answer text and `llm_used`

#### Scenario: Unknown player
- **WHEN** the player id is not in the roster
- **THEN** the response is 422 with a message naming it

#### Scenario: Database down
- **WHEN** the graph database is down and a history is requested
- **THEN** the response is the same events as with the database up
