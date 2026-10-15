"""Structured, local, rotating logging."""

from __future__ import annotations

import json
import logging
import logging.handlers
import sys
from pathlib import Path

MAX_BYTES = 5 * 1024 * 1024
BACKUPS = 3


class JsonFormatter(logging.Formatter):

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "source": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False)


def configure(log_dir: Path, development: bool = False) -> None:
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if development else logging.INFO)
    root_logger.handlers.clear()

    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(
        logging.Formatter("%(levelname)-7s %(name)-28s %(message)s")
    )
    root_logger.addHandler(console)

    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        file = logging.handlers.RotatingFileHandler(
            log_dir / "substrakt.log",
            maxBytes=MAX_BYTES,
            backupCount=BACKUPS,
            encoding="utf-8",
        )
        file.setFormatter(JsonFormatter())
        root_logger.addHandler(file)
    except OSError as exc:
        
        logging.getLogger(__name__).warning("File logging unavailable: %s", exc)

    
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(name).handlers.clear()
        logging.getLogger(name).propagate = True
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
