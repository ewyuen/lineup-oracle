# Spec Delta

## ADDED Requirements

### Requirement: Language preference updates asynchronously
Changing the page language SHALL update localized page content and the prediction without a full-page navigation, and SHALL remember the selected language.

#### Scenario: Change language
- **WHEN** the user selects a supported language
- **THEN** the language preference is saved, localized page content and lineup explanations are refreshed asynchronously, and the browser remains on the selected fixture and club

### Requirement: Favourite-club preference updates asynchronously
Changing the favourite club SHALL save the preference and update the favourite marker and selected lineup without a full-page navigation.

#### Scenario: Mark a club as favourite
- **WHEN** the user marks one of the current fixture's clubs as favourite
- **THEN** the preference is saved, the favourite marker and active club update, and that club's lineup is shown asynchronously
