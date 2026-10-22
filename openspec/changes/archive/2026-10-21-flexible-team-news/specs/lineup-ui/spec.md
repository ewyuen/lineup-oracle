## MODIFIED Requirements

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
