# Spec Delta

## MODIFIED Requirements

### Requirement: Alternatives
The page SHALL show, for each position line, up to four alternatives returned by the API, none of whom is in the starting XI. It SHALL identify when an alternative is still injured or doubtful and provide a way to add eligible injured or doubtful non-starters to the alternatives without changing their status or the starting XI.

#### Scenario: Alternatives listed
- **WHEN** a predicted XI is shown
- **THEN** each position line lists up to four alternatives, none of whom is in the XI

#### Scenario: Selected injured or doubtful player is shown with status
- **WHEN** an injured or doubtful player has been manually included in the alternatives
- **THEN** the page shows the player under their position and indicates their current injury or doubt status

## ADDED Requirements

### Requirement: Choose eligible unavailable players as alternatives
The analyst SHALL be able to add or remove an injured or doubtful non-starter from the alternatives for the selected match and club. The action SHALL use an in-page update, preserve the displayed starting XI, and SHALL NOT clear or alter the player's injury or doubt status. Suspended players SHALL NOT be offered for selection.

#### Scenario: Add an injured player
- **WHEN** the analyst adds an eligible injured player to the alternatives
- **THEN** the lineup fragment updates to show the player in their position's alternatives, the starting XI is unchanged, and the injury status remains visible

#### Scenario: Add a doubtful player
- **WHEN** the analyst adds an eligible doubtful player to the alternatives
- **THEN** the lineup fragment updates to show the player in their position's alternatives, the starting XI is unchanged, and the doubt status remains visible

#### Scenario: Remove a selected player
- **WHEN** the analyst removes a manually included player from the alternatives
- **THEN** the lineup fragment updates with the normal ranked alternatives and the starting XI remains unchanged

#### Scenario: The position already has four alternatives
- **WHEN** the analyst adds an eligible player to a position with four alternatives
- **THEN** the new player appears in the list and the lowest-ranked alternative is displaced

#### Scenario: Suspended players cannot be selected
- **WHEN** a player is suspended
- **THEN** the page does not offer an action to include that player in alternatives

#### Scenario: Alternative selection persists for the browser session
- **WHEN** an analyst selects an alternative and later refreshes the same match and club in that browser session
- **THEN** the selection remains reflected in the alternatives
