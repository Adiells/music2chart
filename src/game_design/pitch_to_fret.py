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
        disable_open_notes: bool = True,
        consistent_patterns: bool = True,
        min_pattern_len: int = 3,
        creativity: float = 0.5,
    ) -> None:
        """Initialize PitchToFretMapper.

        Args:
            window_ticks: Size of sliding tessitura window in ticks (default 1536).
            max_jump: Maximum allowed fret jump in rapid passages (default 3).
            rapid_interval: Tick threshold defining rapid passages (default 48).
            open_threshold: Pitch cutoff below which notes become Open (default 40).
            disable_open_notes: If True (default for lead guitar), maps sub-threshold pitches
                to Green (0) instead of Open notes (7).
            consistent_patterns: If True (default), enforces consistent motif anchoring on
                repeating musical riffs and maps repeating phrases/solos to identical fret sequences.
            min_pattern_len: Minimum consecutive notes required to form a repeating motif (default 3).
            creativity: Creativity / temperature parameter in [0.0, 1.0] (default 0.5).
                Low creativity (< 0.35) enforces strict motif anchoring with tolerance for vibrato/contour.
                High creativity (> 0.7) relaxes motif anchoring for varied solo expressions.

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
        if min_pattern_len < 1:
            raise ValueError(f"min_pattern_len must be at least 1, got {min_pattern_len}")

        self.window_ticks = window_ticks
        self.max_jump = max_jump
        self.rapid_interval = rapid_interval
        self.open_threshold = open_threshold
        self.disable_open_notes = disable_open_notes
        self.consistent_patterns = consistent_patterns
        self.min_pattern_len = min_pattern_len
        self.creativity = max(0.0, min(1.0, float(creativity)))
        self.pattern_cache: dict[tuple[int, ...], list[int]] = {}

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

    def _find_localized_root(self, valid_pitches: Sequence[int]) -> int:
        """Find the localized root pitch (lowest prominent pitch in the window/measure).

        Filters out isolated transcription noise below the true musical root/pedal tone.
        """
        if not valid_pitches:
            return 0
        p_min = min(valid_pitches)
        if len(valid_pitches) <= 3:
            return p_min

        counts: dict[int, int] = defaultdict(int)
        for p in valid_pitches:
            counts[p] += 1

        total = len(valid_pitches)
        # Prominent pitches appear at least twice or comprise >= 15% of notes
        prominent = [p for p, c in counts.items() if c >= 2 or (c / total) >= 0.15]
        if prominent:
            return min(prominent)
        return p_min

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

        # Motif Anchoring: anchor localized root to Green (0) if consistent_patterns enabled
        root_pitch = self._find_localized_root(valid) if self.consistent_patterns else min(valid)
        p_max = max(valid)

        if target_pitch <= root_pitch:
            return 0
        if target_pitch >= p_max:
            return 4

        active_pitches = [p for p in valid if p >= root_pitch]
        span = p_max - root_pitch

        # Degenerate Case 1: Monotone passage or single note -> Green (0)
        if span == 0:
            return 0

        # Degenerate Case 2: Narrow pitch range (< 5 semitones) -> Rank order 0 to K-1
        if span < 5:
            unique_p = sorted(set(active_pitches))
            idx = unique_p.index(target_pitch) if target_pitch in unique_p else 0
            return min(4, idx)

        # Standard & Wide Case (span >= 5): 5-Point Quartile Reference
        sorted_active = sorted(active_pitches)
        ref_thresholds = [
            float(root_pitch),
            self._compute_percentile(sorted_active, 25.0),
            self._compute_percentile(sorted_active, 50.0),
            self._compute_percentile(sorted_active, 75.0),
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
            Chronologically and fret-sorted list of ChartNotes preserving note duration in
            sustain_length and is_hopo=False.
        """
        if not notes:
            return []

        sorted_notes = sorted(notes, key=lambda n: (n.tick, n.pitch))
        ticks = [n.tick for n in sorted_notes]
        half_window = self.window_ticks // 2

        raw_mapped: list[tuple[int, int, FretType, int]] = []
        for qn in sorted_notes:
            if qn.pitch < self.open_threshold:
                if self.disable_open_notes:
                    raw_mapped.append((qn.tick, qn.pitch, FretType.GREEN, qn.duration_ticks))
                else:
                    raw_mapped.append((qn.tick, qn.pitch, FretType.OPEN, qn.duration_ticks))
                continue

            t_start = qn.tick - half_window
            t_end = qn.tick + half_window
            left_idx = bisect.bisect_left(ticks, t_start)
            right_idx = bisect.bisect_right(ticks, t_end)
            w_pitches = [sorted_notes[k].pitch for k in range(left_idx, right_idx)]

            fret_val = self._project_pitch_to_fret(w_pitches, qn.pitch)
            raw_mapped.append((qn.tick, qn.pitch, FretType(fret_val), qn.duration_ticks))

        # Group by tick to process chronological transitions and chords
        tick_map: dict[int, list[tuple[int, FretType, int]]] = defaultdict(list)
        for t, p, f, dur in raw_mapped:
            tick_map[t].append((p, f, dur))

        final_chart_notes: list[ChartNote] = []
        last_fretted_tick: int | None = None
        last_fretted_frets: list[int] = []

        for tick in sorted(tick_map.keys()):
            notes_at_tick = tick_map[tick]
            current_fretted: list[int] = []
            has_fretted = False

            for _p, fret, dur in notes_at_tick:
                if fret == FretType.OPEN:
                    final_chart_notes.append(
                        ChartNote(
                            tick=tick,
                            fret=FretType.OPEN,
                            sustain_length=dur,
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
                            sustain_length=dur,
                            is_hopo=False,
                        )
                    )

            if has_fretted:
                last_fretted_tick = tick
                last_fretted_frets = current_fretted
            else:
                last_fretted_tick = None
                last_fretted_frets = []

        if self.consistent_patterns and len(final_chart_notes) >= self.min_pattern_len:
            frets = [n.fret.value for n in final_chart_notes]
            consistent_frets = self._apply_pattern_consistency(sorted_notes, frets)
            final_chart_notes = [
                ChartNote(
                    tick=n.tick,
                    fret=FretType(cf),
                    sustain_length=n.sustain_length,
                    is_hopo=n.is_hopo,
                )
                for n, cf in zip(final_chart_notes, consistent_frets, strict=True)
            ]

        final_chart_notes.sort()
        return final_chart_notes

    def _clamp_following_jump(
        self,
        sorted_notes: Sequence[QuantizedNote],
        out_frets: list[int],
        next_idx: int,
    ) -> None:
        """Clamp rapid physical jump for the note immediately following a pattern replacement."""
        n_notes = len(sorted_notes)
        if next_idx >= n_notes:
            return
        prev_idx = next_idx - 1
        tick_delta = sorted_notes[next_idx].tick - sorted_notes[prev_idx].tick
        if 0 < tick_delta < self.rapid_interval:
            prev_fret = out_frets[prev_idx]
            curr_fret = out_frets[next_idx]
            if prev_fret != FretType.OPEN.value and curr_fret != FretType.OPEN.value:
                diff = curr_fret - prev_fret
                if abs(diff) > self.max_jump:
                    clamped = prev_fret + (self.max_jump if diff > 0 else -self.max_jump)
                    out_frets[next_idx] = max(0, min(4, clamped))

    def _phrases_match(
        self,
        p1: Sequence[int],
        p2: Sequence[int],
        notes1: Sequence[QuantizedNote] | None = None,
        notes2: Sequence[QuantizedNote] | None = None,
    ) -> bool:
        """Check if two pitch sequences match, incorporating creativity tolerance."""
        if len(p1) != len(p2):
            return False
        if list(p1) == list(p2):
            return True
        if self.creativity >= 0.35:
            return False

        # Low creativity (< 0.35): Strict motif anchoring
        # 1. Identical pitch contour (inter-note intervals match)
        length = len(p1)
        if length >= 2:
            contour1 = tuple(p1[k + 1] - p1[k] for k in range(length - 1))
            contour2 = tuple(p2[k + 1] - p2[k] for k in range(length - 1))
            if contour1 == contour2 and abs(p1[0] - p2[0]) <= 2:
                return True

        # 2. Slight pitch variations (+/- 1 semitone tolerance on unaccented notes)
        if abs(p1[0] - p2[0]) > 1:
            return False
        if p1[0] != p2[0]:
            if notes2 is not None and notes2[0].tick % 192 == 0:
                return False

        for k in range(1, length):
            diff = abs(p1[k] - p2[k])
            if diff == 0:
                continue
            if diff > 1:
                return False
            # +/- 1 semitone allowed on unaccented notes
            if notes2 is not None and notes2[k].tick % 192 == 0:
                if notes1 is not None and notes1[k].tick % 192 == 0:
                    return False

        return True

    def _apply_pattern_consistency(
        self,
        sorted_notes: Sequence[QuantizedNote],
        frets: list[int],
    ) -> list[int]:
        """Enforce identical fret sequences for recurring melodic motifs and solo phrases."""
        if not self.consistent_patterns or len(sorted_notes) < self.min_pattern_len:
            return list(frets)

        # High creativity (>= 0.95): completely loose, disable pattern locking
        if self.creativity >= 0.95:
            return list(frets)

        pitches = [n.pitch for n in sorted_notes]
        out_frets = list(frets)
        n_notes = len(pitches)

        # Looser motif anchoring at high creativity (> 0.7)
        if self.creativity > 0.7:
            min_len = max(self.min_pattern_len + 1, 4)
        else:
            min_len = self.min_pattern_len

        pitch_positions: dict[int, list[int]] = defaultdict(list)
        for idx, p in enumerate(pitches):
            pitch_positions[p].append(idx)

        j = 0
        while j < n_notes:
            # At high creativity (> 0.7), skip locking for high-register dynamic solos
            if self.creativity > 0.7 and (
                pitches[j] >= 72
                or (
                    j + min_len <= n_notes
                    and max(pitches[j : j + min_len]) - min(pitches[j : j + min_len]) >= 8
                )
            ):
                j += 1
                continue

            # 1. Check if pattern matches an existing entry in self.pattern_cache
            max_cache_len = max((len(k) for k in self.pattern_cache), default=0)
            best_cached_match: tuple[int, list[int]] | None = None
            if max_cache_len >= min_len:
                for length in range(min(n_notes - j, max_cache_len), min_len - 1, -1):
                    sub = tuple(pitches[j : j + length])
                    if sub in self.pattern_cache:
                        cached_raw = self.pattern_cache[sub]
                        best_cached_match = (
                            length,
                            [f.value if isinstance(f, FretType) else int(f) for f in cached_raw],
                        )
                        break
                    elif self.creativity < 0.35:
                        for cached_key, cached_raw in self.pattern_cache.items():
                            if len(cached_key) == length and self._phrases_match(
                                cached_key,
                                sub,
                                None,
                                sorted_notes[j : j + length],
                            ):
                                best_cached_match = (
                                    length,
                                    [
                                        f.value if isinstance(f, FretType) else int(f)
                                        for f in cached_raw
                                    ],
                                )
                                break
                        if best_cached_match is not None:
                            break

            # 2. Check if pattern matches an earlier occurrence in the track (i < j)
            best_earlier_len = 0
            best_earlier_i = -1

            candidate_indices: list[int]
            if self.creativity < 0.35:
                cand_set: set[int] = set(pitch_positions[pitches[j]])
                cand_set.update(pitch_positions[pitches[j] - 1])
                cand_set.update(pitch_positions[pitches[j] + 1])
                candidate_indices = sorted(idx for idx in cand_set if idx < j)
            else:
                candidate_indices = [idx for idx in pitch_positions[pitches[j]] if idx < j]

            for i in candidate_indices:
                max_l = min(n_notes - j, j - i)
                if self.creativity < 0.35:
                    matched_len = 0
                    for test_len in range(min_len, max_l + 1):
                        p_sub_i = pitches[i : i + test_len]
                        p_sub_j = pitches[j : j + test_len]
                        if self._phrases_match(
                            p_sub_i,
                            p_sub_j,
                            sorted_notes[i : i + test_len],
                            sorted_notes[j : j + test_len],
                        ):
                            matched_len = test_len
                        else:
                            break
                    if matched_len >= min_len and matched_len > best_earlier_len:
                        best_earlier_len = matched_len
                        best_earlier_i = i
                else:
                    length = 0
                    while length < max_l and pitches[i + length] == pitches[j + length]:
                        length += 1
                    if length >= min_len and length > best_earlier_len:
                        best_earlier_len = length
                        best_earlier_i = i

            # Decide best match between cache and earlier occurrence
            if best_cached_match is not None and best_cached_match[0] >= best_earlier_len:
                match_len, canonical_frets = best_cached_match
                out_frets[j : j + match_len] = canonical_frets
                self._clamp_following_jump(sorted_notes, out_frets, j + match_len)
                j += match_len
                continue

            if best_earlier_len >= min_len:
                canonical_frets = list(
                    out_frets[best_earlier_i : best_earlier_i + best_earlier_len]
                )
                out_frets[j : j + best_earlier_len] = canonical_frets
                self.pattern_cache[tuple(pitches[j : j + best_earlier_len])] = canonical_frets
                self._clamp_following_jump(sorted_notes, out_frets, j + best_earlier_len)
                j += best_earlier_len
                continue

            # 3. If no earlier occurrence or cached pattern, check if it repeats later (i > j)
            best_later_len = 0
            later_candidate_indices: list[int]
            if self.creativity < 0.35:
                cand_later: set[int] = set(pitch_positions[pitches[j]])
                cand_later.update(pitch_positions[pitches[j] - 1])
                cand_later.update(pitch_positions[pitches[j] + 1])
                later_candidate_indices = sorted(idx for idx in cand_later if idx > j)
            else:
                later_candidate_indices = [idx for idx in pitch_positions[pitches[j]] if idx > j]

            for i in later_candidate_indices:
                max_l = min(n_notes - j, n_notes - i)
                if self.creativity < 0.35:
                    matched_len = 0
                    for test_len in range(min_len, max_l + 1):
                        p_sub_j = pitches[j : j + test_len]
                        p_sub_i = pitches[i : i + test_len]
                        if self._phrases_match(
                            p_sub_j,
                            p_sub_i,
                            sorted_notes[j : j + test_len],
                            sorted_notes[i : i + test_len],
                        ):
                            matched_len = test_len
                        else:
                            break
                    if matched_len >= min_len and matched_len > best_later_len:
                        best_later_len = matched_len
                else:
                    length = 0
                    while length < max_l and pitches[j + length] == pitches[i + length]:
                        length += 1
                    if length >= min_len and length > best_later_len:
                        best_later_len = length

            if best_later_len >= min_len:
                pattern_key = tuple(pitches[j : j + best_later_len])
                if pattern_key not in self.pattern_cache:
                    self.pattern_cache[pattern_key] = list(out_frets[j : j + best_later_len])

            j += 1

        return out_frets

    # Convenience aliases
    map = map_notes
    map_pitch_to_frets = map_notes
