# p-start-scoring Specification

## Purpose
TBD - created by archiving change pstart-scoring-and-xi-optimizer. Update Purpose after archive.

## Requirements

### Requirement: Weighted P(start) score
The system SHALL compute a P(start) score between 0 and 1 for every player of a club as a fixed weighted sum of the player's squad quality for their position and the share of the club's last 5 matches the player started, multiplied by an availability factor. The weights SHALL be constants in code, and the score SHALL need no trained model.

#### Scenario: Score range
- **WHEN** P(start) is computed for any player
- **THEN** the score is between 0 and 1

#### Scenario: Better player scores higher
- **WHEN** two available players of the same position have the same recent-start share and one has higher position-relevant ratings
- **THEN** the better player has the higher P(start)

#### Scenario: Recent starts raise the score
- **WHEN** two available players of the same position have the same ratings and one started more of the last 5 matches
- **THEN** that player has the higher P(start)

#### Scenario: No history
- **WHEN** a club has no earlier matches
- **THEN** the recent-start share is a fixed neutral value for every player, and scoring still works

### Requirement: Availability factor
Availability SHALL be one of out, doubt or available. An out player SHALL have P(start) 0, a doubt player SHALL have the available score multiplied by 0.5, and an available player SHALL keep the score unchanged. A player with no availability entry SHALL count as available.

#### Scenario: Out player
- **WHEN** a player is marked out
- **THEN** the player's P(start) is 0

#### Scenario: Doubt player
- **WHEN** a player is marked doubt
- **THEN** the player's P(start) is half the score the same player would have as available

### Requirement: Recent XIs from events
The system SHALL provide a function that returns a club's starting XIs from `match_metadata` events of matches before a given match, oldest first, using only events of earlier matchdays.

#### Scenario: Only earlier matches
- **WHEN** recent XIs are requested for a match on matchday 4
- **THEN** only XIs from matchdays 1 to 3 are returned, and never the match's own XI

### Requirement: Deterministic scoring
Scoring SHALL give the same result for the same inputs.

#### Scenario: Same inputs
- **WHEN** scoring runs twice with the same roster, recent XIs and availability
- **THEN** the two result sets are identical
