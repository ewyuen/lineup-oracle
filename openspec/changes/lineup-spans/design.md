# Design

## Context

`POST /predict_lineup` and `POST /team_news` are sync handlers in `backend/lineup_oracle/api.py` that both finish in `_render`, where `llm_used`, `formation`, `mode` and `language` are known. `setup_telemetry` runs in `create_app` and configures the Azure Monitor distro only when the connection string is set. See proposal.md for motivation. ARCHITECTURE.md's Telemetry bullet currently says "No custom telemetry or dashboards" and must change with this.

## Goals / Non-Goals

**Goals:**
- One span per request on the two endpoints, filterable by club and match, showing model versus template fallback.
- Identical behaviour and no new dependency when telemetry is off.

**Non-Goals:**
- Feed ticker span, `xi.changed`, custom metrics or events, eval or grounding results on spans.

## Decisions

- **Plain `opentelemetry.trace` API, no wrapper module.** `trace.get_tracer(__name__)` returns a no-op tracer when no provider is set, so there is no `if enabled` branch and local runs are unchanged. Alternative: a helper in `telemetry.py`; rejected as more code for two call sites.
- **Span around the handler body, attributes set where the values are known.** `_render` sets the shared attributes (`formation`, `llm_used`, `mode`, `language`) on `trace.get_current_span()`. Each handler sets `match_id`, `club` and its own attributes. Alternative: return the values from `_render` and set them in the handlers; rejected as it duplicates the setting code.
- **`team_news` span covers the parser call too.** `interpret` runs inside the handler, so the parser's model span nests under `lineup.team_news`. `news.kind` is set once the kind is known (after parsing).
- **Errors:** the span is used with the default `record_exception` and `set_status_on_exception`, so an `HTTPException` 422 raised inside it marks the span as an error. A template fallback is not an exception, so it shows only as `llm_used` false.
- **No sensitive data:** only the listed attributes. Session ids, texts and explanations are never set.
- **Tests with the in-memory span exporter** (`opentelemetry-sdk`, already installed by the distro) on a private tracer provider, using the existing API test client and fake model. No connection string is needed.

## Risks / Trade-offs

- [The global tracer provider can only be set once per process] → tests inject their provider through a small fixture and do not call `set_tracer_provider` twice; if that proves brittle, patch the module's `tracer`.
- [Sync handlers run on a worker thread, so context must follow] → the span is started inside the handler body, so the current span is the right one for `_render`.
- [Attribute names become an informal contract for queries] → they are fixed in the spec.
