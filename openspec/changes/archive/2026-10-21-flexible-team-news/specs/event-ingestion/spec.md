## MODIFIED Requirements

### Requirement: A numbered news log
Every delivery, every reset of the feed and every line posted by a visitor SHALL append an entry to an ordered news log with a sequence number that never decreases, including across resets. A news entry SHALL retain its English (`en`), Spanish (`es`) and Traditional Chinese (`zh-Hant`) texts with its match, club and applied status. An entry posted by a visitor SHALL be an informational entry: it is shown to every visitor, is not a failed delivery, and has no effect on availability or predictions. A restart SHALL be a marker. The service SHALL keep only a bounded recent window of the log. A reset SHALL NOT remove informational entries from the retained window.

#### Scenario: Sequence continues across a reset
- **WHEN** the feed resets and delivers its first item again
- **THEN** the new entries have higher sequence numbers than every earlier entry

#### Scenario: Localized texts are kept
- **WHEN** a team-news item is appended to the log, applied or not
- **THEN** its English, Spanish and Traditional Chinese texts are all available to pollers

#### Scenario: Posted line is shared
- **WHEN** a visitor posts a line and another visitor polls
- **THEN** the other visitor receives the entry in their selected language

#### Scenario: Posted line changes nothing
- **WHEN** a visitor's line is posted
- **THEN** the shared availability and the stored predictions are unchanged
