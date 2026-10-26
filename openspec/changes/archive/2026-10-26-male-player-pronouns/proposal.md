# Proposal

## Why

Every synthetic player is male, but the model's prompts say nothing about gender, so explanations and translated news may call a player "they" or "she". The wording should be consistent: a player is "he".

## What Changes

- The explainer prompt tells the model to refer to a player as he/him/his (él/su in Spanish, 他 in Traditional Chinese), never they or she, to use no gendered pronoun for a club, and to use masculine Spanish adjectives for a player.
- The news-parser prompt carries the same rule for the `es` and `zh-Hant` (and `en`) translations of a line.
- The player-history answer prompt gets the same rule. This change branches off `feature/player-history-graph-rag` (the trunk), where that prompt lives, and is merged after it.
- No change to template explanations (already pronoun-free), the roster, scoring, the optimizer or any API contract.

Contracts touched (ARCHITECTURE.md): none. It describes the agents but not prompt wording, so it needs no update. Components touched: the explainer and news-parser agents in `backend/lineup_oracle/agents.py`.

## Capabilities

### New Capabilities

### Modified Capabilities
- `llm-explanations`: model-written explanations refer to players as male.
- `team-news-parsing`: translations of a news line refer to players as male.

## Impact

- `backend/lineup_oracle/agents.py`: one sentence added to `EXPLAINER_INSTRUCTIONS`, `PARSER_INSTRUCTIONS` and `HISTORY_ANSWER_INSTRUCTIONS`.
- `backend/tests/`: a unit test that each constant contains the rule.
- No delta spec for the history answer: its requirements are still in the in-flight `player-history-graph-rag` change, not in `openspec/specs/`.
