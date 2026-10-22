## MODIFIED Requirements

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
