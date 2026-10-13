"""Unit tests for PitchTranscriber wrapper around Basic Pitch."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.audio_processing.pitch_transcriber import PitchTranscriber
from src.models import NoteEvent


@pytest.fixture
def dummy_guitar_audio(tmp_path: Path) -> Path:
    """Create a dummy guitar stem file."""
    audio = tmp_path / "guitar.wav"
    audio.write_bytes(b"RIFFdummy_guitar_stream")
    return audio


def test_pitch_transcriber_mock_predict(dummy_guitar_audio: Path) -> None:
    """Validate that Basic Pitch raw predictions are converted into sorted NoteEvents."""
    transcriber = PitchTranscriber(onset_threshold=0.5, frame_threshold=0.3, min_note_len=58.0)

    # Mock raw prediction tuples: (start, end, pitch, amplitude, bends)
    mock_raw_notes: list[tuple[float, float, float, float, list[float]]] = [
        (1.5, 2.0, 64.1, 0.90, []),
        (0.5, 1.0, 72.0, 0.40, []),
        (0.5, 1.2, 60.0, 0.85, []),
    ]

    mock_predict = MagicMock(return_value=(None, None, mock_raw_notes))
    transcriber._predict_fn = mock_predict

    notes = transcriber.transcribe(dummy_guitar_audio)

    assert len(notes) == 3
    # Check chronological ordering: at 0.5s, pitch 60 precedes pitch 72
    assert notes[0] == NoteEvent(start_time=0.5, end_time=1.2, pitch=60, amplitude=0.85)
    assert notes[1] == NoteEvent(start_time=0.5, end_time=1.0, pitch=72, amplitude=0.40)
    assert notes[2] == NoteEvent(start_time=1.5, end_time=2.0, pitch=64, amplitude=0.90)

    mock_predict.assert_called_once_with(
        dummy_guitar_audio,
        onset_threshold=0.5,
        frame_threshold=0.3,
        minimum_note_length=58.0,
    )


def test_pitch_transcriber_missing_file_raises(tmp_path: Path) -> None:
    """Ensure FileNotFoundError is raised if audio file does not exist."""
    transcriber = PitchTranscriber()
    with pytest.raises(FileNotFoundError):
        transcriber.transcribe(tmp_path / "non_existent.wav")


def test_pitch_transcriber_no_engine_raises(
    dummy_guitar_audio: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ensure RuntimeError is raised when inference engine is unavailable."""
    transcriber = PitchTranscriber()
    transcriber._predict_fn = None
    monkeypatch.setattr(transcriber, "_get_predict_fn", lambda: None)

    with pytest.raises(RuntimeError, match="not available"):
        transcriber.transcribe(dummy_guitar_audio)
