"""Clone Hero .chart text format serializer."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from src.models import (
    FretType,
    SongTrack,
    TempoMap,
)


class ChartWriter:
    """Serializes in-memory song tracks, tempo maps, and metadata to .chart format."""

    @classmethod
    def generate_chart_string(
        cls,
        song_name: str,
        artist: str,
        tempo_map: TempoMap,
        tracks: Mapping[str, SongTrack],
        charter: str = "music2chart AI",
        offset: int = 0,
        resolution: int | None = None,
        player2: str = "bass",
        difficulty: int = 0,
        preview_start: int = 0,
        preview_end: int = 0,
        genre: str = "rock",
        media_type: str = "cd",
        music_stream: str = "song.ogg",
        events: Sequence[tuple[int, str]] | None = None,
        extra_song_properties: Mapping[str, Any] | None = None,
    ) -> str:
        """Generate string representation of standard .chart file.

        Args:
            song_name: Name of the song.
            artist: Performing artist.
            tempo_map: TempoMap holding resolution, BPM changes, and time signatures.
            tracks: Mapping of track name (e.g. "ExpertSingle") to SongTrack.
            charter: Name of charter / transcription credit.
            offset: Audio offset in milliseconds (default 0).
            resolution: Resolution (PPQ), defaults to tempo_map.resolution.
            player2: Player 2 instrument identifier (default "bass").
            difficulty: Track difficulty scalar (default 0).
            preview_start: Audio preview start time in seconds.
            preview_end: Audio preview end time in seconds.
            genre: Song musical genre.
            media_type: Media type source (default "cd").
            music_stream: Audio stream filename (default "song.ogg").
            events: List of (tick, section_name) events.
            extra_song_properties: Additional custom [Song] properties.

        Returns:
            Standardized UTF-8 formatted .chart content string with UNIX newlines.
        """
        res = resolution if resolution is not None else tempo_map.resolution

        lines: list[str] = []

        # -------------------------------------------------------------------
        # 1. [Song] Section
        # -------------------------------------------------------------------
        lines.append("[Song]")
        lines.append("{")
        lines.append(f'  Name = "{song_name}"')
        lines.append(f'  Artist = "{artist}"')
        lines.append(f'  Charter = "{charter}"')
        lines.append(f"  Offset = {offset}")
        lines.append(f"  Resolution = {res}")
        lines.append(f"  Player2 = {player2}")
        lines.append(f"  Difficulty = {difficulty}")
        lines.append(f"  PreviewStart = {preview_start}")
        lines.append(f"  PreviewEnd = {preview_end}")
        lines.append(f'  Genre = "{genre}"')
        lines.append(f'  MediaType = "{media_type}"')
        lines.append(f'  MusicStream = "{music_stream}"')

        if extra_song_properties:
            for k, v in extra_song_properties.items():
                if isinstance(v, (int, float)):
                    lines.append(f"  {k} = {v}")
                else:
                    lines.append(f'  {k} = "{v}"')

        lines.append("}")

        # -------------------------------------------------------------------
        # 2. [SyncTrack] Section
        # -------------------------------------------------------------------
        lines.append("[SyncTrack]")
        lines.append("{")

        # Gather all SyncTrack items: (tick, sort_priority, formatted_line)
        # Priority 0 for TimeSignature, Priority 1 for BPMChange
        sync_items: list[tuple[int, int, str]] = []

        for ts in tempo_map.time_signatures:
            if ts.denominator == 4:
                sync_items.append((ts.tick, 0, f"  {ts.tick} = TS {ts.numerator}"))
            else:
                exponent = int(round(math.log2(ts.denominator)))
                sync_items.append((ts.tick, 0, f"  {ts.tick} = TS {ts.numerator} {exponent}"))

        for bpm_change in tempo_map.bpm_changes:
            milli_bpm = int(round(bpm_change.bpm * 1000.0))
            sync_items.append((bpm_change.tick, 1, f"  {bpm_change.tick} = B {milli_bpm}"))

        # Sort chronologically by tick, then priority
        sync_items.sort(key=lambda item: (item[0], item[1]))
        for _, _, line in sync_items:
            lines.append(line)

        lines.append("}")

        # -------------------------------------------------------------------
        # 3. [Events] Section
        # -------------------------------------------------------------------
        lines.append("[Events]")
        lines.append("{")

        if events is not None and len(events) > 0:
            sorted_events = sorted(events, key=lambda ev: ev[0])
            for tick, ev_name in sorted_events:
                clean_name = ev_name.strip('"')
                lines.append(f'  {tick} = E "{clean_name}"')
        else:
            lines.append('  0 = E "section Intro"')

        lines.append("}")

        # -------------------------------------------------------------------
        # 4. Instrument Track Sections (e.g., [ExpertSingle])
        # -------------------------------------------------------------------
        for track_name, track in tracks.items():
            lines.append(f"[{track_name}]")
            lines.append("{")

            # Collect all track events: (tick, priority, formatted_line)
            # Priority 0 for Note events, Priority 1 for Star Power phrases
            track_items: list[tuple[int, int, int, str]] = []

            # Deduplicate notes by (tick, fret_int), enforcing sustain 0 for modifiers
            # and resolving conflicting modifiers (STRUM_FORCE takes precedence over HOPO_FORCE)
            notes_by_tick_fret: dict[tuple[int, int], int] = {}
            for note in track.notes:
                fret_int = int(note.fret)
                # Modifier notes (HOPO_FORCE=5, STRUM_FORCE=6) must strictly have sustain_length = 0
                if fret_int in (int(FretType.HOPO_FORCE), int(FretType.STRUM_FORCE)):
                    sus = 0
                else:
                    sus = max(0, note.sustain_length)

                key = (note.tick, fret_int)
                if key in notes_by_tick_fret:
                    notes_by_tick_fret[key] = max(notes_by_tick_fret[key], sus)
                else:
                    notes_by_tick_fret[key] = sus

            # Resolve conflicting modifiers (both HOPO_FORCE and STRUM_FORCE at same tick)
            ticks_with_strum = {
                t for (t, f) in notes_by_tick_fret if f == int(FretType.STRUM_FORCE)
            }

            for (tick, fret_int), sus in notes_by_tick_fret.items():
                if fret_int == int(FretType.HOPO_FORCE) and tick in ticks_with_strum:
                    continue
                track_items.append(
                    (
                        tick,
                        0,
                        fret_int,
                        f"  {tick} = N {fret_int} {sus}",
                    )
                )

            # Deduplicate Star Power phrases: (tick, length)
            seen_sp: set[tuple[int, int]] = set()
            for sp in track.star_power:
                sp_key = (sp.tick, sp.length)
                if sp_key in seen_sp:
                    continue
                seen_sp.add(sp_key)
                track_items.append(
                    (
                        sp.tick,
                        1,
                        0,
                        f"  {sp.tick} = S 2 {sp.length}",
                    )
                )

            # Sort by tick ascending, then priority (notes first), then fret int
            track_items.sort(key=lambda item: (item[0], item[1], item[2]))
            for _, _, _, formatted in track_items:
                lines.append(formatted)

            lines.append("}")

        return "\n".join(lines) + "\n"

    @classmethod
    def write(
        cls,
        song_name: str,
        artist: str,
        tempo_map: TempoMap,
        tracks: Mapping[str, SongTrack],
        output_path: Path | str,
        charter: str = "music2chart AI",
        offset: int = 0,
        resolution: int | None = None,
        player2: str = "bass",
        difficulty: int = 0,
        preview_start: int = 0,
        preview_end: int = 0,
        genre: str = "rock",
        media_type: str = "cd",
        music_stream: str = "song.ogg",
        events: Sequence[tuple[int, str]] | None = None,
        extra_song_properties: Mapping[str, Any] | None = None,
    ) -> Path:
        """Serialize chart content and write to output file on disk.

        Args:
            song_name: Song title.
            artist: Song artist.
            tempo_map: Rhythmic TempoMap.
            tracks: Mapping of difficulty track names to SongTrack objects.
            output_path: File system path to write notes.chart.
            charter: Transcription author.
            offset: Song offset in milliseconds.
            resolution: Resolution (PPQ).
            player2: Player 2 instrument.
            difficulty: Overall difficulty index.
            preview_start: Preview start in seconds.
            preview_end: Preview end in seconds.
            genre: Musical genre.
            media_type: Media source.
            music_stream: Associated audio stream file.
            events: Practice section events.
            extra_song_properties: Extra metadata pairs.

        Returns:
            The Path written to.
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        content = cls.generate_chart_string(
            song_name=song_name,
            artist=artist,
            tempo_map=tempo_map,
            tracks=tracks,
            charter=charter,
            offset=offset,
            resolution=resolution,
            player2=player2,
            difficulty=difficulty,
            preview_start=preview_start,
            preview_end=preview_end,
            genre=genre,
            media_type=media_type,
            music_stream=music_stream,
            events=events,
            extra_song_properties=extra_song_properties,
        )
        path.write_text(content, encoding="utf-8", newline="\n")
        return path
