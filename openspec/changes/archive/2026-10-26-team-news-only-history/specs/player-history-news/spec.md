# Spec Delta

## ADDED Requirements

### Requirement: History contains only team news
A player's history SHALL contain only team-news items: items the shared feed delivered for the player and statuses the requesting session submitted. It SHALL NOT contain shots, tackles, starts or any other event, whatever the filters or the question. The history request SHALL have no event-type filter; a request that sends one SHALL be rejected with 422.

#### Scenario: Other events are absent
- **WHEN** a player with shots, tackles and starts in the seeded events is asked for with no filters
- **THEN** every returned item has type `team_news`

#### Scenario: Question about shots
- **WHEN** a question asks about a player's shots
- **THEN** the answer is built from the player's team news only and no shot is returned or cited

#### Scenario: Type filter sent
- **WHEN** a request includes `types`
- **THEN** it is rejected with 422

#### Scenario: Graph and memory
- **WHEN** the graph is configured and answers
- **THEN** it returns the same team-news rows as memory, and the graph holds no shot, tackle or start data
