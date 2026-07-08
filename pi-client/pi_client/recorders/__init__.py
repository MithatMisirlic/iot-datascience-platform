"""Hardware-specific and mock sensor recorder adapters."""


class HardwareUnavailableError(RuntimeError):
    """Raised when an optional hardware dependency or device is unavailable."""


class FrameCaptureError(OSError):
    """Raised when a transient hardware frame cannot be captured or encoded."""
