#!/usr/bin/env python3
"""Entrypoint with dependency checks and configurable host/port."""

import importlib
import os
import sys

from dotenv import load_dotenv
from loguru import logger


REQUIRED_MODULES = (
    "fastapi",
    "uvicorn",
    "pydantic",
    "rapidfuzz",
    "dotenv",
    "loguru",
)

OPTIONAL_MODULES = (
    ("geopy", "geospatial validation"),
    ("sklearn", "ML matching"),
)


def check_dependencies() -> bool:
    """Verify required packages are importable. Log optional gaps."""
    missing = []
    for module in REQUIRED_MODULES:
        try:
            importlib.import_module(module)
        except ImportError:
            missing.append(module)

    if missing:
        logger.error(
            "Missing required dependencies: {}. "
            "Install with: pip install -r requirements.txt",
            ", ".join(missing),
        )
        return False

    for module, purpose in OPTIONAL_MODULES:
        try:
            importlib.import_module(module)
        except ImportError:
            logger.warning(
                "Optional dependency '{}' not installed ({}); "
                "related features will be disabled.",
                module,
                purpose,
            )

    return True


def main() -> int:
    load_dotenv()

    if not check_dependencies():
        return 1

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    log_level = os.getenv("LOG_LEVEL", "INFO").lower()

    logger.info("Starting Address Matching Service on {}:{}", host, port)

    import uvicorn

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        log_level=log_level,
        reload=os.getenv("API_RELOAD", "").lower() in ("1", "true", "yes"),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
