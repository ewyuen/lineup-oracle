# lineup-evaluation Specification

## Purpose
TBD - created by archiving change agent-pipeline-and-llm. Update Purpose after archive.

## Requirements

### Requirement: Lineup score against a baseline
The project SHALL provide a command that reports, for held-out matches, how many of the 11 starters the pipeline predicted correctly on average, next to a baseline that predicts the club's XI from its previous match. It SHALL use the team news recorded for each match and only data from earlier matchdays, and SHALL print both scores and the number of matches.

#### Scenario: Report printed
- **WHEN** the evaluation runs on the default seeded data
- **THEN** it prints the pipeline score, the baseline score and the number of matches evaluated

#### Scenario: No leakage
- **WHEN** a match is evaluated
- **THEN** its own XI is never used to score it

#### Scenario: Deterministic
- **WHEN** the lineup evaluation runs twice on the same data without the model
- **THEN** the scores are identical

### Requirement: Parser accuracy
The command SHALL be able to run the news parser over the generated team-news events and report the share parsed to the right player and kind, using each event's answer labels only for scoring and never as parser input. It SHALL list the failures and SHALL say clearly when the model is not configured instead of reporting a score.

#### Scenario: Labels not leaked
- **WHEN** an event is parsed
- **THEN** only its text and the club are given to the parser

#### Scenario: Model not configured
- **WHEN** the parser evaluation runs with no model configured
- **THEN** it reports that it was skipped and why, and the lineup evaluation still runs
