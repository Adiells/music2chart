"""Motif-similarity threshold calibration against a ground-truth chart.

The calibration sweep answers a single question: *which motif-similarity threshold
produces the most human-like fret sequences?*  For every candidate threshold the tool
simulates what :class:`src.game_design.pitch_to_fret.PitchToFretMapper` does when a
repeating riff is recognised (motif lock):

* phrases whose predicted fret sequences already agree with the canonical (first)
  occurrence (similarity >= threshold) are accepted and normalised to it;
* phrases below the threshold are left untouched (no lock).

The effective chart is then scored against the ground truth with
:func:`dataset.evaluate_mapping.evaluate_timed_events`:

* ``fret_accuracy``           -- exact fret matches over aligned onsets;
* ``riff_consistency_score``  -- agreement of predicted sequences with the human
  sequence on riffs that repeat in the ground truth;
* ``composite_score``         -- ``0.70 * riff_consistency + 0.30 * fret_accuracy``.

A lower threshold locks more aggressively (higher consistency, but it may force the
anchor's pattern onto every repetition), while a higher threshold locks less. The
composite curve therefore exposes the best trade-off instead of trivially favouring
the lowest threshold.

Usage::

    python -m dataset.calibrate_motif_threshold --gt notes.mid --pred tmp/output/notes.chart
    python -m dataset.calibrate_motif_threshold --gt notes.mid --pred pred.chart --apply

When ``--pred`` is omitted the ground truth is evaluated against itself (sanity run).
That run cannot produce a meaningful optimum for ``--apply``; the flag is therefore
rejected unless ``--allow-self-calibration`` is passed explicitly.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Sequence
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

from dataset.chart_parser import ChartParser
from dataset.evaluate_mapping import (
    MotifGroup,
    align_predictions_to_gt,
    evaluate_timed_events,
    find_repeated_motifs,
    shift_events,
)
from dataset.feature_extractor import (
    TimedFretEvent,
    chart_notes_to_timed_events,
    compute_fret_mask,
    match_event_indices,
)
from dataset.midi_parser import INSTRUMENT_SUFFIX, MidiChartParser
from src.models import ChartNote, TempoMap

#: Candidate thresholds, coarse enough to finish quickly on full-length charts.
THRESHOLD_GRID: Final[tuple[float, ...]] = (
    0.50,
    0.55,
    0.60,
    0.65,
    0.70,
    0.75,
    0.80,
    0.85,
    0.90,
    0.95,
)

#: Threshold currently hard-coded across the project.
DEFAULT_THRESHOLD: Final[float] = 0.75

#: Weights of the composite objective. Riff consistency dominates because the metric
#: targets motif locking, while fret accuracy guards against degenerate locks.
COMPOSITE_WEIGHTS: Final[dict[str, float]] = {
    "riff_consistency_score": 0.70,
    "fret_accuracy": 0.30,
}

PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[1]

#: Files whose ``motif_similarity_threshold`` default is rewritten by ``--apply``.
TARGET_FILES: Final[tuple[str, ...]] = (
    "src/game_design/pitch_to_fret.py",
    "src/pipeline.py",
    "src/api/schemas.py",
)


@dataclass(frozen=True)
class ThresholdResult:
    """Metrics obtained for one candidate motif-similarity threshold."""

    threshold: float
    fret_accuracy: float
    riff_consistency_score: float
    composite_score: float
    onset_precision: float
    onset_recall: float
    onset_f1: float
    chord_agreement: float
    locked_occurrences: int
    total_occurrences: int
    matched_count: int


def score_offset(
    pred_events: list[TimedFretEvent],
    gt_events: list[TimedFretEvent],
    offset_seconds: float,
    tolerance_seconds: float = 0.030,
) -> int:
    """Count chronologically matchable onsets after shifting predictions by an offset."""
    if not pred_events or not gt_events:
        return 0

    pred_times = sorted(event.timestamp_seconds + offset_seconds for event in pred_events)
    gt_times = sorted(event.timestamp_seconds for event in gt_events)

    gt_cursor = 0
    matches = 0
    for pred_time in pred_times:
        while gt_cursor < len(gt_times) and gt_times[gt_cursor] < pred_time - tolerance_seconds:
            gt_cursor += 1
        if gt_cursor >= len(gt_times):
            break
        if gt_times[gt_cursor] <= pred_time + tolerance_seconds:
            matches += 1
            gt_cursor += 1
    return matches


def find_optimal_offset(
    pred_events: list[TimedFretEvent],
    gt_events: list[TimedFretEvent],
    search_range: tuple[float, float] = (-1.0, 5.0),
    step: float = 0.01,
    tolerance_seconds: float = 0.030,
) -> float:
    """Find the constant shift (seconds) that aligns predictions with the ground truth.

    Rock Band MIDIs keep two lead-in measures before ``[music_start]``; depending on
    the source of the prediction (audio onset vs. authored chart) the whole chart can
    be displaced by several seconds. Shifting predictions by the returned offset
    compensates that latency. Ties are broken in favour of the smallest absolute shift.
    """
    if step <= 0:
        raise ValueError(f"step must be positive, got {step}")
    lower, upper = search_range
    if upper < lower:
        raise ValueError(f"search_range must be ascending, got {search_range}")

    if not pred_events or not gt_events:
        return 0.0

    steps = int(round((upper - lower) / step))
    best_offset = 0.0
    best_score = -1
    best_distance = float("inf")

    for index in range(steps + 1):
        offset = round(lower + index * step, 6)
        score = score_offset(pred_events, gt_events, offset, tolerance_seconds)
        distance = abs(offset)
        if score > best_score or (score == best_score and distance < best_distance):
            best_offset = offset
            best_score = score
            best_distance = distance

    return best_offset


def _anchor_sequence(
    sequences: Sequence[tuple[tuple[int, ...] | None, ...]],
) -> tuple[tuple[int, ...] | None, ...]:
    """Return the canonical sequence: the first occurrence of the motif."""
    return sequences[0] if sequences else ()


def apply_motif_lock(
    pred_events: list[TimedFretEvent],
    gt_events: list[TimedFretEvent],
    groups: list[MotifGroup],
    threshold: float,
    tolerance_seconds: float = 0.030,
) -> tuple[list[TimedFretEvent], int, int]:
    """Normalise motif occurrences whose internal similarity reaches ``threshold``.

    Returns the repaired prediction list plus ``(locked_occurrences, total_occurrences)``.
    """
    pred_by_gt = {
        gt_idx: pred_idx
        for pred_idx, gt_idx in match_event_indices(
            pred_events, gt_events, tolerance_seconds=tolerance_seconds
        )
    }

    repairs: dict[int, tuple[int, ...]] = {}
    locked = 0
    total = 0

    for group in groups:
        sequences = [occurrence.predicted for occurrence in group.occurrences]
        reference = _anchor_sequence(sequences)
        for occurrence in group.occurrences:
            total += 1
            if occurrence.similarity < threshold:
                continue
            locked += 1
            for position, gt_idx in enumerate(occurrence.gt_indices):
                pred_idx = pred_by_gt.get(gt_idx)
                target = reference[position] if position < len(reference) else None
                if pred_idx is None or target is None:
                    continue
                repairs[pred_idx] = target

    if not repairs:
        return pred_events, locked, total

    repaired = list(pred_events)
    for pred_idx, frets in repairs.items():
        event = repaired[pred_idx]
        repaired[pred_idx] = replace(
            event,
            frets=frozenset(frets),
            fret_mask=compute_fret_mask(set(frets)),
            is_chord=len(frets) > 1,
        )
    return repaired, locked, total


def _composite(fret_accuracy: float, riff_consistency: float) -> float:
    return (
        COMPOSITE_WEIGHTS["riff_consistency_score"] * riff_consistency
        + COMPOSITE_WEIGHTS["fret_accuracy"] * fret_accuracy
    )


def sweep_thresholds(
    gt_events: list[TimedFretEvent],
    pred_events: list[TimedFretEvent],
    thresholds: Sequence[float] = THRESHOLD_GRID,
    tolerance_seconds: float = 0.030,
) -> list[ThresholdResult]:
    """Evaluate every candidate threshold on already offset-aligned predictions."""
    original_alignment = align_predictions_to_gt(
        gt_events, pred_events, tolerance_seconds=tolerance_seconds
    )
    groups = find_repeated_motifs(gt_events, original_alignment)
    # Consistency of the unmodified predictions is threshold independent, but the
    # effective metric is recomputed after each simulated lock.
    results: list[ThresholdResult] = []

    for threshold in thresholds:
        if not 0.0 <= threshold <= 1.0:
            raise ValueError(f"threshold must be in [0.0, 1.0], got {threshold}")

        effective_events, locked, total = apply_motif_lock(
            pred_events, gt_events, groups, threshold, tolerance_seconds
        )
        metrics = evaluate_timed_events(
            effective_events, gt_events, tolerance_seconds=tolerance_seconds
        )
        results.append(
            ThresholdResult(
                threshold=float(threshold),
                fret_accuracy=metrics["fret_accuracy"],
                riff_consistency_score=metrics["riff_consistency_score"],
                composite_score=_composite(
                    metrics["fret_accuracy"], metrics["riff_consistency_score"]
                ),
                onset_precision=metrics["onset_precision"],
                onset_recall=metrics["onset_recall"],
                onset_f1=metrics["onset_f1"],
                chord_agreement=metrics["chord_agreement"],
                locked_occurrences=locked,
                total_occurrences=total,
                matched_count=int(metrics["matched_count"]),
            )
        )

    return results


def select_optimal_threshold(
    results: Sequence[ThresholdResult],
    preference: float = DEFAULT_THRESHOLD,
) -> ThresholdResult:
    """Pick the best composite score, preferring values near ``preference`` on ties."""
    if not results:
        raise ValueError("results must not be empty")
    return max(
        results,
        key=lambda result: (result.composite_score, -abs(result.threshold - preference), -result.threshold),
    )


def load_notes(
    path: Path,
    instrument: str = "guitar",
    difficulty: str = "Expert",
) -> tuple[TempoMap, list[ChartNote], Path]:
    """Load notes and the matching tempo map from a ``.chart`` or ``.mid`` file."""
    suffix = path.suffix.lower()
    track_suffix = INSTRUMENT_SUFFIX.get(instrument.lower())
    if track_suffix is None:
        valid = ", ".join(sorted(INSTRUMENT_SUFFIX))
        raise ValueError(f"Unknown instrument '{instrument}'. Valid values: {valid}")

    if suffix in {".mid", ".midi"}:
        tempo_map, tracks, _ = MidiChartParser().parse_file(path)
    elif suffix in {".chart", ".txt"}:
        tempo_map, tracks, _ = ChartParser().parse_file(path)
    else:
        raise ValueError(f"Unsupported chart format '{path.suffix}' (expected .chart or .mid)")

    track_name = f"{difficulty}{track_suffix}"
    track = tracks.get(track_name)
    if track is None:
        available = ", ".join(sorted(tracks)) or "<none>"
        raise KeyError(
            f"Track '{track_name}' not found in {path}; available tracks: {available}"
        )
    # ``ChartNote.tick`` values stay in the file's native resolution (192 or 480 PPQ);
    # the returned tempo map guarantees the correct tick -> seconds conversion.
    return tempo_map, track.notes, path


def _format_threshold(value: float) -> str:
    return f"{value:.2f}"


def apply_threshold_to_defaults(
    new_threshold: float,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, int]:
    """Rewrite the hard-coded motif threshold in the project sources.

    Args:
        new_threshold: Threshold to write, in [0.0, 1.0].
        project_root: Repository root used to resolve the target files.

    Returns:
        Mapping of relative file path -> number of substitutions.

    Raises:
        ValueError: If the threshold is out of range.
    """
    if not 0.0 <= new_threshold <= 1.0:
        raise ValueError(f"threshold must be in [0.0, 1.0], got {new_threshold}")

    value = _format_threshold(new_threshold)
    patterns: dict[str, list[tuple[re.Pattern[str], str]]] = {
        "src/game_design/pitch_to_fret.py": [
            (
                re.compile(
                    r"(DEFAULT_MOTIF_SIMILARITY_THRESHOLD:\s*Final\[float\]\s*=\s*)\d+\.\d+"
                ),
                rf"\g<1>{value}",
            ),
            (
                re.compile(
                    r"(in \[0\.0, 1\.0\] \(default )\d+\.\d+(\) for matching repeating motifs)"
                ),
                rf"\g<1>{value}\g<2>",
            ),
        ],
        "src/pipeline.py": [
            (
                re.compile(r"(\bmotif_similarity_threshold=)\d+\.\d+\b"),
                rf"\g<1>{value}",
            ),
            (
                re.compile(r"(\"motif_similarity_threshold\",\s*)\d+\.\d+\b"),
                rf"\g<1>{value}",
            ),
            (
                re.compile(r"(\(0\.5 to 1\.0, default )\d+\.\d+"),
                rf"\g<1>{value}",
            ),
        ],
        "src/api/schemas.py": [
            (
                re.compile(r"(\"motif_similarity_threshold\":\s*)\d+\.\d+\b"),
                rf"\g<1>{value}",
            ),
            (
                re.compile(
                    r"(motif_similarity_threshold: float = Field\(\s*\n\s*default=)\d+\.\d+\b"
                ),
                rf"\g<1>{value}",
            ),
            (
                re.compile(
                    r"(motif alignment similarity threshold \(0\.5 to 1\.0, default )\d+\.\d+"
                ),
                rf"\g<1>{value}",
            ),
        ],
    }

    applied: dict[str, int] = {}
    for relative_path, substitutions in patterns.items():
        target = project_root / relative_path
        if not target.is_file():
            applied[relative_path] = 0
            continue
        content = target.read_text(encoding="utf-8")
        updated = content
        total = 0
        for pattern, replacement in substitutions:
            updated, count = pattern.subn(replacement, updated)
            total += count
        if total > 0:
            target.write_text(updated, encoding="utf-8")
        applied[relative_path] = total

    return applied


def format_report_table(results: Sequence[ThresholdResult]) -> str:
    """Render the sweep as a fixed-width console table."""
    header = (
        f"{'Threshold':>9} | {'Fret Acc':>8} | {'Riff Cons':>9} | "
        f"{'Composite':>9} | {'Onset F1':>8} | {'Locked':>10}"
    )
    separator = "-" * len(header)
    lines = [header, separator]
    for result in results:
        lines.append(
            f"{result.threshold:>9.2f} | {result.fret_accuracy:>8.4f} | "
            f"{result.riff_consistency_score:>9.4f} | {result.composite_score:>9.4f} | "
            f"{result.onset_f1:>8.4f} | "
            f"{result.locked_occurrences:>4}/{result.total_occurrences:<5}"
        )
    return "\n".join(lines)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="calibrate_motif_threshold",
        description=(
            "Sweep motif_similarity_threshold values against a ground-truth chart and "
            "optionally update the project defaults."
        ),
    )
    parser.add_argument("--gt", "--midi", dest="gt", required=True, type=Path, help="Ground-truth .mid or .chart")
    parser.add_argument(
        "--pred",
        "--audio-chart",
        dest="pred",
        type=Path,
        default=None,
        help="Predicted .mid or .chart (defaults to the ground truth for a sanity run)",
    )
    parser.add_argument(
        "--instrument",
        default="guitar",
        choices=sorted({"guitar", "bass", "rhythm", "keys"}),
        help="Instrument track to compare (default: guitar)",
    )
    parser.add_argument(
        "--difficulty",
        default="Expert",
        choices=("Easy", "Medium", "Hard", "Expert"),
        help="Difficulty track to compare (default: Expert)",
    )
    parser.add_argument(
        "--offset",
        type=float,
        default=None,
        help="Use a fixed time shift instead of searching the optimal offset",
    )
    parser.add_argument(
        "--search-min", type=float, default=-1.0, help="Offset search lower bound (s)"
    )
    parser.add_argument(
        "--search-max", type=float, default=5.0, help="Offset search upper bound (s)"
    )
    parser.add_argument("--step", type=float, default=0.01, help="Offset search step (s)")
    parser.add_argument(
        "--tolerance",
        type=float,
        default=0.030,
        help="Onset matching tolerance in seconds (default: 0.030)",
    )
    parser.add_argument(
        "--thresholds",
        default=",".join(_format_threshold(value) for value in THRESHOLD_GRID),
        help="Comma separated threshold grid",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=PROJECT_ROOT / "tmp" / "calibration_report.json",
        help="JSON report destination (default: tmp/calibration_report.json)",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=PROJECT_ROOT,
        help="Repository root used by --apply",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write the optimal threshold into the project defaults when it differs from 0.75",
    )
    parser.add_argument(
        "--allow-self-calibration",
        action="store_true",
        help="Allow --apply when --pred is omitted (prediction equals ground truth)",
    )
    return parser


def _parse_thresholds(raw: str) -> list[float]:
    values = []
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            values.append(float(chunk))
        except ValueError as exc:
            raise SystemExit(f"Invalid threshold value '{chunk}'") from exc
    if not values:
        raise SystemExit("At least one threshold is required")
    return values


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point. Returns a process exit code."""
    try:
        return _run(argv)
    except (FileNotFoundError, KeyError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


def _run(argv: Sequence[str] | None = None) -> int:
    """Execute the calibration workflow, raising on invalid inputs."""
    args = _build_parser().parse_args(argv)
    project_root = Path(args.project_root).resolve()

    gt_path = Path(args.gt).resolve()
    gt_tempo_map, gt_notes, _ = load_notes(gt_path, args.instrument, args.difficulty)
    gt_events = chart_notes_to_timed_events(gt_notes, gt_tempo_map)

    self_calibration = args.pred is None
    pred_path = gt_path if self_calibration else Path(args.pred).resolve()
    pred_tempo_map, pred_notes, _ = load_notes(pred_path, args.instrument, args.difficulty)
    pred_events = chart_notes_to_timed_events(pred_notes, pred_tempo_map)

    if args.offset is not None:
        optimal_offset = float(args.offset)
    else:
        optimal_offset = find_optimal_offset(
            pred_events,
            gt_events,
            search_range=(args.search_min, args.search_max),
            step=args.step,
            tolerance_seconds=args.tolerance,
        )
    aligned_events = shift_events(pred_events, optimal_offset)

    thresholds = _parse_thresholds(args.thresholds)
    results = sweep_thresholds(
        gt_events, aligned_events, thresholds=thresholds, tolerance_seconds=args.tolerance
    )
    best = select_optimal_threshold(results)

    print(f"Ground truth : {gt_path} ({len(gt_events)} onsets, {gt_tempo_map.resolution} PPQ)")
    print(f"Prediction   : {pred_path} ({len(pred_events)} onsets, {pred_tempo_map.resolution} PPQ)")
    if self_calibration:
        print("Note         : prediction equals ground truth (sanity run)")
    print(f"Offset       : {optimal_offset:+.3f}s ({score_offset(pred_events, gt_events, optimal_offset, args.tolerance)} matched onsets)")
    print()
    print(format_report_table(results))
    print()
    print(
        f"Optimal threshold: {_format_threshold(best.threshold)} "
        f"(composite {best.composite_score:.4f}, "
        f"weights riff={COMPOSITE_WEIGHTS['riff_consistency_score']:.2f} "
        f"fret={COMPOSITE_WEIGHTS['fret_accuracy']:.2f})"
    )

    changed = abs(best.threshold - DEFAULT_THRESHOLD) > 1e-9
    applied_files: dict[str, int] = {}
    apply_skipped_reason: str | None = None

    if args.apply:
        if not changed:
            print(f"Default already at {_format_threshold(DEFAULT_THRESHOLD)}; no source changes.")
        elif self_calibration and not args.allow_self_calibration:
            apply_skipped_reason = "self-calibration requires --allow-self-calibration"
            print(
                "Refusing --apply: predictions equal the ground truth. "
                "Pass --pred <chart> or --allow-self-calibration."
            )
        else:
            applied_files = apply_threshold_to_defaults(best.threshold, project_root)
            for relative_path, count in applied_files.items():
                print(f"Updated {relative_path}: {count} occurrence(s)")
            if not any(applied_files.values()):
                apply_skipped_reason = "no matching defaults were found"
                print("Warning: no matching default declarations were rewritten.")

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "ground_truth": {
            "path": str(gt_path),
            "events": len(gt_events),
            "resolution": gt_tempo_map.resolution,
        },
        "prediction": {
            "path": str(pred_path),
            "events": len(pred_events),
            "resolution": pred_tempo_map.resolution,
            "is_ground_truth": self_calibration,
        },
        "offset_seconds": optimal_offset,
        "offset_search": {
            "range": [args.search_min, args.search_max],
            "step": args.step,
            "tolerance_seconds": args.tolerance,
            "matched_events": score_offset(
                pred_events, gt_events, optimal_offset, args.tolerance
            ),
        },
        "composite_weights": COMPOSITE_WEIGHTS,
        "thresholds": [asdict(result) for result in results],
        "optimal_threshold": best.threshold,
        "default_threshold": DEFAULT_THRESHOLD,
        "apply_requested": bool(args.apply),
        "applied_files": applied_files,
        "apply_skipped_reason": apply_skipped_reason,
    }

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Report written to {report_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
