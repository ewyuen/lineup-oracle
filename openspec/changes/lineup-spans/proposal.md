# Proposal

## Why

The deployed traces show only library spans (HTTP requests, Agent Framework model calls). Nothing marks "a lineup was predicted" or "team news changed the lineup", so a trace in Application Insights cannot be filtered by club or match, and cannot show at a glance whether the model or the template fallback wrote the explanations.

## What Changes

- Add one custom OpenTelemetry span to each of `POST /predict_lineup` (`lineup.predict`) and `POST /team_news` (`lineup.team_news`), nested under the request span the distro already creates.
- Attributes: `match_id`, `club`, `mode`, `language`, `formation`, `llm_used` on both; `lineup.source` (`stored` or `personal`) on predict; `news.input` (`text` or `structured`) and `news.kind` on team_news.
- Prompts, reply text, session ids and the XI itself are not recorded.
- Relax the "no custom telemetry" rule to allow exactly these two spans; custom metrics, events and dashboards stay out.
- No new dependency (`opentelemetry-api` already comes with the Azure Monitor distro) and no behaviour change when `APPLICATIONINSIGHTS_CONNECTION_STRING` is unset (the tracer is a no-op).

Out of scope: a span for the feed ticker, an `xi.changed` attribute, and eval or grounding results on spans.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `telemetry`: the "No custom telemetry" requirement becomes "Two custom lineup spans", with the span names and attributes above.

## Impact

- Code: `backend/lineup_oracle/api.py` (two handlers and `_render`), a small test in `backend/tests/test_telemetry.py`.
- Contracts: no API or event contract changes. [ARCHITECTURE.md](../../../ARCHITECTURE.md) Telemetry bullet ("No custom telemetry or dashboards") is updated in the same PR.
- Azure: nothing to deploy beyond the new API image; the connection string is already set by Bicep.
