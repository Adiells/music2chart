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
    DEFAULT_RUN_THRESHOLD: Final[int] = 96  # 1/8 note run threshold for explicit HOPO force

    def __init__(
        self,
        hopo_threshold: int = DEFAULT_HOPO_THRESHOLD,
        run_threshold: int = DEFAULT_RUN_THRESHOLD,
    ) -> None:
        """Initialize HopoEngine.

        Args:
            hopo_threshold: Maximum delta tick spacing for natural HOPO (default 65).
            run_threshold: Maximum delta tick spacing for melodic run HOPO forcing (default 96).

        Raises:
            ValueError: If hopo_threshold < 0 or run_threshold < 0.
        """
        if hopo_threshold < 0:
            raise ValueError(f"hopo_threshold must be non-negative, got {hopo_threshold}")
        if run_threshold < 0:
            raise ValueError(f"run_threshold must be non-negative, got {run_threshold}")
        self.hopo_threshold = hopo_threshold
        self.run_threshold = run_threshold

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
        """Add explicit HOPO_FORCE (5) or STRUM_FORCE (6) modifier notes where helpful.

        Detects melodic single-note runs with inter-note distance <= run_threshold (96 ticks)
        and fret variation:
        - Note 1 of the run is a Strum anchor (is_hopo=False, no modifier).
        - Notes 2..N in the run receive an explicit HOPO_FORCE modifier note (tick=note.tick,
          fret=FretType.HOPO_FORCE, sustain_length=0).
        - Repeated consecutive frets within the rapid window receive an explicit STRUM_FORCE
          modifier note (tick=note.tick, fret=FretType.STRUM_FORCE, sustain_length=0).
        - Chords default to Strum and break melodic single-note runs.
        """
        if not notes:
            return []

        sorted_notes = sorted(notes)
        tick_groups: dict[int, list[ChartNote]] = defaultdict(list)
        for note in sorted_notes:
            if note.fret not in (FretType.HOPO_FORCE, FretType.STRUM_FORCE):
                tick_groups[note.tick].append(note)

        sorted_ticks = sorted(tick_groups.keys())
        output: list[ChartNote] = []

        prev_tick: int | None = None
        prev_fret: FretType | None = None

        for tick in sorted_ticks:
            group = tick_groups[tick]
            is_single_note = len(group) == 1

            if is_single_note:
                note = group[0]
                if prev_tick is not None and prev_fret is not None:
                    delta = tick - prev_tick
                    if delta <= self.run_threshold:
                        if note.fret != prev_fret:
                            # Melodic run note 2..N: emit note and HOPO_FORCE modifier
                            output.append(
                                ChartNote(
                                    tick=tick,
                                    fret=note.fret,
                                    sustain_length=note.sustain_length,
                                    is_hopo=True,
                                )
                            )
                            output.append(
                                ChartNote(
                                    tick=tick,
                                    fret=FretType.HOPO_FORCE,
                                    sustain_length=0,
                                )
                            )
                            prev_tick = tick
                            prev_fret = note.fret
                            continue
                        else:
                            # Repeated consecutive fret in rapid window: emit note and STRUM_FORCE modifier
                            output.append(
                                ChartNote(
                                    tick=tick,
                                    fret=note.fret,
                                    sustain_length=note.sustain_length,
                                    is_hopo=False,
                                )
                            )
                            output.append(
                                ChartNote(
                                    tick=tick,
                                    fret=FretType.STRUM_FORCE,
                                    sustain_length=0,
                                )
                            )
                            prev_tick = tick
                            prev_fret = note.fret
                            continue

                # First note of run or gap > run_threshold: Strum anchor
                output.append(
                    ChartNote(
                        tick=tick,
                        fret=note.fret,
                        sustain_length=note.sustain_length,
                        is_hopo=False,
                    )
                )
                prev_tick = tick
                prev_fret = note.fret
            else:
                # Chord: strummed, breaks melodic single-note run
                for note in group:
                    output.append(
                        ChartNote(
                            tick=tick,
                            fret=note.fret,
                            sustain_length=note.sustain_length,
                            is_hopo=False,
                        )
                    )
                prev_tick = tick
                prev_fret = None

        output.sort()
        return output

    # Aliases
    calculate_hopos = process
    process_hopos = process
    __call__ = process
