"""Unit tests for HarmonicFilter suppressing distortion overtones."""

from src.audio_processing.harmonic_filter import HarmonicFilter
from src.models import NoteEvent


def test_filter_octave_overtone() -> None:
    """Validate that weak octave (+12 semitones) overtone is suppressed when root is present."""
    root = NoteEvent(start_time=1.0, end_time=2.0, pitch=40, amplitude=0.90)  # E2 root note
    overtone = NoteEvent(
        start_time=1.02, end_time=1.9, pitch=52, amplitude=0.45
    )  # E3 octave overtone (half amplitude)

    filter_engine = HarmonicFilter()
    filtered = filter_engine.filter_overtones([root, overtone])

    assert len(filtered) == 1
    assert filtered[0] == root


def test_filter_fifth_overtone() -> None:
    """Validate that weak octave+fifth (+19 semitones) overtone is suppressed."""
    root = NoteEvent(start_time=0.5, end_time=1.5, pitch=45, amplitude=0.92)  # A2
    overtone = NoteEvent(
        start_time=0.51, end_time=1.4, pitch=64, amplitude=0.40
    )  # E4 overtone (+19)

    filter_engine = HarmonicFilter()
    filtered = filter_engine.filter_overtones([root, overtone])

    assert len(filtered) == 1
    assert filtered[0] == root


def test_preserve_genuine_played_octave_chord() -> None:
    """Ensure genuine played octaves with balanced amplitudes are NOT filtered out."""
    root = NoteEvent(start_time=0.0, end_time=1.0, pitch=40, amplitude=0.88)
    high_note = NoteEvent(
        start_time=0.0, end_time=1.0, pitch=52, amplitude=0.85
    )  # Strong played octave

    filter_engine = HarmonicFilter(octave_ratio=0.85)
    filtered = filter_engine.filter_overtones([root, high_note])

    assert len(filtered) == 2
    assert root in filtered
    assert high_note in filtered


def test_preserve_sequential_notes_at_octave() -> None:
    """Ensure notes occurring at different times are never treated as overtones."""
    first = NoteEvent(start_time=0.0, end_time=0.5, pitch=40, amplitude=0.90)
    second = NoteEvent(start_time=1.0, end_time=1.5, pitch=52, amplitude=0.30)  # Separate in time

    filter_engine = HarmonicFilter()
    filtered = filter_engine.filter_overtones([first, second])

    assert len(filtered) == 2
    assert filtered == [first, second]


def test_empty_notes_filter() -> None:
    """Ensure empty list is handled cleanly."""
    filter_engine = HarmonicFilter()
    assert filter_engine.filter_overtones([]) == []
