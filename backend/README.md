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

Team-news events use free text inside the `payload.text` field and are emitted before kick-off with negative minutes (-48, -24 and -1). Each match has an injury, a suspension and a fitness doubt per club. Injured and suspended players are excluded from that match's true XI, which is stored in the `match_metadata` event (`payload.schema_version` is 1).

## Replay speed

Replay speed is controlled by the `speed` parameter, measured in match minutes per real second:
- `speed=0` delivers every event immediately (used in tests).
- `speed=1.0` (the default and demo speed) replays a 90-minute match in about 90 seconds.
- Higher values compress the timeline further, for example `speed=60` replays a match in 1.5 seconds.
