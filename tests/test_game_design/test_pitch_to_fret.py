"""Unit tests for adaptive pitch-to-fret mapping engine (PitchToFretMapper)."""

import pytest

from src.game_design.pitch_to_fret import PitchToFretMapper
from src.game_design.quantizer import QuantizedNote
from src.models import ChartNote, FretType


@pytest.fixture
def default_mapper() -> PitchToFretMapper:
    """Return a standard PitchToFretMapper with default parameters (disable_open_notes=True)."""
    return PitchToFretMapper(
        window_ticks=1536,
        max_jump=3,
        rapid_interval=48,
        open_threshold=40,
        disable_open_notes=True,
    )


@pytest.fixture
def open_mapper() -> PitchToFretMapper:
    """Return a PitchToFretMapper with open notes enabled (e.g. for bass/rhythm tracks)."""
    return PitchToFretMapper(
        window_ticks=1536,
        max_jump=3,
        rapid_interval=48,
        open_threshold=40,
        disable_open_notes=False,
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
# 1. Sub-Bass Open Note Mapping & Lead Guitar Restraint
# ---------------------------------------------------------------------------


def test_sub_bass_open_note(open_mapper: PitchToFretMapper) -> None:
    """Verify pitches < 40 map to FretType.OPEN (7) when disable_open_notes=False."""
    notes = [
        _make_qnote(tick=0, pitch=28),  # E1 (< 40) -> OPEN
        _make_qnote(tick=96, pitch=36),  # C2 (< 40) -> OPEN
        _make_qnote(tick=192, pitch=39),  # D#2 (< 40) -> OPEN
        _make_qnote(tick=288, pitch=40),  # E2 (>= 40) -> GREEN (0)
    ]

    result = open_mapper.map_notes(notes)
    assert len(result) == 4
    assert [n.fret for n in result] == [
        FretType.OPEN,
        FretType.OPEN,
        FretType.OPEN,
        FretType.GREEN,
    ]


def test_lead_guitar_disable_open_notes_default(default_mapper: PitchToFretMapper) -> None:
    """Prompt 7.3: Sub-threshold pitches map to Green (0) instead of Open (7) when disable_open_notes=True."""
    assert default_mapper.disable_open_notes is True
    notes = [
        _make_qnote(tick=0, pitch=28),  # E1 (< 40) -> GREEN (0)
        _make_qnote(tick=96, pitch=36),  # C2 (< 40) -> GREEN (0)
        _make_qnote(tick=192, pitch=39),  # D#2 (< 40) -> GREEN (0)
        _make_qnote(tick=288, pitch=40),  # E2 (>= 40) -> GREEN (0)
    ]

    result = default_mapper.map_notes(notes)
    assert all(n.fret == FretType.GREEN for n in result)
    assert not any(n.fret == FretType.OPEN for n in result)


def test_sub_bass_custom_open_threshold() -> None:
    """Verify custom open_threshold parameter correctly partitions sub-bass notes when open notes enabled."""
    mapper = PitchToFretMapper(open_threshold=45, disable_open_notes=False)
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


def test_jump_penalty_does_not_clamp_open_notes(open_mapper: PitchToFretMapper) -> None:
    """Verify sub-bass open notes are immune to physical fret jump penalty when open notes enabled."""
    notes = [
        _make_qnote(tick=0, pitch=60),  # Green (0)
        _make_qnote(tick=24, pitch=36),  # Interval = 24 < 48, pitch < 40 -> OPEN (7)
    ]

    result = open_mapper.map_notes(notes)
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
    notes = [_make_qnote(tick=0, pitch=60, duration_ticks=48)]
    result = default_mapper.map_notes(notes)
    assert len(result) == 1
    assert result[0] == ChartNote(tick=0, fret=FretType.GREEN, sustain_length=48, is_hopo=False)


def test_single_sub_bass_note(open_mapper: PitchToFretMapper) -> None:
    """Verify single sub-bass note maps to FretType.OPEN when open notes enabled."""
    notes = [_make_qnote(tick=0, pitch=35, duration_ticks=48)]
    result = open_mapper.map_notes(notes)
    assert len(result) == 1
    assert result[0] == ChartNote(tick=0, fret=FretType.OPEN, sustain_length=48, is_hopo=False)


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


def test_sub_bass_chord_mapping(open_mapper: PitchToFretMapper) -> None:
    """Verify multiple simultaneous sub-bass notes all map to FretType.OPEN when open notes enabled."""
    notes = [
        _make_qnote(tick=0, pitch=36),
        _make_qnote(tick=0, pitch=38),
    ]

    result = open_mapper.map_notes(notes)
    assert len(result) == 2
    assert all(n.fret == FretType.OPEN for n in result)


def test_motif_anchoring_repeating_riff(default_mapper: PitchToFretMapper) -> None:
    """Prompt 7.3: Localized root pitch is anchored to Green (0), ensuring consistent visual motifs."""
    # Measure 1: Riff in E (root 40 played 4 times), with melody notes 43 (G), 45 (A), 47 (B)
    measure_1 = [
        _make_qnote(tick=0, pitch=40),
        _make_qnote(tick=48, pitch=43),
        _make_qnote(tick=96, pitch=40),
        _make_qnote(tick=144, pitch=45),
        _make_qnote(tick=192, pitch=40),
        _make_qnote(tick=240, pitch=47),
        _make_qnote(tick=288, pitch=40),
    ]

    # Measure 2 (tick 768): Same riff repeated, but with an acoustic transient noise spike at pitch 36
    measure_2 = [
        _make_qnote(tick=768, pitch=36),  # Isolated sub-bass noise spike (count = 1)
        _make_qnote(tick=816, pitch=40),
        _make_qnote(tick=864, pitch=43),
        _make_qnote(tick=912, pitch=40),
        _make_qnote(tick=960, pitch=45),
        _make_qnote(tick=1008, pitch=40),
        _make_qnote(tick=1056, pitch=47),
        _make_qnote(tick=1104, pitch=40),
    ]

    res_1 = default_mapper.map_notes(measure_1)
    res_2 = default_mapper.map_notes(measure_2)

    # In measure 1, root pitch 40 maps to Green (0)
    frets_m1_root = [n.fret for n in res_1 if n.tick in (0, 96, 192, 288)]
    assert all(f == FretType.GREEN for f in frets_m1_root)

    # In measure 2, despite transient noise at 36, motif anchoring keeps pitch 40 anchored to Green (0)
    frets_m2_root = [n.fret for n in res_2 if n.tick in (816, 912, 1008, 1104)]
    assert all(f == FretType.GREEN for f in frets_m2_root)

    # Melodic notes produce consistent frets
    fret_43_m1 = next(n.fret for n in res_1 if n.tick == 48)
    fret_43_m2 = next(n.fret for n in res_2 if n.tick == 864)
    assert fret_43_m1 == fret_43_m2


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
    with pytest.raises(ValueError, match="min_pattern_len"):
        PitchToFretMapper(min_pattern_len=0)
    with pytest.raises(ValueError, match="min_pattern_len"):
        PitchToFretMapper(min_pattern_len=-1)


# ---------------------------------------------------------------------------
# 6. Motif & Repeating Sequence Consistency (User Feedback Enhancement)
# ---------------------------------------------------------------------------


def test_repeating_guitar_phrase_consistency() -> None:
    """Verify repeating guitar solo phrase produces bit-for-bit identical fret sequences across different sections."""
    # A distinct 6-note solo phrase
    phrase_pitches = [72, 75, 77, 75, 74, 72]

    # Occurrence 1 at tick 0 (Section 1)
    section_1 = [_make_qnote(tick=i * 48, pitch=p) for i, p in enumerate(phrase_pitches)]

    # Occurrence 2 at tick 3840 (Section 2, measure 20) with identical pitches
    section_2 = [_make_qnote(tick=3840 + i * 48, pitch=p) for i, p in enumerate(phrase_pitches)]

    # Surrounding context for Section 2: high solo licks that alter sliding window percentiles
    surrounding_notes = [
        _make_qnote(tick=3600, pitch=88),
        _make_qnote(tick=3648, pitch=90),
        _make_qnote(tick=3696, pitch=92),
    ]

    all_notes = section_1 + surrounding_notes + section_2

    # 1. With consistent_patterns=False: varying window context alters the mapped frets
    inconsistent_mapper = PitchToFretMapper(consistent_patterns=False)
    inconsistent_result = inconsistent_mapper.map_notes(all_notes)

    s1_inconsistent = [n.fret for n in inconsistent_result if n.tick < 300]
    s2_inconsistent = [n.fret for n in inconsistent_result if n.tick >= 3840]
    assert s1_inconsistent != s2_inconsistent, (
        "Without pattern consistency, window jitter should alter frets"
    )

    # 2. With consistent_patterns=True (default): produces bit-for-bit identical fret sequences
    consistent_mapper = PitchToFretMapper(consistent_patterns=True)
    consistent_result = consistent_mapper.map_notes(all_notes)

    s1_consistent = [n.fret for n in consistent_result if n.tick < 300]
    s2_consistent = [n.fret for n in consistent_result if n.tick >= 3840]
    assert len(s1_consistent) == len(phrase_pitches)
    assert len(s2_consistent) == len(phrase_pitches)
    assert s1_consistent == s2_consistent, (
        "With pattern consistency, repeating phrase must be bit-for-bit identical"
    )

    # Verify the pattern was stored in pattern_cache
    assert tuple(phrase_pitches) in consistent_mapper.pattern_cache
    assert consistent_mapper.pattern_cache[tuple(phrase_pitches)] == [int(f) for f in s1_consistent]


def test_pre_cached_patterns_applied() -> None:
    """Verify pre-populating pattern_cache forces exact custom fret sequences across occurrences."""
    phrase_pitches = [70, 74, 77]
    custom_frets = [FretType.RED, FretType.YELLOW, FretType.BLUE]

    mapper = PitchToFretMapper(consistent_patterns=True)
    mapper.pattern_cache[tuple(phrase_pitches)] = [int(f) for f in custom_frets]

    notes = [
        _make_qnote(tick=0, pitch=70),
        _make_qnote(tick=48, pitch=74),
        _make_qnote(tick=96, pitch=77),
        _make_qnote(tick=1920, pitch=70),
        _make_qnote(tick=1968, pitch=74),
        _make_qnote(tick=2016, pitch=77),
    ]

    result = mapper.map_notes(notes)
    occ1 = [n.fret for n in result if n.tick < 200]
    occ2 = [n.fret for n in result if n.tick >= 1920]

    assert occ1 == custom_frets
    assert occ2 == custom_frets


def test_sub_phrase_motif_consistency() -> None:
    """Verify 3-note sub-phrases recurring across different sections map identically."""
    # A 3-note riff repeated 3 times across the track
    riff_pitches = [62, 65, 69]
    occ1 = [_make_qnote(tick=i * 96, pitch=p) for i, p in enumerate(riff_pitches)]
    occ2 = [_make_qnote(tick=1536 + i * 96, pitch=p) for i, p in enumerate(riff_pitches)]
    occ3 = [_make_qnote(tick=3072 + i * 96, pitch=p) for i, p in enumerate(riff_pitches)]

    mapper = PitchToFretMapper(consistent_patterns=True)
    result = mapper.map_notes(occ1 + occ2 + occ3)

    fret_occ1 = [n.fret for n in result if n.tick < 500]
    fret_occ2 = [n.fret for n in result if 1500 <= n.tick < 2000]
    fret_occ3 = [n.fret for n in result if n.tick >= 3000]

    assert fret_occ1 == fret_occ2 == fret_occ3


def test_min_pattern_len_threshold() -> None:
    """Verify phrases shorter than min_pattern_len do not trigger pattern caching."""
    mapper = PitchToFretMapper(consistent_patterns=True, min_pattern_len=4)
    # 3-note phrase with min_pattern_len=4
    notes = [
        _make_qnote(tick=0, pitch=60),
        _make_qnote(tick=48, pitch=64),
        _make_qnote(tick=96, pitch=67),
        _make_qnote(tick=1000, pitch=60),
        _make_qnote(tick=1048, pitch=64),
        _make_qnote(tick=1096, pitch=67),
    ]

    mapper.map_notes(notes)
    # Since len is 3 < min_pattern_len (4), it should not be stored in pattern_cache
    assert (60, 64, 67) not in mapper.pattern_cache


def test_output_chart_note_invariants(default_mapper: PitchToFretMapper) -> None:
    """Verify all returned ChartNotes satisfy domain contract invariants."""
    notes = [
        _make_qnote(tick=0, pitch=35),
        _make_qnote(tick=96, pitch=60),
        _make_qnote(tick=192, pitch=72),
    ]

    result = default_mapper.map_notes(notes)
    for i, note in enumerate(result):
        assert isinstance(note, ChartNote)
        assert note.tick >= 0
        assert isinstance(note.fret, FretType)
        assert note.sustain_length == notes[i].duration_ticks
        assert note.is_hopo is False


# ---------------------------------------------------------------------------
# 11. Creativity & Sustain Preservation Tests
# ---------------------------------------------------------------------------


def test_creativity_parameter_clamping() -> None:
    """Verify creativity parameter clamps between 0.0 and 1.0."""
    mapper_low = PitchToFretMapper(creativity=-0.5)
    assert mapper_low.creativity == 0.0

    mapper_high = PitchToFretMapper(creativity=1.5)
    assert mapper_high.creativity == 1.0

    mapper_mid = PitchToFretMapper(creativity=0.7)
    assert mapper_mid.creativity == 0.7


def test_sustain_length_preserved_in_map_notes(default_mapper: PitchToFretMapper) -> None:
    """Verify notes preserve their varied duration_ticks in sustain_length."""
    notes = [
        _make_qnote(tick=0, pitch=60, duration_ticks=96),
        _make_qnote(tick=192, pitch=64, duration_ticks=192),
        _make_qnote(tick=384, pitch=67, duration_ticks=48),
    ]
    result = default_mapper.map_notes(notes)
    assert len(result) == 3
    assert result[0].sustain_length == 96
    assert result[1].sustain_length == 192
    assert result[2].sustain_length == 48


def test_low_creativity_vibrato_motif_anchoring() -> None:
    """Verify low creativity (< 0.35) maps phrases with +/- 1 semitone vibrato to identical frets."""
    # First occurrence: 60, 64, 67 at ticks 0, 48, 96 (tick 48 is unaccented)
    occ1 = [
        _make_qnote(tick=0, pitch=60),
        _make_qnote(tick=48, pitch=64),
        _make_qnote(tick=96, pitch=67),
    ]
    # Surrounding context that would normally shift percentiles
    surrounding = [
        _make_qnote(tick=1500, pitch=85),
        _make_qnote(tick=1548, pitch=87),
        _make_qnote(tick=1596, pitch=89),
    ]
    # Second occurrence: note 2 has 1 semitone vibrato (pitch 65 instead of 64)
    occ2 = [
        _make_qnote(tick=3000, pitch=60),
        _make_qnote(tick=3048, pitch=65),  # 65 vs 64 (diff 1 at unaccented tick)
        _make_qnote(tick=3096, pitch=67),
    ]

    # With low creativity (0.2), occ2 matches occ1
    low_mapper = PitchToFretMapper(creativity=0.2, consistent_patterns=True)
    res_low = low_mapper.map_notes(occ1 + surrounding + occ2)
    frets_occ1 = [n.fret for n in res_low if n.tick < 200]
    frets_occ2 = [n.fret for n in res_low if n.tick >= 3000]
    assert frets_occ1 == frets_occ2


def test_low_creativity_pitch_contour_matching() -> None:
    """Verify low creativity maps identical relative pitch contours to identical frets."""
    phrase1 = [
        _make_qnote(tick=0, pitch=60),
        _make_qnote(tick=48, pitch=62),
        _make_qnote(tick=96, pitch=65),
    ]
    surrounding = [
        _make_qnote(tick=1500, pitch=85),
        _make_qnote(tick=1548, pitch=87),
    ]
    # Phrase 2 has same contour (+2, +3) starting 1 semitone higher (pitch 61)
    phrase2 = [
        _make_qnote(tick=3000, pitch=61),
        _make_qnote(tick=3048, pitch=63),
        _make_qnote(tick=3096, pitch=66),
    ]

    mapper = PitchToFretMapper(creativity=0.2, consistent_patterns=True)
    res = mapper.map_notes(phrase1 + surrounding + phrase2)
    frets_p1 = [n.fret for n in res if n.tick < 200]
    frets_p2 = [n.fret for n in res if n.tick >= 3000]
    assert frets_p1 == frets_p2


def test_high_creativity_allows_varied_expressions() -> None:
    """Verify high creativity (>= 0.95) disables rigid pattern replacement."""
    phrase_pitches = [60, 64, 67]
    occ1 = [_make_qnote(tick=i * 48, pitch=p) for i, p in enumerate(phrase_pitches)]
    surrounding = [
        _make_qnote(tick=3600, pitch=88),
        _make_qnote(tick=3648, pitch=90),
        _make_qnote(tick=3696, pitch=92),
    ]
    occ2 = [_make_qnote(tick=3840 + i * 48, pitch=p) for i, p in enumerate(phrase_pitches)]

    mapper_high = PitchToFretMapper(creativity=0.98, consistent_patterns=True)
    res = mapper_high.map_notes(occ1 + surrounding + occ2)
    s1 = [n.fret for n in res if n.tick < 200]
    s2 = [n.fret for n in res if n.tick >= 3840]
    # With sliding window percentiles shifted by surrounding high notes, occ2 has varied frets
    assert s1 != s2


# ---------------------------------------------------------------------------
# 12. Motif Lock High Fidelity & Fuzzy Sequence Alignment Tests
# ---------------------------------------------------------------------------


def test_motif_matching_with_vibrato_at_default_creativity() -> None:
    """Verify 8-note riff with +-1 semitone vibrato maps to identical frets at default creativity=0.50 (Balanced)."""
    canonical_pitches = [60, 62, 64, 65, 67, 65, 64, 62]
    # Occurrence 1 at tick 0..336
    occ1 = [_make_qnote(tick=i * 48, pitch=p) for i, p in enumerate(canonical_pitches)]

    # Surrounding high-pitch context at tick 1500..1800 that shifts sliding window percentiles
    surrounding = [
        _make_qnote(tick=1500 + i * 48, pitch=p) for i, p in enumerate([84, 86, 88, 91, 88, 86])
    ]

    # Occurrence 2 at tick 3000..3336 with +/- 1 semitone vibrato on selected notes
    vibrato_pitches = [60, 63, 64, 64, 67, 65, 65, 62]
    occ2 = [_make_qnote(tick=3000 + i * 48, pitch=p) for i, p in enumerate(vibrato_pitches)]

    # Default Balanced preset (creativity=0.50, consistent_patterns=True)
    mapper = PitchToFretMapper(creativity=0.50, consistent_patterns=True)
    result = mapper.map_notes(occ1 + surrounding + occ2)

    frets_occ1 = [n.fret for n in result if n.tick < 500]
    frets_occ2 = [n.fret for n in result if n.tick >= 3000]

    assert len(frets_occ1) == 8
    assert len(frets_occ2) == 8
    assert frets_occ1 == frets_occ2, (
        f"Vibrato riff at creativity=0.50 should map to identical frets. Got {frets_occ1} vs {frets_occ2}"
    )


def test_motif_matching_with_ghost_note_insertion() -> None:
    """Verify riff with 1 inserted ghost note / extra pick strike preserves color sequence of aligned notes."""
    canonical_pitches = [60, 62, 64, 65, 67, 65, 64, 62]
    occ1 = [_make_qnote(tick=i * 96, pitch=p) for i, p in enumerate(canonical_pitches)]

    # Surrounding high notes placed close to occ2 to distort local sliding window percentiles
    surrounding = [
        _make_qnote(tick=2400 + i * 48, pitch=p) for i, p in enumerate([85, 88, 90, 93, 90, 88])
    ]

    # Occurrence 2: same 8 notes, but with 1 extra ghost note inserted between note 2 (64) and note 3 (65)
    # Ticks: 3000, 3096, 3192, 3240 (ghost!), 3288, 3384, 3480, 3576, 3672
    occ2 = [
        _make_qnote(tick=3000, pitch=60),
        _make_qnote(tick=3096, pitch=62),
        _make_qnote(tick=3192, pitch=64),
        _make_qnote(tick=3240, pitch=64),  # Ghost note / extra pick stroke on same pitch
        _make_qnote(tick=3288, pitch=65),
        _make_qnote(tick=3384, pitch=67),
        _make_qnote(tick=3480, pitch=65),
        _make_qnote(tick=3576, pitch=64),
        _make_qnote(tick=3672, pitch=62),
    ]

    mapper = PitchToFretMapper(creativity=0.50, consistent_patterns=True)
    result = mapper.map_notes(occ1 + surrounding + occ2)

    occ1_res = [n for n in result if n.tick < 1000]
    occ2_res = [n for n in result if n.tick >= 3000]

    assert len(occ1_res) == 8
    assert len(occ2_res) == 9

    # The 8 aligned notes in occ2 (excluding the inserted ghost note at tick 3240)
    aligned_occ2_frets = [n.fret for n in occ2_res if n.tick != 3240]
    frets_occ1 = [n.fret for n in occ1_res]
    assert aligned_occ2_frets == frets_occ1, (
        f"Aligned notes in riff with ghost note insertion must preserve canonical frets: {aligned_occ2_frets} != {frets_occ1}"
    )

    # Ghost note at 3240 should have an ergonomic fret (within max_jump)
    ghost_note = next(n for n in occ2_res if n.tick == 3240)
    prev_fret = next(n.fret.value for n in occ2_res if n.tick == 3192)
    assert abs(ghost_note.fret.value - prev_fret) <= mapper.max_jump


def test_motif_matching_with_turnaround_variation() -> None:
    """Verify riff with turnaround variation (Option A) preserves canonical sequence in body and transitions smoothly."""
    canonical_pitches = [55, 57, 59, 60, 62, 60, 59, 57]
    occ1 = [_make_qnote(tick=i * 96, pitch=p) for i, p in enumerate(canonical_pitches)]

    # Surrounding high notes placed close to occ2 to distort local sliding window percentiles
    surrounding = [_make_qnote(tick=2400 + i * 48, pitch=p) for i, p in enumerate([85, 88, 90, 93])]

    # Occurrence 2: First 6 notes are the identical body [55, 57, 59, 60, 62, 60],
    # last 2 notes are a turnaround fill [60, 62] (variation of [59, 57])
    turnaround_pitches = [55, 57, 59, 60, 62, 60, 60, 62]
    occ2 = [_make_qnote(tick=3000 + i * 96, pitch=p) for i, p in enumerate(turnaround_pitches)]

    mapper = PitchToFretMapper(creativity=0.50, consistent_patterns=True)
    result = mapper.map_notes(occ1 + surrounding + occ2)

    occ1_res = [n for n in result if n.tick < 1000]
    occ2_res = [n for n in result if n.tick >= 3000]

    assert len(occ1_res) == 8
    assert len(occ2_res) == 8

    # Option A: Body (first 6 notes) must match canonical frets exactly
    frets_body_occ1 = [n.fret for n in occ1_res[:6]]
    frets_body_occ2 = [n.fret for n in occ2_res[:6]]
    assert frets_body_occ2 == frets_body_occ1, (
        f"Turnaround body must preserve canonical frets: {frets_body_occ2} != {frets_body_occ1}"
    )

    # Transition from body to turnaround ending must be physically playable (within max_jump)
    assert abs(occ2_res[6].fret.value - occ2_res[5].fret.value) <= mapper.max_jump


def test_motif_contrasting_background_tessitura() -> None:
    """Verify riff in quiet vs loud/high-tessitura background preserves identical colors with consistent_patterns=True."""
    riff_pitches = [55, 57, 59, 60, 62, 60, 59, 57]
    occ1 = [_make_qnote(tick=i * 96, pitch=p) for i, p in enumerate(riff_pitches)]

    # Quiet/low background surrounding section 1
    quiet_surrounding = [
        _make_qnote(tick=1000 + i * 96, pitch=p) for i, p in enumerate([42, 44, 42, 45])
    ]

    # Loud/high background with cymbals/high vocals surrounding section 2 (ticks 2500..4000)
    high_cymbals_before = [
        _make_qnote(tick=2500 + i * 48, pitch=p) for i, p in enumerate([88, 91, 93, 95, 96, 98])
    ]
    occ2 = [_make_qnote(tick=3000 + i * 96, pitch=p) for i, p in enumerate(riff_pitches)]
    high_cymbals_after = [
        _make_qnote(tick=3800 + i * 48, pitch=p) for i, p in enumerate([90, 92, 95, 97, 99])
    ]

    all_notes = occ1 + quiet_surrounding + high_cymbals_before + occ2 + high_cymbals_after

    # 1. Without pattern consistency, background tessitura shifts the frets
    inconsistent_mapper = PitchToFretMapper(consistent_patterns=False)
    inc_res = inconsistent_mapper.map_notes(all_notes)
    frets_occ1_inc = [n.fret for n in inc_res if n.tick < 1000]
    frets_occ2_inc = [n.fret for n in inc_res if 3000 <= n.tick < 3800]
    assert frets_occ1_inc != frets_occ2_inc, (
        "Without consistent_patterns, tessitura shift must alter frets"
    )

    # 2. With consistent_patterns=True, Motif Lock guarantees identical fret sequence
    consistent_mapper = PitchToFretMapper(consistent_patterns=True)
    con_res = consistent_mapper.map_notes(all_notes)
    frets_occ1_con = [n.fret for n in con_res if n.tick < 1000]
    frets_occ2_con = [n.fret for n in con_res if 3000 <= n.tick < 3800]
    assert frets_occ1_con == frets_occ2_con, (
        f"With consistent_patterns=True, riff must map identically regardless of background tessitura. "
        f"Got {frets_occ1_con} vs {frets_occ2_con}"
    )


def test_unrelated_phrases_not_falsely_matched() -> None:
    """Verify genuinely different musical phrases are not falsely matched or forced into identical frets."""
    # Phrase 1: Low pentatonic riff [50, 53, 55, 56, 57, 60, 57, 55]
    p1_pitches = [50, 53, 55, 56, 57, 60, 57, 55]
    phrase1 = [_make_qnote(tick=i * 96, pitch=p) for i, p in enumerate(p1_pitches)]

    # Phrase 2: High arpeggiated solo licking [72, 76, 79, 84, 88, 84, 79, 76]
    p2_pitches = [72, 76, 79, 84, 88, 84, 79, 76]
    phrase2 = [_make_qnote(tick=2000 + i * 96, pitch=p) for i, p in enumerate(p2_pitches)]

    mapper = PitchToFretMapper(creativity=0.50, consistent_patterns=True)
    res = mapper.map_notes(phrase1 + phrase2)

    frets_p1 = [n.fret for n in res if n.tick < 1000]
    frets_p2 = [n.fret for n in res if n.tick >= 2000]

    assert len(frets_p1) == 8
    assert len(frets_p2) == 8
    assert frets_p1 != frets_p2, "Unrelated phrases must not falsely match to identical frets"
    # Phrase 2 is in much higher octave, so average fret should reflect higher register
    avg_fret_p1 = sum(f.value for f in frets_p1) / len(frets_p1)
    avg_fret_p2 = sum(f.value for f in frets_p2) / len(frets_p2)
    assert avg_fret_p2 > avg_fret_p1, (
        f"High solo phrase should map higher on the highway than low pentatonic riff. "
        f"Got avg {avg_fret_p2} vs {avg_fret_p1}"
    )


def test_fuzzy_similarity_and_alignment_engine(default_mapper: PitchToFretMapper) -> None:
    """Directly verify _compute_phrase_similarity substitution penalties and _align_phrase_frets."""
    # 1. Exact match (cost 0.0)
    sim, align = default_mapper._compute_phrase_similarity([60, 64, 67], [60, 64, 67])
    assert sim == 1.0
    assert align == [(0, 0), (1, 1), (2, 2)]

    # 2. Vibrato +-1 semitone (cost 0.15 on 1 of 4 notes -> similarity 1.0 - 0.15/4 = 0.9625)
    sim_vib, align_vib = default_mapper._compute_phrase_similarity(
        [60, 64, 67, 72], [60, 65, 67, 72]
    )
    assert abs(sim_vib - (1.0 - 0.15 / 4)) < 1e-6
    assert align_vib == [(0, 0), (1, 1), (2, 2), (3, 3)]

    # 3. Bend +-2 semitones (cost 0.35 on 1 of 4 notes -> similarity 1.0 - 0.35/4 = 0.9125)
    sim_bend, align_bend = default_mapper._compute_phrase_similarity(
        [60, 64, 67, 72], [60, 66, 67, 72]
    )
    assert abs(sim_bend - (1.0 - 0.35 / 4)) < 1e-6

    # 4. Octave harmonic +-12 semitones (cost 0.40 on 1 of 4 notes -> similarity 1.0 - 0.40/4 = 0.90)
    sim_oct, align_oct = default_mapper._compute_phrase_similarity(
        [60, 64, 67, 72], [60, 76, 67, 72]
    )
    assert abs(sim_oct - (1.0 - 0.40 / 4)) < 1e-6

    # 5. Insertion / Ghost note (cost 1.0 on 1 extra note -> max_len 5 -> similarity 1.0 - 1.0/5 = 0.80)
    sim_ins, align_ins = default_mapper._compute_phrase_similarity(
        [60, 64, 67, 72], [60, 64, 64, 67, 72]
    )
    assert abs(sim_ins - (1.0 - 1.0 / 5)) < 1e-6
    assert (None, 2) in align_ins

    # 6. Test _align_phrase_frets interpolation with max_jump clamping
    canonical_frets = [0, 2, 3, 4]
    canonical_pitches = [60, 64, 67, 72]
    target_pitches = [60, 64, 64, 67, 72]
    target_base = [0, 2, 2, 3, 4]
    aligned = default_mapper._align_phrase_frets(
        canonical_frets=canonical_frets,
        canonical_pitches=canonical_pitches,
        target_pitches=target_pitches,
        target_base_frets=target_base,
        alignment=align_ins,
    )
    assert aligned == [0, 2, 2, 3, 4]


def test_motif_similarity_threshold_parameter() -> None:
    """Verify motif_similarity_threshold parameter validation and customization."""
    with pytest.raises(ValueError, match="motif_similarity_threshold must be between 0.0 and 1.0"):
        PitchToFretMapper(motif_similarity_threshold=-0.1)

    with pytest.raises(ValueError, match="motif_similarity_threshold must be between 0.0 and 1.0"):
        PitchToFretMapper(motif_similarity_threshold=1.5)

    custom_mapper = PitchToFretMapper(motif_similarity_threshold=0.88)
    assert custom_mapper.motif_similarity_threshold == 0.88
