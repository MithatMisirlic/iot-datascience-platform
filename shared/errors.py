"""Dependency-light application errors shared across platform components."""


class ResourceNotFoundError(Exception):
    """Raised when an application resource cannot be found."""


class ResourceConflictError(Exception):
    """Raised when an operation conflicts with current resource state."""


class OperationDeferredError(Exception):
    """Raised when an integration is intentionally unavailable."""


class InvalidArtifactError(Exception):
    """Raised when an uploaded artifact is missing or malformed."""


class UnsupportedArtifactError(Exception):
    """Raised when an artifact type is not supported by the application."""


class MissingArtifactsError(Exception):
    """Raised when processing inputs are incomplete."""


class InvalidProcessedResultError(Exception):
    """Raised when a processor returns data outside the API contract."""
