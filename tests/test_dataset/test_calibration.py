"""Unit tests for motif threshold calibration and evaluation metrics."""

import json
from pathlib import Path

import pytest

from dataset.calibrate_motif_threshold import (
    DEFAULT_THRESHOLD,
    THRESHOLD_GRID,
    apply_motif_lock,
    apply_threshold_to_defaults,
    find_optimal_offset,
    main,
    score_offset,
    select_optimal_threshold,
    sweep_thresholds,
)
from dataset.evaluate_mapping import (
    DEFAULT_MOTIF_MIN_NOTES,
    MotifGroup,
    evaluate_chart_alignment,
    evaluate_timed_events,
    find_repeated_motifs,
    shift_events,
)
from dataset.feature_extractor import TimedFretEvent, compute_fret_mask
from src.models import BPMChange, ChartNote, FretType, TempoMap


def _event(timestamp: float, frets: tuple[int, ...] = (0,)) -> TimedFretEvent:
    fret_set = frozenset(frets)
    return TimedFretEvent(
        timestamp_seconds=timestamp,
        tick=int(round(timestamp * 1000)),
        frets=fret_set,
        fret_mask=compute_fret_mask(fret_set),
        is_chord=len(fret_set) > 1,
    )


def _repeated_riff_chart() -> list[TimedFretEvent]:
    """GT riff [0, 1, 2] written twice with a gap in between."""
    return [
        _event(0.0),
        _event(0.5, (1,)),
        _event(1.0, (2,)),
        _event(2.0),
        _event(2.5, (1,)),
        _event(3.0, (2,)),
    ]


def _prediction_with_divergent_repeat() -> list[TimedFretEvent]:
    """First riff is correct, second repeat deviates on its last note."""
    return [
        _event(0.0),
        _event(0.5, (1,)),
        _event(1.0, (2,)),
        _event(2.0),
        _event(2.5, (1,)),
        _event(3.0, (3,)),
    ]


# ---------------------------------------------------------------------------
# Offset detection
# ---------------------------------------------------------------------------


def test_find_optimal_offset_recovers_constant_latency() -> None:
    """A uniform -1.25s displacement must be compensated by +1.25s."""
    gt_events = [_event(t * 0.25) for t in range(12)]
    pred_events = shift_events(gt_events, -1.25)

    offset = find_optimal_offset(pred_events, gt_events, step=0.01)

    assert offset == pytest.approx(1.25, abs=0.05)
    assert score_offset(pred_events, gt_events, offset, tolerance_seconds=0.03) == 12


def test_find_optimal_offset_prefers_small_shift_on_ties() -> None:
    """With no predictions the offset is neutral; equal scores prefer near-zero shifts."""
    gt_events = [_event(10.0)]
    pred_events = [_event(10.0)]

    assert find_optimal_offset(pred_events, gt_events) == pytest.approx(0.0)
    assert find_optimal_offset([], gt_events) == 0.0


def test_find_optimal_offset_validates_step() -> None:
    """Non-positive steps are rejected."""
    with pytest.raises(ValueError, match="step must be positive"):
        find_optimal_offset([_event(0.0)], [_event(0.0)], step=0.0)


# ---------------------------------------------------------------------------
# Motif detection and consistency
# ---------------------------------------------------------------------------


def test_repeated_motif_detection_ignores_constant_sequences() -> None:
    """Constant fret runs do not constrain the mapping and must be skipped."""
    events = [_event(t * 0.25, (2,)) for t in range(12)]
    alignment = [tuple(event.frets) for event in events]

    assert find_repeated_motifs(events, alignment) == []


def test_riff_consistency_penalises_divergent_repeats() -> None:
    """The second occurrence must lower consistency against the anchored first one."""
    gt_events = _repeated_riff_chart()
    pred_events = _prediction_with_divergent_repeat()

    metrics = evaluate_timed_events(pred_events, gt_events)

    assert metrics["riff_consistency_score"] == pytest.approx((1.0 + 2 / 3) / 2)
    assert metrics["fret_accuracy"] == pytest.approx(5 / 6)


def test_motif_lock_repairs_occurrences_above_threshold() -> None:
    """Locking at 0.60 must normalise the divergent repeat to the anchored riff."""
    gt_events = _repeated_riff_chart()
    pred_events = _prediction_with_divergent_repeat()
    alignment = [tuple(pred_events[index].frets) for index in range(len(gt_events))]
    groups = find_repeated_motifs(gt_events, alignment)
    assert groups
    assert all(isinstance(group, MotifGroup) for group in groups)

    repaired, locked, total = apply_motif_lock(pred_events, gt_events, groups, threshold=0.60)

    assert (locked, total) == (2, 2)
    assert repaired[-1].frets == frozenset({2})
    assert repaired[-1].fret_mask == compute_fret_mask({2})

    untouched, locked_high, _ = apply_motif_lock(pred_events, gt_events, groups, threshold=0.90)
    assert locked_high == 1  # only the anchor occurrence matches itself
    assert untouched[-1].frets == frozenset({3})


# ---------------------------------------------------------------------------
# Threshold sweep
# ---------------------------------------------------------------------------


def test_sweep_thresholds_uses_requested_grid_and_composite() -> None:
    """Sweep returns every grid value and the documented composite weighting."""
    gt_events = _repeated_riff_chart()
    pred_events = _prediction_with_divergent_repeat()

    results = sweep_thresholds(gt_events, pred_events)

    assert [result.threshold for result in results] == list(THRESHOLD_GRID)
    for result in results:
        expected = 0.70 * result.riff_consistency_score + 0.30 * result.fret_accuracy
        assert result.composite_score == pytest.approx(expected)

    low, high = results[0], results[-1]
    assert low.locked_occurrences == 2
    assert high.locked_occurrences == 1
    assert low.riff_consistency_score > high.riff_consistency_score
    # 0.50-0.65 tie on composite (the divergent repeat scores 2/3); the tie-break
    # keeps the threshold closest to the current default (0.75).
    assert select_optimal_threshold(results).threshold == pytest.approx(0.65)


def test_select_optimal_prefers_default_on_ties() -> None:
    """Perfect, identical results should not move the default threshold."""
    gt_events = _repeated_riff_chart()
    results = sweep_thresholds(gt_events, gt_events)

    assert select_optimal_threshold(results).threshold == pytest.approx(DEFAULT_THRESHOLD)


# ---------------------------------------------------------------------------
# Evaluation enhancements
# ---------------------------------------------------------------------------


def test_evaluate_chart_alignment_applies_offset() -> None:
    """offset_seconds shifts predictions before onset matching."""
    tempo_map = TempoMap(resolution=192, bpm_changes=[BPMChange(tick=0, bpm=120.0)])
    gt_notes = [ChartNote(tick=0, fret=FretType.GREEN), ChartNote(tick=192, fret=FretType.RED)]
    # 192 ticks at 120 BPM / 192 PPQ = 0.5s; predict 1.0s late (384 ticks).
    pred_notes = [
        ChartNote(tick=384, fret=FretType.GREEN),
        ChartNote(tick=576, fret=FretType.RED),
    ]

    unshifted = evaluate_chart_alignment(pred_notes, gt_notes, tempo_map)
    shifted = evaluate_chart_alignment(pred_notes, gt_notes, tempo_map, offset_seconds=-1.0)

    assert unshifted["onset_f1"] == 0.0
    assert shifted["onset_f1"] == 1.0
    assert shifted["fret_accuracy"] == 1.0


def test_evaluate_chart_alignment_supports_different_resolutions() -> None:
    """The same musical notes in 192 and 480 PPQ must align when maps are provided."""
    low_res = TempoMap(resolution=192, bpm_changes=[BPMChange(tick=0, bpm=120.0)])
    high_res = TempoMap(resolution=480, bpm_changes=[BPMChange(tick=0, bpm=120.0)])

    pred_notes = [ChartNote(tick=0, fret=FretType.GREEN), ChartNote(tick=480, fret=FretType.RED)]
    gt_notes = [ChartNote(tick=0, fret=FretType.GREEN), ChartNote(tick=192, fret=FretType.RED)]

    metrics = evaluate_chart_alignment(
        pred_notes,
        gt_notes,
        low_res,
        pred_tempo_map=high_res,
        gt_tempo_map=low_res,
    )

    assert metrics["onset_f1"] == 1.0
    assert metrics["fret_accuracy"] == 1.0


def test_evaluate_chart_alignment_without_repeats_scores_zero_consistency() -> None:
    """Charts with no repeated motif have no consistency evidence."""
    tempo_map = TempoMap(resolution=192, bpm_changes=[BPMChange(tick=0, bpm=120.0)])
    notes = [
        ChartNote(tick=0, fret=FretType.GREEN),
        ChartNote(tick=96, fret=FretType.RED),
    ]

    metrics = evaluate_chart_alignment(notes, notes, tempo_map)

    assert metrics["riff_consistency_score"] == 0.0
    assert metrics["motif_group_count"] == 0.0
    assert metrics["fret_accuracy"] == 1.0


# ---------------------------------------------------------------------------
# --apply source rewriting
# ---------------------------------------------------------------------------


def _create_fake_project(root: Path) -> None:
    files = {
        "src/game_design/pitch_to_fret.py": (
            "DEFAULT_MOTIF_SIMILARITY_THRESHOLD: Final[float] = 0.75  # x\n"
            "            creativity: factor in [0.0, 1.0] (default 0.5).\n"
            "            motif_similarity_threshold: Minimum fuzzy threshold\n"
            "                in [0.0, 1.0] (default 0.75) for matching repeating motifs.\n"
        ),
        "src/pipeline.py": (
            "motif_similarity_threshold=0.75,\n"
            'preset_cfg.get("motif_similarity_threshold", 0.75)\n'
            "(0.5 to 1.0, default 0.75)\n"
        ),
        "src/api/schemas.py": (
            '"motif_similarity_threshold": 0.75,\n'
            "    motif_similarity_threshold: float = Field(\n"
            "        default=0.75,\n"
            "        ge=0.5,\n"
            "        le=1.0,\n"
            '        description="Fuzzy motif alignment similarity threshold '
            '(0.5 to 1.0, default 0.75)",\n'
            "    )\n"
        ),
    }
    for relative, content in files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def test_apply_threshold_rewrites_all_defaults(tmp_path: Path) -> None:
    """Every hard-coded default must be rewritten consistently."""
    _create_fake_project(tmp_path)

    applied = apply_threshold_to_defaults(0.65, project_root=tmp_path)

    assert applied == {
        "src/game_design/pitch_to_fret.py": 2,
        "src/pipeline.py": 3,
        "src/api/schemas.py": 3,
    }
    for relative in applied:
        content = (tmp_path / relative).read_text(encoding="utf-8")
        assert "0.75" not in content
        assert "0.65" in content
    creativity_line = (tmp_path / "src/game_design/pitch_to_fret.py").read_text(encoding="utf-8")
    assert "(default 0.5)." in creativity_line


def test_apply_threshold_validates_range(tmp_path: Path) -> None:
    """Out-of-range thresholds are rejected before touching any file."""
    with pytest.raises(ValueError):
        apply_threshold_to_defaults(1.5, project_root=tmp_path)


def test_apply_threshold_can_rewrite_a_non_default_value(tmp_path: Path) -> None:
    """Re-applying must work after a previous calibration changed the value."""
    _create_fake_project(tmp_path)
    apply_threshold_to_defaults(0.50, project_root=tmp_path)

    applied = apply_threshold_to_defaults(0.75, project_root=tmp_path)

    assert applied == {
        "src/game_design/pitch_to_fret.py": 2,
        "src/pipeline.py": 3,
        "src/api/schemas.py": 3,
    }
    for relative in applied:
        content = (tmp_path / relative).read_text(encoding="utf-8")
        assert "0.50" not in content
        assert "0.75" in content


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

_CHART_TEMPLATE = """[Song]
{{
  Name = "Test"
  Resolution = 192
}}
[SyncTrack]
{{
  0 = B 120000
}}
[ExpertSingle]
{{
{notes}
}}
"""


def _write_chart(path: Path, notes: list[tuple[int, int]]) -> Path:
    lines = [f"  {tick} = N {fret} 0" for tick, fret in notes]
    path.write_text(_CHART_TEMPLATE.format(notes="\n".join(lines)), encoding="utf-8")
    return path


def test_cli_writes_report(tmp_path: Path) -> None:
    """The CLI persists a JSON report containing every threshold row."""
    gt_notes = [(0, 0), (96, 1), (192, 2), (480, 0), (576, 1), (672, 2)]
    pred_notes = [(0, 0), (96, 1), (192, 2), (480, 0), (576, 1), (672, 3)]
    gt_path = _write_chart(tmp_path / "gt.chart", gt_notes)
    pred_path = _write_chart(tmp_path / "pred.chart", pred_notes)
    report_path = tmp_path / "report.json"

    exit_code = main(
        [
            "--gt",
            str(gt_path),
            "--pred",
            str(pred_path),
            "--report",
            str(report_path),
            "--step",
            "0.05",
        ]
    )

    assert exit_code == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["ground_truth"]["resolution"] == 192
    assert report["prediction"]["is_ground_truth"] is False
    assert len(report["thresholds"]) == len(THRESHOLD_GRID)
    assert report["optimal_threshold"] in THRESHOLD_GRID
    assert report["composite_weights"] == {
        "riff_consistency_score": 0.70,
        "fret_accuracy": 0.30,
    }
    assert report["offset_seconds"] == pytest.approx(0.0, abs=0.05)


def test_cli_apply_requires_self_calibration_opt_in(tmp_path: Path) -> None:
    """--apply must refuse when predictions are the ground truth."""
    chart_path = _write_chart(tmp_path / "gt.chart", [(0, 0), (96, 1), (192, 2)] * 2)
    report_path = tmp_path / "report.json"

    exit_code = main(
        [
            "--gt",
            str(chart_path),
            "--report",
            str(report_path),
            "--apply",
            "--thresholds",
            "0.50",
            "--project-root",
            str(tmp_path),
        ]
    )

    assert exit_code == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["apply_requested"] is True
    assert report["applied_files"] == {}
    assert "self-calibration" in report["apply_skipped_reason"]


def test_cli_reports_missing_instrument_track(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Invalid inputs produce a clean error message and exit code 2."""
    chart_path = _write_chart(tmp_path / "gt.chart", [(0, 0), (96, 1)])

    exit_code = main(
        [
            "--gt",
            str(chart_path),
            "--difficulty",
            "Hard",
            "--report",
            str(tmp_path / "report.json"),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "Track 'HardSingle' not found" in captured.err


def test_motif_min_notes_constant_matches_mapper_default() -> None:
    """Motif window must mirror PitchToFretMapper.min_pattern_len."""
    from src.game_design.pitch_to_fret import PitchToFretMapper

    assert DEFAULT_MOTIF_MIN_NOTES == PitchToFretMapper().min_pattern_len
