# Spec Delta

## ADDED Requirements

### Requirement: Lineup spans
When telemetry is configured, the API SHALL record one span named `lineup.predict` for each lineup prediction request and one named `lineup.team_news` for each team-news request, as children of the request span. Both SHALL carry `match_id` and `club`, and, when the request succeeds, `mode`, `language`, `formation` and `llm_used` (whether the model wrote the explanations). `lineup.predict` SHALL also carry `lineup.source`, `stored` when the club has no news of its own in the session and `personal` otherwise. `lineup.team_news` SHALL also carry `news.input` (`text` or `structured`) and, once the news is understood, `news.kind` (`injury`, `suspension` or `doubt`). A request that is rejected SHALL carry only the attributes known by then, with no placeholder values. The spans SHALL NOT carry prompts, reply text, explanations or session ids.

#### Scenario: Prediction traced
- **WHEN** a lineup is predicted for a club with no personal news
- **THEN** a `lineup.predict` span exists with `lineup.source` `stored`, the club, the match, the formation and `llm_used`

#### Scenario: Prediction after personal news
- **WHEN** a lineup is predicted in a session that has already submitted news for that club
- **THEN** the `lineup.predict` span has `lineup.source` `personal`

#### Scenario: Team news traced
- **WHEN** team news is submitted as text and parsed to a player and kind
- **THEN** a `lineup.team_news` span exists with `news.input` `text` and the parsed `news.kind`

#### Scenario: Structured team news traced
- **WHEN** team news is submitted with a player id and a kind
- **THEN** a `lineup.team_news` span exists with `news.input` `structured` and that `news.kind`

#### Scenario: Model fallback visible
- **WHEN** the model fails and template explanations serve the XI
- **THEN** the span has `llm_used` false and the response is still 200

#### Scenario: Rejected news
- **WHEN** team news text names no player of the club and the request is rejected with 422
- **THEN** the `lineup.team_news` span is marked as an error, carries `match_id` and `club`, and has no `news.kind`, `formation` or `llm_used`

### Requirement: No other custom telemetry
Apart from the two lineup spans, telemetry SHALL use only the standard instrumentation and the Agent Framework's built-in traces: no custom metrics, dashboards or events.

#### Scenario: Scope
- **WHEN** the telemetry code is reviewed
- **THEN** it contains the distro configuration call and the two lineup spans, and no custom metrics or events

## REMOVED Requirements

### Requirement: No custom telemetry
**Reason**: The two lineup spans are the first deliberate custom telemetry.
**Migration**: Replaced by "Lineup spans" and the narrower "No other custom telemetry".
