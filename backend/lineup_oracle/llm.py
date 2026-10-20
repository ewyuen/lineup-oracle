from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

from dotenv import find_dotenv, load_dotenv

DEFAULT_TIMEOUT = 15.0


@dataclass(frozen=True)
class LlmSettings:
    endpoint: str
    deployment: str
    api_key: str | None = None  # None means Azure default credentials (managed identity on Azure)
    timeout: float = DEFAULT_TIMEOUT

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> LlmSettings | None:
        """Settings from LINEUP_LLM_* variables, or None (model off) unless endpoint and deployment are both set."""
        if env is None:
            load_dotenv(find_dotenv(usecwd=True))  # a .env in the working directory or above; real variables win
            env = os.environ
        endpoint, deployment = env.get("LINEUP_LLM_ENDPOINT"), env.get("LINEUP_LLM_DEPLOYMENT")
        if not endpoint or not deployment:
            return None
        return cls(endpoint, deployment, env.get("LINEUP_LLM_API_KEY") or None, float(env.get("LINEUP_LLM_TIMEOUT") or DEFAULT_TIMEOUT))


def build_client(settings: LlmSettings):
    """The Agent Framework chat client for the configured Foundry deployment."""
    from agent_framework_openai import OpenAIChatCompletionClient

    if settings.api_key:
        return OpenAIChatCompletionClient(model=settings.deployment, azure_endpoint=settings.endpoint, api_key=settings.api_key)
    from azure.identity import DefaultAzureCredential

    return OpenAIChatCompletionClient(model=settings.deployment, azure_endpoint=settings.endpoint, credential=DefaultAzureCredential())


def main() -> None:
    """One real call to check the model setup: parse a sample news line and explain a sample lineup."""
    from .pipeline import NewsRejected, Pipeline
    from .roster import generate_synthetic_roster

    pipeline = Pipeline.from_env()
    if not pipeline.enabled:
        raise SystemExit("Model off: set LINEUP_LLM_ENDPOINT and LINEUP_LLM_DEPLOYMENT (and LINEUP_LLM_API_KEY unless using Azure credentials).")
    club = next(iter(generate_synthetic_roster(42).clubs.values()))
    star = club.players[8]
    try:
        print("parse:", pipeline.interpret(f"{club.name}: {star.name} is out with a hamstring injury", club), "expected:", (star.id, "injury"))
    except NewsRejected as err:
        print("parse rejected:", err)
    facts = [{"id": star.id, "name": star.name, "position": star.position, "p_start": 0.77, "starts": 4, "played": 5, "status": "available", "best_rating": "passing"}]
    for language in ("en", "es", "zh-Hant"):
        print(language, pipeline.explain(facts, "fan", language))


if __name__ == "__main__":
    main()
