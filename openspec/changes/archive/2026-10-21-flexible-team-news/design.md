## Context

`POST /team_news` with `text` calls `Pipeline.interpret(text, club)`, which sends the selected club's roster to the parser and returns `(player_id, kind)` or raises `NewsRejected` (422). Only feed items reach the shared log. `STATUS_OF_KIND` maps kinds to `out`/`doubt`; `p_start_scores` already accepts `available`. Personal and shared availability merge by "larger seq wins, a tie goes to personal", so a clear has to be stored as `available`, not deleted. The log entry `kind` is `news` or `restart`; the UI marks `applied=false` entries "not applied". Read ARCHITECTURE.md contracts: `submit_team_news`, the shared feed and `GET /news`, the UI section, telemetry. All are touched and updated in the same PR.

## Goals / Non-Goals

**Goals:** accept ordinary news in any language up to 100 characters; apply status changes including clearing ones; find players across clubs; post non-status news to everyone; keep XI choice in code.

**Non-Goals:** moderation or rate limiting beyond the length cap; changing the structured path or presets; classifying outsiders; changing how the feed delivers its items.

## Decisions

**1. One parser prompt, a richer answer, a new read path.** `ParsedNews` gains `persons` (each `{name, player_id|null}`, `player_id` set only for the selected club's roster) and `translations` (`en`, `es`, `zh-Hant`), and its `kind` gains `recovered`, `cleared`, `fit`. `Pipeline.interpret` (feed, evals) keeps its signature and behaviour, so the feed is untouched. A new `Pipeline.read(text, club, clubs, opponent)` returns a small result: `{player, status_kind, posted_texts}` or raises `NewsRejected`. Alternative, two prompts, was rejected: one extra model call per line for no gain.

**2. Resolution is code, not the model.** The model lists persons as written. Code resolves each: a `player_id` that is in the selected club's roster, else an exact case-insensitive full-name match in the opponent, else in any club. More than one distinct resolved player: reject. The model never decides that someone "is not a player"; no match means "player not found". Partial names ("Hale") resolve only through the model's `player_id` for the selected club, so the existing behaviour for the selected club is kept.

**3. Outcome rules in `read`.**

```
 persons empty:  known club in answer? yes -> post   no -> reject (name a player or a team)
 one player:     status? yes -> apply to the player's club (must be in the match, else reject)
                          no  -> post
 unresolved person or 2+ players -> reject
 post requires en, es, zh-Hant each non-empty and <= 200 chars after strip (MAX_POST_CHARS, the
 same guard as MAX_EXPLANATION_CHARS); otherwise reject like an unreadable answer.
 Applied status lines never need the translations.
```

The model's translations are shown to every visitor, so their length is capped even though the input is capped at 100 characters.

A status without a person (for example "Harbor City have an injury crisis") is a club line and is posted.

**4. Clearing stores `available`.** `STATUS_OF_KIND` gets `recovered`, `cleared`, `fit` -> `available`. `pick` and scoring already treat it as a factor of 1.0, and the merge rule lets the later personal `available` beat a shared `out`. Entries are never deleted from the availability map. The structured `Kind` literal on the API stays injury/suspension/doubt, so presets and MCP keep their contract; the text path can reach the new kinds.

**5. Applying to the other club.** The status is written under `(session, match, resolved_club)` and the response is the lineup of the requested club (unchanged when the player is in the opponent), with `news.club` naming where it landed. A player of a club outside the match with a status is rejected, because no XI exists to change.

**6. Posting.** New `Feed.post(match_id, club, texts)` appends `kind="info"`, `applied=False` under the lock and returns the seq. It does not touch `_shared` or `_predictions`, is not tied to `generation`, and survives resets as any log entry does. `Feed.poll` ignores `info` when computing `changed`. `applied=False` is kept so no consumer reads it as applied; the UI tells `info` from a failed `news` entry by `kind`. The entry's match and club are the sender's displayed match and club.

**7. Response shape.** `LineupOut` gains optional `news: {outcome: "applied"|"posted", club, player_name, kind}`; `predict_lineup` leaves it null. Alternative, a separate response model, was rejected because the UI swaps the lineup fragment and needs both in one answer.

**8. Length.** `TeamNewsRequest.text` gets `max_length=100`, which the existing validation handler turns into one-message 422. The textarea gets `maxlength="100"`. The cap also bounds the cost of a model call and of a public post.

**9. UI.** `NewsEntry.From` passes `Applied = item.Applied || item.Kind == "info"` so posted lines carry no "not applied" mark. `OnPostNews` builds the message from `Lineup.News`: applied (reuses `MarkedUpdated`, with new past-tense strings for recovered, cleared, fit) or posted (new string). The poll's `lineup-changed` trigger is unchanged because the API's `changed` ignores `info`. Strings are added in en, es and zh-Hant.

**10. Telemetry.** `lineup.team_news` gains `news.outcome` (`applied` or `posted`); the rejected case already marks the span as an error. Text and names stay out of spans.

**11. Per-session post limit.** The log keeps 50 entries and the feed adds one every 15 seconds, so an unlimited poster could push every feed item out of the window. The API keeps `{session_id: last_post_time}` in memory (monotonic clock, one lock), and a post within 10 seconds of the session's last one is 429. The check and the update happen under that lock just before `Feed.post`, so two simultaneous posts cannot both pass. Only a post that was accepted updates the time; applied and rejected submissions do not count. The model call has already happened by then, so the limit protects the log, not the model bill. `shortcut: the map grows with the number of sessions and is lost on restart; use a bounded or shared store if the API runs several replicas.`

## Risks / Trade-offs

- Anyone can post up to 100 characters to every visitor, unmoderated, at most once per 10 seconds per session. A visitor can still start new sessions; the limit is not a defence against a determined abuser.
- Name matching is exact on the full name; a misspelt name is "player not found". The model could normalize it to a roster id for the selected club only.
- Translations are model output and are not checked beyond being non-empty; a bad translation is shown as written.
- The shared prompt grows, which may move the feed's parse accuracy slightly; the existing parser eval is rerun.
- Restart (`/news/restart`) leaves posted lines in the log window, so they scroll out with the bounded window.
