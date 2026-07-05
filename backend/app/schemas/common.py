"""Schemas shared by multiple API resources."""

from pydantic import BaseModel, RootModel


class Properties(RootModel[dict[str, str]]):
    """Custom string key-value pairs supplied by an experimenter."""


class Error(BaseModel):
    """Contract error response."""

    error: str
