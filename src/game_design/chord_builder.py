"""Ergonomic chord formation and playability constraint engine for Clone Hero charts."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from typing import Final

from src.models.chart import ChartNote, FretType

DEFAULT_MAX_FRETS: Final[int] = 2

CANONICAL_POWER_CHORDS: Final[frozenset[tuple[int, int]]] = frozenset(
    {
        (0, 1),  # Green + Red
        (0, 2),  # Green + Yellow
        (1, 2),  # Red + Yellow
        (1, 3),  # Red + Blue
        (2, 3),  # Yellow + Blue
        (2, 4),  # Yellow + Orange
        (3, 4),  # Blue + Orange
    }
)

CANONICAL_TRIADS: Final[frozenset[tuple[int, int, int]]] = frozenset(
    {
        (0, 1, 2),  # Green + Red + Yellow
        (0, 2, 3),  # Green + Yellow + Blue
        (1, 2, 3),  # Red + Yellow + Blue
        (2, 3, 4),  # Yellow + Blue + Orange
    }
)


class ChordBuilder:
    """Groups simultaneous notes into playable, ergonomic Clone Hero chords.

    Enforces physical playability constraints on 5-fret guitar controllers:
    - Default maximum 2 simultaneous frets (canonical power chords).
    - Permits 3-note triads only on accented beats with duration/sustain >= 96 ticks.
    - Strictly prohibits 4-fret and 5-fret chords.
    - Eliminates unplayable (0, 4) Green + Orange stretches via generalized dyad clamping.
    - Open Note exclusivity: fretted notes take precedence by default (open_note_precedence=False).
    - Fast-run single-note collapsing: chords in passages with spacing <= 48 ticks collapse to root note.
    - Deterministic sorting by (tick, fret) ascending.
    """

    DEFAULT_MAX_FRETS: Final[int] = DEFAULT_MAX_FRETS
    CANONICAL_POWER_CHORDS: Final[frozenset[tuple[int, int]]] = CANONICAL_POWER_CHORDS
    CANONICAL_TRIADS: Final[frozenset[tuple[int, int, int]]] = CANONICAL_TRIADS

    def __init__(
        self,
        max_frets: int = DEFAULT_MAX_FRETS,
        allow_wide_triads: bool = False,
        open_note_precedence: bool = False,
        prefer_open: bool | None = None,
        collapse_fast_runs: bool = True,
        fast_run_tick_threshold: int = 48,
        allow_triads_on_accents: bool = True,
        min_triad_sustain_ticks: int = 96,
        accent_tick_interval: int = 96,
    ) -> None:
        """Initialize ChordBuilder.

        Args:
            max_frets: Maximum simultaneous frets allowed in a chord (range 1-5, default 2).
            allow_wide_triads: If True, permits (0, 2, 4) Green-Yellow-Orange tri-color triads.
                If False, simplifies (0, 2, 4) to canonical triad (0, 2, 3).
            open_note_precedence: If True, Open notes take precedence over concurrent fretted notes.
                If False (default), fretted notes take precedence over concurrent Open notes.
            prefer_open: Compatibility alias for open_note_precedence.
            collapse_fast_runs: If True (default), collapses chords in fast runs (spacing <= threshold)
                into the single dominant root note.
            fast_run_tick_threshold: Maximum tick distance to qualify as a fast run (default 48 ticks / 1/16 note).
            allow_triads_on_accents: If True (default), permits 3-note canonical triads on accented beats
                with duration/sustain >= min_triad_sustain_ticks.
            min_triad_sustain_ticks: Minimum sustain ticks required for a 3-note triad (default 96 ticks / 1/8 note).
            accent_tick_interval: Subdivision interval for accented beats (default 96 ticks / 1/8 note).

        Raises:
            ValueError: If max_frets is not between 1 and 5.
        """
        if not (1 <= max_frets <= 5):
            raise ValueError(f"max_frets must be between 1 and 5, got {max_frets}")
        self.max_frets = max_frets
        self.allow_wide_triads = allow_wide_triads
        if prefer_open is not None:
            self.open_note_precedence = prefer_open
        else:
            self.open_note_precedence = open_note_precedence
        self.prefer_open = self.open_note_precedence
        self.collapse_fast_runs = collapse_fast_runs
        self.fast_run_tick_threshold = fast_run_tick_threshold
        self.allow_triads_on_accents = allow_triads_on_accents
        self.min_triad_sustain_ticks = min_triad_sustain_ticks
        self.accent_tick_interval = accent_tick_interval

    def _clamp_dyad(self, frets: list[int]) -> list[int]:
        """Apply generalized dyad clamping to 2-note chords.

        If the span between high and low exceeds 2 frets, high is clamped to low + 2.
        This eliminates (0, 4) -> (0, 2), (0, 3) -> (0, 2), and (1, 4) -> (1, 3).
        All 7 canonical power chords have span <= 2 and pass through unchanged.
        """
        low, high = frets[0], frets[1]
        if high - low > 2:
            return [low, low + 2]
        return frets

    def _clamp_triad(self, frets: list[int]) -> list[int]:
        """Apply triad stretch clamping to 3-note chords.

        Eliminates unplayable stretches containing both Green (0) and Orange (4):
        - (0, 1, 4) -> (0, 1, 2)
        - (0, 3, 4) -> (2, 3, 4)
        - (0, 2, 4) -> (0, 2, 4) if allow_wide_triads is True, else (0, 2, 3).
        Preserves canonical triads and root-anchors other shapes.
        """
        if frets[0] == 0 and frets[2] == 4:
            if frets[1] == 2:
                if self.allow_wide_triads:
                    return frets
                return [0, 2, 3]
            elif frets[1] == 1:
                return [0, 1, 2]
            elif frets[1] == 3:
                return [2, 3, 4]

        if tuple(frets) in CANONICAL_TRIADS:
            return frets

        if frets == [0, 1, 3]:
            return [0, 1, 2]
        if frets == [1, 2, 4]:
            return [1, 2, 3]

        return frets

    def _simplify_polyphonic(self, frets: list[int]) -> list[int]:
        """Simplify 4-note or 5-note polyphonic clusters to canonical triads."""
        tup = tuple(frets)
        if tup == (0, 1, 2, 3, 4):
            return [0, 1, 2]
        if tup == (0, 1, 2, 3):
            return [0, 1, 2]
        if tup == (0, 1, 2, 4):
            return [0, 1, 2]
        if tup == (0, 1, 3, 4):
            return [0, 1, 2]
        if tup == (0, 2, 3, 4):
            return [0, 2, 3]
        if tup == (1, 2, 3, 4):
            return [1, 2, 3]

        return frets[:3]

    def _reduce_cluster(self, frets: list[int], max_f: int | None = None) -> list[int]:
        """Reduce a sorted list of unique frets (0-4) according to game design rules."""
        limit = self.max_frets if max_f is None else max_f
        # 4-fret and 5-fret chords are strictly prohibited
        limit = min(limit, 3)

        k = len(frets)
        if k <= 1:
            return frets

        if k >= 4:
            simplified = self._simplify_polyphonic(frets)
        elif k == 3:
            simplified = self._clamp_triad(frets)
        else:
            simplified = self._clamp_dyad(frets)

        if len(simplified) > limit:
            if limit == 1:
                return [simplified[0]]
            if limit == 2 and len(simplified) == 3:
                low = simplified[0]
                if simplified[1] - low <= 2:
                    return [low, simplified[1]]
                return [low, min(low + 2, 4)]

        return simplified

    def build_chords(self, notes: Sequence[ChartNote]) -> list[ChartNote]:
        """Group simultaneous notes into playable, ergonomic Clone Hero chords.

        Args:
            notes: Chronological or unsorted sequence of ChartNotes.

        Returns:
            List of ChartNotes grouped into chords conforming to Clone Hero constraints,
            sorted ascending by (tick, fret).
        """
        if not notes:
            return []

        tick_map: dict[int, list[ChartNote]] = defaultdict(list)
        for note in notes:
            tick_map[note.tick].append(note)

        sorted_ticks = sorted(tick_map.keys())
        num_ticks = len(sorted_ticks)
        result: list[ChartNote] = []

        for i, tick in enumerate(sorted_ticks):
            chord_notes = tick_map[tick]

            open_notes = [n for n in chord_notes if n.fret == FretType.OPEN]
            fretted_notes = [n for n in chord_notes if 0 <= n.fret.value <= 4]
            modifier_notes = [n for n in chord_notes if n.fret.value in (5, 6)]

            # Always preserve modifier notes if any exist
            result.extend(modifier_notes)

            # Open Note Exclusivity Check
            if open_notes and fretted_notes:
                if self.open_note_precedence:
                    max_sustain = max(n.sustain_length for n in chord_notes)
                    is_hopo = any(n.is_hopo for n in chord_notes)
                    result.append(
                        ChartNote(
                            tick=tick,
                            fret=FretType.OPEN,
                            sustain_length=max_sustain,
                            is_hopo=is_hopo,
                        )
                    )
                    continue
                # If fretted notes take precedence, drop Open notes and continue to fretted processing
            elif open_notes and not fretted_notes:
                max_sustain = max(n.sustain_length for n in open_notes)
                is_hopo = any(n.is_hopo for n in open_notes)
                result.append(
                    ChartNote(
                        tick=tick,
                        fret=FretType.OPEN,
                        sustain_length=max_sustain,
                        is_hopo=is_hopo,
                    )
                )
                continue

            if not fretted_notes:
                continue

            # Deduplicate by fret value, aggregating max sustain and any is_hopo
            sustain_by_fret: dict[int, int] = {}
            hopo_by_fret: dict[int, bool] = {}
            for n in fretted_notes:
                fv = int(n.fret.value)
                sustain_by_fret[fv] = max(sustain_by_fret.get(fv, 0), n.sustain_length)
                hopo_by_fret[fv] = hopo_by_fret.get(fv, False) or n.is_hopo

            unique_frets = sorted(sustain_by_fret.keys())

            if len(unique_frets) == 1:
                f = unique_frets[0]
                result.append(
                    ChartNote(
                        tick=tick,
                        fret=FretType(f),
                        sustain_length=sustain_by_fret[f],
                        is_hopo=hopo_by_fret[f],
                    )
                )
                continue

            # Fast-run single-note collapsing:
            # During fast passages where inter-note spacing to previous or next note is <= fast_run_tick_threshold (<= 48 ticks),
            # chords are strictly prohibited. Simultaneous notes are collapsed to the single dominant root note.
            is_fast_run = False
            if self.collapse_fast_runs and num_ticks > 1:
                delta_prev = (tick - sorted_ticks[i - 1]) if i > 0 else float("inf")
                delta_next = (sorted_ticks[i + 1] - tick) if i < num_ticks - 1 else float("inf")
                if min(delta_prev, delta_next) <= self.fast_run_tick_threshold:
                    is_fast_run = True

            if is_fast_run:
                # Collapse to single dominant root note (lowest fret)
                root_fret = unique_frets[0]
                cluster_max_sustain = max(sustain_by_fret.values())
                cluster_any_hopo = any(hopo_by_fret.values())
                result.append(
                    ChartNote(
                        tick=tick,
                        fret=FretType(root_fret),
                        sustain_length=max(sustain_by_fret[root_fret], cluster_max_sustain),
                        is_hopo=hopo_by_fret[root_fret] or cluster_any_hopo,
                    )
                )
                continue

            cluster_max_sustain = max(sustain_by_fret.values())
            cluster_any_hopo = any(hopo_by_fret.values())

            # Determine effective maximum frets for this chord:
            # Default max_frets is 2 (canonical power chords).
            # Permit 3-note triads only on accented beats with duration / sustain length >= 96 ticks.
            if self.max_frets == 1:
                effective_max = 1
            elif self.max_frets == 2:
                is_accented = tick % self.accent_tick_interval == 0
                is_sustained = cluster_max_sustain >= self.min_triad_sustain_ticks
                if self.allow_triads_on_accents and is_accented and is_sustained:
                    effective_max = 3
                else:
                    effective_max = 2
            else:
                # max_frets >= 3: clamped strictly to at most 3
                effective_max = min(self.max_frets, 3)

            chosen_frets = self._reduce_cluster(unique_frets, max_f=effective_max)

            for f in chosen_frets:
                sustain = sustain_by_fret.get(f, cluster_max_sustain)
                hopo = hopo_by_fret.get(f, cluster_any_hopo)
                result.append(
                    ChartNote(
                        tick=tick,
                        fret=FretType(f),
                        sustain_length=sustain,
                        is_hopo=hopo,
                    )
                )

        result.sort()
        return result

    build = build_chords
    process = build_chords

    def __call__(self, notes: Sequence[ChartNote]) -> list[ChartNote]:
        """Callable alias for build_chords."""
        return self.build_chords(notes)
