## 1. Branch

- [x] 1.1 Create the feature branch `feature/show-suspended-in-candidates` from main

## 2. Backend

- [x] 2.1 `picking.py`: add visible kinds; `eligible()` returns visible non-starters, a separate selectable check for selections, `included` and `/alternatives`; `overlay` lists suspended candidates (included false)
- [x] 2.2 `api.py`: in `team_news`, reject non-clearing news for a currently suspended player with 422 (structured and text), accept a repeated suspension; `/alternatives` still 422 for suspended
- [x] 2.3 `ingest.py`: feed ingestion ignores non-clearing events for a shared suspension; `merge` keeps a personal suspension against a later non-cleared shared entry
- [x] 2.4 Check `mcp_server.py` tool text and `backend/README.md` mention of candidates, update if they say injury or doubt only

## 3. UI

- [x] 3.1 `_Lineup.cshtml`: suspended candidate shows the Suspended badge and no form
- [x] 3.2 `UiText.resx`, `.en`, `.es`, `.zh-Hant`: rename `AlternativeCandidates` to "Unavailable players" (es "Jugadores no disponibles", zh-Hant "不可出賽球員"), add `StatusSuspended`
- [x] 3.3 Check `LineupApiClient` candidate model needs no change (kind is a string)

## 4. Tests

- [x] 4.1 Backend: suspended non-starter is in `candidates` with kind suspension and not included; `/alternatives` include returns 422 and changes no state; removal still accepted
- [x] 4.2 Backend: injury, doubt, structured or text, for a suspended player returns 422; repeated suspension accepted; text "cleared" lifts it and the player can return to the XI
- [x] 4.3 Backend: feed injury after a session suspension leaves the session suspended; session clear-then-injury is not resurrected by an older feed suspension; feed ingestion ignores injury after a shared suspension
- [x] 4.4 Backend: fix existing tests that send other news for a suspended player or expect suspended players absent from candidates
- [x] 4.5 UI: suspended candidate shows the badge and no add form, injured and doubtful keep the form; heading renders in each language

## 5. Docs and verification

- [x] 5.1 Update ARCHITECTURE.md: `candidates` includes suspended players; the suspension lock in the availability merge
- [x] 5.2 Run the full backend (`python -m pytest -q` in `backend/`) and UI test suites and fix failures

## 6. Approval gate

- [x] 6.1 HITL: summarize results and stop for the user's approval. After approval run the OpenSpec archive, then open a PR to main and merge it
