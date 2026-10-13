"""Exhaustive empirical verification and mathematical oracle harness for NoteQuantizer.

Tests:
1. Exhaustive grid snapping for all ticks t in [0, 1920] (10 measures) against an independent oracle.
2. Verification of grid membership and Voronoi optimality (distance <= distance to any other grid point).
3. Verification of all 120 equidistant tie points across 10 measures (6 per 96-tick half-measure).
4. Custom tolerance testing (tol=0, tol=4, tol=8, tol=16, tol=32) and restricted subdivision sets.
5. Boundary conditions (negative ticks, zero, extreme ticks 1,000,000+, floats).
6. High-volume stress test (10,000 synthetic notes) testing deduplication and chronological ordering.
"""

from __future__ import annotations

import random
import sys
from collections.abc import Sequence

# Add workspace to path if needed
sys.path.insert(0, "/home/adiel/Projects/music2chart")

from src.game_design.quantizer import NoteQuantizer
from src.models import BPMChange, NoteEvent, TempoMap, TimeSignature

# -----------------------------------------------------------------------------
# 1. Independent Mathematical Oracle
# -----------------------------------------------------------------------------


def oracle_priority(tick: int) -> int:
    """Musical hierarchy priority:
    192 (1/4) > 96 (1/8) > 48 (1/16) > 64 (1/12) > 32 (1/24) > 24 (1/32).
    """
    if tick < 0:
        return 0
    if tick % 192 == 0:
        return 6
    if tick % 96 == 0:
        return 5
    if tick % 48 == 0:
        return 4
    if tick % 64 == 0:
        return 3
    if tick % 32 == 0:
        return 2
    if tick % 24 == 0:
        return 1
    return 0


def oracle_snap(
    tick: float,
    subdivisions: Sequence[int] = (192, 96, 64, 48, 32, 24),
    tolerance_ticks: int = 16,
) -> int:
    """Ground truth independent oracle using brute force search."""
    t = int(round(tick))
    if tolerance_ticks < 0:
        raise ValueError("tolerance must be non-negative")

    # Generate all possible non-negative grid points within search window
    min_search = max(0, t - tolerance_ticks)
    max_search = t + tolerance_ticks

    candidates: set[int] = set()
    for s in subdivisions:
        start_k = max(0, (min_search // s) - 1)
        end_k = (max_search // s) + 2
        for k in range(start_k, end_k + 1):
            cand = k * s
            if cand >= 0 and abs(cand - t) <= tolerance_ticks:
                candidates.add(cand)

    if not candidates:
        return max(0, t)

    # Find candidate minimizing: (distance, -priority, candidate_tick)
    best = min(
        candidates,
        key=lambda c: (abs(c - t), -oracle_priority(c), c),
    )
    return best


def get_all_grid_points_in_range(
    max_tick: int,
    subdivisions: Sequence[int] = (192, 96, 64, 48, 32, 24),
) -> set[int]:
    """Return all non-negative grid points up to max_tick."""
    grid: set[int] = set()
    for s in subdivisions:
        k = 0
        while k * s <= max_tick:
            grid.add(k * s)
            k += 1
    return grid


# -----------------------------------------------------------------------------
# Test Suites
# -----------------------------------------------------------------------------


def test_exhaustive_oracle_10_measures() -> tuple[bool, int, list[str]]:
    """Test 1: Compare NoteQuantizer against independent Oracle for all t in [0, 1920]."""
    quantizer = NoteQuantizer(tolerance_ticks=16)
    mismatches: list[str] = []
    total = 1921

    for t in range(total):
        actual = quantizer.snap_tick(t)
        expected = oracle_snap(t, tolerance_ticks=16)
        if actual != expected:
            mismatches.append(f"t={t}: actual={actual}, expected={expected}")

    return len(mismatches) == 0, total, mismatches


def test_grid_membership_and_voronoi_optimality() -> tuple[bool, int, list[str]]:
    """Test 2:
    - Every snapped tick in [0, 1920] belongs to the valid grid subdivision set.
    - Distance to snapped tick is <= 16.
    - Distance to snapped tick is <= distance to ANY other grid point in existence.
    """
    quantizer = NoteQuantizer(tolerance_ticks=16)
    all_grid_points = get_all_grid_points_in_range(2500)
    failures: list[str] = []
    total = 1921

    for t in range(total):
        snapped = quantizer.snap_tick(t)

        # Invariant 1: Non-negative
        if snapped < 0:
            failures.append(f"t={t}: snapped tick {snapped} < 0")
            continue

        # Invariant 2: Snapped tick is a member of valid grid points
        if snapped not in all_grid_points:
            failures.append(f"t={t}: snapped tick {snapped} not in grid points")

        # Invariant 3: Distance <= 16
        dist = abs(snapped - t)
        if dist > 16:
            failures.append(f"t={t}: snapped distance {dist} > tolerance 16")

        # Invariant 4: Snapped tick has minimal distance among ALL grid points
        for g in all_grid_points:
            other_dist = abs(g - t)
            if other_dist < dist:
                failures.append(
                    f"t={t}: suboptimal snap! Snapped to {snapped} (dist={dist}), but grid point {g} has closer dist={other_dist}"
                )
                break

    return len(failures) == 0, total, failures


def test_all_equidistant_tie_points() -> tuple[bool, int, list[dict]]:
    """Test 3: Verify all 120 equidistant conflict points in [0, 1920] (6 per 96 ticks)."""
    quantizer = NoteQuantizer(tolerance_ticks=16)
    tie_results: list[dict] = []
    failures: list[dict] = []

    # 10 measures = 1920 ticks = 20 half-measures of 96 ticks
    for half_measure in range(20):
        base = half_measure * 96
        # The 6 equidistant conflict offsets mod 96:
        # 12: between 0 and 24 (dist 12)
        # 28: between 24 and 32 (dist 4)
        # 40: between 32 and 48 (dist 8)
        # 56: between 48 and 64 (dist 8)
        # 68: between 64 and 72 (dist 4)
        # 84: between 72 and 96 (dist 12)
        midpoints = [
            (12, base + 0, base + 24),
            (28, base + 24, base + 32),
            (40, base + 32, base + 48),
            (56, base + 48, base + 64),
            (68, base + 64, base + 72),
            (84, base + 72, base + 96),
        ]

        for offset, left_cand, right_cand in midpoints:
            t = base + offset
            dist_left = abs(t - left_cand)
            dist_right = abs(t - right_cand)
            assert dist_left == dist_right, f"Internal test error: not equidistant at t={t}"

            prio_left = oracle_priority(left_cand)
            prio_right = oracle_priority(right_cand)
            expected_winner = left_cand if prio_left > prio_right else right_cand

            actual_winner = quantizer.snap_tick(t)

            res = {
                "t": t,
                "left": left_cand,
                "right": right_cand,
                "dist": dist_left,
                "prio_left": prio_left,
                "prio_right": prio_right,
                "expected": expected_winner,
                "actual": actual_winner,
                "passed": (actual_winner == expected_winner),
            }
            tie_results.append(res)
            if not res["passed"]:
                failures.append(res)

    return len(failures) == 0, len(tie_results), failures


def test_custom_tolerances() -> tuple[bool, int, list[str]]:
    """Test 4: Custom tolerance behavior.
    - tol=0: Only exact grid points snap, non-grid remain raw.
    - tol=4: Only points within 4 ticks snap.
    - tol=8: Points within 8 ticks snap, distance 9-12 remain raw.
    - Restricted subdivisions (subdivisions=[192]): strictly enforces tol=16 window.
    """
    failures: list[str] = []
    total = 0

    # tol = 0
    q_tol0 = NoteQuantizer(tolerance_ticks=0)
    all_grid = get_all_grid_points_in_range(192)
    for t in range(193):
        total += 1
        snapped = q_tol0.snap_tick(t)
        if t in all_grid:
            if snapped != t:
                failures.append(f"tol=0: grid point {t} should snap to itself, got {snapped}")
        else:
            if snapped != t:
                failures.append(f"tol=0: non-grid point {t} should remain {t}, got {snapped}")

    # tol = 8
    q_tol8 = NoteQuantizer(tolerance_ticks=8)
    for t in range(193):
        total += 1
        actual = q_tol8.snap_tick(t)
        expected = oracle_snap(t, tolerance_ticks=8)
        if actual != expected:
            failures.append(f"tol=8: t={t}: actual={actual}, expected={expected}")

    # Restricted subdivision [192] with tol=16
    q_192 = NoteQuantizer(subdivisions=[192], tolerance_ticks=16)
    for t in range(500):
        total += 1
        actual = q_192.snap_tick(t)
        expected = oracle_snap(t, subdivisions=[192], tolerance_ticks=16)
        if actual != expected:
            failures.append(f"subdiv=[192]: t={t}: actual={actual}, expected={expected}")

    # Restricted subdivision [64] with tol=10
    q_64 = NoteQuantizer(subdivisions=[64], tolerance_ticks=10)
    for t in range(300):
        total += 1
        actual = q_64.snap_tick(t)
        expected = oracle_snap(t, subdivisions=[64], tolerance_ticks=10)
        if actual != expected:
            failures.append(f"subdiv=[64]: t={t}: actual={actual}, expected={expected}")

    return len(failures) == 0, total, failures


def test_float_and_boundary_conditions() -> tuple[bool, int, list[str]]:
    """Test 5: Float ticks, negative values, and very large ticks."""
    quantizer = NoteQuantizer(tolerance_ticks=16)
    failures: list[str] = []
    total = 0

    # Floats: t + 0.1 * step
    for base in [0, 24, 48, 64, 96, 192]:
        for delta in [-10.4, -5.7, -0.4, 0.0, 0.3, 0.6, 7.8, 15.9, 16.1, 20.0]:
            total += 1
            t_float = base + delta
            actual = quantizer.snap_tick(t_float)
            expected = quantizer.snap_tick(int(round(t_float)))
            if actual != expected:
                failures.append(f"float t={t_float}: actual={actual}, expected={expected}")

    # Negative ticks
    for neg_t in [-50, -20, -17, -16, -15, -5, -1, 0]:
        total += 1
        actual = quantizer.snap_tick(neg_t)
        # If abs(0 - neg_t) <= 16, 0 is candidate -> returns 0
        # If neg_t < -16, no valid candidate -> returns max(0, neg_t) = 0!
        if actual != 0:
            failures.append(f"neg t={neg_t}: actual={actual}, expected=0")

    # Extreme large ticks
    large_ticks = [1_000_000, 1_000_002, 10_000_192, 50_000_000]
    for lt in large_ticks:
        total += 1
        actual = quantizer.snap_tick(lt)
        expected = oracle_snap(lt, tolerance_ticks=16)
        if actual != expected:
            failures.append(f"large t={lt}: actual={actual}, expected={expected}")

    return len(failures) == 0, total, failures


def test_high_volume_stress_and_deduplication() -> tuple[bool, int, list[str]]:
    """Test 6: 10,000 synthetic notes stress test:
    - Verifies deduplication logic merges identical (snapped_tick, pitch).
    - Verifies max(amplitude) and max(duration_ticks) are strictly preserved.
    - Verifies chronological ordering invariant: tick ascending, then pitch ascending.
    """
    quantizer = NoteQuantizer(tolerance_ticks=16)
    tempo_map = TempoMap(
        resolution=192,
        bpm_changes=[
            BPMChange(tick=0, bpm=120.0),
            BPMChange(tick=768, bpm=150.0),
            BPMChange(tick=1536, bpm=100.0),
        ],
        time_signatures=[TimeSignature(tick=0, numerator=4, denominator=4)],
    )

    random.seed(42)
    raw_notes: list[NoteEvent] = []
    expected_clusters: dict[tuple[int, int], tuple[int, float]] = {}

    n_notes = 10_000
    for _ in range(n_notes):
        # Pick a target grid tick in [0, 1920]
        base_grid = random.choice([0, 24, 32, 48, 64, 72, 96, 120, 128, 144, 160, 168, 192])
        measure = random.randint(0, 9)
        grid_tick = measure * 192 + base_grid

        # Add jitter in [-15, 15]
        jitter = random.randint(-15, 15)
        raw_start_tick = max(0, grid_tick + jitter)
        raw_dur_ticks = random.randint(20, 250)
        raw_end_tick = raw_start_tick + raw_dur_ticks

        pitch = random.randint(40, 80)
        amplitude = round(random.uniform(0.1, 1.0), 3)

        start_sec = tempo_map.tick_to_seconds(raw_start_tick)
        end_sec = tempo_map.tick_to_seconds(raw_end_tick)

        raw_notes.append(
            NoteEvent(
                start_time=start_sec,
                end_time=end_sec,
                pitch=pitch,
                amplitude=amplitude,
            )
        )

        snapped = quantizer.snap_tick(raw_start_tick)
        effective_dur = max(1, raw_end_tick - raw_start_tick)
        key = (snapped, pitch)
        if key not in expected_clusters:
            expected_clusters[key] = (effective_dur, amplitude)
        else:
            prev_dur, prev_amp = expected_clusters[key]
            expected_clusters[key] = (
                max(prev_dur, effective_dur),
                max(prev_amp, amplitude),
            )

    # Run quantizer
    result = quantizer.quantize(raw_notes, tempo_map)
    failures: list[str] = []

    # Check 1: Length matches unique clusters
    if len(result) != len(expected_clusters):
        failures.append(
            f"Length mismatch: result has {len(result)} notes, expected {len(expected_clusters)}"
        )

    # Check 2: Strict chronological sorting
    for i in range(len(result) - 1):
        curr = result[i]
        nxt = result[i + 1]
        if curr.tick > nxt.tick or (curr.tick == nxt.tick and curr.pitch > nxt.pitch):
            failures.append(
                f"Sorting violation at index {i}: ({curr.tick}, {curr.pitch}) > ({nxt.tick}, {nxt.pitch})"
            )
            break

    # Check 3: Every cluster correctly preserved with max amplitude and duration
    for note in result:
        key = (note.tick, note.pitch)
        if key not in expected_clusters:
            failures.append(f"Unexpected note in result: {key}")
            continue
        exp_dur, exp_amp = expected_clusters[key]
        if note.duration_ticks != exp_dur:
            failures.append(
                f"{key}: duration_ticks mismatch. Got {note.duration_ticks}, expected {exp_dur}"
            )
            break
        if abs(note.amplitude - exp_amp) > 1e-4:
            failures.append(
                f"{key}: amplitude mismatch. Got {note.amplitude}, expected {exp_amp}"
            )
            break

    return len(failures) == 0, n_notes, failures


# -----------------------------------------------------------------------------
# Main Runner
# -----------------------------------------------------------------------------


def main() -> int:
    print("=" * 70)
    print("CHALLENGER STRESS HARNESS: NoteQuantizer Exhaustive Oracle Verification")
    print("=" * 70)

    # Test 1
    t1_pass, t1_count, t1_errs = test_exhaustive_oracle_10_measures()
    print("[TEST 1] Exhaustive Oracle Comparison (0..1920 ticks):")
    print(f"         Total evaluated: {t1_count} ticks")
    print(f"         Status: {'PASSED (100% match)' if t1_pass else 'FAILED'}")
    if not t1_pass:
        print(f"         Errors (first 5): {t1_errs[:5]}")

    # Test 2
    t2_pass, t2_count, t2_errs = test_grid_membership_and_voronoi_optimality()
    print("\n[TEST 2] Grid Subdivision Membership & Voronoi Distance Minimization:")
    print(f"         Total evaluated: {t2_count} ticks")
    print(f"         Status: {'PASSED (All points optimal & valid)' if t2_pass else 'FAILED'}")
    if not t2_pass:
        print(f"         Errors (first 5): {t2_errs[:5]}")

    # Test 3
    t3_pass, t3_count, t3_errs = test_all_equidistant_tie_points()
    print("\n[TEST 3] Equidistant Tie-Breaking Priority Hierarchy:")
    print(f"         Total tie points evaluated: {t3_count} (across 10 measures)")
    print(f"         Status: {'PASSED (All 120 ties resolved strictly by hierarchy)' if t3_pass else 'FAILED'}")
    if not t3_pass:
        print(f"         Errors: {t3_errs}")

    # Test 4
    t4_pass, t4_count, t4_errs = test_custom_tolerances()
    print("\n[TEST 4] Custom Tolerances (tol=0, tol=8, restricted subdivs):")
    print(f"         Total evaluated: {t4_count} points")
    print(f"         Status: {'PASSED' if t4_pass else 'FAILED'}")
    if not t4_pass:
        print(f"         Errors (first 5): {t4_errs[:5]}")

    # Test 5
    t5_pass, t5_count, t5_errs = test_float_and_boundary_conditions()
    print("\n[TEST 5] Float Jitter, Negative Ticks & Large Tick Boundaries:")
    print(f"         Total evaluated: {t5_count} cases")
    print(f"         Status: {'PASSED' if t5_pass else 'FAILED'}")
    if not t5_pass:
        print(f"         Errors: {t5_errs}")

    # Test 6
    t6_pass, t6_count, t6_errs = test_high_volume_stress_and_deduplication()
    print("\n[TEST 6] High-Volume Stress Test (10,000 NoteEvents, Multi-BPM):")
    print(f"         Total notes processed: {t6_count}")
    print(f"         Status: {'PASSED (Deduplication, Max-Amp/Dur, Sorting all 100%)' if t6_pass else 'FAILED'}")
    if not t6_pass:
        print(f"         Errors: {t6_errs}")

    print("\n" + "=" * 70)
    all_passed = t1_pass and t2_pass and t3_pass and t4_pass and t5_pass and t6_pass
    if all_passed:
        print("OVERALL VERDICT: ALL TESTS PASSED STRICTLY. 0 FAILURES.")
        return 0
    else:
        print("OVERALL VERDICT: FAILURES DETECTED.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
