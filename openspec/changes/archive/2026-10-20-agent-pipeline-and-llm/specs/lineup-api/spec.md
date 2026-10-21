## MODIFIED Requirements

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

## ADDED Requirements

### Requirement: Free-text team news
The service SHALL accept a team-news submission that carries `text` and no player and kind, parse it (see the team-news-parsing capability), and answer with the updated predicted lineup. A submission that carries a player and a kind SHALL keep using the structured path.

#### Scenario: Text submission
- **WHEN** a text submission names a player of the club and a kind and the model works
- **THEN** the response is the updated lineup, without that player if the kind is injury or suspension

#### Scenario: Rejected text
- **WHEN** the text cannot be parsed or is rejected
- **THEN** the response is 422 with a message and the lineup and stored news are unchanged

## REMOVED Requirements

### Requirement: Free-text news is rejected for now
**Reason**: Free-text parsing now exists in this change.
**Migration**: Send free text to the same endpoint; without a configured model it is still rejected, with the message that text parsing is unavailable.
