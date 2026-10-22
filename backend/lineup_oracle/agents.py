from __future__ import annotations

from typing import Literal

from agent_framework import Agent
from pydantic import BaseModel, ConfigDict


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
    "Use only ids from the roster. If the text names no player of this roster or no clear kind, use null. Never invent ids."
)

EXPLAINER_INSTRUCTIONS = (
    "You write one short sentence per player explaining why the player is likely to start, or for a player with status out why not. "
    "You receive JSON with a mode, a language and a list of players with facts (id, name, position, p_start, starts, played, status, best_rating). "
    "Use only these facts, nothing else, and do not invent events or real-world names. "
    "Write every sentence in the requested language (en English, es Spanish, zh-Hant Traditional Chinese), at most 25 words. "
    "In mode analyst you may quote p_start as a percentage and the counts. In mode fan write plain words: no numbers with percent signs and no probabilities. "
    "A status of doubt means a fitness doubt; mention it. "
    "A status of out means the player is injured or unavailable and not expected to start; say so and never call such a player a likely starter. "
    "Answer with JSON only: {\"explanations\": [{\"id\": the player id, \"text\": the sentence}]} with exactly one entry per player, using the same ids."
)


def parser_agent(client) -> Agent:
    return Agent(client, PARSER_INSTRUCTIONS, name="news-parser")


def explainer_agent(client) -> Agent:
    return Agent(client, EXPLAINER_INSTRUCTIONS, name="explainer")
