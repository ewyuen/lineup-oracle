# Spec Delta

## ADDED Requirements

### Requirement: Fixture and club selection use asynchronous updates
Changing the selected fixture or club SHALL update the lineup and all dependent selection controls without a full-page navigation.

#### Scenario: Select a fixture
- **WHEN** the user selects a fixture
- **THEN** the page asynchronously shows that fixture, selects the favourite club when it participates or otherwise the home club, and updates the club controls, team-news form, lineup, and browser URL consistently

#### Scenario: Select a club
- **WHEN** the user selects either club in the current fixture
- **THEN** the active club, team-news form, lineup, and browser URL update asynchronously without replacing unrelated page content

### Requirement: Failed fixture or club predictions preserve the last successful view
When a prediction request caused by fixture or club selection fails, the page SHALL show the error without losing the last successfully displayed selection or lineup.

#### Scenario: Prediction service is unavailable
- **WHEN** the API cannot be reached after the user requests another fixture or club
- **THEN** the last successful selection and lineup remain visible, a service-unavailable banner appears, and retry targets the requested fixture and club

#### Scenario: Selection prediction is rejected
- **WHEN** the API rejects a prediction request caused by fixture or club selection
- **THEN** the API message is shown and the last successful selection and lineup remain visible

### Requirement: In-page UI updates use HTMX
UI actions that update the current page without changing document context SHALL use asynchronous HTMX requests and server-rendered HTML updates; true document navigation and file downloads MAY use normal requests.

#### Scenario: Add an in-page UI action
- **WHEN** a future UI action changes part of the current page
- **THEN** it uses HTMX to request and apply the server-rendered update without a full-page navigation

#### Scenario: Navigate to another document or download a file
- **WHEN** an action navigates to a different document context or downloads a file
- **THEN** it may use a normal browser request instead of an HTMX fragment update
