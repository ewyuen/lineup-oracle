# Backend

This backend contains the synthetic roster generator, event generation, and replay logic used by Lineup Oracle.

## Event generation

Run:

```bash
python -m lineup_oracle.events --seed 42 --out backend/data/events.jsonl
```

The generated file contains one JSON event per line. Each event includes:
- `id`
- `match_id`
- `type`
- `minute`
- `club`
- `player`
- `payload`
- `simulated`

Team-news events use free text inside the `payload.text` field and are emitted before kick-off with negative minutes.

## Replay speed

Replay speed is controlled by the `speed` parameter. Set `speed=0` for instant delivery in tests; values greater than zero compress the virtual timeline.
