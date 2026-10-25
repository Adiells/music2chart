"""Integration tests for end-to-end Music2ChartPipeline orchestrator."""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
import soundfile as sf

from config.settings import Settings
from dataset.chart_parser import ChartParser
from src.models import FretType, NoteEvent
from src.pipeline import Music2ChartPipeline
from src.serialization.ini_writer import IniWriter
from src.serialization.sng_packer import SngPacker


@pytest.fixture
def synthesized_audio_wav(tmp_path: Path) -> Path:
    """Generate a 3-second synthesized audio wave file (C major arpeggio pulse)."""
    sr = 22050
    duration = 3.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    # Simple sine wave 440 Hz with envelope
    waveform = (0.5 * np.sin(2 * np.pi * 440.0 * t)).astype(np.float32)

    audio_file = tmp_path / "test_synth.wav"
    sf.write(str(audio_file), waveform, sr)
    return audio_file


@pytest.fixture
def mock_transcribed_notes() -> list[NoteEvent]:
    """Sample NoteEvents simulating realistic polyphonic guitar transcription.

    Features:
    - Melodic fast run (<= 96 ticks / 1/8 note) with fret variation to trigger HOPO_FORCE (N 5 0)
    - Consecutive repeated pitch in fast passage to trigger STRUM_FORCE (N 6 0)
    - Polyphonic 4-note chord burst to verify playability clamping (zero 4-fret chord walls)
    - Sub-bass note (< 40 pitch) to verify open note suppression for lead guitar (mapped to Green 0, zero Open 7)
    - Near-simultaneous notes within 35ms to verify chord onset fusion
    """
    return [
        # 1. Melodic fast run at 120 BPM (1 beat = 0.5s = 192 ticks, 1/16 note = 0.125s = 48 ticks)
        NoteEvent(start_time=0.0, end_time=0.1, pitch=52, amplitude=0.95),  # Strum anchor (tick 0)
        NoteEvent(
            start_time=0.125, end_time=0.225, pitch=57, amplitude=0.90
        ),  # tick 48 -> HOPO_FORCE (N 5 0)
        NoteEvent(
            start_time=0.250, end_time=0.350, pitch=62, amplitude=0.90
        ),  # tick 96 -> HOPO_FORCE (N 5 0)
        # 2. Repeated pitch in rapid passage
        NoteEvent(
            start_time=0.375, end_time=0.475, pitch=62, amplitude=0.88
        ),  # tick 144 -> STRUM_FORCE (N 6 0)
        NoteEvent(
            start_time=0.500, end_time=0.600, pitch=67, amplitude=0.85
        ),  # tick 192 -> HOPO_FORCE (N 5 0)
        # 3. Polyphonic 4-note chord wall at 1.0s (all simultaneous onsets)
        NoteEvent(start_time=1.0, end_time=1.3, pitch=52, amplitude=0.90),
        NoteEvent(start_time=1.0, end_time=1.3, pitch=57, amplitude=0.85),
        NoteEvent(start_time=1.0, end_time=1.3, pitch=62, amplitude=0.85),
        NoteEvent(start_time=1.0, end_time=1.3, pitch=67, amplitude=0.80),
        # 4. Sub-bass note below open_threshold (pitch 32 < 40)
        NoteEvent(start_time=1.5, end_time=1.8, pitch=32, amplitude=0.85),
        # 5. Near-simultaneous acoustic string roll within 35ms (2.0s and 2.02s)
        NoteEvent(start_time=2.0, end_time=2.3, pitch=55, amplitude=0.90),
        NoteEvent(start_time=2.02, end_time=2.3, pitch=60, amplitude=0.85),
    ]


def test_pipeline_default_components_configuration():
    """Verify that default pipeline components enforce strict playability constraints."""
    pipeline = Music2ChartPipeline()

    # NoteQuantizer has chord fusion (35ms) and strict snapping active
    assert pipeline.quantizer.chord_fusion_window_s == pytest.approx(0.035)
    assert pipeline.quantizer.strict_snap is True
    assert pipeline.quantizer.min_spacing_ticks == 24

    # PitchToFretMapper disables open notes for Lead Guitar (ExpertSingle)
    assert pipeline.pitch_mapper.disable_open_notes is True

    # ChordBuilder enforces playability caps and fast-run collapsing
    assert pipeline.chord_builder.max_frets == 2
    assert pipeline.chord_builder.open_note_precedence is False
    assert pipeline.chord_builder.collapse_fast_runs is True
    assert pipeline.chord_builder.fast_run_tick_threshold == 48

    # HopoEngine thresholds
    assert pipeline.hopo_engine.hopo_threshold == 65
    assert pipeline.hopo_engine.run_threshold == 96


def test_pipeline_end_to_end(
    synthesized_audio_wav: Path,
    mock_transcribed_notes: list[NoteEvent],
    tmp_path: Path,
):
    """Verify that Music2ChartPipeline executes all 10 stages and outputs valid files with playability constraints."""
    test_settings = Settings(
        UPLOAD_DIR=tmp_path / "uploads",
        OUTPUT_DIR=tmp_path / "output",
        STEMS_DIR=tmp_path / "stems",
    )

    pipeline = Music2ChartPipeline(settings=test_settings)

    # Mock Basic Pitch inference to avoid heavy model downloads during CI/unit testing
    with patch.object(pipeline.transcriber, "transcribe", return_value=mock_transcribed_notes):
        progress_steps: list[tuple[float, str]] = []

        def callback(p: float, step: str) -> None:
            progress_steps.append((p, step))

        result = pipeline.process_song(
            audio_path=synthesized_audio_wav,
            song_name="Neon Knights",
            artist="Black Sabbath",
            output_format="both",
            output_dir=tmp_path / "output" / "Black Sabbath - Neon Knights",
            progress_callback=callback,
        )

    # 1. Verify all expected artifacts exist in output dictionary
    assert "chart" in result
    assert "ini" in result
    assert "audio" in result
    assert "sng" in result
    assert "package_dir" in result

    chart_path = result["chart"]
    ini_path = result["ini"]
    audio_path = result["audio"]
    sng_path = result["sng"]

    assert chart_path.exists()
    assert ini_path.exists()
    assert audio_path.exists()
    assert sng_path.exists()

    # 2. Verify progress callbacks occurred
    assert len(progress_steps) > 0
    assert progress_steps[-1][0] == 1.0

    # 3. Read chart text directly to verify HOPO/Strum modifier serialization
    chart_content = chart_path.read_text(encoding="utf-8")
    assert "[ExpertSingle]" in chart_content

    # Extract ExpertSingle section
    expert_section_match = re.search(r"\[ExpertSingle\]\s*\{([^}]+)\}", chart_content)
    assert expert_section_match is not None
    expert_section = expert_section_match.group(1)

    # Verify HOPO_FORCE (N 5 0) and STRUM_FORCE (N 6 0) are serialized
    assert re.search(r"\d+\s*=\s*N\s+5\s+0", expert_section), (
        "HOPO_FORCE modifier (N 5 0) must be present in chart"
    )
    assert re.search(r"\d+\s*=\s*N\s+6\s+0", expert_section), (
        "STRUM_FORCE modifier (N 6 0) must be present in chart"
    )

    # Verify lead guitar has ZERO random purple open notes (N 7 0)
    assert not re.search(r"\d+\s*=\s*N\s+7\s+", expert_section), (
        "Lead guitar must have zero Open notes (N 7)"
    )

    # 4. Verify .chart file structure with ChartParser
    parser = ChartParser()
    tempo_map, tracks, metadata = parser.parse_file(chart_path)
    assert metadata["Name"] == "Neon Knights"
    assert metadata["Artist"] == "Black Sabbath"
    assert "ExpertSingle" in tracks
    expert_track = tracks["ExpertSingle"]
    assert len(expert_track.notes) > 0

    # 5. Playability verification: zero invalid chord walls
    tick_groups: dict[int, list[FretType]] = defaultdict(list)
    for note in expert_track.notes:
        tick_groups[note.tick].append(note.fret)

    for tick, frets in tick_groups.items():
        # Playable frets (0 to 4)
        playable_frets = [f for f in frets if 0 <= f.value <= 4]
        # Max simultaneous notes clamped: never 4- or 5-fret chord walls
        assert len(playable_frets) <= 2 or (len(playable_frets) == 3 and tick % 96 == 0), (
            f"Invalid chord wall with {len(playable_frets)} notes at tick {tick}: {playable_frets}"
        )
        assert len(playable_frets) < 4, f"Strictly forbidden 4+ fret chord wall at tick {tick}"

        # No Open notes on Lead Guitar
        assert FretType.OPEN not in frets, (
            f"Forbidden Open note found on lead guitar at tick {tick}"
        )

        # Modifiers (5 and 6) must strictly have sustain 0
        for n in expert_track.notes_at_tick(tick):
            if n.fret in (FretType.HOPO_FORCE, FretType.STRUM_FORCE):
                assert n.sustain_length == 0, (
                    f"Modifier {n.fret} at tick {tick} must have sustain 0"
                )

        # Note snapping: tick must align with valid grid subdivisions (192, 96, 64, 48, 32, 24)
        assert any(tick % s == 0 for s in (192, 96, 64, 48, 32, 24)), (
            f"Tick {tick} is not snapped to musical subdivision grid"
        )

    # 6. Verify song.ini content with IniWriter
    ini_data = IniWriter.parse_file(ini_path)
    assert ini_data["name"] == "Neon Knights"
    assert ini_data["artist"] == "Black Sabbath"

    # 7. Verify .sng unpacking round-trip
    unpacked_dir = tmp_path / "unpacked_sng"
    SngPacker.unpack_dir(sng_path, unpacked_dir)
    assert (unpacked_dir / "notes.chart").exists()
    assert (unpacked_dir / "song.ini").exists()
    assert (unpacked_dir / "song.ogg").exists()


def test_pipeline_chord_wall_suppression_and_ergonomics(
    synthesized_audio_wav: Path,
    tmp_path: Path,
):
    """Verify that extreme polyphonic bursts (5 concurrent notes) are clamped to max 2 frets."""
    extreme_cluster_notes = [
        # Strum anchor
        NoteEvent(start_time=0.0, end_time=0.3, pitch=48, amplitude=0.9),
        # 5-note polyphonic burst at 1.0s
        NoteEvent(start_time=1.0, end_time=1.3, pitch=48, amplitude=0.9),  # C3
        NoteEvent(start_time=1.0, end_time=1.3, pitch=52, amplitude=0.9),  # E3
        NoteEvent(start_time=1.0, end_time=1.3, pitch=55, amplitude=0.9),  # G3
        NoteEvent(start_time=1.0, end_time=1.3, pitch=60, amplitude=0.9),  # C4
        NoteEvent(start_time=1.0, end_time=1.3, pitch=64, amplitude=0.9),  # E4
    ]

    pipeline = Music2ChartPipeline(
        settings=Settings(
            UPLOAD_DIR=tmp_path / "uploads",
            OUTPUT_DIR=tmp_path / "output",
            STEMS_DIR=tmp_path / "stems",
        )
    )

    with patch.object(pipeline.transcriber, "transcribe", return_value=extreme_cluster_notes):
        result = pipeline.process_song(
            audio_path=synthesized_audio_wav,
            song_name="Polyphonic Test",
            artist="Stress Tester",
            output_format="chart",
            output_dir=tmp_path / "output" / "Polyphonic Test",
        )

    parser = ChartParser()
    _, tracks, _ = parser.parse_file(result["chart"])
    expert_track = tracks["ExpertSingle"]

    # Identify the chord tick (> 0)
    distinct_ticks = sorted({n.tick for n in expert_track.notes if n.tick > 0})
    assert len(distinct_ticks) >= 1
    chord_tick = distinct_ticks[0]

    chord_notes = [n for n in expert_track.notes_at_tick(chord_tick) if 0 <= n.fret.value <= 4]
    # 5-note burst must be clamped to at most 2 frets (canonical power chord)
    assert 1 <= len(chord_notes) <= 2, f"Expected 1 or 2 frets, got {len(chord_notes)}"
    # No 4- or 5-fret chord walls allowed anywhere in the chart
    for t in {n.tick for n in expert_track.notes}:
        frets_at_t = [n.fret for n in expert_track.notes_at_tick(t) if 0 <= n.fret.value <= 4]
        assert len(frets_at_t) <= 2


def test_pipeline_fast_run_chord_collapsing(
    synthesized_audio_wav: Path,
    tmp_path: Path,
):
    """Verify that chords occurring during fast passages (spacing <= 48 ticks) collapse to single notes."""
    fast_run_chords = [
        # Note at 0.0s (tick 0)
        NoteEvent(start_time=0.0, end_time=0.1, pitch=50, amplitude=0.9),
        # Chord at 0.125s (tick 48, delta 48 <= 48 ticks threshold)
        NoteEvent(start_time=0.125, end_time=0.225, pitch=52, amplitude=0.9),
        NoteEvent(start_time=0.125, end_time=0.225, pitch=57, amplitude=0.85),
        # Note at 0.250s (tick 96)
        NoteEvent(start_time=0.250, end_time=0.350, pitch=60, amplitude=0.9),
    ]

    pipeline = Music2ChartPipeline(
        settings=Settings(
            UPLOAD_DIR=tmp_path / "uploads",
            OUTPUT_DIR=tmp_path / "output",
            STEMS_DIR=tmp_path / "stems",
        )
    )

    with patch.object(pipeline.transcriber, "transcribe", return_value=fast_run_chords):
        result = pipeline.process_song(
            audio_path=synthesized_audio_wav,
            song_name="Fast Run Test",
            artist="Speed Tester",
            output_format="chart",
            output_dir=tmp_path / "output" / "Fast Run Test",
        )

    parser = ChartParser()
    _, tracks, _ = parser.parse_file(result["chart"])
    expert_track = tracks["ExpertSingle"]

    # At tick 48, the simultaneous notes must collapse to a single dominant root note
    fretted_at_48 = [n for n in expert_track.notes_at_tick(48) if 0 <= n.fret.value <= 4]
    assert len(fretted_at_48) == 1, (
        f"Expected fast run chord to collapse to 1 note, got {len(fretted_at_48)}"
    )


def test_pipeline_custom_fitting_parameters(
    synthesized_audio_wav: Path,
    tmp_path: Path,
):
    """Verify that process_song overrides (max_frets=1, disable_open_notes=False, etc.) take effect."""
    test_notes = [
        # Note at 0.0s (tick 0)
        NoteEvent(start_time=0.0, end_time=0.2, pitch=52, amplitude=0.9),
        # Chord at 1.0s (two simultaneous notes)
        NoteEvent(start_time=1.0, end_time=1.3, pitch=52, amplitude=0.9),
        NoteEvent(start_time=1.0, end_time=1.3, pitch=57, amplitude=0.85),
        # Sub-bass note below open threshold (pitch 32 < 40)
        NoteEvent(start_time=1.5, end_time=1.8, pitch=32, amplitude=0.9),
    ]

    pipeline = Music2ChartPipeline(
        settings=Settings(
            UPLOAD_DIR=tmp_path / "uploads",
            OUTPUT_DIR=tmp_path / "output",
            STEMS_DIR=tmp_path / "stems",
        )
    )

    with patch.object(pipeline.transcriber, "transcribe", return_value=test_notes):
        result = pipeline.process_song(
            audio_path=synthesized_audio_wav,
            song_name="Custom Fit",
            artist="Fit Artist",
            output_format="both",
            output_dir=tmp_path / "output" / "Custom Fit",
            max_frets=1,
            disable_open_notes=False,  # Allow open notes
            difficulty=5,
            genre="metal",
        )

    parser = ChartParser()
    _, tracks, metadata = parser.parse_file(result["chart"])
    expert_track = tracks["ExpertSingle"]

    # 1. max_frets=1: every tick has at most 1 fretted note
    tick_frets: dict[int, list[int]] = defaultdict(list)
    for n in expert_track.notes:
        if 0 <= n.fret.value <= 4:
            tick_frets[n.tick].append(n.fret.value)
    for t, frets in tick_frets.items():
        assert len(frets) <= 1, f"Expected max 1 fret at tick {t}, got {frets}"

    # 2. disable_open_notes=False: Open note is present
    open_notes = [n for n in expert_track.notes if n.fret == FretType.OPEN]
    assert len(open_notes) >= 1, "Expected Open notes when disable_open_notes=False"

    # 3. Check difficulty and genre in song.ini
    ini_data = IniWriter.parse_file(result["ini"])
    assert ini_data["diff_guitar"] == "5"
    assert ini_data["genre"] == "metal"

    # 4. Check difficulty and genre in notes.chart metadata
    assert metadata.get("Difficulty") == "5"
    assert metadata.get("Genre") == "metal"


def test_pipeline_preset_strict_rhythm(
    synthesized_audio_wav: Path,
    tmp_path: Path,
):
    """Verify that preset='strict_rhythm' applies strict rhythm parameters."""
    test_notes = [
        # Ghost note with amplitude 0.15 (below strict_rhythm min_amplitude 0.20)
        NoteEvent(start_time=0.0, end_time=0.1, pitch=52, amplitude=0.15),
        # Real note with amplitude 0.85
        NoteEvent(start_time=0.5, end_time=0.7, pitch=52, amplitude=0.85),
    ]

    pipeline = Music2ChartPipeline(
        settings=Settings(
            UPLOAD_DIR=tmp_path / "uploads",
            OUTPUT_DIR=tmp_path / "output",
            STEMS_DIR=tmp_path / "stems",
        )
    )

    with patch.object(pipeline.transcriber, "transcribe", return_value=test_notes):
        result = pipeline.process_song(
            audio_path=synthesized_audio_wav,
            song_name="Strict Rhythm Test",
            artist="Rhythm Master",
            output_format="chart",
            output_dir=tmp_path / "output" / "Strict Rhythm Test",
            preset="strict_rhythm",
        )

    parser = ChartParser()
    _, tracks, _ = parser.parse_file(result["chart"])
    expert_track = tracks["ExpertSingle"]

    # Ghost note at tick 0 (amplitude 0.15) should be filtered out by strict_rhythm min_amplitude 0.20
    assert not any(n.tick == 0 for n in expert_track.notes)
    # Note at 0.5s should be present
    assert any(n.tick > 0 for n in expert_track.notes)


def test_pipeline_preset_dynamic_solo_preserves_fast_chords(
    synthesized_audio_wav: Path,
    tmp_path: Path,
):
    """Verify that preset='dynamic_solo' disables collapse_fast_runs so chords in fast runs are kept."""
    fast_run_chords = [
        NoteEvent(start_time=0.0, end_time=0.1, pitch=50, amplitude=0.9),
        # Chord in fast passage (delta <= 48 ticks)
        NoteEvent(start_time=0.125, end_time=0.225, pitch=52, amplitude=0.9),
        NoteEvent(start_time=0.125, end_time=0.225, pitch=57, amplitude=0.85),
    ]

    pipeline = Music2ChartPipeline(
        settings=Settings(
            UPLOAD_DIR=tmp_path / "uploads",
            OUTPUT_DIR=tmp_path / "output",
            STEMS_DIR=tmp_path / "stems",
        )
    )

    with patch.object(pipeline.transcriber, "transcribe", return_value=fast_run_chords):
        result = pipeline.process_song(
            audio_path=synthesized_audio_wav,
            song_name="Dynamic Solo Test",
            artist="Solo Shredder",
            output_format="chart",
            output_dir=tmp_path / "output" / "Dynamic Solo Test",
            preset="dynamic_solo",
        )

    parser = ChartParser()
    _, tracks, _ = parser.parse_file(result["chart"])
    expert_track = tracks["ExpertSingle"]

    # In dynamic_solo, collapse_fast_runs is False, so the 2-note chord at the fast tick is preserved (2 frets)
    distinct_ticks = sorted({n.tick for n in expert_track.notes if n.tick > 0})
    assert len(distinct_ticks) >= 1
    fast_tick = distinct_ticks[0]
    frets_at_fast_tick = [
        n for n in expert_track.notes_at_tick(fast_tick) if 0 <= n.fret.value <= 4
    ]
    assert len(frets_at_fast_tick) == 2, (
        f"Expected 2 frets in dynamic_solo, got {len(frets_at_fast_tick)}"
    )


def test_pipeline_preset_override_parameter(
    synthesized_audio_wav: Path,
    tmp_path: Path,
):
    """Verify that explicit arguments override preset configuration values."""
    fast_run_chords = [
        NoteEvent(start_time=0.0, end_time=0.1, pitch=50, amplitude=0.9),
        # Chord in fast passage
        NoteEvent(start_time=0.125, end_time=0.225, pitch=52, amplitude=0.9),
        NoteEvent(start_time=0.125, end_time=0.225, pitch=57, amplitude=0.85),
    ]

    pipeline = Music2ChartPipeline(
        settings=Settings(
            UPLOAD_DIR=tmp_path / "uploads",
            OUTPUT_DIR=tmp_path / "output",
            STEMS_DIR=tmp_path / "stems",
        )
    )

    # In dynamic_solo, collapse_fast_runs is False by default, but we explicitly pass collapse_fast_runs=True
    with patch.object(pipeline.transcriber, "transcribe", return_value=fast_run_chords):
        result = pipeline.process_song(
            audio_path=synthesized_audio_wav,
            song_name="Override Test",
            artist="Overrider",
            output_format="chart",
            output_dir=tmp_path / "output" / "Override Test",
            preset="dynamic_solo",
            collapse_fast_runs=True,  # Explicit override
        )

    parser = ChartParser()
    _, tracks, _ = parser.parse_file(result["chart"])
    expert_track = tracks["ExpertSingle"]

    distinct_ticks = sorted({n.tick for n in expert_track.notes if n.tick > 0})
    assert len(distinct_ticks) >= 1
    fast_tick = distinct_ticks[0]
    frets_at_fast_tick = [
        n for n in expert_track.notes_at_tick(fast_tick) if 0 <= n.fret.value <= 4
    ]
    assert len(frets_at_fast_tick) == 1, (
        f"Expected override collapse_fast_runs=True to collapse to 1 note, got {len(frets_at_fast_tick)}"
    )


def test_pipeline_preset_the_best(
    synthesized_audio_wav: Path,
    tmp_path: Path,
):
    """Verify that preset='the_best' applies strict rhythm heuristics with noise gate 0.41 and bpm_scale 0.65."""
    test_notes = [
        # Note with amplitude 0.35 (below the_best min_amplitude 0.41)
        NoteEvent(start_time=0.0, end_time=0.1, pitch=52, amplitude=0.35),
        # Real note with amplitude 0.85
        NoteEvent(start_time=0.5, end_time=0.7, pitch=52, amplitude=0.85),
    ]

    pipeline = Music2ChartPipeline(
        settings=Settings(
            UPLOAD_DIR=tmp_path / "uploads",
            OUTPUT_DIR=tmp_path / "output",
            STEMS_DIR=tmp_path / "stems",
        )
    )

    with patch.object(pipeline.transcriber, "transcribe", return_value=test_notes):
        result = pipeline.process_song(
            audio_path=synthesized_audio_wav,
            song_name="The Best Preset Test",
            artist="Developer",
            output_format="chart",
            output_dir=tmp_path / "output" / "The Best Preset Test",
            preset="the_best",
        )

    parser = ChartParser()
    tempo_map, tracks, _ = parser.parse_file(result["chart"])
    expert_track = tracks["ExpertSingle"]

    # Note at tick 0 (amplitude 0.35) should be filtered out by the_best min_amplitude 0.41
    assert not any(n.tick == 0 for n in expert_track.notes)
    # Note at 0.5s should be present
    assert any(n.tick > 0 for n in expert_track.notes)
    # Verify tempo map has bpm changes
    assert len(tempo_map.bpm_changes) >= 1
