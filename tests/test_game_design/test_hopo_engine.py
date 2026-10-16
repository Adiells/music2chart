"""Comprehensive unit tests for HopoEngine and strum forcing rules.

Covers:
- Natural HOPO threshold (<= 65 ticks with fret variation)
- Strums (> 65 ticks)
- Forced strums on repeated frets/chords
- First note of track is always Strum
- Rapid ascending/descending scales and trills
- Chords and Open note interactions
- Full Game Design Pipeline End-to-End Integration
"""

from __future__ import annotations

import pytest

from src.game_design.chord_builder import ChordBuilder
from src.game_design.hopo_engine import HopoEngine
from src.game_design.pitch_to_fret import PitchToFretMapper
from src.game_design.quantizer import NoteQuantizer
from src.game_design.star_power_generator import StarPowerGenerator
from src.game_design.sustain_processor import SustainProcessor
from src.models import (
    BPMChange,
    ChartNote,
    FretType,
    NoteEvent,
    SongTrack,
    TempoMap,
    TimeSignature,
)

# ---------------------------------------------------------------------------
# Test Helpers & Fixtures
# ---------------------------------------------------------------------------


def _make_note(
    tick: int,
    fret: int | FretType,
    sustain_length: int = 0,
    is_hopo: bool = False,
) -> ChartNote:
    """Helper to synthesize a ChartNote with typed fret enum."""
    fret_val = FretType(fret) if isinstance(fret, int) else fret
    return ChartNote(
        tick=tick,
        fret=fret_val,
        sustain_length=sustain_length,
        is_hopo=is_hopo,
    )


@pytest.fixture
def default_hopo_engine() -> HopoEngine:
    """Return a standard HopoEngine with 65-tick threshold."""
    return HopoEngine(hopo_threshold=65)


# ---------------------------------------------------------------------------
# 1. HopoEngine Tests
# ---------------------------------------------------------------------------


class TestHopoEngine:
    """Test suite for HopoEngine mechanics."""

    def test_hopo_empty_notes(self, default_hopo_engine: HopoEngine) -> None:
        """Verify empty input returns empty list."""
        assert default_hopo_engine.process([]) == []

    def test_hopo_single_note_first_is_strum(self, default_hopo_engine: HopoEngine) -> None:
        """Verify the first note of a track is always a strum (is_hopo=False)."""
        notes = [_make_note(tick=0, fret=FretType.GREEN)]
        result = default_hopo_engine.process(notes)
        assert len(result) == 1
        assert result[0].is_hopo is False

    def test_hopo_consecutive_within_threshold_different_frets(
        self, default_hopo_engine: HopoEngine
    ) -> None:
        """Verify consecutive notes <= 65 ticks with different frets are marked as HOPO."""
        notes = [
            _make_note(tick=0, fret=FretType.GREEN),
            _make_note(tick=48, fret=FretType.RED),
        ]
        result = default_hopo_engine.process(notes)
        assert len(result) == 2
        assert result[0].is_hopo is False  # First note is strum
        assert result[1].is_hopo is True  # HOPO

    def test_hopo_exact_threshold_boundary_65(self, default_hopo_engine: HopoEngine) -> None:
        """Verify note exactly at threshold boundary (65 ticks) is marked as HOPO."""
        notes = [
            _make_note(tick=0, fret=FretType.GREEN),
            _make_note(tick=65, fret=FretType.RED),
        ]
        result = default_hopo_engine.process(notes)
        assert result[1].is_hopo is True

    def test_hopo_beyond_threshold_boundary_66(self, default_hopo_engine: HopoEngine) -> None:
        """Verify note just beyond threshold boundary (66 ticks) is marked as Strum."""
        notes = [
            _make_note(tick=0, fret=FretType.GREEN),
            _make_note(tick=66, fret=FretType.RED),
        ]
        result = default_hopo_engine.process(notes)
        assert result[1].is_hopo is False

    @pytest.mark.parametrize("spacing", [96, 192, 384])
    def test_hopo_large_spacing_marked_as_strum(
        self, default_hopo_engine: HopoEngine, spacing: int
    ) -> None:
        """Verify notes spaced beyond 65 ticks (e.g. 96, 192 ticks) are marked as Strum."""
        notes = [
            _make_note(tick=0, fret=FretType.GREEN),
            _make_note(tick=spacing, fret=FretType.RED),
        ]
        result = default_hopo_engine.process(notes)
        assert result[1].is_hopo is False

    def test_hopo_repeated_frets_within_threshold_forced_strum(
        self, default_hopo_engine: HopoEngine
    ) -> None:
        """Verify repeated frets within <= 65 ticks force Strum."""
        notes = [
            _make_note(tick=0, fret=FretType.GREEN),
            _make_note(tick=48, fret=FretType.GREEN),
        ]
        result = default_hopo_engine.process(notes)
        assert result[0].is_hopo is False
        assert result[1].is_hopo is False  # Repeated fret must be strummed

    def test_hopo_rapid_ascending_scale(self, default_hopo_engine: HopoEngine) -> None:
        """Verify rapid scale (0 -> 1 -> 2 -> 3 -> 4 every 48 ticks) marks all except first as HOPOs."""
        notes = [
            _make_note(tick=0, fret=FretType.GREEN),
            _make_note(tick=48, fret=FretType.RED),
            _make_note(tick=96, fret=FretType.YELLOW),
            _make_note(tick=144, fret=FretType.BLUE),
            _make_note(tick=192, fret=FretType.ORANGE),
        ]
        result = default_hopo_engine.process(notes)
        assert [n.is_hopo for n in result] == [False, True, True, True, True]

    def test_hopo_rapid_descending_scale(self, default_hopo_engine: HopoEngine) -> None:
        """Verify rapid scale (4 -> 3 -> 2 -> 1 -> 0 every 48 ticks) marks all except first as HOPOs."""
        notes = [
            _make_note(tick=0, fret=FretType.ORANGE),
            _make_note(tick=48, fret=FretType.BLUE),
            _make_note(tick=96, fret=FretType.YELLOW),
            _make_note(tick=144, fret=FretType.RED),
            _make_note(tick=192, fret=FretType.GREEN),
        ]
        result = default_hopo_engine.process(notes)
        assert [n.is_hopo for n in result] == [False, True, True, True, True]

    def test_hopo_alternating_trill(self, default_hopo_engine: HopoEngine) -> None:
        """Verify alternating trill (0 -> 1 -> 0 -> 1 -> 0 at 48 ticks) keeps alternating HOPOs."""
        notes = [
            _make_note(tick=0, fret=FretType.GREEN),
            _make_note(tick=48, fret=FretType.RED),
            _make_note(tick=96, fret=FretType.GREEN),
            _make_note(tick=144, fret=FretType.RED),
            _make_note(tick=192, fret=FretType.GREEN),
        ]
        result = default_hopo_engine.process(notes)
        assert [n.is_hopo for n in result] == [False, True, True, True, True]

    def test_hopo_repeated_pairs_pattern(self, default_hopo_engine: HopoEngine) -> None:
        """Verify repeated pairs pattern (0 -> 0 -> 1 -> 1 at 48 ticks) alternates strum and HOPO."""
        notes = [
            _make_note(tick=0, fret=FretType.GREEN),
            _make_note(tick=48, fret=FretType.GREEN),  # repeat -> Strum
            _make_note(tick=96, fret=FretType.RED),  # diff fret -> HOPO
            _make_note(tick=144, fret=FretType.RED),  # repeat -> Strum
        ]
        result = default_hopo_engine.process(notes)
        assert [n.is_hopo for n in result] == [False, False, True, False]

    def test_hopo_single_to_chord_transition(self, default_hopo_engine: HopoEngine) -> None:
        """Verify transitioning from single note to chord forces Strum on all chord notes."""
        notes = [
            _make_note(tick=0, fret=FretType.GREEN),
            _make_note(tick=48, fret=FretType.RED),
            _make_note(tick=48, fret=FretType.YELLOW),
        ]
        result = default_hopo_engine.process(notes)
        chord_at_48 = [n for n in result if n.tick == 48]
        assert len(chord_at_48) == 2
        assert all(n.is_hopo is False for n in chord_at_48)

    def test_hopo_chord_to_chord_transition(self, default_hopo_engine: HopoEngine) -> None:
        """Verify transitioning from chord to chord within <= 65 ticks forces Strum on both."""
        notes = [
            _make_note(tick=0, fret=FretType.GREEN),
            _make_note(tick=0, fret=FretType.RED),
            _make_note(tick=48, fret=FretType.RED),
            _make_note(tick=48, fret=FretType.YELLOW),
        ]
        result = default_hopo_engine.process(notes)
        assert all(n.is_hopo is False for n in result)

    def test_hopo_chord_to_single_note_new_fret(self, default_hopo_engine: HopoEngine) -> None:
        """Verify chord followed by single note on a new fret within <= 65 ticks is HOPO."""
        notes = [
            _make_note(tick=0, fret=FretType.GREEN),
            _make_note(tick=0, fret=FretType.RED),
            _make_note(tick=48, fret=FretType.YELLOW),  # Fret 2 was not in {0, 1}
        ]
        result = default_hopo_engine.process(notes)
        assert result[2].tick == 48
        assert result[2].is_hopo is True

    def test_hopo_chord_to_single_note_held_fret(self, default_hopo_engine: HopoEngine) -> None:
        """Verify chord followed by single note that was part of the chord forces Strum."""
        notes = [
            _make_note(tick=0, fret=FretType.GREEN),
            _make_note(tick=0, fret=FretType.RED),
            _make_note(tick=48, fret=FretType.RED),  # Fret 1 was in previous chord
        ]
        result = default_hopo_engine.process(notes)
        assert result[2].is_hopo is False

    def test_hopo_open_note_to_fretted(self, default_hopo_engine: HopoEngine) -> None:
        """Verify Open note (7) followed by fretted note (0) at 48 ticks is HOPO (hammer-on)."""
        notes = [
            _make_note(tick=0, fret=FretType.OPEN),
            _make_note(tick=48, fret=FretType.GREEN),
        ]
        result = default_hopo_engine.process(notes)
        assert result[0].is_hopo is False
        assert result[1].is_hopo is True

    def test_hopo_fretted_to_open_note(self, default_hopo_engine: HopoEngine) -> None:
        """Verify fretted note (0) followed by Open note (7) at 48 ticks is HOPO (pull-off)."""
        notes = [
            _make_note(tick=0, fret=FretType.GREEN),
            _make_note(tick=48, fret=FretType.OPEN),
        ]
        result = default_hopo_engine.process(notes)
        assert result[0].is_hopo is False
        assert result[1].is_hopo is True

    def test_hopo_repeated_open_notes(self, default_hopo_engine: HopoEngine) -> None:
        """Verify repeated Open notes at 48 ticks force Strum."""
        notes = [
            _make_note(tick=0, fret=FretType.OPEN),
            _make_note(tick=48, fret=FretType.OPEN),
        ]
        result = default_hopo_engine.process(notes)
        assert result[0].is_hopo is False
        assert result[1].is_hopo is False

    def test_hopo_preserves_sustain_and_fret(self, default_hopo_engine: HopoEngine) -> None:
        """Verify HopoEngine preserves tick, fret, and sustain_length attributes unchanged."""
        notes = [
            _make_note(tick=0, fret=FretType.GREEN, sustain_length=168),
            _make_note(tick=48, fret=FretType.RED, sustain_length=96),
        ]
        result = default_hopo_engine.process(notes)
        assert result[0].sustain_length == 168
        assert result[1].sustain_length == 96
        assert result[0].fret == FretType.GREEN
        assert result[1].fret == FretType.RED

    def test_hopo_unsorted_input_handled(self, default_hopo_engine: HopoEngine) -> None:
        """Verify unsorted input list is processed in ascending chronological order."""
        notes = [
            _make_note(tick=48, fret=FretType.RED),
            _make_note(tick=0, fret=FretType.GREEN),
        ]
        result = default_hopo_engine.process(notes)
        assert result[0].tick == 0
        assert result[0].is_hopo is False
        assert result[1].tick == 48
        assert result[1].is_hopo is True

    def test_hopo_custom_threshold(self) -> None:
        """Verify custom hopo_threshold parameter is applied."""
        engine = HopoEngine(hopo_threshold=96)
        notes = [
            _make_note(tick=0, fret=FretType.GREEN),
            _make_note(tick=96, fret=FretType.RED),
            _make_note(tick=193, fret=FretType.YELLOW),
        ]
        result = engine.process(notes)
        assert result[1].is_hopo is True  # 96 <= 96 -> HOPO
        assert result[2].is_hopo is False  # 97 > 96 -> Strum

    def test_hopo_invalid_threshold_raises(self) -> None:
        """Verify negative threshold raises ValueError."""
        with pytest.raises(ValueError):
            HopoEngine(hopo_threshold=-1)


# ---------------------------------------------------------------------------
# Legacy HopoEngine Tests (preservation)
# ---------------------------------------------------------------------------


def test_hopo_detection_fast_different_frets() -> None:
    """Validate that consecutive notes within 65 ticks on different frets are marked as HOPO."""
    notes = [
        ChartNote(tick=0, fret=FretType.GREEN),
        ChartNote(tick=48, fret=FretType.RED),
        ChartNote(tick=96, fret=FretType.YELLOW),
    ]

    engine = HopoEngine(hopo_threshold=65)
    processed = engine.process_hopos(notes)

    assert not processed[0].is_hopo
    assert processed[1].is_hopo
    assert processed[2].is_hopo


def test_strum_forced_on_identical_fret_repeat() -> None:
    """Validate that consecutive notes on the same fret are forced to strum even if fast."""
    notes = [
        ChartNote(tick=0, fret=FretType.GREEN),
        ChartNote(tick=48, fret=FretType.GREEN),
        ChartNote(tick=96, fret=FretType.RED),
    ]

    engine = HopoEngine(hopo_threshold=65)
    processed = engine.process_hopos(notes)

    assert not processed[0].is_hopo
    assert not processed[1].is_hopo
    assert processed[2].is_hopo


def test_large_interval_exceeding_threshold() -> None:
    """Validate that intervals greater than threshold (e.g. 96 ticks) default to strum."""
    notes = [
        ChartNote(tick=0, fret=FretType.GREEN),
        ChartNote(tick=96, fret=FretType.RED),
    ]

    engine = HopoEngine(hopo_threshold=65)
    processed = engine.process_hopos(notes)

    assert not processed[0].is_hopo
    assert not processed[1].is_hopo


def test_chords_default_to_strum() -> None:
    """Validate that multi-note chords are not marked as natural HOPOs."""
    notes = [
        ChartNote(tick=0, fret=FretType.GREEN),
        ChartNote(tick=48, fret=FretType.GREEN),
        ChartNote(tick=48, fret=FretType.RED),
    ]

    engine = HopoEngine(hopo_threshold=65)
    processed = engine.process_hopos(notes)

    assert not processed[0].is_hopo
    assert not processed[1].is_hopo
    assert not processed[2].is_hopo


def test_add_force_modifiers() -> None:
    """Validate injection of STRUM_FORCE (6) modifier for repeated fast frets."""
    notes = [
        ChartNote(tick=0, fret=FretType.GREEN),
        ChartNote(tick=48, fret=FretType.GREEN),
    ]

    engine = HopoEngine(hopo_threshold=65)
    modified = engine.add_force_modifiers(notes)

    frets_at_48 = [n.fret for n in modified if n.tick == 48]
    assert FretType.GREEN in frets_at_48
    assert FretType.STRUM_FORCE in frets_at_48


def test_melodic_run_hopo_forcing() -> None:
    """Prompt 7.3: In melodic runs (<= 96 ticks), note 1 is Strum anchor, notes 2..N get HOPO_FORCE."""
    notes = [
        ChartNote(tick=0, fret=FretType.GREEN),
        ChartNote(tick=48, fret=FretType.RED),
        ChartNote(tick=96, fret=FretType.YELLOW),
        ChartNote(tick=144, fret=FretType.BLUE),
        ChartNote(tick=192, fret=FretType.ORANGE),
    ]

    engine = HopoEngine(run_threshold=96)
    result = engine.add_force_modifiers(notes)

    # Note 1 at tick 0: Strum anchor, no HOPO_FORCE
    assert FretType.HOPO_FORCE not in [n.fret for n in result if n.tick == 0]

    # Notes 2..5 at ticks 48, 96, 144, 192: each must have HOPO_FORCE
    for t in [48, 96, 144, 192]:
        frets_at_t = [n.fret for n in result if n.tick == t]
        assert FretType.HOPO_FORCE in frets_at_t


def test_melodic_run_repeated_fret_strum_forcing() -> None:
    """Prompt 7.3: Repeated consecutive frets in rapid window emit STRUM_FORCE modifier."""
    notes = [
        ChartNote(tick=0, fret=FretType.GREEN),
        ChartNote(tick=48, fret=FretType.RED),
        ChartNote(tick=96, fret=FretType.RED),  # Repeated fret -> STRUM_FORCE
        ChartNote(tick=144, fret=FretType.YELLOW),  # Next note in run -> HOPO_FORCE
    ]

    engine = HopoEngine(run_threshold=96)
    result = engine.add_force_modifiers(notes)

    # Tick 48: Red note 2 in run -> HOPO_FORCE
    assert FretType.HOPO_FORCE in [n.fret for n in result if n.tick == 48]
    # Tick 96: Repeated Red -> STRUM_FORCE
    assert FretType.STRUM_FORCE in [n.fret for n in result if n.tick == 96]
    assert FretType.HOPO_FORCE not in [n.fret for n in result if n.tick == 96]
    # Tick 144: Yellow note 2 after strum anchor -> HOPO_FORCE
    assert FretType.HOPO_FORCE in [n.fret for n in result if n.tick == 144]


def test_gap_breaks_melodic_run() -> None:
    """Prompt 7.3: Distance > 96 ticks breaks run; following note is Strum anchor (no modifier)."""
    notes = [
        ChartNote(tick=0, fret=FretType.GREEN),
        ChartNote(tick=48, fret=FretType.RED),  # HOPO_FORCE
        ChartNote(tick=240, fret=FretType.YELLOW),  # 240 - 48 = 192 > 96 -> Strum anchor
    ]

    engine = HopoEngine(run_threshold=96)
    result = engine.add_force_modifiers(notes)

    assert FretType.HOPO_FORCE in [n.fret for n in result if n.tick == 48]
    assert FretType.HOPO_FORCE not in [n.fret for n in result if n.tick == 240]
    assert FretType.STRUM_FORCE not in [n.fret for n in result if n.tick == 240]


# ---------------------------------------------------------------------------
# End-to-End Game Design Pipeline Integration Test
# ---------------------------------------------------------------------------


def test_game_design_end_to_end_pipeline() -> None:
    """Test full Phase 4 Game Design pipeline integration from NoteEvents to SongTrack.

    Flow: NoteEvents -> NoteQuantizer -> PitchToFretMapper -> ChordBuilder ->
          HopoEngine -> SustainProcessor -> StarPowerGenerator -> SongTrack.
    """
    tempo_map = TempoMap(
        resolution=192,
        bpm_changes=[BPMChange(tick=0, bpm=120.0)],
        time_signatures=[TimeSignature(tick=0, numerator=4, denominator=4)],
    )

    # Synthesize realistic note events:
    # 1. Strum quarter note (tick 0)
    # 2. Fast ascending scale with HOPOs (ticks 192, 240, 288, 336)
    # 3. Two-note power chord at tick 768
    # 4. Long sustain note at tick 1152 (duration = 500 ticks)
    # 5. Note at tick 1344 (spacing = 192 ticks, causing sustain clamping)
    events = [
        NoteEvent(start_time=0.0, end_time=0.2, pitch=45, amplitude=0.9),  # ~tick 0
        NoteEvent(start_time=0.5, end_time=0.6, pitch=50, amplitude=0.8),  # ~tick 192
        NoteEvent(start_time=0.625, end_time=0.7, pitch=52, amplitude=0.8),  # ~tick 240
        NoteEvent(start_time=0.75, end_time=0.8, pitch=55, amplitude=0.8),  # ~tick 288
        NoteEvent(start_time=0.875, end_time=0.95, pitch=57, amplitude=0.8),  # ~tick 336
        # Chord at tick 768 (2.0s)
        NoteEvent(start_time=2.0, end_time=2.2, pitch=48, amplitude=0.9),
        NoteEvent(start_time=2.0, end_time=2.2, pitch=55, amplitude=0.85),
        # Long note at tick 1152 (3.0s, duration 1.302s ~500 ticks)
        NoteEvent(start_time=3.0, end_time=4.302, pitch=60, amplitude=0.9),
        # Next note at tick 1344 (3.5s)
        NoteEvent(start_time=3.5, end_time=3.7, pitch=62, amplitude=0.8),
    ]

    # Pipeline stages
    quantizer = NoteQuantizer(tolerance_ticks=16)
    q_notes = quantizer.quantize(events, tempo_map)

    mapper = PitchToFretMapper()
    fret_notes = mapper.map_notes(q_notes)

    builder = ChordBuilder(max_frets=3)
    chord_notes = builder.build_chords(fret_notes)

    hopo_engine = HopoEngine(hopo_threshold=65)
    hopo_notes = hopo_engine.process(chord_notes)

    sustain_proc = SustainProcessor(min_sustain_ticks=90, release_margin=24)
    # Map durations from quantized notes
    dur_map = {qn.tick: qn.duration_ticks for qn in q_notes}
    final_notes = sustain_proc.process(hopo_notes, durations=dur_map)

    sp_gen = StarPowerGenerator(interval_measures=4, min_notes=2)
    sp_phrases = sp_gen.generate(final_notes)

    track = SongTrack(name="ExpertSingle", notes=final_notes, star_power=sp_phrases)

    assert track.name == "ExpertSingle"
    assert len(track.notes) > 0
    # First note is strum
    assert track.notes[0].is_hopo is False
    # Ascending run contains HOPOs
    fast_run_notes = [n for n in track.notes if 192 <= n.tick <= 336]
    assert any(n.is_hopo for n in fast_run_notes)
    # Final track is sorted
    assert track.notes == sorted(track.notes)
