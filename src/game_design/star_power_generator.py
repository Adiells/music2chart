"""Periodic Star Power phrase allocation engine for Clone Hero charts."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Final

from src.models import ChartNote, StarPowerPhrase


class StarPowerGenerator:
    """Generates periodic Star Power phrases throughout active song passages."""

    DEFAULT_MEASURE_TICKS: Final[int] = 768  # 4 * 192 PPQ
    DEFAULT_INTERVAL_MEASURES: Final[int] = 16  # One phrase roughly every 16 measures
    DEFAULT_PHRASE_LENGTH_MEASURES: Final[int] = 2  # Phrases span 2 measures
    DEFAULT_MIN_NOTES: Final[int] = 4  # Minimum notes required within a phrase

    def __init__(
        self,
        measure_ticks: int | None = None,
        interval_measures: int | None = None,
        phrase_length_measures: int | None = None,
        min_notes: int = DEFAULT_MIN_NOTES,
        ticks_per_measure: int | None = None,
        phrase_interval_measures: int | None = None,
        phrase_duration_measures: int | None = None,
    ) -> None:
        """Initialize StarPowerGenerator.

        Args:
            measure_ticks: Ticks in one measure (default 768 for 4/4 at 192 PPQ).
            interval_measures: Frequency of star power phrase allocation in measures (default 16).
            phrase_length_measures: Length of phrase in measures (default 2).
            min_notes: Minimum notes required within a phrase (default 4).
            ticks_per_measure: Alias for measure_ticks.
            phrase_interval_measures: Alias for interval_measures.
            phrase_duration_measures: Alias for phrase_length_measures.

        Raises:
            ValueError: If any parameter is <= 0.
        """
        m_ticks = (
            measure_ticks
            if measure_ticks is not None
            else (
                ticks_per_measure if ticks_per_measure is not None else self.DEFAULT_MEASURE_TICKS
            )
        )
        int_measures = (
            interval_measures
            if interval_measures is not None
            else (
                phrase_interval_measures
                if phrase_interval_measures is not None
                else self.DEFAULT_INTERVAL_MEASURES
            )
        )
        dur_measures = (
            phrase_length_measures
            if phrase_length_measures is not None
            else (
                phrase_duration_measures
                if phrase_duration_measures is not None
                else self.DEFAULT_PHRASE_LENGTH_MEASURES
            )
        )

        if m_ticks <= 0:
            raise ValueError(f"measure_ticks must be positive, got {m_ticks}")
        if int_measures <= 0:
            raise ValueError(f"interval_measures must be positive, got {int_measures}")
        if dur_measures <= 0:
            raise ValueError(f"phrase_length_measures must be positive, got {dur_measures}")
        if min_notes <= 0:
            raise ValueError(f"min_notes must be positive, got {min_notes}")

        self.measure_ticks = m_ticks
        self.ticks_per_measure = m_ticks
        self.interval_measures = int_measures
        self.phrase_interval_measures = int_measures
        self.phrase_length_measures = dur_measures
        self.phrase_duration_measures = dur_measures
        self.min_notes = min_notes

    def generate(self, notes: Sequence[ChartNote]) -> list[StarPowerPhrase]:
        """Generate periodic StarPowerPhrase allocations over active note passages.

        Args:
            notes: Sequence of ChartNotes.

        Returns:
            List of StarPowerPhrase instances sorted by tick.
        """
        if not notes or len(notes) < self.min_notes:
            return []

        sorted_notes = sorted(notes)
        first_tick = sorted_notes[0].tick
        last_tick = sorted_notes[-1].tick

        interval_ticks = self.interval_measures * self.measure_ticks
        duration_ticks = self.phrase_length_measures * self.measure_ticks

        phrases: list[StarPowerPhrase] = []
        current_tick = first_tick

        while current_tick <= last_tick:
            # Find closest note at or after current_tick
            candidate_notes = [n for n in sorted_notes if n.tick >= current_tick]
            if not candidate_notes:
                break

            phrase_start = candidate_notes[0].tick

            # Encompass notes in [phrase_start, phrase_start + duration_ticks)
            notes_in_phrase = [
                n for n in sorted_notes if phrase_start <= n.tick < (phrase_start + duration_ticks)
            ]

            if len(notes_in_phrase) >= self.min_notes:
                phrases.append(StarPowerPhrase(tick=phrase_start, length=duration_ticks))
                current_tick = phrase_start + duration_ticks + interval_ticks
            else:
                # Advance by one measure to search for denser section
                current_tick = phrase_start + self.measure_ticks

        return phrases

    # Aliases
    generate_phrases = generate
    generate_star_power = generate
    __call__ = generate
