# Spec Delta

## ADDED Requirements

### Requirement: Optional player-history chat panel
The UI SHALL show an "Ask about a player" panel under the Team news panel only when the setting `PlayerHistory:Enabled` is true; the default SHALL be false. The panel SHALL have a text box limited to 300 characters and an Ask button. When the setting is false the UI SHALL render no panel and SHALL make no player-history request.

#### Scenario: Panel off by default
- **WHEN** the page loads with `PlayerHistory:Enabled` unset
- **THEN** no player-history panel is rendered

#### Scenario: Panel on
- **WHEN** the page loads with `PlayerHistory:Enabled` true
- **THEN** the panel appears under Team news with a question box limited to 300 characters

### Requirement: Single-turn history questions
Submitting a question SHALL send it alone to the API's `/player_history` as `question`, without earlier messages, and SHALL show the question and the result in the panel without reloading the page, replacing any earlier question and result so only one exchange is shown. An empty or blank question SHALL NOT be sent.

#### Scenario: Ask a question
- **WHEN** the user submits "What did Saka do before matchday 3?"
- **THEN** one request carrying only that question is sent, and the panel shows the question followed by the answer

#### Scenario: Second question replaces the first
- **WHEN** the user asks a second question after an answer is shown
- **THEN** the panel shows only the second question and its answer

#### Scenario: Blank question
- **WHEN** the user submits an empty or whitespace-only question
- **THEN** no request is sent and the panel is unchanged

### Requirement: Answers show their source and events
Each answer SHALL show the API's answer text, a marker saying whether the model wrote it (`llm_used`) or a template did, and the retrieved events (time, type, match, and the text of team news) in a collapsible list. When no events are returned the list SHALL be omitted.

#### Scenario: Answer with events
- **WHEN** the API returns an answer with events and `llm_used` true
- **THEN** the panel shows the answer text, the AI marker and a collapsible list of those events

#### Scenario: Nothing found
- **WHEN** the API returns no events
- **THEN** the panel shows the answer text and no event list

### Requirement: History errors replace the answer
When the API rejects a question or cannot be reached, the UI SHALL show an error message in place of the answer and SHALL leave the lineup and the news unchanged.

#### Scenario: Question rejected
- **WHEN** the API answers 422 with a detail message
- **THEN** the panel shows that message as an error and the question box stays usable

#### Scenario: API unreachable
- **WHEN** the API cannot be reached
- **THEN** the panel shows an unavailable message and the lineup is unchanged

### Requirement: Transcript persists across in-page updates
The question and answer SHALL survive club and fixture selection, news polling, team-news submission and other lineup updates. A language change SHALL clear it and relabel the panel in the new language.

#### Scenario: Lineup update keeps exchange
- **WHEN** the user has asked a question and then selects another club
- **THEN** the panel still shows the question and answer

#### Scenario: Language change clears exchange
- **WHEN** the user switches the language
- **THEN** the panel is shown in the new language with no question or answer

### Requirement: Localized panel labels
The panel's labels, placeholder, markers and messages SHALL be localized in English, Spanish and Traditional Chinese. Answer text and event text SHALL be shown as the API returns them.

#### Scenario: Spanish labels
- **WHEN** the language is Spanish and the panel is enabled
- **THEN** the panel heading, placeholder and button are in Spanish
