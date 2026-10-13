"""Oracle and property-based verification harness for ChordBuilder.

Empirically challenges and tests all ergonomic invariants:
1. len(frets_at_tick) <= max_frets (specifically <= 3 by default) for every distinct tick.
2. Never output isolated {0, 4} at any tick.
3. Open Note Exclusivity: if 7 (Open) is in output at a tick, len(frets_at_tick) == 1 (no frets 0-4).
4. Canonical power chords {(0,1), (0,2), (1,2), (1,3), (2,3), (2,4), (3,4)} 100% invariant.
5. Canonical triads {(0,1,2), (0,2,3), (1,2,3), (2,3,4)} 100% invariant.
6. Full combinatorial verification of all 64 fret subsets at a single tick.
7. Property-based fuzzing across 10,000 randomized note configurations.
"""

from __future__ import annotations

import itertools
import random
import sys
import time
from collections.abc import Sequence
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.game_design.chord_builder import (  # noqa: E402
    CANONICAL_POWER_CHORDS,
    CANONICAL_TRIADS,
    ChordBuilder,
)
from src.models.chart import ChartNote, FretType  # noqa: E402

ALL_PLAYABLE_FRETS = [0, 1, 2, 3, 4, 7]


def make_note(
    tick: int,
    fret: int | FretType,
    sustain_length: int = 0,
    is_hopo: bool = False,
) -> ChartNote:
    fret_val = FretType(fret) if isinstance(fret, int) else fret
    return ChartNote(
        tick=tick,
        fret=fret_val,
        sustain_length=sustain_length,
        is_hopo=is_hopo,
    )


def get_frets_by_tick(notes: Sequence[ChartNote]) -> dict[int, list[int]]:
    result: dict[int, list[int]] = {}
    for n in notes:
        result.setdefault(n.tick, []).append(n.fret.value)
    return result


# ---------------------------------------------------------------------------
# Invariant Checkers
# ---------------------------------------------------------------------------


def verify_invariants(
    notes_out: list[ChartNote],
    max_frets: int = 3,
    builder: ChordBuilder | None = None,
) -> tuple[bool, str]:
    """Verify core ergonomic invariants on any ChordBuilder output."""
    limit = builder.max_frets if builder is not None else max_frets

    # 1. Output must be strictly sorted by (tick, fret) ascending
    for i in range(len(notes_out) - 1):
        curr = notes_out[i]
        nxt = notes_out[i + 1]
        if (curr.tick, curr.fret.value) > (nxt.tick, nxt.fret.value):
            return (
                False,
                f"Sorting invariant violated: ({curr.tick}, {curr.fret.value}) > ({nxt.tick}, {nxt.fret.value})",
            )
        if curr.tick == nxt.tick and curr.fret == nxt.fret:
            return (
                False,
                f"Deduplication invariant violated: duplicate note at tick {curr.tick}, fret {curr.fret.value}",
            )

    frets_by_tick = get_frets_by_tick(notes_out)

    for tick, frets in frets_by_tick.items():
        # Invariant 1: len(frets_at_tick) <= limit
        playable_frets = [f for f in frets if f in (0, 1, 2, 3, 4, 7)]
        if len(playable_frets) > limit:
            return (
                False,
                f"Tick {tick}: len(frets)={len(playable_frets)} exceeds max_frets={limit}: frets={playable_frets}",
            )

        # Invariant 2: Never output isolated {0, 4}
        fret_set = set(frets)
        if fret_set == {0, 4}:
            return (
                False,
                f"Tick {tick}: isolated forbidden stretch {{0, 4}} detected in output!",
            )

        # Invariant 3: If 7 (Open) is in output, len(frets) == 1 and no frets 0-4 present
        if 7 in fret_set:
            if len(frets) != 1:
                return (
                    False,
                    f"Tick {tick}: Open note 7 coexists with other notes: frets={frets}",
                )
            if any(f in fret_set for f in (0, 1, 2, 3, 4)):
                return (
                    False,
                    f"Tick {tick}: Open note 7 coexists with fretted notes 0-4: frets={frets}",
                )

    return True, "OK"


# ---------------------------------------------------------------------------
# Suite 1: Full Combinatorial Power Set Verification (64 subsets)
# ---------------------------------------------------------------------------


def run_suite_1_combinatorial_power_set() -> tuple[int, int]:
    print("\n--- Running Suite 1: Full Combinatorial Power Set (64 subsets) ---")
    passes = 0
    failures = 0

    subsets: list[tuple[int, ...]] = []
    for r in range(len(ALL_PLAYABLE_FRETS) + 1):
        for combo in itertools.combinations(ALL_PLAYABLE_FRETS, r):
            subsets.append(combo)

    builder_default = ChordBuilder(max_frets=3)

    for combo in subsets:
        notes_in = [make_note(tick=100, fret=f) for f in combo]
        notes_out = builder_default.build_chords(notes_in)

        ok, msg = verify_invariants(notes_out, max_frets=3, builder=builder_default)
        if not ok:
            print(f"FAILED on input combo {combo}: {msg}")
            failures += 1
        else:
            passes += 1

    print(f"Suite 1 Complete: {passes} passed, {failures} failed out of {len(subsets)} power-set cases.")
    return passes, failures


# ---------------------------------------------------------------------------
# Suite 2: Configuration Matrix Permutations
# ---------------------------------------------------------------------------


def run_suite_2_config_matrix() -> tuple[int, int]:
    print("\n--- Running Suite 2: Config Matrix Permutations ---")
    passes = 0
    failures = 0

    max_frets_options = [1, 2, 3, 4, 5]
    wide_triads_options = [False, True]
    open_precedence_options = [False, True]

    subsets: list[tuple[int, ...]] = []
    for r in range(1, len(ALL_PLAYABLE_FRETS) + 1):
        for combo in itertools.combinations(ALL_PLAYABLE_FRETS, r):
            subsets.append(combo)

    total = len(max_frets_options) * len(wide_triads_options) * len(open_precedence_options) * len(subsets)

    for mf in max_frets_options:
        for wt in wide_triads_options:
            for op in open_precedence_options:
                b = ChordBuilder(
                    max_frets=mf,
                    allow_wide_triads=wt,
                    open_note_precedence=op,
                )
                for combo in subsets:
                    notes_in = [make_note(tick=0, fret=f) for f in combo]
                    notes_out = b.build_chords(notes_in)
                    ok, msg = verify_invariants(notes_out, builder=b)
                    if not ok:
                        print(f"FAILED on mf={mf}, wt={wt}, op={op}, combo={combo}: {msg}")
                        failures += 1
                    else:
                        passes += 1

    print(f"Suite 2 Complete: {passes} passed, {failures} failed out of {total} config combinations.")
    return passes, failures


# ---------------------------------------------------------------------------
# Suite 3: Canonical Power Chords 100% Invariant Verification
# ---------------------------------------------------------------------------


def run_suite_3_canonical_power_chords() -> tuple[int, int]:
    print("\n--- Running Suite 3: Canonical Power Chords 100% Invariant ---")
    passes = 0
    failures = 0

    builder = ChordBuilder(max_frets=3)
    expected_power_chords = [
        (0, 1),
        (0, 2),
        (1, 2),
        (1, 3),
        (2, 3),
        (2, 4),
        (3, 4),
    ]

    # Verify set definition matches
    assert CANONICAL_POWER_CHORDS == frozenset(expected_power_chords)

    test_ticks = [0, 48, 96, 192, 384, 1000]
    sustain_options = [(0, 0), (48, 48), (96, 48), (120, 150)]
    hopo_options = [(False, False), (True, True), (False, True), (True, False)]

    for pc in expected_power_chords:
        for t in test_ticks:
            for s1, s2 in sustain_options:
                for h1, h2 in hopo_options:
                    # In ascending fret order
                    n1 = make_note(tick=t, fret=pc[0], sustain_length=s1, is_hopo=h1)
                    n2 = make_note(tick=t, fret=pc[1], sustain_length=s2, is_hopo=h2)
                    res = builder.build_chords([n1, n2])

                    if len(res) != 2:
                        print(f"FAILED: Expected 2 notes for {pc}, got {len(res)}")
                        failures += 1
                        continue
                    if (res[0].fret.value, res[1].fret.value) != pc:
                        print(f"FAILED: Fret values mismatch: got {(res[0].fret.value, res[1].fret.value)}, expected {pc}")
                        failures += 1
                        continue
                    if res[0].sustain_length != s1 or res[1].sustain_length != s2:
                        print(f"FAILED: Sustain mismatch for {pc}: {(res[0].sustain_length, res[1].sustain_length)} != {(s1, s2)}")
                        failures += 1
                        continue
                    if res[0].is_hopo != h1 or res[1].is_hopo != h2:
                        print(f"FAILED: HOPO mismatch for {pc}")
                        failures += 1
                        continue

                    # In reverse fret order (unsorted input)
                    res_rev = builder.build_chords([n2, n1])
                    if (res_rev[0].fret.value, res_rev[1].fret.value) != pc:
                        print(f"FAILED on reverse input: got {(res_rev[0].fret.value, res_rev[1].fret.value)}")
                        failures += 1
                        continue
                    if res_rev[0].sustain_length != s1 or res_rev[1].sustain_length != s2:
                        print(f"FAILED: Sustain mismatch on reverse input for {pc}")
                        failures += 1
                        continue

                    passes += 2

    print(f"Suite 3 Complete: {passes} passed, {failures} failed (100% invariant verified).")
    return passes, failures


# ---------------------------------------------------------------------------
# Suite 4: Canonical Triads 100% Invariant Verification
# ---------------------------------------------------------------------------


def run_suite_4_canonical_triads() -> tuple[int, int]:
    print("\n--- Running Suite 4: Canonical Triads 100% Invariant ---")
    passes = 0
    failures = 0

    builder = ChordBuilder(max_frets=3)
    expected_triads = [
        (0, 1, 2),
        (0, 2, 3),
        (1, 2, 3),
        (2, 3, 4),
    ]

    assert CANONICAL_TRIADS == frozenset(expected_triads)

    test_ticks = [0, 96, 192, 768]
    sustain_combos = [(0, 0, 0), (96, 96, 96), (48, 96, 120)]

    for triad in expected_triads:
        for t in test_ticks:
            for s1, s2, s3 in sustain_combos:
                base_notes = [
                    make_note(tick=t, fret=triad[0], sustain_length=s1),
                    make_note(tick=t, fret=triad[1], sustain_length=s2),
                    make_note(tick=t, fret=triad[2], sustain_length=s3),
                ]
                # Test all 6 permutations of input order
                for perm in itertools.permutations(base_notes):
                    res = builder.build_chords(list(perm))
                    if len(res) != 3:
                        print(f"FAILED: Expected 3 notes for triad {triad}, got {len(res)}")
                        failures += 1
                        continue
                    out_frets = (res[0].fret.value, res[1].fret.value, res[2].fret.value)
                    if out_frets != triad:
                        print(f"FAILED: Triad mismatch: got {out_frets}, expected {triad}")
                        failures += 1
                        continue
                    if (res[0].sustain_length, res[1].sustain_length, res[2].sustain_length) != (s1, s2, s3):
                        print(f"FAILED: Triad sustain mismatch for {triad}")
                        failures += 1
                        continue
                    passes += 1

    print(f"Suite 4 Complete: {passes} passed, {failures} failed (100% invariant verified).")
    return passes, failures


# ---------------------------------------------------------------------------
# Suite 5: Stretch Clamping & Ergonomic Reduction Oracle
# ---------------------------------------------------------------------------


def run_suite_5_stretch_and_reduction() -> tuple[int, int]:
    print("\n--- Running Suite 5: Stretch Clamping & Ergonomic Reduction ---")
    passes = 0
    failures = 0

    # Specific known stress cases
    test_cases = [
        # (Input frets, Expected output frets, allow_wide_triads flag)
        ([0, 4], [0, 2], False),  # Isolated stretch {0, 4} -> {0, 2}
        ([0, 3], [0, 2], False),  # Dyad {0, 3} -> {0, 2}
        ([1, 4], [1, 3], False),  # Dyad {1, 4} -> {1, 3}
        ([0, 1, 4], [0, 1, 2], False),  # Triad {0, 1, 4} clamped to {0, 1, 2}
        ([0, 3, 4], [2, 3, 4], False),  # Triad {0, 3, 4} clamped to {2, 3, 4}
        ([0, 2, 4], [0, 2, 3], False),  # Triad {0, 2, 4} clamped when wide disallowed
        ([0, 2, 4], [0, 2, 4], True),   # Triad {0, 2, 4} kept when wide allowed
        ([0, 1, 3], [0, 1, 2], False),  # Non-canonical triad clamped
        ([1, 2, 4], [1, 2, 3], False),  # Non-canonical triad clamped
        ([0, 1, 2, 3, 4], [0, 1, 2], False),  # 5-fret cluster -> {0, 1, 2}
        ([0, 1, 2, 3], [0, 1, 2], False),     # 4-fret cluster -> {0, 1, 2}
        ([0, 1, 2, 4], [0, 1, 2], False),     # 4-fret cluster -> {0, 1, 2}
        ([0, 1, 3, 4], [0, 1, 2], False),     # 4-fret cluster -> {0, 1, 2}
        ([0, 2, 3, 4], [0, 2, 3], False),     # 4-fret cluster -> {0, 2, 3}
        ([1, 2, 3, 4], [1, 2, 3], False),     # 4-fret cluster -> {1, 2, 3}
    ]

    for in_frets, exp_frets, allow_wide in test_cases:
        builder = ChordBuilder(max_frets=3, allow_wide_triads=allow_wide)
        notes_in = [make_note(tick=0, fret=f) for f in in_frets]
        notes_out = builder.build_chords(notes_in)
        out_frets = [n.fret.value for n in notes_out]
        if out_frets != exp_frets:
            print(f"FAILED on {in_frets} (allow_wide={allow_wide}): got {out_frets}, expected {exp_frets}")
            failures += 1
        else:
            passes += 1

        # Also verify invariants
        ok, msg = verify_invariants(notes_out, builder=builder)
        if not ok:
            print(f"FAILED invariant on {in_frets}: {msg}")
            failures += 1
        else:
            passes += 1

    print(f"Suite 5 Complete: {passes} passed, {failures} failed.")
    return passes, failures


# ---------------------------------------------------------------------------
# Suite 6: Property-Based Randomized Stress Testing (10,000 cases)
# ---------------------------------------------------------------------------


def run_suite_6_property_fuzzing(num_trials: int = 10000) -> tuple[int, int]:
    print(f"\n--- Running Suite 6: Property-Based Randomized Fuzzing ({num_trials} cases) ---")
    random.seed(42)
    passes = 0
    failures = 0

    start_time = time.time()

    for trial in range(num_trials):
        # Pick random builder settings
        max_frets = random.choice([1, 2, 3, 4, 5])
        allow_wide = random.choice([False, True])
        open_prec = random.choice([False, True])
        builder = ChordBuilder(
            max_frets=max_frets,
            allow_wide_triads=allow_wide,
            open_note_precedence=open_prec,
        )

        # Generate 1 to 10 ticks
        num_ticks = random.randint(1, 10)
        ticks = sorted(random.sample(range(0, 5000, 24), num_ticks))

        notes: list[ChartNote] = []
        for t in ticks:
            # Generate 1 to 15 notes per tick (including duplicates)
            num_notes_at_tick = random.randint(1, 15)
            for _ in range(num_notes_at_tick):
                fret = random.choice(ALL_PLAYABLE_FRETS)
                sus = random.randint(0, 1000)
                hopo = random.choice([False, True])
                notes.append(make_note(tick=t, fret=fret, sustain_length=sus, is_hopo=hopo))

        # Intentionally shuffle input notes to stress sorting and grouping
        random.shuffle(notes)

        notes_out = builder.build_chords(notes)

        ok, msg = verify_invariants(notes_out, builder=builder)
        if not ok:
            print(f"FUZZ FAILURE at trial {trial}: {msg}")
            failures += 1
            break
        else:
            passes += 1

    elapsed = time.time() - start_time
    print(f"Suite 6 Complete: {passes} passed, {failures} failed in {elapsed:.2f}s ({passes / elapsed:.1f} trials/s).")
    return passes, failures


# ---------------------------------------------------------------------------
# Suite 7: Boundary, Multi-Fret, and Deduplication Stress
# ---------------------------------------------------------------------------


def run_suite_7_dedup_and_boundary() -> tuple[int, int]:
    print("\n--- Running Suite 7: Deduplication, Max Sustain & Boundary Stress ---")
    passes = 0
    failures = 0

    builder = ChordBuilder(max_frets=3)

    # 1. 100 identical notes with increasing sustain at same tick
    tick = 192
    fret = FretType.RED
    notes = [make_note(tick=tick, fret=fret, sustain_length=i * 10, is_hopo=(i == 50)) for i in range(100)]
    out = builder.build_chords(notes)
    if len(out) == 1 and out[0].sustain_length == 990 and out[0].is_hopo is True:
        passes += 1
    else:
        print(f"FAILED 100 duplicate notes: len={len(out)}, sustain={out[0].sustain_length if out else None}")
        failures += 1

    # 2. 50 Open notes at same tick
    open_notes = [make_note(tick=tick, fret=FretType.OPEN, sustain_length=i * 5) for i in range(50)]
    out_open = builder.build_chords(open_notes)
    if len(out_open) == 1 and out_open[0].sustain_length == 245 and out_open[0].fret == FretType.OPEN:
        passes += 1
    else:
        print(f"FAILED 50 Open notes dedup: len={len(out_open)}")
        failures += 1

    # 3. Empty input list
    out_empty = builder.build_chords([])
    if out_empty == []:
        passes += 1
    else:
        print("FAILED empty input")
        failures += 1

    # 4. Alternating Open notes and Power Chords across 100 distinct ticks
    alternating_notes: list[ChartNote] = []
    for step in range(100):
        t = step * 96
        if step % 2 == 0:
            alternating_notes.append(make_note(tick=t, fret=FretType.OPEN, sustain_length=48))
        else:
            alternating_notes.append(make_note(tick=t, fret=FretType.GREEN, sustain_length=48))
            alternating_notes.append(make_note(tick=t, fret=FretType.YELLOW, sustain_length=48))

    out_alt = builder.build_chords(alternating_notes)
    ok, msg = verify_invariants(out_alt, builder=builder)
    if ok and len(out_alt) == 150:  # 50 open notes + 50 * 2 power chord notes
        passes += 1
    else:
        print(f"FAILED alternating open/power: ok={ok}, len={len(out_alt)}, msg={msg}")
        failures += 1

    print(f"Suite 7 Complete: {passes} passed, {failures} failed.")
    return passes, failures


# ---------------------------------------------------------------------------
# Main Execution
# ---------------------------------------------------------------------------


def main() -> int:
    print("=" * 70)
    print("CHORDBUILDER EMPIRICAL ORACLE & PROPERTY INVARIANT HARNESS")
    print("=" * 70)

    total_passes = 0
    total_failures = 0

    suites = [
        run_suite_1_combinatorial_power_set,
        run_suite_2_config_matrix,
        run_suite_3_canonical_power_chords,
        run_suite_4_canonical_triads,
        run_suite_5_stretch_and_reduction,
        run_suite_6_property_fuzzing,
        run_suite_7_dedup_and_boundary,
    ]

    start_total = time.time()
    for s in suites:
        p, f = s()
        total_passes += p
        total_failures += f

    total_time = time.time() - start_total

    print("\n" + "=" * 70)
    print(f"FINAL ORACLE HARNESS RESULTS: {total_passes} PASSED, {total_failures} FAILED in {total_time:.2f}s")
    print("=" * 70)

    if total_failures == 0:
        print("\nALL ERGONOMIC INVARIANTS EMPIRICALLY CONFIRMED AND VERIFIED: APPROVE")
        return 0
    else:
        print(f"\nINVARIANTS VIOLATED ({total_failures} failures): REQUEST_CHANGES")
        return 1


if __name__ == "__main__":
    sys.exit(main())
