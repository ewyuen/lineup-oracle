# Spec Delta

## MODIFIED Requirements

### Requirement: Predict a lineup
The service SHALL predict a club's starting XI for a match. It SHALL score players using only the club's XIs from earlier matchdays, apply the shared availability from the news feed together with the availability submitted for that match, club and session (the later event winning for a player), and pick the XI with the optimizer; a session with no submitted news SHALL receive the stored prediction unless it has a manual alternatives selection. The response SHALL contain the formation, 11 players each with position, `p_start` and an explanation, up to 4 alternatives per position, selectable non-starting candidates whose latest effective news is injury or doubt, and `llm_used`, which SHALL be true only when the explanations were written by the model. Each candidate SHALL include its player identity, position, availability kind, and whether it is manually included. The request SHALL carry a club, a match id, a mode (analyst or fan) and a language (en, es or zh-Hant), and an invalid value SHALL be rejected with 422. The mode and language SHALL shape the explanations when the model is used.

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
The service SHALL let a session manually include or remove a non-starting player whose latest effective team-news kind is injury or doubt from the alternatives for that match and club. This operation SHALL NOT change the player's availability or the predicted XI. Suspended players SHALL NOT be eligible.

#### Scenario: Include an injured player
- **WHEN** the session includes an injured non-starter in alternatives
- **THEN** the player appears in the alternatives for their position and remains injured

#### Scenario: Include a doubtful player
- **WHEN** the session includes a doubtful non-starter in alternatives
- **THEN** the player appears in the alternatives for their position and remains doubtful

#### Scenario: Remove a manual selection
- **WHEN** the session removes a manual selection
- **THEN** the player is no longer forced into the alternatives and the ranked alternatives are restored

#### Scenario: Suspended player is rejected
- **WHEN** the session attempts to include a suspended player
- **THEN** the service rejects the request without changing availability, the XI, or any alternatives selection

#### Scenario: Four alternatives per position
- **WHEN** a selected eligible player is added to a position that already has four alternatives
- **THEN** the newly selected player takes a place from the lowest-ranked alternative and no more than four are returned for that position

#### Scenario: Selection persists only in its session and context
- **WHEN** an alternative selection is made for one session, match, and club
- **THEN** later predictions in that same context reflect it, while other sessions, matches, and clubs remain unaffected

#### Scenario: Candidate kind changes to suspension
- **WHEN** the latest effective news for a manually included player becomes suspension
- **THEN** the player is no longer eligible and is omitted from the alternatives and selectable candidates
