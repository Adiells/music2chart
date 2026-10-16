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


def test_configure_tf_gpu_handles_no_gpus(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify _configure_tf_gpu runs safely when no physical GPUs are present."""
    mock_tf = MagicMock()
    mock_tf.config.list_physical_devices.return_value = []
    monkeypatch.setitem(__import__("sys").modules, "tensorflow", mock_tf)

    transcriber = PitchTranscriber()
    transcriber._configure_tf_gpu()
    mock_tf.config.list_physical_devices.assert_called_once_with("GPU")
    mock_tf.config.experimental.set_memory_growth.assert_not_called()


def test_configure_tf_gpu_enables_memory_growth(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify _configure_tf_gpu calls set_memory_growth for all detected GPUs."""
    mock_tf = MagicMock()
    gpu0 = MagicMock(name="GPU:0")
    gpu1 = MagicMock(name="GPU:1")
    mock_tf.config.list_physical_devices.return_value = [gpu0, gpu1]
    monkeypatch.setitem(__import__("sys").modules, "tensorflow", mock_tf)

    transcriber = PitchTranscriber()
    transcriber._configure_tf_gpu()
    mock_tf.config.list_physical_devices.assert_called_once_with("GPU")
    assert mock_tf.config.experimental.set_memory_growth.call_count == 2
    mock_tf.config.experimental.set_memory_growth.assert_any_call(gpu0, True)
    mock_tf.config.experimental.set_memory_growth.assert_any_call(gpu1, True)


def test_configure_tf_gpu_handles_runtime_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify _configure_tf_gpu gracefully handles already initialized physical devices."""
    mock_tf = MagicMock()
    gpu0 = MagicMock(name="GPU:0")
    mock_tf.config.list_physical_devices.return_value = [gpu0]
    mock_tf.config.experimental.set_memory_growth.side_effect = RuntimeError(
        "Physical devices cannot be modified after being initialized"
    )
    monkeypatch.setitem(__import__("sys").modules, "tensorflow", mock_tf)

    transcriber = PitchTranscriber()
    # Should not raise exception
    transcriber._configure_tf_gpu()
    mock_tf.config.experimental.set_memory_growth.assert_called_once_with(gpu0, True)
