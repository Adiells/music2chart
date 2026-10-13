"""Unit tests for AudioSeparator and stem generation."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.audio_processing.separator import AudioSeparator


@pytest.fixture
def dummy_audio_file(tmp_path: Path) -> Path:
    """Create a dummy input audio file."""
    audio = tmp_path / "song.wav"
    audio.write_bytes(b"RIFFdummy_audio_bytes")
    return audio


def test_separator_fallback_mode(dummy_audio_file: Path, tmp_path: Path) -> None:
    """Validate fallback mode generates all 4 stem files without external model."""
    output_dir = tmp_path / "stems"
    separator = AudioSeparator(fallback_to_mono_mix=True)

    collection = separator.separate(dummy_audio_file, output_dir)

    assert collection.mix_path == dummy_audio_file
    assert collection.guitar_path is not None and collection.guitar_path.exists()
    assert collection.bass_path is not None and collection.bass_path.exists()
    assert collection.drums_path is not None and collection.drums_path.exists()
    assert collection.other_path is not None and collection.other_path.exists()

    stems = collection.available_stems()
    assert set(stems.keys()) == {"guitar", "bass", "drums", "other"}


def test_separator_missing_audio_raises(tmp_path: Path) -> None:
    """Ensure missing input file triggers FileNotFoundError."""
    separator = AudioSeparator()
    with pytest.raises(FileNotFoundError):
        separator.separate(tmp_path / "non_existent.wav", tmp_path / "out")


def test_separator_mock_demucs_api(dummy_audio_file: Path, tmp_path: Path) -> None:
    """Validate separation workflow when Demucs Python API model is available."""
    output_dir = tmp_path / "stems_api"
    separator = AudioSeparator(fallback_to_mono_mix=False)

    # Mock Demucs model
    mock_model = MagicMock()

    def fake_save(tensor: object, path: Path) -> None:
        path.write_bytes(b"stem_bytes")

    mock_model.separate_audio_file.return_value = (
        None,
        {"guitar": object(), "bass": object(), "drums": object(), "other": object()},
    )
    mock_model.save_audio.side_effect = fake_save

    separator._model = mock_model

    collection = separator.separate(dummy_audio_file, output_dir)

    assert collection.guitar_path == output_dir / "guitar.wav"
    assert collection.guitar_path.exists()
    assert collection.bass_path == output_dir / "bass.wav"
    assert collection.bass_path.exists()
    assert collection.drums_path == output_dir / "drums.wav"
    assert collection.drums_path.exists()
    assert collection.other_path == output_dir / "other.wav"
    assert collection.other_path.exists()


def test_separator_mock_cli(
    dummy_audio_file: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Validate separation fallback to CLI execution."""
    output_dir = tmp_path / "stems_cli"
    separator = AudioSeparator(model_name="htdemucs", fallback_to_mono_mix=False)

    # Ensure python API fails to load
    monkeypatch.setattr(separator, "_get_model", lambda: None)

    def fake_cli(audio_path: Path, out_dir: Path) -> bool:
        # Simulate CLI creating nested stem files
        nested = out_dir / "htdemucs" / audio_path.stem
        nested.mkdir(parents=True, exist_ok=True)
        for name in ("guitar.wav", "bass.wav", "drums.wav", "other.wav"):
            (nested / name).write_bytes(b"cli_stem_bytes")
        return True

    monkeypatch.setattr(separator, "_run_demucs_cli", fake_cli)

    collection = separator.separate(dummy_audio_file, output_dir)

    assert collection.guitar_path is not None and collection.guitar_path.exists()
    assert collection.bass_path is not None and collection.bass_path.exists()
    assert collection.drums_path is not None and collection.drums_path.exists()
    assert collection.other_path is not None and collection.other_path.exists()
