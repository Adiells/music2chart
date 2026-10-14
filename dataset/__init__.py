"""Dataset utilities, scrapers, and evaluators for music2chart."""

from dataset.chart_parser import ChartParser
from dataset.chorus_scraper import ChorusScraper
from dataset.evaluate_mapping import evaluate_chart_alignment
from dataset.feature_extractor import (
    TimedFretEvent,
    chart_notes_to_timed_events,
    compute_fret_mask,
    match_events,
)

__all__ = [
    "ChorusScraper",
    "ChartParser",
    "evaluate_chart_alignment",
    "chart_notes_to_timed_events",
    "compute_fret_mask",
    "match_events",
    "TimedFretEvent",
]
