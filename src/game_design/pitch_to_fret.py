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
DEFAULT_MOTIF_SIMILARITY_THRESHOLD: Final[float] = 0.75  # Fuzzy motif alignment similarity threshold


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
    DEFAULT_MOTIF_SIMILARITY_THRESHOLD: Final[float] = DEFAULT_MOTIF_SIMILARITY_THRESHOLD

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
        motif_similarity_threshold: float = DEFAULT_MOTIF_SIMILARITY_THRESHOLD,
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
                Controls high-register solo freedom and variance.
            motif_similarity_threshold: Minimum fuzzy sequence alignment similarity threshold
                in [0.0, 1.0] (default 0.75) for matching repeating motifs.

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
        if not (0.0 <= motif_similarity_threshold <= 1.0):
            raise ValueError(
                f"motif_similarity_threshold must be between 0.0 and 1.0, got {motif_similarity_threshold}"
            )

        self.window_ticks = window_ticks
        self.max_jump = max_jump
        self.rapid_interval = rapid_interval
        self.open_threshold = open_threshold
        self.disable_open_notes = disable_open_notes
        self.consistent_patterns = consistent_patterns
        self.min_pattern_len = min_pattern_len
        self.creativity = max(0.0, min(1.0, float(creativity)))
        self.motif_similarity_threshold = float(motif_similarity_threshold)
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

    def _compute_phrase_similarity(
        self,
        p1: Sequence[int],
        p2: Sequence[int],
        dur1: Sequence[int] | None = None,
        dur2: Sequence[int] | None = None,
    ) -> tuple[float, list[tuple[int | None, int | None]]]:
        """Compute fuzzy sequence similarity and optimal alignment via dynamic programming.

        Uses smooth substitution penalties:
        - Exact match (diff == 0): 0.0
        - Vibrato (diff == 1): 0.15
        - Bend (diff == 2): 0.35 (or 0.20 if melodic contour matches)
        - Octave / harmonic (diff == 12): 0.40
        - Other intervals: min(1.0, diff * 0.25)
        - Insertion / Deletion (ghost notes / omissions): 1.0

        Args:
            p1: Reference / canonical pitch sequence.
            p2: Candidate pitch sequence.
            dur1: Optional duration ticks for p1 notes.
            dur2: Optional duration ticks for p2 notes.

        Returns:
            Tuple of (similarity_score [0.0..1.0], alignment_path).
            Alignment path consists of (idx1, idx2) index pairs, where None indicates
            an insertion (in p2) or deletion (from p1).
        """
        n, m = len(p1), len(p2)
        if n == 0 and m == 0:
            return 1.0, []
        if n == 0:
            return 0.0, [(None, j) for j in range(m)]
        if m == 0:
            return 0.0, [(i, None) for i in range(n)]

        # Fast path 1: identical sequences
        if n == m and list(p1) == list(p2):
            return 1.0, [(k, k) for k in range(n)]

        # Fast path 2: length difference exceeds maximum insertion/deletion tolerance (2 notes)
        if abs(n - m) > 2:
            return 0.0, []

        # Fast path 3: disjoint pitch ranges
        if max(p1) < min(p2) - 2 or max(p2) < min(p1) - 2:
            return 0.0, []

        # Check identical pitch contour bonus (e.g. slight transposition within 2 semitones)
        contour_matched = False
        if n == m and n >= 2 and abs(p1[0] - p2[0]) <= 2:
            c1 = tuple(p1[k + 1] - p1[k] for k in range(n - 1))
            c2 = tuple(p2[k + 1] - p2[k] for k in range(m - 1))
            if c1 == c2:
                contour_matched = True

        dp = [[0.0] * (m + 1) for _ in range(n + 1)]
        for i in range(n + 1):
            dp[i][0] = i * 1.0
        for j in range(m + 1):
            dp[0][j] = j * 1.0

        for i in range(1, n + 1):
            for j in range(1, m + 1):
                diff = abs(p1[i - 1] - p2[j - 1])
                if diff == 0:
                    cost = 0.0
                elif diff == 1:
                    cost = 0.15
                elif diff == 2:
                    cost = 0.20 if contour_matched else 0.35
                elif diff == 12:
                    cost = 0.40
                else:
                    cost = min(1.0, diff * 0.25)

                dp[i][j] = min(
                    dp[i - 1][j - 1] + cost,
                    dp[i - 1][j] + 1.0,
                    dp[i][j - 1] + 1.0,
                )

        max_len = max(n, m)
        similarity = max(0.0, 1.0 - (dp[n][m] / max_len)) if max_len > 0 else 1.0

        # Backtrack optimal alignment path
        alignment: list[tuple[int | None, int | None]] = []
        i, j = n, m
        while i > 0 or j > 0:
            # When target has consecutive identical notes, prefer treating the second one as insertion
            if j > 1 and p2[j - 1] == p2[j - 2] and abs(dp[i][j] - (dp[i][j - 1] + 1.0)) < 1e-6:
                alignment.append((None, j - 1))
                j -= 1
                continue
            if i > 0 and j > 0:
                diff = abs(p1[i - 1] - p2[j - 1])
                if diff == 0:
                    cost = 0.0
                elif diff == 1:
                    cost = 0.15
                elif diff == 2:
                    cost = 0.20 if contour_matched else 0.35
                elif diff == 12:
                    cost = 0.40
                else:
                    cost = min(1.0, diff * 0.25)
                if abs(dp[i][j] - (dp[i - 1][j - 1] + cost)) < 1e-6:
                    alignment.append((i - 1, j - 1))
                    i -= 1
                    j -= 1
                    continue
            if j > 0 and abs(dp[i][j] - (dp[i][j - 1] + 1.0)) < 1e-6:
                alignment.append((None, j - 1))
                j -= 1
                continue
            if i > 0 and abs(dp[i][j] - (dp[i - 1][j] + 1.0)) < 1e-6:
                alignment.append((i - 1, None))
                i -= 1
                continue
            # Fallback step
            if i > 0 and j > 0:
                alignment.append((i - 1, j - 1))
                i -= 1
                j -= 1
            elif j > 0:
                alignment.append((None, j - 1))
                j -= 1
            elif i > 0:
                alignment.append((i - 1, None))
                i -= 1

        alignment.reverse()
        return similarity, alignment

    def _align_phrase_frets(
        self,
        canonical_frets: Sequence[int],
        canonical_pitches: Sequence[int],
        target_pitches: Sequence[int],
        target_base_frets: Sequence[int],
        alignment: Sequence[tuple[int | None, int | None]],
    ) -> list[int]:
        """Align target phrase frets to canonical motif frets.

        Follows Option A (turnaround variation preservation) & ghost note interpolation:
        - Matched core notes receive the canonical fret.
        - Modified turnaround notes (ending variations) transition smoothly from preceding fret,
          clamped by max_jump.
        - Inserted ghost notes interpolate from their nearest neighbor fret, clamped by max_jump.

        Args:
            canonical_frets: Fret sequence of reference canonical motif.
            canonical_pitches: MIDI pitches of reference canonical motif.
            target_pitches: MIDI pitches of target phrase to map.
            target_base_frets: Pre-computed sliding-window base frets for target phrase.
            alignment: Alignment index pairs (idx1, idx2) produced by _compute_phrase_similarity.

        Returns:
            List of fret values for target phrase matching the length of target_pitches.
        """
        m = len(target_pitches)
        if m == 0:
            return []

        result_frets = [0] * m

        # Map each target note index j to its canonical counterpart (if any)
        target_to_canonical: dict[int, int | None] = {}
        for idx1, idx2 in alignment:
            if idx2 is not None:
                target_to_canonical[idx2] = idx1

        for j in range(m):
            idx1 = target_to_canonical.get(j, None)

            # Case 1: Insertion (Ghost note)
            if idx1 is None:
                # Interpolate from nearest neighbor
                if j > 0:
                    neighbor_fret = result_frets[j - 1]
                elif j + 1 < m:
                    neighbor_fret = target_base_frets[j + 1]
                else:
                    neighbor_fret = target_base_frets[j]

                # If same pitch as neighbor, use identical fret
                if j > 0 and target_pitches[j] == target_pitches[j - 1]:
                    result_frets[j] = neighbor_fret
                else:
                    base = target_base_frets[j]
                    if neighbor_fret == FretType.OPEN.value or base == FretType.OPEN.value:
                        result_frets[j] = base
                    else:
                        diff = base - neighbor_fret
                        if abs(diff) > self.max_jump:
                            clamped = neighbor_fret + (self.max_jump if diff > 0 else -self.max_jump)
                            result_frets[j] = max(0, min(4, clamped))
                        else:
                            result_frets[j] = base
                continue

            # Case 2: Aligned to canonical note idx1
            c_pitch = canonical_pitches[idx1]
            t_pitch = target_pitches[j]
            c_fret = canonical_frets[idx1]
            p_diff = abs(c_pitch - t_pitch)

            # Core match: exact (0), vibrato (1), bend (2), or octave/harmonic (12)
            if p_diff <= 2 or p_diff == 12:
                result_frets[j] = c_fret
            else:
                # Option A: Turnaround / fill variation note
                # Retains musical character from base fret but transitions smoothly from prev note
                base = target_base_frets[j]
                if j > 0:
                    prev_fret = result_frets[j - 1]
                    if prev_fret == FretType.OPEN.value or base == FretType.OPEN.value:
                        result_frets[j] = base
                    else:
                        diff = base - prev_fret
                        if abs(diff) > self.max_jump:
                            clamped = prev_fret + (self.max_jump if diff > 0 else -self.max_jump)
                            result_frets[j] = max(0, min(4, clamped))
                        else:
                            result_frets[j] = base
                else:
                    result_frets[j] = base

        return result_frets

    def _phrases_match(
        self,
        p1: Sequence[int],
        p2: Sequence[int],
        notes1: Sequence[QuantizedNote] | None = None,
        notes2: Sequence[QuantizedNote] | None = None,
    ) -> bool:
        """Check if two pitch sequences match, incorporating fuzzy sequence similarity."""
        if list(p1) == list(p2):
            return True
        sim, _ = self._compute_phrase_similarity(p1, p2)
        return sim >= self.motif_similarity_threshold

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

        def get_max_phrase_len(start_idx: int) -> int:
            """Maximum consecutive notes before a silence gap (rest > 768 ticks)."""
            idx = start_idx
            while idx + 1 < n_notes and (sorted_notes[idx + 1].tick - sorted_notes[idx].tick <= 768):
                idx += 1
            return idx - start_idx + 1

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

            limit_j = get_max_phrase_len(j)
            if limit_j < min_len:
                j += 1
                continue

            # 1. Check if pattern matches an existing entry in self.pattern_cache
            max_cache_len = max((len(k) for k in self.pattern_cache), default=0)
            best_cached_match: tuple[int, list[int], float] | None = None
            if max_cache_len >= min_len:
                # 1a. Fast exact lookup
                for length in range(min(n_notes - j, max_cache_len, limit_j), min_len - 1, -1):
                    sub = tuple(pitches[j : j + length])
                    if sub in self.pattern_cache:
                        cached_raw = self.pattern_cache[sub]
                        canonical_frets = [
                            f.value if isinstance(f, FretType) else int(f) for f in cached_raw
                        ]
                        best_cached_match = (length, canonical_frets, 1.0)
                        break

                # 1b. Fuzzy cached lookup if no exact match found
                if best_cached_match is None:
                    best_fuzzy_len = 0
                    best_fuzzy_score = 0.0
                    for cached_key, cached_raw in self.pattern_cache.items():
                        c_len = len(cached_key)
                        if c_len < min_len:
                            continue
                        canonical_frets = [
                            f.value if isinstance(f, FretType) else int(f) for f in cached_raw
                        ]
                        # Target phrase can vary by +/- 2 notes due to ghost notes / omissions
                        min_sub_l = max(min_len, c_len - 2)
                        max_sub_l = min(n_notes - j, c_len + 2, limit_j)
                        for sub_len in range(max_sub_l, min_sub_l - 1, -1):
                            target_sub = pitches[j : j + sub_len]
                            sim, alignment = self._compute_phrase_similarity(cached_key, target_sub)
                            if sim >= self.motif_similarity_threshold:
                                if sub_len > best_fuzzy_len or (
                                    sub_len == best_fuzzy_len and sim > best_fuzzy_score
                                ):
                                    aligned_frets = self._align_phrase_frets(
                                        canonical_frets=canonical_frets,
                                        canonical_pitches=cached_key,
                                        target_pitches=target_sub,
                                        target_base_frets=out_frets[j : j + sub_len],
                                        alignment=alignment,
                                    )
                                    best_fuzzy_len = sub_len
                                    best_fuzzy_score = sim
                                    best_cached_match = (sub_len, aligned_frets, sim)
                                if sim >= 0.95:
                                    break

            # 2. Check if pattern matches an earlier occurrence in the track (i < j)
            best_earlier_len = 0
            best_earlier_i = -1
            best_earlier_target_len = 0
            best_earlier_frets: list[int] | None = None
            best_earlier_score = 0.0

            cand_set: set[int] = set()
            for delta in (0, -1, 1, -2, 2, -12, 12):
                cand_set.update(pitch_positions.get(pitches[j] + delta, ()))
            if j + 1 < n_notes:
                for delta in (0, -1, 1):
                    for cand in pitch_positions.get(pitches[j + 1] + delta, ()):
                        if cand > 0:
                            cand_set.add(cand - 1)

            candidate_indices = sorted(idx for idx in cand_set if j - idx >= min_len)

            for i in candidate_indices:
                limit_i = get_max_phrase_len(i)
                max_l = min(n_notes - j, j - i, limit_i, limit_j)
                if max_l < min_len:
                    continue

                # Fast prefix filter: at least first note must be in range
                d0 = abs(pitches[i] - pitches[j])
                if d0 > 2 and d0 != 12:
                    if j + 1 < n_notes and (abs(pitches[i] - pitches[j + 1]) <= 2 or abs(pitches[i] - pitches[j + 1]) == 12):
                        pass
                    elif i + 1 < n_notes and (abs(pitches[i + 1] - pitches[j]) <= 2 or abs(pitches[i + 1] - pitches[j]) == 12):
                        pass
                    else:
                        continue

                # 2a. Fast exact match probe
                exact_l = 0
                while exact_l < max_l and pitches[i + exact_l] == pitches[j + exact_l]:
                    exact_l += 1

                if exact_l >= min_len and exact_l > best_earlier_len:
                    best_earlier_len = exact_l
                    best_earlier_target_len = exact_l
                    best_earlier_i = i
                    best_earlier_frets = list(out_frets[i : i + exact_l])
                    best_earlier_score = 1.0

                # 2b. Fast scan to estimate plausible match length
                scan_l = 0
                mismatches = 0
                max_probe = min(max_l, 24)
                while scan_l < max_probe and mismatches <= 2:
                    d = abs(pitches[i + scan_l] - pitches[j + scan_l])
                    if d > 2 and d != 12:
                        mismatches += 1
                    scan_l += 1
                plausible_l = scan_l if mismatches <= 2 else scan_l - 1
                if plausible_l < min_len or plausible_l < best_earlier_len:
                    continue

                # Fuzzy probe focused exclusively around plausible length
                candidate_test_lengths = {plausible_l}
                if plausible_l - 1 >= min_len:
                    candidate_test_lengths.add(plausible_l - 1)
                if plausible_l + 1 <= max_probe:
                    candidate_test_lengths.add(plausible_l + 1)

                for test_l in sorted(candidate_test_lengths, reverse=True):
                    if test_l < best_earlier_len:
                        break
                    for target_l in (test_l, test_l + 1, test_l - 1):
                        if target_l < min_len or j + target_l > n_notes or target_l > limit_j:
                            continue
                        p1_sub = pitches[i : i + test_l]
                        p2_sub = pitches[j : j + target_l]
                        sim, alignment = self._compute_phrase_similarity(p1_sub, p2_sub)
                        if sim >= self.motif_similarity_threshold:
                            if test_l > best_earlier_len or (
                                test_l == best_earlier_len and sim > best_earlier_score
                            ):
                                canonical_frets = list(out_frets[i : i + test_l])
                                aligned = self._align_phrase_frets(
                                    canonical_frets=canonical_frets,
                                    canonical_pitches=p1_sub,
                                    target_pitches=p2_sub,
                                    target_base_frets=out_frets[j : j + target_l],
                                    alignment=alignment,
                                )
                                best_earlier_len = test_l
                                best_earlier_target_len = target_l
                                best_earlier_i = i
                                best_earlier_frets = aligned
                                best_earlier_score = sim
                            if sim >= 0.95:
                                break

            # Decide best match between cache and earlier occurrence
            cached_len = best_cached_match[0] if best_cached_match is not None else 0
            cached_score = best_cached_match[2] if best_cached_match is not None else 0.0

            if best_cached_match is not None and (
                cached_len > best_earlier_len
                or (cached_len == best_earlier_len and cached_score >= best_earlier_score)
            ):
                match_len, canonical_frets, _ = best_cached_match
                out_frets[j : j + match_len] = canonical_frets
                self._clamp_following_jump(sorted_notes, out_frets, j + match_len)
                j += match_len
                continue

            if best_earlier_frets is not None and best_earlier_len >= min_len:
                out_frets[j : j + best_earlier_target_len] = best_earlier_frets
                pattern_key = tuple(pitches[best_earlier_i : best_earlier_i + best_earlier_len])
                if pattern_key not in self.pattern_cache:
                    self.pattern_cache[pattern_key] = list(
                        out_frets[best_earlier_i : best_earlier_i + best_earlier_len]
                    )
                self._clamp_following_jump(sorted_notes, out_frets, j + best_earlier_target_len)
                j += best_earlier_target_len
                continue

            # 3. If no earlier occurrence or cached pattern, check if it repeats later (i > j)
            best_later_len = 0
            later_cand_set: set[int] = set()
            for delta in (0, -1, 1, -2, 2, -12, 12):
                later_cand_set.update(pitch_positions.get(pitches[j] + delta, ()))
            if j + 1 < n_notes:
                for delta in (0, -1, 1):
                    for cand in pitch_positions.get(pitches[j + 1] + delta, ()):
                        if cand > 0:
                            later_cand_set.add(cand - 1)

            later_candidate_indices = sorted(idx for idx in later_cand_set if idx - j >= min_len)

            for i in later_candidate_indices:
                limit_i = get_max_phrase_len(i)
                max_l = min(n_notes - i, i - j, limit_j, limit_i)
                if max_l < min_len:
                    continue

                # Fast prefix filter
                d0 = abs(pitches[j] - pitches[i])
                if d0 > 2 and d0 != 12:
                    if j + 1 < n_notes and (abs(pitches[j + 1] - pitches[i]) <= 2 or abs(pitches[j + 1] - pitches[i]) == 12):
                        pass
                    elif i + 1 < n_notes and (abs(pitches[j] - pitches[i + 1]) <= 2 or abs(pitches[j] - pitches[i + 1]) == 12):
                        pass
                    else:
                        continue

                # Fast exact match probe
                exact_l = 0
                while exact_l < max_l and pitches[j + exact_l] == pitches[i + exact_l]:
                    exact_l += 1
                if exact_l >= min_len and exact_l > best_later_len:
                    best_later_len = exact_l

                # Fast scan to estimate plausible match length
                scan_l = 0
                mismatches = 0
                max_probe = min(max_l, 24)
                while scan_l < max_probe and mismatches <= 2:
                    d = abs(pitches[j + scan_l] - pitches[i + scan_l])
                    if d > 2 and d != 12:
                        mismatches += 1
                    scan_l += 1
                plausible_l = scan_l if mismatches <= 2 else scan_l - 1
                if plausible_l < min_len or plausible_l <= best_later_len:
                    continue

                candidate_test_lengths = {plausible_l}
                if plausible_l - 1 >= min_len:
                    candidate_test_lengths.add(plausible_l - 1)
                if plausible_l + 1 <= max_probe:
                    candidate_test_lengths.add(plausible_l + 1)

                for test_l in sorted(candidate_test_lengths, reverse=True):
                    if test_l <= best_later_len:
                        break
                    for target_l in (test_l, test_l + 1, test_l - 1):
                        if target_l < min_len or i + target_l > n_notes or target_l > limit_i:
                            continue
                        p_sub_j = pitches[j : j + test_l]
                        p_sub_i = pitches[i : i + target_l]
                        sim, _ = self._compute_phrase_similarity(p_sub_j, p_sub_i)
                        if sim >= self.motif_similarity_threshold:
                            best_later_len = test_l
                            break
                    if best_later_len == test_l:
                        break

            if best_later_len >= min_len:
                pattern_key = tuple(pitches[j : j + best_later_len])
                if pattern_key not in self.pattern_cache:
                    self.pattern_cache[pattern_key] = list(out_frets[j : j + best_later_len])

            j += 1

        return out_frets

    # Convenience aliases
    map = map_notes
    map_pitch_to_frets = map_notes
