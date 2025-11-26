"""Central logging configuration for GraphRAG.

All modules should import `log` from this file instead of configuring the
`logging` module themselves. The configuration prints colorised console output
in development; you can easily extend this for file/JSON handlers in prod.
"""

from __future__ import annotations

import logging
import sys
from typing import Final

_LOG_LEVEL: Final = "DEBUG"

# Basic colour support (Windows 10+ supports ANSI sequences in recent versions)
class _ColorFormatter(logging.Formatter):
    RESET = "\033[0m"
    COLORS = {
        logging.DEBUG: "\033[36m",    # Cyan
        logging.INFO: "\033[32m",     # Green
        logging.WARNING: "\033[33m",  # Yellow
        logging.ERROR: "\033[31m",    # Red
        logging.CRITICAL: "\033[41m", # Red background
    }

    def format(self, record: logging.LogRecord) -> str:  # noqa: D401
        color = self.COLORS.get(record.levelno, "")
        reset = self.RESET if color else ""
        record.levelname = f"{color}{record.levelname}{reset}"
        return super().format(record)


def _configure_root_logger() -> logging.Logger:
    logger = logging.getLogger("graphrag")
    if logger.handlers:  # Already configured
        return logger

    handler = logging.StreamHandler(sys.stdout)
    fmt = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    handler.setFormatter(_ColorFormatter(fmt))

    logger.addHandler(handler)
    logger.setLevel(_LOG_LEVEL)
    logger.propagate = False
    return logger


log: logging.Logger = _configure_root_logger()
