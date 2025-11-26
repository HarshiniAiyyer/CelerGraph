"""
JSON logging utilities that include trace & span IDs when available.

You can use:

    from observability.logging import get_json_logger

    logger = get_json_logger(__name__)
    logger.info("retrieval complete", extra={"retrieved": 10})
"""

from .json_logger import get_json_logger

__all__ = ["get_json_logger"]
