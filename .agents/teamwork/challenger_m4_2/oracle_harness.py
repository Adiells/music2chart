"""Adversarial Property-Based Verification Oracle for Milestone 4.

Exhaustively verifies HopoEngine, SustainProcessor, and StarPowerGenerator
across mathematical invariants, combinatorial transitions, boundary conditions,
and tens of thousands of randomized fuzzing trials.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path
import random
import sys
import time

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.game_design.hopo_engine import HopoEngine
from src.game_design.star_power_generator import StarPowerGenerator
from src.game_design.sustain_processor import SustainProcessor
from src.models import ChartNote, FretType, StarPowerPhrase


# ---------------------------------------------------------------------------
# Helper Constructors
# ---------------------------------------------------------------------------

def _n(
    tick: int,
    fret: int | FretType,
    sustain_length: int = 0,
    is_hopo: bool = False,
) -> ChartNote:
    f_val = FretType(fret) if isinstance(fret, int) else fret
    return ChartNote(
        tick=tick,
        fret=f_val,
        sustain_length=sustain_length,
        is_hopo=is_hopo,
    )


# ===========================================================================
# SUITE 1: HopoEngine Formal Oracle & Property Invariants
# ===========================================================================

def oracle_expected_hopos(
    notes: Sequence[ChartNote],
    hopo_threshold: int,
) -> list[tuple[int, FretType, bool]]:
    """Ground truth formal specification oracle for HOPO states.

    Invariant:
    is_hopo is True IF AND ONLY IF:
      - not first note/event
      - current event is not a chord (len(group) == 1)
      - delta <= hopo_threshold
      - note.fret not in prev_frets
    """
    playable = [n for n in notes if n.fret not in (FretType.HOPO_FORCE, FretType.STRUM_FORCE)]
    sorted_playable = sorted(playable)

    groups: dict[int, list[ChartNote]] = defaultdict(list)
    for n in sorted_playable:
        groups[n.tick].append(n)

    sorted_ticks = sorted(groups.keys())
    expected: list[tuple[int, FretType, bool]] = []
    prev_tick: int | None = None
    prev_frets: set[FretType] = set()

    for tick in sorted_ticks:
        grp = groups[tick]
        is_chord = len(grp) > 1
        for n in grp:
            if prev_tick is None or is_chord:
                exp_hopo = False
            else:
                dist = tick - prev_tick
                if dist <= hopo_threshold and n.fret not in prev_frets:
                    exp_hopo = True
                else:
                    exp_hopo = False
            expected.append((n.tick, n.fret, exp_hopo))
        prev_tick = tick
        prev_frets = {n.fret for n in grp}

    return expected


def test_hopo_oracle_exact_boundaries() -> int:
    """Verify HOPO threshold boundary conditions for Delta in [0, 1, 64, 65, 66, 67, 96, 192]."""
    cases = 0
    engine = HopoEngine(hopo_threshold=65)

    test_deltas = [1, 24, 32, 48, 64, 65, 66, 67, 96, 192]
    frets = [FretType.GREEN, FretType.RED, FretType.YELLOW, FretType.BLUE, FretType.ORANGE, FretType.OPEN]

    for delta in test_deltas:
        for f1 in frets:
            for f2 in frets:
                notes = [_n(0, f1), _n(delta, f2)]
                result = engine.process(notes)
                expected = oracle_expected_hopos(notes, 65)

                assert len(result) == 2, f"Length mismatch for delta={delta}"
                assert result[0].is_hopo is False, "First note must be strum"
                assert (result[1].tick, result[1].fret, result[1].is_hopo) == expected[1], (
                    f"Mismatch at delta={delta}, f1={f1}, f2={f2}: got {result[1].is_hopo}, exp {expected[1][2]}"
                )
                cases += 1
    return cases


def test_hopo_oracle_chord_transitions() -> int:
    """Verify single-to-chord, chord-to-single, and chord-to-chord transitions."""
    cases = 0
    engine = HopoEngine(hopo_threshold=65)

    # All 2-fret combinations
    all_frets = [FretType.GREEN, FretType.RED, FretType.YELLOW, FretType.BLUE, FretType.ORANGE]
    chords = []
    for i in range(len(all_frets)):
        for j in range(i + 1, len(all_frets)):
            chords.append((all_frets[i], all_frets[j]))

    # 1. Chord to Single: test when single is in chord vs single not in chord
    for c in chords:
        for single_fret in all_frets:
            notes = [_n(0, c[0]), _n(0, c[1]), _n(48, single_fret)]
            result = engine.process(notes)
            expected = oracle_expected_hopos(notes, 65)

            # Assert chord notes are strums
            assert result[0].is_hopo is False
            assert result[1].is_hopo is False
            # Assert single note matches oracle
            assert (result[2].tick, result[2].fret, result[2].is_hopo) == expected[2]
            if single_fret in c:
                assert result[2].is_hopo is False, f"Expected strum for held fret {single_fret} from chord {c}"
            else:
                assert result[2].is_hopo is True, f"Expected HOPO for new fret {single_fret} from chord {c}"
            cases += 1

    # 2. Single to Chord: all chord notes must be strum
    for single_fret in all_frets:
        for c in chords:
            notes = [_n(0, single_fret), _n(48, c[0]), _n(48, c[1])]
            result = engine.process(notes)
            expected = oracle_expected_hopos(notes, 65)
            assert result[0].is_hopo is False
            assert result[1].is_hopo is False
            assert result[2].is_hopo is False
            assert [(n.tick, n.fret, n.is_hopo) for n in result] == expected
            cases += 1

    # 3. Chord to Chord: all chord notes must be strum
    for c1 in chords[:5]:
        for c2 in chords[:5]:
            notes = [_n(0, c1[0]), _n(0, c1[1]), _n(48, c2[0]), _n(48, c2[1])]
            result = engine.process(notes)
            expected = oracle_expected_hopos(notes, 65)
            assert all(n.is_hopo is False for n in result)
            assert [(n.tick, n.fret, n.is_hopo) for n in result] == expected
            cases += 1

    return cases


def test_hopo_oracle_custom_thresholds() -> int:
    """Verify custom hopo_threshold parameter behaves as a strict inequality boundary."""
    cases = 0
    for threshold in [0, 1, 10, 48, 65, 96, 192]:
        engine = HopoEngine(hopo_threshold=threshold)
        for delta in [threshold - 1, threshold, threshold + 1]:
            if delta < 0:
                continue
            notes = [_n(0, FretType.GREEN), _n(delta, FretType.RED)]
            result = engine.process(notes)
            expected = oracle_expected_hopos(notes, threshold)
            assert [(n.tick, n.fret, n.is_hopo) for n in result] == expected
            cases += 1
    return cases


def test_hopo_oracle_unsorted_and_modifiers() -> int:
    """Verify input order permutation invariance and add_force_modifiers."""
    cases = 0
    engine = HopoEngine(hopo_threshold=65)

    # Permutation invariance
    base_notes = [
        _n(0, FretType.GREEN),
        _n(48, FretType.RED),
        _n(96, FretType.RED),  # repeat -> strum
        _n(144, FretType.BLUE),  # diff -> hopo
        _n(240, FretType.YELLOW),  # gap > 65 -> strum
    ]
    ref_result = engine.process(base_notes)

    for _ in range(50):
        shuffled = list(base_notes)
        random.shuffle(shuffled)
        res = engine.process(shuffled)
        assert res == ref_result, "Unsorted input produced divergent output!"
        cases += 1

    # Force modifiers
    mod_notes = [
        _n(0, FretType.GREEN),
        _n(48, FretType.GREEN),  # repeat fast -> should get STRUM_FORCE
        _n(96, FretType.RED),
    ]
    with_mods = engine.add_force_modifiers(mod_notes)
    # Check that STRUM_FORCE is present at tick 48
    mods_at_48 = [n for n in with_mods if n.tick == 48 and n.fret == FretType.STRUM_FORCE]
    assert len(mods_at_48) == 1, "STRUM_FORCE modifier missing on fast repeat!"
    cases += 1

    return cases


def test_hopo_property_fuzzing(num_trials: int = 10000) -> int:
    """Property-based randomized fuzzing over 10,000 diverse track configurations."""
    rng = random.Random(42)
    engine = HopoEngine(hopo_threshold=65)
    frets = [FretType.GREEN, FretType.RED, FretType.YELLOW, FretType.BLUE, FretType.ORANGE, FretType.OPEN]

    for trial in range(num_trials):
        num_notes = rng.randint(1, 35)
        notes: list[ChartNote] = []
        curr_tick = 0
        for _ in range(num_notes):
            step = rng.choice([0, 12, 24, 32, 48, 64, 65, 66, 96, 192, 384])
            curr_tick += step
            f = rng.choice(frets)
            # Avoid duplicate (tick, fret)
            if not any(n.tick == curr_tick and n.fret == f for n in notes):
                notes.append(_n(curr_tick, f, sustain_length=rng.randint(0, 500)))

        # Shuffle input to stress ordering
        rng.shuffle(notes)

        result = engine.process(notes)
        expected = oracle_expected_hopos(notes, 65)

        # Invariant checks:
        # 1. Length matches playable notes
        assert len(result) == len(expected), f"Length mismatch on trial {trial}"
        # 2. Output is strictly sorted by (tick, fret)
        assert result == sorted(result), f"Output not sorted on trial {trial}"
        # 3. First note is always strum
        if result:
            first_tick = result[0].tick
            first_notes = [n for n in result if n.tick == first_tick]
            assert all(n.is_hopo is False for n in first_notes), f"First event note marked HOPO on trial {trial}"
        # 4. 100% agreement with oracle
        actual_tuples = [(n.tick, n.fret, n.is_hopo) for n in result]
        assert actual_tuples == expected, f"Oracle mismatch on trial {trial}"

    return num_trials


# ===========================================================================
# SUITE 2: SustainProcessor Formal Oracle & Property Invariants
# ===========================================================================

def oracle_expected_sustains(
    notes: Sequence[ChartNote],
    raw_durations: Sequence[int],
    min_sustain: int,
    release_margin: int,
) -> list[tuple[int, FretType, int]]:
    """Ground truth formal specification oracle for Sustain lengths.

    Invariant:
    - If duration < min_sustain: sustain == 0
    - If duration >= min_sustain:
      - If terminal tick (no next note): sustain == max(0, duration - release_margin)
      - If non-terminal tick:
        max_allowed = max(0, next_tick - tick - release_margin)
        sustain == max(0, min(duration - release_margin, max_allowed))
    """
    paired = list(zip(notes, raw_durations))
    paired.sort(key=lambda item: item[0])

    unique_ticks = sorted({item[0].tick for item in paired})
    tick_to_next_dist: dict[int, int | None] = {}
    for i, t in enumerate(unique_ticks):
        if i + 1 < len(unique_ticks):
            tick_to_next_dist[t] = unique_ticks[i + 1] - t
        else:
            tick_to_next_dist[t] = None

    expected: list[tuple[int, FretType, int]] = []
    for note, dur in paired:
        if dur < min_sustain:
            exp_sustain = 0
        else:
            base_sustain = dur - release_margin
            next_dist = tick_to_next_dist[note.tick]
            if next_dist is not None:
                max_allowed = max(0, next_dist - release_margin)
                exp_sustain = max(0, min(base_sustain, max_allowed))
            else:
                exp_sustain = max(0, base_sustain)
        expected.append((note.tick, note.fret, exp_sustain))

    return expected


def test_sustain_oracle_exact_boundaries() -> int:
    """Verify cutoff boundary around 90 and collision boundary around 24."""
    cases = 0
    processor = SustainProcessor(min_sustain_ticks=90, release_margin=24)

    # 1. Cutoff boundaries: 0, 88, 89, 90, 91, 192 (terminal isolated note)
    for dur in [0, 24, 48, 88, 89, 90, 91, 100, 114, 192]:
        notes = [_n(0, FretType.GREEN, sustain_length=dur)]
        result = processor.process(notes)
        expected = oracle_expected_sustains(notes, [dur], 90, 24)
        assert len(result) == 1
        assert (result[0].tick, result[0].fret, result[0].sustain_length) == expected[0]
        if dur < 90:
            assert result[0].sustain_length == 0, f"Expected 0 sustain for dur={dur}"
        else:
            assert result[0].sustain_length == dur - 24, f"Expected {dur - 24} for dur={dur}"
        cases += 1

    # 2. Collision spacing boundaries: fixed duration=192, varying delta to next note
    for delta in [0, 1, 12, 23, 24, 25, 30, 48, 96, 192, 384]:
        notes = [_n(0, FretType.GREEN, sustain_length=192), _n(delta, FretType.RED, sustain_length=0)]
        if delta == 0:
            # simultaneous chord notes: both keep full duration
            result = processor.process(notes)
            assert result[0].sustain_length == 168
            assert result[1].sustain_length == 0
        else:
            result = processor.process(notes)
            expected = oracle_expected_sustains(notes, [192, 0], 90, 24)
            assert (result[0].tick, result[0].fret, result[0].sustain_length) == expected[0]
            if delta <= 24:
                assert result[0].sustain_length == 0, f"Expected 0 sustain for collision delta={delta}"
            elif delta < 192:
                assert result[0].sustain_length == delta - 24, f"Expected {delta - 24} for delta={delta}"
            else:
                assert result[0].sustain_length == 168, f"Expected 168 for delta={delta}"
        cases += 1

    return cases


def test_sustain_oracle_mapping_and_order() -> int:
    """Verify Sequence, Mapping[(tick, fret), int], Mapping[tick, int], and unsorted inputs."""
    cases = 0
    processor = SustainProcessor(min_sustain_ticks=90, release_margin=24)

    # 1. Unsorted inputs with Sequence[int]
    notes = [
        _n(384, FretType.BLUE, sustain_length=0),
        _n(0, FretType.GREEN, sustain_length=0),
        _n(192, FretType.RED, sustain_length=0),
    ]
    # Corresponding raw durations in the original input order
    raw_durs = [500, 192, 90]
    result = processor.process(notes, durations=raw_durs)

    # In chronological order: tick 0 (dur 192), tick 192 (dur 90), tick 384 (dur 500)
    # tick 0: next_dist=192, min(168, 168) = 168
    # tick 192: next_dist=192, min(66, 168) = 66
    # tick 384: terminal, 500 - 24 = 476
    assert [n.tick for n in result] == [0, 192, 384]
    assert [n.sustain_length for n in result] == [168, 66, 476]
    cases += 1

    # 2. Mapping[(tick, fret), int]
    dur_map_tuples = {
        (0, FretType.GREEN): 192,
        (192, FretType.RED): 90,
        (384, FretType.BLUE): 500,
    }
    res_map = processor.process(notes, durations=dur_map_tuples)
    assert [n.sustain_length for n in res_map] == [168, 66, 476]
    cases += 1

    # 3. Mapping with int keys (0, 1, 3 instead of FretType enum)
    dur_map_ints = {
        (0, 0): 192,
        (192, 1): 90,
        (384, 3): 500,
    }
    res_ints = processor.process(notes, durations=dur_map_ints)
    assert [n.sustain_length for n in res_ints] == [168, 66, 476]
    cases += 1

    # 4. Mapping[tick, int] fallback
    dur_map_ticks = {0: 192, 192: 90, 384: 500}
    res_ticks = processor.process(notes, durations=dur_map_ticks)
    assert [n.sustain_length for n in res_ticks] == [168, 66, 476]
    cases += 1

    return cases


def test_sustain_property_fuzzing(num_trials: int = 10000) -> int:
    """Property-based randomized fuzzing over 10,000 diverse track configurations."""
    rng = random.Random(43)
    processor = SustainProcessor(min_sustain_ticks=90, release_margin=24)
    frets = [FretType.GREEN, FretType.RED, FretType.YELLOW, FretType.BLUE, FretType.ORANGE, FretType.OPEN]

    for trial in range(num_trials):
        num_notes = rng.randint(1, 30)
        notes: list[ChartNote] = []
        raw_durs: list[int] = []
        curr_tick = 0
        for _ in range(num_notes):
            curr_tick += rng.choice([0, 16, 24, 48, 96, 192, 384])
            f = rng.choice(frets)
            dur = rng.choice([0, 20, 24, 48, 89, 90, 95, 120, 192, 384, 1000])
            if not any(n.tick == curr_tick and n.fret == f for n in notes):
                notes.append(_n(curr_tick, f, sustain_length=0))
                raw_durs.append(dur)

        # Randomize input presentation order
        combined = list(zip(notes, raw_durs))
        rng.shuffle(combined)
        shuffled_notes = [c[0] for c in combined]
        shuffled_durs = [c[1] for c in combined]

        result = processor.process(shuffled_notes, durations=shuffled_durs)
        expected = oracle_expected_sustains(shuffled_notes, shuffled_durs, 90, 24)

        # Invariants:
        # 1. Output length matches input
        assert len(result) == len(expected)
        # 2. Output is sorted
        assert result == sorted(result)
        # 3. Sustain values are non-negative
        assert all(n.sustain_length >= 0 for n in result)
        # 4. Exact oracle match
        actual_tuples = [(n.tick, n.fret, n.sustain_length) for n in result]
        assert actual_tuples == expected, f"Sustain oracle mismatch on trial {trial}"

        # 5. Collision clearance invariant: no note sustain extends past next unique tick - 24
        unique_ticks = sorted({n.tick for n in result})
        for i, t in enumerate(unique_ticks[:-1]):
            next_t = unique_ticks[i + 1]
            for n in result:
                if n.tick == t and n.sustain_length > 0:
                    assert n.tick + n.sustain_length <= next_t - 24, (
                        f"Collision tail overlap violation on trial {trial}: note at {n.tick} with sustain "
                        f"{n.sustain_length} extends past {next_t - 24}"
                    )

    return num_trials


# ===========================================================================
# SUITE 3: StarPowerGenerator Formal Oracle & Property Invariants
# ===========================================================================

def test_star_power_oracle_invariants(num_trials: int = 5000) -> int:
    """Formal property oracle testing StarPowerGenerator across 5,000 track layouts."""
    rng = random.Random(44)

    for trial in range(num_trials):
        # Pick varied parameters
        measure_ticks = rng.choice([384, 768, 960])
        interval_measures = rng.randint(2, 20)
        phrase_len_measures = rng.randint(1, 4)
        min_notes = rng.randint(2, 6)

        gen = StarPowerGenerator(
            measure_ticks=measure_ticks,
            interval_measures=interval_measures,
            phrase_length_measures=phrase_len_measures,
            min_notes=min_notes,
        )

        num_notes = rng.randint(0, 80)
        notes: list[ChartNote] = []
        curr_tick = rng.randint(0, 1000)

        for _ in range(num_notes):
            # Include potential dense clusters and long silence gaps
            gap_type = rng.choice(["rapid", "normal", "gap"])
            if gap_type == "rapid":
                curr_tick += rng.choice([0, 24, 48])
            elif gap_type == "normal":
                curr_tick += rng.choice([96, 192])
            else:
                curr_tick += measure_ticks * rng.randint(5, 30)  # Silence gap

            notes.append(_n(curr_tick, rng.randint(0, 4)))

        # Shuffle notes
        rng.shuffle(notes)

        phrases = gen.generate(notes)

        expected_phrase_len = phrase_len_measures * measure_ticks

        # Invariant 1: If input notes < min_notes, phrases MUST be empty
        if len(notes) < min_notes:
            assert phrases == [], f"Expected empty phrases for {len(notes)} notes on trial {trial}"

        # Invariant 2: Strictly sorted phrases by tick
        assert phrases == sorted(phrases, key=lambda p: p.tick), f"Phrases not sorted on trial {trial}"

        # Invariant 3: Non-negative tick and positive length matching expected
        for p in phrases:
            assert p.tick >= 0, f"Negative phrase tick {p.tick} on trial {trial}"
            assert p.length == expected_phrase_len, (
                f"Phrase length {p.length} != {expected_phrase_len} on trial {trial}"
            )

        # Invariant 4: No overlapping phrases: p[i].tick + p[i].length <= p[i+1].tick
        for i in range(len(phrases) - 1):
            assert phrases[i].tick + phrases[i].length <= phrases[i + 1].tick, (
                f"Star power phrase overlap detected: phrase {i} [{phrases[i].tick}, "
                f"{phrases[i].tick + phrases[i].length}) overlaps phrase {i+1} at {phrases[i+1].tick} on trial {trial}"
            )

        # Invariant 5: Each phrase encompasses >= min_notes
        for p in phrases:
            notes_in_p = [n for n in notes if p.tick <= n.tick < p.tick + p.length]
            assert len(notes_in_p) >= min_notes, (
                f"Star power phrase at {p.tick} has only {len(notes_in_p)} notes (min {min_notes}) on trial {trial}"
            )

        # Invariant 6: Phrase start tick coincides with a note tick
        for p in phrases:
            assert any(n.tick == p.tick for n in notes), (
                f"Star power phrase starts at {p.tick} with no note onset on trial {trial}"
            )

    return num_trials


# ===========================================================================
# SUITE 4: Adversarial Edge Cases, Parameter Validation & Interface Aliases
# ===========================================================================

def test_adversarial_edge_cases() -> int:
    """Stress test boundary edge cases, parameter validation, and API aliases."""
    cases = 0

    # 1. Negative parameter exceptions
    try:
        HopoEngine(hopo_threshold=-1)
        assert False, "Should raise ValueError on negative hopo_threshold"
    except ValueError:
        cases += 1

    try:
        SustainProcessor(min_sustain_ticks=-5)
        assert False, "Should raise ValueError on negative min_sustain_ticks"
    except ValueError:
        cases += 1

    try:
        SustainProcessor(release_margin=-10)
        assert False, "Should raise ValueError on negative release_margin"
    except ValueError:
        cases += 1

    for param_name, invalid_val in [
        ("measure_ticks", 0),
        ("interval_measures", 0),
        ("phrase_length_measures", 0),
        ("min_notes", 0),
        ("measure_ticks", -10),
    ]:
        try:
            StarPowerGenerator(**{param_name: invalid_val})
            assert False, f"Should raise ValueError on {param_name}={invalid_val}"
        except ValueError:
            cases += 1

    # 2. Empty input edge cases
    h_eng = HopoEngine()
    s_proc = SustainProcessor()
    sp_gen = StarPowerGenerator()

    assert h_eng.process([]) == []
    assert s_proc.process([]) == []
    assert sp_gen.generate([]) == []
    cases += 3

    # 3. Single note edge case
    single_note = [_n(100, FretType.GREEN, sustain_length=192)]
    h_res = h_eng.process(single_note)
    assert len(h_res) == 1 and h_res[0].is_hopo is False
    s_res = s_proc.process(single_note)
    assert len(s_res) == 1 and s_res[0].sustain_length == 168  # terminal note keeps 192 - 24
    sp_res = sp_gen.generate(single_note)
    assert sp_res == []  # 1 < 4 min_notes
    cases += 3

    # 4. HopoEngine threshold = 0
    h_zero = HopoEngine(hopo_threshold=0)
    notes_zero = [_n(0, 0), _n(1, 1), _n(2, 2)]
    res_zero = h_zero.process(notes_zero)
    assert all(n.is_hopo is False for n in res_zero)
    cases += 1

    # 5. SustainProcessor min_sustain = 0
    s_zero = SustainProcessor(min_sustain_ticks=0, release_margin=24)
    res_s_zero = s_zero.process([_n(0, 0, sustain_length=30)])
    assert res_s_zero[0].sustain_length == 6  # 30 - 24 = 6
    cases += 1

    # 6. API Aliases Verification
    notes_alias = [_n(0, 0), _n(48, 1)]
    assert h_eng.process(notes_alias) == h_eng.calculate_hopos(notes_alias)
    assert h_eng.process(notes_alias) == h_eng.process_hopos(notes_alias)
    assert h_eng.process(notes_alias) == h_eng(notes_alias)
    cases += 3

    assert s_proc.process(notes_alias) == s_proc.calculate_sustains(notes_alias)
    assert s_proc.process(notes_alias) == s_proc.process_notes(notes_alias)
    assert s_proc.process(notes_alias) == s_proc(notes_alias)
    cases += 3

    notes_sp = [_n(t, 0) for t in range(0, 2000, 48)]
    assert sp_gen.generate(notes_sp) == sp_gen.generate_phrases(notes_sp)
    assert sp_gen.generate(notes_sp) == sp_gen.generate_star_power(notes_sp)
    assert sp_gen.generate(notes_sp) == sp_gen(notes_sp)
    cases += 3

    # 7. Extreme tick values (e.g. 10,000,000 ticks)
    extreme_notes = [
        _n(10_000_000, FretType.GREEN, sustain_length=500),
        _n(10_000_048, FretType.RED, sustain_length=192),
    ]
    h_ext = h_eng.process(extreme_notes)
    assert h_ext[0].is_hopo is False
    assert h_ext[1].is_hopo is True
    s_ext = s_proc.process(extreme_notes)
    assert s_ext[0].sustain_length == 24  # 48 - 24
    assert s_ext[1].sustain_length == 168  # 192 - 24
    cases += 2

    return cases


# ===========================================================================
# HARNESS MAIN EXECUTION
# ===========================================================================

def main() -> None:
    print("=" * 72)
    print("MILESTONE 4 EMPIRICAL ADVERSARIAL ORACLE HARNESS")
    print("=" * 72)

    t0 = time.perf_counter()
    total_passed = 0

    # Suite 1
    print("\n--- Running Suite 1: HopoEngine Formal Oracle & Invariants ---")
    c1 = test_hopo_oracle_exact_boundaries()
    print(f"  [1.1] Exact Threshold Boundaries: {c1} tests passed.")
    c2 = test_hopo_oracle_chord_transitions()
    print(f"  [1.2] Combinatorial Chord & Single Transitions: {c2} tests passed.")
    c3 = test_hopo_oracle_custom_thresholds()
    print(f"  [1.3] Custom Hopo Thresholds: {c3} tests passed.")
    c4 = test_hopo_oracle_unsorted_and_modifiers()
    print(f"  [1.4] Permutation Invariance & Force Modifiers: {c4} tests passed.")
    c5 = test_hopo_property_fuzzing(10000)
    print(f"  [1.5] Property-Based Randomized Fuzzing: {c5} trials passed.")
    s1_total = c1 + c2 + c3 + c4 + c5
    total_passed += s1_total

    # Suite 2
    print("\n--- Running Suite 2: SustainProcessor Formal Oracle & Invariants ---")
    c6 = test_sustain_oracle_exact_boundaries()
    print(f"  [2.1] Exact Cutoff & Collision Margin Boundaries: {c6} tests passed.")
    c7 = test_sustain_oracle_mapping_and_order()
    print(f"  [2.2] Heterogeneous Mappings & Unsorted Inputs: {c7} tests passed.")
    c8 = test_sustain_property_fuzzing(10000)
    print(f"  [2.3] Property-Based Randomized Fuzzing: {c8} trials passed.")
    s2_total = c6 + c7 + c8
    total_passed += s2_total

    # Suite 3
    print("\n--- Running Suite 3: StarPowerGenerator Formal Oracle & Invariants ---")
    c9 = test_star_power_oracle_invariants(5000)
    print(f"  [3.1] Randomized Track Cadence & Non-Overlap Invariants: {c9} trials passed.")
    s3_total = c9
    total_passed += s3_total

    # Suite 4
    print("\n--- Running Suite 4: Adversarial Edge Cases & Parameter Validation ---")
    c10 = test_adversarial_edge_cases()
    print(f"  [4.1] Edge Cases, Validations & Aliases: {c10} tests passed.")
    total_passed += c10

    elapsed = time.perf_counter() - t0

    print("\n" + "=" * 72)
    print(f"FINAL ORACLE HARNESS RESULTS: {total_passed} PASSED, 0 FAILED in {elapsed:.2f}s")
    print(f"Speed: {total_passed / elapsed:.1f} verifications/second")
    print("=" * 72)


if __name__ == "__main__":
    main()
