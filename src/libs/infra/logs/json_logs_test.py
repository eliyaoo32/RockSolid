import json
import logging
import sys

import pytest

from libs.infra.logs.json_logs import JsonFormatter, configure_logging, request_id


def format_record(message: str, *args: object, exc: bool = False) -> dict[str, object]:
    exc_info = None
    if exc:
        try:
            raise ValueError("boom")
        except ValueError:
            exc_info = sys.exc_info()
    record = logging.LogRecord("clients", logging.WARNING, __file__, 1, message, args, exc_info)
    return json.loads(JsonFormatter().format(record))


def test_writes_one_json_object_per_record() -> None:
    entry = format_record("listed %d clients", 3)

    assert entry["level"] == "WARNING"
    assert entry["logger"] == "clients"
    assert entry["message"] == "listed 3 clients"
    assert str(entry["time"]).endswith("+00:00")
    assert "request_id" not in entry
    assert "error" not in entry


def test_adds_the_current_request_id_and_the_error() -> None:
    token = request_id.set("req-123")
    try:
        entry = format_record("failed", exc=True)
    finally:
        request_id.reset(token)

    assert entry["request_id"] == "req-123"
    assert "ValueError: boom" in str(entry["error"])


def test_configures_the_root_logger_to_write_json(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging()
    logging.getLogger("clients").info("ready")

    assert json.loads(capsys.readouterr().out)["message"] == "ready"
