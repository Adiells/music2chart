"""Hammer-On and Pull-Off (HOPO) calculation engine for Clone Hero charts."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from typing import Final

from src.models import ChartNote, FretType

HOPO_TICK_THRESHOLD: Final[int] = (
    65  # Community standard threshold (1/16 note at 192 PPQ is 48 ticks)
)


class HopoEngine:
    """Calculates HOPO states and strum enforcement based on Clone Hero rules."""

    DEFAULT_HOPO_THRESHOLD: Final[int] = HOPO_TICK_THRESHOLD

    def __init__(self, hopo_threshold: int = DEFAULT_HOPO_THRESHOLD) -> None:
        """Initialize HopoEngine.

        Args:
            hopo_threshold: Maximum delta tick spacing for natural HOPO (default 65).

        Raises:
            ValueError: If hopo_threshold < 0.
        """
        if hopo_threshold < 0:
            raise ValueError(f"hopo_threshold must be non-negative, got {hopo_threshold}")
        self.hopo_threshold = hopo_threshold

    def process(self, notes: Sequence[ChartNote]) -> list[ChartNote]:
        """Evaluate and assign is_hopo flags for all notes in chronological order.

        Args:
            notes: Sequence of ChartNotes.

        Returns:
            New list of ChartNotes sorted by (tick, fret) with is_hopo accurately set.
        """
        if not notes:
            return []

        # Sort notes by tick, then fret
        sorted_notes = sorted(notes)

        # Group notes by tick
        tick_groups: dict[int, list[ChartNote]] = defaultdict(list)
        for note in sorted_notes:
            # Skip modifier notes
            if note.fret in (FretType.HOPO_FORCE, FretType.STRUM_FORCE):
                continue
            tick_groups[note.tick].append(note)

        sorted_ticks = sorted(tick_groups.keys())
        processed_notes: list[ChartNote] = []

        prev_tick: int | None = None
        prev_frets: set[FretType] = set()

        for tick in sorted_ticks:
            current_group = tick_groups[tick]
            current_frets = {n.fret for n in current_group}
            is_chord = len(current_group) > 1

            for note in current_group:
                # Default to strum (first note, chords, or large gaps)
                is_hopo = False

                if prev_tick is not None and not is_chord:
                    distance = tick - prev_tick
                    if distance <= self.hopo_threshold:
                        # Must have fret variation from previous event
                        if note.fret not in prev_frets:
                            is_hopo = True
                        else:
                            # Repeated fret -> forced strum
                            is_hopo = False

                processed_notes.append(
                    ChartNote(
                        tick=note.tick,
                        fret=note.fret,
                        sustain_length=note.sustain_length,
                        is_hopo=is_hopo,
                    )
                )

            prev_tick = tick
            prev_frets = current_frets

        return processed_notes

    def add_force_modifiers(self, notes: Sequence[ChartNote]) -> list[ChartNote]:
        """Add explicit HOPO_FORCE (5) or STRUM_FORCE (6) modifier notes where helpful."""
        processed = self.process(notes)
        output: list[ChartNote] = []

        # Group by tick
        tick_groups: dict[int, list[ChartNote]] = defaultdict(list)
        for note in processed:
            tick_groups[note.tick].append(note)

        sorted_ticks = sorted(tick_groups.keys())
        prev_tick: int | None = None
        prev_frets: set[FretType] = set()

        for tick in sorted_ticks:
            group = tick_groups[tick]
            output.extend(group)

            # If a fast consecutive note on identical fret exists, emit STRUM_FORCE (6)
            if (
                prev_tick is not None
                and len(group) == 1
                and (tick - prev_tick) <= self.hopo_threshold
            ):
                if group[0].fret in prev_frets:
                    output.append(ChartNote(tick=tick, fret=FretType.STRUM_FORCE, sustain_length=0))

            prev_tick = tick
            prev_frets = {n.fret for n in group}

        output.sort()
        return output

    # Aliases
    calculate_hopos = process
    process_hopos = process
    __call__ = process
