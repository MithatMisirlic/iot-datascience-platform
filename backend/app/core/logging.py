"""Application logging configuration."""

import logging


def configure_logging(level: str) -> None:
    """Configure consistent process-wide logging."""

    logging.basicConfig(
        level=getattr(logging, level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
