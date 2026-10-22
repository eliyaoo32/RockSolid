"""The language models an agent executable chooses from. Each executable names its own model;
the deployable's settings say where each provider runs and how to sign in to it."""

from functools import cached_property
from typing import Protocol

from pydantic_ai.models import Model
from pydantic_ai.models.ollama import OllamaModel
from pydantic_ai.providers.ollama import OllamaProvider


class MissingApiKeyError(ValueError):
    """An agent asked for a provider's model, and the deployable has no API key for it."""


class Models(Protocol):
    def ollama(self, name: str) -> Model:
        """The Ollama model with this name, such as `deepseek-v4.1-flash:cloud`. Raises
        MissingApiKeyError when no Ollama API key is configured."""
        ...


class ConfiguredModels:
    """Builds each provider's models from the deployable's settings."""

    def __init__(self, ollama_base_url: str, ollama_api_key: str | None) -> None:
        self._ollama_base_url = ollama_base_url
        self._ollama_api_key = ollama_api_key

    def ollama(self, name: str) -> Model:
        if not self._ollama_api_key:
            raise MissingApiKeyError(f"{name} runs on Ollama, so OLLAMA_API_KEY must be set")
        return OllamaModel(name, provider=self._ollama)

    @cached_property
    def _ollama(self) -> OllamaProvider:
        # Both values are passed, so the provider never falls back to reading the environment.
        return OllamaProvider(base_url=self._ollama_base_url, api_key=self._ollama_api_key)
