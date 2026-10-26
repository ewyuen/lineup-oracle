# llm-explanations Specification

## Purpose
TBD - created by archiving change agent-pipeline-and-llm. Update Purpose after archive.

## Requirements

### Requirement: Model-written explanations
When the model is configured, the service SHALL write each predicted player's explanation with the model, in the requested language (en, es or zh-Hant) and mode, from facts computed by code (the player's `p_start`, recent starts, availability, strongest rating). The prediction response SHALL then carry `llm_used` true. The model SHALL NOT change which players are picked, their order or their `p_start`.

#### Scenario: Spanish explanations
- **WHEN** a lineup is predicted with language `es` and the model works
- **THEN** all 11 players and all listed alternatives carry a non-empty explanation, and `llm_used` is true

#### Scenario: Same XI with or without the model
- **WHEN** the same prediction is made with the model on and off
- **THEN** the players, formation, order and `p_start` values are identical

### Requirement: Mode controls the style
In analyst mode explanations SHALL be short and MAY quote `p_start` and counts. In fan mode they SHALL be plain sentences with no `p_start` number.

#### Scenario: Fan mode has no probability
- **WHEN** a lineup is predicted in fan mode
- **THEN** no explanation contains a `P(start)` figure or a percentage

### Requirement: Validate the model's explanations
The service SHALL accept the model's explanations only when they cover exactly the players of the lineup (XI and alternatives), each non-empty and no longer than a set limit, and in fan mode free of percentages. Otherwise it SHALL treat the call as failed.

#### Scenario: Missing player
- **WHEN** the model returns explanations for 10 of the 11 players
- **THEN** the call is treated as failed and the template explanations are used

### Requirement: Fall back to templates
If the model is not configured, errors, times out or returns invalid output, the service SHALL still return the XI, with English template explanations and `llm_used` false. It SHALL NOT fail the request because of the model.

#### Scenario: Model error
- **WHEN** the model call raises an error during a prediction
- **THEN** the response is 200 with the same XI, English template explanations and `llm_used` false

#### Scenario: Model off
- **WHEN** no model is configured
- **THEN** every prediction uses template explanations and `llm_used` is false

### Requirement: Repeat requests do not call the model again
The service SHALL reuse the explanations for an identical lineup, mode and language instead of calling the model again, and SHALL call the model at most once per prediction (all explanations in one request).

#### Scenario: Same request twice
- **WHEN** the same prediction is requested twice with no news in between
- **THEN** the model is called once and both responses are identical

#### Scenario: News changes the lineup
- **WHEN** news changes the XI
- **THEN** the explanations are written again for the new lineup

### Requirement: Facts only from the data
The explanations SHALL be generated from the supplied facts only. The model SHALL NOT be given real-world names or data, and the synthetic roster is the only source of names.

#### Scenario: Facts passed
- **WHEN** the explainer is called
- **THEN** its input contains only the lineup facts computed by code for that request

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

### Requirement: Players are referred to as male
Every player is male. A model-written explanation that refers to a player by a pronoun SHALL use he, him or his in English, él or su in Spanish and 他 in Traditional Chinese, and SHALL NOT use they, she or their for a player. Spanish adjectives and participles that describe a player SHALL be masculine. A club SHALL NOT be referred to by a gendered pronoun. The model's instructions SHALL state this rule. Template explanations SHALL stay free of gendered pronouns.

#### Scenario: English pronoun
- **WHEN** the model explains a player in English and uses a pronoun for the player
- **THEN** the pronoun is he, him or his, never they, she or her

#### Scenario: Spanish agreement
- **WHEN** the model explains a player in Spanish and describes the player with an adjective such as lesionado
- **THEN** the adjective is masculine

#### Scenario: Chinese pronoun
- **WHEN** the model explains a player in Traditional Chinese and uses a pronoun for the player
- **THEN** the pronoun is 他, never 她

#### Scenario: Instructions carry the rule
- **WHEN** the explainer is built
- **THEN** its instructions tell the model that every player is male and to use he/him/his, él and 他
