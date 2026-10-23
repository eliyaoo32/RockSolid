import httpx

from e2e.framework.fakes.ollama import ANSWER_STREAM, API_KEY, serve


def test_streams_the_committed_answer_and_records_what_it_was_asked() -> None:
    messages = [{"role": "system", "content": "Be brief."}, {"role": "user", "content": "Hi"}]
    with serve() as ollama:
        response = httpx.post(
            f"{ollama.url}/chat/completions",
            json={"messages": messages},
            headers={"authorization": "Bearer the-api-key"},
        )

    assert response.content == ANSWER_STREAM.read_bytes()
    assert [authorization for authorization, _ in ollama.requests] == ["Bearer the-api-key"]
    assert ollama.user_messages() == ["Hi"]
    assert ollama.environment == {"OLLAMA_BASE_URL": ollama.url, "OLLAMA_API_KEY": API_KEY}
