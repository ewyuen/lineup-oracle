# azure-deployment Specification

## Purpose
Defines how Lineup Oracle runs on Azure: what is publicly reachable, how the model is accessed, and how a deployment is repeated, so a judge can open one URL and the system works.

## Requirements

### Requirement: One-command repeatable deployment
The repository SHALL deploy the whole system (UI, API, model, monitoring) to an empty resource group from a single script, and running it again SHALL update the deployment without creating duplicates.

#### Scenario: Fresh deployment
- **WHEN** the deploy script is run against an empty resource group with a valid subscription
- **THEN** the UI, the API, the model deployment and Application Insights exist, and the script prints the UI URL

#### Scenario: Re-deployment
- **WHEN** the script is run a second time after a code change
- **THEN** the apps run the new images and no duplicate resources are created

### Requirement: Only the UI is public
The UI SHALL be reachable from the internet over HTTPS. The API SHALL be reachable only from inside the Container Apps environment.

#### Scenario: Public UI works end to end
- **WHEN** a visitor opens the UI URL and picks a fixture
- **THEN** the page shows the predicted XI, served through the internal API

#### Scenario: API not exposed
- **WHEN** a request is sent to the API from outside the environment
- **THEN** it cannot connect

### Requirement: Keyless model access
The API SHALL reach the model with a managed identity, and no model key SHALL be stored in the repository, the Bicep files or the app configuration. The endpoint and deployment name SHALL come from environment variables set by the deployment.

#### Scenario: Model reachable with identity
- **WHEN** the API runs on Azure and a free-text team news message is submitted
- **THEN** it is parsed by the model and the lineup response reports the model was used

### Requirement: Missing model does not break the deployment
If the model deployment is absent or unreachable, the API SHALL still start and return an XI with template explanations.

#### Scenario: Model unavailable
- **WHEN** the API runs with no `LINEUP_LLM_*` settings or the model call fails
- **THEN** `/health` is healthy and a prediction returns an XI with template explanations

### Requirement: Single API instance
The API SHALL run as exactly one replica, because team news is held in memory per session.

#### Scenario: Replica count
- **WHEN** the deployment finishes
- **THEN** the API app has minimum and maximum replicas of 1

### Requirement: Infrastructure checked in CI
The Bicep files SHALL compile without errors in CI on every push and pull request, together with the Python and .NET tests.

#### Scenario: Broken Bicep
- **WHEN** a Bicep file has a syntax or type error
- **THEN** the CI workflow fails
