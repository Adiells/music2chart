"""Tempo tracking, dynamic beat grid extraction, and tempo map synthesis using Librosa."""

import librosa
import numpy as np
import scipy.signal

from src.models import BPMChange, TempoMap, TimeSignature


class TempoTracker:
    """Extracts rhythmic tempo, beat tracking, and sync structures from raw audio waveforms."""

    def __init__(
        self,
        resolution: int = 192,
        hop_length: int = 256,
        min_bpm: float = 40.0,
        max_bpm: float = 300.0,
        auto_calibrate_bpm: bool = True,
        target_bpm_range: tuple[float, float] = (75.0, 160.0),
        bpm_scale: float = 1.0,
    ) -> None:
        self.resolution = resolution
        self.hop_length = hop_length
        self.min_bpm = min_bpm
        self.max_bpm = max_bpm
        self.auto_calibrate_bpm = auto_calibrate_bpm
        self.target_bpm_range = target_bpm_range
        self.bpm_scale = bpm_scale

    def _ensure_mono(self, audio_data: np.ndarray) -> np.ndarray:
        """Convert input signal to 1D mono float32 array."""
        if audio_data.ndim == 1:
            return audio_data.astype(np.float32)
        if audio_data.ndim == 2:
            # Check shape: (channels, samples) or (samples, channels)
            if audio_data.shape[0] in (1, 2) and audio_data.shape[1] > audio_data.shape[0]:
                return np.mean(audio_data, axis=0, dtype=np.float32)
            return np.mean(audio_data, axis=1, dtype=np.float32)
        return np.squeeze(audio_data).astype(np.float32)

    def detect_intro_offset(
        self,
        audio_data: np.ndarray,
        sample_rate: int,
        threshold_ratio: float = 0.05,
    ) -> float:
        """Calculate the lead-in offset (seconds until first significant transient/onset)."""
        y = self._ensure_mono(audio_data)
        if len(y) == 0 or np.max(np.abs(y)) < 1e-5:
            return 0.0

        peak = float(np.max(np.abs(y)))
        threshold = peak * threshold_ratio
        indices = np.where(np.abs(y) >= threshold)[0]
        if len(indices) == 0:
            return 0.0

        first_sample = int(indices[0])
        return float(first_sample / sample_rate)

    def calibrate_bpm(
        self,
        bpm: float,
        auto_calibrate_bpm: bool | None = None,
        target_bpm_range: tuple[float, float] | None = None,
        bpm_scale: float | None = None,
    ) -> float:
        """Calibrate BPM for comfortable highway scroll speed.

        If auto_calibrate_bpm is True, if detected BPM exceeds target_bpm_range high (160.0)
        and dividing by 2 lands within or closer to target_bpm_range (>= 70.0), fold it by
        dividing by 2 (halving excessive tempo). Then multiply by bpm_scale.
        """
        auto_cal = self.auto_calibrate_bpm if auto_calibrate_bpm is None else auto_calibrate_bpm
        t_range = self.target_bpm_range if target_bpm_range is None else target_bpm_range
        scale = self.bpm_scale if bpm_scale is None else bpm_scale

        result = float(bpm)
        if auto_cal:
            target_min, target_max = t_range
            while result > target_max and (result / 2.0 >= 70.0 or result / 2.0 >= target_min):
                result /= 2.0

        result *= scale
        return float(round(result, 2))

    def estimate_tempo(
        self,
        audio_data: np.ndarray,
        sample_rate: int,
        auto_calibrate_bpm: bool | None = None,
        target_bpm_range: tuple[float, float] | None = None,
        bpm_scale: float | None = None,
    ) -> float:
        """Estimate the dominant BPM tempo of an audio segment."""
        y = self._ensure_mono(audio_data)
        if len(y) == 0 or np.max(np.abs(y)) < 1e-4:
            raw_tempo = 120.0
        else:
            # Attempt high-precision peak-to-peak interval detection for clean pulse signals
            peak_bpm = self._estimate_from_peaks(y, sample_rate)
            if peak_bpm is not None and self.min_bpm <= peak_bpm <= self.max_bpm:
                raw_tempo = float(round(peak_bpm, 2))
            else:
                # Standard spectral onset strength and librosa beat tracking
                onset_env = librosa.onset.onset_strength(
                    y=y, sr=sample_rate, hop_length=self.hop_length
                )
                tempo, _ = librosa.beat.beat_track(
                    onset_envelope=onset_env,
                    sr=sample_rate,
                    hop_length=self.hop_length,
                    start_bpm=120.0,
                )

                detected_tempo = float(np.atleast_1d(tempo)[0])
                if detected_tempo <= 0.0 or np.isnan(detected_tempo):
                    raw_tempo = 120.0
                else:
                    # Refine within typical tempo bounds
                    while detected_tempo < self.min_bpm:
                        detected_tempo *= 2.0
                    while detected_tempo > self.max_bpm:
                        detected_tempo /= 2.0
                    raw_tempo = float(round(detected_tempo, 2))

        return self.calibrate_bpm(
            raw_tempo,
            auto_calibrate_bpm=auto_calibrate_bpm,
            target_bpm_range=target_bpm_range,
            bpm_scale=bpm_scale,
        )

    def _estimate_from_peaks(self, y: np.ndarray, sample_rate: int) -> float | None:
        """Estimate BPM from periodic prominent transients."""
        peak_val = float(np.max(np.abs(y)))
        if peak_val < 1e-3:
            return None

        # Min distance between peaks corresponding to max_bpm
        min_distance = int(sample_rate * (60.0 / self.max_bpm))
        peaks, _ = scipy.signal.find_peaks(np.abs(y), height=peak_val * 0.4, distance=min_distance)

        if len(peaks) < 4:
            return None

        intervals = np.diff(peaks) / sample_rate
        median_interval = float(np.median(intervals))
        if median_interval <= 0:
            return None

        # Check consistency (standard deviation of intervals)
        std_interval = float(np.std(intervals))
        if std_interval / median_interval > 0.05:
            # Intervals too irregular for pure click-track estimation
            return None

        return 60.0 / median_interval

    def detect_variable_tempo(
        self,
        audio_data: np.ndarray,
        sample_rate: int,
        window_duration_sec: float = 8.0,
        auto_calibrate_bpm: bool | None = None,
        target_bpm_range: tuple[float, float] | None = None,
        bpm_scale: float | None = None,
    ) -> list[BPMChange]:
        """Detect tempo changes across sliding temporal windows."""
        y = self._ensure_mono(audio_data)
        total_duration = len(y) / sample_rate
        if total_duration <= window_duration_sec:
            bpm = self.estimate_tempo(
                y,
                sample_rate,
                auto_calibrate_bpm=auto_calibrate_bpm,
                target_bpm_range=target_bpm_range,
                bpm_scale=bpm_scale,
            )
            return [BPMChange(tick=0, bpm=bpm)]

        window_samples = int(window_duration_sec * sample_rate)
        num_windows = int(len(y) // window_samples)

        bpm_changes: list[BPMChange] = []
        current_tick = 0
        current_bpm: float | None = None

        for w in range(num_windows):
            start_idx = w * window_samples
            end_idx = min(start_idx + window_samples, len(y))
            chunk = y[start_idx:end_idx]

            chunk_bpm = self.estimate_tempo(
                chunk,
                sample_rate,
                auto_calibrate_bpm=auto_calibrate_bpm,
                target_bpm_range=target_bpm_range,
                bpm_scale=bpm_scale,
            )

            if current_bpm is None:
                current_bpm = chunk_bpm
                bpm_changes.append(BPMChange(tick=0, bpm=current_bpm))
            elif abs(chunk_bpm - current_bpm) >= 3.0:
                # Detectable tempo change: accumulate elapsed ticks under previous BPM
                elapsed_sec = window_duration_sec
                added_ticks = int(round(elapsed_sec * (current_bpm * self.resolution / 60.0)))
                current_tick += added_ticks
                current_bpm = chunk_bpm
                bpm_changes.append(BPMChange(tick=current_tick, bpm=current_bpm))
            else:
                elapsed_sec = window_duration_sec
                added_ticks = int(round(elapsed_sec * (current_bpm * self.resolution / 60.0)))
                current_tick += added_ticks

        return bpm_changes

    def build_tempo_map(
        self,
        audio_data: np.ndarray,
        sample_rate: int,
        variable_tempo: bool = False,
        auto_calibrate_bpm: bool = True,
        target_bpm_range: tuple[float, float] = (75.0, 160.0),
        bpm_scale: float = 1.0,
    ) -> TempoMap:
        """Construct a complete TempoMap from audio waveform."""
        effective_auto_cal = (
            False
            if (auto_calibrate_bpm is True and self.auto_calibrate_bpm is False)
            else auto_calibrate_bpm
        )
        effective_range = (
            self.target_bpm_range
            if (target_bpm_range == (75.0, 160.0) and self.target_bpm_range != (75.0, 160.0))
            else target_bpm_range
        )
        effective_scale = (
            self.bpm_scale if (bpm_scale == 1.0 and self.bpm_scale != 1.0) else bpm_scale
        )

        if variable_tempo:
            changes = self.detect_variable_tempo(
                audio_data,
                sample_rate,
                auto_calibrate_bpm=effective_auto_cal,
                target_bpm_range=effective_range,
                bpm_scale=effective_scale,
            )
        else:
            bpm = self.estimate_tempo(
                audio_data,
                sample_rate,
                auto_calibrate_bpm=effective_auto_cal,
                target_bpm_range=effective_range,
                bpm_scale=effective_scale,
            )
            changes = [BPMChange(tick=0, bpm=bpm)]

        return TempoMap(
            resolution=self.resolution,
            bpm_changes=changes,
            time_signatures=[TimeSignature(tick=0, numerator=4, denominator=4)],
        )
