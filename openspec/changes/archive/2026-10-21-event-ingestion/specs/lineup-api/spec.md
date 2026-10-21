# Spec Delta

## ADDED Requirements

### Requirement: Poll the news
The service SHALL return the recent news log for a caller that sends the last sequence number it saw and, optionally, a match and club: the entries, the latest sequence number, and whether anything new concerns that match and club. A poll SHALL only read the log and SHALL NOT process any item. An entry that is a restart marker SHALL count as concerning every match and club. Without a last-seen number the response SHALL carry the recent entries and report nothing changed.

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

### Requirement: Restart the feed
The service SHALL let any caller restart the shared feed, which resets and begins at the first item as the feed's restart requirement says, and SHALL answer with the latest sequence number.

#### Scenario: Restart by one caller
- **WHEN** one caller restarts the feed
- **THEN** the next poll of every caller reports a restart marker

## MODIFIED Requirements

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
