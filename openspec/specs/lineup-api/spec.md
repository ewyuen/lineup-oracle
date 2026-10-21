# lineup-api Specification

## Purpose
TBD - created by archiving change fastapi-and-mcp-server. Update Purpose after archive.

## Requirements

### Requirement: List matches
The service SHALL return the season's matches, each with its match id, matchday, home club and away club, ordered by matchday. It SHALL derive them from the loaded `match_metadata` events.

#### Scenario: Full fixture list
- **WHEN** the matches are listed with the default seeded data
- **THEN** 30 matches are returned, 3 per matchday, in matchday order

### Requirement: Get a match's actual XI
The service SHALL return, for a match id, the recorded starting XI and formation of both clubs, with player names and positions. It SHALL answer 404 for an unknown match id.

#### Scenario: Known match
- **WHEN** the XI of a known match is requested
- **THEN** both clubs' 11 players and formations are returned

#### Scenario: Unknown match
- **WHEN** an unknown match id is requested
- **THEN** the response is 404 with a message naming the match id

### Requirement: Predict a lineup
The service SHALL predict a club's starting XI for a match. It SHALL score players using only the club's XIs from earlier matchdays, apply the availability submitted for that match, club and session, and pick the XI with the optimizer. The response SHALL contain the formation, 11 players each with position, `p_start` and an explanation, alternatives per position, and `llm_used`, which SHALL be true only when the explanations were written by the model. The request SHALL carry a club, a match id, a mode (analyst or fan) and a language (en, es or zh-Hant), and an invalid value SHALL be rejected with 422. The mode and language SHALL shape the explanations when the model is used.

#### Scenario: Prediction shape
- **WHEN** a lineup is predicted for a club in a match
- **THEN** the response has a formation, 11 distinct players of that club with `p_start` between 0 and 1, up to 2 alternatives per position, and a boolean `llm_used`

#### Scenario: Own XI is never used
- **WHEN** a lineup is predicted for a match on matchday 4
- **THEN** only XIs from matchdays 1 to 3 influence the scores, and the match's own XI is not read

#### Scenario: Club not in the match
- **WHEN** the club is not one of the two clubs of the match
- **THEN** the response is 422 with a message naming the club and the match

#### Scenario: Unknown match
- **WHEN** the match id is unknown
- **THEN** the response is 404

#### Scenario: Model off keeps the old behaviour
- **WHEN** no model is configured
- **THEN** `llm_used` is false and the explanations are English templates

### Requirement: Template explanations
Each predicted player SHALL carry, when the model is not used, a short explanation built from a fixed English template from the player's data, naming the main reasons (recent starts, rating, availability). In analyst mode the template SHALL name the player's `p_start`; in fan mode it SHALL NOT show a `p_start` figure.

#### Scenario: Doubt player explained
- **WHEN** a picked player is marked doubt
- **THEN** the explanation says the player is a fitness doubt

#### Scenario: Fan template without numbers
- **WHEN** a lineup is predicted in fan mode with the model off
- **THEN** no explanation contains a `P(start)` figure

### Requirement: Submit structured team news
The service SHALL accept a structured team-news submission with a match id, club, player id and kind (injury, suspension or doubt). An injury or suspension SHALL mark the player out, and a doubt SHALL mark the player doubt, for that match and club only. The response SHALL be the updated predicted lineup. An unknown match, a player not in the club, or an invalid kind SHALL be rejected without changing any state.

#### Scenario: Injury removes a starter
- **WHEN** an injury is submitted for a player in the predicted XI
- **THEN** the returned lineup does not contain that player and is still a legal XI

#### Scenario: Other matches unaffected
- **WHEN** news is submitted for one match
- **THEN** a prediction for a different match is unchanged

#### Scenario: Sessions are separate
- **WHEN** news is submitted with one `session_id`
- **THEN** predictions with another `session_id`, or with the default, are unchanged

#### Scenario: Bad submission
- **WHEN** the player id does not belong to the club
- **THEN** the response is 422 naming the player and the club, and a following prediction is unchanged

#### Scenario: Latest news wins
- **WHEN** a doubt and then an injury are submitted for the same player and match
- **THEN** the player is out

### Requirement: In-memory state with no database
The service SHALL load the roster and events at startup, from `data/roster.json` and `data/events.jsonl` when present, otherwise generating them in memory from seed 42. Submitted availability SHALL live in memory and be lost on restart.

#### Scenario: Missing events file
- **WHEN** the service starts and `data/events.jsonl` does not exist
- **THEN** it generates the events in memory and serves normally

#### Scenario: Deterministic prediction
- **WHEN** the same prediction is requested twice with no news in between
- **THEN** the two responses are identical

### Requirement: Free-text team news
The service SHALL accept a team-news submission that carries `text` and no player and kind, parse it (see the team-news-parsing capability), and answer with the updated predicted lineup. A submission that carries a player and a kind SHALL keep using the structured path.

#### Scenario: Text submission
- **WHEN** a text submission names a player of the club and a kind and the model works
- **THEN** the response is the updated lineup, without that player if the kind is injury or suspension

#### Scenario: Rejected text
- **WHEN** the text cannot be parsed or is rejected
- **THEN** the response is 422 with a message and the lineup and stored news are unchanged
