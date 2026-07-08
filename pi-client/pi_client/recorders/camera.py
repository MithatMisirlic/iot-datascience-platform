"""OpenCV and mock JPEG camera frame sources."""

import base64
from typing import Any
import time

from pi_client.recorders import HardwareUnavailableError

try:
    import cv2
except ImportError:  # pragma: no cover - optional outside Pi environment
    cv2 = None  # type: ignore[assignment]


class CameraRecorder:
    """Capture JPEG frames from an OpenCV-compatible camera device."""

    def __init__(self, camera_index: int = 0, jpeg_quality: int = 80) -> None:
        if cv2 is None:
            raise HardwareUnavailableError(
                "opencv-python is unavailable; use PI_MOCK_MODE=true."
            )
        self._jpeg_quality = jpeg_quality
        self._capture = cv2.VideoCapture(camera_index)
        if not self._capture.isOpened():
            self._capture.release()
            raise HardwareUnavailableError(
                f"Camera device {camera_index} could not be opened."
            )

    def read_frame(self) -> dict[str, Any]:
        """Capture and base64 encode one JPEG frame."""

        success, image = self._capture.read()
        if not success:
            raise OSError("Camera frame capture failed.")
        encoded, jpeg = cv2.imencode(
            ".jpg",
            image,
            [int(cv2.IMWRITE_JPEG_QUALITY), self._jpeg_quality],
        )
        if not encoded:
            raise OSError("Camera JPEG encoding failed.")
        return {
            "type": "camera",
            "ts": time.time(),
            "jpeg": base64.b64encode(jpeg.tobytes()).decode("ascii"),
        }

    def close(self) -> None:
        """Release the camera device."""

        self._capture.release()


class MockCameraRecorder:
    """Return a static valid JPEG without camera or OpenCV dependencies."""

    _JPEG = (
        "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAP//////////////////////////////////////////"
        "////////////////////////////////////////////2wBDAf//////////////////////////"
        "////////////////////////////////////////////////////////////wAARCAABAAEDASIA"
        "AhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAf/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/9oADAMB"
        "AAIQAxAAAAF//8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABBQJ//8QAFBEBAAAAAAAAAAAA"
        "AAAAAAAAAP/aAAgBAwEBPwF//8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/aAAgBAgEBPwF//8QAFBAB"
        "AAAAAAAAAAAAAAAAAAAAAP/aAAgBAQAGPwJ//8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQAB"
        "PyF//9oADAMBAAIAAwAAABAf/8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/aAAgBAwEBPxB//8QAFBEB"
        "AAAAAAAAAAAAAAAAAAAAAP/aAAgBAgEBPxB//8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQAB"
        "PxB//9k="
    )

    def read_frame(self) -> dict[str, Any]:
        """Return one protocol-compatible mock camera frame."""

        return {"type": "camera", "ts": time.time(), "jpeg": self._JPEG}

    def close(self) -> None:
        """Require no mock cleanup."""
