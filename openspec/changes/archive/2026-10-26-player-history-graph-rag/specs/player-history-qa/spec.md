# Spec Delta

## Purpose

Answers questions about what happened to a player from retrieved history, citing the events used. The answer never states more than the retrieved events support, and a plain summary is returned when no LLM is available.

## ADDED Requirements

### Requirement: Question or explicit filters
A request SHALL carry either a free-text `question` or explicit filters (player, event types, time range, match). With a question, the system SHALL ask the LLM to produce only those filters and SHALL validate them: unknown event types, malformed times, or a missing player SHALL be rejected. With explicit filters, no LLM SHALL be called to parse. A request with neither, or with both, SHALL be rejected with 422.

#### Scenario: Question parsed to filters
- **WHEN** the question "What happened to Pia Ash before matchday 3?" is asked and the LLM is available
- **THEN** the filters name Pia Ash and a time range ending at matchday 3's kickoff, and the history is retrieved with them

#### Scenario: Explicit filters
- **WHEN** a request gives a player id and the event type `injury`
- **THEN** the history is retrieved with no LLM call

#### Scenario: Neither or both
- **WHEN** a request has no question and no filters, or both a question and filters
- **THEN** the response is 422 and nothing is retrieved

#### Scenario: Unparseable question
- **WHEN** the LLM returns filters that fail validation
- **THEN** the response is 422 with a message asking for a player, and no answer is made up

### Requirement: Answer only from retrieved events
The answer SHALL be written only from the retrieved events and SHALL cite the id of each event it relies on. The response SHALL include the filters used, the retrieved events and the answer text. When nothing is retrieved, the answer SHALL say so and cite no events.

#### Scenario: Cited answer
- **WHEN** a player's history is asked and 3 events are retrieved
- **THEN** the answer text is based on those events, the response lists them, and every cited id is among them

#### Scenario: Nothing found
- **WHEN** the filters match no events
- **THEN** the answer says nothing was found and the cited ids are empty

### Requirement: Template answer without an LLM
When the LLM is not configured or fails (error, timeout or invalid output), the system SHALL still return the retrieved events with a template summary built from them, and the response SHALL say the LLM was not used. A failed LLM call SHALL NOT make an explicit-filters request fail.

#### Scenario: LLM unconfigured
- **WHEN** a history is requested with explicit filters and no LLM is configured
- **THEN** the response has the events, a template summary and `llm_used` false

#### Scenario: LLM fails while writing the answer
- **WHEN** the LLM errors after the events are retrieved
- **THEN** the response has the events and the template summary, with `llm_used` false

#### Scenario: Question with no LLM
- **WHEN** a free-text question is asked and no LLM is configured
- **THEN** the response is 422 with a message to give explicit filters instead

### Requirement: Synthetic data only
Answers SHALL contain only names and facts from the loaded synthetic data. The system SHALL NOT add outside knowledge about real players or clubs to an answer.

#### Scenario: Out-of-data question
- **WHEN** the question asks about a player not in the roster
- **THEN** the response is 422 naming that player as unknown
