"""Unit tests for ergonomic chord formation and playability constraints engine (ChordBuilder)."""

from __future__ import annotations

import pytest

from src.game_design.chord_builder import ChordBuilder
from src.models.chart import ChartNote, FretType

# ---------------------------------------------------------------------------
# Test Helpers & Fixtures
# ---------------------------------------------------------------------------


def _make_note(
    tick: int,
    fret: int | FretType,
    sustain_length: int = 0,
    is_hopo: bool = False,
) -> ChartNote:
    """Helper to synthesize a ChartNote."""
    fret_val = FretType(fret) if isinstance(fret, int) else fret
    return ChartNote(
        tick=tick,
        fret=fret_val,
        sustain_length=sustain_length,
        is_hopo=is_hopo,
    )


def _frets_at_tick(notes: list[ChartNote], tick: int) -> tuple[int, ...]:
    """Return sorted tuple of fret integer values present at a given tick."""
    return tuple(sorted(n.fret.value for n in notes if n.tick == tick))


@pytest.fixture
def default_builder() -> ChordBuilder:
    """Return a standard ChordBuilder with max_frets=3."""
    return ChordBuilder(max_frets=3)


# ---------------------------------------------------------------------------
# 1. Grouping Simultaneous Notes at Identical Ticks
# ---------------------------------------------------------------------------


def test_group_simultaneous_notes_identical_tick(default_builder: ChordBuilder) -> None:
    """Verify notes occurring at identical ticks are grouped into chords while preserving separate ticks."""
    notes = [
        _make_note(tick=0, fret=FretType.GREEN),
        _make_note(tick=0, fret=FretType.RED),
        _make_note(tick=192, fret=FretType.YELLOW),
        _make_note(tick=192, fret=FretType.BLUE),
    ]

    result = default_builder.build_chords(notes)
    assert len(result) == 4
    assert _frets_at_tick(result, 0) == (0, 1)
    assert _frets_at_tick(result, 192) == (2, 3)


def test_grouping_preserves_chronological_and_fret_sorting(
    default_builder: ChordBuilder,
) -> None:
    """Verify output is strictly sorted by tick ascending, and then by fret ascending."""
    unsorted_notes = [
        _make_note(tick=192, fret=FretType.BLUE),
        _make_note(tick=0, fret=FretType.YELLOW),
        _make_note(tick=0, fret=FretType.GREEN),
        _make_note(tick=192, fret=FretType.RED),
    ]

    result = default_builder.build_chords(unsorted_notes)
    assert len(result) == 4

    # Verify chronological ordering
    assert [n.tick for n in result] == [0, 0, 192, 192]
    # Verify fret ordering
    assert [n.fret.value for n in result] == [0, 2, 1, 3]


def test_grouping_deduplicates_identical_tick_and_fret(
    default_builder: ChordBuilder,
) -> None:
    """Verify duplicate notes sharing identical (tick, fret) are merged into one, taking max sustain."""
    notes = [
        _make_note(tick=0, fret=FretType.GREEN, sustain_length=0),
        _make_note(tick=0, fret=FretType.GREEN, sustain_length=96),
        _make_note(tick=0, fret=FretType.RED, sustain_length=48),
    ]

    result = default_builder.build_chords(notes)
    assert len(result) == 2
    assert _frets_at_tick(result, 0) == (0, 1)

    green_note = next(n for n in result if n.fret == FretType.GREEN)
    assert green_note.sustain_length == 96


def test_grouping_preserves_note_attributes(default_builder: ChordBuilder) -> None:
    """Verify sustain lengths and hopo attributes are accurately retained."""
    notes = [
        _make_note(tick=96, fret=FretType.RED, sustain_length=120, is_hopo=True),
        _make_note(tick=96, fret=FretType.YELLOW, sustain_length=120, is_hopo=True),
    ]

    result = default_builder.build_chords(notes)
    assert len(result) == 2
    for n in result:
        assert n.sustain_length == 120
        assert n.is_hopo is True


# ---------------------------------------------------------------------------
# 2. Canonical Power Chords Preserved
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "power_chord",
    [
        (0, 1),  # Green + Red
        (0, 2),  # Green + Yellow
        (1, 2),  # Red + Yellow
        (1, 3),  # Red + Blue
        (2, 3),  # Yellow + Blue
        (2, 4),  # Yellow + Orange
        (3, 4),  # Blue + Orange
    ],
)
def test_canonical_power_chords_preserved(
    default_builder: ChordBuilder,
    power_chord: tuple[int, int],
) -> None:
    """Verify all 7 canonical 2-note power chords are preserved verbatim."""
    notes = [
        _make_note(tick=0, fret=power_chord[0]),
        _make_note(tick=0, fret=power_chord[1]),
    ]

    result = default_builder.build_chords(notes)
    assert len(result) == 2
    assert _frets_at_tick(result, 0) == power_chord


# ---------------------------------------------------------------------------
# 3. Canonical Triads Preserved
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "triad",
    [
        (0, 1, 2),  # Green + Red + Yellow
        (0, 2, 3),  # Green + Yellow + Blue
        (1, 2, 3),  # Red + Yellow + Blue
        (2, 3, 4),  # Yellow + Blue + Orange
    ],
)
def test_canonical_triads_preserved(
    default_builder: ChordBuilder,
    triad: tuple[int, int, int],
) -> None:
    """Verify all 4 canonical 3-note triads are preserved verbatim."""
    notes = [
        _make_note(tick=0, fret=triad[0]),
        _make_note(tick=0, fret=triad[1]),
        _make_note(tick=0, fret=triad[2]),
    ]

    result = default_builder.build_chords(notes)
    assert len(result) == 3
    assert _frets_at_tick(result, 0) == triad


# ---------------------------------------------------------------------------
# 4. Polyphonic Clusters Simplified (<= 3 Frets)
# ---------------------------------------------------------------------------


def test_four_note_cluster_0123_simplified(default_builder: ChordBuilder) -> None:
    """Verify 4-note cluster [0, 1, 2, 3] simplifies to at most 3 frets in canonical form."""
    notes = [_make_note(tick=0, fret=f) for f in [0, 1, 2, 3]]

    result = default_builder.build_chords(notes)
    frets = _frets_at_tick(result, 0)
    assert len(frets) <= 3
    assert len(frets) >= 2
    # Must be one of the canonical triads or power chords
    assert frets in {
        (0, 1, 2),
        (0, 2, 3),
        (1, 2, 3),
        (0, 1),
        (0, 2),
    }


def test_four_note_cluster_0124_simplified_and_eliminates_stretch(
    default_builder: ChordBuilder,
) -> None:
    """Verify 4-note cluster [0, 1, 2, 4] eliminates 0+4 stretch and produces canonical triad (0, 1, 2)."""
    notes = [_make_note(tick=0, fret=f) for f in [0, 1, 2, 4]]

    result = default_builder.build_chords(notes)
    frets = _frets_at_tick(result, 0)
    assert len(frets) <= 3
    assert not ({0, 4}.issubset(frets))
    assert frets == (0, 1, 2)


def test_four_note_cluster_0134_simplified_and_eliminates_stretch(
    default_builder: ChordBuilder,
) -> None:
    """Verify 4-note cluster [0, 1, 3, 4] eliminates 0+4 stretch and yields <= 3 frets."""
    notes = [_make_note(tick=0, fret=f) for f in [0, 1, 3, 4]]

    result = default_builder.build_chords(notes)
    frets = _frets_at_tick(result, 0)
    assert len(frets) <= 3
    assert not ({0, 4}.issubset(frets))


def test_four_note_cluster_0234_simplified_and_eliminates_stretch(
    default_builder: ChordBuilder,
) -> None:
    """Verify 4-note cluster [0, 2, 3, 4] eliminates 0+4 stretch and yields canonical triad."""
    notes = [_make_note(tick=0, fret=f) for f in [0, 2, 3, 4]]

    result = default_builder.build_chords(notes)
    frets = _frets_at_tick(result, 0)
    assert len(frets) <= 3
    assert not ({0, 4}.issubset(frets))
    assert frets in {(0, 2, 3), (2, 3, 4)}


def test_four_note_cluster_1234_simplified(default_builder: ChordBuilder) -> None:
    """Verify 4-note cluster [1, 2, 3, 4] simplifies to canonical triad (1, 2, 3) or (2, 3, 4)."""
    notes = [_make_note(tick=0, fret=f) for f in [1, 2, 3, 4]]

    result = default_builder.build_chords(notes)
    frets = _frets_at_tick(result, 0)
    assert len(frets) <= 3
    assert frets in {(1, 2, 3), (2, 3, 4)}


def test_five_note_cluster_simplified(default_builder: ChordBuilder) -> None:
    """Verify 5-note cluster [0, 1, 2, 3, 4] simplifies to at most 3 frets without 0+4 stretch."""
    notes = [_make_note(tick=0, fret=f) for f in [0, 1, 2, 3, 4]]

    result = default_builder.build_chords(notes)
    frets = _frets_at_tick(result, 0)
    assert len(frets) <= 3
    assert not ({0, 4}.issubset(frets))
    assert frets in {(0, 1, 2), (0, 2, 3), (1, 2, 3), (2, 3, 4)}


def test_custom_max_frets_two() -> None:
    """Verify builder with max_frets=2 reduces triads and 4-note clusters to <= 2 frets."""
    builder_2 = ChordBuilder(max_frets=2)
    notes = [_make_note(tick=0, fret=f) for f in [0, 1, 2]]

    result = builder_2.build_chords(notes)
    frets = _frets_at_tick(result, 0)
    assert len(frets) <= 2
    assert frets in {(0, 1), (0, 2)}


def test_custom_max_frets_one() -> None:
    """Verify builder with max_frets=1 reduces chords to single root note."""
    builder_1 = ChordBuilder(max_frets=1)
    notes = [_make_note(tick=0, fret=f) for f in [0, 2, 3]]

    result = builder_1.build_chords(notes)
    frets = _frets_at_tick(result, 0)
    assert len(frets) == 1
    assert frets == (0,)


# ---------------------------------------------------------------------------
# 5. Elimination of Forbidden Stretches & Generalized Clamping
# ---------------------------------------------------------------------------


def test_isolated_0_4_stretch_eliminated(default_builder: ChordBuilder) -> None:
    """Verify isolated 0+4 (Green + Orange) stretch is eliminated from output."""
    notes = [
        _make_note(tick=0, fret=FretType.GREEN),
        _make_note(tick=0, fret=FretType.ORANGE),
    ]

    result = default_builder.build_chords(notes)
    frets = _frets_at_tick(result, 0)
    assert frets != (0, 4)
    assert not ({0, 4}.issubset(frets))
    assert frets in {(0,), (0, 2)}


def test_wide_dyads_clamping(default_builder: ChordBuilder) -> None:
    """Verify wide dyads with span > 2 are clamped: (0, 3) -> (0, 2) and (1, 4) -> (1, 3)."""
    notes = [
        _make_note(tick=96, fret=0),
        _make_note(tick=96, fret=3),
        _make_note(tick=192, fret=1),
        _make_note(tick=192, fret=4),
    ]

    result = default_builder.build_chords(notes)
    assert _frets_at_tick(result, 96) == (0, 2)
    assert _frets_at_tick(result, 192) == (1, 3)


@pytest.mark.parametrize(
    "triad_with_04",
    [
        (0, 1, 4),
        (0, 2, 4),
        (0, 3, 4),
    ],
)
def test_three_note_with_0_4_eliminated(
    default_builder: ChordBuilder,
    triad_with_04: tuple[int, int, int],
) -> None:
    """Verify 3-note inputs containing both 0 and 4 eliminate the stretch."""
    notes = [_make_note(tick=0, fret=f) for f in triad_with_04]

    result = default_builder.build_chords(notes)
    frets = _frets_at_tick(result, 0)
    assert not ({0, 4}.issubset(frets))
    assert len(frets) <= 3


def test_triad_0_2_4_handling_strict() -> None:
    """Verify (0, 2, 4) is simplified to canonical triad (0, 2, 3) when allow_wide_triads=False."""
    builder = ChordBuilder(allow_wide_triads=False, max_frets=3)
    notes = [_make_note(tick=0, fret=f, sustain_length=96) for f in [0, 2, 4]]

    result = builder.build_chords(notes)
    assert _frets_at_tick(result, 0) == (0, 2, 3)


def test_triad_0_2_4_handling_wide() -> None:
    """Verify (0, 2, 4) is preserved as G-Y-O triad when allow_wide_triads=True."""
    builder = ChordBuilder(allow_wide_triads=True, max_frets=3)
    notes = [_make_note(tick=0, fret=f, sustain_length=96) for f in [0, 2, 4]]

    result = builder.build_chords(notes)
    assert _frets_at_tick(result, 0) == (0, 2, 4)


def test_asymmetric_triads_simplification(default_builder: ChordBuilder) -> None:
    """Verify asymmetric triads (0, 1, 4) -> (0, 1, 2) and (0, 3, 4) -> (2, 3, 4)."""
    notes = [
        _make_note(tick=0, fret=0),
        _make_note(tick=0, fret=1),
        _make_note(tick=0, fret=4),
        _make_note(tick=96, fret=0),
        _make_note(tick=96, fret=3),
        _make_note(tick=96, fret=4),
    ]

    result = default_builder.build_chords(notes)
    assert _frets_at_tick(result, 0) in {(0, 1, 2), (0, 1)}
    assert _frets_at_tick(result, 96) in {(2, 3, 4), (0, 2, 3), (2, 3), (0, 2)}


def test_repeated_0_4_in_sequence_all_eliminated(default_builder: ChordBuilder) -> None:
    """Verify sequence of 0+4 stretches across multiple ticks all have the stretch eliminated."""
    notes = [
        _make_note(tick=0, fret=0),
        _make_note(tick=0, fret=4),
        _make_note(tick=96, fret=0),
        _make_note(tick=96, fret=4),
        _make_note(tick=192, fret=0),
        _make_note(tick=192, fret=4),
    ]

    result = default_builder.build_chords(notes)
    for t in [0, 96, 192]:
        frets = _frets_at_tick(result, t)
        assert not ({0, 4}.issubset(frets))


# ---------------------------------------------------------------------------
# 6. Open Note Exclusivity
# ---------------------------------------------------------------------------


def test_open_note_isolated_preserved(default_builder: ChordBuilder) -> None:
    """Verify isolated Open note (7) is preserved intact."""
    notes = [_make_note(tick=0, fret=FretType.OPEN, sustain_length=48)]

    result = default_builder.build_chords(notes)
    assert len(result) == 1
    assert result[0].fret == FretType.OPEN
    assert result[0].sustain_length == 48


def test_open_note_with_single_fretted_note_exclusivity(
    default_builder: ChordBuilder,
) -> None:
    """Verify Open note and fretted note at identical tick never coexist (fretted notes take default precedence)."""
    notes = [
        _make_note(tick=0, fret=FretType.OPEN),
        _make_note(tick=0, fret=FretType.GREEN),
    ]

    result = default_builder.build_chords(notes)
    frets = _frets_at_tick(result, 0)
    assert not (7 in frets and any(f in frets for f in [0, 1, 2, 3, 4]))
    # Prompt 7.2: default open_note_precedence=False gives precedence to fretted notes
    assert frets == (0,)


def test_open_note_with_power_chord_exclusivity(default_builder: ChordBuilder) -> None:
    """Verify Open note conflicting with a power chord enforces exclusivity (fretted precedence)."""
    notes = [
        _make_note(tick=0, fret=FretType.OPEN),
        _make_note(tick=0, fret=FretType.GREEN),
        _make_note(tick=0, fret=FretType.RED),
    ]

    result = default_builder.build_chords(notes)
    frets = _frets_at_tick(result, 0)
    assert not (7 in frets and any(f in frets for f in [0, 1, 2, 3, 4]))
    assert frets == (0, 1)


def test_open_note_with_triad_exclusivity(default_builder: ChordBuilder) -> None:
    """Verify Open note conflicting with a triad enforces exclusivity (fretted precedence)."""
    notes = [
        _make_note(tick=0, fret=FretType.OPEN),
        _make_note(tick=0, fret=0),
        _make_note(tick=0, fret=1),
        _make_note(tick=0, fret=2),
    ]

    result = default_builder.build_chords(notes)
    frets = _frets_at_tick(result, 0)
    assert not (7 in frets and any(f in frets for f in [0, 1, 2, 3, 4]))
    assert frets in {(0, 1), (0, 1, 2)}


def test_open_note_alternating_with_fretted_chords(default_builder: ChordBuilder) -> None:
    """Verify sequence alternating between Open notes and fretted chords preserves both on their respective ticks."""
    notes = [
        _make_note(tick=0, fret=FretType.OPEN),
        _make_note(tick=96, fret=0),
        _make_note(tick=96, fret=1),
        _make_note(tick=192, fret=FretType.OPEN),
        _make_note(tick=288, fret=0),
        _make_note(tick=288, fret=2),
        _make_note(tick=288, fret=3),
    ]

    result = default_builder.build_chords(notes)
    assert _frets_at_tick(result, 0) == (7,)
    assert _frets_at_tick(result, 96) == (0, 1)
    assert _frets_at_tick(result, 192) == (7,)
    assert _frets_at_tick(result, 288) in {(0, 2, 3), (0, 2)}


def test_open_note_precedence_inversion() -> None:
    """Verify open notes take precedence when open_note_precedence=True."""
    builder = ChordBuilder(open_note_precedence=True)
    notes = [
        _make_note(tick=0, fret=FretType.OPEN),
        _make_note(tick=0, fret=0),
        _make_note(tick=0, fret=2),
    ]

    result = builder.build_chords(notes)
    frets = _frets_at_tick(result, 0)
    assert frets == (7,)


# ---------------------------------------------------------------------------
# Prompt 7.2: Fast-Run Collapsing, Dyad Clamping & Triad Permits
# ---------------------------------------------------------------------------


def test_fast_run_single_note_collapsing() -> None:
    """Prompt 7.2: In passages with inter-note spacing <= 48 ticks, collapse chords to dominant root note."""
    builder = ChordBuilder(collapse_fast_runs=True, fast_run_tick_threshold=48)

    # 16th-note run: spacing of 48 ticks between consecutive notes
    notes = [
        _make_note(tick=0, fret=0),
        _make_note(tick=0, fret=2),  # Power chord at tick 0
        _make_note(tick=48, fret=1),
        _make_note(tick=48, fret=3),  # Power chord at tick 48
        _make_note(tick=96, fret=2),
        _make_note(tick=96, fret=4),  # Power chord at tick 96
    ]

    result = builder.build_chords(notes)
    # Each chord is collapsed to its single dominant root note (lowest fret)
    assert _frets_at_tick(result, 0) == (0,)
    assert _frets_at_tick(result, 48) == (1,)
    assert _frets_at_tick(result, 96) == (2,)


def test_fast_run_collapsing_disabled() -> None:
    """Prompt 7.2: Verify collapse_fast_runs=False preserves chords even in rapid runs."""
    builder = ChordBuilder(collapse_fast_runs=False)

    notes = [
        _make_note(tick=0, fret=0),
        _make_note(tick=0, fret=2),
        _make_note(tick=48, fret=1),
        _make_note(tick=48, fret=3),
    ]

    result = builder.build_chords(notes)
    assert _frets_at_tick(result, 0) == (0, 2)
    assert _frets_at_tick(result, 48) == (1, 3)


def test_slow_passage_preserves_chords() -> None:
    """Prompt 7.2: Verify inter-note spacing > 48 ticks does not trigger fast-run collapsing."""
    builder = ChordBuilder(collapse_fast_runs=True, fast_run_tick_threshold=48)

    # 8th-note passage: spacing of 96 ticks (> 48 ticks threshold)
    notes = [
        _make_note(tick=0, fret=0),
        _make_note(tick=0, fret=2),
        _make_note(tick=96, fret=1),
        _make_note(tick=96, fret=3),
    ]

    result = builder.build_chords(notes)
    assert _frets_at_tick(result, 0) == (0, 2)
    assert _frets_at_tick(result, 96) == (1, 3)


def test_default_max_frets_and_accented_triads() -> None:
    """Prompt 7.2: Default max_frets=2, permitting 3-note triads only on accented beats with sustain >= 96."""
    builder = ChordBuilder()
    assert builder.max_frets == 2

    # Case 1: Accented beat (tick 0 % 96 == 0) with sustain 96 -> 3-note triad permitted
    triad_sustained = [
        _make_note(tick=0, fret=0, sustain_length=96),
        _make_note(tick=0, fret=2, sustain_length=96),
        _make_note(tick=0, fret=3, sustain_length=96),
    ]
    res1 = builder.build_chords(triad_sustained)
    assert _frets_at_tick(res1, 0) == (0, 2, 3)

    # Case 2: Accented beat (tick 0) with sustain 0 (< 96) -> clamped to 2-note power chord
    triad_short = [
        _make_note(tick=0, fret=0, sustain_length=0),
        _make_note(tick=0, fret=2, sustain_length=0),
        _make_note(tick=0, fret=3, sustain_length=0),
    ]
    res2 = builder.build_chords(triad_short)
    assert _frets_at_tick(res2, 0) == (0, 2)

    # Case 3: Unaccented beat (tick 48 % 96 != 0) with sustain 96 -> clamped to 2-note power chord
    triad_unaccented = [
        _make_note(tick=48, fret=0, sustain_length=96),
        _make_note(tick=48, fret=2, sustain_length=96),
        _make_note(tick=48, fret=3, sustain_length=96),
    ]
    res3 = builder.build_chords(triad_unaccented)
    assert _frets_at_tick(res3, 48) == (0, 2)


def test_strictly_prohibit_four_and_five_fret_chords() -> None:
    """Prompt 7.2: Verify 4-fret and 5-fret chords are strictly prohibited under all configurations."""
    for max_f in [2, 3, 4, 5]:
        builder = ChordBuilder(max_frets=max_f)
        notes_4 = [_make_note(tick=0, fret=f, sustain_length=96) for f in [0, 1, 2, 3]]
        notes_5 = [_make_note(tick=0, fret=f, sustain_length=96) for f in [0, 1, 2, 3, 4]]

        res_4 = builder.build_chords(notes_4)
        res_5 = builder.build_chords(notes_5)

        assert len(_frets_at_tick(res_4, 0)) <= 3
        assert len(_frets_at_tick(res_5, 0)) <= 3


# ---------------------------------------------------------------------------
# 7. Edge Cases & Error Handling
# ---------------------------------------------------------------------------


def test_empty_input_list(default_builder: ChordBuilder) -> None:
    """Verify empty input produces empty output list."""
    assert default_builder.build_chords([]) == []


@pytest.mark.parametrize("fret_val", [0, 1, 2, 3, 4, 7])
def test_single_notes_across_all_frets(default_builder: ChordBuilder, fret_val: int) -> None:
    """Verify single notes for each individual fret are preserved unchanged."""
    note = _make_note(tick=192, fret=fret_val, sustain_length=48, is_hopo=False)
    result = default_builder.build_chords([note])

    assert len(result) == 1
    assert result[0].tick == 192
    assert result[0].fret.value == fret_val
    assert result[0].sustain_length == 48


def test_sequential_single_notes_no_chords(default_builder: ChordBuilder) -> None:
    """Verify sequence of single notes at distinct ticks passes through unaffected."""
    notes = [
        _make_note(tick=0, fret=0),
        _make_note(tick=48, fret=1),
        _make_note(tick=96, fret=2),
        _make_note(tick=144, fret=3),
        _make_note(tick=192, fret=4),
    ]

    result = default_builder.build_chords(notes)
    assert len(result) == 5
    assert [n.tick for n in result] == [0, 48, 96, 144, 192]
    assert [n.fret.value for n in result] == [0, 1, 2, 3, 4]


def test_sequential_chords_across_multiple_ticks(default_builder: ChordBuilder) -> None:
    """Verify complex progression of chords and single notes maintains integrity."""
    notes = [
        _make_note(tick=0, fret=0),
        _make_note(tick=0, fret=1),
        _make_note(tick=96, fret=0),
        _make_note(tick=96, fret=2),
        _make_note(tick=192, fret=0),
        _make_note(tick=192, fret=2),
        _make_note(tick=192, fret=3),
        _make_note(tick=288, fret=4),
        _make_note(tick=384, fret=FretType.OPEN),
    ]

    result = default_builder.build_chords(notes)
    assert _frets_at_tick(result, 0) == (0, 1)
    assert _frets_at_tick(result, 96) == (0, 2)
    assert _frets_at_tick(result, 192) == (0, 2, 3)
    assert _frets_at_tick(result, 288) == (4,)
    assert _frets_at_tick(result, 384) == (7,)


def test_unsorted_ticks_input(default_builder: ChordBuilder) -> None:
    """Verify input given out of tick order is strictly sorted in the output."""
    notes = [
        _make_note(tick=384, fret=1),
        _make_note(tick=0, fret=0),
        _make_note(tick=192, fret=2),
    ]

    result = default_builder.build_chords(notes)
    assert [n.tick for n in result] == [0, 192, 384]


def test_unsorted_frets_at_same_tick(default_builder: ChordBuilder) -> None:
    """Verify frets provided in reverse order at the same tick are sorted ascending."""
    notes = [
        _make_note(tick=0, fret=3),
        _make_note(tick=0, fret=1),
        _make_note(tick=0, fret=2),
    ]

    result = default_builder.build_chords(notes)
    assert _frets_at_tick(result, 0) == (1, 2, 3)


def test_high_volume_stress_pipeline(default_builder: ChordBuilder) -> None:
    """Stress test processing 1000 notes with mixed chords and clusters."""
    notes: list[ChartNote] = []
    for i in range(250):
        tick = i * 48
        pattern = i % 5
        if pattern == 0:
            notes.append(_make_note(tick=tick, fret=0))
        elif pattern == 1:
            notes.append(_make_note(tick=tick, fret=0))
            notes.append(_make_note(tick=tick, fret=2))
        elif pattern == 2:
            notes.append(_make_note(tick=tick, fret=0))
            notes.append(_make_note(tick=tick, fret=2))
            notes.append(_make_note(tick=tick, fret=3))
        elif pattern == 3:
            for f in range(4):
                notes.append(_make_note(tick=tick, fret=f))
        else:
            for f in range(5):
                notes.append(_make_note(tick=tick, fret=f))

    result = default_builder.build_chords(notes)
    assert len(result) > 0

    unique_ticks = {n.tick for n in result}
    for t in unique_ticks:
        frets = _frets_at_tick(result, t)
        assert len(frets) <= 3
        assert not ({0, 4}.issubset(frets))
        if 7 in frets:
            assert len(frets) == 1


@pytest.mark.parametrize("invalid_max", [0, -1, 6])
def test_builder_invalid_max_frets(invalid_max: int) -> None:
    """Verify ChordBuilder raises ValueError when max_frets is out of bounds."""
    with pytest.raises(ValueError, match="max_frets must be between 1 and 5"):
        ChordBuilder(max_frets=invalid_max)


def test_builder_convenience_aliases(default_builder: ChordBuilder) -> None:
    """Verify convenience aliases build(), process(), and __call__() produce identical output."""
    notes = [_make_note(tick=0, fret=0), _make_note(tick=0, fret=1)]

    res_primary = default_builder.build_chords(notes)
    res_build = default_builder.build(notes)
    res_process = default_builder.process(notes)
    res_call = default_builder(notes)

    assert res_primary == res_build == res_process == res_call


def test_all_chord_types_preserve_sustain_length() -> None:
    """Verify chords of various configurations preserve input note sustain_length."""
    builder = ChordBuilder(max_frets=2, collapse_fast_runs=True)

    # 1. Standard Power Chord (fret 0 + 2) with 192 ticks sustain
    power_chord = [
        _make_note(tick=0, fret=0, sustain_length=192),
        _make_note(tick=0, fret=2, sustain_length=192),
    ]
    res1 = builder.build_chords(power_chord)
    assert len(res1) == 2
    assert all(n.sustain_length == 192 for n in res1)

    # 2. Clamped Dyad: (0, 4) with sustain 150 clamps to (0, 2), preserving sustain
    clamped_dyad = [
        _make_note(tick=1000, fret=0, sustain_length=150),
        _make_note(tick=1000, fret=4, sustain_length=150),
    ]
    res2 = builder.build_chords(clamped_dyad)
    assert len(res2) == 2
    assert [n.fret.value for n in res2] == [0, 2]
    assert all(n.sustain_length == 150 for n in res2)

    # 3. Fast-run collapsed note: inter-note spacing 48 ticks, sustain 96 preserved
    fast_run_chord = [
        _make_note(tick=2000, fret=0, sustain_length=96),
        _make_note(tick=2000, fret=2, sustain_length=96),
        _make_note(tick=2048, fret=1, sustain_length=0),
    ]
    res3 = builder.build_chords(fast_run_chord)
    # At tick 2000, collapsed to root fret 0 with sustain_length 96
    notes_2000 = [n for n in res3 if n.tick == 2000]
    assert len(notes_2000) == 1
    assert notes_2000[0].fret == FretType.GREEN
    assert notes_2000[0].sustain_length == 96

    # 4. Open Note with sustain 250
    open_note = [_make_note(tick=3000, fret=FretType.OPEN, sustain_length=250)]
    res4 = builder.build_chords(open_note)
    assert len(res4) == 1
    assert res4[0].fret == FretType.OPEN
    assert res4[0].sustain_length == 250
