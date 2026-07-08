"""INMP441-compatible sounddevice and mock RMS frame sources."""

from array import array
import math
from pathlib import Path
import threading
import time
from typing import Any, Iterable
import wave

from pi_client.recorders import HardwareUnavailableError

try:
    import numpy as np
except ImportError:  # pragma: no cover - optional outside Pi environment
    np = None  # type: ignore[assignment]

try:
    import sounddevice as sd
except (ImportError, OSError):  # pragma: no cover - depends on PortAudio
    sd = None  # type: ignore[assignment]


class _WavRecorder:
    """Provide thread-safe PCM WAV writing for audio frame sources."""

    def __init__(self, sample_rate: int, wav_directory: Path) -> None:
        self.sample_rate = sample_rate
        self.wav_directory = wav_directory
        self._wav_writer: wave.Wave_write | None = None
        self._wav_path: Path | None = None
        self._wav_lock = threading.Lock()

    def start_wav(self) -> Path:
        """Start writing subsequent samples to a timestamped WAV file."""

        with self._wav_lock:
            if self._wav_writer is not None:
                self._wav_writer.close()
            self.wav_directory.mkdir(parents=True, exist_ok=True)
            self._wav_path = self.wav_directory / (
                f"recording_{int(time.time() * 1000)}.wav"
            )
            writer = wave.open(str(self._wav_path), "wb")
            writer.setnchannels(1)
            writer.setsampwidth(2)
            writer.setframerate(self.sample_rate)
            self._wav_writer = writer
            return self._wav_path

    def stop_wav(self) -> Path | None:
        """Finish the active WAV recording and return its path."""

        with self._wav_lock:
            if self._wav_writer is None:
                return None
            self._wav_writer.close()
            self._wav_writer = None
            return self._wav_path

    def _write_wav_samples(self, samples: Iterable[float]) -> None:
        pcm = array(
            "h",
            (
                max(-32_768, min(32_767, int(sample * 32_767)))
                for sample in samples
            ),
        )
        with self._wav_lock:
            if self._wav_writer is not None:
                self._wav_writer.writeframesraw(pcm.tobytes())

    def close(self) -> None:
        """Close an active WAV writer."""

        self.stop_wav()


class AudioRecorder(_WavRecorder):
    """Capture short INMP441/PortAudio blocks and emit RMS amplitude."""

    def __init__(
        self,
        sample_rate: int = 48_000,
        frame_rate_hz: float = 60.0,
        wav_directory: Path = Path("./recordings"),
    ) -> None:
        if sd is None or np is None:
            raise HardwareUnavailableError(
                "sounddevice or numpy is unavailable; use PI_MOCK_MODE=true."
            )
        super().__init__(sample_rate, wav_directory)
        self._frames_per_block = max(1, round(sample_rate / frame_rate_hz))

    def read_frame(self) -> dict[str, Any]:
        """Capture one audio block and return its RMS amplitude."""

        samples = sd.rec(
            self._frames_per_block,
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            blocking=True,
        )
        flattened = np.asarray(samples, dtype=np.float32).reshape(-1)
        rms = float(np.sqrt(np.mean(np.square(flattened))))
        self._write_wav_samples(flattened.tolist())
        return {"type": "audio", "ts": time.time(), "spl": rms}


class MockAudioRecorder(_WavRecorder):
    """Generate deterministic audio RMS frames without an input device."""

    def __init__(
        self,
        sample_rate: int = 48_000,
        frame_rate_hz: float = 60.0,
        wav_directory: Path = Path("./recordings"),
    ) -> None:
        super().__init__(sample_rate, wav_directory)
        self._frames_per_block = max(1, round(sample_rate / frame_rate_hz))
        self._sample_index = 0

    def read_frame(self) -> dict[str, Any]:
        """Return RMS for a low-amplitude deterministic sine wave."""

        samples = [
            0.05 * math.sin(2 * math.pi * 440 * (self._sample_index + index) / self.sample_rate)
            for index in range(self._frames_per_block)
        ]
        self._sample_index += self._frames_per_block
        rms = math.sqrt(sum(sample * sample for sample in samples) / len(samples))
        self._write_wav_samples(samples)
        return {"type": "audio", "ts": time.time(), "spl": float(rms)}
