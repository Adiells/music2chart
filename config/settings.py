"""System settings and environment configuration using Pydantic."""

from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
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

    APP_NAME: str = "music2chart"
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
    DEFAULT_CREATIVITY: float = 0.5
    DEFAULT_HOPO_THRESHOLD: int = 65
    DEFAULT_MIN_SUSTAIN_TICKS: int = 72
    DEFAULT_RELEASE_MARGIN: int = 24
    DEFAULT_MIN_AMPLITUDE: float = 0.1
    DEFAULT_CHORD_FUSION_WINDOW_S: float = 0.035
    DEFAULT_BPM_SCALE: float = 1.0
    DEFAULT_AUTO_CALIBRATE_BPM: bool = True
    DEFAULT_MERGE_SUSTAINED_NOTES: bool = True
    DEVICE: str = Field(default_factory=_get_default_device)

    # Security, concurrency, and retention configuration
    MAX_UPLOAD_SIZE_BYTES: int = 100 * 1024 * 1024  # 100 MB
    MAX_AUDIO_DURATION_SECONDS: float = 900.0  # 15 minutes
    MAX_CONCURRENT_TASKS: int = 1  # Maximum concurrent heavy pipeline tasks
    TASK_QUEUE_CAPACITY: int = 10  # Queue capacity before HTTP 429
    TASK_TTL_SECONDS: int = 7200  # 2 hours task retention
    CLEANUP_INTERVAL_SECONDS: int = 300  # Background cleanup every 5 minutes
    ALLOWED_ORIGINS: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://localhost:8000",
            "http://localhost:3000",
            "https://music2chart.adiels.me",
            "http://music2chart.adiels.me",
            "https://adiels.me",
        ]
    )
    RATE_LIMIT_GENERATE: str = "10/minute"
    ENABLE_AUTO_STEM_CLEANUP: bool = True  # Clean intermediate stems after packaging

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def _parse_allowed_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        if isinstance(v, (list, tuple, set)):
            return [str(origin).strip() for origin in v]
        return [str(origin).strip() for origin in list(v)] if v is not None else []

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
