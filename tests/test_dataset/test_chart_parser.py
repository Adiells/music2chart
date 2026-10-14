"""Unit tests for Clone Hero .chart parser."""

from pathlib import Path

from dataset.chart_parser import ChartParser
from src.models import FretType


def test_parse_realistic_chart_metadata(realistic_chart_content: str) -> None:
    """Validate parsing of [Song] section metadata."""
    parser = ChartParser()
    tempo_map, tracks, metadata = parser.parse_text(realistic_chart_content)

    assert metadata["Name"] == "Test Anthem"
    assert metadata["Artist"] == "Synthetics"
    assert metadata["Charter"] == "music2chart AI"
    assert tempo_map.resolution == 192


def test_parse_sync_track(realistic_chart_content: str) -> None:
    """Validate extraction of BPM changes and time signature."""
    parser = ChartParser()
    tempo_map, _, _ = parser.parse_text(realistic_chart_content)

    assert len(tempo_map.bpm_changes) == 2
    assert tempo_map.bpm_changes[0].tick == 0
    assert tempo_map.bpm_changes[0].bpm == 120.0
    assert tempo_map.bpm_changes[1].tick == 768
    assert tempo_map.bpm_changes[1].bpm == 140.0

    assert len(tempo_map.time_signatures) >= 1
    assert tempo_map.time_signatures[0].numerator == 4
    assert tempo_map.time_signatures[0].denominator == 4


def test_parse_expert_single_notes_and_star_power(realistic_chart_content: str) -> None:
    """Validate note counts, open notes, chords, sustains, and Star Power."""
    parser = ChartParser()
    _, tracks, _ = parser.parse_text(realistic_chart_content)

    assert "ExpertSingle" in tracks
    track = tracks["ExpertSingle"]

    # Total notes in the fixture: 0(OPEN), 96(GREEN), 192(RED), 384(GREEN), 384(YELLOW), 768(BLUE), 864(ORANGE) = 7 notes
    assert len(track.notes) == 7

    # Open note at tick 0
    notes_at_0 = track.notes_at_tick(0)
    assert len(notes_at_0) == 1
    assert notes_at_0[0].fret == FretType.OPEN
    assert notes_at_0[0].sustain_length == 0

    # Note with sustain at tick 192
    notes_at_192 = track.notes_at_tick(192)
    assert len(notes_at_192) == 1
    assert notes_at_192[0].fret == FretType.RED
    assert notes_at_192[0].sustain_length == 96

    # Chord at tick 384 (Green + Yellow)
    chord_notes = track.notes_at_tick(384)
    assert len(chord_notes) == 2
    frets = [n.fret for n in chord_notes]
    assert FretType.GREEN in frets
    assert FretType.YELLOW in frets

    # Star Power phrase
    assert len(track.star_power) == 1
    assert track.star_power[0].tick == 384
    assert track.star_power[0].length == 384

    # High note at tick 864
    notes_at_864 = track.notes_at_tick(864)
    assert len(notes_at_864) == 1
    assert notes_at_864[0].fret == FretType.ORANGE
    assert notes_at_864[0].sustain_length == 48


def test_to_chart_notes_method() -> None:
    """Validate direct conversion of raw lines into ChartNotes."""
    parser = ChartParser()
    raw_lines = [
        "  192 = N 0 48 // green with sustain",
        "  192 = N 2 48 // yellow with sustain",
        "  288 = N 7 0  // open note",
        "  invalid line",
    ]
    notes = parser.to_chart_notes(raw_lines)
    assert len(notes) == 3
    assert notes[0].tick == 192
    assert notes[0].fret == FretType.GREEN
    assert notes[0].sustain_length == 48
    assert notes[1].tick == 192
    assert notes[1].fret == FretType.YELLOW
    assert notes[2].tick == 288
    assert notes[2].fret == FretType.OPEN


def test_parse_file_from_filesystem(realistic_chart_content: str, tmp_path: Path) -> None:
    """Validate reading directly from a .chart file on disk."""
    chart_path = tmp_path / "notes.chart"
    chart_path.write_text(realistic_chart_content, encoding="utf-8")

    parser = ChartParser()
    tempo_map, tracks, metadata = parser.parse_file(chart_path)

    assert metadata["Name"] == "Test Anthem"
    assert len(tracks["ExpertSingle"].notes) == 7
    assert len(tempo_map.bpm_changes) == 2
