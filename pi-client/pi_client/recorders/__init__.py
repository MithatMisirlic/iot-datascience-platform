"""Hardware-specific and mock sensor recorder adapters."""


class HardwareUnavailableError(RuntimeError):
    """Raised when an optional hardware dependency or device is unavailable."""
