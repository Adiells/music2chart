"""Unit tests for the Rock Band MIDI chart parser (dataset/midi_parser.py)."""

from pathlib import Path

import mido
import pytest
from mido import Message, MetaMessage, MidiFile, MidiTrack

from dataset.midi_parser import MidiChartParser
from src.models import FretType

RESOLUTION = 480


def _add_note(track: MidiTrack, pitch: int, start: int, duration: int) -> None:
    """Append a note-on/note-off pair using absolute ticks converted to deltas."""
    current_tick = sum(msg.time for msg in track)
    track.append(Message("note_on", note=pitch, velocity=100, time=start - current_tick))
    track.append(Message("note_off", note=pitch, velocity=0, time=duration))


def _write_synthetic_midi(path: Path, instrument: str = "PART GUITAR") -> Path:
    """Create a synthetic Rock Band style MIDI file with TEMPO TRACK and PART GUITAR."""
    mid = MidiFile(type=1, ticks_per_beat=RESOLUTION)

    # 1. TEMPO TRACK
    tempo_track = MidiTrack()
    mid.tracks.append(tempo_track)
    tempo_track.append(MetaMessage("track_name", name="TEMPO TRACK", time=0))
    # 120 BPM: 500,000 microseconds per beat -> at 480 resolution, 1 beat = 480 ticks = 0.5s
    tempo_track.append(MetaMessage("set_tempo", tempo=500000, time=0))
    tempo_track.append(MetaMessage("time_signature", numerator=4, denominator=4, time=0))
    # At tick 1920 (2.0s), change tempo to 150 BPM (400,000 us/beat -> 1 beat = 480 ticks = 0.4s)
    tempo_track.append(MetaMessage("set_tempo", tempo=400000, time=1920))

    # 2. PART GUITAR
    instrument_track = MidiTrack()
    mid.tracks.append(instrument_track)
    instrument_track.append(MetaMessage("track_name", name=instrument, time=0))

    # Expert notes:
    # 96 -> GREEN (tick 0, duration 480 ticks = 1 beat sustain)
    _add_note(instrument_track, 96, 0, 480)
    # 97 -> RED (tick 480, duration 240 ticks = half beat sustain)
    _add_note(instrument_track, 97, 480, 240)
    # 98 -> YELLOW (tick 960, duration 0)
    _add_note(instrument_track, 98, 960, 0)
    # 99 -> BLUE (tick 1200, duration 0)
    _add_note(instrument_track, 99, 1200, 0)
    # 100 -> ORANGE (tick 1440, duration 0)
    _add_note(instrument_track, 100, 1440, 0)

    # Modifiers and open note:
    _add_note(instrument_track, 101, 1680, 0)  # HOPO_FORCE
    _add_note(instrument_track, 102, 1920, 0)  # STRUM_FORCE
    _add_note(instrument_track, 103, 2160, 0)  # OPEN

    # Star Power phrase (pitch 116) spanning ticks 2400 to 3360 (duration 960)
    _add_note(instrument_track, 116, 2400, 960)

    mid.save(str(path))
    return path


def test_synthetic_midi_loading_and_conversion(tmp_path: Path) -> None:
    """Validate loading synthetic MIDI file with TEMPO TRACK and PART GUITAR.

    Verifies:
    - Resolution extraction (480 PPQ)
    - BPM changes (120 BPM at 0, 150 BPM at 1920)
    - Ticks to seconds conversion across tempo changes
    - Expert notes mapping (96-100 -> GREEN, RED, YELLOW, BLUE, ORANGE)
    - Sustain calculations
    - Star Power phrase detection (pitch 116)
    """
    midi_path = _write_synthetic_midi(tmp_path / "synthetic_test.mid")
    parser = MidiChartParser()
    tempo_map, tracks, metadata = parser.parse_file(midi_path)

    # Resolution
    assert tempo_map.resolution == 480
    assert metadata["Resolution"] == "480"
    assert "TEMPO TRACK" in metadata["TrackNames"]
    assert "PART GUITAR" in metadata["TrackNames"]

    # BPM changes
    assert len(tempo_map.bpm_changes) == 2
    assert tempo_map.bpm_changes[0].tick == 0
    assert tempo_map.bpm_changes[0].bpm == pytest.approx(120.0)
    assert tempo_map.bpm_changes[1].tick == 1920
    assert tempo_map.bpm_changes[1].bpm == pytest.approx(150.0)

    # Ticks to seconds conversion
    # At 120 BPM: 480 ticks = 0.5s
    assert tempo_map.tick_to_seconds(0) == pytest.approx(0.0)
    assert tempo_map.tick_to_seconds(480) == pytest.approx(0.5)
    assert tempo_map.tick_to_seconds(960) == pytest.approx(1.0)
    assert tempo_map.tick_to_seconds(1920) == pytest.approx(2.0)
    # At tick 1920+, tempo is 150 BPM (480 ticks = 0.4s)
    # Tick 2400 = 1920 + 480 -> 2.0s + 0.4s = 2.4s
    assert tempo_map.tick_to_seconds(2400) == pytest.approx(2.4)
    # Tick 3360 = 2400 + 960 (2 beats @ 150 BPM = 0.8s) -> 2.4s + 0.8s = 3.2s
    assert tempo_map.tick_to_seconds(3360) == pytest.approx(3.2)

    # Track presence
    assert "ExpertSingle" in tracks
    expert_track = tracks["ExpertSingle"]

    # Expert notes mapping (96-100 -> GREEN through ORANGE)
    regular_notes = [n for n in expert_track.notes if n.fret.value <= 4]
    assert len(regular_notes) == 5
    assert [n.fret for n in regular_notes] == [
        FretType.GREEN,
        FretType.RED,
        FretType.YELLOW,
        FretType.BLUE,
        FretType.ORANGE,
    ]
    assert [n.tick for n in regular_notes] == [0, 480, 960, 1200, 1440]

    # Sustain calculation
    # Note 0 (GREEN at 0): 480 ticks sustain
    assert regular_notes[0].sustain_length == 480
    # Note 1 (RED at 480): 240 ticks sustain
    assert regular_notes[1].sustain_length == 240
    # Note 2 (YELLOW at 960): 0 ticks sustain
    assert regular_notes[2].sustain_length == 0

    # Modifiers and open note
    modifier_notes = [n for n in expert_track.notes if n.fret.value > 4]
    assert len(modifier_notes) == 3
    assert modifier_notes[0].fret == FretType.HOPO_FORCE
    assert modifier_notes[0].tick == 1680
    assert modifier_notes[1].fret == FretType.STRUM_FORCE
    assert modifier_notes[1].tick == 1920
    assert modifier_notes[2].fret == FretType.OPEN
    assert modifier_notes[2].tick == 2160

    # Star Power phrase (pitch 116)
    assert len(expert_track.star_power) == 1
    sp = expert_track.star_power[0]
    assert sp.tick == 2400
    assert sp.length == 960


def test_difficulty_offsets_map_to_same_frets(tmp_path: Path) -> None:
    """Hard (84), Medium (72) and Easy (60) bases must resolve to Green..Orange."""
    midi_path = _write_synthetic_midi(tmp_path / "notes.mid")
    _, tracks, _ = MidiChartParser().parse_file(midi_path)

    for difficulty in ("Hard", "Medium", "Easy"):
        assert tracks[f"{difficulty}Single"].notes == []

    parser = MidiChartParser()
    for base in (84, 72, 60):
        assert parser._pitch_to_fret(base, base) == FretType.GREEN
        assert parser._pitch_to_fret(base + 1, base) == FretType.RED
        assert parser._pitch_to_fret(base + 2, base) == FretType.YELLOW
        assert parser._pitch_to_fret(base + 3, base) == FretType.BLUE
        assert parser._pitch_to_fret(base + 4, base) == FretType.ORANGE
        assert parser._pitch_to_fret(base + 5, base) == FretType.HOPO_FORCE
        assert parser._pitch_to_fret(base + 6, base) == FretType.STRUM_FORCE
        assert parser._pitch_to_fret(base + 7, base) == FretType.OPEN
        assert parser._pitch_to_fret(base + 8, base) is None


def test_bass_track_uses_double_bass_key(tmp_path: Path) -> None:
    """PART BASS maps to the .chart DoubleBass section naming."""
    midi_path = _write_synthetic_midi(tmp_path / "notes.mid", instrument="PART BASS")
    _, tracks, _ = MidiChartParser().parse_file(midi_path)

    assert "ExpertDoubleBass" in tracks
    assert "ExpertSingle" not in tracks
    assert len(tracks["ExpertDoubleBass"].notes) == 8


def test_missing_file_raises(tmp_path: Path) -> None:
    """A missing path propagates FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        MidiChartParser().parse_file(tmp_path / "non_existent_file.mid")


def test_real_notes_mid_file() -> None:
    """Test with the real notes.mid at project root (/home/adiel/Projects/music2chart/notes.mid).

    Must guarantee:
    - parse_file finds exactly 1095 Expert notes (GREEN through ORANGE, pitches 96-100)
    - resolution is 480
    """
    real_midi_path = Path("/home/adiel/Projects/music2chart/notes.mid")
    if not real_midi_path.is_file():
        real_midi_path = Path(__file__).resolve().parents[2] / "notes.mid"

    if not real_midi_path.is_file():
        pytest.skip("notes.mid not present at project root")

    parser = MidiChartParser()
    tempo_map, tracks, metadata = parser.parse_file(real_midi_path)

    # Resolution must be 480
    assert tempo_map.resolution == 480
    assert metadata["Resolution"] == "480"
    mid_raw = mido.MidiFile(str(real_midi_path))
    assert mid_raw.ticks_per_beat == 480

    # Expert Single track must be present
    assert "ExpertSingle" in tracks
    expert_track = tracks["ExpertSingle"]

    # Fret notes Expert (GREEN, RED, YELLOW, BLUE, ORANGE -> 96-100)
    expert_fret_notes = [n for n in expert_track.notes if n.fret.value <= 4]
    assert len(expert_fret_notes) == 1095, (
        f"Expected exactly 1095 Expert notes (frets 0-4), got {len(expert_fret_notes)}"
    )

    # Breakdown validation
    from collections import Counter

    counts = Counter(n.fret for n in expert_fret_notes)
    assert counts[FretType.GREEN] == 160
    assert counts[FretType.RED] == 287
    assert counts[FretType.YELLOW] == 285
    assert counts[FretType.BLUE] == 257
    assert counts[FretType.ORANGE] == 106
    assert sum(counts.values()) == 1095

    # Star Power phrases
    assert len(expert_track.star_power) == 12
