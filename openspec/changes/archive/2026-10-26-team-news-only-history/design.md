# Design

## Context

`history.py` builds history from `shot`, `tackle` and `team_news` events plus `started` rows derived from match metadata; `types` filters among them (API, parser, graph query). ARCHITECTURE.md describes `player_history` and the graph under "Player history". The graph schema has Shot/Tackle/Team-news `Event` vertices and `STARTED` edges. The news overlay (`news-in-player-history`) is applied in `retrieve_player_history`.

## Goals / Non-Goals

**Goals:**
- History returns team news only, from memory and graph alike.
- Smaller contract: no `types`.

**Non-Goals:**
- Changing events, the generator or the feed (shots and tackles stay in the events file).
- Writing news into the graph.

## Decisions

- **Remove the `types` filter** rather than accept only `team_news`: a one-value filter is noise. Pydantic ignores unknown fields by default, so `HistoryFiltersIn` gets `extra="forbid"` to make an old client sending `types` fail with 422 (stated in the spec) instead of silently getting everything; this also rejects other misspelled filter keys. Alternative (keep it, restrict values) rejected as dead surface. The response `filters` loses `types`.
- **Keep `type: "team_news"` on each item**, so the UI and answer-prompt rows keep their shape.
- **Memory path**: `EVENT_TYPES` becomes `("team_news",)`; `HISTORY_TYPES` and the `started` branch are deleted; the overlay no longer checks types.
- **Graph**: `load` writes only team-news events (`HAD`/`IN` edges); `STARTED` edges and Shot/Tackle events go. The fetch query drops the types clause and the starts query. Clubs, players and matches stay because the news events link to them. A graph loaded before the change still holds the extra rows, so the fetch asks for `type = 'team_news'`, and the docs say to reload. Parity tests compare the same filters minus types.
- **Prompts**: `HISTORY_PARSER_INSTRUCTIONS` drops the types list and the `types` key in its JSON; `HISTORY_ANSWER_INSTRUCTIONS` says the events are team news only and to say so when the question asks about anything else. `template_answer` lists the team-news lines and the count, or "Nothing found".
- **API parser validation** loses the unknown-type check.

## Risks / Trade-offs

- Breaking for any client that sends `types`; this repo's UI does not.
- A graph loaded before the change keeps old rows; the type guard in the fetch hides them until reload.
- Questions about shots get a thin answer by design.
