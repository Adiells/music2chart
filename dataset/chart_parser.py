"""Bidirectional parser for Clone Hero .chart text format."""

import re
from pathlib import Path

from src.models import (
    BPMChange,
    ChartNote,
    FretType,
    SongTrack,
    StarPowerPhrase,
    TempoMap,
    TimeSignature,
)

SECTION_REGEX = re.compile(r"^\[([^\]]+)\]$")
KEY_VALUE_REGEX = re.compile(r"^([^=]+)=(.*)$")
NOTE_EVENT_REGEX = re.compile(r"^\s*(\d+)\s*=\s*N\s+(\d+)\s+(\d+)\s*$")
STAR_POWER_REGEX = re.compile(r"^\s*(\d+)\s*=\s*S\s+(\d+)\s+(\d+)\s*$")
SYNC_BPM_REGEX = re.compile(r"^\s*(\d+)\s*=\s*B\s+(\d+)\s*$")
SYNC_TS_REGEX = re.compile(r"^\s*(\d+)\s*=\s*TS\s+(\d+)(?:\s+(\d+))?\s*$")


class ChartParser:
    """Parser for Clone Hero .chart files converting text into domain representations."""

    @staticmethod
    def _strip_comment(line: str) -> str:
        """Strip // inline comments and trim whitespace."""
        if "//" in line:
            line = line.split("//", 1)[0]
        return line.strip()

    def parse_file(self, file_path: Path) -> tuple[TempoMap, dict[str, SongTrack], dict[str, str]]:
        """Read and parse a .chart file from filesystem."""
        try:
            content = file_path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            content = file_path.read_text(encoding="latin-1")
        return self.parse_text(content)

    def parse_text(self, content: str) -> tuple[TempoMap, dict[str, SongTrack], dict[str, str]]:
        """Parse raw text of a .chart format into TempoMap, tracks, and metadata."""
        lines = content.splitlines()
        song_metadata: dict[str, str] = {}
        bpm_changes: list[BPMChange] = []
        time_signatures: list[TimeSignature] = []
        tracks: dict[str, SongTrack] = {}

        current_section: str | None = None
        inside_block = False

        resolution = 192

        for raw_line in lines:
            line = self._strip_comment(raw_line)
            if not line:
                continue

            # Check section header [SectionName]
            section_match = SECTION_REGEX.match(line)
            if section_match:
                current_section = section_match.group(1).strip()
                continue

            if line == "{":
                inside_block = True
                continue
            if line == "}":
                inside_block = False
                current_section = None
                continue

            if not inside_block or not current_section:
                continue

            # Section [Song]
            if current_section == "Song":
                kv_match = KEY_VALUE_REGEX.match(line)
                if kv_match:
                    key = kv_match.group(1).strip()
                    val = kv_match.group(2).strip()
                    if val.startswith('"') and val.endswith('"') and len(val) >= 2:
                        val = val[1:-1]
                    song_metadata[key] = val
                    if key.lower() == "resolution":
                        try:
                            resolution = int(val)
                        except ValueError:
                            pass

            # Section [SyncTrack]
            elif current_section == "SyncTrack":
                bpm_match = SYNC_BPM_REGEX.match(line)
                if bpm_match:
                    tick = int(bpm_match.group(1))
                    milli_bpm = int(bpm_match.group(2))
                    bpm = milli_bpm / 1000.0
                    bpm_changes.append(BPMChange(tick=tick, bpm=bpm))
                    continue

                ts_match = SYNC_TS_REGEX.match(line)
                if ts_match:
                    tick = int(ts_match.group(1))
                    num = int(ts_match.group(2))
                    den_exp = int(ts_match.group(3)) if ts_match.group(3) else 2
                    den = 2**den_exp if ts_match.group(3) else 4
                    time_signatures.append(TimeSignature(tick=tick, numerator=num, denominator=den))
                    continue

            # Track sections (e.g. ExpertSingle, HardSingle, Events, etc.)
            else:
                if current_section not in tracks:
                    tracks[current_section] = SongTrack(name=current_section)
                track = tracks[current_section]

                # Note event
                note_match = NOTE_EVENT_REGEX.match(line)
                if note_match:
                    tick = int(note_match.group(1))
                    fret_val = int(note_match.group(2))
                    sus = int(note_match.group(3))
                    try:
                        fret = FretType(fret_val)
                        track.add_note(ChartNote(tick=tick, fret=fret, sustain_length=sus))
                    except ValueError:
                        # Ignore unknown fret values outside specification
                        pass
                    continue

                # Star power event (S 2 <length>)
                sp_match = STAR_POWER_REGEX.match(line)
                if sp_match:
                    tick = int(sp_match.group(1))
                    sp_type = int(sp_match.group(2))
                    length = int(sp_match.group(3))
                    if sp_type == 2:
                        track.star_power.append(StarPowerPhrase(tick=tick, length=length))
                    continue

        tempo_map = TempoMap(
            resolution=resolution,
            bpm_changes=bpm_changes,
            time_signatures=time_signatures,
        )

        return tempo_map, tracks, song_metadata

    def to_chart_notes(self, raw_lines: list[str]) -> list[ChartNote]:
        """Convert a list of raw track note lines into ChartNote objects."""
        notes: list[ChartNote] = []
        for raw_line in raw_lines:
            line = self._strip_comment(raw_line)
            match = NOTE_EVENT_REGEX.match(line)
            if match:
                tick = int(match.group(1))
                fret_val = int(match.group(2))
                sus = int(match.group(3))
                try:
                    notes.append(ChartNote(tick=tick, fret=FretType(fret_val), sustain_length=sus))
                except ValueError:
                    pass
        notes.sort()
        return notes
