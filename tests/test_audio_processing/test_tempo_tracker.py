"""Unit tests for tempo tracking and sync track generation."""

import numpy as np
import pytest

from src.audio_processing.tempo_tracker import TempoTracker


def _create_pulse_train(
    bpm: float, duration_seconds: float, sample_rate: int = 22050
) -> np.ndarray:
    """Synthesize clean periodic impulses at exact BPM intervals."""
    interval_sec = 60.0 / bpm
    total_samples = int(duration_seconds * sample_rate)
    y = np.zeros(total_samples, dtype=np.float32)

    pulse_times = np.arange(0.0, duration_seconds, interval_sec)
    for t in pulse_times:
        idx = int(round(t * sample_rate))
        if idx < total_samples:
            # Short burst transient
            y[idx : min(idx + 50, total_samples)] = 1.0

    return y


def test_tempo_tracker_synthetic_120_bpm() -> None:
    """Validate tempo detection and grid calculation on 120.0 BPM click track."""
    sr = 22050
    audio = _create_pulse_train(bpm=120.0, duration_seconds=6.0, sample_rate=sr)

    tracker = TempoTracker(resolution=192)
    detected_bpm = tracker.estimate_tempo(audio, sr)
    assert detected_bpm == pytest.approx(120.0, abs=0.5)

    tempo_map = tracker.build_tempo_map(audio, sr)
    assert len(tempo_map.bpm_changes) == 1
    assert tempo_map.bpm_changes[0].tick == 0
    assert tempo_map.bpm_changes[0].bpm == pytest.approx(120.0, abs=0.5)

    # 120 BPM: quarter note (192 ticks) is exactly 0.5 seconds
    assert tempo_map.seconds_to_tick(0.5) == 192
    assert tempo_map.tick_to_seconds(192) == pytest.approx(0.5)


def test_tempo_tracker_synthetic_140_bpm() -> None:
    """Validate tempo detection on 140.0 BPM click track."""
    sr = 22050
    audio = _create_pulse_train(bpm=140.0, duration_seconds=6.0, sample_rate=sr)

    tracker = TempoTracker(resolution=192)
    detected_bpm = tracker.estimate_tempo(audio, sr)
    assert detected_bpm == pytest.approx(140.0, abs=0.5)


def test_detect_intro_offset() -> None:
    """Validate computation of lead-in silence offset before the first transient."""
    sr = 22050
    # 1.5 seconds of silence followed by pulses
    silence = np.zeros(int(1.5 * sr), dtype=np.float32)
    pulses = _create_pulse_train(bpm=120.0, duration_seconds=4.0, sample_rate=sr)
    audio = np.concatenate([silence, pulses])

    tracker = TempoTracker()
    offset = tracker.detect_intro_offset(audio, sr)
    assert offset == pytest.approx(1.5, abs=0.05)


def test_silent_audio_graceful_fallback() -> None:
    """Ensure silent audio falls back to default 120.0 BPM without error."""
    sr = 22050
    audio = np.zeros(sr * 3, dtype=np.float32)

    tracker = TempoTracker()
    bpm = tracker.estimate_tempo(audio, sr)
    assert bpm == 120.0

    offset = tracker.detect_intro_offset(audio, sr)
    assert offset == 0.0

    tmap = tracker.build_tempo_map(audio, sr)
    assert tmap.bpm_changes[0].bpm == 120.0


def test_variable_tempo_detection() -> None:
    """Validate detection of tempo changes across audio sections."""
    sr = 22050
    # 8 seconds at 120 BPM + 8 seconds at 140 BPM
    part1 = _create_pulse_train(bpm=120.0, duration_seconds=8.0, sample_rate=sr)
    part2 = _create_pulse_train(bpm=140.0, duration_seconds=8.0, sample_rate=sr)
    combined = np.concatenate([part1, part2])

    tracker = TempoTracker()
    tempo_map = tracker.build_tempo_map(combined, sr, variable_tempo=True)

    assert len(tempo_map.bpm_changes) >= 2
    assert tempo_map.bpm_changes[0].bpm == pytest.approx(120.0, abs=1.0)
    assert tempo_map.bpm_changes[1].bpm == pytest.approx(140.0, abs=1.0)
