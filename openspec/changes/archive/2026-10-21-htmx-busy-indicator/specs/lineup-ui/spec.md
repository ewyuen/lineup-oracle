# Spec Delta

## ADDED Requirements

### Requirement: In-page requests expose an accessible busy status
While an in-page request is pending, the UI SHALL announce that the page is updating and SHALL keep the last rendered content visible until a response is ready.

#### Scenario: A fixture or club selection is pending
- **WHEN** a fixture or club selection request is still processing
- **THEN** a visible, politely announced busy status indicates that the lineup is refreshing while the previously rendered workspace remains visible

#### Scenario: Another in-page action is pending
- **WHEN** a favourite, language, team-news, or retry request is still processing
- **THEN** the same busy status indicates that the request is in progress without hiding the current page content

#### Scenario: An in-page request completes
- **WHEN** an in-page request completes successfully or with an error response
- **THEN** the busy status is cleared and the response is handled using the existing success or error behavior

#### Scenario: Request duration is unknown
- **WHEN** a request is still pending
- **THEN** the busy status does not display a numeric completion percentage or imply measurable progress
