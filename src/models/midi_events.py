"""Raw musical events extracted via audio-to-MIDI transcription."""

from dataclasses import dataclass


@dataclass(frozen=True)
class NoteEvent:
    """Note event extracted via polyphonic audio transcription."""

    start_time: float  # In seconds
    end_time: float  # In seconds
    pitch: int  # MIDI note number (0 - 127)
    amplitude: float  # Normalized velocity / confidence (0.0 to 1.0)

    def __post_init__(self) -> None:
        if self.start_time < 0.0:
            raise ValueError(f"start_time must be non-negative, got {self.start_time}")
        if self.end_time <= self.start_time:
            raise ValueError(
                f"end_time ({self.end_time}) must be strictly greater than start_time ({self.start_time})"
            )
        if not (0 <= self.pitch <= 127):
            raise ValueError(f"pitch must be between 0 and 127, got {self.pitch}")
        if not (0.0 <= self.amplitude <= 1.0):
            raise ValueError(f"amplitude must be between 0.0 and 1.0, got {self.amplitude}")

    @property
    def duration(self) -> float:
        """Return note duration in seconds."""
        return self.end_time - self.start_time
