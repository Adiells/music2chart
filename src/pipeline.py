"""Full orchestration pipeline integrating audio processing, game design, and serialization."""

from __future__ import annotations

import logging
import re
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf

from config.settings import Settings, get_settings
from src.api.schemas import PRESET_CONFIGS, ChartPreset
from src.audio_processing.harmonic_filter import HarmonicFilter
from src.audio_processing.pitch_transcriber import PitchTranscriber
from src.audio_processing.separator import AudioSeparator
from src.audio_processing.tempo_tracker import TempoTracker
from src.game_design.chord_builder import ChordBuilder
from src.game_design.hopo_engine import HopoEngine
from src.game_design.pitch_to_fret import PitchToFretMapper
from src.game_design.quantizer import NoteQuantizer
from src.game_design.star_power_generator import StarPowerGenerator
from src.game_design.sustain_processor import SustainProcessor
from src.models import SongTrack
from src.serialization.chart_writer import ChartWriter
from src.serialization.ini_writer import IniWriter
from src.serialization.sng_packer import SngPacker

logger = logging.getLogger(__name__)


def _sanitize_filename(name: str) -> str:
    """Sanitize song title or artist for filesystem paths."""
    sanitized = re.sub(r'[\\/*?:"<>|]', "_", name).strip()
    return sanitized if sanitized else "song"


class Music2ChartPipeline:
    """Full end-to-end pipeline orchestrator for music2chart.

    Coordinates all 10 stages from raw audio down to playable Clone Hero
    .chart files and .sng binary containers.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        tempo_tracker: TempoTracker | None = None,
        separator: AudioSeparator | None = None,
        transcriber: PitchTranscriber | None = None,
        harmonic_filter: HarmonicFilter | None = None,
        quantizer: NoteQuantizer | None = None,
        pitch_mapper: PitchToFretMapper | None = None,
        chord_builder: ChordBuilder | None = None,
        hopo_engine: HopoEngine | None = None,
        sustain_processor: SustainProcessor | None = None,
        star_power_generator: StarPowerGenerator | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.tempo_tracker = tempo_tracker or TempoTracker(
            resolution=self.settings.DEFAULT_RESOLUTION
        )
        self.separator = separator or AudioSeparator(
            model_name=self.settings.DEMUCS_MODEL_NAME,
            device=self.settings.DEVICE,
            fallback_to_mono_mix=True,
        )
        self.transcriber = transcriber or PitchTranscriber(
            onset_threshold=self.settings.BASIC_PITCH_ONSET_THRESHOLD,
            frame_threshold=self.settings.BASIC_PITCH_FRAME_THRESHOLD,
            min_note_len=self.settings.BASIC_PITCH_MIN_NOTE_LENGTH,
        )
        self.harmonic_filter = harmonic_filter or HarmonicFilter()
        self.quantizer = quantizer or NoteQuantizer(
            resolution=self.settings.DEFAULT_RESOLUTION,
            chord_fusion_window_s=NoteQuantizer.DEFAULT_CHORD_FUSION_WINDOW_S,
            strict_snap=True,
        )
        self.pitch_mapper = pitch_mapper or PitchToFretMapper(
            disable_open_notes=True,
            motif_similarity_threshold=0.75,
        )
        self.chord_builder = chord_builder or ChordBuilder(
            max_frets=2,
            open_note_precedence=False,
            collapse_fast_runs=True,
            fast_run_tick_threshold=48,
        )
        self.hopo_engine = hopo_engine or HopoEngine()
        self.sustain_processor = sustain_processor or SustainProcessor()
        self.star_power_generator = star_power_generator or StarPowerGenerator()

    def _load_audio(self, audio_path: Path) -> tuple[np.ndarray, int]:
        """Load audio file as numpy array and sample rate."""
        try:
            data, sr = sf.read(str(audio_path))
            return data, sr
        except Exception as exc:
            logger.warning("soundfile failed to load %s: %s; trying librosa", audio_path, exc)
            import librosa

            data, sr = librosa.load(str(audio_path), sr=None, mono=False)
            if data.ndim == 2:
                # librosa shape is (channels, samples), transpose to (samples, channels)
                data = data.T
            return data, int(sr)

    def _write_audio_stream(
        self,
        audio_path: Path,
        audio_data: np.ndarray,
        sample_rate: int,
        destination_path: Path,
    ) -> Path:
        """Write or encode audio as song.ogg for Clone Hero."""
        destination_path.parent.mkdir(parents=True, exist_ok=True)

        # 1. If source audio is already OGG, simply copy
        if audio_path.suffix.lower() == ".ogg" and audio_path.exists():
            shutil.copy2(audio_path, destination_path)
            return destination_path

        # 2. Prefer encoding via FFmpeg (safe against libsndfile C-level SIGSEGV)
        import subprocess

        try:
            cmd = [
                "ffmpeg",
                "-y",
                "-i",
                str(audio_path),
                "-c:a",
                "libvorbis",
                "-q:a",
                "5",
                str(destination_path),
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            if destination_path.exists() and destination_path.stat().st_size > 0:
                return destination_path
        except (subprocess.SubprocessError, FileNotFoundError) as exc:
            logger.warning("FFmpeg OGG encoding unavailable or failed: %s. Trying fallback.", exc)

        # 3. Fallback: soundfile with guaranteed C-contiguous float32 array
        try:
            contiguous_data = np.ascontiguousarray(audio_data, dtype=np.float32)
            sf.write(str(destination_path), contiguous_data, sample_rate, format="OGG")
            if destination_path.exists() and destination_path.stat().st_size > 0:
                return destination_path
        except Exception as exc:
            logger.warning("soundfile OGG write failed: %s. Copying source.", exc)

        # 4. Ultimate fallback: copy original audio file
        shutil.copy2(audio_path, destination_path)
        return destination_path

    def process_song(
        self,
        audio_path: Path | str,
        song_name: str,
        artist: str,
        output_format: str = "both",
        output_dir: Path | str | None = None,
        progress_callback: Callable[[float, str], Any] | None = None,
        max_frets: int = 2,
        hopo_threshold: int | None = None,
        disable_open_notes: bool = True,
        collapse_fast_runs: bool | None = None,
        consistent_patterns: bool | None = None,
        motif_similarity_threshold: float | None = None,
        difficulty: int = 6,
        genre: str = "rock",
        preset: str | None = None,
        creativity: float | None = None,
        min_amplitude: float | None = None,
        min_sustain_ticks: int | None = None,
        release_margin: int | None = None,
        chord_fusion_window_s: float | None = None,
        bpm_scale: float | None = None,
        auto_calibrate_bpm: bool | None = None,
        merge_sustained_notes: bool | None = None,
    ) -> dict[str, Path]:
        """Execute the full 10-step pipeline with configurable playability parameters.

        Args:
            audio_path: Path to input audio waveform file.
            song_name: Name of the song.
            artist: Artist name.
            output_format: 'chart', 'sng', or 'both'.
            output_dir: Optional destination directory. If None, derived from settings.
            progress_callback: Optional callback receiving (progress_ratio: float, step_name: str).
            max_frets: Maximum simultaneous frets allowed in a chord (1-3, default 2).
            hopo_threshold: Tick distance threshold for natural HOPO trigger.
            disable_open_notes: Suppress open notes on lead guitar, mapping to Green (default True).
            collapse_fast_runs: Collapse simultaneous notes in fast sixteenth-note runs.
            consistent_patterns: Enforce consistent motif anchoring on repeating musical riffs.
            motif_similarity_threshold: Fuzzy motif sequence alignment similarity threshold (0.5 to 1.0, default 0.75).
            difficulty: Guitar track difficulty rating scalar (1-6, default 6).
            genre: Musical genre string (default 'rock').
            preset: Optional preset configuration profile name ('the_best', 'standard', 'strict_rhythm', 'dynamic_solo').
            creativity: Fret mapping creativity factor (0.0 to 1.0).
            min_amplitude: Minimum amplitude confidence threshold to filter ghost notes.
            min_sustain_ticks: Minimum note duration in ticks to render sustain tails.
            release_margin: Margin in ticks subtracted before subsequent note release.
            chord_fusion_window_s: Sliding window in seconds to fuse simultaneous string rolls.
            bpm_scale: Tempo multiplier factor.
            auto_calibrate_bpm: Whether to fold excessive tempos (> 160 BPM) by halving.
            merge_sustained_notes: Merge re-triggered ringing notes on same pitch into holds.

        Returns:
            Dictionary mapping artifact identifiers ('chart', 'ini', 'audio', 'sng', 'package_dir')
            to their corresponding generated Paths on disk.
        """
        src_audio = Path(audio_path).resolve()
        if not src_audio.exists():
            raise FileNotFoundError(f"Audio file not found: {src_audio}")

        safe_song = _sanitize_filename(song_name)
        safe_artist = _sanitize_filename(artist)

        # Resolve preset defaults when preset is specified, allowing explicit arguments to override them
        clean_preset_str = (
            preset.lower().strip()
            if isinstance(preset, str)
            else (
                preset.value
                if isinstance(preset, ChartPreset)
                else (str(preset).lower() if preset else None)
            )
        )
        if clean_preset_str in ("string", "none", "null", ""):
            clean_preset_str = None

        if clean_preset_str is not None:
            preset_cfg = PRESET_CONFIGS.get(clean_preset_str, PRESET_CONFIGS["standard"])
        else:
            preset_cfg = {}

        eff_creativity = creativity if creativity is not None else preset_cfg.get("creativity", 0.5)
        eff_hopo_threshold = (
            hopo_threshold if hopo_threshold is not None else preset_cfg.get("hopo_threshold", 65)
        )
        eff_min_sustain_ticks = (
            min_sustain_ticks
            if min_sustain_ticks is not None
            else preset_cfg.get("min_sustain_ticks", 72)
        )
        eff_release_margin = (
            release_margin if release_margin is not None else preset_cfg.get("release_margin", 24)
        )
        raw_min_amp = (
            min_amplitude if min_amplitude is not None else preset_cfg.get("min_amplitude", 0.0)
        )
        eff_min_amplitude = min(0.5, raw_min_amp) if raw_min_amp > 0.5 else raw_min_amp
        eff_chord_fusion_window_s = (
            chord_fusion_window_s
            if chord_fusion_window_s is not None
            else preset_cfg.get("chord_fusion_window_s", 0.035)
        )
        eff_collapse_fast_runs = (
            collapse_fast_runs
            if collapse_fast_runs is not None
            else preset_cfg.get("collapse_fast_runs", True)
        )
        eff_consistent_patterns = (
            consistent_patterns
            if consistent_patterns is not None
            else preset_cfg.get("consistent_patterns", True)
        )
        eff_motif_similarity_threshold = (
            motif_similarity_threshold
            if motif_similarity_threshold is not None
            else preset_cfg.get("motif_similarity_threshold", 0.75)
        )
        eff_auto_calibrate_bpm = (
            auto_calibrate_bpm
            if auto_calibrate_bpm is not None
            else preset_cfg.get("auto_calibrate_bpm", True)
        )
        eff_bpm_scale = bpm_scale if bpm_scale is not None else preset_cfg.get("bpm_scale", 1.0)
        eff_merge_sustained_notes = (
            merge_sustained_notes
            if merge_sustained_notes is not None
            else preset_cfg.get("merge_sustained_notes", False)
        )

        def report(progress: float, step: str) -> None:
            if progress_callback is not None:
                try:
                    progress_callback(progress, step)
                except Exception as exc:
                    logger.debug("Progress callback failed: %s", exc)

        # Establish working directory structure
        if output_dir is not None:
            pkg_dir = Path(output_dir).resolve()
        else:
            pkg_dir = (self.settings.OUTPUT_DIR / f"{safe_artist} - {safe_song}").resolve()

        pkg_dir.mkdir(parents=True, exist_ok=True)
        stems_dir = (self.settings.STEMS_DIR / f"{safe_artist} - {safe_song}").resolve()

        # ------------------------------------------------------------------
        # Step 1: Load audio & generate TempoMap
        # ------------------------------------------------------------------
        report(0.1, "Analyzing tempo and beat grid")
        audio_data, sample_rate = self._load_audio(src_audio)
        tempo_map = self.tempo_tracker.build_tempo_map(
            audio_data,
            sample_rate,
            auto_calibrate_bpm=eff_auto_calibrate_bpm,
            bpm_scale=eff_bpm_scale,
        )

        # ------------------------------------------------------------------
        # Step 2: Stem Separation (isolating electric guitar)
        # ------------------------------------------------------------------
        report(0.25, "Separating audio stems")
        stems = self.separator.separate(src_audio, stems_dir)
        guitar_path = (
            stems.guitar_path if stems.guitar_path and stems.guitar_path.exists() else src_audio
        )

        # Release PyTorch cached VRAM before loading transcription model
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass

        # ------------------------------------------------------------------
        # Step 3: Polyphonic Pitch Transcription
        # ------------------------------------------------------------------
        report(0.45, "Transcribing notes via Spotify Basic Pitch")
        raw_notes = self.transcriber.transcribe(guitar_path)

        # ------------------------------------------------------------------
        # Step 4: Harmonic Filter (suppress distortion overtones)
        # ------------------------------------------------------------------
        report(0.55, "Filtering harmonic distortion overtones")
        filtered_notes = self.harmonic_filter.filter_overtones(raw_notes)

        # ------------------------------------------------------------------
        # Step 5: Quantization & 192 PPQ Snapping
        # ------------------------------------------------------------------
        report(0.65, "Snapping notes to 192 PPQ musical grid")
        quantizer = NoteQuantizer(
            resolution=self.quantizer.resolution,
            subdivisions=self.quantizer.subdivisions,
            tolerance_ticks=self.quantizer.tolerance_ticks,
            chord_fusion_window_s=eff_chord_fusion_window_s,
            min_spacing_ticks=self.quantizer.min_spacing_ticks,
            strict_snap=self.quantizer.strict_snap,
            min_amplitude=eff_min_amplitude,
            merge_retrigger=eff_merge_sustained_notes,
        )
        quantized_notes = quantizer.quantize(filtered_notes, tempo_map)

        # ------------------------------------------------------------------
        # Step 6: Pitch-to-5-Frets Dynamic Projection
        # ------------------------------------------------------------------
        report(0.75, "Mapping pitch tessitura to 5 frets")
        pitch_mapper = PitchToFretMapper(
            window_ticks=self.pitch_mapper.window_ticks,
            max_jump=self.pitch_mapper.max_jump,
            rapid_interval=self.pitch_mapper.rapid_interval,
            open_threshold=self.pitch_mapper.open_threshold,
            disable_open_notes=disable_open_notes,
            consistent_patterns=eff_consistent_patterns,
            min_pattern_len=self.pitch_mapper.min_pattern_len,
            creativity=eff_creativity,
            motif_similarity_threshold=eff_motif_similarity_threshold,
        )
        fret_mapped_notes = pitch_mapper.map_notes(quantized_notes)

        # ------------------------------------------------------------------
        # Step 7: Ergonomic Chord Formation
        # ------------------------------------------------------------------
        report(0.8, "Forming ergonomic guitar chords")
        chord_builder = ChordBuilder(
            max_frets=max_frets,
            allow_wide_triads=self.chord_builder.allow_wide_triads,
            open_note_precedence=self.chord_builder.open_note_precedence,
            collapse_fast_runs=eff_collapse_fast_runs,
            fast_run_tick_threshold=self.chord_builder.fast_run_tick_threshold,
            allow_triads_on_accents=self.chord_builder.allow_triads_on_accents,
            min_triad_sustain_ticks=self.chord_builder.min_triad_sustain_ticks,
            accent_tick_interval=self.chord_builder.accent_tick_interval,
        )
        chord_notes = chord_builder.build_chords(fret_mapped_notes)

        # ------------------------------------------------------------------
        # Step 8: HOPO, Sustain Processing & Star Power Generation
        # ------------------------------------------------------------------
        report(0.85, "Calculating HOPO tags, sustains, and Star Power")
        durations_map = {qn.tick: qn.duration_ticks for qn in quantized_notes}
        sustain_processor = SustainProcessor(
            min_sustain_ticks=eff_min_sustain_ticks,
            release_margin=eff_release_margin,
        )
        sustained_notes = sustain_processor.process(chord_notes, durations=durations_map)
        hopo_engine = HopoEngine(
            hopo_threshold=eff_hopo_threshold,
            run_threshold=self.hopo_engine.run_threshold,
        )
        hopo_notes = hopo_engine.process(sustained_notes)
        star_power_phrases = self.star_power_generator.generate(hopo_notes)
        final_notes = hopo_engine.add_force_modifiers(sustained_notes)

        # ------------------------------------------------------------------
        # Step 9: Serialize notes.chart, song.ini, and song.ogg
        # ------------------------------------------------------------------
        report(0.9, "Serializing notes.chart and metadata")
        track = SongTrack(name="ExpertSingle", notes=final_notes, star_power=star_power_phrases)
        tracks = {"ExpertSingle": track}

        chart_path = pkg_dir / "notes.chart"
        safe_genre = (
            genre.strip() if genre and genre.strip().lower() not in ("string", "") else "rock"
        )
        ChartWriter.write(
            song_name=song_name,
            artist=artist,
            tempo_map=tempo_map,
            tracks=tracks,
            output_path=chart_path,
            difficulty=difficulty,
            genre=safe_genre,
            music_stream="song.ogg",
        )

        ini_path = pkg_dir / "song.ini"
        IniWriter.write(
            output_path=ini_path,
            name=song_name,
            artist=artist,
            charter="music2chart AI",
            genre=safe_genre,
            diff_guitar=difficulty,
        )

        song_ogg_path = pkg_dir / "song.ogg"
        self._write_audio_stream(src_audio, audio_data, sample_rate, song_ogg_path)

        result_paths: dict[str, Path] = {
            "chart": chart_path,
            "ini": ini_path,
            "audio": song_ogg_path,
            "package_dir": pkg_dir,
        }

        # ------------------------------------------------------------------
        # Step 10: Package into .sng container if requested
        # ------------------------------------------------------------------
        if output_format.lower() in ("sng", "both"):
            report(0.95, "Packaging .sng binary container")
            sng_path = pkg_dir.parent / f"{safe_artist} - {safe_song}.sng"
            SngPacker.pack_dir(input_dir=pkg_dir, output_sng_path=sng_path)
            result_paths["sng"] = sng_path

        # Clean up intermediate stems if enabled to prevent disk exhaustion
        if self.settings.ENABLE_AUTO_STEM_CLEANUP:
            if stems_dir.exists():
                try:
                    shutil.rmtree(stems_dir, ignore_errors=True)
                    logger.info("Cleaned up intermediate stems directory: %s", stems_dir)
                except Exception as exc:
                    logger.debug("Failed to remove stems directory %s: %s", stems_dir, exc)

        report(1.0, "Completed successfully")
        return result_paths
