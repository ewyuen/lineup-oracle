import pytest

from lineup_oracle.agents import EXPLAINER_INSTRUCTIONS, HISTORY_ANSWER_INSTRUCTIONS, PARSER_INSTRUCTIONS


@pytest.mark.parametrize("prompt", [EXPLAINER_INSTRUCTIONS, PARSER_INSTRUCTIONS, HISTORY_ANSWER_INSTRUCTIONS])
def test_prompt_says_every_player_is_male(prompt):
    for term in ("Every player is male", "he, him or his", "él", "他", "never they, she", "masculine Spanish", "club"):
        assert term in prompt


def test_parser_adds_no_pronoun_the_original_lacks():
    assert "never add a pronoun the original lacks" in PARSER_INSTRUCTIONS
