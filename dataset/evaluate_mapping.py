"""Evaluation metrics comparing algorithmic note predictions against ground-truth human charts."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace

from dataset.feature_extractor import (
    TimedFretEvent,
    chart_notes_to_timed_events,
    match_event_indices,
)
from src.models import ChartNote, TempoMap

#: Shortest repeating fret sequence considered a "motif" (mirrors
#: ``PitchToFretMapper.min_pattern_len``).
DEFAULT_MOTIF_MIN_NOTES: int = 3

#: Longest repeating fret sequence considered a single motif. Longer windows are
#: preferred so that a long riff is not fragmented into many overlapping 3-grams.
DEFAULT_MOTIF_MAX_NOTES: int = 6


@dataclass(frozen=True)
class MotifOccurrence:
    """One appearance of a repeating ground-truth phrase.

    ``predicted`` holds the predicted fret tuple aligned to each ground-truth event,
    or ``None`` when the predicted onset was not matched inside the time tolerance.

    ``similarity`` measures agreement with the predicted anchor occurrence and drives
    the motif-lock decision. ``gt_similarity`` measures agreement with the human-written
    sequence and feeds :func:`motif_consistency_score`, so a chart cannot score well by
    being consistently wrong.
    """

    gt_indices: tuple[int, ...]
    predicted: tuple[tuple[int, ...] | None, ...]
    similarity: float
    gt_similarity: float


@dataclass(frozen=True)
class MotifGroup:
    """A ground-truth fret sequence that occurs at least twice in the chart."""

    signature: tuple[tuple[int, ...], ...]
    occurrences: tuple[MotifOccurrence, ...]


PredictionAlignment = list[tuple[int, ...] | None]


def shift_events(
    events: list[TimedFretEvent],
    offset_seconds: float,
) -> list[TimedFretEvent]:
    """Return events shifted in time by ``offset_seconds`` (positive = later)."""
    if offset_seconds == 0.0:
        return events
    return [
        replace(event, timestamp_seconds=event.timestamp_seconds + offset_seconds)
        for event in events
    ]


def align_predictions_to_gt(
    ground_truth_events: list[TimedFretEvent],
    predicted_events: list[TimedFretEvent],
    tolerance_seconds: float = 0.030,
) -> PredictionAlignment:
    """Map each ground-truth event index to the aligned predicted fret tuple."""
    alignment: PredictionAlignment = [None] * len(ground_truth_events)
    for pred_idx, gt_idx in match_event_indices(
        predicted_events, ground_truth_events, tolerance_seconds=tolerance_seconds
    ):
        alignment[gt_idx] = tuple(sorted(predicted_events[pred_idx].frets))
    return alignment


def _event_token(event: TimedFretEvent) -> tuple[int, ...]:
    """Fret signature used to compare phrases."""
    return tuple(sorted(event.frets))


def _sequence_similarity(
    sequence: tuple[tuple[int, ...] | None, ...],
    reference: tuple[tuple[int, ...] | None, ...],
) -> float:
    """Position-wise agreement between two predicted fret sequences in [0, 1]."""
    if not sequence:
        return 0.0
    agreements = sum(
        1
        for predicted, expected in zip(sequence, reference, strict=False)
        if predicted is not None and predicted == expected
    )
    return agreements / len(sequence)


def find_repeated_motifs(
    ground_truth_events: list[TimedFretEvent],
    prediction_alignment: Sequence[tuple[int, ...] | None],
    min_notes: int = DEFAULT_MOTIF_MIN_NOTES,
    max_notes: int = DEFAULT_MOTIF_MAX_NOTES,
) -> list[MotifGroup]:
    """Detect fret sequences repeated in the ground truth and score their predictions.

    Detection walks window lengths from ``max_notes`` down to ``min_notes`` and greedily
    assigns non-overlapping occurrences, so a six-note riff is reported as one motif
    instead of four overlapping three-note motifs. Constant sequences (e.g. ``[R, R, R]``)
    are ignored because they do not constrain the fret mapping.
    """
    total_events = len(ground_truth_events)
    if total_events < min_notes * 2:
        return []

    tokens = [_event_token(event) for event in ground_truth_events]
    claimed: set[int] = set()
    groups: list[MotifGroup] = []

    for length in range(max_notes, min_notes - 1, -1):
        if total_events < length * 2:
            continue

        buckets: dict[tuple[tuple[int, ...], ...], list[int]] = {}
        for start in range(total_events - length + 1):
            signature = tuple(tokens[start : start + length])
            if len(set(signature)) == 1:
                continue
            buckets.setdefault(signature, []).append(start)

        candidates: list[tuple[tuple[tuple[int, ...], ...], list[int]]] = []
        for signature, starts in buckets.items():
            if len(starts) < 2:
                continue
            occurrences: list[int] = []
            last_end = -1
            for start in starts:
                if start > last_end:
                    occurrences.append(start)
                    last_end = start + length - 1
            if len(occurrences) >= 2:
                candidates.append((signature, occurrences))

        # Most repeated / earliest motifs claim their spans first.
        candidates.sort(key=lambda item: (-len(item[1]), item[1][0]))

        for signature, starts in candidates:
            spans = {index for start in starts for index in range(start, start + length)}
            if spans & claimed:
                continue
            claimed |= spans

            predicted_sequences = tuple(
                tuple(prediction_alignment[index] for index in range(start, start + length))
                for start in starts
            )
            # The mapper anchors a repeated motif to its first occurrence (pattern cache),
            # so lock similarity is measured against that canonical predicted sequence.
            reference = predicted_sequences[0]

            motif_occurrences = tuple(
                MotifOccurrence(
                    gt_indices=tuple(range(start, start + length)),
                    predicted=sequence,
                    similarity=_sequence_similarity(sequence, reference),
                    gt_similarity=_sequence_similarity(sequence, signature),
                )
                for start, sequence in zip(starts, predicted_sequences, strict=True)
            )
            groups.append(MotifGroup(signature=signature, occurrences=motif_occurrences))

    return groups


def motif_consistency_score(groups: list[MotifGroup]) -> float:
    """Weighted mean agreement between predicted and human fret sequences on repeated riffs.

    The weight of a group is ``occurrences * motif length`` so long, frequently
    repeated riffs dominate. Similarity is measured against the ground-truth signature:
    a chart that repeats the *same wrong* frets must not be rewarded. Returns ``0.0``
    when no repeated motif exists, since there is no consistency evidence.
    """
    total_weight = 0
    accumulated = 0.0
    for group in groups:
        weight = len(group.occurrences) * len(group.signature)
        if weight <= 0:
            continue
        total_weight += weight
        accumulated += sum(occurrence.gt_similarity for occurrence in group.occurrences) * len(
            group.signature
        )
    return accumulated / total_weight if total_weight > 0 else 0.0


def evaluate_timed_events(
    predicted_events: list[TimedFretEvent],
    ground_truth_events: list[TimedFretEvent],
    tolerance_seconds: float = 0.030,
) -> dict[str, float]:
    """Compute alignment metrics directly from timed fret events.

    This is the event-level counterpart of :func:`evaluate_chart_alignment`, used by
    the calibration tool after shifting / repairing predictions.
    """
    matches = match_event_indices(
        predicted_events, ground_truth_events, tolerance_seconds=tolerance_seconds
    )

    true_positives = len(matches)
    total_pred = len(predicted_events)
    total_gt = len(ground_truth_events)

    precision = true_positives / total_pred if total_pred > 0 else 0.0
    recall = true_positives / total_gt if total_gt > 0 else 0.0
    f1_score = 2.0 * (precision * recall) / (precision + recall) if precision + recall else 0.0

    if matches:
        exact_fret_matches = sum(
            1
            for pred_idx, gt_idx in matches
            if predicted_events[pred_idx].frets == ground_truth_events[gt_idx].frets
        )
        fret_accuracy = exact_fret_matches / len(matches)

        jaccard_scores = [
            (
                len(predicted_events[pred_idx].frets & ground_truth_events[gt_idx].frets)
                / len(predicted_events[pred_idx].frets | ground_truth_events[gt_idx].frets)
                if (predicted_events[pred_idx].frets | ground_truth_events[gt_idx].frets)
                else 1.0
            )
            for pred_idx, gt_idx in matches
        ]
        chord_agreement = sum(jaccard_scores) / len(matches)
    else:
        fret_accuracy = 0.0
        chord_agreement = 0.0

    alignment: PredictionAlignment = [None] * total_gt
    for pred_idx, gt_idx in matches:
        alignment[gt_idx] = tuple(sorted(predicted_events[pred_idx].frets))

    groups = find_repeated_motifs(ground_truth_events, alignment)
    riff_consistency = motif_consistency_score(groups)

    return {
        "onset_precision": precision,
        "onset_recall": recall,
        "onset_f1": f1_score,
        "fret_accuracy": fret_accuracy,
        "chord_agreement": chord_agreement,
        "riff_consistency_score": riff_consistency,
        "matched_count": float(true_positives),
        "total_ground_truth": float(total_gt),
        "total_predicted": float(total_pred),
        "motif_group_count": float(len(groups)),
        "motif_occurrence_count": float(sum(len(g.occurrences) for g in groups)),
    }


def evaluate_chart_alignment(
    predicted_notes: list[ChartNote],
    ground_truth_notes: list[ChartNote],
    tempo_map: TempoMap,
    tolerance_seconds: float = 0.030,
    *,
    pred_tempo_map: TempoMap | None = None,
    gt_tempo_map: TempoMap | None = None,
    offset_seconds: float = 0.0,
) -> dict[str, float]:
    """Compute onset precision/recall/F1, fret accuracy, chord agreement and motif consistency.

    Args:
        predicted_notes: Algorithmically generated notes (ticks in ``pred_tempo_map``).
        ground_truth_notes: Human-authored reference notes (ticks in ``gt_tempo_map``).
        tempo_map: Fallback tempo map used when specific maps are omitted.
        tolerance_seconds: Onset matching tolerance in seconds.
        pred_tempo_map: Tempo map of the predicted chart. Allows comparing charts with
            different PPQ resolutions (e.g. 192 vs 480 ticks per beat).
        gt_tempo_map: Tempo map of the ground truth. Defaults to ``pred_tempo_map``
            (or ``tempo_map`` when that is also omitted).
        offset_seconds: Constant time shift added to every predicted onset before
            matching. Used to compensate authoring latency / lead-in silence.

    Returns:
        Metric dictionary. In addition to the alignment scores it exposes
        ``riff_consistency_score``: the weighted agreement of predicted fret
        sequences across phrases that repeat in the ground truth.
    """
    prediction_map = pred_tempo_map or tempo_map
    reference_map = gt_tempo_map or prediction_map

    pred_events = chart_notes_to_timed_events(predicted_notes, prediction_map)
    gt_events = chart_notes_to_timed_events(ground_truth_notes, reference_map)
    pred_events = shift_events(pred_events, offset_seconds)

    metrics = evaluate_timed_events(
        pred_events, gt_events, tolerance_seconds=tolerance_seconds
    )
    metrics["offset_seconds"] = float(offset_seconds)
    return metrics
