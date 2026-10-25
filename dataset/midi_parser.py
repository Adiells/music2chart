"""Parser for Rock Band / Phase Shift MIDI charts (``notes.mid``) into domain models.

The Rock Band MIDI format encodes the 5-fret chart as MIDI note numbers:

======================  ============================================
Note number             Meaning
======================  ============================================
``BASE + 0 .. BASE + 4`` Green (0) .. Orange (4)
``BASE + 5``            Forced HOPO modifier (:attr:`FretType.HOPO_FORCE`)
``BASE + 6``            Forced strum modifier (:attr:`FretType.STRUM_FORCE`)
``BASE + 7``            Open note (:attr:`FretType.OPEN`)
``116``                 Star Power phrase marker
======================  ============================================

``BASE`` depends on the difficulty encoded in the same track:

* Expert -> 96
* Hard -> 84
* Medium -> 72
* Easy -> 60

The output is intentionally isomorphic to :class:`dataset.chart_parser.ChartParser`:
``(TempoMap, dict[str, SongTrack], dict[str, str])`` where the track keys use the
``.chart`` section naming convention (``ExpertSingle``, ``HardSingle``,
``ExpertDoubleBass``, ...).  This allows MIDI ground-truth files to be evaluated by
``dataset.evaluate_mapping`` without any intermediate conversion.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import mido
from mido import MidiFile, MidiTrack

from src.models import (
    BPMChange,
    ChartNote,
    FretType,
    SongTrack,
    StarPowerPhrase,
    TempoMap,
    TimeSignature,
)

#: MIDI note used for Star Power phrase markers in Rock Band charts.
STAR_POWER_NOTE: Final[int] = 116

#: Lowest MIDI note of the Expert/Hard/Medium/Easy fret range.
DIFFICULTY_PITCH_BASE: Final[dict[str, int]] = {
    "Expert": 96,
    "Hard": 84,
    "Medium": 72,
    "Easy": 60,
}

#: Rock Band MIDI instrument track name -> Clone Hero ``.chart`` track suffix.
INSTRUMENT_TRACK_SUFFIX: Final[dict[str, str]] = {
    "PART GUITAR": "Single",
    "PART RHYTHM": "Rhythm",
    "PART BASS": "DoubleBass",
    "PART KEYS": "Keyboard",
}

#: Human readable instrument name -> suffix used by ``.chart`` track sections.
INSTRUMENT_SUFFIX: Final[dict[str, str]] = {
    "guitar": "Single",
    "single": "Single",
    "rhythm": "Rhythm",
    "bass": "DoubleBass",
    "doublebass": "DoubleBass",
    "keys": "Keyboard",
    "keyboard": "Keyboard",
}

_TEMPO_TRACK_NAMES: Final[frozenset[str]] = frozenset({"TEMPO TRACK", "TEMPO"})
_DEFAULT_RESOLUTION: Final[int] = 480
_US_PER_MINUTE: Final[float] = 60_000_000.0


@dataclass(frozen=True)
class RawMidiNote:
    """Absolute-tick MIDI note extracted from an instrument track.

    The raw pitch is preserved (unlike :class:`ChartNote`) so callers can inspect
    the original encoding before the difficulty offset is resolved.
    """

    tick: int
    pitch: int
    duration_ticks: int
    velocity: int


class MidiChartParser:
    """Parse ``notes.mid`` files into the same domain model used by ``.chart`` files."""

    @staticmethod
    def _track_name(track: MidiTrack) -> str:
        """Return the upper-cased track name, or an empty string when absent."""
        for msg in track:
            if msg.type == "track_name":
                return str(msg.name).strip().upper()
        return ""

    @staticmethod
    def _iter_absolute_messages(track: MidiTrack) -> Iterator[tuple[int, mido.Message]]:
        """Yield ``(absolute_tick, message)`` pairs for a delta-time MIDI track."""
        tick = 0
        for msg in track:
            tick += msg.time
            yield tick, msg

    def _select_tempo_tracks(self, mid: MidiFile) -> list[MidiTrack]:
        """Return the dedicated TEMPO TRACK when present, otherwise every track."""
        tempo_tracks = [t for t in mid.tracks if self._track_name(t) in _TEMPO_TRACK_NAMES]
        return tempo_tracks if tempo_tracks else list(mid.tracks)

    def parse_file(
        self,
        file_path: Path,
    ) -> tuple[TempoMap, dict[str, SongTrack], dict[str, str]]:
        """Read and parse a MIDI file from the filesystem.

        Args:
            file_path: Path to a ``.mid``/``.midi`` file.

        Returns:
            Tuple of ``(tempo_map, tracks, metadata)``.  ``tracks`` keys follow the
            ``.chart`` naming convention (e.g. ``ExpertSingle``).

        Raises:
            FileNotFoundError: If ``file_path`` does not exist.
        """
        return self.parse_midi(MidiFile(str(file_path)))

    def parse_midi(
        self,
        mid: MidiFile,
    ) -> tuple[TempoMap, dict[str, SongTrack], dict[str, str]]:
        """Parse an already loaded :class:`mido.MidiFile`.

        Args:
            mid: A ``mido`` MIDI file object.

        Returns:
            Tuple of ``(tempo_map, tracks, metadata)``.
        """
        resolution = int(mid.ticks_per_beat) or _DEFAULT_RESOLUTION
        tempo_map = self._parse_tempo_map(mid, resolution)
        tracks: dict[str, SongTrack] = {}

        for track in mid.tracks:
            instrument = INSTRUMENT_TRACK_SUFFIX.get(self._track_name(track))
            if instrument is None:
                continue

            raw_notes = self._extract_raw_notes(track)
            for difficulty, base_pitch in DIFFICULTY_PITCH_BASE.items():
                song_track = self._build_song_track(
                    name=f"{difficulty}{instrument}",
                    raw_notes=raw_notes,
                    base_pitch=base_pitch,
                )
                tracks[song_track.name] = song_track

        track_names = [name for name in (self._track_name(t) for t in mid.tracks) if name]
        metadata = {
            "MidiFormat": str(mid.type),
            "Resolution": str(resolution),
            "TrackCount": str(len(mid.tracks)),
            "TrackNames": ",".join(track_names),
        }
        return tempo_map, tracks, metadata

    def _parse_tempo_map(self, mid: MidiFile, resolution: int) -> TempoMap:
        """Collect ``set_tempo`` and ``time_signature`` meta events into a TempoMap."""
        bpm_by_tick: dict[int, float] = {}
        ts_by_tick: dict[int, TimeSignature] = {}

        for track in self._select_tempo_tracks(mid):
            for tick, msg in self._iter_absolute_messages(track):
                if msg.type == "set_tempo":
                    tempo_us = int(msg.tempo)
                    if tempo_us > 0:
                        bpm_by_tick[tick] = round(_US_PER_MINUTE / tempo_us, 6)
                elif msg.type == "time_signature":
                    numerator = int(msg.numerator)
                    denominator = int(msg.denominator)
                    if numerator > 0 and denominator > 0:
                        ts_by_tick[tick] = TimeSignature(
                            tick=tick,
                            numerator=numerator,
                            denominator=denominator,
                        )

        bpm_changes = [BPMChange(tick=tick, bpm=bpm) for tick, bpm in sorted(bpm_by_tick.items())]
        time_signatures = [ts_by_tick[tick] for tick in sorted(ts_by_tick)]
        return TempoMap(
            resolution=resolution,
            bpm_changes=bpm_changes,
            time_signatures=time_signatures,
        )

    def _extract_raw_notes(self, track: MidiTrack) -> list[RawMidiNote]:
        """Pair note-on/note-off messages per pitch and compute sustain durations."""
        pending: dict[int, list[tuple[int, int]]] = defaultdict(list)
        notes: list[RawMidiNote] = []

        for tick, msg in self._iter_absolute_messages(track):
            if msg.type == "note_on" and msg.velocity > 0:
                pending[msg.note].append((tick, int(msg.velocity)))
            elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
                fifo = pending.get(msg.note)
                if not fifo:
                    continue
                on_tick, velocity = fifo.pop(0)
                notes.append(
                    RawMidiNote(
                        tick=on_tick,
                        pitch=int(msg.note),
                        duration_ticks=max(0, tick - on_tick),
                        velocity=velocity,
                    )
                )

        # Unclosed notes (missing note-off) are emitted as zero-length events.
        for pitch, fifo in pending.items():
            for on_tick, velocity in fifo:
                notes.append(
                    RawMidiNote(
                        tick=on_tick,
                        pitch=pitch,
                        duration_ticks=0,
                        velocity=velocity,
                    )
                )

        notes.sort(key=lambda n: (n.tick, n.pitch))
        return notes

    def _build_song_track(
        self,
        name: str,
        raw_notes: list[RawMidiNote],
        base_pitch: int,
    ) -> SongTrack:
        """Project raw MIDI notes of one difficulty into a :class:`SongTrack`."""
        chart_notes: dict[tuple[int, int], ChartNote] = {}
        star_power: list[StarPowerPhrase] = []

        for raw in raw_notes:
            if raw.pitch == STAR_POWER_NOTE:
                star_power.append(StarPowerPhrase(tick=raw.tick, length=raw.duration_ticks))
                continue

            fret = self._pitch_to_fret(raw.pitch, base_pitch)
            if fret is None:
                continue

            key = (raw.tick, int(fret))
            existing = chart_notes.get(key)
            if existing is not None:
                # Duplicate encodings: keep the longest sustain.
                existing.sustain_length = max(existing.sustain_length, raw.duration_ticks)
                continue

            chart_notes[key] = ChartNote(
                tick=raw.tick,
                fret=fret,
                sustain_length=raw.duration_ticks,
            )

        notes = sorted(chart_notes.values())
        return SongTrack(name=name, notes=notes, star_power=sorted(star_power, key=lambda s: s.tick))

    @staticmethod
    def _pitch_to_fret(pitch: int, base_pitch: int) -> FretType | None:
        """Translate a Rock Band MIDI note number into a :class:`FretType`."""
        offset = pitch - base_pitch
        if 0 <= offset <= 4:
            return FretType(offset)
        if offset == 5:
            return FretType.HOPO_FORCE
        if offset == 6:
            return FretType.STRUM_FORCE
        if offset == 7:
            return FretType.OPEN
        return None
