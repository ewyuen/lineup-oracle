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
The service SHALL predict a club's starting XI for a match. It SHALL score players using only the club's XIs from earlier matchdays, apply the shared availability from the news feed together with the availability submitted for that match, club and session (the later event winning for a player), and pick the XI with the optimizer; a session with no submitted news SHALL receive the stored prediction. The response SHALL contain the formation, 11 players each with position, `p_start` and an explanation, alternatives per position, and `llm_used`, which SHALL be true only when the explanations were written by the model. The request SHALL carry a club, a match id, a mode (analyst or fan) and a language (en, es or zh-Hant), and an invalid value SHALL be rejected with 422. The mode and language SHALL shape the explanations when the model is used.

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

#### Scenario: Feed news is reflected
- **WHEN** the feed has applied an injury for a starter of a club
- **THEN** a prediction for that match and club, from a session with no submitted news, omits that player and is a legal XI

#### Scenario: Personal news with feed news
- **WHEN** a session has submitted news for the same match and club
- **THEN** its prediction applies the feed's news and its own news together, and other sessions' predictions are unchanged

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

### Requirement: Free-text team news
The service SHALL accept a team-news submission that carries `text` and no player and kind, parse it (see the team-news-parsing capability), and answer with the updated predicted lineup. A submission that carries a player and a kind SHALL keep using the structured path.

#### Scenario: Text submission
- **WHEN** a text submission names a player of the club and a kind and the model works
- **THEN** the response is the updated lineup, without that player if the kind is injury or suspension

#### Scenario: Rejected text
- **WHEN** the text cannot be parsed or is rejected
- **THEN** the response is 422 with a message and the lineup and stored news are unchanged

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

### Requirement: Restart the feed
The service SHALL let any caller restart the shared feed, which resets and begins at the first item as the feed's restart requirement says, and SHALL answer with the latest sequence number.

#### Scenario: Restart by one caller
- **WHEN** one caller restarts the feed
- **THEN** the next poll of every caller reports a restart marker
