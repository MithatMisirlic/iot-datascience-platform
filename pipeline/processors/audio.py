"""RMS audio-frame and speech-proxy feature extraction."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
from scipy.fftpack import dct
from scipy.signal import find_peaks, spectrogram

from pipeline.core.statistics import (
    duration_seconds,
    maximum,
    mean,
    minimum,
    population_std,
    sample_rate_estimate_hz,
)

MFCC_COEFFICIENT_COUNT = 13


@dataclass(frozen=True, slots=True)
class AudioFeatures:
    """Generic audio and speech-proxy features from RMS amplitude samples.

    The speech clarity and syllable metrics are lightweight research proxies
    derived from the RMS envelope. They are not medically validated speech
    assessments and should not be interpreted diagnostically.
    """

    duration_seconds: float
    rms_mean: float
    rms_max: float
    rms_min: float
    rms_std: float
    sample_count: int
    sample_rate_estimate_hz: float
    mfcc_means: list[float]
    mfcc_stds: list[float]
    zero_crossing_rate_mean: float
    zero_crossing_rate_max: float
    spectral_centroid_mean: float
    spectral_centroid_max: float
    spectral_bandwidth_mean: float
    spectral_bandwidth_max: float
    speech_clarity_proxy: float
    syllable_count: int
    average_syllable_duration: float
    syllables_per_second: float

    def to_dict(self) -> dict[str, float | int | list[float]]:
        """Return a JSON-compatible representation."""
        return asdict(self)


def process_audio_frames(frames: Sequence[Mapping[str, Any]]) -> AudioFeatures:
    """Extract deterministic audio features from timestamped RMS frames."""
    timestamps = [float(frame["ts"]) for frame in frames]
    rms_values = [float(frame["spl"]) for frame in frames]
    sample_rate = sample_rate_estimate_hz(timestamps)
    mfcc_means, mfcc_stds = mfcc_summary(rms_values, sample_rate)
    zcr_mean, zcr_max = zero_crossing_rate_summary(rms_values, sample_rate)
    centroid_mean, centroid_max, bandwidth_mean, bandwidth_max = spectral_summary(
        rms_values,
        sample_rate,
    )
    syllable_count, average_duration, syllables_per_second = syllable_timing_summary(
        rms_values,
        timestamps,
    )

    return AudioFeatures(
        duration_seconds=duration_seconds(timestamps),
        rms_mean=mean(rms_values),
        rms_max=maximum(rms_values),
        rms_min=minimum(rms_values),
        rms_std=population_std(rms_values),
        sample_count=len(frames),
        sample_rate_estimate_hz=sample_rate,
        mfcc_means=mfcc_means,
        mfcc_stds=mfcc_stds,
        zero_crossing_rate_mean=zcr_mean,
        zero_crossing_rate_max=zcr_max,
        spectral_centroid_mean=centroid_mean,
        spectral_centroid_max=centroid_max,
        spectral_bandwidth_mean=bandwidth_mean,
        spectral_bandwidth_max=bandwidth_max,
        speech_clarity_proxy=speech_clarity_proxy(rms_values),
        syllable_count=syllable_count,
        average_syllable_duration=average_duration,
        syllables_per_second=syllables_per_second,
    )


def mfcc_summary(
    values: Sequence[float],
    sample_rate_hz: float,
    coefficient_count: int = MFCC_COEFFICIENT_COUNT,
) -> tuple[list[float], list[float]]:
    """Return mean/std for MFCC-style cepstral coefficients.

    The current Pi stream provides RMS envelope frames, not raw microphone
    waveform samples. This function therefore computes cepstral summaries from
    the log-mel spectrum of the RMS envelope. It is useful for deterministic
    research comparison, but it is not equivalent to clinical speech analysis.
    """
    samples = _centered_array(values)
    if samples.size == 0:
        return _zeros(coefficient_count), _zeros(coefficient_count)

    _, _, spectrum = _safe_spectrogram(samples, sample_rate_hz)
    if spectrum.size == 0:
        return _zeros(coefficient_count), _zeros(coefficient_count)

    frequencies = np.linspace(0.0, max(sample_rate_hz, 1.0) / 2.0, spectrum.shape[0])
    filterbank = _mel_filterbank(frequencies, n_mels=max(26, coefficient_count * 2))
    mel_energy = filterbank @ spectrum if filterbank.size else spectrum
    if mel_energy.size == 0:
        return _zeros(coefficient_count), _zeros(coefficient_count)

    cepstra = dct(np.log(mel_energy + 1e-12), type=2, axis=0, norm="ortho")
    selected = cepstra[:coefficient_count]
    if selected.shape[0] < coefficient_count:
        selected = np.pad(selected, ((0, coefficient_count - selected.shape[0]), (0, 0)))
    return (
        [float(value) for value in np.mean(selected, axis=1)],
        [float(value) for value in np.std(selected, axis=1)],
    )


def zero_crossing_rate_summary(
    values: Sequence[float],
    sample_rate_hz: float,
) -> tuple[float, float]:
    """Return mean and max zero-crossing rate over the centered envelope."""
    samples = _centered_array(values)
    if samples.size < 2:
        return 0.0, 0.0
    window = _window_size(samples.size, sample_rate_hz)
    rates: list[float] = []
    for start in range(0, samples.size - 1, window):
        chunk = samples[start : start + window]
        if chunk.size < 2:
            continue
        signs = np.signbit(chunk)
        rates.append(float(np.count_nonzero(signs[1:] != signs[:-1]) / (chunk.size - 1)))
    return mean(rates), maximum(rates)


def spectral_summary(values: Sequence[float], sample_rate_hz: float) -> tuple[float, float, float, float]:
    """Return spectral centroid and bandwidth mean/max for the envelope."""
    samples = _centered_array(values)
    if samples.size < 2:
        return 0.0, 0.0, 0.0, 0.0
    frequencies, _, power = _safe_spectrogram(samples, sample_rate_hz)
    if power.size == 0:
        return 0.0, 0.0, 0.0, 0.0
    centroids: list[float] = []
    bandwidths: list[float] = []
    for column in power.T:
        total = float(np.sum(column))
        if total <= 0.0:
            centroids.append(0.0)
            bandwidths.append(0.0)
            continue
        centroid = float(np.sum(frequencies * column) / total)
        bandwidth = float(np.sqrt(np.sum(((frequencies - centroid) ** 2) * column) / total))
        centroids.append(centroid)
        bandwidths.append(bandwidth)
    return mean(centroids), maximum(centroids), mean(bandwidths), maximum(bandwidths)


def speech_clarity_proxy(values: Sequence[float]) -> float:
    """Return voiced-envelope energy divided by total envelope energy.

    Samples above the envelope mean are treated as voiced-like energy. This is
    a simple explainable proxy for experimentation, not a validated speech
    clarity or clinical measure.
    """
    if not values:
        return 0.0
    envelope = np.asarray(values, dtype=float)
    energy = envelope * envelope
    total = float(np.sum(energy))
    if total <= 0.0:
        return 0.0
    voiced = energy[envelope >= float(np.mean(envelope))]
    return float(np.sum(voiced) / total)


def syllable_timing_summary(
    values: Sequence[float],
    timestamps: Sequence[float],
) -> tuple[int, float, float]:
    """Approximate syllable timing from peaks in the RMS envelope."""
    if len(values) < 2 or len(timestamps) < 2:
        return 0, 0.0, 0.0
    envelope = np.asarray(values, dtype=float)
    sample_rate = sample_rate_estimate_hz(timestamps)
    threshold = float(np.mean(envelope) + 0.25 * np.std(envelope))
    distance = max(1, int(round(max(sample_rate, 1.0) * 0.12)))
    peaks, _ = find_peaks(envelope, height=threshold, distance=distance)
    duration = duration_seconds(timestamps)
    if peaks.size == 0 or duration == 0.0:
        return 0, 0.0, 0.0

    active = envelope >= threshold
    sample_period = duration / max(len(timestamps) - 1, 1)
    durations: list[float] = []
    for peak in peaks:
        left = int(peak)
        while left > 0 and active[left - 1]:
            left -= 1
        right = int(peak)
        while right < len(active) - 1 and active[right + 1]:
            right += 1
        durations.append((right - left + 1) * sample_period)
    return int(peaks.size), mean(durations), float(peaks.size / duration)


def _centered_array(values: Sequence[float]) -> np.ndarray:
    if not values:
        return np.asarray([], dtype=float)
    samples = np.asarray(values, dtype=float)
    return samples - float(np.mean(samples))


def _safe_spectrogram(samples: np.ndarray, sample_rate_hz: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    sample_rate = max(float(sample_rate_hz), 1.0)
    window = _window_size(samples.size, sample_rate)
    noverlap = max(0, min(window - 1, window // 2))
    frequencies, times, power = spectrogram(
        samples,
        fs=sample_rate,
        nperseg=window,
        noverlap=noverlap,
        scaling="spectrum",
        mode="magnitude",
    )
    return frequencies, times, power


def _window_size(sample_count: int, sample_rate_hz: float) -> int:
    if sample_count <= 1:
        return 1
    target = max(2, int(round(max(sample_rate_hz, 1.0) * 0.25)))
    return max(2, min(sample_count, target))


def _mel_filterbank(frequencies: np.ndarray, n_mels: int) -> np.ndarray:
    if frequencies.size == 0:
        return np.asarray([], dtype=float)
    max_hz = float(frequencies[-1])
    if max_hz <= 0.0:
        return np.ones((n_mels, frequencies.size), dtype=float)
    mel_points = np.linspace(_hz_to_mel(0.0), _hz_to_mel(max_hz), n_mels + 2)
    hz_points = _mel_to_hz(mel_points)
    filters = np.zeros((n_mels, frequencies.size), dtype=float)
    for index in range(n_mels):
        left, center, right = hz_points[index : index + 3]
        if center == left or right == center:
            continue
        rising = (frequencies - left) / (center - left)
        falling = (right - frequencies) / (right - center)
        filters[index] = np.maximum(0.0, np.minimum(rising, falling))
    row_sums = filters.sum(axis=1, keepdims=True)
    np.divide(filters, row_sums, out=filters, where=row_sums != 0.0)
    return filters


def _hz_to_mel(value: float) -> float:
    return 2595.0 * np.log10(1.0 + value / 700.0)


def _mel_to_hz(values: np.ndarray) -> np.ndarray:
    return 700.0 * (np.power(10.0, values / 2595.0) - 1.0)


def _zeros(count: int) -> list[float]:
    return [0.0 for _ in range(count)]
