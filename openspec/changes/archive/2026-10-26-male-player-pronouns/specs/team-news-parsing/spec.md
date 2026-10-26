## ADDED Requirements

### Requirement: Translations treat players as male
Every player is male. When the model writes the English, Spanish and Traditional Chinese texts of a news line, it SHALL refer to a player with he, him or his, él or su, and 他, never they, she or 她, and SHALL use masculine Spanish adjectives for a player. Names and the original wording SHALL still be kept verbatim, so a pronoun SHALL NOT be added where the original has none. The model's instructions SHALL state this rule.

#### Scenario: Spanish translation of an injury line
- **WHEN** a line saying a player is injured is posted with its Spanish text and the text uses an adjective for the player
- **THEN** the adjective is masculine

#### Scenario: No pronoun added
- **WHEN** the original line uses no pronoun
- **THEN** the translations add none

#### Scenario: Instructions carry the rule
- **WHEN** the news parser is built
- **THEN** its instructions tell the model that every player is male and to use he/him/his, él and 他 in the translations
