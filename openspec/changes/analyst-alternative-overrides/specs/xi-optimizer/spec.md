# Spec Delta

## MODIFIED Requirements

### Requirement: Alternatives per position
For each position the result SHALL list up to four alternatives: the non-out players of that position with the highest P(start) who were not picked.

#### Scenario: Alternatives are bench players
- **WHEN** the result is built
- **THEN** no alternative is in the XI, each alternative has the same position as its group, and no position lists more than four
