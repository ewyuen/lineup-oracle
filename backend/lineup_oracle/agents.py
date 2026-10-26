from __future__ import annotations

from typing import Literal

from agent_framework import Agent
from pydantic import BaseModel, ConfigDict, Field


class Person(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    player_id: str | None = None  # set by the model only for a player of the selected club's roster


class ParsedNews(BaseModel):
    model_config = ConfigDict(extra="ignore")  # anything beyond these fields is dropped, so the model cannot add an XI

    club: str | None = None
    player_id: str | None = None
    kind: Literal["injury", "suspension", "doubt", "recovered", "cleared", "fit"] | None = None
    persons: list[Person] = []
    translations: dict[str, str] | None = None  # en, es, zh-Hant; used only when the line is posted


class PlayerExplanation(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    text: str


class Explanations(BaseModel):
    model_config = ConfigDict(extra="ignore")

    explanations: list[PlayerExplanation]


class ParsedHistoryQuestion(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    player: str | None = None
    types: list[str] | None = None
    from_: str | None = Field(None, alias="from")
    to: str | None = None
    match: str | None = None


class HistoryAnswer(BaseModel):
    model_config = ConfigDict(extra="ignore")

    answer: str
    cited_event_ids: list[str]


MALE_PLAYERS_RULE = (
    "Every player is male: refer to a player as he, him or his (él or su in Spanish, 他 in Traditional Chinese), never they, she or 她, "
    "and use masculine Spanish adjectives for a player. Use no gendered pronoun for a club. "
)

PARSER_INSTRUCTIONS = (
    "You read one line of football team news, in any language, and extract who and what it is about. "
    "You receive JSON with the club, its roster (id, name, number, position) and the text. "
    "Answer with JSON only: {\"club\": the club the text is about or null, \"player_id\": the roster id of the one player "
    "of this roster the text is about or null, \"kind\": \"injury\" (hurt or ruled out), \"suspension\" (banned or red card), "
    "\"doubt\" (fitness doubt, late test), \"recovered\" (injury healed, back in training), \"cleared\" (suspension served) "
    "or \"fit\" (doubt resolved, declared fit) or null, "
    "\"persons\": [{\"name\": every person the text names, exactly as written, \"player_id\": the roster id when the person is "
    "a player of this roster, else null}] (an owner, buyer or coach is a person too; an empty list if the text names no one), "
    "\"translations\": {\"en\": the line in English, \"es\": in Spanish, \"zh-Hant\": in Traditional Chinese; keep the original "
    "wording and every name verbatim, add nothing}}. "
    + MALE_PLAYERS_RULE + "In the translations never add a pronoun the original lacks. "
    "Use only ids from the roster. If the text names no player of this roster or no clear kind, use null. Never invent ids."
)

EXPLAINER_INSTRUCTIONS = (
    "You write one short sentence per player explaining why the player is likely to start, or for a player with status out why not. "
    "You receive JSON with a mode, a language and a list of players with facts (id, name, position, p_start, starts, played, status, best_rating). "
    "Use only these facts, nothing else, and do not invent events or real-world names. "
    "Write every sentence in the requested language (en English, es Spanish, zh-Hant Traditional Chinese), at most 25 words. "
    + MALE_PLAYERS_RULE +
    "In mode analyst you may quote p_start as a percentage and the counts. In mode fan write plain words: no numbers with percent signs and no probabilities. "
    "A status of doubt means a fitness doubt; mention it. "
    "A status of out means the player is injured or unavailable and not expected to start; say so and never call such a player a likely starter. "
    "Answer with JSON only: {\"explanations\": [{\"id\": the player id, \"text\": the sentence}]} with exactly one entry per player, using the same ids."
)


def parser_agent(client) -> Agent:
    return Agent(client, PARSER_INSTRUCTIONS, name="news-parser")


def explainer_agent(client) -> Agent:
    return Agent(client, EXPLAINER_INSTRUCTIONS, name="explainer")


HISTORY_PARSER_INSTRUCTIONS = (
    "You turn one question about what happened to a football player into search filters. "
    "You receive JSON with the question and the kickoff time of every matchday and the current time now (ISO 8601, UTC). "
    "Answer with JSON only: {\"player\": the player's full name exactly as written in the question, \"types\": a list of the event types the question asks about, "
    "from shot, tackle, team_news (injuries, suspensions and doubts) and started (matches the player started), or null for all, "
    "\"from\": start of the time range as ISO 8601 or null, \"to\": end of the time range as ISO 8601 or null, \"match\": a match id or null}. "
    "Map phrases such as \"before matchday 3\" or \"after matchday 2\" to the kickoff times you were given. "
    "Map \"today\" or \"this week\" to a range ending at now. "
    "Use null for anything the question does not say. Never invent a player."
)

HISTORY_ANSWER_INSTRUCTIONS = (
    "You answer a question about what happened to a football player, using only the events you receive. "
    "You receive JSON with the question, the filters and the events (id, type, match_id, club, occurred_at, payload), oldest first. "
    "Use only these events, nothing else, and add no outside knowledge about real players or clubs. Be brief: at most 80 words. "
    + MALE_PLAYERS_RULE +
    "Answer with JSON only: {\"answer\": the answer text, \"cited_event_ids\": the ids of every event the answer relies on}. "
    "Cite only ids you received."
)


def history_parser_agent(client) -> Agent:
    return Agent(client, HISTORY_PARSER_INSTRUCTIONS, name="history-parser")


def history_answer_agent(client) -> Agent:
    return Agent(client, HISTORY_ANSWER_INSTRUCTIONS, name="history-answerer")
