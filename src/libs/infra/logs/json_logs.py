"""Writes every log record as one JSON object per line on stdout, with the request it served."""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime

# The ID of the request being served; the runtime sets it for every HTTP call.
request_id: ContextVar[str | None] = ContextVar("request_id", default=None)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, str] = {
            "time": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        current_request = request_id.get()
        if current_request is not None:
            entry["request_id"] = current_request
        if record.exc_info:
            entry["error"] = self.formatException(record.exc_info)
        return json.dumps(entry)


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
