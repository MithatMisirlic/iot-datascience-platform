"""Dependency-light application errors shared across platform components."""


class ResourceNotFoundError(Exception):
    """Raised when an application resource cannot be found."""


class ResourceConflictError(Exception):
    """Raised when an operation conflicts with current resource state."""
