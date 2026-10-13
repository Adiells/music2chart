"""System settings and environment configuration using Pydantic."""

from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _get_default_device() -> str:
    """Detect default compute device (CUDA if available, else CPU)."""
    try:
        import torch

        return "cuda" if torch.cuda.is_available() else "cpu"
    except ImportError:
        return "cpu"


class Settings(BaseSettings):
    """Application configuration parameters with environment variable overrides."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "chartgen"
    APP_ENV: str = "development"
    UPLOAD_DIR: Path = Path("tmp/uploads")
    OUTPUT_DIR: Path = Path("tmp/output")
    STEMS_DIR: Path = Path("tmp/stems")
    DATASET_DIR: Path = Path("dataset/storage")
    BASIC_PITCH_ONSET_THRESHOLD: float = 0.5
    BASIC_PITCH_FRAME_THRESHOLD: float = 0.3
    BASIC_PITCH_MIN_NOTE_LENGTH: float = 58.0
    DEMUCS_MODEL_NAME: str = "htdemucs"
    DEFAULT_RESOLUTION: int = 192
    DEVICE: str = Field(default_factory=_get_default_device)

    def ensure_directories(self) -> None:
        """Create working and storage directories if they do not exist."""
        for directory in (self.UPLOAD_DIR, self.OUTPUT_DIR, self.STEMS_DIR, self.DATASET_DIR):
            directory.mkdir(parents=True, exist_ok=True)

    def model_post_init(self, __context: Any) -> None:
        """Initialize post-validation hooks, ensuring directory structure."""
        super().model_post_init(__context)
        try:
            self.ensure_directories()
        except OSError:
            # Fallback for read-only environments
            pass


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    return Settings()
