"""Dataset utilities, scrapers, and evaluators for music2chart."""

from dataset.chart_parser import ChartParser
from dataset.chorus_scraper import ChorusScraper
from dataset.evaluate_mapping import (
    evaluate_chart_alignment,
    evaluate_timed_events,
    find_repeated_motifs,
    shift_events,
)
from dataset.feature_extractor import (
    TimedFretEvent,
    chart_notes_to_timed_events,
    compute_fret_mask,
    match_event_indices,
    match_events,
)
from dataset.midi_parser import MidiChartParser, RawMidiNote

__all__ = [
    "ChorusScraper",
    "ChartParser",
    "MidiChartParser",
    "RawMidiNote",
    "evaluate_chart_alignment",
    "evaluate_timed_events",
    "find_repeated_motifs",
    "shift_events",
    "chart_notes_to_timed_events",
    "compute_fret_mask",
    "match_event_indices",
    "match_events",
    "TimedFretEvent",
]
