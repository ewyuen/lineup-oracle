# Spec Delta

## ADDED Requirements

### Requirement: Shared news ticker
The page SHALL show a ticker of the shared news above the busy status, the same for every visitor and for every selected match and club. Items SHALL move from right to left. The text of each item SHALL be available to assistive technology, an item that was not applied SHALL be visibly marked, and a restart of the feed SHALL show as a marker. With a reduced-motion preference the items SHALL be shown as a static list.

#### Scenario: News arrives
- **WHEN** a new item is delivered to the feed
- **THEN** it appears in the ticker of every open page and moves from right to left

#### Scenario: Same for everyone
- **WHEN** two visitors view different matches
- **THEN** both tickers show the same items

#### Scenario: Item not applied
- **WHEN** an item could not be used
- **THEN** it is shown with a visible not-applied mark

#### Scenario: Reduced motion
- **WHEN** the user prefers reduced motion
- **THEN** the items are shown without moving

### Requirement: Background news polling
While the page is open, it SHALL ask for the news every 10 seconds, sending the last sequence number it saw and the displayed match and club. A poll SHALL NOT show the busy status, and a failed poll SHALL leave the ticker and lineup as they are, with the next poll tried at the usual time. A poll with nothing new SHALL NOT change what is on screen.

#### Scenario: Silent poll
- **WHEN** a background poll is pending
- **THEN** the busy status is not shown

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
