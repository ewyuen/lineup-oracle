# Spec Delta

## ADDED Requirements

### Requirement: Explain unavailable players truthfully
The explanation of a listed player whose availability is out SHALL say the player is injured or unavailable and not expected to start, and SHALL NOT call them a likely starter, in both template and model-written explanations. Wording about unavailability for such a player SHALL NOT be counted as ungrounded, and the model's instructions SHALL tell it how to explain an unavailable player. A manually included alternative SHALL be covered by the same facts, coverage and validation rules as every other listed player.

#### Scenario: Template for an injured alternative
- **WHEN** a manually included injured player is explained by the template
- **THEN** the text says the player is injured or unavailable and not expected to start, and does not say likely starter

#### Scenario: Model explanation of an injured alternative
- **WHEN** the model explains a manually included injured player in unavailability terms that match the facts
- **THEN** the explanation is accepted as grounded and the model's answer is not treated as failed

#### Scenario: Manual alternative is covered
- **WHEN** the model returns explanations for the XI and the natural alternatives but not for a manually included alternative
- **THEN** the call is treated as failed and the template explanations are used
