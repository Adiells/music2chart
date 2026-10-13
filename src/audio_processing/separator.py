"""Audio stem separation using Meta Demucs with lazy loading and fallback mode."""

import logging
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from src.models import StemCollection

logger = logging.getLogger(__name__)

STANDARD_STEMS = ("drums.wav", "bass.wav", "other.wav", "guitar.wav")


class AudioSeparator:
    """Wrapper around Meta Demucs for separating music into drums, bass, guitar, and other stems."""

    def __init__(
        self,
        model_name: str = "htdemucs",
        device: str = "cpu",
        fallback_to_mono_mix: bool = False,
    ) -> None:
        self.model_name = model_name
        self.device = device
        self.fallback_to_mono_mix = fallback_to_mono_mix
        self._model: Any = None

    def _get_model(self) -> Any:
        """Lazy initialization of Demucs model singleton."""
        if self._model is None:
            try:
                import demucs.api

                self._model = demucs.api.Separator(model=self.model_name, device=self.device)
            except Exception as exc:
                logger.warning("Demucs Python API could not be loaded: %s", exc)
                self._model = None
        return self._model

    def _fallback_separate(self, audio_path: Path, output_dir: Path) -> StemCollection:
        """Fallback mode: duplicate the original audio into stem slots for CPU/testing environments."""
        output_dir.mkdir(parents=True, exist_ok=True)
        stem_paths: dict[str, Path] = {}

        for stem_filename in STANDARD_STEMS:
            stem_name = stem_filename.replace(".wav", "")
            target_path = output_dir / stem_filename
            shutil.copy2(audio_path, target_path)
            stem_paths[stem_name] = target_path

        return StemCollection(
            mix_path=audio_path,
            guitar_path=stem_paths.get("guitar"),
            bass_path=stem_paths.get("bass"),
            drums_path=stem_paths.get("drums"),
            other_path=stem_paths.get("other"),
        )

    def _run_demucs_cli(self, audio_path: Path, output_dir: Path) -> bool:
        """Run separation via demucs CLI."""
        cmd = [
            sys.executable,
            "-m",
            "demucs.separate",
            "-n",
            self.model_name,
            "-o",
            str(output_dir),
            "-d",
            self.device,
            str(audio_path),
        ]
        try:
            res = subprocess.run(cmd, check=True, capture_output=True, text=True)
            logger.info("Demucs CLI completed: %s", res.stdout)
            return True
        except (subprocess.SubprocessError, FileNotFoundError) as exc:
            logger.warning("Demucs CLI execution failed: %s", exc)
            return False

    def separate(self, audio_path: Path, output_dir: Path) -> StemCollection:
        """Separate an audio file into 4 standard stems (guitar, bass, drums, other)."""
        if not audio_path.exists():
            raise FileNotFoundError(f"Input audio file not found: {audio_path}")

        output_dir.mkdir(parents=True, exist_ok=True)

        if self.fallback_to_mono_mix:
            return self._fallback_separate(audio_path, output_dir)

        # Attempt Demucs Python API
        model = self._get_model()
        if model is not None:
            try:
                # Use Demucs API
                _origin, separated = model.separate_audio_file(audio_path)
                stem_paths: dict[str, Path] = {}
                for stem_name, stem_tensor in separated.items():
                    target_file = output_dir / f"{stem_name}.wav"
                    model.save_audio(stem_tensor, target_file)
                    stem_paths[stem_name] = target_file

                return StemCollection(
                    mix_path=audio_path,
                    guitar_path=stem_paths.get("guitar"),
                    bass_path=stem_paths.get("bass"),
                    drums_path=stem_paths.get("drums"),
                    other_path=stem_paths.get("other"),
                )
            except Exception as exc:
                logger.warning("Demucs API execution failed (%s), falling back to CLI...", exc)

        # Try Demucs CLI
        cli_success = self._run_demucs_cli(audio_path, output_dir)
        if cli_success:
            # Demucs CLI nests outputs under <output_dir>/<model_name>/<track_name>/
            track_name = audio_path.stem
            nested_dir = output_dir / self.model_name / track_name
            source_dir = nested_dir if nested_dir.exists() else output_dir

            stem_paths = {}
            for stem_filename in STANDARD_STEMS:
                src_stem = source_dir / stem_filename
                dest_stem = output_dir / stem_filename
                if src_stem.exists():
                    if src_stem != dest_stem:
                        shutil.copy2(src_stem, dest_stem)
                    stem_paths[stem_filename.replace(".wav", "")] = dest_stem

            if "guitar" in stem_paths:
                return StemCollection(
                    mix_path=audio_path,
                    guitar_path=stem_paths.get("guitar"),
                    bass_path=stem_paths.get("bass"),
                    drums_path=stem_paths.get("drums"),
                    other_path=stem_paths.get("other"),
                )

        logger.info("Falling back to audio replication for stems.")
        return self._fallback_separate(audio_path, output_dir)
