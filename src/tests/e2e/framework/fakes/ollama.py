"""A fake of Ollama's OpenAI-compatible API, for E2E tests: every chat completion streams the
same committed answer, and every request is recorded, so a test can see what the backend asked
the model."""

import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

# A chat completion stream as Ollama sends it, recorded once.
ANSWER_STREAM = Path(__file__).parent / "testdata" / "ollama_chat_stream.txt"
# The text the committed stream answers with.
ANSWER = "Hello from the fake model."
API_KEY = "e2e-ollama-api-key"


class FakeOllama:
    def __init__(self, port: int) -> None:
        self.url = f"http://127.0.0.1:{port}/v1"
        # Each chat completion request's `Authorization` header and JSON body, in order.
        self.requests: list[tuple[str, dict[str, Any]]] = []

    def user_messages(self) -> list[str]:
        """The user messages in the latest request, in order: what the model was told."""
        _, body = self.requests[-1]
        return [m["content"] for m in body["messages"] if m["role"] == "user"]


@contextmanager
def running_fake_ollama() -> Iterator[FakeOllama]:
    """Serves the fake until the block ends."""
    answer = ANSWER_STREAM.read_bytes()
    recorded: list[tuple[str, dict[str, Any]]] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            body = json.loads(self.rfile.read(int(self.headers["content-length"])))
            recorded.append((self.headers["authorization"], body))
            self.send_response(200)
            self.send_header("content-type", "text/event-stream")
            self.send_header("content-length", str(len(answer)))
            self.end_headers()
            self.wfile.write(answer)

        def log_message(self, format: str, *args: object) -> None:
            """Quiet: the test's own output says what happened."""

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    serving = threading.Thread(target=server.serve_forever, daemon=True)
    serving.start()
    fake = FakeOllama(server.server_port)
    fake.requests = recorded
    try:
        yield fake
    finally:
        server.shutdown()
        server.server_close()
