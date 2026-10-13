"""Adversarial stress-test harness for PitchToFretMapper.

Tests:
1. High-throughput random streams (20,000+ notes across various pitch distributions)
2. Rapid zigzag patterns (oscillating between MIDI 40 and MIDI 100 at 12, 24, 48 ticks)
3. Monotone sequences, microtonal/narrow ranges, and huge octave leaps
4. Alternating open note / fretted note riffs (pedal note riffs)
5. Invariant checking: type safety, chronological ordering, valid FretTypes, sustain/hopo defaults, jump clamping.
"""

from __future__ import annotations

import random
import sys
import time
from collections.abc import Sequence
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.game_design.pitch_to_fret import PitchToFretMapper  # noqa: E402
from src.game_design.quantizer import QuantizedNote  # noqa: E402
from src.models.chart import ChartNote, FretType  # noqa: E402

VALID_FRETS = {
    FretType.GREEN,
    FretType.RED,
    FretType.YELLOW,
    FretType.BLUE,
    FretType.ORANGE,
    FretType.OPEN,
}


def assert_invariants(notes: Sequence[ChartNote], name: str = "") -> None:
    """Validate all core domain invariants on the output ChartNote sequence."""
    if not notes:
        return

    prev_tick = -1
    prev_fret_val = -1

    for idx, n in enumerate(notes):
        # 1. Type and attribute invariants
        assert isinstance(n, ChartNote), f"[{name}] Note {idx} is not ChartNote: {type(n)}"
        assert n.tick >= 0, f"[{name}] Note {idx} has negative tick: {n.tick}"
        assert n.fret in VALID_FRETS, f"[{name}] Note {idx} has invalid fret: {n.fret}"
        assert n.sustain_length == 0, f"[{name}] Note {idx} sustain != 0: {n.sustain_length}"
        assert n.is_hopo is False, f"[{name}] Note {idx} is_hopo is True"

        # 2. Chronological & fret ordering
        if n.tick < prev_tick:
            raise AssertionError(f"[{name}] Chronological ordering violated at idx {idx}: {n.tick} < {prev_tick}")
        if n.tick == prev_tick and n.fret.value < prev_fret_val:
            raise AssertionError(
                f"[{name}] Fret ordering violated at tick {n.tick}: {n.fret.value} < {prev_fret_val}"
            )

        prev_tick = n.tick
        prev_fret_val = n.fret.value


# ===========================================================================
# SUITE 1: High-Throughput Random Streams (20,000+ notes)
# ===========================================================================


def test_high_throughput_uniform_stream() -> None:
    """Stress test with 25,000 notes uniformly distributed across MIDI 0-127."""
    print("\n--- Running Suite 1A: 25,000 Notes Uniform Distribution ---")
    random.seed(42)
    n_notes = 25000
    # Notes spread across a realistic timeline (e.g. 12-tick average spacing ~ 300,000 ticks)
    notes = [
        QuantizedNote(
            tick=i * 12 + random.randint(0, 6),
            pitch=random.randint(0, 127),
            duration_ticks=24,
            amplitude=round(random.uniform(0.1, 1.0), 2),
        )
        for i in range(n_notes)
    ]

    mapper = PitchToFretMapper()
    t0 = time.perf_counter()
    result = mapper.map_notes(notes)
    elapsed = time.perf_counter() - t0

    throughput = len(notes) / elapsed
    print(f"Processed {len(result)} notes in {elapsed:.3f}s ({throughput:,.1f} notes/sec)")
    assert len(result) == n_notes
    assert_invariants(result, "Uniform Stream")
    assert throughput > 1000, f"Throughput too low: {throughput} notes/sec"


def test_high_throughput_gaussian_stream() -> None:
    """Stress test with 20,000 notes with Gaussian distribution centered at C4 (pitch 60, std=8)."""
    print("\n--- Running Suite 1B: 20,000 Notes Gaussian Distribution ---")
    random.seed(12345)
    n_notes = 20000
    notes = []
    for i in range(n_notes):
        p = int(round(random.gauss(60, 8)))
        p = max(0, min(127, p))
        notes.append(
            QuantizedNote(
                tick=i * 24,
                pitch=p,
                duration_ticks=48,
                amplitude=0.8,
            )
        )

    mapper = PitchToFretMapper()
    t0 = time.perf_counter()
    result = mapper.map_notes(notes)
    elapsed = time.perf_counter() - t0

    throughput = len(notes) / elapsed
    print(f"Processed {len(result)} notes in {elapsed:.3f}s ({throughput:,.1f} notes/sec)")
    assert len(result) == n_notes
    assert_invariants(result, "Gaussian Stream")


def test_high_throughput_bimodal_stream() -> None:
    """Stress test with 20,000 notes alternating between low riff (~45) and high solo (~85)."""
    print("\n--- Running Suite 1C: 20,000 Notes Bimodal (Riff + Solo) ---")
    random.seed(999)
    n_notes = 20000
    notes = []
    for i in range(n_notes):
        # 50% chance of riff (40-52), 50% chance of solo (80-95)
        if random.random() < 0.5:
            p = random.randint(40, 52)
        else:
            p = random.randint(80, 95)
        notes.append(
            QuantizedNote(
                tick=i * 12,
                pitch=p,
                duration_ticks=24,
                amplitude=0.8,
            )
        )

    mapper = PitchToFretMapper()
    t0 = time.perf_counter()
    result = mapper.map_notes(notes)
    elapsed = time.perf_counter() - t0

    throughput = len(notes) / elapsed
    print(f"Processed {len(result)} notes in {elapsed:.3f}s ({throughput:,.1f} notes/sec)")
    assert len(result) == n_notes
    assert_invariants(result, "Bimodal Stream")


def test_high_throughput_sub_bass_heavy_stream() -> None:
    """Stress test with 20,000 notes mostly (< 40) sub-bass open notes."""
    print("\n--- Running Suite 1D: 20,000 Notes Sub-Bass Heavy ---")
    random.seed(777)
    n_notes = 20000
    notes = [
        QuantizedNote(
            tick=i * 24,
            pitch=random.randint(20, 39) if random.random() < 0.85 else random.randint(40, 80),
            duration_ticks=24,
            amplitude=0.9,
        )
        for i in range(n_notes)
    ]

    mapper = PitchToFretMapper()
    t0 = time.perf_counter()
    result = mapper.map_notes(notes)
    elapsed = time.perf_counter() - t0

    throughput = len(notes) / elapsed
    print(f"Processed {len(result)} notes in {elapsed:.3f}s ({throughput:,.1f} notes/sec)")
    assert len(result) == n_notes
    assert_invariants(result, "Sub-Bass Heavy")

    # Majority should be OPEN
    open_count = sum(1 for n in result if n.fret == FretType.OPEN)
    assert open_count > n_notes * 0.80, f"Expected >80% open notes, got {open_count}/{n_notes}"


def test_high_density_burst_stream() -> None:
    """Stress test with 5,000 notes tightly packed inside a single 1536-tick window."""
    print("\n--- Running Suite 1E: 5,000 Notes Burst within Single Window ---")
    random.seed(54321)
    n_notes = 5000
    notes = [
        QuantizedNote(
            tick=random.randint(0, 1536),
            pitch=random.randint(40, 100),
            duration_ticks=12,
            amplitude=0.8,
        )
        for _ in range(n_notes)
    ]

    mapper = PitchToFretMapper()
    t0 = time.perf_counter()
    result = mapper.map_notes(notes)
    elapsed = time.perf_counter() - t0

    throughput = len(notes) / elapsed
    print(f"Dense burst: Processed {len(result)} notes in {elapsed:.3f}s ({throughput:,.1f} notes/sec)")
    assert len(result) == n_notes
    assert_invariants(result, "Dense Burst")


# ===========================================================================
# SUITE 2: Rapid Zigzag Patterns (MIDI 40 <-> MIDI 100 at 12, 24, 48 ticks)
# ===========================================================================


def test_rapid_zigzag_12_ticks() -> None:
    """Verify rapid zigzag oscillating every 12 ticks clamps leaps > 3 frets."""
    print("\n--- Running Suite 2A: Rapid Zigzag Oscillating Every 12 Ticks ---")
    mapper = PitchToFretMapper(max_jump=3, rapid_interval=48)
    n_steps = 100
    # Oscillate between pitch 40 (low) and pitch 100 (high)
    notes = [
        QuantizedNote(
            tick=i * 12,
            pitch=40 if i % 2 == 0 else 100,
            duration_ticks=12,
            amplitude=0.8,
        )
        for i in range(n_steps)
    ]

    result = mapper.map_notes(notes)
    assert len(result) == n_steps
    assert_invariants(result, "Zigzag 12 ticks")

    # In a rapid passage (< 48 ticks), consecutive fretted notes must have |fret_i - fret_{i-1}| <= 3
    for i in range(1, len(result)):
        dt = result[i].tick - result[i - 1].tick
        df = abs(result[i].fret.value - result[i - 1].fret.value)
        assert dt == 12
        assert df <= 3, (
            f"Jump penalty violated at step {i}: fret {result[i-1].fret.value} -> {result[i].fret.value} "
            f"(diff {df} > max_jump 3 at dt={dt})"
        )

    # First note (pitch 40) is Green (0)
    assert result[0].fret == FretType.GREEN
    # Second note (pitch 100) raw would be Orange (4), clamped to Blue (3)
    assert result[1].fret == FretType.BLUE
    # Third note (pitch 40) is Green (0) since |0 - 3| = 3 <= 3
    assert result[2].fret == FretType.GREEN
    print("Pass: All 99 transitions satisfy jump penalty <= 3 at dt=12.")


def test_rapid_zigzag_24_ticks() -> None:
    """Verify rapid zigzag oscillating every 24 ticks clamps leaps > 3 frets."""
    print("\n--- Running Suite 2B: Rapid Zigzag Oscillating Every 24 Ticks ---")
    mapper = PitchToFretMapper(max_jump=3, rapid_interval=48)
    n_steps = 100
    notes = [
        QuantizedNote(
            tick=i * 24,
            pitch=40 if i % 2 == 0 else 100,
            duration_ticks=24,
            amplitude=0.8,
        )
        for i in range(n_steps)
    ]

    result = mapper.map_notes(notes)
    assert len(result) == n_steps
    assert_invariants(result, "Zigzag 24 ticks")

    for i in range(1, len(result)):
        dt = result[i].tick - result[i - 1].tick
        df = abs(result[i].fret.value - result[i - 1].fret.value)
        assert dt == 24
        assert df <= 3, f"Jump penalty violated at step {i}: diff {df} > 3 at dt={dt}"

    assert result[0].fret == FretType.GREEN
    assert result[1].fret == FretType.BLUE
    print("Pass: All 99 transitions satisfy jump penalty <= 3 at dt=24.")


def test_zigzag_48_ticks_allows_full_leaps() -> None:
    """Verify zigzag at 48 ticks (interval >= 48) permits full 4-fret leaps (Green 0 <-> Orange 4)."""
    print("\n--- Running Suite 2C: Zigzag at 48 Ticks (Permits Full 4-Fret Leaps) ---")
    mapper = PitchToFretMapper(max_jump=3, rapid_interval=48)
    n_steps = 20
    notes = [
        QuantizedNote(
            tick=i * 48,
            pitch=40 if i % 2 == 0 else 100,
            duration_ticks=48,
            amplitude=0.8,
        )
        for i in range(n_steps)
    ]

    result = mapper.map_notes(notes)
    assert len(result) == n_steps
    assert_invariants(result, "Zigzag 48 ticks")

    frets = [n.fret for n in result]
    # At interval 48 >= rapid_interval 48, clamping must NOT occur!
    for i, f in enumerate(frets):
        expected = FretType.GREEN if i % 2 == 0 else FretType.ORANGE
        assert f == expected, f"Step {i}: expected {expected}, got {f}"

    # Transitions should be full 4-fret leaps: |4 - 0| == 4
    for i in range(1, len(result)):
        df = abs(result[i].fret.value - result[i - 1].fret.value)
        assert df == 4, f"Step {i}: expected unconstrained leap of 4, got {df}"

    print("Pass: Full 4-fret leaps cleanly permitted when dt >= 48 ticks.")


def test_rapid_zigzag_high_to_low() -> None:
    """Verify rapid zigzag starting with high note (100 -> 40 at 12 ticks) clamps downward."""
    print("\n--- Running Suite 2D: Rapid Zigzag High-to-Low at 12 Ticks ---")
    mapper = PitchToFretMapper(max_jump=3, rapid_interval=48)
    notes = [
        QuantizedNote(tick=0, pitch=100, duration_ticks=12, amplitude=0.8),
        QuantizedNote(tick=12, pitch=40, duration_ticks=12, amplitude=0.8),
        QuantizedNote(tick=24, pitch=100, duration_ticks=12, amplitude=0.8),
        QuantizedNote(tick=36, pitch=40, duration_ticks=12, amplitude=0.8),
    ]

    result = mapper.map_notes(notes)
    assert_invariants(result, "High-to-Low Zigzag")
    # Note 0 (100) -> Orange (4)
    assert result[0].fret == FretType.ORANGE
    # Note 1 (40) raw Green (0), clamped from 4 by max_jump=3 -> Red (1)
    assert result[1].fret == FretType.RED
    # Note 2 (100) raw Orange (4), from 1 to 4 is jump of 3 <= 3 -> Orange (4)
    assert result[2].fret == FretType.ORANGE
    # Note 3 (40) raw Green (0), clamped from 4 by max_jump=3 -> Red (1)
    assert result[3].fret == FretType.RED
    print("Pass: Downward jumps clamped accurately (4 -> 1).")


# ===========================================================================
# SUITE 3: Monotone Sequences, Microtonal Ranges, and Huge Octave Leaps
# ===========================================================================


def test_monotone_sequences() -> None:
    """Test 5,000 identical pitches map consistently to Green (0) without zero-division."""
    print("\n--- Running Suite 3A: Monotone Sequences ---")
    mapper = PitchToFretMapper()

    # Monotone fretted sequence
    notes = [QuantizedNote(tick=i * 24, pitch=60, duration_ticks=24, amplitude=0.8) for i in range(5000)]
    result = mapper.map_notes(notes)
    assert len(result) == 5000
    assert_invariants(result, "Monotone fretted")
    assert all(n.fret == FretType.GREEN for n in result)

    # Monotone sub-bass sequence
    bass_notes = [QuantizedNote(tick=i * 24, pitch=32, duration_ticks=24, amplitude=0.8) for i in range(1000)]
    bass_result = mapper.map_notes(bass_notes)
    assert len(bass_result) == 1000
    assert_invariants(bass_result, "Monotone sub-bass")
    assert all(n.fret == FretType.OPEN for n in bass_result)

    print("Pass: Monotone sequences cleanly mapped without numerical error.")


def test_microtonal_and_narrow_ranges() -> None:
    """Test narrow pitch spans (< 5 semitones) rank-order correctly without exploding."""
    print("\n--- Running Suite 3B: Microtonal & Narrow Pitch Ranges (< 5 semitones) ---")
    mapper = PitchToFretMapper()

    # Span = 1 semitone: pitches 60 and 61 (e.g. semitone trill)
    trill = [
        QuantizedNote(tick=i * 48, pitch=60 if i % 2 == 0 else 61, duration_ticks=48, amplitude=0.8)
        for i in range(10)
    ]
    res_trill = mapper.map_notes(trill)
    assert_invariants(res_trill, "Semitone trill")
    assert [n.fret for n in res_trill] == [
        FretType.GREEN if i % 2 == 0 else FretType.RED for i in range(10)
    ]

    # Span = 2 semitones: pitches 60, 61, 62
    notes_span2 = [
        QuantizedNote(tick=i * 48, pitch=60 + (i % 3), duration_ticks=48, amplitude=0.8)
        for i in range(9)
    ]
    res_span2 = mapper.map_notes(notes_span2)
    assert_invariants(res_span2, "Span 2")
    assert [n.fret for n in res_span2] == [
        FretType(i % 3) for i in range(9)
    ]

    # Span = 4 semitones: pitches 60, 61, 62, 63, 64
    notes_span4 = [
        QuantizedNote(tick=i * 48, pitch=60 + (i % 5), duration_ticks=48, amplitude=0.8)
        for i in range(10)
    ]
    res_span4 = mapper.map_notes(notes_span4)
    assert_invariants(res_span4, "Span 4")
    assert [n.fret for n in res_span4] == [
        FretType(i % 5) for i in range(10)
    ]

    # Span = 4 semitones with only 2 distinct pitches: 60 and 64 (major 3rd trill)
    notes_m3 = [
        QuantizedNote(tick=i * 48, pitch=60 if i % 2 == 0 else 64, duration_ticks=48, amplitude=0.8)
        for i in range(8)
    ]
    res_m3 = mapper.map_notes(notes_m3)
    assert_invariants(res_m3, "Major 3rd trill")
    # Narrow span (< 5) rank orders unique pitches [60, 64] -> indices 0 and 1 (Green and Red)
    assert [n.fret for n in res_m3] == [
        FretType.GREEN if i % 2 == 0 else FretType.RED for i in range(8)
    ]

    print("Pass: Narrow pitch ranges (< 5 semitones) rank-order gracefully.")


def test_huge_octave_leaps_and_boundaries() -> None:
    """Test extreme octave leaps (pitch 40 to 127) and boundary values (0, 39, 40, 127)."""
    print("\n--- Running Suite 3C: Huge Octave Leaps & MIDI Boundaries ---")
    mapper = PitchToFretMapper()

    # Boundaries: 0 (sub-bass), 39 (last sub-bass), 40 (first fretted), 127 (max MIDI)
    boundary_notes = [
        QuantizedNote(tick=0, pitch=0, duration_ticks=48, amplitude=0.5),
        QuantizedNote(tick=96, pitch=39, duration_ticks=48, amplitude=0.5),
        QuantizedNote(tick=192, pitch=40, duration_ticks=48, amplitude=0.5),
        QuantizedNote(tick=288, pitch=127, duration_ticks=48, amplitude=0.5),
    ]
    res_b = mapper.map_notes(boundary_notes)
    assert_invariants(res_b, "Boundaries")
    assert res_b[0].fret == FretType.OPEN
    assert res_b[1].fret == FretType.OPEN
    assert res_b[2].fret == FretType.GREEN
    assert res_b[3].fret == FretType.ORANGE

    # Huge leap across 5 octaves in slow passage (dt=96 >= 48)
    huge_leaps = [
        QuantizedNote(tick=0, pitch=40, duration_ticks=48, amplitude=0.8),
        QuantizedNote(tick=96, pitch=127, duration_ticks=48, amplitude=0.8),
        QuantizedNote(tick=192, pitch=40, duration_ticks=48, amplitude=0.8),
        QuantizedNote(tick=288, pitch=127, duration_ticks=48, amplitude=0.8),
    ]
    res_hl = mapper.map_notes(huge_leaps)
    assert_invariants(res_hl, "Huge leaps slow")
    assert [n.fret for n in res_hl] == [
        FretType.GREEN,
        FretType.ORANGE,
        FretType.GREEN,
        FretType.ORANGE,
    ]

    print("Pass: Huge octave leaps and boundary values handled correctly.")


# ===========================================================================
# SUITE 4: Alternating Open Note / Fretted Note Riffs (Pedal Note Riffs)
# ===========================================================================


def test_alternating_open_and_fretted_pedal_riff() -> None:
    """Test alternating pedal note riffs: sub-bass open note (pitch 36) alternating with fretted melody."""
    print("\n--- Running Suite 4A: Alternating Open / Fretted Pedal Riff ---")
    mapper = PitchToFretMapper()

    # Metal pedal riff: Open (36) -> Fret (60) -> Open (36) -> Fret (64) -> Open (36) -> Fret (67) ...
    # Interval = 24 ticks
    riff_pattern = [
        (36, FretType.OPEN),
        (60, None),  # Fretted
        (36, FretType.OPEN),
        (63, None),  # Fretted
        (36, FretType.OPEN),
        (65, None),  # Fretted
        (36, FretType.OPEN),
        (67, None),  # Fretted
    ]

    notes = [
        QuantizedNote(tick=i * 24, pitch=pitch, duration_ticks=24, amplitude=0.8)
        for i, (pitch, _) in enumerate(riff_pattern)
    ]

    result = mapper.map_notes(notes)
    assert len(result) == len(riff_pattern)
    assert_invariants(result, "Pedal Riff")

    # Every even index note must be OPEN
    for i in range(0, len(result), 2):
        assert result[i].fret == FretType.OPEN, f"Expected OPEN at idx {i}, got {result[i].fret}"

    # Every odd index note must be a valid fretted note [0..4]
    fretted_res = [result[i].fret for i in range(1, len(result), 2)]
    for f in fretted_res:
        assert f in {FretType.GREEN, FretType.RED, FretType.YELLOW, FretType.BLUE, FretType.ORANGE}

    # Melodic contour: 60, 63, 65, 67 should be monotonically non-decreasing frets
    for i in range(len(fretted_res) - 1):
        assert fretted_res[i] <= fretted_res[i + 1]

    print("Pass: Alternating pedal riff cleanly partitions open notes from fretted melodic progression.")


def test_pedal_riff_jump_penalty_behavior() -> None:
    """Investigate jump penalty behavior across open note gaps in rapid pedal riffs."""
    print("\n--- Running Suite 4B: Jump Penalty across Open Note Gaps ---")
    mapper = PitchToFretMapper(max_jump=3, rapid_interval=48)

    # Case 1: Open note between Green and Orange
    # Tick 0: 60 (Green 0)
    # Tick 12: 36 (Open 7)
    # Tick 24: 100 (Orange 4)
    # Tick 36: 36 (Open 7)
    # Tick 48: 60 (Green 0)
    notes = [
        QuantizedNote(tick=0, pitch=60, duration_ticks=12, amplitude=0.8),
        QuantizedNote(tick=12, pitch=36, duration_ticks=12, amplitude=0.8),
        QuantizedNote(tick=24, pitch=100, duration_ticks=12, amplitude=0.8),
        QuantizedNote(tick=36, pitch=36, duration_ticks=12, amplitude=0.8),
        QuantizedNote(tick=48, pitch=60, duration_ticks=12, amplitude=0.8),
    ]

    result = mapper.map_notes(notes)
    assert_invariants(result, "Open note reset investigation")
    print(f"Notes produced: {[(n.tick, n.fret.name) for n in result]}")

    # Note 0: Green
    assert result[0].fret == FretType.GREEN
    # Note 1: OPEN
    assert result[1].fret == FretType.OPEN
    # Note 2: Orange (4) - because open note at tick 12 reset anchor
    print(f"Tick 24 fret: {result[2].fret.name} (anchor reset behavior confirmed)")
    assert result[2].fret == FretType.ORANGE
    assert result[3].fret == FretType.OPEN
    assert result[4].fret == FretType.GREEN


def test_fretted_pedal_note_riff() -> None:
    """Test pedal note riff where pedal note is a fretted bass note (pitch 40) rather than open."""
    print("\n--- Running Suite 4C: Fretted Pedal Note Riff (Pitch 40) ---")
    mapper = PitchToFretMapper(max_jump=3, rapid_interval=48)

    # Tick 0: 40 (Pedal, Green 0)
    # Tick 12: 100 (High note, raw Orange 4) -> Clamped to Blue 3!
    # Tick 24: 40 (Pedal, Green 0) -> Jump |0 - 3| = 3 <= 3 -> Green 0!
    # Tick 36: 100 (High note, raw Orange 4) -> Clamped to Blue 3!
    notes = [
        QuantizedNote(tick=i * 12, pitch=40 if i % 2 == 0 else 100, duration_ticks=12, amplitude=0.8)
        for i in range(8)
    ]

    result = mapper.map_notes(notes)
    assert_invariants(result, "Fretted pedal riff")
    frets = [n.fret for n in result]
    print(f"Fretted pedal frets: {[f.name for f in frets]}")

    expected = [
        FretType.GREEN,
        FretType.BLUE,
        FretType.GREEN,
        FretType.BLUE,
        FretType.GREEN,
        FretType.BLUE,
        FretType.GREEN,
        FretType.BLUE,
    ]
    assert frets == expected, f"Expected {expected}, got {frets}"
    print("Pass: Fretted pedal riff properly enforces jump penalty clamping to Blue.")


# ===========================================================================
# SUITE 5: Simultaneous Chords with Rapid Jump Clamping
# ===========================================================================


def test_chords_with_rapid_jump_clamping() -> None:
    """Verify chords in rapid passages handle jump clamping cleanly."""
    print("\n--- Running Suite 5: Chords with Rapid Jump Clamping ---")
    mapper = PitchToFretMapper(max_jump=3, rapid_interval=48)

    # Tick 0: single note 60 (Green 0)
    # Tick 12: triad 85, 95, 100 (raw frets 2, 3, 4 or 3, 4)
    # Interval = 12 < 48
    notes = [
        QuantizedNote(tick=0, pitch=60, duration_ticks=12, amplitude=0.8),
        QuantizedNote(tick=12, pitch=85, duration_ticks=12, amplitude=0.8),
        QuantizedNote(tick=12, pitch=95, duration_ticks=12, amplitude=0.8),
        QuantizedNote(tick=12, pitch=100, duration_ticks=12, amplitude=0.8),
        QuantizedNote(tick=24, pitch=60, duration_ticks=12, amplitude=0.8),
    ]

    result = mapper.map_notes(notes)
    assert_invariants(result, "Chords with jump clamping")

    t12_notes = [n for n in result if n.tick == 12]
    assert len(t12_notes) == 3
    # All frets at tick 12 must be <= 3 (clamped from 0)
    for n in t12_notes:
        assert n.fret.value <= 3, f"Fret at tick 12 exceeded clamp: {n.fret.value}"

    print(f"Tick 12 frets: {[n.fret.name for n in t12_notes]}")
    print("Pass: Chords with jump clamping cleanly executed without exceptions.")


# ===========================================================================
# SUITE 6: Extreme Parameter Settings
# ===========================================================================


def test_extreme_parameters() -> None:
    """Test extreme but valid parameter values (max_jump=1, window_ticks=1, open_threshold=0, 127)."""
    print("\n--- Running Suite 6: Extreme Parameter Settings ---")

    # 1. max_jump = 1: strict clamping
    mapper_mj1 = PitchToFretMapper(max_jump=1, rapid_interval=48)
    notes_mj1 = [
        QuantizedNote(tick=0, pitch=60, duration_ticks=12, amplitude=0.8),
        QuantizedNote(tick=12, pitch=100, duration_ticks=12, amplitude=0.8),
    ]
    res_mj1 = mapper_mj1.map_notes(notes_mj1)
    assert_invariants(res_mj1, "max_jump=1")
    assert res_mj1[0].fret == FretType.GREEN
    assert res_mj1[1].fret == FretType.RED  # 0 + 1 = 1 (Red)

    # 2. window_ticks = 1: minimum window
    mapper_w1 = PitchToFretMapper(window_ticks=1)
    notes_w1 = [
        QuantizedNote(tick=0, pitch=60, duration_ticks=24, amplitude=0.8),
        QuantizedNote(tick=96, pitch=80, duration_ticks=24, amplitude=0.8),
    ]
    res_w1 = mapper_w1.map_notes(notes_w1)
    assert_invariants(res_w1, "window_ticks=1")
    # Isolated single note in 1-tick window has span=0 -> Green
    assert res_w1[0].fret == FretType.GREEN
    assert res_w1[1].fret == FretType.GREEN

    # 3. open_threshold = 0: no notes are OPEN (even pitch 0 is fretted)
    mapper_ot0 = PitchToFretMapper(open_threshold=0)
    notes_ot0 = [
        QuantizedNote(tick=0, pitch=0, duration_ticks=48, amplitude=0.8),
        QuantizedNote(tick=96, pitch=127, duration_ticks=48, amplitude=0.8),
    ]
    res_ot0 = mapper_ot0.map_notes(notes_ot0)
    assert_invariants(res_ot0, "open_threshold=0")
    assert res_ot0[0].fret == FretType.GREEN  # Pitch 0 is lowest fretted note
    assert res_ot0[1].fret == FretType.ORANGE  # Pitch 127 is highest fretted note

    # 4. open_threshold = 127: all notes < 127 are OPEN
    mapper_ot127 = PitchToFretMapper(open_threshold=127)
    notes_ot127 = [
        QuantizedNote(tick=0, pitch=60, duration_ticks=48, amplitude=0.8),
        QuantizedNote(tick=96, pitch=126, duration_ticks=48, amplitude=0.8),
        QuantizedNote(tick=192, pitch=127, duration_ticks=48, amplitude=0.8),
    ]
    res_ot127 = mapper_ot127.map_notes(notes_ot127)
    assert_invariants(res_ot127, "open_threshold=127")
    assert res_ot127[0].fret == FretType.OPEN
    assert res_ot127[1].fret == FretType.OPEN
    assert res_ot127[2].fret == FretType.GREEN  # Pitch 127 is >= 127 -> GREEN

    print("Pass: Extreme parameters (max_jump=1, window=1, thresholds 0/127) operate correctly.")


# ===========================================================================
# SUITE 7: Simultaneous Open and Fretted Notes at Same Tick
# ===========================================================================


def test_simultaneous_open_and_fretted_notes() -> None:
    """Test coexisting Open and fretted notes at identical tick (polyphonic audio artifact)."""
    print("\n--- Running Suite 7: Simultaneous Open and Fretted Notes ---")
    mapper = PitchToFretMapper(max_jump=3, rapid_interval=48)

    # Tick 0 has both sub-bass (36) and fretted (60)
    # Tick 12 has high fretted (100)
    notes = [
        QuantizedNote(tick=0, pitch=36, duration_ticks=24, amplitude=0.8),
        QuantizedNote(tick=0, pitch=60, duration_ticks=24, amplitude=0.8),
        QuantizedNote(tick=12, pitch=100, duration_ticks=24, amplitude=0.8),
    ]

    result = mapper.map_notes(notes)
    assert_invariants(result, "Simultaneous Open and Fretted")

    assert len(result) == 3
    # Tick 0 notes: OPEN and GREEN
    t0_notes = [n for n in result if n.tick == 0]
    assert [n.fret for n in t0_notes] == [FretType.GREEN, FretType.OPEN]

    # Tick 12 note: since Tick 0 had fretted Green (0), Tick 12 (raw Orange 4) is clamped to Blue (3)!
    t12_notes = [n for n in result if n.tick == 12]
    assert len(t12_notes) == 1
    assert t12_notes[0].fret == FretType.BLUE
    print("Pass: Simultaneous open and fretted note correctly anchors rapid jump penalty.")


# ===========================================================================
# SUITE 8: Reverse Chronological and Shuffled Input Order
# ===========================================================================


def test_shuffled_and_reverse_input_orders() -> None:
    """Verify results are deterministic regardless of input ordering."""
    print("\n--- Running Suite 8: Input Order Determinism ---")
    mapper = PitchToFretMapper()

    canonical = [
        QuantizedNote(tick=i * 24, pitch=50 + (i % 15), duration_ticks=24, amplitude=0.8)
        for i in range(200)
    ]
    ref_result = mapper.map_notes(canonical)

    # Reverse order
    reversed_notes = list(reversed(canonical))
    rev_result = mapper.map_notes(reversed_notes)
    assert rev_result == ref_result, "Reversed input yielded different result!"

    # Shuffled order
    shuffled_notes = list(canonical)
    random.seed(112233)
    random.shuffle(shuffled_notes)
    shuf_result = mapper.map_notes(shuffled_notes)
    assert shuf_result == ref_result, "Shuffled input yielded different result!"

    print("Pass: Deterministic output for canonical, reversed, and shuffled inputs.")


# ===========================================================================
# SUITE 9: Scaled 50,000 Note Ultra Stress Stream
# ===========================================================================


def test_scaled_50k_stream() -> None:
    """Ultra-scale stress test with 50,000 notes across 1,000 measures."""
    print("\n--- Running Suite 9: 50,000 Notes Ultra Stream ---")
    random.seed(8888)
    n_notes = 50000
    notes = [
        QuantizedNote(
            tick=i * 12 + random.randint(0, 4),
            pitch=random.randint(25, 105),
            duration_ticks=24,
            amplitude=round(random.uniform(0.2, 0.9), 2),
        )
        for i in range(n_notes)
    ]

    mapper = PitchToFretMapper()
    t0 = time.perf_counter()
    result = mapper.map_notes(notes)
    elapsed = time.perf_counter() - t0

    throughput = len(notes) / elapsed
    print(f"Processed {len(result)} notes in {elapsed:.3f}s ({throughput:,.1f} notes/sec)")
    assert len(result) == n_notes
    assert_invariants(result, "50k Ultra Stream")
    assert throughput > 10000


# ===========================================================================
# MAIN RUNNER
# ===========================================================================


def main() -> None:
    print("=================================================================")
    print("ADVERSARIAL STRESS TEST HARNESS: PitchToFretMapper")
    print("=================================================================")

    start_time = time.perf_counter()
    failures: list[str] = []

    tests = [
        # Suite 1
        ("Suite 1A: 25k Uniform Stream", test_high_throughput_uniform_stream),
        ("Suite 1B: 20k Gaussian Stream", test_high_throughput_gaussian_stream),
        ("Suite 1C: 20k Bimodal Stream", test_high_throughput_bimodal_stream),
        ("Suite 1D: 20k Sub-Bass Heavy Stream", test_high_throughput_sub_bass_heavy_stream),
        ("Suite 1E: 5k Dense Burst Stream", test_high_density_burst_stream),
        # Suite 2
        ("Suite 2A: Rapid Zigzag 12 ticks", test_rapid_zigzag_12_ticks),
        ("Suite 2B: Rapid Zigzag 24 ticks", test_rapid_zigzag_24_ticks),
        ("Suite 2C: Zigzag 48 ticks unconstrained", test_zigzag_48_ticks_allows_full_leaps),
        ("Suite 2D: Rapid Zigzag High-to-Low", test_rapid_zigzag_high_to_low),
        # Suite 3
        ("Suite 3A: Monotone Sequences", test_monotone_sequences),
        ("Suite 3B: Microtonal & Narrow Ranges", test_microtonal_and_narrow_ranges),
        ("Suite 3C: Huge Octave Leaps & Boundaries", test_huge_octave_leaps_and_boundaries),
        # Suite 4
        ("Suite 4A: Alternating Open/Fretted Pedal Riff", test_alternating_open_and_fretted_pedal_riff),
        ("Suite 4B: Open Gap Jump Penalty", test_pedal_riff_jump_penalty_behavior),
        ("Suite 4C: Fretted Pedal Riff", test_fretted_pedal_note_riff),
        # Suite 5 - 9
        ("Suite 5: Chords with Rapid Jump Clamping", test_chords_with_rapid_jump_clamping),
        ("Suite 6: Extreme Parameters", test_extreme_parameters),
        ("Suite 7: Simultaneous Open and Fretted", test_simultaneous_open_and_fretted_notes),
        ("Suite 8: Input Order Determinism", test_shuffled_and_reverse_input_orders),
        ("Suite 9: 50k Ultra Stream", test_scaled_50k_stream),
    ]

    for name, test_fn in tests:
        try:
            test_fn()
        except Exception as e:
            print(f"FAILED: {name}: {e}", file=sys.stderr)
            failures.append(f"{name}: {e}")

    total_elapsed = time.perf_counter() - start_time
    print("\n=================================================================")
    print(f"HARNESS EXECUTION COMPLETE IN {total_elapsed:.2f}s")
    if failures:
        print(f"FAILURES DETECTED ({len(failures)}):")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    else:
        print("ALL ADVERSARIAL STRESS TESTS PASSED SUCCESSFULLY!")
        print("=================================================================")


if __name__ == "__main__":
    main()

