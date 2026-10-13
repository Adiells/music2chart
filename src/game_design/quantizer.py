"""Musical quantization and grid snapping engine for Clone Hero charts."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

from src.models.midi_events import NoteEvent
from src.models.tempo import TempoMap

# Priority scores for musical hierarchy tie-breaking (higher = more fundamental).
# Hierarchy: 192 (1/4) > 96 (1/8) > 48 (1/16) > 64 (1/12) > 32 (1/24) > 24 (1/32).
_PRIORITY_QUARTER: Final[int] = 6  # 192 PPQ (1/4 note)
_PRIORITY_EIGHTH: Final[int] = 5  # 96 PPQ (1/8 note)
_PRIORITY_SIXTEENTH: Final[int] = 4  # 48 PPQ (1/16 note)
_PRIORITY_EIGHTH_TRIPLET: Final[int] = 3  # 64 PPQ (1/12 triplet)
_PRIORITY_SIXTEENTH_TRIPLET: Final[int] = 2  # 32 PPQ (1/24 triplet)
_PRIORITY_THIRTY_SECOND: Final[int] = 1  # 24 PPQ (1/32 note)


@dataclass(frozen=True, slots=True, order=True)
class QuantizedNote:
    """A quantized musical note aligned to the 192 PPQ grid."""

    tick: int  # Snapped grid position in ticks (>= 0)
    pitch: int  # MIDI note number (0 - 127)
    duration_ticks: int  # Acoustic duration in ticks (>= 0)
    amplitude: float  # Normalized velocity / confidence (0.0 to 1.0)

    def __post_init__(self) -> None:
        if self.tick < 0:
            raise ValueError(f"tick must be non-negative, got {self.tick}")
        if not (0 <= self.pitch <= 127):
            raise ValueError(f"pitch must be between 0 and 127, got {self.pitch}")
        if self.duration_ticks < 0:
            raise ValueError(f"duration_ticks must be non-negative, got {self.duration_ticks}")
        if not (0.0 <= self.amplitude <= 1.0):
            raise ValueError(f"amplitude must be between 0.0 and 1.0, got {self.amplitude}")


class NoteQuantizer:
    """Snaps continuous NoteEvents to a 192 PPQ musical grid and deduplicates."""

    DEFAULT_SUBDIVISIONS: tuple[int, ...] = (192, 96, 64, 48, 32, 24)
    DEFAULT_TOLERANCE_TICKS: int = 16

    def __init__(
        self,
        subdivisions: Sequence[int] | None = None,
        tolerance_ticks: int = DEFAULT_TOLERANCE_TICKS,
        resolution: int = 192,
    ) -> None:
        """Initialize NoteQuantizer.

        Args:
            subdivisions: Grid subdivision tick intervals to snap against.
                Defaults to (192, 96, 64, 48, 32, 24).
            tolerance_ticks: Maximum tick distance to snap to a grid point.
                Defaults to 16 ticks.
            resolution: Ticks per quarter note (PPQ). Defaults to 192.
        """
        if tolerance_ticks < 0:
            raise ValueError(f"tolerance_ticks must be non-negative, got {tolerance_ticks}")
        if resolution <= 0:
            raise ValueError(f"resolution must be positive, got {resolution}")

        if subdivisions is not None:
            subdiv_tuple = tuple(subdivisions)
            if not subdiv_tuple:
                raise ValueError("subdivisions cannot be empty")
            if any(s <= 0 for s in subdiv_tuple):
                raise ValueError("all subdivisions must be positive integers")
            self.subdivisions: tuple[int, ...] = subdiv_tuple
        else:
            self.subdivisions = self.DEFAULT_SUBDIVISIONS

        self.tolerance_ticks = tolerance_ticks
        self.resolution = resolution

    @staticmethod
    def _get_grid_priority(tick: int) -> int:
        """Return musical hierarchy priority for tie-breaking equidistant grid points."""
        if tick % 192 == 0:
            return _PRIORITY_QUARTER
        if tick % 96 == 0:
            return _PRIORITY_EIGHTH
        if tick % 48 == 0:
            return _PRIORITY_SIXTEENTH
        if tick % 64 == 0:
            return _PRIORITY_EIGHTH_TRIPLET
        if tick % 32 == 0:
            return _PRIORITY_SIXTEENTH_TRIPLET
        if tick % 24 == 0:
            return _PRIORITY_THIRTY_SECOND
        return 0

    def snap_tick(self, tick: int, tolerance_ticks: int | None = None) -> int:
        """Snap a raw tick position to the nearest active subdivision point within tolerance.

        Args:
            tick: Raw tick position.
            tolerance_ticks: Optional tolerance override in ticks.

        Returns:
            Snapped non-negative tick, or max(0, tick) if outside tolerance window.
        """
        tol = self.tolerance_ticks if tolerance_ticks is None else tolerance_ticks
        if tol < 0:
            raise ValueError(f"tolerance_ticks must be non-negative, got {tol}")

        t = int(round(tick))

        candidates: set[int] = set()
        for s in self.subdivisions:
            min_k = (t - tol) // s
            max_k = (t + tol) // s + 1
            for k in range(min_k, max_k + 1):
                candidates.add(k * s)

        valid_candidates = [c for c in candidates if c >= 0 and abs(c - t) <= tol]

        if not valid_candidates:
            return max(0, t)

        return min(
            valid_candidates,
            key=lambda c: (abs(c - t), -self._get_grid_priority(c), c),
        )

    def quantize(
        self,
        notes: list[NoteEvent],
        tempo_map: TempoMap,
    ) -> list[QuantizedNote]:
        """Quantize and deduplicate NoteEvents into 192 PPQ grid QuantizedNotes.

        Args:
            notes: List of raw NoteEvents extracted from audio.
            tempo_map: TempoMap for timestamp to tick conversion.

        Returns:
            Chronologically sorted, deduplicated list of QuantizedNotes.
        """
        if not notes:
            return []

        # Deduplication map: (snapped_tick, pitch) -> (max_duration_ticks, max_amplitude)
        dedup_map: dict[tuple[int, int], tuple[int, float]] = {}

        for note in notes:
            raw_start = tempo_map.seconds_to_tick(note.start_time)
            raw_end = tempo_map.seconds_to_tick(note.end_time)
            snapped_start = self.snap_tick(raw_start)
            duration_ticks = max(1, raw_end - raw_start)

            key = (snapped_start, note.pitch)
            if key not in dedup_map:
                dedup_map[key] = (duration_ticks, note.amplitude)
            else:
                prev_dur, prev_amp = dedup_map[key]
                dedup_map[key] = (
                    max(prev_dur, duration_ticks),
                    max(prev_amp, note.amplitude),
                )

        quantized_notes = [
            QuantizedNote(
                tick=tick,
                pitch=pitch,
                duration_ticks=dur,
                amplitude=amp,
            )
            for (tick, pitch), (dur, amp) in dedup_map.items()
        ]

        quantized_notes.sort()
        return quantized_notes

    quantize_notes = quantize
