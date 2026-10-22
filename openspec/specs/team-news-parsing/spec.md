# team-news-parsing Specification

## Purpose
TBD - created by archiving change agent-pipeline-and-llm. Update Purpose after archive.

## Requirements

### Requirement: Parse free-text team news
The service SHALL read a free-text team-news line (at most 100 characters, in any language) into: the persons it names, the club it names if any, an optional status, and the line in English, Spanish and Traditional Chinese. The status SHALL be one of injury, suspension, doubt, recovered (an injury healed), cleared (a suspension served) or fit (a doubt resolved). Injury and suspension SHALL mark a player out, doubt SHALL mark a player doubt, and recovered, cleared and fit SHALL mark a player available. A line that names a player and a status SHALL then go through the same availability path as a structured submission, and a clearing status SHALL replace an earlier "out" or "doubt" for that player, whether it came from the feed or from the same session. A suspended player SHALL be made available only by a cleared status; any other status for a suspended player SHALL be rejected with a message naming the player, and a recovered or fit status for a player who is not injured or doubtful SHALL still be applied as before.

#### Scenario: Injury line
- **WHEN** a line saying a named player of the club is out with an injury is submitted for that club
- **THEN** that player is marked out for that match, club and session, and the updated lineup is returned

#### Scenario: Doubt line
- **WHEN** the text says a player of the club is a fitness doubt
- **THEN** that player is marked doubt

#### Scenario: Recovery clears an injury
- **WHEN** a player is out and the text says the player has recovered
- **THEN** the player is available again and may return to the predicted XI

#### Scenario: Recovery overrides the feed
- **WHEN** the feed has marked a player out and a session submits that the player is fit again
- **THEN** that session's XI treats the player as available and other sessions are unchanged

#### Scenario: Same result as the buttons
- **WHEN** a free-text line and a structured submission describe the same player and kind
- **THEN** the returned lineups are identical

#### Scenario: Other status for a suspended player
- **WHEN** a player is suspended and the text says the player is a fitness doubt or has recovered
- **THEN** the response is 422 with a message naming the player and the suspension stays

#### Scenario: Suspension served
- **WHEN** a player is suspended and the text says the player has served the ban
- **THEN** the player is available again

### Requirement: Reject news that cannot be trusted
The service SHALL reject the text, with a message and no state change and no broadcast, when a named person does not resolve to a roster player (message: player not found, naming the person), when the text names no person and no known club, or when the model does not answer in the expected form. A person who is not a player, such as an owner or a buyer, SHALL be treated as a player that was not found.

#### Scenario: Unknown player
- **WHEN** the text names a person who is in no club's roster
- **THEN** the response is 422 with a player-not-found message and the lineup, stored news and the news log are unchanged

#### Scenario: Outsider named
- **WHEN** the text says an outsider proposes to buy a club
- **THEN** the response is 422 with a player-not-found message naming the outsider and nothing is posted

#### Scenario: Other club
- **WHEN** the text gives a status to a player of a club that is not in the match
- **THEN** the response is 422 with a message and nothing changes (a player of the other club of the match is found and applied instead)

#### Scenario: Unclear text
- **WHEN** the text names no person and no club (for example "big game tonight")
- **THEN** the response is 422 asking for a player or a team

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

### Requirement: News without a status is posted, not applied
A line that names exactly one resolved player but no status, or names no person but names a known club, SHALL be posted to the shared news log as an informational entry carrying the line in all three languages, and SHALL NOT change any availability, stored prediction or lineup. A line that names a player and a status SHALL NOT be posted. Each of the three texts SHALL be non-empty and at most 200 characters after trimming; a line whose answer lacks one, or has one too long, SHALL be rejected with a message and nothing posted. A line that is applied, not posted, SHALL NOT need the translations.

#### Scenario: Missing translation
- **WHEN** a line would be posted and the answer has no Spanish text
- **THEN** the response is 422 with a message and nothing is posted

#### Scenario: Translation too long
- **WHEN** a line would be posted and one of the three texts is longer than 200 characters
- **THEN** the response is 422 with a message and nothing is posted

#### Scenario: Status line without translations
- **WHEN** a line names a player and a status and the answer has no translations
- **THEN** the status is applied as usual

#### Scenario: Transfer news about a player
- **WHEN** a line says a named player of a club receives a transfer proposal
- **THEN** the line is posted to the news log and no lineup changes

#### Scenario: News about a club
- **WHEN** a line names a club and no person
- **THEN** the line is posted to the news log and no lineup changes

#### Scenario: Status line stays private
- **WHEN** a line names a player and a status
- **THEN** it changes that session's availability only and no entry is added to the news log

### Requirement: Players are found across clubs
Every person a line names SHALL resolve to a roster player, looked up by full name in the selected club first, then the other club of the match, then any club. A line that names more than one distinct resolved player SHALL be rejected with a message saying one player per line.

#### Scenario: Player of the opponent
- **WHEN** a line about a player of the other club of the match is submitted for the selected club
- **THEN** the player is found in the other club and the status is applied to that club's availability for that match

#### Scenario: Player of a club outside the match with a status
- **WHEN** a line gives a status to a player whose club does not play in the selected match
- **THEN** the line is rejected with a message naming the player and the club, and nothing changes

#### Scenario: Two players
- **WHEN** a line names two different players
- **THEN** the line is rejected with a message saying one player per line and nothing changes
