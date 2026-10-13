"""Audio metadata and stem collection models."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AudioMetadata:
    """Metadata describing an audio file."""

    sample_rate: int
    channels: int
    duration_seconds: float
    file_path: Path

    def __post_init__(self) -> None:
        if self.sample_rate <= 0:
            raise ValueError(f"sample_rate must be positive, got {self.sample_rate}")
        if self.channels <= 0:
            raise ValueError(f"channels must be positive, got {self.channels}")
        if self.duration_seconds < 0.0:
            raise ValueError(f"duration_seconds cannot be negative, got {self.duration_seconds}")


@dataclass(frozen=True)
class StemCollection:
    """Paths to separated audio stems and original mix."""

    mix_path: Path
    guitar_path: Path | None = None
    bass_path: Path | None = None
    drums_path: Path | None = None
    other_path: Path | None = None

    def available_stems(self) -> dict[str, Path]:
        """Return dictionary of present instrument stems."""
        stems: dict[str, Path] = {}
        if self.guitar_path is not None:
            stems["guitar"] = self.guitar_path
        if self.bass_path is not None:
            stems["bass"] = self.bass_path
        if self.drums_path is not None:
            stems["drums"] = self.drums_path
        if self.other_path is not None:
            stems["other"] = self.other_path
        return stems
