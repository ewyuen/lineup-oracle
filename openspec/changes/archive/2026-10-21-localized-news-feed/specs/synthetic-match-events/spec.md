# Spec Delta

## MODIFIED Requirements

### Requirement: Team-news events
Before each kick-off the generator SHALL emit team-news events (injury, suspension, late fitness doubt) that affect who is available, marked as simulated. Each event SHALL carry English free-text in `payload.text` and, in `payload.translations`, equivalent text in Spanish (`es`) and Traditional Chinese (`zh-Hant`), each naming the club and affected player, with `player` left null so the text is the only source of the player.

#### Scenario: Text names the team
- **WHEN** a team-news event is generated for a club
- **THEN** each language variant mentions that club and a player from that club's roster

#### Scenario: Text matches the truth
- **WHEN** a team-news event says a player is injured or suspended in any supported language
- **THEN** that player is not in the club's true XI in the match metadata

#### Scenario: Text is deterministic
- **WHEN** the generator runs twice with the same seed and roster
- **THEN** the English and localized team-news texts are identical

#### Scenario: Complete translations
- **WHEN** a team-news event is generated
- **THEN** `payload.text` is non-empty and `payload.translations` contains non-empty text for `es` and `zh-Hant`

#### Scenario: Unavailable player does not start
- **WHEN** a player has an injury or suspension event for a match
- **THEN** that player is not in that match's starting XI
