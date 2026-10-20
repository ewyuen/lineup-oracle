# Backend

This backend contains the synthetic roster generator, event generation, and replay logic used by Lineup Oracle.

## Event generation

Run from the `backend/` folder:

```bash
cd backend
python -m lineup_oracle.events --seed 42 --out data/events.jsonl
```

The generated file contains one JSON event per line. Each event includes:
- `id`
- `match_id`
- `type` (`pass`, `shot`, `tackle`, `possession_change`, `pressure`, `team_news`, `match_metadata`)
- `minute`
- `club`
- `player`
- `payload`
- `simulated`

Team-news events carry `payload.kind` and `payload.player_name` as answer labels for the parser eval (the parser must not read them). They use free text inside the `payload.text` field and are emitted before kick-off with negative minutes (-48, -24 and -1). Each match has an injury, a suspension and a fitness doubt per club. Injured and suspended players are excluded from that match's true XI, which is stored in the `match_metadata` event (`payload.schema_version` is 1; `payload.matchday` is 1 to 10). Minutes are relative to each match's kick-off, so every match shares the same time axis: replay one match at a time (filter on `match_id`), not the whole file.

## Replay speed

Replay speed is controlled by the `speed` parameter, measured in match minutes per real second:
- `speed=0` delivers every event immediately (used in tests).
- `speed=1.0` (the default and demo speed) replays a 90-minute match in about 90 seconds. Pre-kick-off team news (negative minutes) is delivered without waiting, so a whole match including its news still takes about 90 seconds.
- Higher values compress the timeline further, for example `speed=60` replays a match in 1.5 seconds.

## Scoring and the XI optimizer

`lineup_oracle.scoring.p_start_scores(club, recent_xis, availability)` returns a P(start) per player: `availability * (0.7 * quality + 0.3 * recent_share)`. `quality` is the mean of the ratings that matter for the position; `recent_share` is the share of the last 5 matches the player started (0.5 with no history); availability is `available` 1.0, `doubt` 0.5, `out` 0. `recent_xis(events, club, matchday)` reads earlier `match_metadata` events.

`lineup_oracle.optimizer.pick_xi(club, scores)` solves one SciPy MILP per supported formation, multiplies the total by the formation prior (1.0 for the club's usual formation, 0.85 otherwise) and returns the best `XI` (formation, 11 players with `p_start`, up to 2 alternatives per position). It raises `ValueError` naming the club if no formation can be filled. Ties go to the lower player id.

The generator draws each true XI with weight `quality ** 4`, so better players start more often.

## API and MCP server

Run the API from `backend/`: `uvicorn lineup_oracle.api:create_app --factory` (port 8000). It loads `data/roster.json` and `data/events.jsonl` if present, otherwise generates the same data in memory from seed 42. Regenerate the events file with the command above if it was made before the `matchday` field existed. Operations: `GET /matches`, `GET /matches/{match_id}/xi`, `POST /predict_lineup`, `POST /team_news`, `GET /health`. Team news accepts a player id and a kind (`injury`, `suspension`, `doubt`); free text goes to the LLM parser when the model is configured (otherwise it is rejected with 422). Availability is in memory only and kept per `session_id` (default `"default"`), so separate visitors do not affect each other.

Run the MCP server (stdio) with `python -m lineup_oracle.mcp_server`. It forwards four tools to the API at `LINEUP_API_URL` (default `http://127.0.0.1:8000`).

## LLM pipeline and evals

The model is optional. Put the settings in a `.env` file in the repo root (copy `.env.example`; gitignored) or set them as environment variables (real variables win). Set `LINEUP_LLM_ENDPOINT` and `LINEUP_LLM_DEPLOYMENT` (and `LINEUP_LLM_API_KEY`, or sign in for `DefaultAzureCredential`; `LINEUP_LLM_TIMEOUT` defaults to 15 seconds) to turn on free-text team news parsing and model-written explanations in the chosen mode and language. Without them, or on any model failure, the API returns the same XI with English template explanations and `llm_used` false.

- `python -m lineup_oracle.llm --check` makes live calls (parse one line, explain in en, es and zh-Hant).
- `python -m lineup_oracle.evals [--parser]` prints the lineup score against the previous-match baseline; `--parser` also scores the news parser and needs the model.
