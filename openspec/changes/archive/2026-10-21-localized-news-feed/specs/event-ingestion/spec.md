# Spec Delta

## MODIFIED Requirements

### Requirement: A numbered news log
Every delivery, and every reset of the feed, SHALL append an entry to an ordered news log with a sequence number that never decreases, including across resets. A news entry SHALL retain its English (`en`), Spanish (`es`) and Traditional Chinese (`zh-Hant`) texts with its match, club and applied status. A restart SHALL be a marker. The service SHALL keep only a bounded recent window of the log.

#### Scenario: Sequence continues across a reset
- **WHEN** the feed resets and delivers its first item again
- **THEN** the new entries have higher sequence numbers than every earlier entry

#### Scenario: Localized texts are kept
- **WHEN** a team-news item is appended to the log, applied or not
- **THEN** its English, Spanish and Traditional Chinese texts are all available to pollers
