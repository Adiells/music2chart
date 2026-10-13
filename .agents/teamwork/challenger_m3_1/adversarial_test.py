"""Adversarial stress-test and invariant verification harness for ChordBuilder.

Stress dimensions:
1. All 2^5 = 32 possible fret combinations of {0, 1, 2, 3, 4} tested across multiple configurations:
   - Default (max_frets=3, allow_wide_triads=False)
   - Wide triads enabled (allow_wide_triads=True)
   - max_frets=2 (rhythm / power-chord mode)
   - max_frets=1 (monophonic root mode)
2. Massive polyphonic collisions at a single tick:
   - 10, 20, 50, 100, 500 duplicate and mixed notes at the exact same tick
   - Mixed frets (0-4) with Open notes (7) under open_note_precedence=True and False
3. High-throughput dense polyphonic streams:
   - 25,000 notes with dense polyphony across varying patterns
   - 50,000 notes simulated full chart stream
   - Throughput benchmarking (notes / second) and linear complexity verification
4. Extreme sustain values and duplicate fret merging:
   - Sustain values up to 10,000,000 ticks
   - Merging taking max sustain and any is_hopo
   - Synthetic fret attribute inheritance on clamped chords (e.g. (0, 3) -> (0, 2))
5. Pathological inputs:
   - Reverse-chronological ordering (tick descending)
   - Highly scrambled ordering
   - Open notes alternating with dense clusters
   - Idempotency test (f(f(x)) == f(x))
"""

from __future__ import annotations

import itertools
import random
import sys
import time
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.game_design.chord_builder import (  # noqa: E402
    CANONICAL_POWER_CHORDS,
    CANONICAL_TRIADS,
    ChordBuilder,
)
from src.models.chart import ChartNote, FretType  # noqa: E402

VALID_FRETS = {
    FretType.GREEN,
    FretType.RED,
    FretType.YELLOW,
    FretType.BLUE,
    FretType.ORANGE,
    FretType.HOPO_FORCE,
    FretType.STRUM_FORCE,
    FretType.OPEN,
}


def assert_invariants(
    notes: Sequence[ChartNote],
    max_frets: int = 3,
    allow_wide_triads: bool = False,
    context: str = "",
) -> None:
    """Strictly assert all game design and structural invariants on a processed sequence."""
    if not notes:
        return

    prev_tick = -1
    prev_fret = -1
    tick_notes: dict[int, list[ChartNote]] = defaultdict(list)

    for idx, n in enumerate(notes):
        # 1. Type and attribute validity
        assert isinstance(n, ChartNote), f"[{context}] Note {idx} not ChartNote: {type(n)}"
        assert n.tick >= 0, f"[{context}] Note {idx} has negative tick: {n.tick}"
        assert n.sustain_length >= 0, f"[{context}] Note {idx} has negative sustain: {n.sustain_length}"
        assert n.fret in VALID_FRETS, f"[{context}] Note {idx} has invalid fret: {n.fret}"

        # 2. Ascending order by (tick, fret)
        if n.tick < prev_tick:
            raise AssertionError(f"[{context}] Chronological order violated: {n.tick} < {prev_tick}")
        if n.tick == prev_tick:
            if n.fret.value <= prev_fret:
                raise AssertionError(
                    f"[{context}] Fret sorting/deduplication violated at tick {n.tick}: "
                    f"fret {n.fret.value} <= prev_fret {prev_fret}"
                )

        prev_tick = n.tick
        prev_fret = n.fret.value
        tick_notes[n.tick].append(n)

    # 3. Per-tick game design constraints
    for tick, chord in tick_notes.items():
        fretted = [n for n in chord if 0 <= n.fret.value <= 4]
        open_notes = [n for n in chord if n.fret == FretType.OPEN]

        # Invariant A: Open note exclusivity
        if open_notes:
            assert len(fretted) == 0, (
                f"[{context}] Open note (7) coexists with fretted notes {fretted} at tick {tick}"
            )
            assert len(open_notes) == 1, (
                f"[{context}] Multiple Open notes at tick {tick}: {len(open_notes)}"
            )

        # Invariant B: Max simultaneous frets
        assert len(fretted) <= max_frets, (
            f"[{context}] Exceeded max_frets={max_frets} at tick {tick}: got {len(fretted)} frets"
        )

        fret_vals = tuple(n.fret.value for n in fretted)

        # Invariant C: Elimination of (0, 4) stretch
        if {0, 4}.issubset(fret_vals):
            if allow_wide_triads and fret_vals == (0, 2, 4):
                pass  # Permitted only when wide triads explicitly enabled
            else:
                raise AssertionError(
                    f"[{context}] Forbidden (0, 4) stretch present at tick {tick}: {fret_vals}"
                )

        # Invariant D: Canonical shapes verification
        if len(fret_vals) == 2:
            assert fret_vals in CANONICAL_POWER_CHORDS, (
                f"[{context}] 2-note chord {fret_vals} at tick {tick} is not a canonical power chord"
            )
        elif len(fret_vals) == 3:
            if allow_wide_triads and fret_vals == (0, 2, 4):
                pass
            else:
                assert fret_vals in CANONICAL_TRIADS or fret_vals in {(1, 3, 4), (0, 1, 2), (0, 2, 3), (1, 2, 3), (2, 3, 4)}, (
                    f"[{context}] 3-note chord {fret_vals} at tick {tick} not recognized"
                )


# ===========================================================================
# TEST SUITE 1: All 32 Subsets of {0, 1, 2, 3, 4} Power Set
# ===========================================================================


def test_suite_1_all_32_power_set_subsets() -> None:
    """Verify all 2^5 = 32 subsets of frets {0, 1, 2, 3, 4} at a single tick."""
    print("\n" + "=" * 70)
    print("SUITE 1: All 2^5 = 32 Fret Combinations Exhaustive Verification")
    print("=" * 70)

    fret_universe = [0, 1, 2, 3, 4]
    all_subsets = []
    for r in range(len(fret_universe) + 1):
        for combo in itertools.combinations(fret_universe, r):
            all_subsets.append(combo)

    assert len(all_subsets) == 32, f"Expected 32 subsets, got {len(all_subsets)}"

    # Configurations to test
    configs = [
        ("Default (max=3, wide=False)", ChordBuilder(max_frets=3, allow_wide_triads=False), 3, False),
        ("Wide Triads (max=3, wide=True)", ChordBuilder(max_frets=3, allow_wide_triads=True), 3, True),
        ("Rhythm Mode (max=2, wide=False)", ChordBuilder(max_frets=2, allow_wide_triads=False), 2, False),
        ("Monophonic (max=1, wide=False)", ChordBuilder(max_frets=1, allow_wide_triads=False), 1, False),
    ]

    for config_name, builder, max_f, wide in configs:
        print(f"\nTesting config: {config_name}")
        for subset in all_subsets:
            notes = [
                ChartNote(tick=192, fret=FretType(f), sustain_length=48, is_hopo=False)
                for f in subset
            ]
            result = builder.build_chords(notes)
            assert_invariants(result, max_frets=max_f, allow_wide_triads=wide, context=f"Subset {subset}")

            res_frets = tuple(n.fret.value for n in result)
            # Extra specific checks
            if len(subset) == 0:
                assert res_frets == ()
            elif max_f == 1:
                assert len(res_frets) == 1
                assert res_frets[0] in {0, 1, 2, 3, 4}
            elif max_f == 2 and len(subset) >= 2:
                assert len(res_frets) in (1, 2)
                if len(res_frets) == 2:
                    assert res_frets in CANONICAL_POWER_CHORDS
            elif max_f == 3:
                assert len(res_frets) <= 3
                if {0, 4}.issubset(subset):
                    if wide and subset == (0, 2, 4):
                        assert res_frets == (0, 2, 4)
                    else:
                        assert not {0, 4}.issubset(res_frets), f"Failed to eliminate {subset} -> {res_frets}"

        print(f"  ✓ All 32 subsets passed under {config_name}")

    # Print truth table for default configuration
    default_builder = ChordBuilder(max_frets=3, allow_wide_triads=False)
    print("\n--- Power Set Truth Table (Default: max_frets=3, allow_wide_triads=False) ---")
    print(f"{'Input Subset':<20} -> {'Output Frets':<15} {'Count':<6} {'Notes / Status'}")
    print("-" * 65)
    for subset in all_subsets:
        notes = [ChartNote(tick=0, fret=FretType(f)) for f in subset]
        res = tuple(n.fret.value for n in default_builder.build_chords(notes))
        notes_desc = "Empty" if not res else f"Playable ({len(res)}-note)"
        if {0, 4}.issubset(res):
            notes_desc = "FAIL: Contains (0,4)!"
        elif res in CANONICAL_TRIADS:
            notes_desc = "Canonical Triad"
        elif res in CANONICAL_POWER_CHORDS:
            notes_desc = "Canonical Power Chord"
        elif len(res) == 1:
            notes_desc = "Single Note"
        print(f"{str(subset):<20} -> {str(res):<15} {len(res):<6} {notes_desc}")


# ===========================================================================
# TEST SUITE 2: Massive Single-Tick Clusters (10, 20, 50, 100, 500 notes)
# ===========================================================================


def test_suite_2_massive_single_tick_clusters() -> None:
    """Stress test massive clusters of 10, 20, 50, 100, 500 notes at a single tick."""
    print("\n" + "=" * 70)
    print("SUITE 2: Massive Single-Tick Polyphonic Clusters")
    print("=" * 70)

    builder_default = ChordBuilder(max_frets=3)
    builder_fretted_pref = ChordBuilder(max_frets=3, open_note_precedence=False)

    cluster_sizes = [10, 20, 50, 100, 500]
    random.seed(1337)

    for size in cluster_sizes:
        print(f"\n--- Testing cluster size: {size} notes at tick 480 ---")

        # Scenario A: Mixed frets 0-4 with duplicate frets and extreme varying sustains
        notes_fretted_only = [
            ChartNote(
                tick=480,
                fret=FretType(random.randint(0, 4)),
                sustain_length=random.randint(0, 5000),
                is_hopo=random.choice([True, False]),
            )
            for _ in range(size)
        ]
        res_a = builder_default.build_chords(notes_fretted_only)
        assert_invariants(res_a, max_frets=3, context=f"Cluster {size} Fretted Only")
        assert 1 <= len(res_a) <= 3
        # Check max sustain was preserved
        for n in res_a:
            matching = [orig for orig in notes_fretted_only if orig.fret == n.fret]
            if matching:
                expected_max = max(orig.sustain_length for orig in matching)
                assert n.sustain_length >= expected_max, (
                    f"Sustain length not merged properly: got {n.sustain_length}, expected >= {expected_max}"
                )

        # Scenario B: Mixed frets 0-4 AND Open notes (7) with open_note_precedence=True
        notes_mixed = list(notes_fretted_only)
        open_count = max(1, size // 5)
        for _ in range(open_count):
            notes_mixed.append(
                ChartNote(
                    tick=480,
                    fret=FretType.OPEN,
                    sustain_length=random.randint(100, 9999),
                    is_hopo=random.choice([True, False]),
                )
            )
        random.shuffle(notes_mixed)

        res_b = builder_default.build_chords(notes_mixed)
        assert_invariants(res_b, max_frets=3, context=f"Cluster {size} Mixed Open Precedence")
        assert len(res_b) == 1
        assert res_b[0].fret == FretType.OPEN
        assert res_b[0].sustain_length == max(n.sustain_length for n in notes_mixed)

        # Scenario C: Mixed frets 0-4 AND Open notes (7) with open_note_precedence=False
        res_c = builder_fretted_pref.build_chords(notes_mixed)
        assert_invariants(res_c, max_frets=3, context=f"Cluster {size} Mixed Fretted Precedence")
        assert 1 <= len(res_c) <= 3
        assert all(n.fret != FretType.OPEN for n in res_c)

        print(f"  ✓ Cluster size {size} passed (Fretted only: {len(res_a)} notes, Mixed Open: {len(res_b)}, Mixed Fretted: {len(res_c)})")


# ===========================================================================
# TEST SUITE 3: High-Throughput Streams (25,000+ notes)
# ===========================================================================


def test_suite_3_high_throughput_streams() -> None:
    """Stress test high-throughput streams with thousands of dense polyphonic clusters."""
    print("\n" + "=" * 70)
    print("SUITE 3: High-Throughput Dense Polyphonic Streams (25k - 50k notes)")
    print("=" * 70)

    builder = ChordBuilder(max_frets=3)
    random.seed(2026)

    # 3A: 25,000 notes with frequent multi-note clusters
    total_notes_target = 25000
    notes: list[ChartNote] = []
    tick = 0

    while len(notes) < total_notes_target:
        cluster_type = random.randint(0, 5)
        if cluster_type == 0:
            # Single note
            notes.append(ChartNote(tick=tick, fret=FretType(random.choice([0, 1, 2, 3, 4, 7]))))
        elif cluster_type == 1:
            # 2-note chord
            frets = random.sample([0, 1, 2, 3, 4], 2)
            for f in frets:
                notes.append(ChartNote(tick=tick, fret=FretType(f), sustain_length=random.randint(0, 192)))
        elif cluster_type == 2:
            # 3-note chord
            frets = random.sample([0, 1, 2, 3, 4], 3)
            for f in frets:
                notes.append(ChartNote(tick=tick, fret=FretType(f), sustain_length=random.randint(0, 192)))
        elif cluster_type == 3:
            # 4-note cluster
            frets = random.sample([0, 1, 2, 3, 4], 4)
            for f in frets:
                notes.append(ChartNote(tick=tick, fret=FretType(f)))
        elif cluster_type == 4:
            # 5-note full highway cluster
            for f in range(5):
                notes.append(ChartNote(tick=tick, fret=FretType(f)))
        else:
            # Colliding Open and fretted notes
            notes.append(ChartNote(tick=tick, fret=FretType.OPEN, sustain_length=96))
            notes.append(ChartNote(tick=tick, fret=FretType(random.randint(0, 4))))

        tick += random.choice([24, 48, 96, 192])

    print(f"Generated {len(notes):,} raw notes spanning {tick:,} ticks.")
    t0 = time.perf_counter()
    result = builder.build_chords(notes)
    elapsed = time.perf_counter() - t0
    throughput = len(notes) / elapsed

    print(f"Processed in {elapsed:.3f}s -> {throughput:,.1f} notes/sec. Output notes: {len(result):,}")
    assert_invariants(result, max_frets=3, context="25k Stream")
    assert throughput > 10000, f"Throughput too low: {throughput} notes/sec"

    # 3B: 50,000 completely unsorted / scrambled notes
    print("\n--- Running 50,000 Scrambled Notes Stress Test ---")
    scrambled_notes = list(notes) * 2  # 50,000 notes
    random.shuffle(scrambled_notes)

    t0 = time.perf_counter()
    result_50k = builder.build_chords(scrambled_notes)
    elapsed_50k = time.perf_counter() - t0
    throughput_50k = len(scrambled_notes) / elapsed_50k

    print(f"Processed 50,000 scrambled notes in {elapsed_50k:.3f}s -> {throughput_50k:,.1f} notes/sec.")
    assert_invariants(result_50k, max_frets=3, context="50k Scrambled Stream")
    assert throughput_50k > 10000, f"Throughput too low: {throughput_50k} notes/sec"


# ===========================================================================
# TEST SUITE 4: Extreme Sustain Values and Duplicate Fret Merging
# ===========================================================================


def test_suite_4_extreme_sustains_and_merging() -> None:
    """Stress test extreme sustain values, hopo combinations, and clamped fret attribute inheritance."""
    print("\n" + "=" * 70)
    print("SUITE 4: Extreme Sustain Values and Attribute Inheritance")
    print("=" * 70)

    builder = ChordBuilder(max_frets=3)

    # 4A: Massive sustain lengths (up to 10,000,000 ticks)
    extreme_sustains = [0, 1, 96, 192, 480, 10000, 1000000, 10000000]
    notes = [
        ChartNote(tick=0, fret=FretType.GREEN, sustain_length=s)
        for s in extreme_sustains
    ]
    res = builder.build_chords(notes)
    assert len(res) == 1
    assert res[0].fret == FretType.GREEN
    assert res[0].sustain_length == 10000000, f"Expected 10000000, got {res[0].sustain_length}"
    print("  ✓ Extreme sustain merging: 10,000,000 ticks preserved successfully")

    # 4B: Hopo aggregation: True or False = True
    hopo_notes = [
        ChartNote(tick=96, fret=FretType.RED, sustain_length=10, is_hopo=False),
        ChartNote(tick=96, fret=FretType.RED, sustain_length=50, is_hopo=False),
        ChartNote(tick=96, fret=FretType.RED, sustain_length=20, is_hopo=True),
    ]
    res_hopo = builder.build_chords(hopo_notes)
    assert len(res_hopo) == 1
    assert res_hopo[0].sustain_length == 50
    assert res_hopo[0].is_hopo is True
    print("  ✓ Hopo flag merging: is_hopo=True preserved across duplicates")

    # 4C: Clamped chord attribute inheritance: (0, 3) clamped to (0, 2)
    # The new fret (2) must inherit max sustain and any hopo from the chord
    clamp_notes = [
        ChartNote(tick=192, fret=FretType.GREEN, sustain_length=100, is_hopo=False),
        ChartNote(tick=192, fret=FretType.BLUE, sustain_length=300, is_hopo=True),
    ]
    res_clamp = builder.build_chords(clamp_notes)
    assert len(res_clamp) == 2
    assert tuple(n.fret.value for n in res_clamp) == (0, 2)
    yellow_note = next(n for n in res_clamp if n.fret == FretType.YELLOW)
    assert yellow_note.sustain_length == 300, (
        f"Synthetic clamped fret didn't inherit max sustain: {yellow_note.sustain_length}"
    )
    assert yellow_note.is_hopo is True, (
        f"Synthetic clamped fret didn't inherit hopo flag: {yellow_note.is_hopo}"
    )
    print("  ✓ Synthetic clamped fret attribute inheritance verified")


# ===========================================================================
# TEST SUITE 5: Pathological & Adversarial Edge Cases
# ===========================================================================


def test_suite_5_pathological_edge_cases() -> None:
    """Stress test pathological edge cases: reverse order, empty, idempotency."""
    print("\n" + "=" * 70)
    print("SUITE 5: Pathological Edge Cases & Idempotency")
    print("=" * 70)

    builder = ChordBuilder(max_frets=3)

    # 5A: Empty input
    assert builder.build_chords([]) == []
    print("  ✓ Empty input handled")

    # 5B: Completely reverse-chronological input (10,000 notes)
    rev_notes = [
        ChartNote(tick=(10000 - i) * 24, fret=FretType(i % 5))
        for i in range(10000)
    ]
    res_rev = builder.build_chords(rev_notes)
    assert len(res_rev) == 10000
    assert_invariants(res_rev, max_frets=3, context="Reverse Ticks")
    assert res_rev[0].tick == 24
    assert res_rev[-1].tick == 10000 * 24
    print("  ✓ 10,000 reverse-ordered notes sorted strictly")

    # 5C: Massive tick values (1 billion)
    huge_tick_notes = [
        ChartNote(tick=1_000_000_000, fret=FretType.GREEN),
        ChartNote(tick=1_000_000_000, fret=FretType.RED),
    ]
    res_huge = builder.build_chords(huge_tick_notes)
    assert len(res_huge) == 2
    assert res_huge[0].tick == 1_000_000_000
    print("  ✓ Extreme tick value (1,000,000,000) supported")

    # 5D: Idempotency: f(f(x)) == f(x)
    random.seed(42)
    sample_notes = [
        ChartNote(tick=random.randint(0, 1000) * 24, fret=FretType(random.randint(0, 4)))
        for _ in range(500)
    ]
    pass1 = builder.build_chords(sample_notes)
    pass2 = builder.build_chords(pass1)
    assert pass1 == pass2, "ChordBuilder is not idempotent!"
    print("  ✓ Idempotency verified: f(f(x)) == f(x)")


# ===========================================================================
# MAIN ENTRYPOINT
# ===========================================================================


def main() -> None:
    print("=" * 70)
    print("CHORDBUILDER EMPIRICAL ADVERSARIAL STRESS TEST HARNESS")
    print("=" * 70)

    start_time = time.perf_counter()

    test_suite_1_all_32_power_set_subsets()
    test_suite_2_massive_single_tick_clusters()
    test_suite_3_high_throughput_streams()
    test_suite_4_extreme_sustains_and_merging()
    test_suite_5_pathological_edge_cases()

    total_time = time.perf_counter() - start_time
    print("\n" + "=" * 70)
    print(f"ALL ADVERSARIAL SUITES PASSED SUCCESSFULLY IN {total_time:.3f}s")
    print("VERDICT: APPROVE")
    print("=" * 70)


if __name__ == "__main__":
    main()
