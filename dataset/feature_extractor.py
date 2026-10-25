"""Feature extraction and time-alignment between synthesized predictions and ground-truth charts."""

import bisect
from collections import defaultdict
from dataclasses import dataclass

from src.models import ChartNote, TempoMap


@dataclass(frozen=True)
class TimedFretEvent:
    """Consolidated musical onset at a specific point in time."""

    timestamp_seconds: float
    tick: int
    frets: frozenset[int]
    fret_mask: int
    is_chord: bool


def compute_fret_mask(frets: frozenset[int] | set[int]) -> int:
    """Calculate integer bitmask for active fret indices."""
    mask = 0
    for f in frets:
        mask |= 1 << f
    return mask


def chart_notes_to_timed_events(
    notes: list[ChartNote],
    tempo_map: TempoMap,
) -> list[TimedFretEvent]:
    """Group simultaneous notes at identical ticks into consolidated TimedFretEvents."""
    if not notes:
        return []

    # Group notes by tick
    tick_groups: dict[int, list[ChartNote]] = defaultdict(list)
    for note in notes:
        # Exclude modifier notes (HOPO force = 5, Strum force = 6) from pitch scoring
        if note.fret.value in (5, 6):
            continue
        tick_groups[note.tick].append(note)

    events: list[TimedFretEvent] = []
    for tick in sorted(tick_groups.keys()):
        group = tick_groups[tick]
        fret_set = frozenset(n.fret.value for n in group)
        timestamp = tempo_map.tick_to_seconds(tick)
        mask = compute_fret_mask(fret_set)
        is_chord = len(fret_set) > 1

        events.append(
            TimedFretEvent(
                timestamp_seconds=timestamp,
                tick=tick,
                frets=fret_set,
                fret_mask=mask,
                is_chord=is_chord,
            )
        )

    return events


def match_event_indices(
    predicted_events: list[TimedFretEvent],
    ground_truth_events: list[TimedFretEvent],
    tolerance_seconds: float = 0.030,
) -> list[tuple[int, int]]:
    """Greedily match events, returning ``(predicted_index, ground_truth_index)`` pairs.

    Each ground-truth event is used at most once. Among candidates inside the
    tolerance window the nearest one wins.
    """
    if not predicted_events or not ground_truth_events:
        return []

    # Index ground-truth onsets by time so each lookup only scans the tolerance window.
    gt_order = sorted(
        range(len(ground_truth_events)),
        key=lambda idx: (ground_truth_events[idx].timestamp_seconds, idx),
    )
    gt_times = [ground_truth_events[idx].timestamp_seconds for idx in gt_order]

    matched_pairs: list[tuple[int, int]] = []
    matched_gt_indices: set[int] = set()

    for pred_idx, pred in enumerate(predicted_events):
        window_start = bisect.bisect_left(gt_times, pred.timestamp_seconds - tolerance_seconds)
        window_end = bisect.bisect_right(gt_times, pred.timestamp_seconds + tolerance_seconds)

        best_gt_idx: int | None = None
        best_diff = float("inf")

        for position in range(window_start, window_end):
            gt_idx = gt_order[position]
            if gt_idx in matched_gt_indices:
                continue

            diff = abs(pred.timestamp_seconds - ground_truth_events[gt_idx].timestamp_seconds)
            if diff <= tolerance_seconds and diff < best_diff:
                best_diff = diff
                best_gt_idx = gt_idx

        if best_gt_idx is not None:
            matched_gt_indices.add(best_gt_idx)
            matched_pairs.append((pred_idx, best_gt_idx))

    return matched_pairs


def match_events(
    predicted_events: list[TimedFretEvent],
    ground_truth_events: list[TimedFretEvent],
    tolerance_seconds: float = 0.030,
) -> list[tuple[TimedFretEvent, TimedFretEvent]]:
    """Greedily match predicted events to nearest ground-truth events within time tolerance."""
    return [
        (predicted_events[pred_idx], ground_truth_events[gt_idx])
        for pred_idx, gt_idx in match_event_indices(
            predicted_events, ground_truth_events, tolerance_seconds=tolerance_seconds
        )
    ]
