# event-ingestion Specification

## Purpose
Runs one shared, paced and looping feed of team news from the start of the service, and processes each item once into shared availability and a stored prediction, so the cost of an item does not depend on how many visitors there are.

## Requirements

### Requirement: A shared, ordered feed of the featured matchday
The service SHALL run one feed for all visitors from its start. The feed SHALL consist of the team-news events of the featured matchday's matches, ordered by scheduled time across those matches, ties broken by match id and then event id. The featured matchday SHALL be matchday 1. Other event types and other matchdays SHALL NOT be in the feed.

#### Scenario: Feed content and order
- **WHEN** the feed is built from the default seeded data
- **THEN** it holds only the team-news events of the 3 matches of matchday 1, at most 18, earliest scheduled time first

### Requirement: Paced delivery
The feed SHALL deliver one item every 15 seconds, without anyone asking, starting from the service's start. A delivery that takes longer than the interval SHALL NOT be followed by a burst of catch-up deliveries.

#### Scenario: Items arrive on a schedule
- **WHEN** the service has run for 35 seconds
- **THEN** the feed has delivered two or three items, no more than one per 15 seconds

#### Scenario: Slow delivery
- **WHEN** one item takes 40 seconds to process
- **THEN** the next item is delivered after it, not alongside it, and the feed does not deliver several items at once to catch up

### Requirement: Each item is processed once
Delivering an item SHALL interpret it once as free-text team news, update the shared availability for its match and club, pick that club's XI again and store the resulting prediction. Visitors, polls and lineup requests SHALL NOT repeat any of this.

#### Scenario: Many visitors, one parse
- **WHEN** an item is delivered and 50 visitors poll and refresh their lineups
- **THEN** the model has been asked to interpret that item once and the XI for that match and club has been picked once for it

#### Scenario: An injury is ingested
- **WHEN** an injury item for a player in a club's predicted XI is delivered and the model reads it
- **THEN** that player is out in the shared availability and the stored prediction for that match and club omits them

### Requirement: Items that cannot be used
An item that cannot be interpreted, that names a player outside the club, or that would leave the club with no legal XI SHALL stay in the news log marked as not applied and SHALL change neither the shared availability nor the stored prediction. A failure while processing one item SHALL NOT stop the feed.

#### Scenario: Model off
- **WHEN** no model is configured and an item is delivered
- **THEN** the item is in the log marked not applied and the stored predictions are unchanged

#### Scenario: A failing item
- **WHEN** processing one item raises an error
- **THEN** the item is marked not applied and the next item is delivered on schedule

### Requirement: Stored predictions
The service SHALL keep the current prediction of each match and club in memory, so a prediction for a visitor with no personal news is read, not recomputed. A match and club with no stored prediction SHALL be predicted once from the shared availability and stored.

#### Scenario: Reading the stored prediction
- **WHEN** two visitors with no personal news request the same match and club
- **THEN** both receive the same XI and the XI is picked once

### Requirement: Personal news on top of the shared availability
Personal team news (preset or typed) SHALL stay per session and SHALL apply on top of the shared availability for that session only. Where a personal event and a feed event concern the same player, the later event SHALL win.

#### Scenario: Personal news is private
- **WHEN** one visitor marks a player doubt
- **THEN** that visitor's XI reflects it and every other visitor's XI is unchanged

#### Scenario: Later event wins
- **WHEN** a visitor marks a player doubt and the feed then marks the same player out
- **THEN** that visitor's XI treats the player as out

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

### Requirement: Loop and restart
After delivering the last item the feed SHALL wait one interval, reset the shared availability and stored predictions to the baseline, record a restart marker and begin again at the first item. A restart request SHALL do the same at once and deliver the first item immediately. A reset SHALL NOT remove any visitor's personal news.

#### Scenario: Loop
- **WHEN** the last item of a lap has been delivered and one interval has passed
- **THEN** the shared availability is the baseline, a restart marker is in the log and the first item is delivered again

#### Scenario: Restart
- **WHEN** a restart is requested while the feed is part-way through a lap
- **THEN** the shared availability is the baseline, a restart marker is in the log and the first item is in the log

#### Scenario: Personal news survives a reset
- **WHEN** the feed resets while a visitor has personal news
- **THEN** that visitor's personal news is still applied to their XI
