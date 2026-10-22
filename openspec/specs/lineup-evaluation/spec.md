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

### Requirement: Explanation grounding
The project SHALL check each explanation against the facts it was written from, with rules and no model call. An explanation is grounded when: every number in it is one of the player's `starts`, `played` or `p_start` as a whole percentage (one point either way); a player with status `doubt` is described as a doubt and a player who is available is not described as doubtful, injured or suspended; it names no other player of the club; and, in fan mode, it contains no percentage or `P(start)`. The check SHALL work for English, Spanish and Traditional Chinese.

#### Scenario: Wrong count
- **WHEN** the facts say 3 starts of 5 and the text says 4 of 5
- **THEN** the explanation is not grounded and the failed rule is `numbers`

#### Scenario: Doubt claimed for a fit player
- **WHEN** a player's status is available and the text calls the player a fitness doubt
- **THEN** the explanation is not grounded and the failed rule is `availability`

#### Scenario: Another player named
- **WHEN** the text for one player names a teammate
- **THEN** the explanation is not grounded and the failed rule is `names`

#### Scenario: Same result every time
- **WHEN** the check runs twice on the same text and facts
- **THEN** the result is identical

### Requirement: Grounding score
The evaluation command SHALL print the share of grounded explanations for the template explanations of every club-match, which must be all of them. With `--explanations` and a configured model it SHALL also print the share for the model's explanations (for the requested mode and language) and list each failure with its failed rules. With no model configured it SHALL say the model part was skipped and why, and the rest SHALL still run.

#### Scenario: Templates always grounded
- **WHEN** the evaluation runs on the default seeded data
- **THEN** it prints the template grounding share and it is 100%

#### Scenario: Model not configured
- **WHEN** `--explanations` is given and no model is configured
- **THEN** the model part is reported as skipped with the reason and the lineup evaluation still runs

#### Scenario: Failures listed
- **WHEN** the model writes an explanation that is not grounded
- **THEN** the report lists the player, the text and the failed rules
