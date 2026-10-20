import pytest
from pydantic_ai.models.ollama import OllamaModel

from libs.infra.llm.models import ConfiguredModels, MissingApiKeyError


def test_builds_an_ollama_model_on_the_configured_server_and_key() -> None:
    models = ConfiguredModels(ollama_base_url="https://ollama.example/v1", ollama_api_key="key-1")

    model = models.ollama("deepseek-v4.1-flash:cloud")

    assert isinstance(model, OllamaModel)
    assert model.model_name == "deepseek-v4.1-flash:cloud"
    assert model.base_url == "https://ollama.example/v1/"
    assert model.client.api_key == "key-1"
    other = models.ollama("qwen3")
    assert isinstance(other, OllamaModel)
    assert other.client is model.client, "every Ollama model shares one client"


def test_refuses_an_ollama_model_without_an_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    # The provider would fall back to this variable; the settings are the only source we allow.
    monkeypatch.setenv("OLLAMA_API_KEY", "from-the-environment")
    models = ConfiguredModels(ollama_base_url="https://ollama.example/v1", ollama_api_key=None)

    with pytest.raises(MissingApiKeyError, match=r"deepseek-v4\.1-flash:cloud runs on Ollama"):
        models.ollama("deepseek-v4.1-flash:cloud")
