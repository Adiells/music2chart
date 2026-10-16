"""Unit tests for musical quantization and grid snapping (NoteQuantizer)."""

import pytest

from src.game_design.quantizer import NoteQuantizer, QuantizedNote
from src.models import BPMChange, NoteEvent, TempoMap, TimeSignature


@pytest.fixture
def tempo_map_120() -> TempoMap:
    """Return a standard 120 BPM tempo map (192 PPQ)."""
    return TempoMap(
        resolution=192,
        bpm_changes=[BPMChange(tick=0, bpm=120.0)],
        time_signatures=[TimeSignature(tick=0, numerator=4, denominator=4)],
    )


@pytest.fixture
def variable_tempo_map() -> TempoMap:
    """Return a multi-tempo map: 120 BPM until measure 2 (tick 768), then 140 BPM."""
    return TempoMap(
        resolution=192,
        bpm_changes=[
            BPMChange(tick=0, bpm=120.0),
            BPMChange(tick=768, bpm=140.0),
        ],
        time_signatures=[TimeSignature(tick=0, numerator=4, denominator=4)],
    )


@pytest.fixture
def quantizer() -> NoteQuantizer:
    """Return a default NoteQuantizer with 16-tick tolerance."""
    return NoteQuantizer(tolerance_ticks=16)


def _make_note(
    start_tick: int,
    duration_ticks: int = 96,
    pitch: int = 60,
    amplitude: float = 0.8,
    jitter_ticks: int = 0,
    tempo_map: TempoMap | None = None,
) -> NoteEvent:
    """Helper to synthesize a NoteEvent at an exact grid tick with optional jitter."""
    if tempo_map is None:
        tempo_map = TempoMap(resolution=192, bpm_changes=[BPMChange(tick=0, bpm=120.0)])

    start_sec = tempo_map.tick_to_seconds(start_tick + jitter_ticks)
    end_sec = tempo_map.tick_to_seconds(start_tick + jitter_ticks + duration_ticks)
    return NoteEvent(
        start_time=start_sec,
        end_time=end_sec,
        pitch=pitch,
        amplitude=amplitude,
    )


def test_quantize_quarter_notes_exact(quantizer: NoteQuantizer, tempo_map_120: TempoMap) -> None:
    """Validate snapping for exact quarter notes (multiples of 192 ticks)."""
    notes = [
        _make_note(start_tick=0, tempo_map=tempo_map_120),
        _make_note(start_tick=192, tempo_map=tempo_map_120),
        _make_note(start_tick=384, tempo_map=tempo_map_120),
        _make_note(start_tick=576, tempo_map=tempo_map_120),
    ]

    result = quantizer.quantize(notes, tempo_map_120)
    assert len(result) == 4
    assert [n.tick for n in result] == [0, 192, 384, 576]


def test_quantize_quarter_notes_with_jitter(
    quantizer: NoteQuantizer, tempo_map_120: TempoMap
) -> None:
    """Validate snapping for slightly jittered quarter notes within 16 ticks."""
    notes = [
        _make_note(start_tick=192, jitter_ticks=-10, tempo_map=tempo_map_120),  # tick 182 -> 192
        _make_note(start_tick=384, jitter_ticks=12, tempo_map=tempo_map_120),  # tick 396 -> 384
        _make_note(start_tick=576, jitter_ticks=-11, tempo_map=tempo_map_120),  # tick 565 -> 576
    ]

    result = quantizer.quantize(notes, tempo_map_120)
    assert [n.tick for n in result] == [192, 384, 576]


def test_quantize_eighth_notes_exact_and_jitter(
    quantizer: NoteQuantizer, tempo_map_120: TempoMap
) -> None:
    """Validate snapping for eighth notes (multiples of 96 ticks) with and without jitter."""
    notes = [
        _make_note(start_tick=0, jitter_ticks=0, tempo_map=tempo_map_120),
        _make_note(start_tick=96, jitter_ticks=-8, tempo_map=tempo_map_120),  # tick 88 -> 96
        _make_note(start_tick=192, jitter_ticks=0, tempo_map=tempo_map_120),
        _make_note(start_tick=288, jitter_ticks=9, tempo_map=tempo_map_120),  # tick 297 -> 288
    ]

    result = quantizer.quantize(notes, tempo_map_120)
    assert [n.tick for n in result] == [0, 96, 192, 288]


def test_quantize_twelfth_triplets(quantizer: NoteQuantizer, tempo_map_120: TempoMap) -> None:
    """Validate snapping for 1/12 triplets (multiples of 64 ticks)."""
    notes = [
        _make_note(start_tick=0, jitter_ticks=0, tempo_map=tempo_map_120),
        _make_note(start_tick=64, jitter_ticks=-5, tempo_map=tempo_map_120),  # tick 59 -> 64
        _make_note(start_tick=128, jitter_ticks=6, tempo_map=tempo_map_120),  # tick 134 -> 128
        _make_note(start_tick=192, jitter_ticks=0, tempo_map=tempo_map_120),
    ]

    result = quantizer.quantize(notes, tempo_map_120)
    assert [n.tick for n in result] == [0, 64, 128, 192]


def test_quantize_sixteenth_notes_delayed_prompt_spec(
    quantizer: NoteQuantizer, tempo_map_120: TempoMap
) -> None:
    """Validate snapping for 1/16 notes, specifically tick 50 -> 48 as requested in Prompt 4.1."""
    # Note at tick 48 + 2 = 50 ticks -> must snap to 48
    note_delayed = _make_note(start_tick=48, jitter_ticks=2, tempo_map=tempo_map_120)
    note_early = _make_note(start_tick=96, jitter_ticks=-6, tempo_map=tempo_map_120)
    note_sixteenth_3 = _make_note(start_tick=144, jitter_ticks=4, tempo_map=tempo_map_120)

    result = quantizer.quantize([note_delayed, note_early, note_sixteenth_3], tempo_map_120)
    assert [n.tick for n in result] == [48, 96, 144]


def test_quantize_twenty_fourth_triplets(quantizer: NoteQuantizer, tempo_map_120: TempoMap) -> None:
    """Validate snapping for 1/24 triplet notes (multiples of 32 ticks, sextuplets)."""
    notes = [
        _make_note(start_tick=32, jitter_ticks=-3, tempo_map=tempo_map_120),  # tick 29 -> 32
        _make_note(start_tick=64, jitter_ticks=0, tempo_map=tempo_map_120),
        _make_note(start_tick=96, jitter_ticks=0, tempo_map=tempo_map_120),
        _make_note(start_tick=160, jitter_ticks=4, tempo_map=tempo_map_120),  # tick 164 -> 160
    ]

    result = quantizer.quantize(notes, tempo_map_120)
    assert [n.tick for n in result] == [32, 64, 96, 160]


def test_quantize_thirty_second_notes(quantizer: NoteQuantizer, tempo_map_120: TempoMap) -> None:
    """Validate snapping for 1/32 notes (multiples of 24 ticks)."""
    notes = [
        _make_note(start_tick=24, jitter_ticks=2, tempo_map=tempo_map_120),  # tick 26 -> 24
        _make_note(start_tick=72, jitter_ticks=-2, tempo_map=tempo_map_120),  # tick 70 -> 72
        _make_note(start_tick=120, jitter_ticks=3, tempo_map=tempo_map_120),  # tick 123 -> 120
        _make_note(start_tick=168, jitter_ticks=-3, tempo_map=tempo_map_120),  # tick 165 -> 168
    ]

    result = quantizer.quantize(notes, tempo_map_120)
    assert [n.tick for n in result] == [24, 72, 120, 168]


def test_quantize_outside_tolerance_remains_unsnapped(tempo_map_120: TempoMap) -> None:
    """Validate that deviations > 16 ticks remain unsnapped at their raw tick position when strict_snap=False."""
    # When quantizing against quarter notes only (192) with strict_snap=False, min_spacing_ticks=0, chord_fusion_window_s=0
    quarter_quantizer = NoteQuantizer(
        subdivisions=[192],
        tolerance_ticks=16,
        strict_snap=False,
        min_spacing_ticks=0,
        chord_fusion_window_s=0.0,
    )

    # Note at tick 192 + 16 = 208 -> dist is 16 -> snapped to 192
    note_boundary_in = _make_note(start_tick=192, jitter_ticks=16, tempo_map=tempo_map_120)
    # Note at tick 192 + 17 = 209 -> dist is 17 -> unsnapped (remains 209)
    note_boundary_out = _make_note(start_tick=192, jitter_ticks=17, tempo_map=tempo_map_120)
    # Note at tick 20 -> dist to 0 is 20, dist to 192 is 172 -> unsnapped (remains 20)
    note_isolated = _make_note(start_tick=0, jitter_ticks=20, tempo_map=tempo_map_120)

    result = quarter_quantizer.quantize(
        [note_isolated, note_boundary_in, note_boundary_out], tempo_map_120
    )
    assert result[0].tick == 20  # Unsnapped
    assert result[1].tick == 192  # Snapped
    assert result[2].tick == 209  # Unsnapped


def test_quantize_custom_tolerance(tempo_map_120: TempoMap) -> None:
    """Validate custom tolerance parameter (e.g. tolerance_ticks=8) with strict_snap=False."""
    tight_quantizer = NoteQuantizer(
        subdivisions=[24],
        tolerance_ticks=8,
        strict_snap=False,
        min_spacing_ticks=0,
        chord_fusion_window_s=0.0,
    )

    # Note at tick 24 - 8 = 16 -> dist 8 <= 8 -> snapped to 24
    note_in = _make_note(start_tick=24, jitter_ticks=-8, tempo_map=tempo_map_120)
    # Note at tick 24 - 10 = 14 -> dist 10 > 8 and dist to 0 is 14 > 8 -> unsnapped (14)
    note_out = _make_note(start_tick=24, jitter_ticks=-10, tempo_map=tempo_map_120)

    result = tight_quantizer.quantize([note_out, note_in], tempo_map_120)
    assert result[0].tick == 14  # Unsnapped
    assert result[1].tick == 24  # Snapped


def test_strict_grid_snapping_eliminates_unsnapped_ticks(
    quantizer: NoteQuantizer, tempo_map_120: TempoMap
) -> None:
    """Prompt 7.1: Verify default strict grid snapping snaps raw ticks to active subdivisions."""
    assert quantizer.strict_snap is True

    # Notes with raw tick positions that would fall outside traditional tolerance
    notes = [
        _make_note(
            start_tick=0, jitter_ticks=20, tempo_map=tempo_map_120
        ),  # tick 20 -> closest is 24
        _make_note(
            start_tick=48, jitter_ticks=10, tempo_map=tempo_map_120
        ),  # tick 58 -> closest is 64 (diff 6)
        _make_note(
            start_tick=96, jitter_ticks=-20, tempo_map=tempo_map_120
        ),  # tick 76 -> closest is 72 (diff 4)
        _make_note(
            start_tick=192, jitter_ticks=22, tempo_map=tempo_map_120
        ),  # tick 214 -> closest is 216 (diff 2)
    ]

    result = quantizer.quantize(notes, tempo_map_120)
    valid_subdivs = {24, 32, 48, 64, 72, 96, 120, 128, 144, 160, 168, 192, 216}

    for note in result:
        # Every note must strictly lie on a valid subdivision point
        assert any(note.tick % s == 0 for s in quantizer.subdivisions)
        assert note.tick in valid_subdivs


def test_chord_fusion_window_35ms(quantizer: NoteQuantizer, tempo_map_120: TempoMap) -> None:
    """Prompt 7.1: Verify onsets within 35ms sliding window fuse into exact same onset tick."""
    # At 120 BPM, 1 tick = 2.604ms. 35ms = ~13.4 ticks.
    # Note 1: at t = 0.0s (tick 0), pitch 60
    # Note 2: at t = 0.015s (tick 5.76, 15ms later), pitch 64
    # Note 3: at t = 0.030s (tick 11.52, 30ms later), pitch 67
    n1 = NoteEvent(start_time=0.0, end_time=0.4, pitch=60, amplitude=0.8)
    n2 = NoteEvent(start_time=0.015, end_time=0.4, pitch=64, amplitude=0.85)
    n3 = NoteEvent(start_time=0.030, end_time=0.4, pitch=67, amplitude=0.9)

    fused = quantizer.fuse_chord_onsets([n1, n2, n3])
    # All 3 notes must have identical start_time (cluster anchor = 0.0)
    assert len(fused) == 3
    assert fused[0].start_time == 0.0
    assert fused[1].start_time == 0.0
    assert fused[2].start_time == 0.0

    # Quantize to 192 PPQ grid
    result = quantizer.quantize([n1, n2, n3], tempo_map_120)
    assert len(result) == 3
    assert all(n.tick == 0 for n in result)
    assert {n.pitch for n in result} == {60, 64, 67}


def test_chord_fusion_outside_window_remains_distinct(
    quantizer: NoteQuantizer, tempo_map_120: TempoMap
) -> None:
    """Prompt 7.1: Verify onsets separated by > 35ms remain distinct."""
    # Note 1 at 0.0s, Note 2 at 0.050s (50ms > 35ms window)
    n1 = NoteEvent(start_time=0.0, end_time=0.4, pitch=60, amplitude=0.8)
    n2 = NoteEvent(start_time=0.050, end_time=0.45, pitch=64, amplitude=0.85)

    fused = quantizer.fuse_chord_onsets([n1, n2])
    assert fused[0].start_time == 0.0
    assert fused[1].start_time == 0.050


def test_minimum_note_spacing_filter(tempo_map_120: TempoMap) -> None:
    """Prompt 7.1: Enforce minimum note spacing of 24 ticks (1/32 note), filtering micro-jitters."""
    quantizer = NoteQuantizer(tolerance_ticks=4, min_spacing_ticks=24)

    # Legitimate note at tick 48 (1/16 note, amp 0.9).
    # Noise micro-jitter at tick 64 (1/12 triplet note, amp 0.3).
    # Time delta: 16 ticks = 41.6ms > 35ms (not fused by chord fusion).
    # Grid distance: 64 - 48 = 16 ticks < 24 ticks (unplayable micro-spacing artifact).
    n_primary = NoteEvent(
        start_time=tempo_map_120.tick_to_seconds(48),
        end_time=tempo_map_120.tick_to_seconds(96),
        pitch=60,
        amplitude=0.9,
    )
    n_noise = NoteEvent(
        start_time=tempo_map_120.tick_to_seconds(64),
        end_time=tempo_map_120.tick_to_seconds(96),
        pitch=62,
        amplitude=0.3,
    )
    # Next legitimate note at tick 96 (96 - 48 = 48 >= 24 ticks)
    n_next = NoteEvent(
        start_time=tempo_map_120.tick_to_seconds(96),
        end_time=tempo_map_120.tick_to_seconds(144),
        pitch=64,
        amplitude=0.85,
    )

    result = quantizer.quantize([n_primary, n_noise, n_next], tempo_map_120)
    # The noise artifact at sub-24 spacing is filtered
    assert len(result) == 2
    assert [n.tick for n in result] == [48, 96]
    assert [n.pitch for n in result] == [60, 64]


def test_minimum_note_spacing_preserves_chords(
    quantizer: NoteQuantizer, tempo_map_120: TempoMap
) -> None:
    """Prompt 7.1: Verify notes at the exact same tick (chords) are not eliminated by spacing filter."""
    c1 = _make_note(start_tick=96, pitch=60, amplitude=0.8, tempo_map=tempo_map_120)
    c2 = _make_note(start_tick=96, pitch=64, amplitude=0.8, tempo_map=tempo_map_120)
    next_note = _make_note(start_tick=144, pitch=67, amplitude=0.8, tempo_map=tempo_map_120)

    result = quantizer.quantize([c1, c2, next_note], tempo_map_120)
    assert len(result) == 3
    # Two notes at tick 96 (chord) and one at tick 144
    assert [n.tick for n in result] == [96, 96, 144]


def test_tie_breaking_rules(quantizer: NoteQuantizer) -> None:
    """Validate musical hierarchy priority tie-breaking at all 6 conflict points.

    Hierarchy: 192 (1/4) > 96 (1/8) > 48 (1/16) > 64 (1/12) > 32 (1/24) > 24 (1/32).
    """
    # Tick 12: equidistant to 0 (1/4, prio 6) and 24 (1/32, prio 1) -> 0 wins
    assert quantizer.snap_tick(12) == 0
    # Tick 28: equidistant to 24 (1/32, prio 1) and 32 (1/24, prio 2) -> 32 wins
    assert quantizer.snap_tick(28) == 32
    # Tick 40: equidistant to 32 (1/24, prio 2) and 48 (1/16, prio 4) -> 48 wins
    assert quantizer.snap_tick(40) == 48
    # Tick 56: equidistant to 48 (1/16, prio 4) and 64 (1/12, prio 3) -> 48 wins
    assert quantizer.snap_tick(56) == 48
    # Tick 68: equidistant to 64 (1/12, prio 3) and 72 (1/32, prio 1) -> 64 wins
    assert quantizer.snap_tick(68) == 64
    # Tick 84: equidistant to 72 (1/32, prio 1) and 96 (1/8, prio 5) -> 96 wins
    assert quantizer.snap_tick(84) == 96


def test_boundary_conditions(quantizer: NoteQuantizer) -> None:
    """Validate boundary conditions: 0, negative ticks near 0, and large ticks."""
    assert quantizer.snap_tick(0) == 0
    # Slight negative tick within tolerance snaps to 0
    assert quantizer.snap_tick(-5) == 0
    # 500000 is a multiple of 32 (500000 / 32 = 15625); 500002 snaps to 500000
    assert quantizer.snap_tick(500002) == 500000


def test_deduplication_identical_tick_and_pitch(
    quantizer: NoteQuantizer, tempo_map_120: TempoMap
) -> None:
    """Ensure duplicate notes at the same tick and pitch merge, keeping max amplitude & duration."""
    note_a = NoteEvent(
        start_time=tempo_map_120.tick_to_seconds(192),
        end_time=tempo_map_120.tick_to_seconds(192 + 96),  # 96 ticks
        pitch=60,
        amplitude=0.55,
    )
    # Note B is slightly jittered (+4 ticks), snapping to 192, with higher amplitude and longer duration
    note_b = NoteEvent(
        start_time=tempo_map_120.tick_to_seconds(196),
        end_time=tempo_map_120.tick_to_seconds(196 + 144),  # 144 ticks
        pitch=60,
        amplitude=0.92,
    )

    result = quantizer.quantize([note_a, note_b], tempo_map_120)
    assert len(result) == 1
    assert result[0].tick == 192
    assert result[0].pitch == 60
    assert result[0].amplitude == 0.92  # max(0.55, 0.92)
    assert result[0].duration_ticks == 144  # max(96, 144)


def test_deduplication_preserves_chords_and_different_ticks(
    quantizer: NoteQuantizer, tempo_map_120: TempoMap
) -> None:
    """Ensure distinct pitches at the same tick (chords) and identical pitches at different ticks are kept."""
    # Polyphonic chord at tick 192: Pitch 60 and Pitch 64
    chord_root = _make_note(start_tick=192, pitch=60, amplitude=0.7, tempo_map=tempo_map_120)
    chord_third = _make_note(start_tick=192, pitch=64, amplitude=0.8, tempo_map=tempo_map_120)

    # Repeated pitch 60 at tick 384
    next_note = _make_note(start_tick=384, pitch=60, amplitude=0.75, tempo_map=tempo_map_120)

    result = quantizer.quantize([chord_root, chord_third, next_note], tempo_map_120)
    assert len(result) == 3
    assert result[0].tick == 192 and result[0].pitch == 60
    assert result[1].tick == 192 and result[1].pitch == 64
    assert result[2].tick == 384 and result[2].pitch == 60


def test_empty_note_list(quantizer: NoteQuantizer, tempo_map_120: TempoMap) -> None:
    """Ensure an empty NoteEvent list returns an empty list without error."""
    assert quantizer.quantize([], tempo_map_120) == []


def test_chronological_sorting_output(quantizer: NoteQuantizer, tempo_map_120: TempoMap) -> None:
    """Ensure notes provided out of chronological order are returned strictly sorted by tick, then pitch."""
    note_late = _make_note(start_tick=384, pitch=60, tempo_map=tempo_map_120)
    note_early = _make_note(start_tick=0, pitch=60, tempo_map=tempo_map_120)
    note_mid_high = _make_note(start_tick=192, pitch=64, tempo_map=tempo_map_120)
    note_mid_low = _make_note(start_tick=192, pitch=60, tempo_map=tempo_map_120)

    result = quantizer.quantize([note_late, note_early, note_mid_high, note_mid_low], tempo_map_120)
    assert len(result) == 4
    assert [(n.tick, n.pitch) for n in result] == [
        (0, 60),
        (192, 60),
        (192, 64),
        (384, 60),
    ]


def test_multi_tempo_map_variable_bpm(
    quantizer: NoteQuantizer, variable_tempo_map: TempoMap
) -> None:
    """Validate quantization across dynamic BPM changes (120 BPM -> 140 BPM at tick 768)."""
    # Note in 120 BPM section (0.5s = tick 192)
    note_120 = NoteEvent(
        start_time=variable_tempo_map.tick_to_seconds(192),
        end_time=variable_tempo_map.tick_to_seconds(288),
        pitch=60,
        amplitude=0.8,
    )
    # Note exactly at the tempo change boundary (tick 768)
    note_transition = NoteEvent(
        start_time=variable_tempo_map.tick_to_seconds(768),
        end_time=variable_tempo_map.tick_to_seconds(864),
        pitch=62,
        amplitude=0.85,
    )
    # Note in 140 BPM section (tick 960) with slight jitter (+3 ticks)
    note_140_jitter = NoteEvent(
        start_time=variable_tempo_map.tick_to_seconds(963),
        end_time=variable_tempo_map.tick_to_seconds(1059),
        pitch=64,
        amplitude=0.9,
    )

    result = quantizer.quantize([note_120, note_transition, note_140_jitter], variable_tempo_map)
    assert len(result) == 3
    assert [n.tick for n in result] == [192, 768, 960]


def test_quantized_note_model_validation() -> None:
    """Validate QuantizedNote parameter bounds and exception handling."""
    valid = QuantizedNote(tick=192, pitch=60, duration_ticks=96, amplitude=0.8)
    assert valid.tick == 192
    assert valid.pitch == 60
    assert valid.duration_ticks == 96
    assert valid.amplitude == 0.8

    with pytest.raises(ValueError):
        QuantizedNote(tick=-1, pitch=60, duration_ticks=96, amplitude=0.8)

    with pytest.raises(ValueError):
        QuantizedNote(tick=0, pitch=128, duration_ticks=96, amplitude=0.8)

    with pytest.raises(ValueError):
        QuantizedNote(tick=0, pitch=60, duration_ticks=-5, amplitude=0.8)

    with pytest.raises(ValueError):
        QuantizedNote(tick=0, pitch=60, duration_ticks=96, amplitude=1.2)


def test_note_quantizer_validation() -> None:
    """Ensure invalid NoteQuantizer configuration raises ValueError."""
    with pytest.raises(ValueError):
        NoteQuantizer(tolerance_ticks=-1)

    with pytest.raises(ValueError):
        NoteQuantizer(resolution=0)

    with pytest.raises(ValueError):
        NoteQuantizer(subdivisions=[])

    with pytest.raises(ValueError):
        NoteQuantizer(subdivisions=[192, -24])

    quantizer = NoteQuantizer()
    with pytest.raises(ValueError):
        quantizer.snap_tick(192, tolerance_ticks=-2)


# ---------------------------------------------------------------------------
# 11. Ghost Note Filtering & Sustain-Hold / Re-Trigger Merging Tests
# ---------------------------------------------------------------------------


def test_min_amplitude_filtering(tempo_map_120: TempoMap) -> None:
    """Verify notes below min_amplitude threshold are filtered out."""
    quantizer = NoteQuantizer(min_amplitude=0.5)
    notes = [
        NoteEvent(start_time=0.0, end_time=0.5, pitch=60, amplitude=0.8),  # >= 0.5 -> kept
        NoteEvent(
            start_time=0.5, end_time=1.0, pitch=64, amplitude=0.3
        ),  # < 0.5 -> ghost note dropped
        NoteEvent(start_time=1.0, end_time=1.5, pitch=67, amplitude=0.6),  # >= 0.5 -> kept
    ]
    result = quantizer.quantize(notes, tempo_map_120)
    assert len(result) == 2
    assert [n.pitch for n in result] == [60, 67]


def test_min_amplitude_validation() -> None:
    """Verify invalid min_amplitude values raise ValueError."""
    with pytest.raises(ValueError, match="min_amplitude"):
        NoteQuantizer(min_amplitude=-0.1)
    with pytest.raises(ValueError, match="min_amplitude"):
        NoteQuantizer(min_amplitude=1.5)


def test_retrigger_merge_overlapping_notes() -> None:
    """Verify consecutive overlapping notes on the same pitch merge into a prolonged note."""
    quantizer = NoteQuantizer()
    notes = [
        NoteEvent(start_time=0.0, end_time=1.0, pitch=60, amplitude=0.7),
        NoteEvent(start_time=0.8, end_time=1.8, pitch=60, amplitude=0.9),  # Overlapping pitch 60
    ]
    merged = quantizer.merge_retrigger_notes(notes)
    assert len(merged) == 1
    assert merged[0].start_time == 0.0
    assert merged[0].end_time == 1.8
    assert merged[0].pitch == 60
    assert merged[0].amplitude == 0.9


def test_retrigger_merge_near_contiguous_notes(tempo_map_120: TempoMap) -> None:
    """Verify notes with a near-contiguous micro-gap (<= 0.1s / 48 ticks) merge into a prolonged note."""
    quantizer = NoteQuantizer(retrigger_merge_gap_s=0.1)
    notes = [
        NoteEvent(start_time=0.0, end_time=0.5, pitch=60, amplitude=0.8),
        # Gap: 0.55 - 0.5 = 0.05s <= 0.1s
        NoteEvent(start_time=0.55, end_time=1.2, pitch=60, amplitude=0.85),
    ]
    merged = quantizer.merge_retrigger_notes(notes, tempo_map=tempo_map_120)
    assert len(merged) == 1
    assert merged[0].start_time == 0.0
    assert merged[0].end_time == 1.2
    assert merged[0].pitch == 60


def test_retrigger_merge_distinct_pitches_preserved() -> None:
    """Verify consecutive notes on different pitches do not merge."""
    quantizer = NoteQuantizer()
    notes = [
        NoteEvent(start_time=0.0, end_time=1.0, pitch=60, amplitude=0.8),
        NoteEvent(start_time=0.5, end_time=1.5, pitch=64, amplitude=0.8),
    ]
    merged = quantizer.merge_retrigger_notes(notes)
    assert len(merged) == 2
    assert [n.pitch for n in merged] == [60, 64]


def test_quantize_with_merge_retrigger_enabled(tempo_map_120: TempoMap) -> None:
    """Verify quantize with merge_retrigger=True merges chopped re-triggers into a single prolonged note."""
    quantizer = NoteQuantizer(merge_retrigger=True)
    # Ringing chord chopped into two micro-fragments
    notes = [
        NoteEvent(start_time=0.0, end_time=0.48, pitch=60, amplitude=0.8),
        NoteEvent(start_time=0.50, end_time=1.0, pitch=60, amplitude=0.85),
    ]
    result = quantizer.quantize(notes, tempo_map_120)
    assert len(result) == 1
    assert result[0].tick == 0
    # Combined duration in ticks should span ~1.0s (384 ticks at 120 BPM)
    assert result[0].duration_ticks >= 380


def test_configurable_chord_fusion_and_spacing() -> None:
    """Verify configurable chord_fusion_window_s and min_spacing_ticks."""
    q = NoteQuantizer(chord_fusion_window_s=0.05, min_spacing_ticks=32)
    assert q.chord_fusion_window_s == 0.05
    assert q.min_spacing_ticks == 32


def test_quantize_excessive_min_amplitude_fallback(tempo_map_120: TempoMap) -> None:
    """Verify quantizer falls back to top notes instead of returning an empty list when min_amplitude is too high."""
    q = NoteQuantizer(min_amplitude=0.99)
    notes = [
        NoteEvent(start_time=0.0, end_time=0.5, pitch=60, amplitude=0.4),
        NoteEvent(start_time=0.5, end_time=1.0, pitch=62, amplitude=0.6),
        NoteEvent(start_time=1.0, end_time=1.5, pitch=64, amplitude=0.5),
        NoteEvent(start_time=1.5, end_time=2.0, pitch=65, amplitude=0.3),
    ]
    result = q.quantize(notes, tempo_map_120)
    # Must never be empty
    assert len(result) > 0
    # Top amplitude notes should be preserved
    pitches = {n.pitch for n in result}
    assert 62 in pitches  # Highest amplitude (0.6) must be preserved
