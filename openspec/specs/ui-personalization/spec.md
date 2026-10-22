# ui-personalization Specification

## Purpose

TBD - Update Purpose after archive.

## Requirements

### Requirement: Analyst and fan modes
The page SHALL offer two modes. Analyst mode SHALL show each player's `p_start` as a percentage, the alternatives with their `p_start`, and one badge for the whole lineup saying whether its explanations came from a template or the LLM (the API reports this once per lineup, as `llm_used`). Fan mode SHALL hide numbers and the badge and show only names, shirt numbers and the explanation. The chosen mode SHALL be sent to the API with each prediction.

#### Scenario: Analyst view
- **WHEN** the mode is analyst
- **THEN** every player shows a `p_start` percentage

#### Scenario: Fan view
- **WHEN** the mode is fan
- **THEN** no `p_start` number is shown on the page

#### Scenario: Fan explanation without probability
- **WHEN** the API explanation contains an inline `P(start)` value and the mode is fan
- **THEN** the explanation is shown without the `P(start)` label or its number, while its remaining text is preserved

#### Scenario: Switching keeps the XI
- **WHEN** the user switches mode
- **THEN** the same XI is shown in the other presentation

### Requirement: Page language
The page SHALL support English, Spanish and Traditional Chinese (`en`, `es`, `zh-Hant`) for its own text: labels, buttons, headings and messages. The chosen language SHALL be sent to the API with each prediction and news poll. News ticker messages SHALL appear in the chosen language without falling back to a different language. Player explanations SHALL appear as the API returns them, except that fan mode SHALL omit any inline `P(start)` value and its number.

#### Scenario: Spanish page
- **WHEN** the language is Spanish
- **THEN** the labels and buttons are shown in Spanish

#### Scenario: Localized news
- **WHEN** the language is Spanish or Traditional Chinese and news is polled
- **THEN** the ticker displays the corresponding localized message text

#### Scenario: Missing translation
- **WHEN** a page label or message other than a news ticker item has no translation in the chosen language
- **THEN** the English text is shown, never a blank or a key

#### Scenario: Language is remembered
- **WHEN** the user picks a language and reloads
- **THEN** the page is still in that language

### Requirement: Favourite club
The user SHALL be able to mark one club as favourite. It SHALL be remembered in a cookie, pre-select that club in the club toggle when a match includes it, and be marked in the fixture picker.

#### Scenario: Preselected club
- **WHEN** the user has a favourite club and opens a match that includes it
- **THEN** that club is selected and its XI is shown

#### Scenario: Match without the favourite
- **WHEN** the opened match does not include the favourite club
- **THEN** the home club is selected

### Requirement: Preferences survive updates
Mode, language and favourite club SHALL stay unchanged when the XI is updated by team news.

#### Scenario: Preferences after news
- **WHEN** a team-news submission updates the XI
- **THEN** the mode, language and favourite club are unchanged

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
