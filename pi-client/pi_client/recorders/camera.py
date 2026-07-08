"""Picamera2 and mock JPEG camera frame sources."""

import base64
import logging
from typing import Any
import time

from pi_client.recorders import FrameCaptureError, HardwareUnavailableError


logger = logging.getLogger(__name__)

try:
    from picamera2 import Picamera2
except (ImportError, OSError) as error:  # pragma: no cover - optional off the Pi
    Picamera2 = None  # type: ignore[assignment,misc]
    _PICAMERA_IMPORT_ERROR: Exception | None = error
else:
    _PICAMERA_IMPORT_ERROR = None

try:
    import cv2
except (ImportError, OSError) as error:  # pragma: no cover - optional off the Pi
    cv2 = None  # type: ignore[assignment]
    _OPENCV_IMPORT_ERROR: Exception | None = error
else:
    _OPENCV_IMPORT_ERROR = None


class CameraRecorder:
    """Capture Picamera2 frames and encode them as protocol-compatible JPEGs."""

    FRAME_SIZE = (320, 240)
    PIXEL_FORMAT = "BGR888"

    def __init__(self, camera_index: int = 0, jpeg_quality: int = 80) -> None:
        if Picamera2 is None:
            detail = f": {_PICAMERA_IMPORT_ERROR}" if _PICAMERA_IMPORT_ERROR else ""
            raise HardwareUnavailableError(
                f"Picamera2 is unavailable{detail}; use PI_MOCK_MODE=true."
            )
        if cv2 is None:
            detail = f": {_OPENCV_IMPORT_ERROR}" if _OPENCV_IMPORT_ERROR else ""
            raise HardwareUnavailableError(
                f"OpenCV is unavailable{detail}; use PI_MOCK_MODE=true."
            )

        self._jpeg_quality = jpeg_quality
        self._camera: Any | None = None
        try:
            self._camera = Picamera2(camera_index)
            configuration = self._camera.create_video_configuration(
                main={"size": self.FRAME_SIZE, "format": self.PIXEL_FORMAT},
                buffer_count=2,
            )
            self._camera.configure(configuration)
            self._camera.start()
            logger.info(
                "Picamera2 camera %d initialized at %dx%d",
                camera_index,
                *self.FRAME_SIZE,
            )
        except Exception as error:
            logger.exception(
                "Failed to initialize Picamera2 camera %d at %dx%d",
                camera_index,
                *self.FRAME_SIZE,
            )
            self.close()
            raise HardwareUnavailableError(
                f"Picamera2 camera {camera_index} initialization failed: {error}"
            ) from error

    def read_frame(self) -> dict[str, Any]:
        """Capture and base64 encode one JPEG frame."""
        if self._camera is None:
            raise FrameCaptureError("Picamera2 camera is not initialized.")

        try:
            # Picamera2's BGR888 stream stores channels in RGB order. Convert
            # explicitly to OpenCV's BGR convention before JPEG encoding.
            rgb_image = self._camera.capture_array("main")
            if rgb_image is None or getattr(rgb_image, "size", 0) == 0:
                raise ValueError("Picamera2 returned an empty frame")
            bgr_image = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2BGR)
            encoded, jpeg = cv2.imencode(
                ".jpg",
                bgr_image,
                [int(cv2.IMWRITE_JPEG_QUALITY), self._jpeg_quality],
            )
            if not encoded:
                raise ValueError("OpenCV could not encode the frame")
        except Exception as error:
            logger.warning("Picamera2 frame capture failed: %s", error)
            raise FrameCaptureError(f"Camera frame capture failed: {error}") from error

        return {
            "type": "camera",
            "ts": time.time(),
            "jpeg": base64.b64encode(jpeg.tobytes()).decode("ascii"),
        }

    def close(self) -> None:
        """Stop and close the Picamera2 device."""
        camera, self._camera = self._camera, None
        if camera is None:
            return
        try:
            camera.stop()
        except Exception:
            logger.debug("Picamera2 stop failed during cleanup", exc_info=True)
        try:
            camera.close()
        except Exception:
            logger.debug("Picamera2 close failed during cleanup", exc_info=True)


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
