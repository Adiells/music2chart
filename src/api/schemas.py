"""Pydantic request and response schemas for REST API endpoints."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ChartPreset(StrEnum):
    """Preset configuration profiles for automated Clone Hero chart fitting."""

    THE_BEST = "the_best"
    STANDARD = "standard"
    STRICT_RHYTHM = "strict_rhythm"
    DYNAMIC_SOLO = "dynamic_solo"


PRESET_CONFIGS: dict[str, dict[str, Any]] = {
    "the_best": {
        "creativity": 0.15,
        "hopo_threshold": 48,
        "min_sustain_ticks": 96,
        "release_margin": 24,
        "min_amplitude": 0.41,
        "chord_fusion_window_s": 0.040,
        "collapse_fast_runs": True,
        "consistent_patterns": True,
        "auto_calibrate_bpm": True,
        "bpm_scale": 0.65,
        "merge_sustained_notes": True,
    },
    "standard": {
        "creativity": 0.5,
        "hopo_threshold": 65,
        "min_sustain_ticks": 72,
        "release_margin": 24,
        "min_amplitude": 0.1,
        "chord_fusion_window_s": 0.035,
        "collapse_fast_runs": True,
        "consistent_patterns": True,
        "auto_calibrate_bpm": True,
        "bpm_scale": 1.0,
        "merge_sustained_notes": True,
    },
    "strict_rhythm": {
        "creativity": 0.15,
        "hopo_threshold": 48,
        "min_sustain_ticks": 96,
        "release_margin": 24,
        "min_amplitude": 0.2,
        "chord_fusion_window_s": 0.040,
        "collapse_fast_runs": True,
        "consistent_patterns": True,
        "auto_calibrate_bpm": True,
        "bpm_scale": 1.0,
        "merge_sustained_notes": True,
    },
    "dynamic_solo": {
        "creativity": 0.85,
        "hopo_threshold": 80,
        "min_sustain_ticks": 60,
        "release_margin": 24,
        "min_amplitude": 0.08,
        "chord_fusion_window_s": 0.030,
        "collapse_fast_runs": False,
        "consistent_patterns": False,
        "auto_calibrate_bpm": True,
        "bpm_scale": 1.0,
        "merge_sustained_notes": True,
    },
}


class TaskStatus(StrEnum):
    """Lifecycle status states for an asynchronous chart generation task."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class OutputFormat(StrEnum):
    """Supported pipeline output packaging formats."""

    CHART = "chart"
    SNG = "sng"
    BOTH = "both"


class DownloadFormat(StrEnum):
    """Formats available via the download endpoint."""

    SNG = "sng"
    CHART = "chart"
    ZIP = "zip"


class ChartFittingParams(BaseModel):
    """Configurable playability, ergonomics, and metadata parameters for chart fitting."""

    preset: str | None = Field(default=None, description="Preset configuration name")
    creativity: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Creativity / solo expression factor"
    )
    min_amplitude: float = Field(
        default=0.1, ge=0.0, le=1.0, description="Minimum amplitude confidence threshold"
    )
    min_sustain_ticks: int = Field(
        default=72, ge=0, le=768, description="Minimum duration in ticks to render sustain tail"
    )
    release_margin: int = Field(
        default=24, ge=0, le=96, description="Release margin ticks before subsequent note"
    )
    chord_fusion_window_s: float = Field(
        default=0.035, ge=0.005, le=0.100, description="Acoustic chord fusion window in seconds"
    )
    bpm_scale: float = Field(
        default=1.0, gt=0.0, le=2.0, description="Tempo multiplier / scroll speed scaler"
    )
    auto_calibrate_bpm: bool = Field(
        default=True, description="Auto-halve excessive BPM (> 160.0) for comfortable scroll speed"
    )
    merge_sustained_notes: bool = Field(
        default=True, description="Merge consecutive notes on same pitch into prolonged sustains"
    )
    max_frets: int = Field(default=2, ge=1, le=3, description="Maximum simultaneous frets (1-3)")
    hopo_threshold: int = Field(
        default=65, ge=0, le=192, description="HOPO trigger tick distance threshold"
    )
    disable_open_notes: bool = Field(default=True, description="Suppress open notes on lead guitar")
    collapse_fast_runs: bool = Field(
        default=True, description="Collapse chords in fast sixteenth-note runs"
    )
    consistent_patterns: bool = Field(
        default=True, description="Enforce identical fret sequences on repeating musical riffs"
    )
    difficulty: int = Field(
        default=6, ge=1, le=6, description="Guitar track difficulty level (1-6)"
    )
    genre: str = Field(default="rock", description="Song genre")


class GenerateResponse(BaseModel):
    """Response returned upon successfully queuing a chart generation task."""

    task_id: str = Field(..., description="Unique UUID identifier for tracking the task.")
    status: str = Field(
        default=TaskStatus.PENDING.value,
        description="Initial task status (typically PENDING).",
    )
    message: str = Field(
        default="Chart generation task queued successfully.",
        description="Informational status message.",
    )


class TaskStatusResponse(BaseModel):
    """Response returned when polling task status."""

    task_id: str = Field(..., description="Unique UUID identifier of the queried task.")
    status: str = Field(
        ...,
        description="Current task status (PENDING, PROCESSING, COMPLETED, FAILED).",
    )
    progress: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Completion progress ratio between 0.0 and 1.0.",
    )
    stage: str = Field(
        default="Queued",
        description="Current pipeline processing stage.",
    )
    error: str | None = Field(
        default=None,
        description="Error details if the task failed, otherwise null.",
    )
    result_files: dict[str, str] | None = Field(
        default=None,
        description="Mapping of file names or keys to generated paths/URLs when COMPLETED.",
    )


class HealthResponse(BaseModel):
    """Health check endpoint status response."""

    status: str = Field(default="ok", description="Service health state.")
    app_name: str = Field(default="music2chart", description="Application service name.")
    version: str = Field(default="0.1.0", description="Application version.")
