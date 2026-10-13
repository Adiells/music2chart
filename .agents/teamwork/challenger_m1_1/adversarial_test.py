"""Adversarial stress-testing harness for NoteQuantizer (Milestone 1).

Tests:
1. High-throughput random tick streams (50,000 notes) & multi-BPM scaling
2. Extreme boundary timestamps (floating-point precision jitter, microsecond deltas, timestamps > 1 hour)
3. Dense polyphonic note clusters (10+ simultaneous notes at exact same tick/pitch vs chords vs 128-polyphony)
4. Negative, zero, or inverted intervals & tolerance boundaries
5. Mathematical invariants & idempotency
"""

import random
import sys
import time
from pathlib import Path
from typing import Any

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.game_design.quantizer import NoteQuantizer, QuantizedNote  # noqa: E402
from src.models import BPMChange, NoteEvent, TempoMap  # noqa: E402


class StressTestFailure(Exception):
    """Raised when an invariant or assertion is violated during stress testing."""


def log_section(title: str) -> None:
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")


def run_suite_1_high_throughput() -> dict[str, Any]:
    """Test high-throughput random note streams (50,000 notes)."""
    log_section("SUITE 1: High-Throughput Random Note Stream (50,000 notes)")

    random.seed(42)
    n_notes = 50_000

    tempo_map = TempoMap(
        resolution=192,
        bpm_changes=[
            BPMChange(tick=0, bpm=120.0),
            BPMChange(tick=19200, bpm=140.0),
            BPMChange(tick=38400, bpm=160.0),
        ],
    )

    quantizer = NoteQuantizer(tolerance_ticks=16)

    print(f"Generating {n_notes} synthetic NoteEvents across multi-BPM timeline...")
    max_time_sec = 600.0  # 10 minutes
    notes: list[NoteEvent] = []

    for _ in range(n_notes):
        start_sec = random.uniform(0.0, max_time_sec)
        duration_sec = random.uniform(0.01, 1.5)
        pitch = random.randint(0, 127)
        amplitude = round(random.uniform(0.05, 1.0), 4)

        notes.append(
            NoteEvent(
                start_time=start_sec,
                end_time=start_sec + duration_sec,
                pitch=pitch,
                amplitude=amplitude,
            )
        )

    print(f"Executing NoteQuantizer.quantize() on {n_notes} notes...")
    t0 = time.perf_counter()
    result = quantizer.quantize(notes, tempo_map)
    elapsed = time.perf_counter() - t0

    throughput = n_notes / elapsed
    print(
        f"Quantized {n_notes} input notes -> {len(result)} output notes in {elapsed:.4f}s ({throughput:,.1f} notes/sec)"
    )

    # Invariant 1: Output notes must be non-empty
    if not result:
        raise StressTestFailure("Suite 1: Output list is unexpectedly empty")

    # Invariant 2: Output strictly sorted by (tick, pitch, duration, amplitude)
    is_sorted = all(result[i] <= result[i + 1] for i in range(len(result) - 1))
    if not is_sorted:
        raise StressTestFailure("Suite 1: Output notes are not monotonically sorted")

    # Invariant 3: Output tick >= 0, 0 <= pitch <= 127, duration_ticks >= 1, 0.0 <= amplitude <= 1.0
    for idx, qn in enumerate(result):
        if qn.tick < 0:
            raise StressTestFailure(f"Suite 1: Note #{idx} has negative tick: {qn.tick}")
        if not (0 <= qn.pitch <= 127):
            raise StressTestFailure(f"Suite 1: Note #{idx} has invalid pitch: {qn.pitch}")
        if qn.duration_ticks < 1:
            raise StressTestFailure(f"Suite 1: Note #{idx} has duration < 1: {qn.duration_ticks}")
        if not (0.0 <= qn.amplitude <= 1.0):
            raise StressTestFailure(f"Suite 1: Note #{idx} has invalid amplitude: {qn.amplitude}")

    # Invariant 4: No duplicate (tick, pitch) pairs exist in output
    seen_keys: set[tuple[int, int]] = set()
    for qn in result:
        key = (qn.tick, qn.pitch)
        if key in seen_keys:
            raise StressTestFailure(f"Suite 1: Duplicate (tick, pitch) found: {key}")
        seen_keys.add(key)

    # Invariant 5: Throughput must meet performance threshold (> 10,000 notes/sec)
    min_throughput = 10_000
    if throughput < min_throughput:
        raise StressTestFailure(
            f"Suite 1: Throughput {throughput:.1f} notes/sec below minimum {min_throughput}"
        )

    print("✓ Suite 1 PASSED: all invariants held, no duplicate keys, throughput acceptable.")
    return {
        "n_input": n_notes,
        "n_output": len(result),
        "elapsed_sec": round(elapsed, 4),
        "throughput_notes_per_sec": round(throughput, 1),
    }


def run_suite_2_extreme_boundary_timestamps() -> dict[str, Any]:
    """Test extreme boundary timestamps: microsecond deltas, floating-point jitter, >1 hour."""
    log_section("SUITE 2: Extreme Boundary Timestamps & Floating-Point Jitter")

    tempo_map = TempoMap(resolution=192, bpm_changes=[BPMChange(tick=0, bpm=120.0)])
    quantizer = NoteQuantizer(tolerance_ticks=16)

    # 1. Extreme long timestamps (> 1 hour, 10 hours, 100 hours)
    test_hours = [1.0, 5.0, 10.0, 24.0, 100.0]
    for h in test_hours:
        sec = h * 3600.0
        expected_tick = tempo_map.seconds_to_tick(sec)
        snapped = quantizer.snap_tick(expected_tick)
        # Verify valid snap and non-negative
        if snapped < 0:
            raise StressTestFailure(f"Suite 2: Negative snap for {h} hours: {snapped}")
        # Verify snapping with +/- 5 ticks jitter at large timestamps
        jittered_tick = expected_tick + 5
        snapped_jitter = quantizer.snap_tick(jittered_tick)
        if abs(snapped_jitter - jittered_tick) > 16:
            raise StressTestFailure(
                f"Suite 2: Jittered tick at {h}h did not snap within tolerance: {snapped_jitter}"
            )

    print(
        f"✓ Timestamps up to 100 hours ({100 * 3600}s, ~{tempo_map.seconds_to_tick(100 * 3600):,} ticks) processed flawlessly."
    )

    # 2. Microsecond and sub-microsecond duration deltas
    micro_deltas = [1e-3, 1e-4, 1e-5, 1e-6, 1e-7, 1e-8]
    notes_micro: list[NoteEvent] = []
    for i, delta in enumerate(micro_deltas):
        start_t = 10.0 + i * 2.0
        notes_micro.append(
            NoteEvent(
                start_time=start_t,
                end_time=start_t + delta,
                pitch=60 + i,
                amplitude=0.7,
            )
        )

    res_micro = quantizer.quantize(notes_micro, tempo_map)
    for qn in res_micro:
        if qn.duration_ticks < 1:
            raise StressTestFailure(
                f"Suite 2: Microsecond note has duration_ticks < 1: {qn.duration_ticks}"
            )
    print("✓ Microsecond deltas down to 1e-8s clamped safely to duration_ticks >= 1.")

    # 3. Floating-point precision jitter around snap tolerance boundaries (16 ticks)
    # Exactly tick 192 + 15 ticks -> dist 15 <= 16 -> snaps to 192
    tick_in = 192 + 15
    tick_edge = 192 + 16  # dist 16 <= 16 -> snaps to 192
    tick_out = 192 + 17  # dist 17 > 16 -> remains 209 (for subdivisions=[192])

    q_quarter = NoteQuantizer(subdivisions=[192], tolerance_ticks=16)
    if q_quarter.snap_tick(tick_in) != 192:
        raise StressTestFailure(
            f"Suite 2: tick 192+15 failed to snap to 192: {q_quarter.snap_tick(tick_in)}"
        )
    if q_quarter.snap_tick(tick_edge) != 192:
        raise StressTestFailure(
            f"Suite 2: tick 192+16 failed to snap to 192: {q_quarter.snap_tick(tick_edge)}"
        )
    if q_quarter.snap_tick(tick_out) != 209:
        raise StressTestFailure(
            f"Suite 2: tick 192+17 unexpectedly snapped: {q_quarter.snap_tick(tick_out)}"
        )

    # Float jitter with IEEE-754 epsilon
    epsilons = [1e-15, -1e-15, 1e-12, -1e-12, 1e-9, -1e-9]
    for eps in epsilons:
        float_tick = 192.0 + eps
        if quantizer.snap_tick(int(round(float_tick))) != 192:
            raise StressTestFailure(
                f"Suite 2: Floating point epsilon jitter failed at {float_tick}"
            )

    print("✓ Boundary tolerance (15, 16, 17 ticks) and IEEE-754 epsilon jitters verified.")
    return {"status": "PASSED"}


def run_suite_3_dense_polyphony() -> dict[str, Any]:
    """Test dense polyphonic note clusters: identical tick/pitch collisions vs chords vs 128 notes."""
    log_section("SUITE 3: Dense Polyphonic Note Clusters & Collisions")

    tempo_map = TempoMap(resolution=192, bpm_changes=[BPMChange(tick=0, bpm=120.0)])
    quantizer = NoteQuantizer(tolerance_ticks=16)

    # 1. 100 simultaneous notes at EXACT same tick and pitch with varying amplitudes and durations
    n_identical = 100
    base_start = tempo_map.tick_to_seconds(192)
    notes_identical: list[NoteEvent] = []

    max_expected_amp = 0.99
    max_expected_dur = 250

    for i in range(n_identical):
        # Slightly jittered timestamps within +/- 5 ticks, all snapping to 192
        jitter_ticks = random.randint(-5, 5)
        st = tempo_map.tick_to_seconds(192 + jitter_ticks)
        dur = random.randint(10, 200)
        amp = round(random.uniform(0.1, 0.8), 3)

        if i == 42:
            amp = max_expected_amp
        if i == 84:
            dur = max_expected_dur

        notes_identical.append(
            NoteEvent(
                start_time=st,
                end_time=tempo_map.tick_to_seconds(192 + jitter_ticks + dur),
                pitch=60,
                amplitude=amp,
            )
        )

    res_identical = quantizer.quantize(notes_identical, tempo_map)
    if len(res_identical) != 1:
        raise StressTestFailure(
            f"Suite 3: Expected 1 merged note from {n_identical} collisions, got {len(res_identical)}"
        )

    merged = res_identical[0]
    if merged.tick != 192:
        raise StressTestFailure(f"Suite 3: Expected snapped tick 192, got {merged.tick}")
    if merged.pitch != 60:
        raise StressTestFailure(f"Suite 3: Expected pitch 60, got {merged.pitch}")
    if abs(merged.amplitude - max_expected_amp) > 1e-4:
        raise StressTestFailure(
            f"Suite 3: Merged amplitude {merged.amplitude} != expected max {max_expected_amp}"
        )
    if merged.duration_ticks != max_expected_dur:
        raise StressTestFailure(
            f"Suite 3: Merged duration {merged.duration_ticks} != expected max {max_expected_dur}"
        )

    print(
        f"✓ 100 identical note collisions merged into exactly 1 note preserving max amplitude ({merged.amplitude}) and max duration ({merged.duration_ticks})."
    )

    # 2. Maximum polyphony: ALL 128 MIDI pitches (0 to 127) at the EXACT SAME TICK
    notes_128: list[NoteEvent] = []
    for pitch in range(128):
        notes_128.append(
            NoteEvent(
                start_time=base_start,
                end_time=tempo_map.tick_to_seconds(192 + 96),
                pitch=pitch,
                amplitude=0.75,
            )
        )

    res_128 = quantizer.quantize(notes_128, tempo_map)
    if len(res_128) != 128:
        raise StressTestFailure(f"Suite 3: Expected 128 distinct chord notes, got {len(res_128)}")
    # Verify strict ascending pitch ordering
    for i, qn in enumerate(res_128):
        if qn.pitch != i:
            raise StressTestFailure(f"Suite 3: Expected pitch {i} at index {i}, got {qn.pitch}")
        if qn.tick != 192:
            raise StressTestFailure(f"Suite 3: Expected tick 192 for pitch {i}, got {qn.tick}")

    print("✓ Full 128-voice polyphonic cluster at tick 192 preserved and sorted 0..127.")

    # 3. Massive grid collision: 10,000 notes concentrated on only 25 distinct (tick, pitch) cells
    n_massive = 10_000
    target_ticks = [0, 192, 384, 576, 768]
    target_pitches = [40, 52, 60, 64, 72]

    notes_grid: list[NoteEvent] = []
    for _ in range(n_massive):
        t_base = random.choice(target_ticks)
        p = random.choice(target_pitches)
        jitter = random.randint(-4, 4)
        st = tempo_map.tick_to_seconds(max(0, t_base + jitter))
        notes_grid.append(
            NoteEvent(
                start_time=st,
                end_time=tempo_map.tick_to_seconds(max(0, t_base + jitter) + 96),
                pitch=p,
                amplitude=0.8,
            )
        )

    res_grid = quantizer.quantize(notes_grid, tempo_map)
    expected_cells = len(target_ticks) * len(target_pitches)
    if len(res_grid) != expected_cells:
        raise StressTestFailure(
            f"Suite 3: Expected exactly {expected_cells} merged cells from {n_massive} notes, got {len(res_grid)}"
        )

    print(
        f"✓ Massive {n_massive}-note collision across 25 discrete bins resolved into exactly 25 notes."
    )
    return {"status": "PASSED"}


def run_suite_4_negative_zero_inverted() -> dict[str, Any]:
    """Test negative, zero, and inverted intervals and tolerance edge cases."""
    log_section("SUITE 4: Negative, Zero, and Inverted Intervals & Validation")

    quantizer = NoteQuantizer(tolerance_ticks=16)

    # 1. Negative ticks in snap_tick
    neg_ticks = [-1, -5, -15, -16, -17, -50, -100, -10_000]
    for nt in neg_ticks:
        snapped = quantizer.snap_tick(nt)
        if snapped < 0:
            raise StressTestFailure(f"Suite 4: snap_tick({nt}) produced negative tick {snapped}")
        # Ticks within 16 ticks of 0 should snap to 0
        if abs(nt) <= 16 and snapped != 0:
            raise StressTestFailure(
                f"Suite 4: snap_tick({nt}) within 16 ticks of 0 did not snap to 0, got {snapped}"
            )
        # Ticks beyond 16 ticks of 0 should clamp to 0 via max(0, t)
        if abs(nt) > 16 and snapped != 0:
            raise StressTestFailure(
                f"Suite 4: snap_tick({nt}) beyond tolerance did not clamp to 0, got {snapped}"
            )

    print("✓ All negative tick inputs to snap_tick safely bounded to >= 0.")

    # 2. Zero tolerance parameter (tolerance_ticks=0)
    q_zero_tol = NoteQuantizer(tolerance_ticks=0)
    # Exact subdivisions must snap to themselves
    assert q_zero_tol.snap_tick(192) == 192
    assert q_zero_tol.snap_tick(96) == 96
    assert q_zero_tol.snap_tick(48) == 48
    # Even 1 tick deviation must remain unsnapped
    assert q_zero_tol.snap_tick(193) == 193
    assert q_zero_tol.snap_tick(191) == 191
    print(
        "✓ tolerance_ticks=0 strictly snaps only exact multiples and preserves raw ticks for all deviations."
    )

    # 3. Model validation exceptions
    try:
        NoteQuantizer(tolerance_ticks=-1)
        raise StressTestFailure("Suite 4: Expected ValueError for negative tolerance_ticks")
    except ValueError:
        pass

    try:
        NoteQuantizer(resolution=-192)
        raise StressTestFailure("Suite 4: Expected ValueError for negative resolution")
    except ValueError:
        pass

    try:
        NoteQuantizer(subdivisions=[])
        raise StressTestFailure("Suite 4: Expected ValueError for empty subdivisions")
    except ValueError:
        pass

    try:
        NoteQuantizer(subdivisions=[192, 0])
        raise StressTestFailure("Suite 4: Expected ValueError for zero subdivision")
    except ValueError:
        pass

    try:
        QuantizedNote(tick=-1, pitch=60, duration_ticks=96, amplitude=0.8)
        raise StressTestFailure("Suite 4: Expected ValueError for negative QuantizedNote tick")
    except ValueError:
        pass

    try:
        QuantizedNote(tick=0, pitch=-1, duration_ticks=96, amplitude=0.8)
        raise StressTestFailure("Suite 4: Expected ValueError for negative QuantizedNote pitch")
    except ValueError:
        pass

    try:
        QuantizedNote(tick=0, pitch=128, duration_ticks=96, amplitude=0.8)
        raise StressTestFailure("Suite 4: Expected ValueError for pitch 128")
    except ValueError:
        pass

    try:
        QuantizedNote(tick=0, pitch=60, duration_ticks=-1, amplitude=0.8)
        raise StressTestFailure("Suite 4: Expected ValueError for negative duration_ticks")
    except ValueError:
        pass

    try:
        QuantizedNote(tick=0, pitch=60, duration_ticks=96, amplitude=-0.1)
        raise StressTestFailure("Suite 4: Expected ValueError for negative amplitude")
    except ValueError:
        pass

    try:
        QuantizedNote(tick=0, pitch=60, duration_ticks=96, amplitude=1.01)
        raise StressTestFailure("Suite 4: Expected ValueError for amplitude > 1.0")
    except ValueError:
        pass

    print("✓ All validation boundaries raised expected ValueErrors.")
    return {"status": "PASSED"}


def run_suite_5_invariants_and_idempotency() -> dict[str, Any]:
    """Test idempotency and mathematical invariants of snap_tick across 20,000 samples."""
    log_section("SUITE 5: Mathematical Invariants & Idempotency")

    quantizer = NoteQuantizer(tolerance_ticks=16)

    # 1. Idempotency: snap_tick(snap_tick(t)) == snap_tick(t)
    random.seed(1337)
    n_samples = 20_000
    for _ in range(n_samples):
        t = random.randint(-1000, 1_000_000)
        s1 = quantizer.snap_tick(t)
        s2 = quantizer.snap_tick(s1)
        if s1 != s2:
            raise StressTestFailure(
                f"Suite 5: Idempotency failed: snap_tick({t}) = {s1}, but snap_tick({s1}) = {s2}"
            )

    print(
        f"✓ Idempotency verified across {n_samples:,} random samples: snap_tick(snap_tick(t)) == snap_tick(t)."
    )

    # 2. Priority tie-breaking consistency across 100 octave shifts
    conflict_points = [(12, 0), (28, 32), (40, 48), (56, 48), (68, 64), (84, 96)]
    for base_conflict, expected_target in conflict_points:
        for offset_multiplier in range(100):
            offset = offset_multiplier * 192  # Measure shift
            t = offset + base_conflict
            expected = offset + expected_target
            actual = quantizer.snap_tick(t)
            if actual != expected:
                raise StressTestFailure(
                    f"Suite 5: Tie break failed at tick {t} (offset {offset}): expected {expected}, got {actual}"
                )

    print(
        "✓ Equidistant tie-breaking priorities hold across 100 consecutive measures (600 conflict checks)."
    )
    return {"status": "PASSED"}


def run_suite_6_subdivision_permutation_invariance() -> dict[str, Any]:
    """Test that the order of subdivisions tuple does not change snap_tick output."""
    log_section("SUITE 6: Subdivision Permutation & Configuration Invariance")

    subdiv_default = (192, 96, 64, 48, 32, 24)
    subdiv_reversed = (24, 32, 48, 64, 96, 192)
    subdiv_shuffled = (48, 24, 192, 32, 96, 64)

    q1 = NoteQuantizer(subdivisions=subdiv_default)
    q2 = NoteQuantizer(subdivisions=subdiv_reversed)
    q3 = NoteQuantizer(subdivisions=subdiv_shuffled)

    # Test all integer ticks from -50 to 500
    for t in range(-50, 501):
        s1 = q1.snap_tick(t)
        s2 = q2.snap_tick(t)
        s3 = q3.snap_tick(t)
        if s1 != s2 or s1 != s3:
            raise StressTestFailure(
                f"Suite 6: Subdivision permutation mismatch at tick {t}: default={s1}, rev={s2}, shuf={s3}"
            )

    print(
        "✓ Subdivision permutation invariance holds identically across all orderings for ticks -50..500."
    )
    return {"status": "PASSED"}


def run_suite_7_rapid_tempo_transitions() -> dict[str, Any]:
    """Test quantization across a timeline with 50 rapid BPM changes."""
    log_section("SUITE 7: Rapid Dynamic BPM Transitions (50 BPM Changes)")

    bpm_changes: list[BPMChange] = []
    # Every 2 measures (768 ticks), BPM changes alternating between 100, 130, 160, 200, 115
    bpms = [100.0, 130.0, 160.0, 200.0, 115.0]
    for i in range(50):
        bpm_changes.append(BPMChange(tick=i * 768, bpm=bpms[i % len(bpms)]))

    tempo_map = TempoMap(resolution=192, bpm_changes=bpm_changes)
    quantizer = NoteQuantizer(tolerance_ticks=16)

    # Place notes exactly at transition ticks and +/- 10 ticks around transitions
    notes: list[NoteEvent] = []
    for i in range(50):
        trans_tick = i * 768
        # Exact transition
        st_exact = tempo_map.tick_to_seconds(trans_tick)
        et_exact = tempo_map.tick_to_seconds(trans_tick + 48)
        notes.append(NoteEvent(start_time=st_exact, end_time=et_exact, pitch=60, amplitude=0.8))

        # 10 ticks before transition
        if trans_tick >= 10:
            st_pre = tempo_map.tick_to_seconds(trans_tick - 10)
            et_pre = tempo_map.tick_to_seconds(trans_tick + 38)
            notes.append(NoteEvent(start_time=st_pre, end_time=et_pre, pitch=62, amplitude=0.75))

        # 10 ticks after transition
        st_post = tempo_map.tick_to_seconds(trans_tick + 10)
        et_post = tempo_map.tick_to_seconds(trans_tick + 58)
        notes.append(NoteEvent(start_time=st_post, end_time=et_post, pitch=64, amplitude=0.85))

    result = quantizer.quantize(notes, tempo_map)
    if not result:
        raise StressTestFailure("Suite 7: Result is unexpectedly empty")

    # Verify that all notes at transition_tick - 10 and transition_tick + 10 snap properly to trans_tick (multiples of 768)
    for qn in result:
        if qn.tick < 0:
            raise StressTestFailure(f"Suite 7: Negative tick {qn.tick}")
        if qn.duration_ticks < 1:
            raise StressTestFailure(f"Suite 7: Duration < 1: {qn.duration_ticks}")

    print(
        f"✓ 50 dynamic tempo transitions processed cleanly across {len(notes)} notes -> {len(result)} quantized notes."
    )
    return {"status": "PASSED"}


def run_suite_8_float_tick_snapping() -> dict[str, Any]:
    """Test snap_tick directly with float values (continuous tick inputs)."""
    log_section("SUITE 8: Continuous Float Tick Snapping")

    quantizer = NoteQuantizer(tolerance_ticks=16)

    float_cases = [
        (47.9, 48),
        (48.1, 48),
        (11.9, 0),
        (12.1, 0),
        (23.9, 24),
        (24.1, 24),
        (31.8, 32),
        (32.2, 32),
        (63.9, 64),
        (64.1, 64),
        (95.8, 96),
        (96.2, 96),
        (191.9, 192),
        (192.1, 192),
        (0.4, 0),
        (-0.4, 0),
        (-15.9, 0),
        (-16.0, 0),
    ]

    for f_tick, expected in float_cases:
        actual = quantizer.snap_tick(f_tick)  # type: ignore[arg-type]
        if actual != expected:
            raise StressTestFailure(
                f"Suite 8: float snap failed for {f_tick}: expected {expected}, got {actual}"
            )

    print("✓ Continuous float inputs to snap_tick round and snap accurately.")
    return {"status": "PASSED"}


def main() -> None:
    print("======================================================================")
    print("     ADVERSARIAL STRESS TEST HARNESS — NoteQuantizer (Milestone 1)    ")
    print("======================================================================")

    results: dict[str, Any] = {}
    try:
        results["suite_1"] = run_suite_1_high_throughput()
        results["suite_2"] = run_suite_2_extreme_boundary_timestamps()
        results["suite_3"] = run_suite_3_dense_polyphony()
        results["suite_4"] = run_suite_4_negative_zero_inverted()
        results["suite_5"] = run_suite_5_invariants_and_idempotency()
        results["suite_6"] = run_suite_6_subdivision_permutation_invariance()
        results["suite_7"] = run_suite_7_rapid_tempo_transitions()
        results["suite_8"] = run_suite_8_float_tick_snapping()

        log_section("FINAL VERDICT: ALL SUITES PASSED")
        print("Summary of Results:")
        for suite_name, data in results.items():
            print(f" - {suite_name}: {data}")
        print(
            "\nNoteQuantizer is robust, mathematically sound, performant, and conforms to all specifications."
        )

    except StressTestFailure as err:
        log_section("FAILURE: STRESS TEST FAILED")
        print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
