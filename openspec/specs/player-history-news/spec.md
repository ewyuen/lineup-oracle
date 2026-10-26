# player-history-news Specification

## Purpose
Makes team news that arrives while the service runs part of a player's history, dated when it arrived and added once. The shared feed's news is visible to everyone; a visitor's own submissions are visible only in that visitor's session.

## Requirements

### Requirement: Feed news is dated when it is delivered
When the shared feed delivers a team-news item, that item's history entry SHALL carry the delivery time (UTC) as its time instead of its synthetic kickoff-based time. There SHALL be one entry per event id: later deliveries of the same item (the next lap of the feed, a loop reset, a feed restart) SHALL NOT change its time and SHALL NOT add a second entry. A team-news item the feed has not delivered SHALL keep its synthetic time. Delivered times SHALL be kept in memory only, so after the service restarts an item is dated by its next delivery.

#### Scenario: First delivery
- **WHEN** the feed delivers an item that names a player
- **THEN** that player's history lists the item once, at the delivery time

#### Scenario: Same item again
- **WHEN** the feed delivers the same item again on its next lap, or after a feed restart
- **THEN** the history still lists it once, at the first delivery time

#### Scenario: Not yet delivered
- **WHEN** a team-news item has not been delivered
- **THEN** it is listed at its synthetic time, as before

### Requirement: Applied manual news is added to the session's history
When a visitor's team-news submission is applied (a free-text line that names a player and a status, or a status button) it SHALL add an entry to that session's history of the player, dated when it was first submitted and carrying the kind and a text. An entry SHALL be identified by its session, the player and the kind: submitting the same kind for the same player again in the session SHALL NOT add an entry or change its time, and a different kind for that player SHALL add a new one. A submission that is rejected, a posted information line and a line that names no status SHALL NOT add an entry. The entries SHALL be kept in memory only and SHALL NOT be cleared by a feed restart.

#### Scenario: Status button
- **WHEN** a visitor marks a player as injured with the button
- **THEN** that visitor's history of the player lists an injury entry at the submission time

#### Scenario: Free-text line
- **WHEN** a visitor submits a free-text line that names a player and says the player is a doubt
- **THEN** that visitor's history of the player lists a doubt entry at the submission time

#### Scenario: Repeated submission
- **WHEN** the visitor marks the same player injured again
- **THEN** the history has one injury entry, still at the first submission time

#### Scenario: A later kind
- **WHEN** a player was marked suspended and the visitor then marks the player cleared
- **THEN** the history lists both entries

#### Scenario: Rejected or posted
- **WHEN** a submission is rejected, or is posted as information
- **THEN** no entry is added

### Requirement: Manual news is private to its session
An entry added by a visitor's submission SHALL appear only in history requested with that visitor's session id. History requested with another session id, or with none, SHALL show the shared history only. A request without a session id SHALL be treated as session `default`.

#### Scenario: Another visitor
- **WHEN** one visitor marks a player injured and another visitor asks for that player's history
- **THEN** the other visitor's history does not list the entry and the first visitor's does

### Requirement: History keeps the same rows from the graph or from memory
The delivered times and the session entries SHALL be applied to the rows of the retrieval whichever store supplied them, and the `from` and `to` time filters SHALL then be applied to the result, so a request returns the same rows whether the graph or memory supplied the base rows.

#### Scenario: Time range after delivery
- **WHEN** an item was delivered today and history is requested from the start of today
- **THEN** the item is included, and with a range that ends before today it is not, with the graph or without it

#### Scenario: Graph unavailable
- **WHEN** the graph database cannot answer
- **THEN** the same rows come from memory, including the delivered times and the session's entries

### Requirement: The history request carries the session
`POST /player_history` SHALL accept an optional `session_id` of at most 64 characters (default `default`). A longer value SHALL be rejected with 422 like any other invalid field. The UI SHALL send the visitor's session id with every history question.

#### Scenario: Question from the UI
- **WHEN** a visitor who submitted news asks about the player in the history chat
- **THEN** the request carries their session id and the answer can cite their entry

#### Scenario: Session id too long
- **WHEN** the request has a `session_id` of 65 characters
- **THEN** the response is 422 with a message

### Requirement: Questions can say today
The service SHALL give the model that turns a history question into filters the current UTC time, so a question such as "what happened today" or "this week" is turned into a time range from it. The filters SHALL still be validated by code as before.

#### Scenario: Today
- **WHEN** the question is "what happened to a player today?" and news was delivered today
- **THEN** the filters' range covers today and the answer can cite that news
