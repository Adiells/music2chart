"""Unit tests for dataset feature extraction and chart alignment evaluation."""

import pytest

from dataset.evaluate_mapping import evaluate_chart_alignment
from dataset.feature_extractor import chart_notes_to_timed_events, compute_fret_mask
from src.models import BPMChange, ChartNote, FretType, TempoMap


@pytest.fixture
def standard_tempo_map() -> TempoMap:
    """120 BPM tempo map (each tick = 2.604ms at 192 PPQ)."""
    return TempoMap(
        resolution=192,
        bpm_changes=[BPMChange(tick=0, bpm=120.0)],
    )


def test_compute_fret_mask() -> None:
    """Validate bitmask calculation for distinct frets."""
    mask = compute_fret_mask({0, 2, 4})  # Green(1), Yellow(4), Orange(16) -> 21
    assert mask == (1 << 0) | (1 << 2) | (1 << 4)
    assert mask == 21


def test_chart_notes_to_timed_events_grouping(standard_tempo_map: TempoMap) -> None:
    """Validate grouping of multiple notes at the same tick into chords."""
    notes = [
        ChartNote(tick=0, fret=FretType.GREEN),
        ChartNote(tick=192, fret=FretType.RED),
        ChartNote(tick=192, fret=FretType.BLUE),
        ChartNote(tick=192, fret=FretType.HOPO_FORCE),  # Modifier should be ignored
    ]
    events = chart_notes_to_timed_events(notes, standard_tempo_map)

    assert len(events) == 2
    assert events[0].tick == 0
    assert not events[0].is_chord
    assert events[0].frets == frozenset({0})

    assert events[1].tick == 192
    assert events[1].is_chord
    assert events[1].frets == frozenset({1, 3})


def test_perfect_prediction(standard_tempo_map: TempoMap) -> None:
    """Simulate identical predicted and ground-truth notes (F1 = 1.0)."""
    gt_notes = [
        ChartNote(tick=0, fret=FretType.GREEN),
        ChartNote(tick=192, fret=FretType.RED),
        ChartNote(tick=384, fret=FretType.GREEN),
        ChartNote(tick=384, fret=FretType.YELLOW),
        ChartNote(tick=576, fret=FretType.ORANGE),
    ]
    pred_notes = list(gt_notes)

    metrics = evaluate_chart_alignment(pred_notes, gt_notes, standard_tempo_map)

    assert metrics["onset_precision"] == 1.0
    assert metrics["onset_recall"] == 1.0
    assert metrics["onset_f1"] == 1.0
    assert metrics["fret_accuracy"] == 1.0
    assert metrics["chord_agreement"] == 1.0
    assert metrics["matched_count"] == 4.0  # 4 distinct onset timestamps


def test_prediction_timing_tolerances(standard_tempo_map: TempoMap) -> None:
    """Test timing tolerance boundaries (+/- 30ms)."""
    gt_notes = [ChartNote(tick=192, fret=FretType.RED)]

    # At 120 BPM and 192 PPQ, 1 tick = ~2.604ms
    # 5 ticks shift = 13.02ms (< 30ms -> within tolerance)
    close_notes = [ChartNote(tick=197, fret=FretType.RED)]
    close_metrics = evaluate_chart_alignment(close_notes, gt_notes, standard_tempo_map)
    assert close_metrics["onset_f1"] == 1.0
    assert close_metrics["fret_accuracy"] == 1.0

    # 30 ticks shift = 78.12ms (> 30ms -> outside tolerance)
    far_notes = [ChartNote(tick=222, fret=FretType.RED)]
    far_metrics = evaluate_chart_alignment(far_notes, gt_notes, standard_tempo_map)
    assert far_metrics["onset_f1"] == 0.0
    assert far_metrics["matched_count"] == 0.0


def test_inverted_frets_prediction(standard_tempo_map: TempoMap) -> None:
    """Simulate onsets matched perfectly in time but with inverted/wrong frets."""
    gt_notes = [
        ChartNote(tick=0, fret=FretType.GREEN),
        ChartNote(tick=192, fret=FretType.RED),
    ]
    # Inverted frets: Green -> Orange, Red -> Blue
    pred_notes = [
        ChartNote(tick=0, fret=FretType.ORANGE),
        ChartNote(tick=192, fret=FretType.BLUE),
    ]

    metrics = evaluate_chart_alignment(pred_notes, gt_notes, standard_tempo_map)

    assert metrics["onset_f1"] == 1.0
    assert metrics["fret_accuracy"] == 0.0
    assert metrics["chord_agreement"] == 0.0


def test_partial_chord_agreement(standard_tempo_map: TempoMap) -> None:
    """Simulate partial chord match and verify Jaccard similarity."""
    # GT is 3-note chord: Green, Red, Yellow (frets 0, 1, 2)
    gt_notes = [
        ChartNote(tick=100, fret=FretType.GREEN),
        ChartNote(tick=100, fret=FretType.RED),
        ChartNote(tick=100, fret=FretType.YELLOW),
    ]
    # Pred is 2-note chord: Green, Red (frets 0, 1)
    pred_notes = [
        ChartNote(tick=100, fret=FretType.GREEN),
        ChartNote(tick=100, fret=FretType.RED),
    ]

    metrics = evaluate_chart_alignment(pred_notes, gt_notes, standard_tempo_map)

    assert metrics["onset_f1"] == 1.0
    assert metrics["fret_accuracy"] == 0.0  # Not exact match
    # Jaccard: intersection({0, 1}) / union({0, 1, 2}) = 2 / 3
    assert metrics["chord_agreement"] == pytest.approx(2 / 3)


def test_empty_notes_evaluation(standard_tempo_map: TempoMap) -> None:
    """Test empty note lists edge case."""
    metrics = evaluate_chart_alignment([], [], standard_tempo_map)
    assert metrics["onset_f1"] == 0.0
    assert metrics["fret_accuracy"] == 0.0
    assert metrics["chord_agreement"] == 0.0
