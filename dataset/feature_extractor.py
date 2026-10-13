"""Feature extraction and time-alignment between synthesized predictions and ground-truth charts."""

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


def match_events(
    predicted_events: list[TimedFretEvent],
    ground_truth_events: list[TimedFretEvent],
    tolerance_seconds: float = 0.030,
) -> list[tuple[TimedFretEvent, TimedFretEvent]]:
    """Greedily match predicted events to nearest ground-truth events within time tolerance."""
    if not predicted_events or not ground_truth_events:
        return []

    matched_pairs: list[tuple[TimedFretEvent, TimedFretEvent]] = []
    matched_gt_indices: set[int] = set()

    for pred in predicted_events:
        best_gt_idx: int | None = None
        best_diff = float("inf")

        for idx, gt in enumerate(ground_truth_events):
            if idx in matched_gt_indices:
                continue

            diff = abs(pred.timestamp_seconds - gt.timestamp_seconds)
            if diff <= tolerance_seconds and diff < best_diff:
                best_diff = diff
                best_gt_idx = idx

        if best_gt_idx is not None:
            matched_gt_indices.add(best_gt_idx)
            matched_pairs.append((pred, ground_truth_events[best_gt_idx]))

    return matched_pairs
