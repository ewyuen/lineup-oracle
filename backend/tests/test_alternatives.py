from __future__ import annotations

import copy

import pytest
from fastapi.testclient import TestClient

from lineup_oracle.api import create_app
from lineup_oracle.events import generate_fixtures, generate_match_events
from lineup_oracle.ingest import Feed
from lineup_oracle.optimizer import POSITIONS
from lineup_oracle.pipeline import Pipeline
from lineup_oracle.roster import CLUB_NAMES, generate_synthetic_roster
from lineup_oracle.state import State

from fake_llm import FakeClient, explain_all

ROSTER = generate_synthetic_roster(42)
EVENTS = generate_match_events(ROSTER, generate_fixtures(CLUB_NAMES), seed=42)
POS = "MID"


@pytest.fixture
def state() -> State:
    return State(ROSTER, copy.deepcopy(EVENTS))


@pytest.fixture
def client(state) -> TestClient:
    return TestClient(create_app(state, Pipeline()))


class Scene:
    """One match and club, with helpers to post requests as a session."""

    def __init__(self, client: TestClient, session: str = "s") -> None:
        self.client, self.session = client, session
        self.match = next(m for m in client.get("/matches").json() if m["matchday"] == 4)
        self.club = self.match["home_club"]
        self.base = self.lineup(session="natural")
        self.starters = {p["id"] for p in self.base["players"]}
        natural = [p["id"] for p in self.base["alternatives"][POS]]
        self.natural = natural
        # players of POS who do not start, and those of them who are not natural alternatives, in id order
        self.pool = [p.id for p in ROSTER.clubs[self.club].players if p.position == POS and p.id not in self.starters]
        self.deep = [i for i in self.pool if i not in natural]
        assert len(self.pool) >= 4 and len(natural) == 2 and len(self.deep) >= 2

    def body(self, **extra):
        return {"match_id": self.match["match_id"], "club": self.club, "session_id": self.session, **extra}

    def lineup(self, **extra):
        return self.client.post("/predict_lineup", json=self.body(**extra)).json()

    def lineup_response(self):
        return self.client.post("/predict_lineup", json=self.body())

    def news(self, player_id, kind, **extra):
        return self.client.post("/team_news", json=self.body(player_id=player_id, kind=kind, **extra))

    def select(self, player_id, included=True, **extra):
        return self.client.post("/alternatives", json=self.body(player_id=player_id, included=included, **extra))

    def alts(self, response, pos=POS):
        return [p["id"] for p in response.json()["alternatives"][pos]]


@pytest.fixture
def scene(client) -> Scene:
    return Scene(client)


def _candidate(lineup, player_id):
    return next((c for c in lineup["candidates"] if c["id"] == player_id), None)


def test_every_player_has_a_status(scene):
    players = scene.base["players"] + [p for pos in POSITIONS for p in scene.base["alternatives"][pos]]
    assert {p["status"] for p in players} <= {"available", "doubt", "out"}
    assert scene.base["candidates"] == []


def test_include_an_injured_player_keeps_xi_and_status(scene, state):
    a = scene.deep[0]
    scene.news(a, "injury")
    before = scene.lineup()
    assert _candidate(before, a) == {"id": a, "name": ROSTER_NAME(a), "number": _number(a), "position": POS, "kind": "injury", "included": False}
    after = scene.select(a).json()
    assert after["players"] == before["players"] and after["formation"] == before["formation"]
    alts = after["alternatives"][POS]
    assert [p["id"] for p in alts] == [before["alternatives"][POS][0]["id"], a]  # the lowest-ranked one was displaced
    injured = alts[1]
    assert injured["status"] == "out" and injured["p_start"] == 0
    assert injured["explanation"].startswith("Injured or unavailable, not expected to start") and "Likely starter" not in injured["explanation"]
    assert _candidate(after, a)["included"] is True
    assert state.availability[("s", scene.match["match_id"], scene.club)][a][0] == "injury"  # still injured
    back = scene.select(a, False).json()
    assert back["alternatives"] == before["alternatives"] and _candidate(back, a)["included"] is False


def test_include_a_doubtful_player_below_the_top_two(scene):
    a = scene.deep[0]
    scene.news(a, "doubt")
    before = scene.lineup()
    assert a not in [p["id"] for p in before["alternatives"][POS]]
    after = scene.select(a).json()
    entry = next(p for p in after["alternatives"][POS] if p["id"] == a)
    assert entry["status"] == "doubt" and 0 < entry["p_start"] < 1
    assert len(after["alternatives"][POS]) == 2 and after["players"] == before["players"]


def test_include_a_player_who_is_already_a_natural_alternative(scene):
    n = scene.natural[0]
    for other in scene.deep:  # only the two natural alternatives are left to rank
        scene.news(other, "injury")
    scene.news(n, "doubt")
    before = scene.lineup()
    shown = [p["id"] for p in before["alternatives"][POS]]
    assert n in shown and _candidate(before, n)["included"] is False
    after = scene.select(n).json()
    assert [p["id"] for p in after["alternatives"][POS]] == shown  # rank order and the others unchanged
    assert _candidate(after, n)["included"] is True


def test_latest_selections_win_and_order_is_oldest_first(scene):
    a, b, c = scene.pool[:3]
    for p in (a, b, c):
        scene.news(p, "injury")
    rest = scene.alts(scene.lineup_response())  # the one non-starter left is the only natural alternative
    assert len(rest) == 1
    assert scene.alts(scene.select(a)) == rest + [a]
    assert scene.alts(scene.select(b)) == [a, b]
    assert scene.alts(scene.select(c)) == [b, c]  # a is stored but hidden
    assert _candidate(scene.lineup(), a)["included"] is False
    assert scene.alts(scene.select(b)) == [b, c]  # already shown: nothing moves
    assert scene.alts(scene.select(a)) == [c, a]  # a hidden selection becomes the newest
    assert scene.alts(scene.select(b)) == [a, b]
    assert scene.alts(scene.select(c)) == [b, c]
    assert scene.alts(scene.select(c, False)) == [a, b]  # removal brings back the most recent hidden selection


def test_removing_everything_restores_the_natural_alternatives(scene, state):
    a, b = scene.deep[:2]
    scene.news(a, "injury"), scene.news(b, "doubt")
    base = scene.lineup()["alternatives"]
    scene.select(a), scene.select(b)
    scene.select(a, False)
    assert scene.select(b, False).json()["alternatives"] == base
    assert state.selections == {}


def test_repeating_a_request_changes_nothing(scene):
    a = scene.deep[0]
    scene.news(a, "injury")
    assert scene.select(a).json() == scene.select(a).json()
    assert scene.select(a, False).json() == scene.select(a, False).json()


def test_rejections_change_nothing(scene, state):
    a = scene.deep[0]
    starter = next(iter(scene.starters))
    foreign = ROSTER.clubs[scene.match["away_club"]].players[0].id
    scene.news(a, "suspension")
    before = scene.lineup()
    for player in (starter, scene.deep[1], foreign, a, "nobody"):  # starter, no news, other club, suspended, unknown
        response = scene.select(player)
        assert response.status_code == 422 and response.json()["detail"], player
    assert scene.client.post("/alternatives", json=scene.body(player_id=a, included=True, club="Nowhere")).status_code == 422
    assert scene.client.post("/alternatives", json={**scene.body(player_id=a, included=True), "club": scene.match["away_club"] if False else "Nowhere FC"}).status_code == 422
    assert scene.client.post("/alternatives", json={**scene.body(player_id=a, included=True), "match_id": "nope"}).status_code == 404
    assert scene.client.post("/alternatives", json=scene.body(player_id=a)).status_code == 422  # included missing
    assert state.selections == {} and scene.lineup() == before


def test_removal_is_always_accepted(scene, state):
    assert scene.select(next(iter(scene.starters)), False).status_code == 200
    assert scene.select("nobody", False).status_code == 422  # not a player of the club at all
    assert scene.select(scene.deep[0], False).status_code == 200 and state.selections == {}


def test_selections_stay_in_their_session_match_and_club(scene, state):
    a = scene.deep[0]
    scene.news(a, "injury")
    scene.select(a)
    mine = scene.lineup()
    assert a in [p["id"] for p in mine["alternatives"][POS]]
    assert scene.lineup(session_id="other") == scene.base  # no news, no selection
    other_club = scene.client.post("/predict_lineup", json=scene.body(club=scene.match["away_club"])).json()
    assert other_club["candidates"] == []
    other_match = next(m for m in scene.client.get("/matches").json() if m["matchday"] == 5)
    assert scene.client.post("/predict_lineup", json=scene.body(match_id=other_match["match_id"], club=other_match["home_club"])).json()["candidates"] == []
    assert set(state.selections) == {("s", scene.match["match_id"], scene.club)}


def test_suspension_after_selection_hides_it_and_the_next_change_discards_it(scene, state):
    a, b = scene.deep[:2]
    scene.news(a, "injury"), scene.news(b, "injury")
    scene.select(a)
    scene.news(a, "suspension")
    after = scene.lineup()
    assert a not in [p["id"] for p in after["alternatives"][POS]] and _candidate(after, a) is None
    key = ("s", scene.match["match_id"], scene.club)
    assert state.selections[key] == (a,)  # kept until the next change
    scene.select(b)
    assert state.selections[key] == (b,)
    assert scene.select(a).status_code == 422


def test_promotion_into_the_xi_hides_the_selection(scene, state):
    d = scene.natural[0]
    for other in scene.pool:  # d is the only fit-or-doubtful non-starter of its position
        scene.news(other, "doubt" if other == d else "injury")
    scene.select(d)
    key = ("s", scene.match["match_id"], scene.club)
    scene.news(next(p["id"] for p in scene.base["players"] if p["position"] == POS), "injury")  # d is promoted to cover
    lineup = scene.lineup()
    assert d in [p["id"] for p in lineup["players"]]
    assert d not in [p["id"] for p in lineup["alternatives"][POS]] and _candidate(lineup, d) is None
    assert state.selections[key] == (d,)
    other = next(c["id"] for c in lineup["candidates"] if c["position"] == POS)
    scene.select(other)
    assert state.selections[key] == (other,)


# --- shared feed ------------------------------------------------------


@pytest.fixture
def feed_scene(state):
    app = create_app(state, Pipeline())
    app.state.feed = Feed(state, None)
    return Scene(TestClient(app)), app.state.feed


def test_selection_only_session_overlays_the_stored_prediction(feed_scene, monkeypatch):
    scene, feed = feed_scene
    a = scene.deep[0]
    key = (scene.match["match_id"], scene.club)
    feed._shared[key] = {a: ("injury", 1)}
    feed._predictions.clear()
    stored = feed.prediction(*key)
    snapshot = copy.deepcopy(stored)
    import lineup_oracle.api as api

    monkeypatch.setattr(api, "pick", lambda *args: pytest.fail("a selection-only session must not re-run the optimizer"))
    after = scene.select(a).json()
    assert a in [p["id"] for p in after["alternatives"][POS]]
    assert scene.lineup(session_id="other") == scene.lineup(session_id="third")
    assert a not in [p["id"] for p in scene.lineup(session_id="other")["alternatives"][POS]]
    assert feed.prediction(*key)[0] is stored[0] and feed.prediction(*key)[1] is stored[1]
    assert (stored[0].alternatives, stored[1]) == (snapshot[0].alternatives, snapshot[1])  # the shared objects were not touched


def test_feed_lap_reset_hides_the_selection(feed_scene):
    scene, feed = feed_scene
    a = scene.deep[0]
    key = (scene.match["match_id"], scene.club)
    feed._shared[key] = {a: ("doubt", 1)}
    feed._predictions.clear()
    scene.select(a)
    assert a in [p["id"] for p in scene.lineup()["alternatives"][POS]]
    feed._reset()  # the player has "recovered"
    after = scene.lineup()
    assert a not in [p["id"] for p in after["alternatives"][POS]] and _candidate(after, a) is None


# --- explanations -----------------------------------------------------


def _with_model(state, handler):
    return TestClient(create_app(state, Pipeline(FakeClient(handler))))


def test_model_must_cover_a_manual_alternative(state):
    seen = []

    def handler(payload):
        seen.append(payload)
        return explain_all(payload, "Not expected to start: injured.")

    scene = Scene(_with_model(state, handler))
    a = scene.deep[0]
    scene.news(a, "injury")
    response = scene.select(a).json()
    assert response["llm_used"] is True
    assert any(p["id"] == a and p["status"] == "out" for p in seen[-1]["players"])
    assert next(p for p in response["alternatives"][POS] if p["id"] == a)["explanation"] == "Not expected to start: injured."

    def forgetful(payload):
        answer = explain_all(payload)
        answer["explanations"] = [e for e in answer["explanations"] if e["id"] != a]
        return answer

    scene = Scene(_with_model(State(ROSTER, copy.deepcopy(EVENTS)), forgetful))
    scene.news(a, "injury")
    response = scene.select(a).json()
    assert response["llm_used"] is False
    assert next(p for p in response["alternatives"][POS] if p["id"] == a)["explanation"].startswith("Injured or unavailable")


def test_explainer_instructions_cover_unavailable_players():
    from lineup_oracle.agents import EXPLAINER_INSTRUCTIONS

    assert "out" in EXPLAINER_INSTRUCTIONS and "not expected to start" in EXPLAINER_INSTRUCTIONS


def test_template_for_an_injured_player():
    from lineup_oracle.explain import explain

    player = ROSTER.clubs["Harbor City"].players[8]
    text = explain(player, 0.0, 0, 5, "out", "fan")
    assert text.startswith("Injured or unavailable, not expected to start:") and "Likely starter" not in text and "P(start)" not in text
    assert "P(start) 0.00" in explain(player, 0.0, 0, 5, "out")


def ROSTER_NAME(player_id):
    return next(p.name for c in ROSTER.clubs.values() for p in c.players if p.id == player_id)


def _number(player_id):
    return next(p.number for c in ROSTER.clubs.values() for p in c.players if p.id == player_id)
