"""
JSON logging utilities that include trace & span IDs when available.
"""

import json
import logging
from typing import Any, Dict

from opentelemetry import trace


class JsonFormatter(logging.Formatter):
    # Standard LogRecord attributes to ignore when looking for 'extra' fields
    _SKIP_ATTRS = {
        "args", "asctime", "created", "exc_info", "exc_text", "filename",
        "funcName", "levelname", "levelno", "lineno", "module", "msecs",
        "message", "msg", "name", "pathname", "process", "processName",
        "relativeCreated", "stack_info", "thread", "threadName",
    }

    def format(self, record: logging.LogRecord) -> str:
        span_context = trace.get_current_span().get_span_context()
        trace_id = (
            f"{span_context.trace_id:032x}" if span_context.is_valid() else None
        )
        span_id = (
            f"{span_context.span_id:016x}" if span_context.is_valid() else None
        )

        log_entry: Dict[str, Any] = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "service": record.name,
            "trace_id": trace_id,
            "span_id": span_id,
        }

        if record.exc_info:
            log_entry["exc_info"] = self.formatException(record.exc_info)
        if record.stack_info:
            log_entry["stack_info"] = self.formatStack(record.stack_info)
        
        # Add any extra attributes that were passed in the 'extra' dict
        # (These become attributes of the record)
        extra_fields = {
            k: v
            for k, v in record.__dict__.items()
            if k not in self._SKIP_ATTRS and not k.startswith("_")
        }
        if extra_fields:
            log_entry.update(extra_fields)

        return json.dumps(log_entry)


def get_json_logger(name: str) -> logging.Logger:
    """
    Get a logger that outputs JSON format with trace and span IDs.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Ensure only one handler is added to avoid duplicate logs
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = JsonFormatter()
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
