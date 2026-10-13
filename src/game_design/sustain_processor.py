"""Sustain calculation engine enforcing threshold and release margins for Clone Hero."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Final

from src.models import ChartNote

MIN_SUSTAIN_TICKS: Final[int] = (
    90  # Notes shorter than 90 ticks (~less than an eighth note) are strum-only
)
RELEASE_MARGIN_TICKS: Final[int] = (
    24  # 24-tick gap left before next note to prevent overlapping tails
)


class SustainProcessor:
    """Calculates sustain lengths with release gap margins and truncation before subsequent notes."""

    DEFAULT_MIN_SUSTAIN: Final[int] = MIN_SUSTAIN_TICKS
    DEFAULT_RELEASE_MARGIN: Final[int] = RELEASE_MARGIN_TICKS

    def __init__(
        self,
        min_sustain_ticks: int = DEFAULT_MIN_SUSTAIN,
        release_margin: int | None = None,
        release_margin_ticks: int | None = None,
    ) -> None:
        """Initialize SustainProcessor.

        Args:
            min_sustain_ticks: Duration threshold below which sustain is 0 (default 90).
            release_margin: Margin in ticks subtracted before release/next note (default 24).
            release_margin_ticks: Alias for release_margin.

        Raises:
            ValueError: If min_sustain_ticks < 0 or release_margin < 0.
        """
        margin = (
            release_margin
            if release_margin is not None
            else (
                release_margin_ticks
                if release_margin_ticks is not None
                else self.DEFAULT_RELEASE_MARGIN
            )
        )
        if min_sustain_ticks < 0:
            raise ValueError(f"min_sustain_ticks must be non-negative, got {min_sustain_ticks}")
        if margin < 0:
            raise ValueError(f"release_margin must be non-negative, got {margin}")

        self.min_sustain_ticks = min_sustain_ticks
        self.release_margin = margin
        self.release_margin_ticks = margin

    def calculate_sustain_length(
        self,
        duration_ticks: int,
        next_note_distance: int | None = None,
    ) -> int:
        """Calculate final sustain ticks given raw duration and distance to subsequent note."""
        if duration_ticks < self.min_sustain_ticks:
            return 0

        # Base sustain: duration minus release margin
        sustain = duration_ticks - self.release_margin

        if next_note_distance is not None:
            max_allowed = max(0, next_note_distance - self.release_margin)
            sustain = min(sustain, max_allowed)

        return max(0, sustain)

    def process(
        self,
        notes: Sequence[ChartNote],
        durations: Sequence[int] | Mapping[tuple[int, int], int] | Mapping[int, int] | None = None,
    ) -> list[ChartNote]:
        """Process and clamp sustain lengths across all notes in chronological order.

        Args:
            notes: Sequence of ChartNotes.
            durations: Optional mapping or sequence of raw duration ticks. If None,
                uses note.sustain_length as the raw input duration.

        Returns:
            New list of ChartNotes sorted by (tick, fret) with sustain_length computed.
        """
        if not notes:
            return []

        # Associate raw duration with each note before sorting
        dur_dict = dict(durations.items()) if isinstance(durations, Mapping) else None
        paired: list[tuple[ChartNote, int]] = []
        for i, note in enumerate(notes):
            if durations is not None:
                if isinstance(durations, Sequence) and not isinstance(durations, (str, bytes)):
                    raw_dur = durations[i] if i < len(durations) else note.sustain_length
                elif dur_dict is not None:
                    fret_val = note.fret.value if hasattr(note.fret, "value") else int(note.fret)
                    raw_dur = dur_dict.get(
                        (note.tick, fret_val), dur_dict.get(note.tick, note.sustain_length)
                    )
                else:
                    raw_dur = note.sustain_length
            else:
                raw_dur = note.sustain_length
            paired.append((note, raw_dur))

        paired.sort(key=lambda item: item[0])

        unique_ticks = sorted({item[0].tick for item in paired})
        tick_to_next_dist: dict[int, int | None] = {}

        for i, tick in enumerate(unique_ticks):
            if i + 1 < len(unique_ticks):
                tick_to_next_dist[tick] = unique_ticks[i + 1] - tick
            else:
                tick_to_next_dist[tick] = None

        processed: list[ChartNote] = []
        for note, raw_dur in paired:
            next_dist = tick_to_next_dist.get(note.tick)
            final_sustain = self.calculate_sustain_length(raw_dur, next_dist)

            processed.append(
                ChartNote(
                    tick=note.tick,
                    fret=note.fret,
                    sustain_length=final_sustain,
                    is_hopo=note.is_hopo,
                )
            )

        return processed

    # Aliases
    calculate_sustains = process
    process_notes = process
    __call__ = process
