# Tasks

## 1. Branch

- [x] 1.1 Create the feature branch `feature/male-player-pronouns` from `feature/player-history-graph-rag` (the trunk) and verify `git branch --show-current` shows it

## 2. Prompts and tests

- [x] 2.1 Add the male-player rule (he/him/his, él/su, 他, never they/she, no gendered pronoun for a club, masculine Spanish adjectives) to `EXPLAINER_INSTRUCTIONS` in `backend/lineup_oracle/agents.py` and verify with the unit test in 2.3
- [x] 2.2 Add the same rule to `PARSER_INSTRUCTIONS`, with "never add a pronoun the original lacks", and verify with the unit test in 2.3
- [x] 2.3 Add the same rule to `HISTORY_ANSWER_INSTRUCTIONS` and verify with the unit test in 2.4
- [x] 2.4 Add a unit test in `backend/tests/` that the three constants contain the rule's key terms, and verify `python -m pytest -q -k pronoun` passes
- [x] 2.5 Run the explainer, the parser and the history answerer against the `.env` model for a few players in en, es and zh-Hant (analyst and fan) and verify no they/she/她 or feminine Spanish adjective for a player appears; report the outputs

## 3. Docs and full run

- [x] 3.1 Check ARCHITECTURE.md: it does not describe prompt wording, so verify no edit is needed
- [x] 3.2 Run the full suite (`python -m pytest -q` in `backend/`) and verify it passes

## 4. Approval

- [ ] 4.1 Human approval gate: stop and wait for the user to approve. After approval, run the OpenSpec archive, then open a PR and merge it after `feature/player-history-graph-rag` (the PR targets that branch, or main once it has merged)
