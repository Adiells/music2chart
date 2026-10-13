"""Adaptive pitch-to-fret projection engine for Clone Hero charts."""

from __future__ import annotations

import bisect
from collections import defaultdict
from collections.abc import Sequence
from typing import Final

from src.game_design.quantizer import QuantizedNote
from src.models.chart import ChartNote, FretType

DEFAULT_WINDOW_TICKS: Final[int] = 1536  # ~2 measures in 4/4 at 192 PPQ
DEFAULT_MAX_JUMP: Final[int] = 3  # Maximum allowed fret jump in rapid passages
DEFAULT_RAPID_INTERVAL: Final[int] = 48  # Sixteenth-note tick interval at 192 PPQ
DEFAULT_OPEN_THRESHOLD: Final[int] = 40  # Pitches < 40 are sub-bass open notes


class PitchToFretMapper:
    """Projects quantized MIDI notes into playable Clone Hero 5-fret charts and open notes.

    Employs a dynamic centered sliding window to project pitch tessitura percentiles
    organically into 5 frets (Green 0 to Orange 4). Sub-bass notes (< open_threshold)
    are mapped to Open Strum (7) and isolated from the fretted tessitura pool. In rapid
    passages (interval < rapid_interval), wide leaps (> max_jump) are directionally clamped.
    """

    DEFAULT_WINDOW_TICKS: Final[int] = DEFAULT_WINDOW_TICKS
    DEFAULT_MAX_JUMP: Final[int] = DEFAULT_MAX_JUMP
    DEFAULT_RAPID_INTERVAL: Final[int] = DEFAULT_RAPID_INTERVAL
    DEFAULT_OPEN_THRESHOLD: Final[int] = DEFAULT_OPEN_THRESHOLD

    def __init__(
        self,
        window_ticks: int = DEFAULT_WINDOW_TICKS,
        max_jump: int = DEFAULT_MAX_JUMP,
        rapid_interval: int = DEFAULT_RAPID_INTERVAL,
        open_threshold: int = DEFAULT_OPEN_THRESHOLD,
    ) -> None:
        """Initialize PitchToFretMapper.

        Args:
            window_ticks: Size of sliding tessitura window in ticks (default 1536).
            max_jump: Maximum allowed fret jump in rapid passages (default 3).
            rapid_interval: Tick threshold defining rapid passages (default 48).
            open_threshold: Pitch cutoff below which notes become Open (default 40).

        Raises:
            ValueError: If any parameter is outside valid physical or musical bounds.
        """
        if window_ticks <= 0:
            raise ValueError(f"window_ticks must be positive, got {window_ticks}")
        if max_jump < 1:
            raise ValueError(f"max_jump must be at least 1, got {max_jump}")
        if rapid_interval < 0:
            raise ValueError(f"rapid_interval must be non-negative, got {rapid_interval}")
        if not (0 <= open_threshold <= 127):
            raise ValueError(f"open_threshold must be between 0 and 127, got {open_threshold}")

        self.window_ticks = window_ticks
        self.max_jump = max_jump
        self.rapid_interval = rapid_interval
        self.open_threshold = open_threshold

    @staticmethod
    def _compute_percentile(sorted_data: Sequence[int], q: float) -> float:
        """Compute percentile via linear interpolation (matches standard numpy method)."""
        n = len(sorted_data)
        if n == 1:
            return float(sorted_data[0])
        idx = (q / 100.0) * (n - 1)
        i = int(idx)
        alpha = idx - i
        if i + 1 < n:
            return sorted_data[i] * (1.0 - alpha) + sorted_data[i + 1] * alpha
        return float(sorted_data[-1])

    def _project_pitch_to_fret(
        self,
        window_pitches: Sequence[int],
        target_pitch: int,
    ) -> int:
        """Project a single fretted pitch (>= open_threshold) to fret [0, 4].

        Args:
            window_pitches: Sequence of all pitches within the temporal sliding window.
            target_pitch: Pitch of the current note being mapped.

        Returns:
            Projected fret index in [0, 4] (Green to Orange).
        """
        valid = [p for p in window_pitches if p >= self.open_threshold]
        if not valid:
            return 0

        p_min = min(valid)
        p_max = max(valid)
        span = p_max - p_min

        # Degenerate Case 1: Monotone passage or single note -> Green (0)
        if span == 0:
            return 0

        # Degenerate Case 2: Narrow pitch range (< 5 semitones) -> Rank order 0 to K-1
        if span < 5:
            unique_p = sorted(set(valid))
            return min(4, unique_p.index(target_pitch))

        # Standard & Wide Case (span >= 5): 5-Point Quartile Reference
        if target_pitch <= p_min:
            return 0
        if target_pitch >= p_max:
            return 4

        sorted_valid = sorted(valid)
        ref_thresholds = [
            float(p_min),
            self._compute_percentile(sorted_valid, 25.0),
            self._compute_percentile(sorted_valid, 50.0),
            self._compute_percentile(sorted_valid, 75.0),
            float(p_max),
        ]

        dists = [abs(target_pitch - t) for t in ref_thresholds]
        min_d = min(dists)
        candidates = [f for f, d in enumerate(dists) if abs(d - min_d) < 1e-6]

        if len(candidates) == 1:
            return candidates[0]

        # Tie-breaking relative to median
        median_val = ref_thresholds[2]
        if target_pitch < median_val:
            return min(candidates)
        if target_pitch > median_val:
            return max(candidates)
        return 2 if 2 in candidates else min(candidates)

    def map_notes(self, notes: Sequence[QuantizedNote]) -> list[ChartNote]:
        """Project quantized musical notes to 5-fret ChartNotes and Open strums.

        Args:
            notes: Sequence of QuantizedNotes.

        Returns:
            Chronologically and fret-sorted list of ChartNotes with sustain_length=0
            and is_hopo=False.
        """
        if not notes:
            return []

        sorted_notes = sorted(notes, key=lambda n: (n.tick, n.pitch))
        ticks = [n.tick for n in sorted_notes]
        half_window = self.window_ticks // 2

        raw_mapped: list[tuple[int, int, FretType]] = []
        for qn in sorted_notes:
            if qn.pitch < self.open_threshold:
                raw_mapped.append((qn.tick, qn.pitch, FretType.OPEN))
                continue

            t_start = qn.tick - half_window
            t_end = qn.tick + half_window
            left_idx = bisect.bisect_left(ticks, t_start)
            right_idx = bisect.bisect_right(ticks, t_end)
            w_pitches = [sorted_notes[k].pitch for k in range(left_idx, right_idx)]

            fret_val = self._project_pitch_to_fret(w_pitches, qn.pitch)
            raw_mapped.append((qn.tick, qn.pitch, FretType(fret_val)))

        # Group by tick to process chronological transitions and chords
        tick_map: dict[int, list[tuple[int, FretType]]] = defaultdict(list)
        for t, p, f in raw_mapped:
            tick_map[t].append((p, f))

        final_chart_notes: list[ChartNote] = []
        last_fretted_tick: int | None = None
        last_fretted_frets: list[int] = []

        for tick in sorted(tick_map.keys()):
            notes_at_tick = tick_map[tick]
            current_fretted: list[int] = []
            has_fretted = False

            for _p, fret in notes_at_tick:
                if fret == FretType.OPEN:
                    final_chart_notes.append(
                        ChartNote(
                            tick=tick,
                            fret=FretType.OPEN,
                            sustain_length=0,
                            is_hopo=False,
                        )
                    )
                else:
                    target_val = fret.value
                    if (
                        last_fretted_tick is not None
                        and (0 < tick - last_fretted_tick < self.rapid_interval)
                        and last_fretted_frets
                    ):
                        closest_prev = min(last_fretted_frets, key=lambda f: abs(target_val - f))
                        diff = target_val - closest_prev
                        if abs(diff) > self.max_jump:
                            if diff > 0:
                                clamped = closest_prev + self.max_jump
                            else:
                                clamped = closest_prev - self.max_jump
                            target_val = max(0, min(4, clamped))

                    has_fretted = True
                    current_fretted.append(target_val)
                    final_chart_notes.append(
                        ChartNote(
                            tick=tick,
                            fret=FretType(target_val),
                            sustain_length=0,
                            is_hopo=False,
                        )
                    )

            if has_fretted:
                last_fretted_tick = tick
                last_fretted_frets = current_fretted
            else:
                last_fretted_tick = None
                last_fretted_frets = []

        final_chart_notes.sort()
        return final_chart_notes

    # Convenience aliases
    map = map_notes
    map_pitch_to_frets = map_notes
