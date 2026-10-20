# Spec Delta

## Purpose

Delivers generated events to downstream stages in time order at an adjustable speed, so the pipeline behaves as if events arrive live.

## ADDED Requirements

### Requirement: Ordered replay
The replay SHALL yield events in ascending order of their scheduled time, with ties broken by event id.

#### Scenario: Order preserved
- **WHEN** a match's events are replayed
- **THEN** each event arrives no earlier than the one before it

### Requirement: Speed control
The replay SHALL scale waiting time by a speed factor, and a speed of zero SHALL deliver all events without waiting.

#### Scenario: Fast replay
- **WHEN** a 90-minute match is replayed at a speed that compresses it to under 2 minutes
- **THEN** the replay completes in under 2 minutes and every event is delivered

#### Scenario: Instant replay
- **WHEN** the speed is zero
- **THEN** all events are delivered immediately, in order, which tests can rely on

### Requirement: Late event injection
The replay SHALL accept an extra event while running and deliver it at the next point in the order that is not in the past.

#### Scenario: Injected injury
- **WHEN** a team-news injury event is injected mid-replay
- **THEN** subscribers receive it before any later-scheduled event and it is recorded in the log

### Requirement: Multiple subscribers
The replay SHALL deliver every event to each subscriber exactly once.

#### Scenario: Two subscribers
- **WHEN** two subscribers consume one replay
- **THEN** both receive the same events in the same order
