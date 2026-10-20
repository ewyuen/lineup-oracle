## ADDED Requirements

### Requirement: Rating-weighted true XI
The generator SHALL draw each club's true XI from its available players with a probability that rises with the player's position-relevant ratings, so higher-rated players start more often over a season. It SHALL stay deterministic for the same seed and roster.

#### Scenario: Better players start more
- **WHEN** a season is generated
- **THEN** across all clubs, players in the top third by position-relevant rating start more matches on average than players in the bottom third

#### Scenario: Still reproducible
- **WHEN** the generator runs twice with the same seed and roster
- **THEN** the true XIs are identical
