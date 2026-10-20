# synthetic-roster Specification

## Purpose
Provides the invented clubs and players that all other components use, with realistic squad structure and no real names, so the project stays within the synthetic-data rule.

## Requirements

### Requirement: Synthetic roster file
The system SHALL load clubs and players from a single roster file in which every club and player name is invented and each player has a shirt number, a position, a coarse archetype and a rating profile.

#### Scenario: Roster loads
- **WHEN** the roster file is loaded
- **THEN** it contains 6 clubs, each with a squad of at least 20 players covering goalkeeper, defender, midfielder and forward positions

#### Scenario: Invalid roster is rejected
- **WHEN** the roster file has a duplicate shirt number within a club or a player without a position
- **THEN** loading fails with an error naming the club and player

### Requirement: Club tactical profile
Each club SHALL have a tactical profile that names its usual formation and a style tag, for use as a formation prior.

#### Scenario: Profile present
- **WHEN** a club is read from the roster
- **THEN** its usual formation is one of the supported formations and its style tag is set

### Requirement: Seeded invented identities
The roster SHALL be generated from a seed with no real input, so no real club or player name is ever used.

#### Scenario: Same seed
- **WHEN** the roster is generated twice with the same seed
- **THEN** the two roster files are identical
