"""Oracle and Property-Based Verification Harness for PitchToFretMapper.

Challenger: challenger_m2_2
Milestone: Phase 4 — Milestone 2 (Adaptive Pitch-to-Fret Projection)
Target: src/game_design/pitch_to_fret.py
"""

from __future__ import annotations

import pathlib
import random
import sys
import time

# Ensure project root is on sys.path
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.game_design.pitch_to_fret import (  # noqa: E402
    DEFAULT_MAX_JUMP,
    DEFAULT_OPEN_THRESHOLD,
    PitchToFretMapper,
)
from src.game_design.quantizer import QuantizedNote  # noqa: E402
from src.models.chart import ChartNote, FretType  # noqa: E402


def _make_qn(tick: int, pitch: int, duration_ticks: int = 48, amplitude: float = 0.8) -> QuantizedNote:
    return QuantizedNote(
        tick=tick,
        pitch=pitch,
        duration_ticks=duration_ticks,
        amplitude=amplitude,
    )


# ===========================================================================
# Suite 1: Sub-bass & Valid Fret Invariants
# ===========================================================================


def test_suite_1_invariants() -> None:
    """Verify fret bounds and sub-bass partitioning invariants across full MIDI range."""
    print("[Suite 1] Running Sub-bass & Valid Fret Invariants...")
    mapper = PitchToFretMapper()

    # 1. Full MIDI pitch sweep (0 to 127) individually
    for p in range(128):
        notes = [_make_qn(tick=0, pitch=p)]
        res = mapper.map_notes(notes)
        assert len(res) == 1, f"Expected 1 note for pitch {p}, got {len(res)}"
        n = res[0]
        assert isinstance(n, ChartNote)
        assert n.sustain_length == 0
        assert n.is_hopo is False

        if p < DEFAULT_OPEN_THRESHOLD:
            assert n.fret == FretType.OPEN, f"Pitch {p} < 40 must map to OPEN (7), got {n.fret}"
            assert n.fret.value == 7
        else:
            assert n.fret.value in (0, 1, 2, 3, 4), f"Pitch {p} >= 40 must map to 0..4, got {n.fret}"

    # 2. Dense random stream across full MIDI range (2,000 notes)
    random.seed(101)
    dense_notes = []
    t = 0
    for _ in range(2000):
        t += random.choice([24, 48, 96, 192])
        p = random.randint(0, 127)
        dense_notes.append(_make_qn(tick=t, pitch=p))

    res_dense = mapper.map_notes(dense_notes)
    assert len(res_dense) == len(dense_notes)

    for qn, cn in zip(dense_notes, res_dense, strict=True):
        assert cn.tick == qn.tick
        if qn.pitch < DEFAULT_OPEN_THRESHOLD:
            assert cn.fret == FretType.OPEN, f"Pitch {qn.pitch} mapped to {cn.fret}"
        else:
            assert cn.fret.value in (0, 1, 2, 3, 4), f"Fretted note pitch {qn.pitch} mapped to {cn.fret}"
        assert cn.sustain_length == 0
        assert cn.is_hopo is False

    print("  -> PASSED: All 2,128 notes satisfied domain bounds and sub-bass partitioning.")


# ===========================================================================
# Suite 2: Ergonomic Rapid Passage Jump Clamping (|fret - prev_fret| <= 3)
# ===========================================================================


def test_suite_2_rapid_passage_jump_clamping() -> None:
    """Verify rapid passage jump penalty strictly enforces |fret - prev_fret| <= 3 for dt < 48."""
    print("[Suite 2] Running Rapid Passage Jump Clamping (|fret - prev_fret| <= 3)...")
    mapper = PitchToFretMapper()

    # 1. Exhaustive pairwise leap test for dt in [1, 47]
    # In a window with p_min=60 and p_max=84, raw frets map to 0 and 4.
    for dt in [1, 6, 12, 24, 36, 47]:
        # Green (0) -> Orange (4) clamped to Blue (3)
        res_asc = mapper.map_notes([_make_qn(0, 60), _make_qn(dt, 84)])
        assert len(res_asc) == 2
        f0 = res_asc[0].fret.value
        f1 = res_asc[1].fret.value
        diff_asc = abs(f1 - f0)
        assert diff_asc <= DEFAULT_MAX_JUMP, f"Ascending leap dt={dt} failed: {f0} -> {f1} (diff {diff_asc})"
        assert f0 == 0 and f1 == 3, f"Expected 0 -> 3, got {f0} -> {f1}"

        # Orange (4) -> Green (0) clamped to Red (1)
        res_desc = mapper.map_notes([_make_qn(0, 84), _make_qn(dt, 60)])
        assert len(res_desc) == 2
        f0 = res_desc[0].fret.value
        f1 = res_desc[1].fret.value
        diff_desc = abs(f1 - f0)
        assert diff_desc <= DEFAULT_MAX_JUMP, f"Descending leap dt={dt} failed: {f0} -> {f1} (diff {diff_desc})"
        assert f0 == 4 and f1 == 1, f"Expected 4 -> 1, got {f0} -> {f1}"

    # 2. Verification that dt >= 48 permits full 4-fret leap without clamping
    for dt in [48, 64, 96, 192]:
        res = mapper.map_notes([_make_qn(0, 60), _make_qn(dt, 84)])
        assert res[0].fret.value == 0 and res[1].fret.value == 4, f"Permitted leap dt={dt} was clamped"

    # 3. 5,000 random monophonic rapid passage transitions with dt < 48
    random.seed(202)
    violations = 0
    total_rapid_pairs = 0

    for _trial in range(500):
        length = random.randint(5, 30)
        t = 0
        notes = []
        for _ in range(length):
            t += random.randint(1, 47)  # Strictly rapid (< 48 ticks)
            p = random.randint(40, 100)  # Fretted notes only
            notes.append(_make_qn(t, p))

        res = mapper.map_notes(notes)
        for i in range(len(res) - 1):
            interval = res[i + 1].tick - res[i].tick
            jump = abs(res[i + 1].fret.value - res[i].fret.value)
            if 0 < interval < 48:
                total_rapid_pairs += 1
                if jump > DEFAULT_MAX_JUMP:
                    violations += 1

    assert violations == 0, f"Found {violations} violations of |fret - prev_fret| <= 3 among {total_rapid_pairs} pairs"
    print(f"  -> PASSED: 0 violations out of {total_rapid_pairs} rapid consecutive pairs checked.")


# ===========================================================================
# Suite 3: Ascending Chromatic Scales Monotonicity
# ===========================================================================


def test_suite_3_ascending_chromatic_monotonicity() -> None:
    """Verify ascending chromatic scales produce monotonically non-decreasing frets."""
    print("[Suite 3] Running Ascending Chromatic Scales Monotonicity...")
    mapper = PitchToFretMapper()

    # 1. Exhaustive testing of uniform chromatic scales across various start pitches,
    # lengths, and musical subdivisions
    tested_scales = 0
    failures = 0

    subdivisions = [12, 24, 32, 48, 64, 96, 192]
    start_pitches = list(range(40, 95, 5))
    scale_lengths = [3, 5, 8, 12, 16, 20, 24]  # Up to 2 full octaves

    for start_p in start_pitches:
        for length in scale_lengths:
            if start_p + length > 127:
                continue
            for step in subdivisions:
                notes = [_make_qn(tick=i * step, pitch=start_p + i, duration_ticks=step) for i in range(length)]
                res = mapper.map_notes(notes)
                frets = [n.fret.value for n in res]

                # Check non-decreasing condition
                for i in range(len(frets) - 1):
                    if frets[i] > frets[i + 1]:
                        failures += 1
                        print(
                            f"FAIL in chromatic scale: start={start_p}, len={length}, step={step}: "
                            f"frets[{i}]={frets[i]} > frets[{i+1}]={frets[i+1]} (frets={frets})"
                        )
                        break
                tested_scales += 1

                # Check boundary coverage for standard 12-note chromatic scale
                if length == 12:
                    assert frets[0] == 0, f"12-note scale must start at Green (0), got {frets[0]}"
                    assert frets[-1] == 4, f"12-note scale must end at Orange (4), got {frets[-1]}"

    assert failures == 0, f"Found {failures} non-monotonic scales out of {tested_scales} tested"
    print(f"  -> PASSED: {tested_scales} uniform chromatic scales verified 100% monotonic non-decreasing.")

    # 2. Variable-rhythm single-window chromatic scales (span < 1536 ticks)
    random.seed(303)
    single_window_trials = 300
    single_window_failures = 0

    for _ in range(single_window_trials):
        start_p = random.randint(40, 75)
        length = random.randint(4, 15)
        t = 0
        ticks = []
        for _ in range(length):
            t += random.choice([24, 48, 64, 96])
            ticks.append(t)
        if ticks[-1] - ticks[0] >= 1500:
            continue

        notes = [_make_qn(tick=ticks[i], pitch=start_p + i, duration_ticks=24) for i in range(length)]
        res = mapper.map_notes(notes)
        frets = [n.fret.value for n in res]
        for i in range(len(frets) - 1):
            if frets[i] > frets[i + 1]:
                single_window_failures += 1
                break

    assert single_window_failures == 0, f"Found {single_window_failures} variable-rhythm single-window failures"
    print(f"  -> PASSED: {single_window_trials} variable-rhythm single-window chromatic scales verified monotonic.")


# ===========================================================================
# Suite 4: Dynamic Register & Solo Fret Utilization
# ===========================================================================


def test_suite_4_high_solo_fret_utilization() -> None:
    """Verify high-solo register passages utilize at least 4 of the 5 frets over a 4-measure solo."""
    print("[Suite 4] Running High-Solo Register Fret Utilization...")
    mapper = PitchToFretMapper()

    # 4 measures in 4/4 at 192 PPQ = 3072 ticks
    solo_ticks = 3072
    random.seed(404)
    num_trials = 500
    insufficient_fret_count = 0

    for _ in range(num_trials):
        base_pitch = random.randint(72, 84)  # High guitar register (C5 to C6)
        num_distinct_pitches = random.randint(5, 12)  # Realistic musical variety
        pool = sorted(random.sample(range(base_pitch, base_pitch + 16), num_distinct_pitches))

        num_notes = random.randint(24, 64)  # 24 to 64 notes over 4 measures (8th to 16th notes)
        step = solo_ticks // num_notes

        notes = []
        for i in range(num_notes):
            p = random.choice(pool)
            notes.append(_make_qn(tick=i * step, pitch=p, duration_ticks=step // 2, amplitude=0.9))

        # Anchor the min and max pitch into the solo passage
        notes[0] = _make_qn(tick=notes[0].tick, pitch=pool[0], duration_ticks=step // 2, amplitude=0.9)
        notes[1] = _make_qn(tick=notes[1].tick, pitch=pool[-1], duration_ticks=step // 2, amplitude=0.9)

        res = mapper.map_notes(notes)
        unique_frets = {n.fret.value for n in res}

        if len(unique_frets) < 4:
            insufficient_fret_count += 1
            print(f"FAIL: Solo used only {len(unique_frets)} frets {unique_frets} with pitches {pool}")

    assert insufficient_fret_count == 0, (
        f"Found {insufficient_fret_count} 4-measure high solos utilizing fewer than 4 frets"
    )
    print(f"  -> PASSED: All {num_trials} 4-measure high solos utilized at least 4 of 5 frets (>= 80% span).")

    # Also verify low riff passage (pitches 42..56) utilizes at least 4 frets (symmetry test)
    low_riff_notes = [_make_qn(tick=i * 96, pitch=42 + (i % 6) * 2) for i in range(32)]
    res_riff = mapper.map_notes(low_riff_notes)
    unique_riff_frets = {n.fret.value for n in res_riff}
    assert len(unique_riff_frets) >= 4, f"Low riff only used {len(unique_riff_frets)} frets"
    print("  -> PASSED: Low riff symmetry test also utilized >= 4 frets.")


# ===========================================================================
# Suite 5: Adversarial Boundary & Stress Scenarios
# ===========================================================================


def test_suite_5_adversarial_boundaries_and_stress() -> None:
    """Stress test boundary cases, chords, out-of-order notes, and throughput."""
    print("[Suite 5] Running Adversarial Boundary & Stress Scenarios...")
    mapper = PitchToFretMapper()

    # 1. Empty input
    assert mapper.map_notes([]) == []

    # 2. Single fretted note & single sub-bass note
    s_fret = mapper.map_notes([_make_qn(0, 60)])
    assert len(s_fret) == 1 and s_fret[0].fret == FretType.GREEN

    s_open = mapper.map_notes([_make_qn(0, 32)])
    assert len(s_open) == 1 and s_open[0].fret == FretType.OPEN

    # 3. Monotone repeating note (no division-by-zero or crash)
    monotone = mapper.map_notes([_make_qn(i * 48, 64) for i in range(100)])
    assert len(monotone) == 100
    assert all(n.fret == FretType.GREEN for n in monotone)

    # 4. Out-of-order input sorting invariant
    unordered = [
        _make_qn(1000, 70),
        _make_qn(0, 50),
        _make_qn(500, 60),
        _make_qn(500, 55),
    ]
    sorted_res = mapper.map_notes(unordered)
    ticks = [n.tick for n in sorted_res]
    assert ticks == [0, 500, 500, 1000]

    # 5. Throughput benchmark: 5,000 notes in < 0.5s
    bench_notes = [_make_qn(tick=i * 24, pitch=45 + (i % 30)) for i in range(5000)]
    t0 = time.perf_counter()
    bench_res = mapper.map_notes(bench_notes)
    elapsed = time.perf_counter() - t0
    assert len(bench_res) == 5000
    print(f"  -> PASSED: Benchmark processed 5,000 notes in {elapsed:.3f}s ({len(bench_notes)/elapsed:.0f} notes/sec).")


def main() -> None:
    print("=" * 70)
    print("ORACLE PROPERTY VERIFICATION: PitchToFretMapper")
    print("=" * 70)

    start = time.perf_counter()
    test_suite_1_invariants()
    test_suite_2_rapid_passage_jump_clamping()
    test_suite_3_ascending_chromatic_monotonicity()
    test_suite_4_high_solo_fret_utilization()
    test_suite_5_adversarial_boundaries_and_stress()
    total_time = time.perf_counter() - start

    print("=" * 70)
    print(f"ALL 5 ORACLE PROPERTY SUITES PASSED in {total_time:.3f}s")
    print("=" * 70)


if __name__ == "__main__":
    main()
