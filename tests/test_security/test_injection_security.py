"""Tests for metadata injection prevention in .chart and song.ini serializers."""

from __future__ import annotations

from src.models import (
    BPMChange,
    ChartNote,
    FretType,
    SongTrack,
    TempoMap,
    TimeSignature,
)
from src.serialization.chart_writer import ChartWriter
from src.serialization.ini_writer import IniWriter
from src.utils.security import sanitize_ini_key, sanitize_ini_value, sanitize_string


def create_minimal_tempo_map() -> TempoMap:
    return TempoMap(
        resolution=192,
        bpm_changes=[BPMChange(tick=0, bpm=120.0)],
        time_signatures=[TimeSignature(tick=0, numerator=4, denominator=4)],
    )


def test_chart_writer_prevents_section_injection():
    """Verify that malicious newlines and section closers do not inject new sections into .chart."""
    malicious_song_name = 'Legit Title"\n}\n[InjectedSection]\n{\n  InjectedKey = "pwned"'
    malicious_artist = 'Legit Artist"\n  Evil = "injection"'

    tempo_map = create_minimal_tempo_map()
    tracks = {
        "ExpertSingle": SongTrack(
            name="ExpertSingle",
            notes=[ChartNote(tick=0, fret=FretType.GREEN, sustain_length=0)],
            star_power=[],
        )
    }

    chart_content = ChartWriter.generate_chart_string(
        song_name=malicious_song_name,
        artist=malicious_artist,
        tempo_map=tempo_map,
        tracks=tracks,
    )

    # Verify that [InjectedSection] was NOT created as a standalone section header
    assert "\n[InjectedSection]\n" not in chart_content
    assert not any(line.strip() == "[InjectedSection]" for line in chart_content.splitlines())
    assert "\n  InjectedKey" not in chart_content
    assert '\n  Evil = "injection"' not in chart_content


def test_chart_writer_sanitizes_events_and_extra_properties():
    """Verify that practice section event names and extra song properties are sanitized."""
    malicious_event = 'section Solo"\n  0 = E "injected'
    malicious_prop = 'value"\n}\n[Bad]'

    tempo_map = create_minimal_tempo_map()
    tracks = {"ExpertSingle": SongTrack(name="ExpertSingle", notes=[], star_power=[])}

    chart_content = ChartWriter.generate_chart_string(
        song_name="Song",
        artist="Artist",
        tempo_map=tempo_map,
        tracks=tracks,
        events=[(0, malicious_event)],
        extra_song_properties={"custom_prop": malicious_prop},
    )

    assert "\n[Bad]\n" not in chart_content
    assert '\n  0 = E "injected' not in chart_content


def test_ini_writer_prevents_section_and_property_injection():
    """Verify that song.ini serializer sanitizes newlines to prevent rogue section injection."""
    malicious_meta = {
        "name": "Standard Song\n[InjectedSection]\ninjected_key = evil_value",
        "artist": "Safe Artist\nother_key = injected",
        "bad:key=name\n": "normal_value",
    }

    ini_content = IniWriter.generate_string(malicious_meta)

    # Verify that [InjectedSection] is NOT a standalone section
    assert "\n[InjectedSection]\n" not in ini_content

    # Parse resulting INI file to confirm only legitimate [Song] section exists
    parsed = IniWriter.parse_string(ini_content)
    assert "injected_key" not in parsed
    assert "bad:key=name" not in parsed
    assert parsed.get("name") is not None
    assert "\n" not in parsed["name"]


def test_string_sanitizer_edge_cases():
    """Verify sanitize_string behavior with quotes, braces, control chars, and truncation."""
    # Control chars removal
    raw = "Hello\x00\x08World\x1b"
    assert sanitize_string(raw) == "HelloWorld"

    # Max length truncation
    long_string = "A" * 200
    assert len(sanitize_string(long_string, max_length=128)) == 128

    # Escape quotes and strip section closers
    exploit = 'Track Name "with quotes" and } closing brace'
    sanitized = sanitize_string(exploit)
    assert "}" not in sanitized
    assert r"\"with quotes\"" in sanitized


def test_ini_sanitizers():
    """Verify sanitize_ini_key and sanitize_ini_value functionality."""
    assert sanitize_ini_key("  Name=Prop:Sec\n[Test]  ") == "namepropsectest"
    assert sanitize_ini_value("Line 1\r\nLine 2\nLine 3") == "Line 1 Line 2 Line 3"
