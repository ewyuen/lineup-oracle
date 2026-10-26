# Spec Delta

## Purpose

Keeps a queryable graph of clubs, players, matches and timed events so the service can retrieve what happened to a player and when. The graph is a derived index of the roster and event files, which stay the source of truth.

## ADDED Requirements

### Requirement: Graph built from the roster and events
The system SHALL build a graph with Club, Player, Match and Event vertices from the roster and event files. Event vertices SHALL cover shot, tackle and team-news events only; passes, possession changes and pressure events are not player history and SHALL NOT be loaded. A club SHALL be linked to its players and to the matches it plays (home or away). A player SHALL be linked to each match they started and to each event that names them. An event SHALL be linked to its match. Rebuilding SHALL replace the previous graph, so loading twice gives the same graph.

#### Scenario: Seeded data
- **WHEN** the graph is built from the default seeded roster and events
- **THEN** it holds 6 clubs, every roster player, 30 matches and every shot, tackle and team-news event, each club-player and event-match link present, and no pass events

#### Scenario: Reload is idempotent
- **WHEN** the graph is built twice from the same files
- **THEN** the vertex and edge counts are the same after both builds

### Requirement: Team news is linked to its player
A team-news event names its player only in its payload, with the event's own player empty. The loader SHALL link such an event to the player of that club whose name matches, so team news appears in that player's history. Team news that matches no player of the club SHALL fail the load with a message naming the event.

#### Scenario: Injury news linked
- **WHEN** a team-news event names a player of its club
- **THEN** the event is linked to that player and has its kind and text

#### Scenario: Unknown player in news
- **WHEN** a team-news event names nobody in its club
- **THEN** the load fails with an error that names the event id

### Requirement: Deterministic match and event times
Each match SHALL have a kickoff time derived only from its matchday: a fixed season start plus one week per matchday, so every load gives the same times. Each event SHALL have an occurrence time equal to its match's kickoff plus its minute, except team news, whose offsets (48, 24 and 1) SHALL count as hours before kickoff. The event file SHALL NOT change.

#### Scenario: Kickoff by matchday
- **WHEN** matches of matchday 1 and matchday 2 are loaded
- **THEN** their kickoff times differ by exactly 7 days, and every match of a matchday has the same kickoff

#### Scenario: Team news precedes kickoff
- **WHEN** a team-news event with offset 48 is loaded
- **THEN** its occurrence time is 48 hours before its match's kickoff

### Requirement: Player history retrieval
The system SHALL return a player's events filtered by any combination of event types, a time range and a match, ordered by occurrence time then event id. The player SHALL be identified by id or by exact name, and a name matching more than one player SHALL be rejected as ambiguous. Each returned event SHALL carry its id, type, match, club, occurrence time and payload. Each match the player started SHALL also be returned as a `started` item at the match's kickoff, unless the event types filter is given and excludes `started`.

#### Scenario: Filter by type and range
- **WHEN** a player's `shot` events between two times are requested
- **THEN** only that player's shots inside the range are returned, in time order

#### Scenario: Ambiguous name
- **WHEN** a name shared by two players is requested
- **THEN** the request is rejected with a message listing the candidate ids

#### Scenario: Unknown player
- **WHEN** an id or name matches no player
- **THEN** the request is rejected with a message naming it

### Requirement: Same results from the graph or from memory
When the graph database is unreachable or not configured, the system SHALL answer the same retrieval from the in-memory events, with results identical to the graph's for the same filters. A graph error during a query SHALL fall back the same way and SHALL NOT surface as a failure.

#### Scenario: Database not configured
- **WHEN** no database address is configured and a player's history is requested
- **THEN** the result is returned from memory and equals what the graph returns for the same filters

#### Scenario: Database goes away
- **WHEN** the database fails during a query
- **THEN** the result is still returned from memory

### Requirement: Only fixed queries reach the database
Retrieval SHALL use fixed, parameterised query templates. Names, ids, types and times from a request or from an LLM SHALL only be passed as validated parameters and SHALL NOT be placed into query text.

#### Scenario: Hostile input
- **WHEN** a player name contains query syntax such as quotes or `}) DETACH DELETE`
- **THEN** it is treated as a name, matches no player, and the graph is unchanged
