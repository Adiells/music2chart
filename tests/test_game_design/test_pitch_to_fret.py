"""Unit tests for adaptive pitch-to-fret mapping engine (PitchToFretMapper)."""

import pytest

from src.game_design.pitch_to_fret import PitchToFretMapper
from src.game_design.quantizer import QuantizedNote
from src.models import ChartNote, FretType


@pytest.fixture
def default_mapper() -> PitchToFretMapper:
    """Return a standard PitchToFretMapper with default parameters."""
    return PitchToFretMapper(
        window_ticks=1536,
        max_jump=3,
        rapid_interval=48,
        open_threshold=40,
    )


def _make_qnote(
    tick: int,
    pitch: int,
    duration_ticks: int = 48,
    amplitude: float = 0.8,
) -> QuantizedNote:
    """Synthesize a QuantizedNote helper."""
    return QuantizedNote(
        tick=tick,
        pitch=pitch,
        duration_ticks=duration_ticks,
        amplitude=amplitude,
    )


# ---------------------------------------------------------------------------
# 1. Sub-Bass Open Note Mapping
# ---------------------------------------------------------------------------


def test_sub_bass_open_note(default_mapper: PitchToFretMapper) -> None:
    """Verify pitches < 40 map to FretType.OPEN (7) and pitch >= 40 maps to regular fret."""
    notes = [
        _make_qnote(tick=0, pitch=28),  # E1 (< 40) -> OPEN
        _make_qnote(tick=96, pitch=36),  # C2 (< 40) -> OPEN
        _make_qnote(tick=192, pitch=39),  # D#2 (< 40) -> OPEN
        _make_qnote(tick=288, pitch=40),  # E2 (>= 40) -> GREEN (0)
    ]

    result = default_mapper.map_notes(notes)
    assert len(result) == 4
    assert [n.fret for n in result] == [
        FretType.OPEN,
        FretType.OPEN,
        FretType.OPEN,
        FretType.GREEN,
    ]


def test_sub_bass_custom_open_threshold() -> None:
    """Verify custom open_threshold parameter correctly partitions sub-bass notes."""
    mapper = PitchToFretMapper(open_threshold=45)
    notes = [
        _make_qnote(tick=0, pitch=42),  # 42 < 45 -> OPEN
        _make_qnote(tick=96, pitch=45),  # 45 >= 45 -> GREEN
    ]

    result = mapper.map_notes(notes)
    assert result[0].fret == FretType.OPEN
    assert result[1].fret == FretType.GREEN


# ---------------------------------------------------------------------------
# 2. Scale Flow Mapping (Ascending & Descending)
# ---------------------------------------------------------------------------


def test_ascending_5_fret_scale(default_mapper: PitchToFretMapper) -> None:
    """Verify a 5-step ascending scale produces sequential frets 0 -> 1 -> 2 -> 3 -> 4."""
    # Pitches: C4 (60), D4 (62), E4 (64), G4 (67), A4 (69)
    notes = [_make_qnote(tick=i * 96, pitch=p) for i, p in enumerate([60, 62, 64, 67, 69])]

    result = default_mapper.map_notes(notes)
    assert len(result) == 5
    assert [n.fret for n in result] == [
        FretType.GREEN,
        FretType.RED,
        FretType.YELLOW,
        FretType.BLUE,
        FretType.ORANGE,
    ]


def test_ascending_chromatic_scale(default_mapper: PitchToFretMapper) -> None:
    """Verify an octave chromatic scale produces monotonically non-decreasing frets."""
    notes = [_make_qnote(tick=i * 96, pitch=60 + i) for i in range(12)]

    result = default_mapper.map_notes(notes)
    assert len(result) == 12

    # Frets must be non-decreasing
    for i in range(len(result) - 1):
        assert result[i].fret <= result[i + 1].fret

    # Must start at Green and end at Orange
    assert result[0].fret == FretType.GREEN
    assert result[-1].fret == FretType.ORANGE

    # Must span all 5 frets
    fret_set = {n.fret for n in result}
    assert fret_set == {
        FretType.GREEN,
        FretType.RED,
        FretType.YELLOW,
        FretType.BLUE,
        FretType.ORANGE,
    }


def test_descending_scale_flow(default_mapper: PitchToFretMapper) -> None:
    """Verify a descending scale produces sequential frets 4 -> 3 -> 2 -> 1 -> 0."""
    notes = [_make_qnote(tick=i * 96, pitch=p) for i, p in enumerate([69, 67, 64, 62, 60])]

    result = default_mapper.map_notes(notes)
    assert [n.fret for n in result] == [
        FretType.ORANGE,
        FretType.BLUE,
        FretType.YELLOW,
        FretType.RED,
        FretType.GREEN,
    ]


# ---------------------------------------------------------------------------
# 3. Dynamic Sliding-Window Tessitura (Solos & Riffs)
# ---------------------------------------------------------------------------


def test_relative_tessitura_high_solo_passage(default_mapper: PitchToFretMapper) -> None:
    """Verify high register solo passages use the full 5-fret span rather than clustering on Orange."""
    # Solo high on guitar neck: pitches 75 to 90
    solo_pitches = [75, 77, 80, 82, 85, 87, 89, 90]
    notes = [_make_qnote(tick=i * 96, pitch=p) for i, p in enumerate(solo_pitches)]

    result = default_mapper.map_notes(notes)
    assert len(result) == len(solo_pitches)

    # Must NOT cluster only on Orange
    assert {n.fret for n in result} != {FretType.ORANGE}

    # Must use full 5-fret span organically
    fret_set = {n.fret for n in result}
    assert fret_set == {
        FretType.GREEN,
        FretType.RED,
        FretType.YELLOW,
        FretType.BLUE,
        FretType.ORANGE,
    }

    # Lowest note in solo maps to Green, highest to Orange
    assert result[0].fret == FretType.GREEN
    assert result[-1].fret == FretType.ORANGE


def test_relative_tessitura_low_riff_passage(default_mapper: PitchToFretMapper) -> None:
    """Verify low register riff passages use the full 5-fret span rather than clustering on Green."""
    # Low riff: pitches 42 to 56 (all >= 40)
    riff_pitches = [42, 45, 48, 52, 56]
    notes = [_make_qnote(tick=i * 96, pitch=p) for i, p in enumerate(riff_pitches)]

    result = default_mapper.map_notes(notes)
    assert len(result) == len(riff_pitches)

    # Must NOT cluster only on Green
    assert {n.fret for n in result} != {FretType.GREEN}

    # Must span all 5 frets
    assert {n.fret for n in result} == {
        FretType.GREEN,
        FretType.RED,
        FretType.YELLOW,
        FretType.BLUE,
        FretType.ORANGE,
    }


def test_sliding_window_section_transitions(default_mapper: PitchToFretMapper) -> None:
    """Verify dynamic sliding window adjusts tessitura between verse and solo across measures."""
    # Verse (ticks 0..384): low pitches 48..56
    verse_notes = [_make_qnote(tick=i * 96, pitch=48 + i * 2) for i in range(5)]
    # Solo (ticks 3072..3456, well beyond window 1536): high pitches 76..88
    solo_notes = [_make_qnote(tick=3072 + i * 96, pitch=76 + i * 3) for i in range(5)]

    all_notes = verse_notes + solo_notes
    result = default_mapper.map_notes(all_notes)

    # Pitch 56 (top of verse) maps to Orange (4) in its local window
    verse_result = [n for n in result if n.tick < 1000]
    assert verse_result[-1].fret == FretType.ORANGE

    # Pitch 76 (bottom of solo) maps to Green (0) in its local window
    solo_result = [n for n in result if n.tick >= 3000]
    assert solo_result[0].fret == FretType.GREEN


# ---------------------------------------------------------------------------
# 4. Rapid Passage Jump Penalty
# ---------------------------------------------------------------------------


def test_rapid_passage_jump_penalty_ascending(default_mapper: PitchToFretMapper) -> None:
    """Verify interval < 48 ticks clamps raw jumps > 3 frets (Green 0 -> Orange 4 clamped to Blue 3)."""
    notes = [
        _make_qnote(tick=0, pitch=60),  # Maps to Green (0)
        _make_qnote(tick=24, pitch=72),  # Interval = 24 < 48; raw Orange (4) clamped to Blue (3)
    ]

    result = default_mapper.map_notes(notes)
    assert len(result) == 2
    assert result[0].fret == FretType.GREEN
    assert result[1].fret == FretType.BLUE


def test_rapid_passage_jump_penalty_descending(default_mapper: PitchToFretMapper) -> None:
    """Verify interval < 48 ticks clamps raw drops > 3 frets (Orange 4 -> Green 0 clamped to Red 1)."""
    notes = [
        _make_qnote(tick=0, pitch=72),  # Maps to Orange (4)
        _make_qnote(tick=24, pitch=60),  # Interval = 24 < 48; raw Green (0) clamped to Red (1)
    ]

    result = default_mapper.map_notes(notes)
    assert len(result) == 2
    assert result[0].fret == FretType.ORANGE
    assert result[1].fret == FretType.RED


def test_jump_penalty_not_applied_at_or_above_48_ticks(
    default_mapper: PitchToFretMapper,
) -> None:
    """Verify interval >= 48 ticks permits full 4-fret leap without clamping."""
    notes = [
        _make_qnote(tick=0, pitch=60),  # Green (0)
        _make_qnote(tick=48, pitch=72),  # Interval = 48 >= 48; permitted at Orange (4)
    ]

    result = default_mapper.map_notes(notes)
    assert len(result) == 2
    assert result[0].fret == FretType.GREEN
    assert result[1].fret == FretType.ORANGE


def test_jump_penalty_custom_parameters() -> None:
    """Verify custom max_jump=2 and rapid_interval=96 parameters clamp correctly."""
    mapper = PitchToFretMapper(max_jump=2, rapid_interval=96)
    notes = [
        _make_qnote(tick=0, pitch=60),  # Green (0)
        _make_qnote(tick=72, pitch=72),  # Interval = 72 < 96; clamped by max_jump=2 to Yellow (2)
    ]

    result = mapper.map_notes(notes)
    assert result[0].fret == FretType.GREEN
    assert result[1].fret == FretType.YELLOW


def test_jump_penalty_does_not_clamp_open_notes(default_mapper: PitchToFretMapper) -> None:
    """Verify sub-bass open notes are immune to physical fret jump penalty."""
    notes = [
        _make_qnote(tick=0, pitch=60),  # Green (0)
        _make_qnote(tick=24, pitch=36),  # Interval = 24 < 48, pitch < 40 -> OPEN (7)
    ]

    result = default_mapper.map_notes(notes)
    assert result[0].fret == FretType.GREEN
    assert result[1].fret == FretType.OPEN


# ---------------------------------------------------------------------------
# 5. Edge Cases & Robustness
# ---------------------------------------------------------------------------


def test_empty_input_list(default_mapper: PitchToFretMapper) -> None:
    """Verify empty note list returns an empty list without raising exceptions."""
    result = default_mapper.map_notes([])
    assert result == []


def test_single_note_input(default_mapper: PitchToFretMapper) -> None:
    """Verify single note maps cleanly to Green (0) without division-by-zero."""
    notes = [_make_qnote(tick=0, pitch=60)]
    result = default_mapper.map_notes(notes)
    assert len(result) == 1
    assert result[0] == ChartNote(tick=0, fret=FretType.GREEN, sustain_length=0, is_hopo=False)


def test_single_sub_bass_note(default_mapper: PitchToFretMapper) -> None:
    """Verify single sub-bass note maps to FretType.OPEN."""
    notes = [_make_qnote(tick=0, pitch=35)]
    result = default_mapper.map_notes(notes)
    assert len(result) == 1
    assert result[0] == ChartNote(tick=0, fret=FretType.OPEN, sustain_length=0, is_hopo=False)


def test_monophonic_repeating_pitch(default_mapper: PitchToFretMapper) -> None:
    """Verify constant repeating pitch maps consistently to Green without errors."""
    notes = [_make_qnote(tick=i * 48, pitch=64) for i in range(8)]
    result = default_mapper.map_notes(notes)
    assert len(result) == 8
    assert all(n.fret == FretType.GREEN for n in result)


def test_simultaneous_notes_chord_mapping(default_mapper: PitchToFretMapper) -> None:
    """Verify simultaneous notes at identical tick preserve tick and map to ordered frets."""
    # C major triad at tick 192: pitches 60, 64, 67
    notes = [
        _make_qnote(tick=192, pitch=60),
        _make_qnote(tick=192, pitch=64),
        _make_qnote(tick=192, pitch=67),
    ]

    result = default_mapper.map_notes(notes)
    assert len(result) == 3

    # All notes retain tick 192
    assert all(n.tick == 192 for n in result)

    # Frets must be ordered strictly increasing
    assert result[0].fret < result[1].fret < result[2].fret
    assert [n.fret for n in result] == [
        FretType.GREEN,
        FretType.YELLOW,
        FretType.ORANGE,
    ]


def test_sub_bass_chord_mapping(default_mapper: PitchToFretMapper) -> None:
    """Verify multiple simultaneous sub-bass notes all map to FretType.OPEN."""
    notes = [
        _make_qnote(tick=0, pitch=36),
        _make_qnote(tick=0, pitch=38),
    ]

    result = default_mapper.map_notes(notes)
    assert len(result) == 2
    assert all(n.fret == FretType.OPEN for n in result)


def test_unsorted_inputs_sorted_chronologically(default_mapper: PitchToFretMapper) -> None:
    """Verify out-of-order input notes are returned chronologically sorted."""
    notes = [
        _make_qnote(tick=384, pitch=64),
        _make_qnote(tick=0, pitch=60),
        _make_qnote(tick=192, pitch=62),
    ]

    result = default_mapper.map_notes(notes)
    assert [n.tick for n in result] == [0, 192, 384]


def test_mapper_invalid_parameters() -> None:
    """Verify constructor validates parameters and raises ValueError on invalid inputs."""
    with pytest.raises(ValueError, match="window_ticks"):
        PitchToFretMapper(window_ticks=0)
    with pytest.raises(ValueError, match="window_ticks"):
        PitchToFretMapper(window_ticks=-100)
    with pytest.raises(ValueError, match="max_jump"):
        PitchToFretMapper(max_jump=0)
    with pytest.raises(ValueError, match="rapid_interval"):
        PitchToFretMapper(rapid_interval=-1)
    with pytest.raises(ValueError, match="open_threshold"):
        PitchToFretMapper(open_threshold=-5)


def test_output_chart_note_invariants(default_mapper: PitchToFretMapper) -> None:
    """Verify all returned ChartNotes satisfy domain contract invariants."""
    notes = [
        _make_qnote(tick=0, pitch=35),
        _make_qnote(tick=96, pitch=60),
        _make_qnote(tick=192, pitch=72),
    ]

    result = default_mapper.map_notes(notes)
    for note in result:
        assert isinstance(note, ChartNote)
        assert note.tick >= 0
        assert isinstance(note.fret, FretType)
        assert note.sustain_length == 0
        assert note.is_hopo is False
