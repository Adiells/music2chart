"""Comprehensive unit tests for SustainProcessor and StarPowerGenerator.

Covers:
- Sustain cutoff (< 90 ticks -> 0)
- Sustain margin calculation (duration - 24 ticks)
- Next-note collision clamping (t_next - t_curr - 24 ticks)
- Final note duration preservation
- Chords and simultaneous notes handling
- Explicit duration mappings and sequences
- Star Power periodic phrase allocation
- Star Power active note region alignment
- Star Power silence gap handling and empty/short chart grace
"""

from __future__ import annotations

import pytest

from src.game_design.star_power_generator import StarPowerGenerator
from src.game_design.sustain_processor import SustainProcessor
from src.models import ChartNote, FretType

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
def default_sustain_processor() -> SustainProcessor:
    """Return a standard SustainProcessor with 90-tick cutoff and 24-tick margin."""
    return SustainProcessor(min_sustain_ticks=90, release_margin=24)


@pytest.fixture
def default_sp_generator() -> StarPowerGenerator:
    """Return a standard StarPowerGenerator configured for 16-measure intervals."""
    return StarPowerGenerator(
        measure_ticks=768,
        interval_measures=16,
        phrase_length_measures=2,
        min_notes=4,
    )


# ---------------------------------------------------------------------------
# 1. SustainProcessor Tests
# ---------------------------------------------------------------------------


class TestSustainProcessor:
    """Test suite for SustainProcessor mechanics."""

    def test_sustain_empty_notes(self, default_sustain_processor: SustainProcessor) -> None:
        """Verify empty input returns empty list."""
        assert default_sustain_processor.process([]) == []

    @pytest.mark.parametrize("duration", [0, 24, 48, 89])
    def test_sustain_below_90_cutoff_zero(
        self, default_sustain_processor: SustainProcessor, duration: int
    ) -> None:
        """Verify durations < 90 ticks produce sustain_length = 0."""
        notes = [_make_note(tick=0, fret=FretType.GREEN, sustain_length=duration)]
        result = default_sustain_processor.process(notes)
        assert result[0].sustain_length == 0

    def test_sustain_exact_threshold_90(self, default_sustain_processor: SustainProcessor) -> None:
        """Verify duration of exactly 90 ticks produces sustain_length = 90 - 24 = 66."""
        notes = [_make_note(tick=0, fret=FretType.GREEN, sustain_length=90)]
        result = default_sustain_processor.process(notes)
        assert result[0].sustain_length == 66

    def test_sustain_quarter_note_192(self, default_sustain_processor: SustainProcessor) -> None:
        """Verify quarter note (192 ticks) produces sustain_length = 192 - 24 = 168."""
        notes = [_make_note(tick=0, fret=FretType.GREEN, sustain_length=192)]
        result = default_sustain_processor.process(notes)
        assert result[0].sustain_length == 168

    def test_sustain_half_note_384(self, default_sustain_processor: SustainProcessor) -> None:
        """Verify half note (384 ticks) produces sustain_length = 384 - 24 = 360."""
        notes = [_make_note(tick=0, fret=FretType.GREEN, sustain_length=384)]
        result = default_sustain_processor.process(notes)
        assert result[0].sustain_length == 360

    def test_sustain_next_note_overlap_clamping(
        self, default_sustain_processor: SustainProcessor
    ) -> None:
        """Verify long note (500 ticks) followed by next note at +192 ticks clamps to 192 - 24 = 168."""
        notes = [
            _make_note(tick=0, fret=FretType.GREEN, sustain_length=500),
            _make_note(tick=192, fret=FretType.RED, sustain_length=0),
        ]
        result = default_sustain_processor.process(notes)
        assert result[0].sustain_length == 168  # 192 - 24
        assert result[1].sustain_length == 0

    def test_sustain_consecutive_rapid_notes_48_spacing(
        self, default_sustain_processor: SustainProcessor
    ) -> None:
        """Verify consecutive notes with 48-tick spacing and long durations clamp to 48 - 24 = 24."""
        notes = [
            _make_note(tick=0, fret=FretType.GREEN, sustain_length=192),
            _make_note(tick=48, fret=FretType.RED, sustain_length=192),
            _make_note(tick=96, fret=FretType.YELLOW, sustain_length=0),
        ]
        result = default_sustain_processor.process(notes)
        assert result[0].sustain_length == 24  # 48 - 24
        assert result[1].sustain_length == 24  # (96 - 48) - 24
        assert result[2].sustain_length == 0

    def test_sustain_final_note_retains_full_duration(
        self, default_sustain_processor: SustainProcessor
    ) -> None:
        """Verify final note of track retains full duration - 24 without collision clamping."""
        notes = [
            _make_note(tick=0, fret=FretType.GREEN, sustain_length=192),
            _make_note(tick=384, fret=FretType.RED, sustain_length=500),
        ]
        result = default_sustain_processor.process(notes)
        assert result[0].sustain_length == 168  # 192 - 24 (next note is at 384, no clamp needed)
        assert result[1].sustain_length == 476  # 500 - 24 (final note, retains full duration)

    def test_sustain_tight_spacing_below_margin_24(
        self, default_sustain_processor: SustainProcessor
    ) -> None:
        """Verify note followed by next note within <= 24 ticks clamps sustain to 0."""
        notes = [
            _make_note(tick=0, fret=FretType.GREEN, sustain_length=192),
            _make_note(tick=16, fret=FretType.RED, sustain_length=0),
        ]
        result = default_sustain_processor.process(notes)
        assert result[0].sustain_length == 0  # 16 - 24 <= 0 -> 0

    def test_sustain_exact_spacing_margin_24(
        self, default_sustain_processor: SustainProcessor
    ) -> None:
        """Verify note followed by next note at exactly +24 ticks clamps sustain to 0."""
        notes = [
            _make_note(tick=0, fret=FretType.GREEN, sustain_length=192),
            _make_note(tick=24, fret=FretType.RED, sustain_length=0),
        ]
        result = default_sustain_processor.process(notes)
        assert result[0].sustain_length == 0  # 24 - 24 = 0

    def test_sustain_chords_simultaneous_notes(
        self, default_sustain_processor: SustainProcessor
    ) -> None:
        """Verify notes in the same chord (identical tick) do not clamp each other."""
        notes = [
            _make_note(tick=0, fret=FretType.GREEN, sustain_length=192),
            _make_note(tick=0, fret=FretType.RED, sustain_length=192),
            _make_note(tick=384, fret=FretType.YELLOW, sustain_length=0),
        ]
        result = default_sustain_processor.process(notes)
        assert result[0].sustain_length == 168
        assert result[1].sustain_length == 168

    def test_sustain_explicit_duration_mapping(
        self, default_sustain_processor: SustainProcessor
    ) -> None:
        """Verify durations passed as explicit mapping or sequence are properly used."""
        notes = [
            _make_note(tick=0, fret=FretType.GREEN, sustain_length=0),
            _make_note(tick=384, fret=FretType.RED, sustain_length=0),
        ]
        durations = [192, 90]
        result = default_sustain_processor.process(notes, durations=durations)
        assert result[0].sustain_length == 168
        assert result[1].sustain_length == 66

    def test_sustain_preserves_is_hopo_and_fret(
        self, default_sustain_processor: SustainProcessor
    ) -> None:
        """Verify SustainProcessor preserves is_hopo and fret attributes unchanged."""
        notes = [
            _make_note(tick=0, fret=FretType.GREEN, sustain_length=192, is_hopo=False),
            _make_note(tick=192, fret=FretType.RED, sustain_length=192, is_hopo=True),
        ]
        result = default_sustain_processor.process(notes)
        assert result[0].is_hopo is False
        assert result[1].is_hopo is True
        assert result[0].fret == FretType.GREEN
        assert result[1].fret == FretType.RED

    def test_sustain_custom_parameters(self) -> None:
        """Verify custom min_sustain_ticks and release_margin are applied."""
        processor = SustainProcessor(min_sustain_ticks=120, release_margin=30)
        notes = [
            _make_note(tick=0, fret=FretType.GREEN, sustain_length=100),  # < 120 -> 0
            _make_note(tick=384, fret=FretType.RED, sustain_length=150),  # >= 120 -> 150 - 30 = 120
        ]
        result = processor.process(notes)
        assert result[0].sustain_length == 0
        assert result[1].sustain_length == 120

    def test_sustain_invalid_parameters_raises(self) -> None:
        """Verify negative parameter values raise ValueError."""
        with pytest.raises(ValueError):
            SustainProcessor(min_sustain_ticks=-1)
        with pytest.raises(ValueError):
            SustainProcessor(release_margin=-1)


# ---------------------------------------------------------------------------
# 2. StarPowerGenerator Tests
# ---------------------------------------------------------------------------


class TestStarPowerGenerator:
    """Test suite for StarPowerGenerator mechanics."""

    def test_star_power_empty_notes(self, default_sp_generator: StarPowerGenerator) -> None:
        """Verify empty input notes returns empty star power phrase list."""
        assert default_sp_generator.generate([]) == []

    def test_star_power_single_short_note(self, default_sp_generator: StarPowerGenerator) -> None:
        """Verify single short note returns empty phrases (insufficient note density)."""
        notes = [_make_note(tick=0, fret=FretType.GREEN)]
        assert default_sp_generator.generate(notes) == []

    def test_star_power_sparse_few_notes(self, default_sp_generator: StarPowerGenerator) -> None:
        """Verify track with fewer than min_notes (4) produces no star power phrases."""
        notes = [
            _make_note(tick=0, fret=FretType.GREEN),
            _make_note(tick=192, fret=FretType.RED),
            _make_note(tick=384, fret=FretType.YELLOW),
        ]
        assert default_sp_generator.generate(notes) == []

    def test_star_power_long_song_64_measures_periodic(
        self, default_sp_generator: StarPowerGenerator
    ) -> None:
        """Verify long song (64 measures = 49,152 ticks) generates periodic phrases (~3-4 phrases)."""
        notes: list[ChartNote] = []
        for measure in range(64):
            for beat in range(4):
                tick = measure * 768 + beat * 192
                fret = (measure + beat) % 5
                notes.append(_make_note(tick=tick, fret=fret))

        phrases = default_sp_generator.generate(notes)
        assert len(phrases) >= 3
        assert len(phrases) <= 5

        # Verify phrases are chronologically sorted and non-overlapping
        for i in range(len(phrases) - 1):
            assert phrases[i].tick < phrases[i + 1].tick
            assert phrases[i].tick + phrases[i].length <= phrases[i + 1].tick

    def test_star_power_phrases_within_active_note_regions(
        self, default_sp_generator: StarPowerGenerator
    ) -> None:
        """Verify every StarPowerPhrase encompasses active notes."""
        notes: list[ChartNote] = []
        for measure in range(32):
            for beat in range(4):
                tick = measure * 768 + beat * 192
                notes.append(_make_note(tick=tick, fret=beat % 5))

        phrases = default_sp_generator.generate(notes)
        assert len(phrases) >= 1

        for phrase in phrases:
            # Must encompass notes
            notes_in_phrase = [
                n for n in notes if phrase.tick <= n.tick < phrase.tick + phrase.length
            ]
            assert len(notes_in_phrase) >= default_sp_generator.min_notes

    def test_star_power_silence_gap_no_phrase(
        self, default_sp_generator: StarPowerGenerator
    ) -> None:
        """Verify 16-measure silent gap contains no Star Power phrase."""
        notes: list[ChartNote] = []
        # Measures 0-15: active notes
        for measure in range(16):
            for beat in range(4):
                notes.append(_make_note(tick=measure * 768 + beat * 192, fret=0))
        # Measures 16-31: SILENCE (no notes)
        # Measures 32-47: active notes
        for measure in range(32, 48):
            for beat in range(4):
                notes.append(_make_note(tick=measure * 768 + beat * 192, fret=1))

        phrases = default_sp_generator.generate(notes)
        # Verify no phrase starts or exists within silent gap [16 * 768, 32 * 768)
        gap_start = 16 * 768
        gap_end = 32 * 768
        for p in phrases:
            assert not (gap_start <= p.tick < gap_end)

    def test_star_power_phrase_non_negative_values(
        self, default_sp_generator: StarPowerGenerator
    ) -> None:
        """Verify all generated StarPowerPhrases have non-negative tick and positive length."""
        notes = [_make_note(tick=m * 192, fret=0) for m in range(40)]
        phrases = default_sp_generator.generate(notes)
        for phrase in phrases:
            assert phrase.tick >= 0
            assert phrase.length > 0

    def test_star_power_custom_interval(self) -> None:
        """Verify custom interval_measures generates phrases more frequently."""
        gen_dense = StarPowerGenerator(interval_measures=8, min_notes=2)
        gen_sparse = StarPowerGenerator(interval_measures=16, min_notes=2)

        notes = [_make_note(tick=m * 192, fret=0) for m in range(128)]
        phrases_dense = gen_dense.generate(notes)
        phrases_sparse = gen_sparse.generate(notes)

        assert len(phrases_dense) > len(phrases_sparse)

    def test_star_power_invalid_parameters_raises(self) -> None:
        """Verify non-positive parameters raise ValueError."""
        with pytest.raises(ValueError):
            StarPowerGenerator(measure_ticks=0)
        with pytest.raises(ValueError):
            StarPowerGenerator(interval_measures=0)
        with pytest.raises(ValueError):
            StarPowerGenerator(phrase_length_measures=0)
        with pytest.raises(ValueError):
            StarPowerGenerator(min_notes=0)


# ---------------------------------------------------------------------------
# Legacy Tests (preservation)
# ---------------------------------------------------------------------------


def test_short_notes_have_zero_sustain() -> None:
    """Validate that notes shorter than 90 ticks have sustain_length = 0."""
    processor = SustainProcessor(min_sustain_ticks=90, release_margin_ticks=24)

    assert processor.calculate_sustain_length(48) == 0
    assert processor.calculate_sustain_length(89) == 0


def test_isolated_sustained_note() -> None:
    """Validate that sustained notes subtract 24 ticks release margin."""
    processor = SustainProcessor(min_sustain_ticks=90, release_margin_ticks=24)

    assert processor.calculate_sustain_length(192) == 168
    assert processor.calculate_sustain_length(384) == 360


def test_sustain_truncated_before_subsequent_note() -> None:
    """Validate that a sustained note cannot overlap the following note tail."""
    processor = SustainProcessor(min_sustain_ticks=90, release_margin_ticks=24)

    sustain = processor.calculate_sustain_length(duration_ticks=384, next_note_distance=192)
    assert sustain == 168


def test_process_notes_collection() -> None:
    """Validate sustain calculation across a list of ChartNotes."""
    notes = [
        ChartNote(tick=0, fret=FretType.GREEN, sustain_length=384),
        ChartNote(tick=192, fret=FretType.RED, sustain_length=48),
        ChartNote(tick=384, fret=FretType.YELLOW, sustain_length=192),
    ]

    processor = SustainProcessor()
    processed = processor.process_notes(notes)

    assert processed[0].sustain_length == 168
    assert processed[1].sustain_length == 0
    assert processed[2].sustain_length == 168


def test_star_power_generator_cadence() -> None:
    """Validate that Star Power phrases are distributed periodically across measures."""
    notes = [ChartNote(tick=t, fret=FretType.GREEN) for t in range(0, 36 * 768, 48)]

    generator = StarPowerGenerator(
        ticks_per_measure=768,
        phrase_interval_measures=16,
        phrase_duration_measures=2,
    )
    phrases = generator.generate_star_power(notes)

    assert len(phrases) >= 2
    for sp in phrases:
        assert sp.length == 768 * 2

    for i in range(len(phrases) - 1):
        assert phrases[i].tick + phrases[i].length < phrases[i + 1].tick


# ---------------------------------------------------------------------------
# 3. New Sustain Features Tests (Lookup, Max Clamp, Configurable Thresholds)
# ---------------------------------------------------------------------------


def test_sustain_lookup_by_tick() -> None:
    """Verify durations mapping lookup by integer tick."""
    processor = SustainProcessor(min_sustain_ticks=90, release_margin=24)
    notes = [
        _make_note(tick=0, fret=FretType.GREEN, sustain_length=0),
        _make_note(tick=384, fret=FretType.RED, sustain_length=0),
    ]
    durations = {0: 192, 384: 90}
    result = processor.process(notes, durations=durations)
    assert result[0].sustain_length == 168
    assert result[1].sustain_length == 66


def test_sustain_lookup_by_tick_and_fret() -> None:
    """Verify durations mapping lookup by (tick, fret_val) tuple."""
    processor = SustainProcessor(min_sustain_ticks=90, release_margin=24)
    notes = [
        _make_note(tick=0, fret=FretType.GREEN, sustain_length=0),
        _make_note(tick=0, fret=FretType.RED, sustain_length=0),
    ]
    durations = {(0, 0): 192, (0, 1): 120}
    result = processor.process(notes, durations=durations)
    assert result[0].sustain_length == 168
    assert result[1].sustain_length == 96


def test_sustain_lookup_defaults_to_note_sustain_length() -> None:
    """Verify missing keys in durations mapping fall back to note.sustain_length."""
    processor = SustainProcessor(min_sustain_ticks=90, release_margin=24)
    notes = [
        _make_note(tick=0, fret=FretType.GREEN, sustain_length=192),
        _make_note(tick=384, fret=FretType.RED, sustain_length=120),
    ]
    # Empty mapping or missing keys
    durations = {999: 500}
    result = processor.process(notes, durations=durations)
    assert result[0].sustain_length == 168  # 192 - 24
    assert result[1].sustain_length == 96  # 120 - 24


def test_max_sustain_ticks_clamping() -> None:
    """Verify max_sustain_ticks clamps very long sustain durations."""
    processor = SustainProcessor(min_sustain_ticks=90, release_margin=24, max_sustain_ticks=100)
    notes = [
        _make_note(tick=0, fret=FretType.GREEN, sustain_length=384),
        _make_note(tick=1000, fret=FretType.RED, sustain_length=110),
    ]
    result = processor.process(notes)
    # Note 0: 384 - 24 = 360, clamped by max_sustain_ticks=100 -> 100
    assert result[0].sustain_length == 100
    # Note 1: 110 - 24 = 86 <= 100 -> 86
    assert result[1].sustain_length == 86


def test_max_sustain_ticks_negative_raises() -> None:
    """Verify negative max_sustain_ticks raises ValueError."""
    with pytest.raises(ValueError, match="max_sustain_ticks"):
        SustainProcessor(max_sustain_ticks=-1)


def test_configurable_min_sustain_and_release_margin() -> None:
    """Verify configurable min_sustain_ticks (e.g. 72) and release_margin (24)."""
    processor = SustainProcessor(min_sustain_ticks=72, release_margin=24)
    notes = [
        _make_note(tick=0, fret=FretType.GREEN, sustain_length=70),  # < 72 -> 0
        _make_note(tick=200, fret=FretType.RED, sustain_length=72),  # >= 72 -> 72 - 24 = 48
    ]
    result = processor.process(notes)
    assert result[0].sustain_length == 0
    assert result[1].sustain_length == 48
