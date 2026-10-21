# Spec Delta

## MODIFIED Requirements

### Requirement: Shared news ticker
The page SHALL show a ticker of the shared news above the busy status, containing the same feed events for every visitor and selected match and club, with each message shown in that visitor's selected language. Items SHALL move from right to left. The text of each item SHALL be available to assistive technology, an item that was not applied SHALL be visibly marked, and a restart of the feed SHALL show as a marker. With a reduced-motion preference the items SHALL be shown as a static list.

#### Scenario: News arrives
- **WHEN** a new item is delivered to the feed
- **THEN** it appears in every open page's ticker in that page's selected language and moves from right to left

#### Scenario: Same for everyone
- **WHEN** two visitors view different matches or select different languages
- **THEN** both tickers show the same feed events, with each message rendered in the visitor's selected language

#### Scenario: Item not applied
- **WHEN** an item could not be used
- **THEN** it is shown with a visible not-applied mark

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
