# Spec Delta

## MODIFIED Requirements

### Requirement: Loop and restart
After delivering the last item the feed SHALL wait one interval, reset the shared availability and stored predictions to the baseline, record a restart marker and begin again at the first item. This automatic loop reset SHALL preserve every visitor's personal news. A manual restart request SHALL immediately reset the shared availability and stored predictions, clear personal availability and alternatives for every visitor session, record a restart marker and deliver the first item.

#### Scenario: Loop
- **WHEN** the last item of a lap has been delivered and one interval has passed
- **THEN** the shared availability is the baseline, a restart marker is in the log and the first item is delivered again

#### Scenario: Restart
- **WHEN** a manual restart is requested while multiple visitor sessions have personal news or alternatives
- **THEN** personal availability and alternatives are cleared for every session, shared availability and stored predictions are reset, a restart marker is logged, and the first feed item is logged immediately

#### Scenario: Personal news survives a reset
- **WHEN** the feed resets in its automatic loop while a visitor has personal news
- **THEN** that visitor's personal news is still applied to their XI

#### Scenario: Personal news after manual restart
- **WHEN** a visitor submits personal news after a manual restart
- **THEN** that news applies to that visitor's XI only and does not restore any earlier session's personal news
