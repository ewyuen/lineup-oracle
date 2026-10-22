# Spec Delta

## MODIFIED Requirements

### Requirement: Predict a lineup
The service SHALL predict a club's starting XI for a match. It SHALL score players using only the club's XIs from earlier matchdays, apply the shared availability from the news feed together with the availability submitted for that match, club and session (the later event winning for a player), and pick the XI with the optimizer; a session with no submitted news SHALL receive the stored prediction, to which any manual alternatives selection SHALL be applied on a copy so other sessions' predictions are unchanged. The response SHALL contain the formation, 11 players each with position, `p_start`, a status (available, doubt or out) and an explanation, up to 4 alternatives per position with the same fields, selectable non-starting candidates whose latest effective news is injury or doubt, and `llm_used`, which SHALL be true only when the explanations were written by the model. Every listed player, including a manually included one, SHALL have an explanation, and the explanation of an injured player SHALL say so instead of calling them a likely starter. Each candidate SHALL include its player id, name, number, position, availability kind, and whether it is manually included. The request SHALL carry a club, a match id, a mode (analyst or fan) and a language (en, es or zh-Hant), and an invalid value SHALL be rejected with 422. The mode and language SHALL shape the explanations when the model is used.

#### Scenario: Prediction shape
- **WHEN** a lineup is predicted for a club in a match
- **THEN** the response has a formation, 11 distinct players of that club with `p_start` between 0 and 1, up to 4 alternatives per position, eligible non-starting injured or doubtful candidates, and a boolean `llm_used`

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

#### Scenario: Manual alternatives do not change the XI
- **WHEN** a session has manually included an eligible injured or doubtful player
- **THEN** its next prediction preserves the same XI and availability while reflecting that selection in the alternatives

## ADDED Requirements

### Requirement: Manage session-scoped alternative selections
The service SHALL let a session manually include or remove a non-starting player whose latest effective team-news kind is injury or doubt from the alternatives for that match and club, through `POST /alternatives` with the prediction request fields, a player id and `included` (true or false), returning the updated lineup. Repeating a request SHALL leave the same state. This operation SHALL NOT change the player's availability or the predicted XI. Suspended players SHALL NOT be eligible. An unknown match SHALL be rejected with 404. A club not in the match, a player not of the club, a starter, a player without injury or doubt news, a suspended player, or an include when the position already lists four alternatives and the player is not one of them SHALL be rejected with 422 and a message, without changing any state. A removal SHALL always be accepted and removing an absent selection SHALL change nothing. A stored selection that is not currently valid (suspended, recovered or in the XI) SHALL be left out of the response and kept until removed.

#### Scenario: Include an injured player
- **WHEN** the session includes an injured non-starter in alternatives
- **THEN** the player appears in the alternatives for their position and remains injured

#### Scenario: Include a doubtful player
- **WHEN** the session includes a doubtful non-starter in alternatives
- **THEN** the player appears in the alternatives for their position and remains doubtful

#### Scenario: Include a player who is already a natural alternative
- **WHEN** the session includes a doubtful non-starter who already ranks among the position's alternatives
- **THEN** the player stays listed in rank order, is marked manually included, and no other alternative is displaced

#### Scenario: Remove a manual selection
- **WHEN** the session removes a manual selection
- **THEN** the player is no longer marked included, is listed only if they rank among the position's natural alternatives, and the other selections are kept

#### Scenario: Repeating a request
- **WHEN** the same include or remove request is sent twice
- **THEN** the second response equals the first and no error is returned

#### Scenario: Ineligible player is rejected
- **WHEN** the session includes a starter, a player with no injury or doubt news, or a player of another club
- **THEN** the response is 422 and no state changes


#### Scenario: Selection became a starter
- **WHEN** a selected doubtful player is promoted into the XI by a starter's injury
- **THEN** the player is not listed as an alternative, and the session can still remove the selection

#### Scenario: Suspended player is rejected
- **WHEN** the session attempts to include a suspended player
- **THEN** the service rejects the request without changing availability, the XI, or any alternatives selection

#### Scenario: Four alternatives per position
- **WHEN** a selected eligible player is added to a position that already lists four alternatives and is not one of them
- **THEN** the response is 422 with a message, the four alternatives and all selections are unchanged, and no more than four are ever returned for a position

#### Scenario: Selection persists only in its session and context
- **WHEN** an alternative selection is made for one session, match, and club
- **THEN** later predictions in that same context reflect it, while other sessions, matches, and clubs remain unaffected

#### Scenario: Candidate kind changes to suspension
- **WHEN** the latest effective news for a manually included player becomes suspension
- **THEN** the player is no longer eligible and is omitted from the alternatives and selectable candidates
