# Spec Delta

## Purpose
Defines trace export from the API and UI to Application Insights, so per-stage timing and model failures with the template fallback are visible on Azure, without affecting local runs.

## ADDED Requirements

### Requirement: Traces exported when configured
The API and the UI SHALL export OpenTelemetry traces to Application Insights when `APPLICATIONINSIGHTS_CONNECTION_STRING` is set.

#### Scenario: Request traced
- **WHEN** a prediction request reaches the deployed UI
- **THEN** a trace linking the UI request and the API request appears in Application Insights

#### Scenario: Model failure visible
- **WHEN** a model call fails and the template explanation serves the XI
- **THEN** the failure is recorded on the trace and the response is still 200

### Requirement: Silent when not configured
Without the connection string, the API and the UI SHALL start and behave exactly as before, with no export attempts and no errors.

#### Scenario: Local run
- **WHEN** the API or UI starts with the variable unset
- **THEN** telemetry setup is skipped and all existing tests pass

### Requirement: No custom telemetry
Telemetry SHALL use only the standard instrumentation and the Agent Framework's built-in traces: no custom metrics, dashboards or events.

#### Scenario: Scope
- **WHEN** the telemetry code is reviewed
- **THEN** it contains only the distro configuration call
