# synthetic-match-events Specification

## Purpose
Generates reproducible, football-realistic synthetic match and team-news events that feed the pipeline, so no real match data is needed.

## Requirements

### Requirement: Deterministic generation
The generator SHALL produce identical events for the same seed and roster.

#### Scenario: Same seed
- **WHEN** the generator runs twice with the same seed and roster
- **THEN** the two event streams are identical

#### Scenario: Different seed
- **WHEN** the generator runs with a different seed
- **THEN** the results differ

### Requirement: Season fixtures
The generator SHALL create a fixture list of about 10 matchdays in which every club plays once per matchday.

#### Scenario: Fixtures complete
- **WHEN** fixtures are generated for 6 clubs
- **THEN** each matchday has 3 matches and no club appears twice in one matchday

### Requirement: Match event types
For each match the generator SHALL emit events of the types pass, shot, tackle, possession change and pressure, plus match metadata, each with a match minute, a club and a player where applicable.

#### Scenario: Event fields
- **WHEN** a match is generated
- **THEN** every event has an id, match id, type, minute, club and, for player events, a player id that belongs to that club

#### Scenario: Lineup consistency
- **WHEN** match metadata is emitted
- **THEN** it records the actual starting XI and formation of both clubs, 11 distinct players each

### Requirement: Team-news events
Before each kick-off the generator SHALL emit team-news events (injury, suspension, late fitness doubt) that affect who is available, marked as simulated. Each event SHALL carry free-text news in `payload.text`, written from seeded templates and naming the club and the affected player, with `player` left null so the text is the only source of the player.

#### Scenario: Text names the team
- **WHEN** a team-news event is generated for a club
- **THEN** its text mentions that club and a player from that club's roster

#### Scenario: Text matches the truth
- **WHEN** a team-news event says a player is injured or suspended
- **THEN** that player is not in the club's true XI in the match metadata

#### Scenario: Text is deterministic
- **WHEN** the generator runs twice with the same seed and roster
- **THEN** the team-news texts are identical

#### Scenario: Unavailable player does not start
- **WHEN** a player has an injury or suspension event for a match
- **THEN** that player is not in that match's starting XI

### Requirement: Realistic distributions
Generated match totals SHALL fall in plausible ranges per team and match.

#### Scenario: Plausible totals
- **WHEN** 100 matches are generated
- **THEN** the mean passes per team is between 300 and 600 and the mean shots per team is between 8 and 20

### Requirement: Rating-weighted true XI
The generator SHALL draw each club's true XI from its available players with a probability that rises with the player's position-relevant ratings, so higher-rated players start more often over a season. It SHALL stay deterministic for the same seed and roster.

#### Scenario: Better players start more
- **WHEN** a season is generated
- **THEN** across all clubs, players in the top third by position-relevant rating start more matches on average than players in the bottom third

#### Scenario: Still reproducible
- **WHEN** the generator runs twice with the same seed and roster
- **THEN** the true XIs are identical
