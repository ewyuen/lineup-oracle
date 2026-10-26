from __future__ import annotations

import copy
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from lineup_oracle.events import generate_fixtures, generate_match_events
from lineup_oracle.history import (
    SEASON_START,
    HistoryError,
    HistoryFilters,
    kickoff,
    occurred_at,
    retrieve_player_history,
    template_answer,
)
from lineup_oracle.roster import CLUB_NAMES, generate_synthetic_roster
from lineup_oracle.state import State

ROSTER = generate_synthetic_roster(42)
EVENTS = generate_match_events(ROSTER, generate_fixtures(CLUB_NAMES), seed=42)
STATE = State(ROSTER, EVENTS)
PIA = "Pia Ash"  # harbor-city-20: two team-news items in the seed (and shots, tackles and starts, which history ignores)


def history(**kw):
    return retrieve_player_history(STATE, HistoryFilters(**{"player": PIA, **kw}))


# --- times --------------------------------------------------------------


def test_kickoffs_are_a_week_apart():
    assert kickoff(1) == SEASON_START
    assert kickoff(2) - kickoff(1) == timedelta(days=7)
    assert kickoff(10) - kickoff(9) == timedelta(days=7)


def test_team_news_of_one_matchday_shares_a_kickoff_base():
    news = [e for e in EVENTS if e.type == "team_news" and e.minute == -24]
    for e in news[:5]:
        day = STATE.metadata[e.match_id].payload["matchday"]
        assert occurred_at(e, day) == kickoff(day) - timedelta(hours=24)


def test_team_news_counts_offsets_as_hours_and_play_as_minutes():
    news = next(e for e in EVENTS if e.type == "team_news" and e.minute == -48)
    shot = next(e for e in EVENTS if e.type == "shot")
    assert occurred_at(news, 3) == kickoff(3) - timedelta(hours=48)
    exact = kickoff(3) + timedelta(minutes=shot.minute)
    assert occurred_at(shot, 3) == exact.replace(microsecond=exact.microsecond // 1000 * 1000)  # kept to the millisecond


# --- retrieval ----------------------------------------------------------


def test_history_is_ordered_by_time_then_id_and_has_the_expected_shape():
    h = history()
    assert h.player.id == "harbor-city-20"
    keys = [(i.occurred_at, i.id) for i in h.items]
    assert keys == sorted(keys)
    assert {i.type for i in h.items} == {"team_news"}
    item = h.items[0].to_dict()
    assert set(item) == {"id", "type", "match_id", "club", "occurred_at", "payload"}
    assert item["occurred_at"].endswith("Z")
    assert all(i.club == "Harbor City" for i in h.items)


def test_id_and_name_give_the_same_history():
    assert history().items == history(player="harbor-city-20").items


def test_only_team_news_is_returned():
    assert len(history().items) == 2 and {i.type for i in history().items} == {"team_news"}


def test_filter_by_range():
    items = history().items
    assert history(start=items[1].occurred_at).items == items[1:]  # inclusive
    assert history(end=items[0].occurred_at).items == items[:1]
    assert history(start=items[-1].occurred_at + timedelta(days=100)).items == []


def test_naive_times_are_read_as_utc():
    at = history().items[1].occurred_at
    assert history(start=at.replace(tzinfo=None), end=at.replace(tzinfo=None)).items == [i for i in history().items if i.occurred_at == at]


def test_filter_by_match():
    match = history().items[0].match_id
    items = history(match=match).items
    assert items and {i.match_id for i in items} == {match}


def test_team_news_is_linked_by_payload_name():
    news = history().items
    assert len(news) == 2
    assert all(PIA in i.payload["text"] and i.payload["kind"] in {"injury", "suspension", "doubt"} for i in news)
    # no other player's history contains these events
    other = retrieve_player_history(STATE, HistoryFilters("harbor-city-1")).items
    assert not {i.id for i in news} & {i.id for i in other}


def test_team_news_that_names_nobody_fails_with_the_event_id():
    events = copy.deepcopy(EVENTS)
    bad = next(e for e in events if e.type == "team_news")
    bad.payload["player_name"] = "Nobody Here"
    with pytest.raises(HistoryError, match=bad.id):
        retrieve_player_history(State(ROSTER, events), HistoryFilters(PIA))


def test_unknown_player_is_rejected_by_name():
    with pytest.raises(HistoryError, match="Unknown player 'Zed Zed'"):
        history(player="Zed Zed")


def test_ambiguous_name_lists_the_candidates():
    roster = copy.deepcopy(ROSTER)
    first, second = roster.clubs["Harbor City"].players[0], roster.clubs["Westbrook"].players[0]
    events = copy.deepcopy(EVENTS)
    for e in events:
        if e.type == "team_news" and e.club == "Westbrook" and e.payload["player_name"] == second.name:
            e.payload["player_name"] = first.name
    roster.clubs["Westbrook"].players[0] = replace(second, name=first.name)
    state = State(roster, events)
    with pytest.raises(HistoryError, match=f"{first.id}, {second.id}"):
        retrieve_player_history(state, HistoryFilters(first.name))
    assert retrieve_player_history(state, HistoryFilters(first.id)).player.id == first.id  # an id still works


@pytest.mark.parametrize(
    "kw, message",
    [
        ({"match": "match-999"}, "Unknown match"),
        ({"start": datetime(2026, 9, 1, tzinfo=timezone.utc), "end": datetime(2026, 8, 1, tzinfo=timezone.utc)}, "ends before it starts"),
    ],
)
def test_bad_filters_are_rejected(kw, message):
    with pytest.raises(HistoryError, match=message):
        history(**kw)


def test_used_filters_carry_the_resolved_player():
    assert history().filters_dict() == {"player": "harbor-city-20", "from": None, "to": None, "match": None}


# --- template answer ----------------------------------------------------


def test_template_for_a_normal_history():
    text = template_answer(history())
    assert text.startswith("Pia Ash (Harbor City): 2 team news items. 2026-")
    assert text.count("[Harbor City-match-") == 2  # each item cites its id


def test_template_singular_and_empty():
    one = history(match=history().items[0].match_id)
    assert template_answer(one).startswith("Pia Ash (Harbor City): 1 team news item. ")
    empty = history(start=kickoff(50))
    assert template_answer(empty) == "No team news found for Pia Ash (Harbor City) with these filters."


def test_a_name_shared_within_a_club_fails_instead_of_guessing():
    roster = copy.deepcopy(ROSTER)
    club = roster.clubs["Harbor City"]
    club.players[1] = replace(club.players[1], name=club.players[0].name)
    with pytest.raises(HistoryError, match="share a name"):
        retrieve_player_history(State(roster, copy.deepcopy(EVENTS)), HistoryFilters(club.players[0].id))
