# lineup-ui Specification

## Purpose

TBD - Update Purpose after archive.

## Requirements

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
- **THEN** the shown XI is replaced by the updated lineup, the player is no longer in it, a message names the player and the news, and the rest of the page is unchanged

#### Scenario: Partial update
- **WHEN** an HTMX request is made for a lineup update
- **THEN** the response is only the lineup fragment, not the whole page

### Requirement: Free-text team news
The page SHALL have a text box and a submit button that send free-text team news for the selected match and club. The box SHALL accept at most 100 characters. After a submission the page SHALL say what happened: that a player's status was updated (naming the player and, when it is not the selected club, the club), or that the line was posted to the news feed.

#### Scenario: Text rejected by the API
- **WHEN** the API rejects the text with a message (for example player not found)
- **THEN** the message is shown under the box and the shown XI is unchanged

#### Scenario: Status applied
- **WHEN** the API reports that a status was applied
- **THEN** the page names the player and the new status, including a clearing status such as recovered, and shows the lineup

#### Scenario: Line posted
- **WHEN** the API reports that the line was posted
- **THEN** the page says it was posted to the news feed and the shown XI is unchanged

#### Scenario: Length limit
- **WHEN** a visitor types in the box
- **THEN** no more than 100 characters can be entered

### Requirement: Errors are visible and non-destructive
When the API answers with an error, the page SHALL show the API's message inline. When the API cannot be reached, the page SHALL show a banner that the service is unavailable. In both cases the last shown XI SHALL stay on screen.

#### Scenario: API down
- **WHEN** the API cannot be reached during a team-news submission
- **THEN** a service-unavailable banner with a retry button is shown and the previous XI stays visible

#### Scenario: Retry
- **WHEN** the user presses retry and the API is reachable again
- **THEN** the banner is removed and the lineup is loaded again

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

### Requirement: One session id per browser
The UI SHALL create a random session id on the first visit, keep it in a cookie, and send it as `session_id` with every prediction and team-news call, so each visitor's news stays separate.

#### Scenario: Same id on every call
- **WHEN** the same browser makes a prediction and then a team-news call
- **THEN** both calls carry the same `session_id`

#### Scenario: Different browsers
- **WHEN** two browsers each open the page for the first time
- **THEN** they send different `session_id` values

### Requirement: Only data the API provides
The page SHALL show only fields the API returns (club and player names, shirt numbers, position, formation, `p_start`, explanation, alternatives, `llm_used`, matchday). It SHALL NOT show invented figures or panels such as model confidence, latency, win probability, kickoff time, venue or heatmaps.

#### Scenario: No invented data
- **WHEN** a lineup is shown
- **THEN** every number on the page comes from the API response

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

### Requirement: Shared news ticker
The page SHALL show a ticker of the shared news above the busy status, containing the same feed events and posted lines for every visitor and selected match and club, with each message shown in that visitor's selected language. Items SHALL move from right to left. The text of each item SHALL be available to assistive technology, a feed item that was not applied SHALL be visibly marked, a posted line SHALL be shown without that mark, and a restart of the feed SHALL show as a marker. With a reduced-motion preference the items SHALL be shown as a static list.

#### Scenario: News arrives
- **WHEN** a new item is delivered to the feed
- **THEN** it appears in every open page's ticker in that page's selected language and moves from right to left

#### Scenario: Same for everyone
- **WHEN** two visitors view different matches or select different languages
- **THEN** both tickers show the same feed events, with each message rendered in the visitor's selected language

#### Scenario: Item not applied
- **WHEN** an item could not be used
- **THEN** it is shown with a visible not-applied mark

#### Scenario: Posted line
- **WHEN** a visitor posts a line
- **THEN** it appears in every open page's ticker without a not-applied mark and does not refetch the lineup

#### Scenario: Reduced motion
- **WHEN** the user prefers reduced motion
- **THEN** the items are shown without moving

### Requirement: Background news polling
While the page is open, it SHALL ask for the news every 10 seconds, sending the last sequence number it saw, the displayed match and club, and the selected language (`en`, `es` or `zh-Hant`). A poll SHALL NOT show the busy status, and a failed poll SHALL leave the ticker and lineup as they are, with the next poll tried at the usual time. A poll with nothing new SHALL NOT change what is on screen.

#### Scenario: Silent poll
- **WHEN** a background poll is pending
- **THEN** the busy status is not shown

#### Scenario: Localized poll
- **WHEN** a background poll is sent
- **THEN** it requests news text in the page's selected language

#### Scenario: Restart in the selected language
- **WHEN** the visitor restarts the feed
- **THEN** the entries shown afterwards are in the page's selected language

#### Scenario: Nothing new
- **WHEN** a poll returns no new items
- **THEN** the ticker does not move or restart

#### Scenario: Poll fails
- **WHEN** a poll fails
- **THEN** the ticker and lineup stay as they were

### Requirement: Refresh the lineup only for the displayed club
The page SHALL refresh the lineup, for the current selection and without adding to browser history, when a poll reports that the displayed match and club changed. News for any other match or club SHALL NOT refresh it. After a selection or language change the page SHALL NOT refresh because of news seen before the change.

#### Scenario: News for the displayed club
- **WHEN** a poll reports that the displayed club changed
- **THEN** the lineup is refreshed and shows the new XI

#### Scenario: News for another club
- **WHEN** new items are for another club
- **THEN** they appear in the ticker and the lineup is not refreshed

#### Scenario: After switching club
- **WHEN** the user selects another club
- **THEN** the lineup shown comes from the selection request and no refresh is triggered by older news

### Requirement: Restart feed control
The page SHALL show one control to restart the shared feed, usable by any visitor and without leaving the page. Its label SHALL be localized like the rest of the page, and pressing it SHALL show the busy status, since it is a user action.

#### Scenario: Restart
- **WHEN** the user presses the control
- **THEN** the feed restarts, the ticker shows the restart marker and the first item, and the lineup is refreshed

#### Scenario: Another visitor restarts
- **WHEN** another visitor restarts the feed
- **THEN** within one poll interval the ticker shows the marker and the lineup is refreshed
