# Design

## Context

Pronouns come only from the model. Template explanations (`explain.py`) and the generated news (`events.py`, in en/es/zh-Hant) are pronoun-free, and the English eval text already says "his". See proposal.md for motivation.

## Goals / Non-Goals

**Goals:**
- One sentence in each of the two prompts that states the rule.

**Non-Goals:**
- No post-check or rewriting of model output; the explanation validation stays as it is.
- No change to the history parser prompt (it outputs filters, not prose).
- No gender field on the roster; all players are male by definition.

## Decisions

- **Prompt rule, not code.** A pronoun check would need per-language parsing for little gain; a prompt sentence is the same pattern as the existing status rules. Alternative considered: validate the output for "she/they/她" and fall back to templates, rejected as brittle (they is a valid word elsewhere) and it would turn a style slip into a failed call.
- **Wording.** The sentence says every player is male, lists he/him/his, él/su and 他, forbids they/she, asks for masculine Spanish adjectives, and says no gendered pronoun for a club. In the parser it adds "never add a pronoun the original lacks", so it does not conflict with "keep the original wording, add nothing".
- **Branch.** Based on `feature/player-history-graph-rag`, the trunk, so the history answer prompt is covered here too. It merges after that branch; its spec requirements live in the in-flight change, so no delta spec is written for it.
- **Test.** A unit test asserts each constant contains the rule's key terms, like the existing `test_alternatives` check on `EXPLAINER_INSTRUCTIONS`. Real-model behaviour is checked once by hand with the `.env` model.

## Risks / Trade-offs

- [The model still slips] → check a few players in all three languages and both modes before approval; the rule is advisory, as with the other prompt rules.
- [Rule makes the parser add pronouns to the translations] → the sentence limits it to pronouns already implied by the original.
