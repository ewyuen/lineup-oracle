# Spec Delta

## MODIFIED Requirements

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
