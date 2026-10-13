"""Empirical Adversarial Stress Test Harness for Milestone 4 (Game Design Engine).

Tests HopoEngine, SustainProcessor, and StarPowerGenerator against:
1. Boundary interval matrix (0, 1, 12, 24, 32, 48, 64, 65, 66, 96, 192, 768 ticks)
2. Rapid repetitive trills (0-1-0-1, 0-0-1-1-2-2, 0-0-0-1-1-1)
3. Massive sustain overlaps and micro-interval collision clamping
4. StarPowerGenerator alignment over long tracks with large silent gaps
5. Negative parameters validating ValueError exceptions
6. Ultra-dense 50,000+ note streams and throughput benchmarks
7. Invariant fuzzing on randomized note streams
"""

from __future__ import annotations

import random
import sys
import time
from pathlib import Path
from typing import Final

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.game_design.hopo_engine import HopoEngine  # noqa: E402
from src.game_design.star_power_generator import StarPowerGenerator  # noqa: E402
from src.game_design.sustain_processor import SustainProcessor  # noqa: E402
from src.models import ChartNote, FretType  # noqa: E402


# ---------------------------------------------------------------------------
# Test Utilities & Reporters
# ---------------------------------------------------------------------------
class TestStats:
    def __init__(self) -> None:
        self.passed: int = 0
        self.failed: int = 0
        self.benchmarks: list[tuple[str, float, str]] = []

    def assert_true(self, condition: bool, description: str) -> None:
        if condition:
            self.passed += 1
            print(f"  ✓ {description}")
        else:
            self.failed += 1
            print(f"  ✗ FAILED: {description}")

    def assert_raises(
        self,
        exc_type: type[Exception],
        func: object,
        description: str,
        *args: object,
        **kwargs: object,
    ) -> None:
        try:
            if callable(func):
                func(*args, **kwargs)
            self.failed += 1
            print(f"  ✗ FAILED (expected {exc_type.__name__}): {description}")
        except exc_type:
            self.passed += 1
            print(f"  ✓ {description} (raised {exc_type.__name__})")
        except Exception as e:
            self.failed += 1
            print(f"  ✗ FAILED (unexpected exception {type(e).__name__}): {description}")

    def record_bench(self, name: str, elapsed: float, notes_or_items: str) -> None:
        self.benchmarks.append((name, elapsed, notes_or_items))


STATS = TestStats()


# ---------------------------------------------------------------------------
# SUITE 1: HopoEngine Boundary & Micro-Interval Truth Matrix
# ---------------------------------------------------------------------------
def run_suite_1_hopo_boundary() -> None:
    print("\n" + "=" * 70)
    print("SUITE 1: HopoEngine Boundary & Micro-Interval Truth Matrix")
    print("=" * 70)

    engine = HopoEngine(hopo_threshold=65)

    # Micro-intervals under test
    intervals = [1, 12, 24, 32, 48, 64, 65, 66, 96, 192, 768]

    # Test Fret Variation (0 -> 1)
    print("\n--- Subtest 1.1: Fret Change Transitions (0 -> 1) ---")
    for iv in intervals:
        notes = [
            ChartNote(tick=0, fret=FretType.GREEN),
            ChartNote(tick=iv, fret=FretType.RED),
        ]
        res = engine.process(notes)
        expected_hopo = iv <= 65
        STATS.assert_true(
            res[0].is_hopo is False and res[1].is_hopo is expected_hopo,
            f"Interval {iv:3d} ticks (0->1): note[0]=Strum, note[1]={'HOPO' if expected_hopo else 'Strum'}",
        )

    # Test Identical Fret Repeat (0 -> 0)
    print("\n--- Subtest 1.2: Identical Fret Repetition (0 -> 0) ---")
    for iv in intervals:
        notes = [
            ChartNote(tick=0, fret=FretType.GREEN),
            ChartNote(tick=iv, fret=FretType.GREEN),
        ]
        res = engine.process(notes)
        STATS.assert_true(
            res[0].is_hopo is False and res[1].is_hopo is False,
            f"Interval {iv:3d} ticks (0->0): BOTH forced Strum (no HOPO)",
        )

    # Test Open Note (7) transitions
    print("\n--- Subtest 1.3: Open Note (7) Transitions ---")
    # Open -> Fretted
    res_open_fret = engine.process(
        [
            ChartNote(tick=0, fret=FretType.OPEN),
            ChartNote(tick=48, fret=FretType.GREEN),
        ]
    )
    STATS.assert_true(
        res_open_fret[0].is_hopo is False and res_open_fret[1].is_hopo is True,
        "Open (7) -> Green (0) at 48 ticks: note[1] is natural HOPO",
    )

    # Fretted -> Open
    res_fret_open = engine.process(
        [
            ChartNote(tick=0, fret=FretType.GREEN),
            ChartNote(tick=48, fret=FretType.OPEN),
        ]
    )
    STATS.assert_true(
        res_fret_open[0].is_hopo is False and res_fret_open[1].is_hopo is True,
        "Green (0) -> Open (7) at 48 ticks: note[1] is natural HOPO",
    )

    # Open -> Open (repeated)
    res_open_open = engine.process(
        [
            ChartNote(tick=0, fret=FretType.OPEN),
            ChartNote(tick=48, fret=FretType.OPEN),
        ]
    )
    STATS.assert_true(
        res_open_open[0].is_hopo is False and res_open_open[1].is_hopo is False,
        "Open (7) -> Open (7) at 48 ticks: BOTH forced Strum",
    )

    # Test Chords vs Singles
    print("\n--- Subtest 1.4: Chords vs Single Notes ---")
    # Single -> Chord
    res_single_chord = engine.process(
        [
            ChartNote(tick=0, fret=FretType.GREEN),
            ChartNote(tick=48, fret=FretType.RED),
            ChartNote(tick=48, fret=FretType.YELLOW),
        ]
    )
    STATS.assert_true(
        res_single_chord[0].is_hopo is False
        and res_single_chord[1].is_hopo is False
        and res_single_chord[2].is_hopo is False,
        "Single -> Chord (Red+Yellow) at 48 ticks: chord notes are forced Strum",
    )

    # Chord -> Single (Disjoint fret)
    res_chord_single_disjoint = engine.process(
        [
            ChartNote(tick=0, fret=FretType.GREEN),
            ChartNote(tick=0, fret=FretType.RED),
            ChartNote(tick=48, fret=FretType.YELLOW),
        ]
    )
    STATS.assert_true(
        res_chord_single_disjoint[2].is_hopo is True,
        "Chord (Green+Red) -> Yellow at 48 ticks: Yellow is natural HOPO",
    )

    # Chord -> Single (Overlapping fret: player holds Green)
    res_chord_single_overlap = engine.process(
        [
            ChartNote(tick=0, fret=FretType.GREEN),
            ChartNote(tick=0, fret=FretType.RED),
            ChartNote(tick=48, fret=FretType.GREEN),
        ]
    )
    STATS.assert_true(
        res_chord_single_overlap[2].is_hopo is False,
        "Chord (Green+Red) -> Green at 48 ticks: Green is forced Strum (repetition)",
    )

    # Test add_force_modifiers
    print("\n--- Subtest 1.5: Force Modifiers Injection ---")
    mod_test_notes = [
        ChartNote(tick=0, fret=FretType.GREEN),
        ChartNote(tick=48, fret=FretType.GREEN),  # rapid repeat -> should get STRUM_FORCE (6)
        ChartNote(
            tick=96, fret=FretType.RED
        ),  # rapid fret shift -> natural HOPO (no modifier needed)
    ]
    res_mods = engine.add_force_modifiers(mod_test_notes)
    has_strum_force = any(n.fret == FretType.STRUM_FORCE and n.tick == 48 for n in res_mods)
    has_no_mod_at_96 = not any(
        n.fret in (FretType.HOPO_FORCE, FretType.STRUM_FORCE) and n.tick == 96 for n in res_mods
    )
    STATS.assert_true(
        has_strum_force and has_no_mod_at_96,
        "add_force_modifiers correctly injected STRUM_FORCE at tick 48 on repeated fret",
    )


# ---------------------------------------------------------------------------
# SUITE 2: Rapid Repetitive Trills & Multi-Fret Cascades
# ---------------------------------------------------------------------------
def run_suite_2_trills() -> None:
    print("\n" + "=" * 70)
    print("SUITE 2: Rapid Repetitive Trills & Multi-Fret Cascades")
    print("=" * 70)

    engine = HopoEngine(hopo_threshold=65)

    # 1. High-frequency trill 0-1-0-1-0-1 at 24 ticks (1/32 notes)
    print("\n--- Subtest 2.1: Alternating Trill (0-1-0-1-0-1-0-1) at 24 ticks ---")
    trill_notes = [
        ChartNote(tick=i * 24, fret=FretType.GREEN if i % 2 == 0 else FretType.RED)
        for i in range(16)
    ]
    res_trill = engine.process(trill_notes)
    STATS.assert_true(
        res_trill[0].is_hopo is False and all(n.is_hopo is True for n in res_trill[1:]),
        "16-note trill (24 ticks): note 0 is Strum, notes 1..15 are all HOPO",
    )

    # 2. Double-strum trill 0-0-1-1-2-2-0-0 at 24 ticks
    print("\n--- Subtest 2.2: Doublet Repetition (0-0-1-1-2-2-3-3-4-4) at 24 ticks ---")
    pattern = [0, 0, 1, 1, 2, 2, 3, 3, 4, 4]
    doublet_notes = [ChartNote(tick=i * 24, fret=FretType(pattern[i])) for i in range(len(pattern))]
    res_doublet = engine.process(doublet_notes)
    # Expected:
    # i=0 (0): Strum (first note)
    # i=1 (0): Strum (repeat 0)
    # i=2 (1): HOPO (changed to 1)
    # i=3 (1): Strum (repeat 1)
    # i=4 (2): HOPO (changed to 2)
    # i=5 (2): Strum (repeat 2)
    # i=6 (3): HOPO (changed to 3)
    # i=7 (3): Strum (repeat 3)
    # i=8 (4): HOPO (changed to 4)
    # i=9 (4): Strum (repeat 4)
    expected_hopos = [False, False, True, False, True, False, True, False, True, False]
    actual_hopos = [n.is_hopo for n in res_doublet]
    STATS.assert_true(
        actual_hopos == expected_hopos,
        f"Doublet trill pattern: {actual_hopos} == {expected_hopos}",
    )

    # Check STRUM_FORCE modifier on doublets
    res_doublet_mods = engine.add_force_modifiers(doublet_notes)
    strum_mod_ticks = [n.tick for n in res_doublet_mods if n.fret == FretType.STRUM_FORCE]
    expected_strum_ticks = [24, 72, 120, 168, 216]
    STATS.assert_true(
        strum_mod_ticks == expected_strum_ticks,
        f"STRUM_FORCE modifiers on doublets at ticks: {strum_mod_ticks} == {expected_strum_ticks}",
    )

    # 3. Triplets 0-0-0-1-1-1 at 32 ticks
    print("\n--- Subtest 2.3: Triplet Repetition (0-0-0-1-1-1) at 32 ticks ---")
    triplet_pattern = [0, 0, 0, 1, 1, 1]
    triplet_notes = [
        ChartNote(tick=i * 32, fret=FretType(triplet_pattern[i]))
        for i in range(len(triplet_pattern))
    ]
    res_triplet = engine.process(triplet_notes)
    # Expected: [Strum, Strum, Strum, HOPO, Strum, Strum]
    exp_triplet = [False, False, False, True, False, False]
    STATS.assert_true(
        [n.is_hopo for n in res_triplet] == exp_triplet,
        f"Triplet pattern HOPOs: {[n.is_hopo for n in res_triplet]} == {exp_triplet}",
    )

    # 4. Chromatic runs up and down (0-1-2-3-4-3-2-1-0) at 48 ticks
    print("\n--- Subtest 2.4: Ascending & Descending Scale (0-1-2-3-4-3-2-1-0) at 48 ticks ---")
    scale_frets = [0, 1, 2, 3, 4, 3, 2, 1, 0]
    scale_notes = [
        ChartNote(tick=i * 48, fret=FretType(scale_frets[i])) for i in range(len(scale_frets))
    ]
    res_scale = engine.process(scale_notes)
    STATS.assert_true(
        res_scale[0].is_hopo is False and all(n.is_hopo is True for n in res_scale[1:]),
        "Full scale traversal (48 ticks): note 0 is Strum, all subsequent notes are HOPOs",
    )


# ---------------------------------------------------------------------------
# SUITE 3: Sustain Processor Collision Clamping & Micro-Interval Release
# ---------------------------------------------------------------------------
def run_suite_3_sustain_clamping() -> None:
    print("\n" + "=" * 70)
    print("SUITE 3: Sustain Processor Collision Clamping & Micro-Intervals")
    print("=" * 70)

    proc = SustainProcessor(min_sustain_ticks=90, release_margin=24)

    # 1. Isolated note durations
    print("\n--- Subtest 3.1: Isolated Notes Threshold Cutoff ---")
    test_durations = [
        (0, 0),
        (24, 0),
        (89, 0),
        (90, 66),  # 90 - 24
        (91, 67),  # 91 - 24
        (192, 168),  # 192 - 24
        (384, 360),  # 384 - 24
        (768, 744),  # 768 - 24
        (10000, 9976),  # 10000 - 24
    ]
    for raw_dur, exp_sus in test_durations:
        note = ChartNote(tick=0, fret=FretType.GREEN, sustain_length=raw_dur)
        res = proc.process([note])
        STATS.assert_true(
            res[0].sustain_length == exp_sus,
            f"Isolated raw duration {raw_dur:5d} -> sustain {res[0].sustain_length} (expected {exp_sus})",
        )

    # 2. Massive sustain collision clamping on micro-intervals
    print("\n--- Subtest 3.2: Massive Sustain Overlap Micro-Interval Clamping ---")
    # Note at tick 0 has raw duration 10,000. Next note at distance d.
    micro_distances = [
        (1, 0),  # max(0, 1 - 24) = 0
        (12, 0),  # max(0, 12 - 24) = 0
        (24, 0),  # max(0, 24 - 24) = 0
        (25, 1),  # 25 - 24 = 1
        (48, 24),  # 48 - 24 = 24
        (65, 41),  # 65 - 24 = 41
        (90, 66),  # 90 - 24 = 66
        (192, 168),  # 192 - 24 = 168
        (500, 476),  # 500 - 24 = 476
    ]
    for dist, exp_clamped in micro_distances:
        notes = [
            ChartNote(tick=0, fret=FretType.GREEN, sustain_length=10000),
            ChartNote(tick=dist, fret=FretType.RED, sustain_length=0),
        ]
        res = proc.process(notes)
        actual_sustain = res[0].sustain_length
        tail_tick = res[0].tick + actual_sustain
        gap_to_next = dist - tail_tick
        STATS.assert_true(
            actual_sustain == exp_clamped and (dist <= 24 or gap_to_next == 24),
            f"Dist {dist:3d} ticks (raw=10000): clamped sustain={actual_sustain:3d} (tail={tail_tick}, gap={gap_to_next})",
        )

    # 3. Dense cascade of 10 massive sustains
    print("\n--- Subtest 3.3: 10-Note Cascade of 10,000-Tick Sustains Spaced by 48 Ticks ---")
    cascade_notes = [
        ChartNote(tick=i * 48, fret=FretType(i % 5), sustain_length=10000) for i in range(10)
    ]
    res_cascade = proc.process(cascade_notes)
    # Notes 0..8 have next note at 48 ticks -> clamped to 48 - 24 = 24
    intermediate_ok = all(n.sustain_length == 24 for n in res_cascade[:-1])
    # Terminal note 9 has no next note -> retains 10000 - 24 = 9976
    terminal_ok = res_cascade[-1].sustain_length == 9976
    STATS.assert_true(
        intermediate_ok and terminal_ok,
        "Cascade: notes 0..8 clamped to 24 ticks (48-24), terminal note retains 9976 ticks (10000-24)",
    )

    # 4. Chord simultaneous notes sustain preservation
    print("\n--- Subtest 3.4: Chords with Heterogeneous Sustains at Same Tick ---")
    chord_notes = [
        ChartNote(tick=0, fret=FretType.GREEN, sustain_length=500),
        ChartNote(tick=0, fret=FretType.RED, sustain_length=300),
        ChartNote(tick=0, fret=FretType.YELLOW, sustain_length=50),  # < 90 -> 0
        ChartNote(tick=192, fret=FretType.BLUE, sustain_length=0),
    ]
    res_chord = proc.process(chord_notes)
    # Tick 0 has next note at 192 -> max allowed = 192 - 24 = 168
    # Green (500) -> min(476, 168) = 168
    # Red (300) -> min(276, 168) = 168
    # Yellow (50) -> 0 (< 90)
    exp_sustains = [168, 168, 0, 0]
    actual_sustains = [n.sustain_length for n in res_chord]
    STATS.assert_true(
        actual_sustains == exp_sustains,
        f"Chord simultaneous sustains: {actual_sustains} == {exp_sustains}",
    )

    # 5. Heterogeneous duration sequence and mapping formats
    print("\n--- Subtest 3.5: Heterogeneous Duration Input Formats ---")
    sample_notes = [
        ChartNote(tick=0, fret=FretType.GREEN, sustain_length=0),
        ChartNote(tick=0, fret=FretType.RED, sustain_length=0),
        ChartNote(tick=192, fret=FretType.YELLOW, sustain_length=0),
    ]

    # Passing Sequence[int]
    res_seq = proc.process(sample_notes, durations=[500, 300, 200])
    STATS.assert_true(
        res_seq[0].sustain_length == 168
        and res_seq[1].sustain_length == 168
        and res_seq[2].sustain_length == 176,
        "Sequence[int] durations processed correctly",
    )

    # Passing Mapping[(tick, fret), dur]
    res_map_fret = proc.process(
        sample_notes,
        durations={
            (0, int(FretType.GREEN)): 500,
            (0, int(FretType.RED)): 80,
            (192, int(FretType.YELLOW)): 200,
        },
    )
    STATS.assert_true(
        res_map_fret[0].sustain_length == 168
        and res_map_fret[1].sustain_length == 0
        and res_map_fret[2].sustain_length == 176,
        "Mapping[tuple[int, int], int] durations processed correctly",
    )

    # Passing Mapping[tick, dur]
    res_map_tick = proc.process(sample_notes, durations={0: 500, 192: 200})
    STATS.assert_true(
        res_map_tick[0].sustain_length == 168
        and res_map_tick[1].sustain_length == 168
        and res_map_tick[2].sustain_length == 176,
        "Mapping[int, int] (by tick) durations processed correctly",
    )


# ---------------------------------------------------------------------------
# SUITE 4: StarPowerGenerator Alignment & Silent Gaps
# ---------------------------------------------------------------------------
def run_suite_4_star_power() -> None:
    print("\n" + "=" * 70)
    print("SUITE 4: StarPowerGenerator Alignment & Silent Gaps")
    print("=" * 70)

    gen = StarPowerGenerator(
        measure_ticks=768,
        interval_measures=16,
        phrase_length_measures=2,
        min_notes=4,
    )

    phrase_len = 2 * 768  # 1536 ticks

    # 1. Empty and under-density charts
    print("\n--- Subtest 4.1: Empty and Under-Density Handling ---")
    STATS.assert_true(gen.generate([]) == [], "Empty notes sequence returns empty phrases []")

    sparse_3_notes = [ChartNote(tick=i * 192, fret=FretType.GREEN) for i in range(3)]
    STATS.assert_true(
        gen.generate(sparse_3_notes) == [],
        "Chart with 3 notes (< min_notes=4) returns empty phrases []",
    )

    # 2. Long track with multiple large silent gaps
    print("\n--- Subtest 4.2: Multiple Silent Gaps Avoidance & Note Alignment ---")
    # Section 1: Measures 0-3 (ticks 0 to 3072) - 16 dense notes
    sec1 = [ChartNote(tick=i * 192, fret=FretType(i % 5)) for i in range(16)]

    # Silent gap of 40 measures (ticks 3072 to 33792)

    # Section 2: Measures 44-47 (ticks 33792 to 36864) - 16 dense notes
    sec2 = [ChartNote(tick=33792 + i * 192, fret=FretType(i % 5)) for i in range(16)]

    # Silent gap of 60 measures (ticks 36864 to 82944)

    # Section 3: Measures 108-111 (ticks 82944 to 86016) - 16 dense notes
    sec3 = [ChartNote(tick=82944 + i * 192, fret=FretType(i % 5)) for i in range(16)]

    long_track = sec1 + sec2 + sec3
    phrases = gen.generate(long_track)

    print(f"  Generated {len(phrases)} Star Power phrases:")
    for idx, p in enumerate(phrases):
        print(
            f"    Phrase {idx}: tick={p.tick:6d}, length={p.length:5d} (spans ticks {p.tick} to {p.tick + p.length})"
        )

    # Invariants check:
    # 1. Exactly 3 phrases (one per active section)
    # 2. Each phrase starts exactly at or within the active section
    # 3. No phrase falls in the silent gaps [3072, 33792) or [36864, 82944)
    # 4. Phrases never overlap
    STATS.assert_true(
        len(phrases) == 3,
        f"Generated exactly 3 phrases (one per active section), got {len(phrases)}",
    )

    all_start_on_note = all(any(n.tick == p.tick for n in long_track) for p in phrases)
    STATS.assert_true(
        all_start_on_note,
        "Every Star Power phrase starts exactly on an existing note tick",
    )

    gap_1_empty = not any(3072 <= p.tick < 33792 for p in phrases)
    gap_2_empty = not any(36864 <= p.tick < 82944 for p in phrases)
    STATS.assert_true(
        gap_1_empty and gap_2_empty,
        "No Star Power phrases allocated within silent gaps",
    )

    no_overlap = all(
        phrases[i].tick + phrases[i].length <= phrases[i + 1].tick for i in range(len(phrases) - 1)
    )
    STATS.assert_true(
        no_overlap,
        "All Star Power phrases are strictly non-overlapping",
    )

    all_correct_length = all(p.length == phrase_len for p in phrases)
    STATS.assert_true(
        all_correct_length,
        f"All phrases have length exactly {phrase_len} ticks (2 measures)",
    )


# ---------------------------------------------------------------------------
# SUITE 5: Negative Parameters & Exception Validation
# ---------------------------------------------------------------------------
def run_suite_5_parameter_validation() -> None:
    print("\n" + "=" * 70)
    print("SUITE 5: Negative Parameters & Exception Validation")
    print("=" * 70)

    # HopoEngine
    print("\n--- Subtest 5.1: HopoEngine Parameter Validation ---")
    STATS.assert_raises(ValueError, HopoEngine, "HopoEngine(hopo_threshold=-1)", hopo_threshold=-1)
    STATS.assert_raises(
        ValueError, HopoEngine, "HopoEngine(hopo_threshold=-100)", hopo_threshold=-100
    )

    # Valid non-negative
    h_zero = HopoEngine(hopo_threshold=0)
    STATS.assert_true(
        h_zero.hopo_threshold == 0, "HopoEngine(hopo_threshold=0) accepted (non-negative)"
    )

    # SustainProcessor
    print("\n--- Subtest 5.2: SustainProcessor Parameter Validation ---")
    STATS.assert_raises(
        ValueError, SustainProcessor, "SustainProcessor(min_sustain_ticks=-1)", min_sustain_ticks=-1
    )
    STATS.assert_raises(
        ValueError, SustainProcessor, "SustainProcessor(release_margin=-1)", release_margin=-1
    )
    STATS.assert_raises(
        ValueError,
        SustainProcessor,
        "SustainProcessor(release_margin_ticks=-5)",
        release_margin_ticks=-5,
    )

    s_zero = SustainProcessor(min_sustain_ticks=0, release_margin=0)
    STATS.assert_true(
        s_zero.min_sustain_ticks == 0 and s_zero.release_margin == 0,
        "SustainProcessor(min_sustain_ticks=0, release_margin=0) accepted (non-negative)",
    )

    # StarPowerGenerator
    print("\n--- Subtest 5.3: StarPowerGenerator Parameter Validation ---")
    STATS.assert_raises(
        ValueError, StarPowerGenerator, "StarPowerGenerator(measure_ticks=0)", measure_ticks=0
    )
    STATS.assert_raises(
        ValueError, StarPowerGenerator, "StarPowerGenerator(measure_ticks=-1)", measure_ticks=-1
    )
    STATS.assert_raises(
        ValueError,
        StarPowerGenerator,
        "StarPowerGenerator(interval_measures=0)",
        interval_measures=0,
    )
    STATS.assert_raises(
        ValueError,
        StarPowerGenerator,
        "StarPowerGenerator(interval_measures=-16)",
        interval_measures=-16,
    )
    STATS.assert_raises(
        ValueError,
        StarPowerGenerator,
        "StarPowerGenerator(phrase_length_measures=0)",
        phrase_length_measures=0,
    )
    STATS.assert_raises(
        ValueError,
        StarPowerGenerator,
        "StarPowerGenerator(phrase_length_measures=-2)",
        phrase_length_measures=-2,
    )
    STATS.assert_raises(
        ValueError, StarPowerGenerator, "StarPowerGenerator(min_notes=0)", min_notes=0
    )
    STATS.assert_raises(
        ValueError, StarPowerGenerator, "StarPowerGenerator(min_notes=-4)", min_notes=-4
    )


# ---------------------------------------------------------------------------
# SUITE 6: Ultra-Dense Stress & Performance Benchmarks (50,000+ Notes)
# ---------------------------------------------------------------------------
def run_suite_6_benchmarks() -> None:
    print("\n" + "=" * 70)
    print("SUITE 6: Ultra-Dense Stress Benchmarks (50,000+ Notes)")
    print("=" * 70)

    NOTE_COUNT: Final[int] = 50_000

    print(f"Generating synthetic dense stream of {NOTE_COUNT:,} notes...")
    t0 = time.perf_counter()
    dense_notes = [
        ChartNote(
            tick=i * 24,  # 1/32 note grid
            fret=FretType(i % 5),
            sustain_length=random.choice([0, 48, 96, 192, 384]),
        )
        for i in range(NOTE_COUNT)
    ]
    t_gen = time.perf_counter() - t0
    print(f"Generated {NOTE_COUNT:,} notes in {t_gen:.3f}s")

    # 1. HopoEngine Benchmark
    print("\n--- Benchmark 6.1: HopoEngine.process(50,000 notes) ---")
    h_engine = HopoEngine(hopo_threshold=65)
    t0 = time.perf_counter()
    hopo_res = h_engine.process(dense_notes)
    t_hopo = time.perf_counter() - t0
    throughput_hopo = NOTE_COUNT / t_hopo
    STATS.record_bench("HopoEngine.process", t_hopo, f"{throughput_hopo:,.0f} notes/sec")
    print(f"  Processed {NOTE_COUNT:,} notes in {t_hopo:.4f}s ({throughput_hopo:,.0f} notes/sec)")
    STATS.assert_true(
        len(hopo_res) == NOTE_COUNT and t_hopo < 1.0,
        f"HopoEngine processed 50k notes under 1.0s (actual: {t_hopo:.4f}s)",
    )

    # 2. SustainProcessor Benchmark
    print("\n--- Benchmark 6.2: SustainProcessor.process(50,000 notes) ---")
    s_proc = SustainProcessor(min_sustain_ticks=90, release_margin=24)
    t0 = time.perf_counter()
    sustain_res = s_proc.process(dense_notes)
    t_sustain = time.perf_counter() - t0
    throughput_sustain = NOTE_COUNT / t_sustain
    STATS.record_bench(
        "SustainProcessor.process", t_sustain, f"{throughput_sustain:,.0f} notes/sec"
    )
    print(
        f"  Processed {NOTE_COUNT:,} notes in {t_sustain:.4f}s ({throughput_sustain:,.0f} notes/sec)"
    )
    STATS.assert_true(
        len(sustain_res) == NOTE_COUNT and t_sustain < 1.0,
        f"SustainProcessor processed 50k notes under 1.0s (actual: {t_sustain:.4f}s)",
    )

    # 3. StarPowerGenerator Benchmark
    print("\n--- Benchmark 6.3: StarPowerGenerator.generate(50,000 notes) ---")
    sp_gen = StarPowerGenerator()
    t0 = time.perf_counter()
    sp_res = sp_gen.generate(dense_notes)
    t_sp = time.perf_counter() - t0
    throughput_sp = NOTE_COUNT / t_sp
    STATS.record_bench(
        "StarPowerGenerator.generate",
        t_sp,
        f"{len(sp_res)} phrases ({throughput_sp:,.0f} notes/sec)",
    )
    print(f"  Generated {len(sp_res)} phrases across {NOTE_COUNT:,} notes in {t_sp:.4f}s")
    STATS.assert_true(
        len(sp_res) > 0 and t_sp < 2.0,
        f"StarPowerGenerator generated {len(sp_res)} phrases under 2.0s (actual: {t_sp:.4f}s)",
    )


# ---------------------------------------------------------------------------
# SUITE 7: Invariant Fuzzing on Randomized Streams
# ---------------------------------------------------------------------------
def run_suite_7_fuzzing() -> None:
    print("\n" + "=" * 70)
    print("SUITE 7: Invariant Fuzzing on Randomized Streams")
    print("=" * 70)

    random.seed(42)
    FUZZ_COUNT: Final[int] = 10_000

    print(f"Generating {FUZZ_COUNT:,} randomized notes with jittered ticks and chords...")
    ticks: list[int] = []
    current_t = 0
    while len(ticks) < FUZZ_COUNT:
        # random step: 0 (chord), micro-step (1 to 24), or musical step (48 to 384)
        step = random.choice([0, 0, 1, 12, 24, 32, 48, 64, 65, 66, 96, 192, 384])
        current_t += step
        ticks.append(current_t)

    raw_fuzzed: list[ChartNote] = []
    frets_pool = [
        FretType.GREEN,
        FretType.RED,
        FretType.YELLOW,
        FretType.BLUE,
        FretType.ORANGE,
        FretType.OPEN,
    ]
    for t in ticks:
        raw_fuzzed.append(
            ChartNote(
                tick=t,
                fret=random.choice(frets_pool),
                sustain_length=random.randint(0, 1500),
            )
        )

    # Shuffle to test unsorted input resilience
    random.shuffle(raw_fuzzed)

    h_engine = HopoEngine(hopo_threshold=65)
    s_proc = SustainProcessor(min_sustain_ticks=90, release_margin=24)
    sp_gen = StarPowerGenerator()

    # Step 1: HopoEngine
    hopo_out = h_engine.process(raw_fuzzed)

    # Invariants for HopoEngine
    # 1. Output is strictly sorted by tick then fret
    is_sorted = all(
        (hopo_out[i].tick, hopo_out[i].fret) <= (hopo_out[i + 1].tick, hopo_out[i + 1].fret)
        for i in range(len(hopo_out) - 1)
    )
    STATS.assert_true(is_sorted, "Fuzzed HopoEngine output is strictly sorted by (tick, fret)")

    # 2. First note is NEVER HOPO
    first_not_hopo = hopo_out[0].is_hopo is False
    STATS.assert_true(first_not_hopo, "Fuzzed track initial note is never a HOPO")

    # 3. No chord notes are HOPO
    tick_counts: dict[int, int] = {}
    for n in hopo_out:
        tick_counts[n.tick] = tick_counts.get(n.tick, 0) + 1
    no_chord_hopo = all(n.is_hopo is False for n in hopo_out if tick_counts[n.tick] > 1)
    STATS.assert_true(no_chord_hopo, "No simultaneous notes (chords) in fuzzed stream are HOPOs")

    # Step 2: SustainProcessor
    sustain_out = s_proc.process(hopo_out)

    # Invariants for SustainProcessor
    # 1. Sustain is never negative
    all_non_negative_sus = all(n.sustain_length >= 0 for n in sustain_out)
    STATS.assert_true(all_non_negative_sus, "All fuzzed sustain lengths are non-negative (>= 0)")

    # 2. No sustain overlaps next note: tail_tick + 24 <= next_tick (unless next_tick - tick <= 24 where sus=0)
    unique_ticks = sorted({n.tick for n in sustain_out})
    tick_to_next = {unique_ticks[i]: unique_ticks[i + 1] for i in range(len(unique_ticks) - 1)}

    no_sustain_overlap = True
    overlap_violation_count = 0
    for n in sustain_out:
        next_t = tick_to_next.get(n.tick)
        if next_t is not None:
            tail = n.tick + n.sustain_length
            if tail + 24 > next_t and n.sustain_length > 0:
                overlap_violation_count += 1
                no_sustain_overlap = False

    STATS.assert_true(
        no_sustain_overlap,
        f"All fuzzed sustains leave at least 24-tick margin before next note (violations: {overlap_violation_count})",
    )

    # Step 3: StarPowerGenerator
    sp_out = sp_gen.generate(sustain_out)

    # Invariants for StarPowerGenerator
    # 1. Phrases are non-overlapping
    sp_no_overlap = all(
        sp_out[i].tick + sp_out[i].length <= sp_out[i + 1].tick for i in range(len(sp_out) - 1)
    )
    STATS.assert_true(sp_no_overlap, "All fuzzed Star Power phrases are strictly non-overlapping")

    # 2. Phrases start on an existing note tick
    sp_aligned = all(p.tick in tick_counts for p in sp_out)
    STATS.assert_true(sp_aligned, "All fuzzed Star Power phrases start on an existing note tick")


# ---------------------------------------------------------------------------
# MAIN ENTRY POINT
# ---------------------------------------------------------------------------
def main() -> int:
    print("=" * 70)
    print("GAME DESIGN ENGINE (MILESTONE 4) EMPIRICAL ADVERSARIAL HARNESS")
    print("=" * 70)

    t_start = time.perf_counter()

    run_suite_1_hopo_boundary()
    run_suite_2_trills()
    run_suite_3_sustain_clamping()
    run_suite_4_star_power()
    run_suite_5_parameter_validation()
    run_suite_6_benchmarks()
    run_suite_7_fuzzing()

    total_time = time.perf_counter() - t_start

    print("\n" + "=" * 70)
    print("HARNESS EXECUTION SUMMARY")
    print("=" * 70)
    print(f"Total assertions passed : {STATS.passed}")
    print(f"Total assertions failed : {STATS.failed}")
    print(f"Total harness runtime   : {total_time:.3f}s")
    print("\nPerformance Benchmarks Recorded:")
    for name, elapsed, note_rate in STATS.benchmarks:
        print(f"  - {name:<28}: {elapsed:.4f}s ({note_rate})")
    print("=" * 70)

    if STATS.failed == 0:
        print("\n>>> ALL ADVERSARIAL STRESS SUITES PASSED! <<<\n")
        return 0
    else:
        print(f"\n>>> HARNESS FAILED WITH {STATS.failed} ERRORS! <<<\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
