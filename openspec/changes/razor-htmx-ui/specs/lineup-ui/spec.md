## ADDED Requirements

### Requirement: Pick a fixture and a club
The page SHALL list the season's matches from the API, grouped or ordered by matchday, and let the user pick one match and then one of its two clubs. Picking a match and club SHALL show that club's predicted XI.

#### Scenario: Fixture list
- **WHEN** the page loads and the API is reachable
- **THEN** the picker lists every match with its matchday, home club and away club

#### Scenario: Prediction shown
- **WHEN** the user picks a match and a club
- **THEN** the page shows the formation and the 11 players grouped in lines for goalkeeper, defenders, midfielders and forwards, each with name, shirt number and explanation

### Requirement: Alternatives
The page SHALL show, for each position line, the alternatives returned by the API.

#### Scenario: Alternatives listed
- **WHEN** a predicted XI is shown
- **THEN** each position line lists its alternatives, none of whom is in the XI

### Requirement: Structured team news from the page
Each picked player SHALL have preset buttons for injury, suspension and doubt. Pressing one SHALL send a structured team-news submission for the selected match and club and replace the shown XI with the updated lineup, without a full page reload.

#### Scenario: Inject an injury
- **WHEN** the user presses the injury button on a picked player
- **THEN** the shown XI is replaced by the updated lineup, the player is no longer in it, and the rest of the page is unchanged

#### Scenario: Partial update
- **WHEN** an HTMX request is made for a lineup update
- **THEN** the response is only the lineup fragment, not the whole page

### Requirement: Free-text team news
The page SHALL have a text box and a submit button that send free-text team news for the selected match and club.

#### Scenario: Text rejected by the API
- **WHEN** the API rejects the text with a message
- **THEN** the message is shown next to the box and the shown XI is unchanged

### Requirement: Errors are visible and non-destructive
When the API answers with an error, the page SHALL show the API's message inline. When the API cannot be reached, the page SHALL show a banner that the service is unavailable. In both cases the last shown XI SHALL stay on screen.

#### Scenario: API down
- **WHEN** the API cannot be reached during a team-news submission
- **THEN** a service-unavailable banner is shown and the previous XI stays visible

#### Scenario: API error message
- **WHEN** the API answers 422 with a message
- **THEN** that message is shown and the previous XI stays visible

### Requirement: API address from configuration
The UI SHALL read the API base URL from configuration, defaulting to `http://127.0.0.1:8000`, and SHALL call only that service.

#### Scenario: Configured URL
- **WHEN** the setting `LineupApi:BaseUrl` is set
- **THEN** all API calls go to that address

### Requirement: No real-world imagery
The page SHALL NOT show crests, logos or photos. Clubs and players appear as text only.

#### Scenario: Text only
- **WHEN** any page is rendered
- **THEN** it contains no image elements for clubs or players
