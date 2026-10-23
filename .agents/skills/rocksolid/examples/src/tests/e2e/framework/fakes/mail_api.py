"""A fake of the mail API, the third party that sends the clients module's email, for component
and E2E tests: it records every message it is asked to send, and answers 503 to the requests a test
tells it to fail."""

import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

API_KEY = "e2e-mail-api-key"


class FakeMailApi:
    def __init__(self, port: int) -> None:
        self.url = f"http://127.0.0.1:{port}"
        # The clients module's settings that point it at this fake.
        self.environment = {"CLIENTS_MAIL_API_URL": self.url, "CLIENTS_MAIL_API_KEY": API_KEY}
        # Each message's path, `Authorization` header, and JSON body, in the order it came.
        self.messages: list[tuple[str, str, dict[str, Any]]] = []
        # How many of the next requests answer 503 and send nothing.
        self.failures = 0


@contextmanager
def serve() -> Iterator[FakeMailApi]:
    """Serves the fake until the block ends."""

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            body = json.loads(self.rfile.read(int(self.headers["content-length"])))
            if fake.failures:
                fake.failures -= 1
                self.send_response(503)
            else:
                fake.messages.append((self.path, self.headers["authorization"], body))
                self.send_response(202)
            self.send_header("content-length", "0")
            self.end_headers()

        def log_message(self, format: str, *args: object) -> None:
            """Quiet: the test's own output says what happened."""

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    fake = FakeMailApi(server.server_port)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield fake
    finally:
        server.shutdown()
        server.server_close()
