"""Shared behavior for contract-only endpoint placeholders."""

from typing import NoReturn

from fastapi import HTTPException, status


def not_implemented() -> NoReturn:
    """Terminate a placeholder operation with HTTP 501."""

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Not implemented",
    )
