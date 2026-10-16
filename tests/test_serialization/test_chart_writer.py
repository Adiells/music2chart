"""Unit tests for Clone Hero .chart and song.ini serializers."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from dataset.chart_parser import ChartParser
from src.models import (
    BPMChange,
    ChartNote,
    FretType,
    SongTrack,
    StarPowerPhrase,
    TempoMap,
    TimeSignature,
)
from src.models.sng import SngMetadata
from src.serialization.chart_writer import ChartWriter
from src.serialization.ini_writer import IniWriter

# ---------------------------------------------------------------------------
# ChartWriter Tests
# ---------------------------------------------------------------------------


class TestChartWriter:
    """Test suite for ChartWriter text serialization."""

    @pytest.fixture
    def sample_tempo_map(self) -> TempoMap:
        """Create a multi-tempo map with variable time signatures."""
        return TempoMap(
            resolution=192,
            bpm_changes=[
                BPMChange(tick=0, bpm=120.0),
                BPMChange(tick=768, bpm=145.5),
            ],
            time_signatures=[
                TimeSignature(tick=0, numerator=4, denominator=4),
                TimeSignature(tick=1536, numerator=3, denominator=4),
                TimeSignature(tick=2304, numerator=6, denominator=8),
            ],
        )

    @pytest.fixture
    def sample_tracks(self) -> dict[str, SongTrack]:
        """Create sample ExpertSingle track with chords, open notes, sustains, forcers, and SP."""
        notes = [
            ChartNote(tick=0, fret=FretType.OPEN, sustain_length=0),
            ChartNote(tick=96, fret=FretType.GREEN, sustain_length=0),
            ChartNote(tick=192, fret=FretType.RED, sustain_length=96),
            # Two-note chord at tick 384
            ChartNote(tick=384, fret=FretType.GREEN, sustain_length=0),
            ChartNote(tick=384, fret=FretType.YELLOW, sustain_length=0),
            # HOPO and Strum forcers
            ChartNote(tick=480, fret=FretType.BLUE, sustain_length=0),
            ChartNote(tick=480, fret=FretType.HOPO_FORCE, sustain_length=0),
            ChartNote(tick=576, fret=FretType.BLUE, sustain_length=0),
            ChartNote(tick=576, fret=FretType.STRUM_FORCE, sustain_length=0),
            # High solo notes
            ChartNote(tick=768, fret=FretType.ORANGE, sustain_length=48),
        ]
        star_power = [
            StarPowerPhrase(tick=384, length=384),
        ]
        track = SongTrack(name="ExpertSingle", notes=notes, star_power=star_power)
        return {"ExpertSingle": track}

    def test_generate_chart_string_structure(
        self, sample_tempo_map: TempoMap, sample_tracks: dict[str, SongTrack]
    ) -> None:
        """Verify the generated chart string contains all required section blocks."""
        content = ChartWriter.generate_chart_string(
            song_name="Through the Fire",
            artist="DragonForce",
            tempo_map=sample_tempo_map,
            tracks=sample_tracks,
            charter="music2chart AI",
            genre="power metal",
        )

        assert "[Song]" in content
        assert "[SyncTrack]" in content
        assert "[Events]" in content
        assert "[ExpertSingle]" in content
        assert content.endswith("\n")
        assert "\r\n" not in content  # Standard UNIX newlines

    def test_song_section_regex_validation(
        self, sample_tempo_map: TempoMap, sample_tracks: dict[str, SongTrack]
    ) -> None:
        """Verify each line in the [Song] section adheres to specification."""
        content = ChartWriter.generate_chart_string(
            song_name="Epic Anthem",
            artist="Band X",
            tempo_map=sample_tempo_map,
            tracks=sample_tracks,
            offset=15,
            difficulty=5,
        )

        # Regex patterns for mandatory [Song] fields
        assert re.search(r'Name\s*=\s*"Epic Anthem"', content)
        assert re.search(r'Artist\s*=\s*"Band X"', content)
        assert re.search(r'Charter\s*=\s*"music2chart AI"', content)
        assert re.search(r"Offset\s*=\s*15", content)
        assert re.search(r"Resolution\s*=\s*192", content)
        assert re.search(r"Player2\s*=\s*bass", content)
        assert re.search(r"Difficulty\s*=\s*5", content)
        assert re.search(r'MusicStream\s*=\s*"song\.ogg"', content)

    def test_sync_track_regex_validation(
        self, sample_tempo_map: TempoMap, sample_tracks: dict[str, SongTrack]
    ) -> None:
        """Verify SyncTrack contains correctly scaled BPMs and time signatures."""
        content = ChartWriter.generate_chart_string(
            song_name="Song",
            artist="Artist",
            tempo_map=sample_tempo_map,
            tracks=sample_tracks,
        )

        # 120.0 BPM -> 120000
        assert re.search(r"0\s*=\s*B\s+120000", content)
        # 145.5 BPM -> 145500
        assert re.search(r"768\s*=\s*B\s+145500", content)
        # 4/4 TS
        assert re.search(r"0\s*=\s*TS\s+4", content)
        # 3/4 TS
        assert re.search(r"1536\s*=\s*TS\s+3", content)
        # 6/8 TS (8 is 2^3, so exponent 3)
        assert re.search(r"2304\s*=\s*TS\s+6\s+3", content)

    def test_events_section(
        self, sample_tempo_map: TempoMap, sample_tracks: dict[str, SongTrack]
    ) -> None:
        """Verify custom and default practice events serialization."""
        # Default event
        content_default = ChartWriter.generate_chart_string(
            song_name="Song",
            artist="Artist",
            tempo_map=sample_tempo_map,
            tracks=sample_tracks,
        )
        assert re.search(r'0\s*=\s*E\s+"section Intro"', content_default)

        # Custom events
        custom_events = [
            (0, "section Intro"),
            (768, "section Verse 1"),
            (1536, "section Solo"),
        ]
        content_custom = ChartWriter.generate_chart_string(
            song_name="Song",
            artist="Artist",
            tempo_map=sample_tempo_map,
            tracks=sample_tracks,
            events=custom_events,
        )
        assert re.search(r'0\s*=\s*E\s+"section Intro"', content_custom)
        assert re.search(r'768\s*=\s*E\s+"section Verse 1"', content_custom)
        assert re.search(r'1536\s*=\s*E\s+"section Solo"', content_custom)

    def test_track_notes_and_star_power(
        self, sample_tempo_map: TempoMap, sample_tracks: dict[str, SongTrack]
    ) -> None:
        """Verify note serialization for open notes, chords, forcers, and star power."""
        content = ChartWriter.generate_chart_string(
            song_name="Song",
            artist="Artist",
            tempo_map=sample_tempo_map,
            tracks=sample_tracks,
        )

        # Open note at tick 0
        assert re.search(r"0\s*=\s*N\s+7\s+0", content)
        # Green note at tick 96
        assert re.search(r"96\s*=\s*N\s+0\s+0", content)
        # Red note with sustain 96 at tick 192
        assert re.search(r"192\s*=\s*N\s+1\s+96", content)
        # Two-note chord at tick 384 (Green 0 + Yellow 2)
        assert re.search(r"384\s*=\s*N\s+0\s+0", content)
        assert re.search(r"384\s*=\s*N\s+2\s+0", content)
        # Star power phrase at tick 384 length 384
        assert re.search(r"384\s*=\s*S\s+2\s+384", content)
        # HOPO forcer at tick 480
        assert re.search(r"480\s*=\s*N\s+5\s+0", content)
        # Strum forcer at tick 576
        assert re.search(r"576\s*=\s*N\s+6\s+0", content)
        # High note with sustain at tick 768
        assert re.search(r"768\s*=\s*N\s+4\s+48", content)

    def test_write_to_file_and_round_trip(
        self, sample_tempo_map: TempoMap, sample_tracks: dict[str, SongTrack], tmp_path: Path
    ) -> None:
        """Verify write() creates a valid file that can be parsed back with ChartParser identically."""
        output_path = tmp_path / "notes.chart"
        written_path = ChartWriter.write(
            song_name="Roundtrip Test",
            artist="Tester",
            tempo_map=sample_tempo_map,
            tracks=sample_tracks,
            output_path=output_path,
            charter="music2chart AI",
        )

        assert written_path.is_file()
        assert written_path == output_path

        # Parse generated chart back with ChartParser
        parser = ChartParser()
        parsed_tempo, parsed_tracks, parsed_meta = parser.parse_file(written_path)

        # Verify metadata
        assert parsed_meta["Name"] == "Roundtrip Test"
        assert parsed_meta["Artist"] == "Tester"
        assert parsed_meta["Charter"] == "music2chart AI"
        assert parsed_tempo.resolution == 192

        # Verify BPM changes
        assert len(parsed_tempo.bpm_changes) == 2
        assert parsed_tempo.bpm_changes[0].tick == 0
        assert parsed_tempo.bpm_changes[0].bpm == 120.0
        assert parsed_tempo.bpm_changes[1].tick == 768
        assert pytest.approx(parsed_tempo.bpm_changes[1].bpm) == 145.5

        # Verify notes in ExpertSingle
        assert "ExpertSingle" in parsed_tracks
        track = parsed_tracks["ExpertSingle"]

        orig_track = sample_tracks["ExpertSingle"]
        # Filter expected notes (ChartParser loads all N events with valid FretType)
        assert len(track.notes) == len(orig_track.notes)
        for orig_n, parsed_n in zip(orig_track.notes, track.notes, strict=True):
            assert orig_n.tick == parsed_n.tick
            assert orig_n.fret == parsed_n.fret
            assert orig_n.sustain_length == parsed_n.sustain_length

        # Verify Star Power
        assert len(track.star_power) == len(orig_track.star_power)
        assert track.star_power[0].tick == orig_track.star_power[0].tick
        assert track.star_power[0].length == orig_track.star_power[0].length

    def test_hopo_and_strum_force_formatting_and_ordering(self, sample_tempo_map: TempoMap) -> None:
        """Verify HOPO_FORCE (5) and STRUM_FORCE (6) are formatted as N 5 0 / N 6 0 and sorted by tick."""
        notes = [
            ChartNote(tick=192, fret=FretType.HOPO_FORCE, sustain_length=0),
            ChartNote(tick=192, fret=FretType.RED, sustain_length=0),
            ChartNote(tick=96, fret=FretType.GREEN, sustain_length=0),
            ChartNote(tick=288, fret=FretType.STRUM_FORCE, sustain_length=0),
            ChartNote(tick=288, fret=FretType.YELLOW, sustain_length=48),
        ]
        track = SongTrack(name="ExpertSingle", notes=notes)
        content = ChartWriter.generate_chart_string(
            song_name="Modifier Test",
            artist="Tester",
            tempo_map=sample_tempo_map,
            tracks={"ExpertSingle": track},
        )

        # Verify correct formatting
        assert "  192 = N 5 0\n" in content
        assert "  288 = N 6 0\n" in content

        # Verify sorting: 96 before 192 before 288
        idx_96 = content.index("  96 = N 0 0")
        idx_192_n = content.index("  192 = N 1 0")
        idx_192_m = content.index("  192 = N 5 0")
        idx_288_n = content.index("  288 = N 2 48")
        idx_288_m = content.index("  288 = N 6 0")

        assert idx_96 < idx_192_n < idx_192_m < idx_288_n < idx_288_m

    def test_modifier_sustain_length_forced_to_zero(self, sample_tempo_map: TempoMap) -> None:
        """Verify any non-zero sustain length on HOPO_FORCE and STRUM_FORCE is forced to 0."""
        notes = [
            ChartNote(tick=96, fret=FretType.HOPO_FORCE, sustain_length=192),
            ChartNote(tick=192, fret=FretType.STRUM_FORCE, sustain_length=96),
        ]
        track = SongTrack(name="ExpertSingle", notes=notes)
        content = ChartWriter.generate_chart_string(
            song_name="Sustain Force Test",
            artist="Tester",
            tempo_map=sample_tempo_map,
            tracks={"ExpertSingle": track},
        )

        assert "  96 = N 5 0\n" in content
        assert "  192 = N 6 0\n" in content
        assert "N 5 192" not in content
        assert "N 6 96" not in content

    def test_duplicate_and_conflicting_modifiers_deduplication(
        self, sample_tempo_map: TempoMap
    ) -> None:
        """Verify duplicate modifiers are deduplicated and STRUM_FORCE overrides HOPO_FORCE at the same tick."""
        notes = [
            # Duplicate HOPO_FORCE at tick 96
            ChartNote(tick=96, fret=FretType.GREEN, sustain_length=0),
            ChartNote(tick=96, fret=FretType.HOPO_FORCE, sustain_length=0),
            ChartNote(tick=96, fret=FretType.HOPO_FORCE, sustain_length=0),
            # Conflicting HOPO_FORCE and STRUM_FORCE at tick 192 (STRUM_FORCE takes precedence)
            ChartNote(tick=192, fret=FretType.RED, sustain_length=0),
            ChartNote(tick=192, fret=FretType.HOPO_FORCE, sustain_length=0),
            ChartNote(tick=192, fret=FretType.STRUM_FORCE, sustain_length=0),
            # Duplicate playable note at tick 288 (longer sustain preserved)
            ChartNote(tick=288, fret=FretType.YELLOW, sustain_length=0),
            ChartNote(tick=288, fret=FretType.YELLOW, sustain_length=96),
        ]
        track = SongTrack(name="ExpertSingle", notes=notes)
        content = ChartWriter.generate_chart_string(
            song_name="Deduplication Test",
            artist="Tester",
            tempo_map=sample_tempo_map,
            tracks={"ExpertSingle": track},
        )

        # Tick 96: Exactly one N 5 0 line
        assert content.count("  96 = N 5 0") == 1

        # Tick 192: STRUM_FORCE present, conflicting HOPO_FORCE omitted
        assert "  192 = N 6 0\n" in content
        assert "  192 = N 5 0" not in content

        # Tick 288: Playable note deduplicated with max sustain
        assert content.count("  288 = N 2 ") == 1
        assert "  288 = N 2 96\n" in content

    def test_melodic_run_modifiers_roundtrip_with_chart_parser(
        self, sample_tempo_map: TempoMap, tmp_path: Path
    ) -> None:
        """Verify full round-trip of melodic runs with HOPO_FORCE and STRUM_FORCE through ChartWriter and ChartParser."""
        notes = [
            # Note 1: Strum anchor
            ChartNote(tick=0, fret=FretType.GREEN, sustain_length=0),
            # Notes 2-4: Forced HOPO in melodic run
            ChartNote(tick=48, fret=FretType.RED, sustain_length=0),
            ChartNote(tick=48, fret=FretType.HOPO_FORCE, sustain_length=0),
            ChartNote(tick=96, fret=FretType.YELLOW, sustain_length=0),
            ChartNote(tick=96, fret=FretType.HOPO_FORCE, sustain_length=0),
            ChartNote(tick=144, fret=FretType.BLUE, sustain_length=0),
            ChartNote(tick=144, fret=FretType.HOPO_FORCE, sustain_length=0),
            # Note 5: Repeated blue fret -> Forced Strum
            ChartNote(tick=192, fret=FretType.BLUE, sustain_length=0),
            ChartNote(tick=192, fret=FretType.STRUM_FORCE, sustain_length=0),
            # Note 6: High solo note with sustain
            ChartNote(tick=288, fret=FretType.ORANGE, sustain_length=96),
        ]
        track = SongTrack(name="ExpertSingle", notes=notes)

        out_path = tmp_path / "notes.chart"
        ChartWriter.write(
            song_name="Melodic Run Chart",
            artist="Speed Tester",
            tempo_map=sample_tempo_map,
            tracks={"ExpertSingle": track},
            output_path=out_path,
        )

        assert out_path.is_file()

        parser = ChartParser()
        _, parsed_tracks, _ = parser.parse_file(out_path)

        assert "ExpertSingle" in parsed_tracks
        parsed_notes = parsed_tracks["ExpertSingle"].notes

        # Compare notes one by one
        assert len(parsed_notes) == len(track.notes)
        for orig, parsed in zip(track.notes, parsed_notes, strict=True):
            assert orig.tick == parsed.tick
            assert orig.fret == parsed.fret
            assert orig.sustain_length == parsed.sustain_length

        # Also test ChartParser.to_chart_notes directly
        lines = [
            "48 = N 1 0",
            "48 = N 5 0",
            "192 = N 3 0",
            "192 = N 6 0",
        ]
        direct_notes = parser.to_chart_notes(lines)
        assert len(direct_notes) == 4
        assert direct_notes[0] == ChartNote(tick=48, fret=FretType.RED, sustain_length=0)
        assert direct_notes[1] == ChartNote(tick=48, fret=FretType.HOPO_FORCE, sustain_length=0)
        assert direct_notes[2] == ChartNote(tick=192, fret=FretType.BLUE, sustain_length=0)
        assert direct_notes[3] == ChartNote(tick=192, fret=FretType.STRUM_FORCE, sustain_length=0)

    def test_resolution_192_ppq_and_override(self) -> None:
        """Verify standard 192 PPQ resolution is preserved and outputted in [Song]."""
        default_tempo = TempoMap()  # defaults to resolution=192
        assert default_tempo.resolution == 192

        chart_default = ChartWriter.generate_chart_string(
            song_name="PPQ Test",
            artist="Charter",
            tempo_map=default_tempo,
            tracks={},
        )
        assert "  Resolution = 192\n" in chart_default

        # Override resolution
        chart_custom = ChartWriter.generate_chart_string(
            song_name="PPQ Test Custom",
            artist="Charter",
            tempo_map=default_tempo,
            tracks={},
            resolution=480,
        )
        assert "  Resolution = 480\n" in chart_custom

    def test_bpm_exact_milli_bpm_precision(self) -> None:
        """Verify BPM markers in [SyncTrack] are written with exact milli-BPM precision (B <bpm * 1000>)."""
        tempo = TempoMap(
            resolution=192,
            bpm_changes=[
                BPMChange(tick=0, bpm=120.0),
                BPMChange(tick=192, bpm=133.333),
                BPMChange(tick=384, bpm=98.7654),
                BPMChange(tick=576, bpm=145.5),
            ],
        )
        content = ChartWriter.generate_chart_string(
            song_name="MilliBPM Test",
            artist="Charter",
            tempo_map=tempo,
            tracks={},
        )
        assert "  0 = B 120000\n" in content
        assert "  192 = B 133333\n" in content
        assert "  384 = B 98765\n" in content
        assert "  576 = B 145500\n" in content

    def test_sustain_notes_held_vs_non_held_formatting(self, sample_tempo_map: TempoMap) -> None:
        """Verify held notes have sustain_length > 0 and non-held notes have sustain_length = 0."""
        notes = [
            ChartNote(tick=0, fret=FretType.GREEN, sustain_length=0),  # non-held
            ChartNote(tick=96, fret=FretType.RED, sustain_length=192),  # held
            ChartNote(tick=384, fret=FretType.YELLOW, sustain_length=0),  # non-held chord note
            ChartNote(tick=384, fret=FretType.BLUE, sustain_length=48),  # held chord note
        ]
        track = SongTrack(name="ExpertSingle", notes=notes)
        content = ChartWriter.generate_chart_string(
            song_name="Sustain Format Test",
            artist="Charter",
            tempo_map=sample_tempo_map,
            tracks={"ExpertSingle": track},
        )
        assert "  0 = N 0 0\n" in content
        assert "  96 = N 1 192\n" in content
        assert "  384 = N 2 0\n" in content
        assert "  384 = N 3 48\n" in content

    def test_extra_song_properties_and_duplicate_star_power(
        self, sample_tempo_map: TempoMap
    ) -> None:
        """Verify extra [Song] properties (numbers and strings) and duplicate SP phrases deduplication."""
        track = SongTrack(
            name="ExpertSingle",
            notes=[ChartNote(tick=0, fret=FretType.GREEN, sustain_length=0)],
            star_power=[
                StarPowerPhrase(tick=192, length=96),
                StarPowerPhrase(tick=192, length=96),  # Duplicate
            ],
        )
        content = ChartWriter.generate_chart_string(
            song_name="Extra Props Test",
            artist="Charter",
            tempo_map=sample_tempo_map,
            tracks={"ExpertSingle": track},
            extra_song_properties={
                "CustomInt": 42,
                "CustomFloat": 3.14,
                "CustomStr": "Hello",
            },
        )
        assert "  CustomInt = 42\n" in content
        assert "  CustomFloat = 3.14\n" in content
        assert '  CustomStr = "Hello"\n' in content
        assert content.count("  192 = S 2 96") == 1


# ---------------------------------------------------------------------------
# IniWriter Tests
# ---------------------------------------------------------------------------


class TestIniWriter:
    """Test suite for song.ini generator and parser."""

    def test_generate_ini_string_from_dataclass(self) -> None:
        """Verify INI content generation from SngMetadata dataclass."""
        meta = SngMetadata(
            name="Through the Fire and Flames",
            artist="DragonForce",
            charter="Custom Charter",
            album="Inhuman Rampage",
            year="2006",
            genre="Power Metal",
            diff_guitar=6,
            extra={"icon": "gh3"},
        )
        ini_text = IniWriter.generate_string(meta)

        assert "[Song]" in ini_text
        assert "name = Through the Fire and Flames" in ini_text
        assert "artist = DragonForce" in ini_text
        assert "charter = Custom Charter" in ini_text
        assert "album = Inhuman Rampage" in ini_text
        assert "year = 2006" in ini_text
        assert "genre = Power Metal" in ini_text
        assert "diff_guitar = 6" in ini_text
        assert "icon = gh3" in ini_text
        assert "\r\n" not in ini_text

    def test_generate_ini_string_from_dict(self) -> None:
        """Verify INI generation from plain dictionary."""
        data = {
            "name": "Cliffs of Dover",
            "artist": "Eric Johnson",
            "diff_guitar": 5,
        }
        ini_text = IniWriter.generate_string(data)
        assert "name = Cliffs of Dover" in ini_text
        assert "artist = Eric Johnson" in ini_text
        assert "diff_guitar = 5" in ini_text
        assert "charter = music2chart AI" in ini_text  # default charter

    def test_ini_write_and_parse_roundtrip(self, tmp_path: Path) -> None:
        """Verify writing song.ini and parsing it back returns exact metadata."""
        out_file = tmp_path / "song.ini"
        meta = SngMetadata(
            name="Free Bird",
            artist="Lynyrd Skynyrd",
            charter="music2chart AI",
            album="Pronounced",
            year="1973",
            genre="Southern Rock",
            diff_guitar=4,
        )

        written_path = IniWriter.write(out_file, meta)
        assert written_path.is_file()

        parsed = IniWriter.parse_file(written_path)
        assert parsed["name"] == "Free Bird"
        assert parsed["artist"] == "Lynyrd Skynyrd"
        assert parsed["charter"] == "music2chart AI"
        assert parsed["album"] == "Pronounced"
        assert parsed["year"] == "1973"
        assert parsed["genre"] == "Southern Rock"
        assert parsed["diff_guitar"] == "4"
