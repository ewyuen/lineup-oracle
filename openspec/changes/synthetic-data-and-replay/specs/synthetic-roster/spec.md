# Spec Delta

## Purpose

Provides the invented clubs and players that all other components use, with realistic squad structure and no real names, so the project stays within the synthetic-data rule.

## ADDED Requirements

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

### Requirement: Aliasing without publishing real identities
The aliasing step SHALL produce the committed roster from a private input and SHALL keep the real-to-synthetic mapping only in the gitignored private folder.

#### Scenario: Mapping stays private
- **WHEN** the aliasing step finishes
- **THEN** the committed roster contains no real club or player name and the mapping file exists only under `private/`

#### Scenario: Name collision with a real name
- **WHEN** a generated name equals a name in the private real-name list
- **THEN** the aliasing step generates a different name
