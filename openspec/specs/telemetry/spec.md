# telemetry Specification

## Purpose
Defines trace export from the API and UI to Application Insights, so per-stage timing and model failures with the template fallback are visible on Azure, without affecting local runs.

## Requirements

### Requirement: Traces exported when configured
The API and the UI SHALL export OpenTelemetry traces to Application Insights when `APPLICATIONINSIGHTS_CONNECTION_STRING` is set.

#### Scenario: Request traced
- **WHEN** a prediction request reaches the deployed UI
- **THEN** a trace linking the UI request and the API request appears in Application Insights

#### Scenario: Model failure visible
- **WHEN** a model call fails and the template explanation serves the XI
- **THEN** the failure is recorded on the trace and the response is still 200

### Requirement: Silent when not configured
Without the connection string, the API and the UI SHALL start and behave exactly as before, with no export attempts and no errors.

#### Scenario: Local run
- **WHEN** the API or UI starts with the variable unset
- **THEN** telemetry setup is skipped and all existing tests pass

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
Apart from the `lineup.predict`, `lineup.team_news` and `news.step` spans and their attributes, telemetry SHALL use only the standard instrumentation and the Agent Framework's built-in traces: no custom metrics, dashboards or events.

#### Scenario: Scope
- **WHEN** the telemetry code is reviewed
- **THEN** it contains the distro configuration call and the three spans, and no custom metrics or events

### Requirement: Explanation grounding on lineup spans
When the model wrote the explanations (`llm_used` true), the `lineup.predict` and `lineup.team_news` spans SHALL also carry `explanation.grounded_ratio`, the share of the listed players whose explanation is grounded (0 to 1), and `explanation.failed_rules`, the distinct names of the rules that failed, sorted. It SHALL be observe-only: the response, the XI and the explanations SHALL be the same with or without the attributes. The attributes SHALL NOT be set when the template wrote the explanations.

#### Scenario: Grounded explanations
- **WHEN** the model writes explanations that match the facts
- **THEN** the span has `explanation.grounded_ratio` 1 and an empty `explanation.failed_rules`

#### Scenario: Ungrounded explanation still served
- **WHEN** the model writes one explanation with a wrong count
- **THEN** the response is 200 with that text unchanged, and the span has a ratio below 1 and `numbers` in `explanation.failed_rules`

#### Scenario: Template fallback
- **WHEN** the template wrote the explanations
- **THEN** the span has no `explanation.*` attributes

### Requirement: News step span
When telemetry is configured, each news item the shared feed delivers SHALL be recorded as a span named `news.step`, with no parent, carrying `match_id`, `club`, `news.applied` (whether the item was understood and applied) and `news.parse_correct` (whether the parsed player and kind equal the event's answer labels). The labels SHALL be compared only after the parser has answered and SHALL NOT be given to the parser. A parse that fails SHALL record `news.parse_correct` false. The span SHALL NOT carry the news text.

#### Scenario: Correct parse
- **WHEN** the feed parses an item to the player and kind in its labels
- **THEN** the `news.step` span has `news.parse_correct` true and `news.applied` true

#### Scenario: Wrong or failed parse
- **WHEN** the parser returns a different kind, a player outside the club or an error
- **THEN** `news.parse_correct` is false and the feed carries on with the next item

#### Scenario: Labels not leaked
- **WHEN** the feed calls the parser
- **THEN** only the text and the club are given to it
