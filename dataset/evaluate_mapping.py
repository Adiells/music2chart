"""Evaluation metrics comparing algorithmic note predictions against ground-truth human charts."""

from dataset.feature_extractor import chart_notes_to_timed_events, match_events
from src.models import ChartNote, TempoMap


def evaluate_chart_alignment(
    predicted_notes: list[ChartNote],
    ground_truth_notes: list[ChartNote],
    tempo_map: TempoMap,
    tolerance_seconds: float = 0.030,
) -> dict[str, float]:
    """Compute Onset Precision/Recall/F1, Fret Accuracy, and Chord Agreement against ground truth."""
    pred_events = chart_notes_to_timed_events(predicted_notes, tempo_map)
    gt_events = chart_notes_to_timed_events(ground_truth_notes, tempo_map)

    matches = match_events(pred_events, gt_events, tolerance_seconds=tolerance_seconds)

    true_positives = len(matches)
    total_pred = len(pred_events)
    total_gt = len(gt_events)

    precision = true_positives / total_pred if total_pred > 0 else 0.0
    recall = true_positives / total_gt if total_gt > 0 else 0.0
    if precision + recall > 0.0:
        f1_score = 2.0 * (precision * recall) / (precision + recall)
    else:
        f1_score = 0.0

    if matches:
        # Fret Accuracy: fraction of matched events with identical fret assignments
        exact_fret_matches = sum(1 for p, g in matches if p.frets == g.frets)
        fret_accuracy = exact_fret_matches / len(matches)

        # Chord Agreement: average Jaccard similarity between fret sets
        jaccard_scores = [
            len(p.frets & g.frets) / len(p.frets | g.frets) if (p.frets | g.frets) else 1.0
            for p, g in matches
        ]
        chord_agreement = sum(jaccard_scores) / len(matches)
    else:
        fret_accuracy = 0.0
        chord_agreement = 0.0

    return {
        "onset_precision": precision,
        "onset_recall": recall,
        "onset_f1": f1_score,
        "fret_accuracy": fret_accuracy,
        "chord_agreement": chord_agreement,
        "matched_count": float(true_positives),
        "total_ground_truth": float(total_gt),
        "total_predicted": float(total_pred),
    }
