# Proposal

## Why

The team-news text box only accepts a line about one player of the selected club with one of three negative kinds (injury, suspension, doubt). Anything else is a 422 and the visitor learns nothing: a player of the opponent is refused, a recovery ("Finn Hale is fit again") cannot be entered, and club or transfer news is rejected. The box should accept ordinary news, apply what changes availability, and share what does not.

## What Changes

- Free-text news is read into: the persons named, the club named (if any), an optional status, and the line in English, Spanish and Traditional Chinese. The status gains three clearing kinds besides injury, suspension and doubt: recovered, suspension cleared, fit (no doubt). A clearing kind sets the player to `available`, which overrides an earlier shared or personal "out" or "doubt".
- Every named person must resolve to a roster player, looked up in the selected club, then the other club of the match, then any club. A name that does not resolve is a "player not found" error under the box: no broadcast, no state change.
- Outcomes of a line:
  - player resolved with a status: applied to that player's club, for the sender's session only, not broadcast (as today);
  - player resolved without a status, or no person but a known club named: posted to the shared news log as a new informational entry, with no effect on any XI;
  - no person and no club: error asking for a player or a team.
- Posted entries show in every visitor's ticker in the visitor's language. They are not marked "not applied" and do not make pollers refetch the lineup.
- Typed text is limited to 100 characters: 422 from the API, `maxlength` on the box.
- `POST /team_news` answers with the lineup plus a small `news` object (outcome, club, player name, kind) so the page can say what happened.
- The model off, failing or unreadable still rejects the line with the existing "unavailable" message; nothing is posted.

Out of scope: moderation or rate limiting of posted lines beyond the length cap, new preset buttons, changing the structured `player_id` + `kind` path, treating outsiders (owners, buyers) as anything other than "player not found".

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `team-news-parsing`: richer reading (persons, club, clearing kinds, translations), player lookup across clubs, new outcomes and rejections.
- `lineup-api`: free-text `/team_news` outcomes, 100-character limit, `news` object in the response.
- `event-ingestion`: the news log gains an informational entry kind that is posted by a visitor's line.
- `lineup-ui`: text box limit, outcome messages, ticker shows informational entries without the not-applied mark.

## Impact

ARCHITECTURE.md: the `submit_team_news` contract (text path and `LineupOut.news`), the shared feed section (entry kind `info`), the `GET /news` description (`changed` ignores `info`), the UI section and the telemetry line (`news.outcome`) change, so they are updated in the same PR. Components touched: parser agent and `Pipeline` (`agents.py`, `pipeline.py`), `/team_news` and `Feed` (`api.py`, `ingest.py`), `STATUS_OF_KIND` (`picking.py`), the parser evals (`evals.py`), the Razor `_TeamNews` partial, `Index` handler, `NewsEntry`, UI resource strings (en, es, zh-Hant). The MCP adapter forwards the API response, so it needs no code change. Scoring already accepts the `available` status.
