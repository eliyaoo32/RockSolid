"""Language models for tests: every agent runs on the test model the test passes in."""

from pydantic_ai.models import Model


class FakeModels:
    """Returns the same test model, such as a `FunctionModel`, for any model an agent asks for,
    and records the names asked for."""

    def __init__(self, model: Model) -> None:
        self._model = model
        self.asked_for: list[str] = []

    def ollama(self, name: str) -> Model:
        self.asked_for.append(name)
        return self._model
