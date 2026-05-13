"""Logging setup for the BuenChollo API."""

import logging


def configure_logging(level: str) -> None:
    """Configure root logging with a compact production-friendly format."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

