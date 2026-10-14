"""Unit tests for system configuration management."""

from pathlib import Path

import pytest

from config.settings import Settings, get_settings


def test_settings_defaults_and_types() -> None:
    """Validate default configuration values and their corresponding types."""
    settings = Settings()

    # Type assertions
    assert isinstance(settings.APP_NAME, str)
    assert isinstance(settings.APP_ENV, str)
    assert isinstance(settings.UPLOAD_DIR, Path)
    assert isinstance(settings.OUTPUT_DIR, Path)
    assert isinstance(settings.STEMS_DIR, Path)
    assert isinstance(settings.DATASET_DIR, Path)
    assert isinstance(settings.BASIC_PITCH_ONSET_THRESHOLD, float)
    assert isinstance(settings.BASIC_PITCH_FRAME_THRESHOLD, float)
    assert isinstance(settings.BASIC_PITCH_MIN_NOTE_LENGTH, float)
    assert isinstance(settings.DEMUCS_MODEL_NAME, str)
    assert isinstance(settings.DEFAULT_RESOLUTION, int)
    assert isinstance(settings.DEVICE, str)

    # Default value assertions
    assert settings.APP_NAME == "music2chart"
    assert settings.APP_ENV == "development"
    assert settings.UPLOAD_DIR == Path("tmp/uploads")
    assert settings.OUTPUT_DIR == Path("tmp/output")
    assert settings.STEMS_DIR == Path("tmp/stems")
    assert settings.DATASET_DIR == Path("dataset/storage")
    assert settings.BASIC_PITCH_ONSET_THRESHOLD == 0.5
    assert settings.BASIC_PITCH_FRAME_THRESHOLD == 0.3
    assert settings.BASIC_PITCH_MIN_NOTE_LENGTH == 58.0
    assert settings.DEMUCS_MODEL_NAME == "htdemucs"
    assert settings.DEFAULT_RESOLUTION == 192
    assert settings.DEVICE in ("cuda", "cpu")


def test_directory_auto_creation(tmp_path: Path) -> None:
    """Verify that required working directories are created automatically upon instantiation."""
    custom_upload = tmp_path / "custom_uploads"
    custom_output = tmp_path / "custom_output"
    custom_stems = tmp_path / "custom_stems"
    custom_dataset = tmp_path / "custom_dataset"

    # Pre-condition: directories should not exist yet
    assert not custom_upload.exists()
    assert not custom_output.exists()
    assert not custom_stems.exists()
    assert not custom_dataset.exists()

    settings = Settings(
        UPLOAD_DIR=custom_upload,
        OUTPUT_DIR=custom_output,
        STEMS_DIR=custom_stems,
        DATASET_DIR=custom_dataset,
    )
    assert settings.UPLOAD_DIR == custom_upload

    # Post-condition: directories should be created
    assert custom_upload.exists() and custom_upload.is_dir()
    assert custom_output.exists() and custom_output.is_dir()
    assert custom_stems.exists() and custom_stems.is_dir()
    assert custom_dataset.exists() and custom_dataset.is_dir()


def test_settings_environment_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """Validate that environment variables properly override defaults."""
    monkeypatch.setenv("APP_NAME", "custom_music2chart")
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DEFAULT_RESOLUTION", "480")
    monkeypatch.setenv("DEVICE", "cpu")

    settings = Settings()
    assert settings.APP_NAME == "custom_music2chart"
    assert settings.APP_ENV == "production"
    assert settings.DEFAULT_RESOLUTION == 480
    assert settings.DEVICE == "cpu"


def test_get_settings_singleton() -> None:
    """Validate that get_settings returns a cached instance."""
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
