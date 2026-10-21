# team-news-parsing Specification

## Purpose
TBD - created by archiving change agent-pipeline-and-llm. Update Purpose after archive.

## Requirements

### Requirement: Parse free-text team news
The service SHALL turn a free-text team-news line into one structured submission: a player of the requested club and a kind (injury, suspension or doubt). The player SHALL be chosen from the club's roster, and the result SHALL then go through the same availability path as a structured submission.

#### Scenario: Injury line
- **WHEN** a line saying a named player of the club is out with an injury is submitted for that club
- **THEN** that player is marked out for that match, club and session, and the updated lineup is returned

#### Scenario: Doubt line
- **WHEN** the text says a player of the club is a fitness doubt
- **THEN** that player is marked doubt

#### Scenario: Same result as the buttons
- **WHEN** a free-text line and a structured submission describe the same player and kind
- **THEN** the returned lineups are identical

### Requirement: Reject news that cannot be trusted
The service SHALL reject the text, with a message and no state change, when the model names a player that is not in the requested club's roster, when the text is about a different club, when the text names no player or no recognizable kind, or when the model does not answer in the expected form.

#### Scenario: Unknown player
- **WHEN** the model answers with a player id that is not in the club
- **THEN** the response is 422 with a message and the lineup and stored news are unchanged

#### Scenario: Other club
- **WHEN** the text is about a player of the other club in the match
- **THEN** the response is 422 with a message and nothing changes

#### Scenario: Unclear text
- **WHEN** the text names no player (for example "big game tonight")
- **THEN** the response is 422 asking for a player and a kind

### Requirement: Parsing is unavailable without the model
When the model is not configured, errors or times out, a free-text submission SHALL be rejected with a message that text parsing is unavailable and that the player and kind can be sent instead. The XI SHALL be unchanged and structured submissions SHALL keep working.

#### Scenario: Model off
- **WHEN** no model is configured and a text submission arrives
- **THEN** the response is 422 with the unavailable message

#### Scenario: Model fails
- **WHEN** the model call raises an error or exceeds its time limit
- **THEN** the response is 422 with the unavailable message and the lineup is unchanged

### Requirement: The model never changes the XI directly
The model's output SHALL only supply a player and a kind. The XI SHALL always come from the scoring and optimizer, never from model text.

#### Scenario: Model suggests a lineup
- **WHEN** the model's answer contains an XI or extra fields
- **THEN** they are ignored and only the validated player and kind are used
