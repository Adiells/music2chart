"""Unit tests for core domain models and representations."""

from pathlib import Path

import pytest

from src.models import (
    AudioMetadata,
    BPMChange,
    ChartNote,
    FretType,
    NoteEvent,
    SngFileEntry,
    SngMetadata,
    SongTrack,
    StarPowerPhrase,
    StemCollection,
    TempoMap,
    TimeSignature,
)


def test_note_event_valid_and_duration() -> None:
    """Validate valid NoteEvent instantiation and duration calculation."""
    note = NoteEvent(start_time=1.0, end_time=2.5, pitch=60, amplitude=0.8)
    assert note.start_time == 1.0
    assert note.end_time == 2.5
    assert note.pitch == 60
    assert note.amplitude == 0.8
    assert note.duration == 1.5


@pytest.mark.parametrize(
    ("start_time", "end_time", "pitch", "amplitude"),
    [
        (-0.1, 1.0, 60, 0.8),  # Negative start time
        (1.0, 1.0, 60, 0.8),  # end_time == start_time
        (1.0, 0.5, 60, 0.8),  # end_time < start_time
        (0.0, 1.0, -1, 0.8),  # Pitch below 0
        (0.0, 1.0, 128, 0.8),  # Pitch above 127
        (0.0, 1.0, 60, -0.1),  # Amplitude below 0.0
        (0.0, 1.0, 60, 1.1),  # Amplitude above 1.0
    ],
)
def test_note_event_invalid_constraints(
    start_time: float, end_time: float, pitch: int, amplitude: float
) -> None:
    """Ensure invalid NoteEvent parameters raise ValueError."""
    with pytest.raises(ValueError):
        NoteEvent(start_time=start_time, end_time=end_time, pitch=pitch, amplitude=amplitude)


def test_tempo_map_constant_120_bpm() -> None:
    """Validate tick <-> second conversion for constant 120 BPM."""
    tmap = TempoMap(
        resolution=192,
        bpm_changes=[BPMChange(tick=0, bpm=120.0)],
        time_signatures=[TimeSignature(tick=0, numerator=4, denominator=4)],
    )

    # 120 BPM = 2 beats/sec -> 0.5s per quarter note (192 ticks)
    assert tmap.tick_to_seconds(0) == 0.0
    assert tmap.tick_to_seconds(192) == pytest.approx(0.5)
    assert tmap.tick_to_seconds(384) == pytest.approx(1.0)
    assert tmap.tick_to_seconds(768) == pytest.approx(2.0)

    # Inverted conversion
    assert tmap.seconds_to_tick(0.0) == 0
    assert tmap.seconds_to_tick(0.5) == 192
    assert tmap.seconds_to_tick(1.0) == 384
    assert tmap.seconds_to_tick(2.0) == 768

    # Edge cases
    assert tmap.seconds_to_tick(-1.0) == 0
    assert tmap.tick_to_seconds(-50) == 0.0


def test_tempo_map_variable_bpm() -> None:
    """Validate tick <-> second conversion across variable BPM changes."""
    # From tick 0 to 384: 120.0 BPM (duration = 384 * (60 / (120 * 192)) = 1.0s)
    # From tick 384 onward: 60.0 BPM (duration = 192 * (60 / (60 * 192)) = 1.0s per beat)
    tmap = TempoMap(
        resolution=192,
        bpm_changes=[
            BPMChange(tick=0, bpm=120.0),
            BPMChange(tick=384, bpm=60.0),
        ],
    )

    # At tick 384: exactly 1.0s
    assert tmap.tick_to_seconds(384) == pytest.approx(1.0)

    # At tick 576 (384 + 192): 1.0s + 1.0s = 2.0s
    assert tmap.tick_to_seconds(576) == pytest.approx(2.0)

    # Inverse checks
    assert tmap.seconds_to_tick(1.0) == 384
    assert tmap.seconds_to_tick(2.0) == 576
    assert tmap.seconds_to_tick(1.5) == 480  # 384 + (0.5 * 192)


def test_chart_note_ordering() -> None:
    """Verify that ChartNote instances sort primarily by tick, secondarily by fret."""
    notes = [
        ChartNote(tick=192, fret=FretType.BLUE),
        ChartNote(tick=96, fret=FretType.RED),
        ChartNote(tick=192, fret=FretType.GREEN),
        ChartNote(tick=0, fret=FretType.OPEN),
        ChartNote(tick=96, fret=FretType.GREEN),
    ]

    sorted_notes = sorted(notes)
    expected = [
        ChartNote(tick=0, fret=FretType.OPEN),
        ChartNote(tick=96, fret=FretType.GREEN),
        ChartNote(tick=96, fret=FretType.RED),
        ChartNote(tick=192, fret=FretType.GREEN),
        ChartNote(tick=192, fret=FretType.BLUE),
    ]
    assert sorted_notes == expected


def test_chart_note_validations() -> None:
    """Ensure invalid note values trigger validation errors."""
    with pytest.raises(ValueError):
        ChartNote(tick=-1, fret=FretType.GREEN)
    with pytest.raises(ValueError):
        ChartNote(tick=0, fret=FretType.GREEN, sustain_length=-10)

    # Int fret coercion
    note = ChartNote(tick=100, fret=0)  # type: ignore[arg-type]
    assert note.fret == FretType.GREEN


def test_audio_metadata_and_stem_collection() -> None:
    """Validate AudioMetadata and StemCollection methods."""
    meta = AudioMetadata(
        sample_rate=44100,
        channels=2,
        duration_seconds=180.5,
        file_path=Path("song.mp3"),
    )
    assert meta.sample_rate == 44100

    with pytest.raises(ValueError):
        AudioMetadata(sample_rate=-1, channels=2, duration_seconds=10.0, file_path=Path("s.wav"))

    stems = StemCollection(
        mix_path=Path("mix.wav"),
        guitar_path=Path("guitar.wav"),
        bass_path=Path("bass.wav"),
    )
    avail = stems.available_stems()
    assert "guitar" in avail
    assert "bass" in avail
    assert "drums" not in avail


def test_sng_models_validation() -> None:
    """Validate SngMetadata conversion and SngFileEntry rules."""
    meta = SngMetadata(
        name="Test Song",
        artist="Test Artist",
        diff_guitar=6,
        extra={"custom_tag": "value"},
    )
    data = meta.to_dict()
    assert data["name"] == "Test Song"
    assert data["diff_guitar"] == "6"
    assert data["custom_tag"] == "value"

    # SngFileEntry validations
    with pytest.raises(ValueError, match="backslashes"):
        SngFileEntry(file_name="sub\\song.ogg", file_length=100, file_offset=0)

    with pytest.raises(ValueError, match="exceeds 255"):
        SngFileEntry(file_name="a" * 256, file_length=100, file_offset=0)


def test_song_track_and_star_power() -> None:
    """Validate SongTrack collection helpers and StarPowerPhrase."""
    sp = StarPowerPhrase(tick=100, length=768)
    assert sp.tick == 100
    assert sp.length == 768

    with pytest.raises(ValueError):
        StarPowerPhrase(tick=-1, length=100)

    track = SongTrack(name="ExpertSingle", star_power=[sp])
    note1 = ChartNote(tick=100, fret=FretType.GREEN)
    note2 = ChartNote(tick=100, fret=FretType.RED)
    note3 = ChartNote(tick=200, fret=FretType.YELLOW)
    track.add_note(note3)
    track.add_note(note1)
    track.add_note(note2)

    assert track.notes == [note1, note2, note3]
    assert track.notes_at_tick(100) == [note1, note2]
    assert track.notes_at_tick(999) == []
    assert len(track.star_power) == 1
