## ADDED Requirements

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
