"""Musical quantization and grid snapping engine for Clone Hero charts."""

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

from src.models.midi_events import NoteEvent
from src.models.tempo import TempoMap

logger = logging.getLogger(__name__)

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
    DEFAULT_CHORD_FUSION_WINDOW_S: float = 0.035  # 35ms acoustic strum roll window
    DEFAULT_MIN_SPACING_TICKS: int = 24  # Minimum 1/32 note spacing (24 ticks)

    def __init__(
        self,
        subdivisions: Sequence[int] | None = None,
        tolerance_ticks: int = DEFAULT_TOLERANCE_TICKS,
        resolution: int = 192,
        chord_fusion_window_s: float = DEFAULT_CHORD_FUSION_WINDOW_S,
        min_spacing_ticks: int = DEFAULT_MIN_SPACING_TICKS,
        strict_snap: bool = True,
        min_amplitude: float = 0.0,
        merge_retrigger: bool = False,
        merge_retrigger_notes: bool | None = None,
        merge_sustained_notes: bool | None = None,
        retrigger_merge_gap_s: float = 0.1,
        retrigger_merge_gap_ticks: int = 48,
    ) -> None:
        """Initialize NoteQuantizer.

        Args:
            subdivisions: Grid subdivision tick intervals to snap against.
                Defaults to (192, 96, 64, 48, 32, 24).
            tolerance_ticks: Maximum tick distance to snap to a grid point.
                Defaults to 16 ticks.
            resolution: Ticks per quarter note (PPQ). Defaults to 192.
            chord_fusion_window_s: Time window in seconds within which onsets are fused into chords.
            min_spacing_ticks: Minimum allowable tick distance between distinct consecutive notes.
            strict_snap: If True, always snaps to nearest grid point even if outside tolerance.
            min_amplitude: Minimum amplitude/confidence threshold (0.0 to 1.0) to filter ghost notes.
            merge_retrigger: If True, merges consecutive NoteEvents on the same pitch with overlapping
                or near-contiguous boundaries into prolonged notes.
            retrigger_merge_gap_s: Temporal gap threshold in seconds for re-trigger merging (default 0.1s).
            retrigger_merge_gap_ticks: Tick gap threshold for re-trigger merging (default 48 ticks).
        """
        if tolerance_ticks < 0:
            raise ValueError(f"tolerance_ticks must be non-negative, got {tolerance_ticks}")
        if resolution <= 0:
            raise ValueError(f"resolution must be positive, got {resolution}")
        if chord_fusion_window_s < 0:
            raise ValueError("chord_fusion_window_s must be non-negative")
        if min_spacing_ticks < 0:
            raise ValueError("min_spacing_ticks must be non-negative")
        if not (0.0 <= min_amplitude <= 1.0):
            raise ValueError(f"min_amplitude must be between 0.0 and 1.0, got {min_amplitude}")
        if retrigger_merge_gap_s < 0:
            raise ValueError("retrigger_merge_gap_s must be non-negative")
        if retrigger_merge_gap_ticks < 0:
            raise ValueError("retrigger_merge_gap_ticks must be non-negative")

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
        self.chord_fusion_window_s = chord_fusion_window_s
        self.min_spacing_ticks = min_spacing_ticks
        self.strict_snap = strict_snap
        self.min_amplitude = min_amplitude
        effective_merge = (
            merge_retrigger_notes
            if merge_retrigger_notes is not None
            else (merge_sustained_notes if merge_sustained_notes is not None else merge_retrigger)
        )
        self.merge_retrigger = effective_merge
        self.merge_sustained_notes = effective_merge
        self.retrigger_merge_gap_s = retrigger_merge_gap_s
        self.retrigger_merge_gap_ticks = retrigger_merge_gap_ticks

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
            Snapped non-negative tick.
        """
        tol = self.tolerance_ticks if tolerance_ticks is None else tolerance_ticks
        if tol < 0:
            raise ValueError(f"tolerance_ticks must be non-negative, got {tol}")

        t = int(round(tick))
        if t <= 0:
            return 0

        candidates: set[int] = set()
        for s in self.subdivisions:
            k_floor = (t // s) * s
            k_ceil = ((t // s) + 1) * s
            if k_floor >= 0:
                candidates.add(k_floor)
            if k_ceil >= 0:
                candidates.add(k_ceil)

        valid_candidates = [c for c in candidates if abs(c - t) <= tol]

        if not valid_candidates:
            if self.strict_snap and candidates:
                # Snap to closest subdivision in the candidate pool
                return min(
                    candidates,
                    key=lambda c: (abs(c - t), -self._get_grid_priority(c), c),
                )
            return max(0, t)

        return min(
            valid_candidates,
            key=lambda c: (abs(c - t), -self._get_grid_priority(c), c),
        )

    def fuse_chord_onsets(
        self, notes: Sequence[NoteEvent], window_s: float | None = None
    ) -> list[NoteEvent]:
        """Fuse near-simultaneous note onsets within window_s into unified chord hits."""
        if not notes:
            return []
        win = window_s if window_s is not None else self.chord_fusion_window_s
        if win <= 0:
            return list(notes)

        # Sort chronologically, then by pitch
        sorted_notes = sorted(notes, key=lambda n: (n.start_time, n.pitch))
        fused: list[NoteEvent] = []

        current_cluster: list[NoteEvent] = [sorted_notes[0]]
        cluster_anchor = sorted_notes[0].start_time

        for note in sorted_notes[1:]:
            if note.start_time - cluster_anchor <= win:
                current_cluster.append(note)
            else:
                for c in current_cluster:
                    orig_dur = max(0.01, c.end_time - c.start_time)
                    fused.append(
                        NoteEvent(
                            start_time=cluster_anchor,
                            end_time=cluster_anchor + orig_dur,
                            pitch=c.pitch,
                            amplitude=c.amplitude,
                        )
                    )
                current_cluster = [note]
                cluster_anchor = note.start_time

        for c in current_cluster:
            orig_dur = max(0.01, c.end_time - c.start_time)
            fused.append(
                NoteEvent(
                    start_time=cluster_anchor,
                    end_time=cluster_anchor + orig_dur,
                    pitch=c.pitch,
                    amplitude=c.amplitude,
                )
            )

        fused.sort(key=lambda n: (n.start_time, n.pitch))
        return fused

    def filter_minimum_spacing(
        self,
        notes: Sequence[QuantizedNote],
        min_spacing_ticks: int | None = None,
    ) -> list[QuantizedNote]:
        """Filter micro-spacing artifacts by enforcing a minimum tick distance.

        Consecutive distinct note onsets on the highway must maintain a minimum
        distance of at least min_spacing_ticks (default 24 ticks / 1/32 note).
        Sub-spacing micro-jitters are filtered out as acoustic noise artifacts.
        Chords occurring at the exact same tick are preserved intact.

        Args:
            notes: Sequence of QuantizedNotes.
            min_spacing_ticks: Minimum tick distance between consecutive distinct onsets.

        Returns:
            Filtered list of QuantizedNotes.
        """
        if not notes:
            return []
        spacing = self.min_spacing_ticks if min_spacing_ticks is None else min_spacing_ticks
        if spacing <= 0:
            return list(notes)

        # Group notes by snapped tick position
        tick_groups: dict[int, list[QuantizedNote]] = {}
        for n in notes:
            tick_groups.setdefault(n.tick, []).append(n)

        sorted_ticks = sorted(tick_groups.keys())
        if len(sorted_ticks) <= 1:
            return list(notes)

        def tick_score(t: int) -> tuple[float, int]:
            notes_at_t = tick_groups[t]
            max_amp = max(n.amplitude for n in notes_at_t)
            prio = self._get_grid_priority(t)
            return (round(max_amp, 2), prio)

        accepted_ticks: list[int] = [sorted_ticks[0]]

        for t in sorted_ticks[1:]:
            last_t = accepted_ticks[-1]
            if t - last_t < spacing:
                # Conflict: within minimum spacing window.
                # If current tick has strictly higher score and replacing last_t
                # respects spacing with accepted_ticks[-2], replace it.
                score_curr = tick_score(t)
                score_last = tick_score(last_t)
                can_replace = len(accepted_ticks) == 1 or (t - accepted_ticks[-2] >= spacing)
                if can_replace and score_curr > score_last:
                    accepted_ticks[-1] = t
                # Otherwise, discard t as micro-spacing artifact
            else:
                accepted_ticks.append(t)

        result: list[QuantizedNote] = []
        for t in accepted_ticks:
            result.extend(tick_groups[t])

        result.sort()
        return result

    def merge_retrigger_notes(
        self,
        notes: Sequence[NoteEvent],
        tempo_map: TempoMap | None = None,
        max_gap_s: float | None = None,
        max_gap_ticks: int | None = None,
    ) -> list[NoteEvent]:
        """Merge consecutive raw NoteEvents on the same pitch with overlapping or near-contiguous boundaries.

        Helps prevent sustained ringing guitar chords from being chopped into rapid repeated taps.

        Args:
            notes: Sequence of raw NoteEvents.
            tempo_map: Optional TempoMap for tick-based boundary checking.
            max_gap_s: Maximum temporal gap in seconds between note boundaries to merge (default 0.1s).
            max_gap_ticks: Maximum tick gap between note boundaries to merge (default 48 ticks).

        Returns:
            Chronologically sorted list of merged NoteEvents.
        """
        if not notes or len(notes) <= 1:
            return list(notes)

        gap_s = max_gap_s if max_gap_s is not None else self.retrigger_merge_gap_s
        gap_ticks = max_gap_ticks if max_gap_ticks is not None else self.retrigger_merge_gap_ticks

        pitch_groups: dict[int, list[NoteEvent]] = {}
        for n in notes:
            pitch_groups.setdefault(n.pitch, []).append(n)

        merged_all: list[NoteEvent] = []

        for pitch, p_notes in pitch_groups.items():
            sorted_p = sorted(p_notes, key=lambda n: (n.start_time, n.end_time))
            merged_pitch: list[NoteEvent] = [sorted_p[0]]

            for curr in sorted_p[1:]:
                prev = merged_pitch[-1]
                should_merge = False
                if curr.start_time <= prev.end_time:
                    should_merge = True
                elif curr.start_time - prev.end_time <= gap_s:
                    should_merge = True
                elif tempo_map is not None:
                    prev_end_tick = tempo_map.seconds_to_tick(prev.end_time)
                    curr_start_tick = tempo_map.seconds_to_tick(curr.start_time)
                    if curr_start_tick - prev_end_tick <= gap_ticks:
                        should_merge = True

                if should_merge:
                    merged_pitch[-1] = NoteEvent(
                        start_time=prev.start_time,
                        end_time=max(prev.end_time, curr.end_time),
                        pitch=pitch,
                        amplitude=max(prev.amplitude, curr.amplitude),
                    )
                else:
                    merged_pitch.append(curr)

            merged_all.extend(merged_pitch)

        merged_all.sort(key=lambda n: (n.start_time, n.pitch))
        return merged_all

    merge_sustain_holds = merge_retrigger_notes

    def quantize(
        self,
        notes: list[NoteEvent],
        tempo_map: TempoMap,
        merge_retrigger: bool | None = None,
        merge_sustained_notes: bool | None = None,
        merge_retrigger_notes: bool | None = None,
    ) -> list[QuantizedNote]:
        """Quantize and deduplicate NoteEvents into 192 PPQ grid QuantizedNotes.

        Args:
            notes: List of raw NoteEvents extracted from audio.
            tempo_map: TempoMap for timestamp to tick conversion.
            merge_retrigger: Optional override to enable/disable sustain-hold merging.
                If None, uses self.merge_retrigger.
            merge_sustained_notes: Alias for merge_retrigger.
            merge_retrigger_notes: Alias for merge_retrigger.

        Returns:
            Chronologically sorted, deduplicated list of QuantizedNotes.
        """
        if not notes:
            return []

        # 0. Filter low-confidence / ghost notes below min_amplitude
        active_notes = notes
        if self.min_amplitude > 0.0:
            filtered = [n for n in active_notes if n.amplitude >= self.min_amplitude]
            if not filtered:
                logger.warning(
                    "min_amplitude threshold (%.2f) filtered out all %d notes; "
                    "falling back to preserving highest confidence notes",
                    self.min_amplitude,
                    len(active_notes),
                )
                sorted_by_amp = sorted(active_notes, key=lambda n: n.amplitude, reverse=True)
                cutoff = max(1, len(sorted_by_amp) // 2)
                active_notes = sorted_by_amp[:cutoff]
            else:
                active_notes = filtered

        # 1. Sustain-hold / re-trigger merging
        override_merge = (
            merge_retrigger_notes
            if merge_retrigger_notes is not None
            else (merge_sustained_notes if merge_sustained_notes is not None else merge_retrigger)
        )
        should_merge = self.merge_retrigger if override_merge is None else override_merge
        if should_merge:
            active_notes = self.merge_retrigger_notes(active_notes, tempo_map=tempo_map)

        # 2. Pre-pass: fuse near-simultaneous onsets into unified chord hits
        fused_notes = self.fuse_chord_onsets(active_notes)

        # 3. Snapping and deduplication map: (snapped_tick, pitch) -> (max_duration_ticks, max_amplitude)
        dedup_map: dict[tuple[int, int], tuple[int, float]] = {}

        for note in fused_notes:
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

        # 4. Filter micro-spacing artifacts (minimum note spacing of min_spacing_ticks)
        if self.min_spacing_ticks > 0:
            quantized_notes = self.filter_minimum_spacing(quantized_notes, self.min_spacing_ticks)

        return quantized_notes

    quantize_notes = quantize
