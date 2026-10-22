## MODIFIED Requirements

### Requirement: Shared news ticker
The page SHALL show a ticker of the shared news above the busy status, containing the same feed events and posted lines for every visitor and selected match and club, with each message shown in that visitor's selected language. Items SHALL move from right to left, all at the same speed. Items SHALL NOT overlap: a new item SHALL enter only after the previous item has fully cleared the entrance edge of the ticker, and at least 3 seconds after the previous item entered, whichever is later, whether the items arrived in the same poll or in different polls. When more than 5 items are waiting to enter, the oldest waiting items SHALL be dropped from the ticker, except a restart marker. The text of each item SHALL be available to assistive technology, a feed item that was not applied SHALL be visibly marked, a posted line SHALL be shown without that mark, and a restart of the feed SHALL show as a marker. With a reduced-motion preference the items SHALL be shown as a static list, with no waiting and no dropping.

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

#### Scenario: Items never overlap
- **WHEN** a new item arrives while an earlier item is still crossing the ticker, in the same poll or a later one
- **THEN** it waits and enters only after the earlier item has cleared the entrance edge and 3 seconds have passed since that item entered, so no two items share space

#### Scenario: Long lines
- **WHEN** items in Spanish or Traditional Chinese are wider than the distance they would have travelled after 3 seconds
- **THEN** the next item still waits until the previous item's right edge has cleared the entrance

#### Scenario: Backlog
- **WHEN** more than 5 items are waiting to enter, such as on page load or after a feed restart
- **THEN** the oldest waiting items are dropped from the ticker, a restart marker is kept, and the rest enter one at a time

#### Scenario: Wide item after a narrow one
- **WHEN** a wide item follows a narrower one
- **THEN** it moves at the same speed and never catches up with the item ahead

#### Scenario: Ticker keeps working after the bar is replaced
- **WHEN** the feed is restarted, or the club or language is changed
- **THEN** items that arrive afterwards still enter the ticker one at a time

#### Scenario: Reduced motion
- **WHEN** the user prefers reduced motion
- **THEN** the items are shown without moving, and none are held back or dropped
