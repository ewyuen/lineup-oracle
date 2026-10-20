## ADDED Requirements

### Requirement: Legal XI per formation
For a given formation the optimizer SHALL select exactly 11 distinct players of the club that maximize total P(start), with one goalkeeper and the defender, midfielder and forward counts the formation requires (the middle bands of a formation count as midfielders). It SHALL be solved as a SciPy mixed-integer linear program.

#### Scenario: Position counts
- **WHEN** the optimizer runs for the formation 4-2-3-1
- **THEN** the XI has 1 goalkeeper, 4 defenders, 5 midfielders and 1 forward

#### Scenario: Out players are never picked
- **WHEN** a player has P(start) 0 because they are out
- **THEN** that player is not in the XI

#### Scenario: Best players are picked
- **WHEN** a position has more available players than slots
- **THEN** the picked players are those with the highest P(start) at that position

### Requirement: Formation choice by prior
The system SHALL solve the optimizer for each of the six supported formations and choose the formation with the highest value of total P(start) times the formation's prior. The prior SHALL be 1.0 for the club's usual formation and 0.85 for any other formation.

#### Scenario: Usual formation wins by default
- **WHEN** all players are available and the club's usual formation has total P(start) within 15 percent of the best other formation
- **THEN** the usual formation is chosen

#### Scenario: Squad shortage changes the formation
- **WHEN** injuries leave too few players of one position for the usual formation
- **THEN** another formation that can be filled is chosen and the result is still a legal XI

### Requirement: Alternatives per position
For each position the result SHALL list up to two alternatives: the non-out players of that position with the highest P(start) who were not picked.

#### Scenario: Alternatives are bench players
- **WHEN** the result is built
- **THEN** no alternative is in the XI, and each alternative has the same position as its group

### Requirement: Always returns an XI
The optimizer SHALL return a legal XI whenever some formation can be filled from the club's non-out players, and SHALL raise a clear error naming the club if none can.

#### Scenario: Not enough players
- **WHEN** no formation can be filled from the non-out players
- **THEN** the optimizer raises an error that names the club

### Requirement: Deterministic selection
The optimizer SHALL give the same XI for the same inputs, breaking ties by player id.

#### Scenario: Ties
- **WHEN** two players have identical P(start) and only one slot remains
- **THEN** the player with the lower id is picked, on every run
