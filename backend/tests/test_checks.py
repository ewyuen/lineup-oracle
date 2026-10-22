from __future__ import annotations

from types import SimpleNamespace

import pytest

from lineup_oracle.checks import failed_rules, parse_correct

FACT = {"id": "p1", "name": "Ari Stone", "p_start": 0.62, "starts": 3, "played": 5, "status": "available"}
DOUBT = {**FACT, "status": "doubt"}
OTHERS = ["Bren Hart", "Cai Lowe"]


def rules(text, fact=FACT, mode="analyst", others=OTHERS):
    return failed_rules(text, fact, mode, others)


@pytest.mark.parametrize("text", [
    "Likely starter: P(start) 0.62, started 3 of the last 5, strong pace.",  # the template shape
    "Starts often: 3 of the last 5, 62% to start.",
    "Empieza casi siempre: 3 de los últimos 5 partidos.",
    "近5場先發3場，開季表現穩定。",
])
def test_grounded_text_in_each_language_passes(text):
    assert rules(text) == []


def test_wrong_count_fails_numbers():
    assert rules("Started 4 of the last 5.") == ["numbers"]
    assert rules("Empezó 4 de los últimos 5.") == ["numbers"]


def test_p_start_as_percentage_within_one_point():
    assert rules("About 63% likely to start.") == []
    assert rules("About 70% likely to start.") == ["numbers"]
    assert rules("P(start) 0,62.") == []  # decimal comma


def test_doubt_must_be_stated_and_only_for_a_doubtful_player():
    assert rules("A fitness doubt, but likely to start.", DOUBT) == []
    assert rules("Duda física, pero probable titular.", DOUBT) == []
    assert rules("體能有疑慮，但仍可能先發。", DOUBT) == []
    assert rules("Likely to start.", DOUBT) == ["availability"]
    assert rules("A fitness doubt for this match.") == ["availability"]
    assert rules("Aparece como duda.") == ["availability"]


def test_fit_player_is_not_called_injured_or_suspended():
    assert rules("Returns from injury.") == ["availability"]
    assert rules("Vuelve tras una lesión.") == ["availability"]
    assert rules("Back from suspension.") == ["availability"]
    assert rules("剛從傷病復出。") == ["availability"]
    assert rules("In good fitness and likely to start.") == []  # "fitness" alone is not a doubt


def test_a_teammates_name_fails_names():
    assert rules("Starts ahead of Bren Hart.") == ["names"]
    assert rules("Starts, as Ari Stone usually does.") == []  # own name is fine


def test_fan_mode_forbids_percent_and_p_start():
    assert rules("Almost always starts.", mode="fan") == []
    assert rules("Starts about 62% of the time.", mode="fan") == ["fan"]
    assert rules("P(start) is high.", mode="fan") == ["fan"]


def test_rules_are_sorted_and_deterministic():
    text = "Started 4 of 5, ahead of Bren Hart."
    assert rules(text) == rules(text) == ["names", "numbers"]


def test_zero_recent_matches_text_without_numbers_passes():
    assert rules("No recent matches.", {**FACT, "starts": 0, "played": 0}) == []


def _event(name="Ari Stone", kind="injury"):
    return SimpleNamespace(payload={"player_name": name, "kind": kind})


CLUB = SimpleNamespace(players=[SimpleNamespace(id="p1", name="Ari Stone"), SimpleNamespace(id="p2", name="Bren Hart")])


def test_parse_correct_needs_player_and_kind():
    assert parse_correct(_event(), CLUB, "p1", "injury")
    assert not parse_correct(_event(), CLUB, "p1", "doubt")  # wrong kind
    assert not parse_correct(_event(), CLUB, "p2", "injury")  # wrong player
    assert not parse_correct(_event(), CLUB, "x-unknown", "injury")  # outside the club
    assert not parse_correct(_event(), CLUB, None, None)
