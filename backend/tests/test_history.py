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
PIA = "Pia Ash"  # harbor-city-20: shots, tackles, two team-news items and three starts in the seed


def history(**kw):
    return retrieve_player_history(STATE, HistoryFilters(**{"player": PIA, **kw}))


# --- times --------------------------------------------------------------


def test_kickoffs_are_a_week_apart():
    assert kickoff(1) == SEASON_START
    assert kickoff(2) - kickoff(1) == timedelta(days=7)
    assert kickoff(10) - kickoff(9) == timedelta(days=7)


def test_events_of_one_matchday_share_a_kickoff_base():
    metas = [m for m in STATE.metadata.values() if m.payload["matchday"] == 2]
    assert len(metas) == 3
    for m in metas:
        items = retrieve_player_history(STATE, HistoryFilters(m.payload["home_xi"][0], ("started",), match=m.match_id)).items
        assert items[0].occurred_at == kickoff(2)


def test_team_news_counts_offsets_as_hours_and_play_as_minutes():
    news = next(e for e in EVENTS if e.type == "team_news" and e.minute == -48)
    shot = next(e for e in EVENTS if e.type == "shot")
    assert occurred_at(news, 3) == kickoff(3) - timedelta(hours=48)
    assert occurred_at(shot, 3) == kickoff(3) + timedelta(minutes=shot.minute)


# --- retrieval ----------------------------------------------------------


def test_history_is_ordered_by_time_then_id_and_has_the_expected_shape():
    h = history()
    assert h.player.id == "harbor-city-20"
    keys = [(i.occurred_at, i.id) for i in h.items]
    assert keys == sorted(keys)
    assert {i.type for i in h.items} == {"shot", "tackle", "team_news", "started"}
    item = h.items[0].to_dict()
    assert set(item) == {"id", "type", "match_id", "club", "occurred_at", "payload"}
    assert item["occurred_at"].endswith("Z")
    assert all(i.club == "Harbor City" for i in h.items)


def test_id_and_name_give_the_same_history():
    assert history().items == history(player="harbor-city-20").items


def test_only_player_history_types_are_returned():
    assert {i.type for i in history().items} <= {"shot", "tackle", "team_news", "started"}


def test_filter_by_type_and_range():
    all_shots = history(types=("shot",)).items
    assert all_shots and {i.type for i in all_shots} == {"shot"}
    lo, hi = all_shots[1].occurred_at, all_shots[-2].occurred_at
    inside = history(types=("shot",), start=lo, end=hi).items
    assert inside == all_shots[1:-1]  # both ends inclusive
    assert history(types=("shot",), start=hi + timedelta(days=100)).items == []


def test_naive_times_are_read_as_utc():
    at = history().items[3].occurred_at
    assert history(start=at.replace(tzinfo=None), end=at.replace(tzinfo=None)).items == [i for i in history().items if i.occurred_at == at]


def test_filter_by_match():
    match = history().items[0].match_id
    items = history(match=match).items
    assert items and {i.match_id for i in items} == {match}


def test_started_items_come_from_the_metadata_and_can_be_excluded():
    h = history()
    started = [i for i in h.items if i.type == "started"]
    assert len(started) == 3
    assert all(i.occurred_at == kickoff(STATE.metadata[i.match_id].payload["matchday"]) for i in started)
    assert all(h.player.id in STATE.metadata[i.match_id].payload["home_xi"] + STATE.metadata[i.match_id].payload["away_xi"] for i in started)
    assert not [i for i in history(types=("shot", "tackle")).items if i.type == "started"]
    assert {i.type for i in history(types=("started",)).items} == {"started"}


def test_team_news_is_linked_by_payload_name():
    news = history(types=("team_news",)).items
    assert len(news) == 2
    assert all(PIA in i.payload["text"] and i.payload["kind"] in {"injury", "suspension", "doubt"} for i in news)
    # no other player's history contains these events
    other = retrieve_player_history(STATE, HistoryFilters("harbor-city-1", ("team_news",))).items
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
        ({"types": ("pass",)}, "Unknown event type 'pass'"),
        ({"match": "match-999"}, "Unknown match"),
        ({"start": datetime(2026, 9, 1, tzinfo=timezone.utc), "end": datetime(2026, 8, 1, tzinfo=timezone.utc)}, "ends before it starts"),
    ],
)
def test_bad_filters_are_rejected(kw, message):
    with pytest.raises(HistoryError, match=message):
        history(**kw)


def test_used_filters_carry_the_resolved_player():
    assert history().filters_dict() == {"player": "harbor-city-20", "types": None, "from": None, "to": None, "match": None}


# --- template answer ----------------------------------------------------


def test_template_for_a_normal_history():
    text = template_answer(history())
    assert text.startswith("Pia Ash (Harbor City): ")
    assert "shots" in text and "tackles" in text and "started 3 matches" in text
    assert text.count("[Harbor City-match-") == 2  # each team-news item cites its id


def test_template_singular_and_empty():
    one = history(types=("started",), match=history(types=("started",)).items[0].match_id)
    assert template_answer(one) == "Pia Ash (Harbor City): started 1 match."
    empty = history(types=("shot",), start=kickoff(50))
    assert template_answer(empty) == "Nothing found for Pia Ash (Harbor City) with these filters."


def test_template_with_team_news_only():
    text = template_answer(history(types=("team_news",)))
    assert text.startswith("Pia Ash (Harbor City): no shots, tackles or starts. Team news: 2026-")


def test_a_name_shared_within_a_club_fails_instead_of_guessing():
    roster = copy.deepcopy(ROSTER)
    club = roster.clubs["Harbor City"]
    club.players[1] = replace(club.players[1], name=club.players[0].name)
    with pytest.raises(HistoryError, match="share a name"):
        retrieve_player_history(State(roster, copy.deepcopy(EVENTS)), HistoryFilters(club.players[0].id))
