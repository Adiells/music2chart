"""Polyphonic audio-to-MIDI transcription engine using Spotify Basic Pitch."""

import logging
from pathlib import Path
from typing import Any

from config.settings import get_settings
from src.models import NoteEvent

logger = logging.getLogger(__name__)


class PitchTranscriber:
    """Polyphonic pitch transcription wrapper around Spotify Basic Pitch."""

    def __init__(
        self,
        onset_threshold: float | None = None,
        frame_threshold: float | None = None,
        min_note_len: float | None = None,
    ) -> None:
        settings = get_settings()
        self.onset_threshold = (
            onset_threshold if onset_threshold is not None else settings.BASIC_PITCH_ONSET_THRESHOLD
        )
        self.frame_threshold = (
            frame_threshold if frame_threshold is not None else settings.BASIC_PITCH_FRAME_THRESHOLD
        )
        self.min_note_len = (
            min_note_len if min_note_len is not None else settings.BASIC_PITCH_MIN_NOTE_LENGTH
        )
        self._predict_fn: Any = None

    def _configure_tf_gpu(self) -> None:
        """Enable dynamic GPU memory growth to prevent TensorFlow from pre-allocating all VRAM."""
        try:
            import tensorflow as tf

            gpus = tf.config.list_physical_devices("GPU")
            if gpus:
                for gpu in gpus:
                    try:
                        tf.config.experimental.set_memory_growth(gpu, True)
                        logger.info("TensorFlow GPU memory growth enabled for %s", gpu)
                    except RuntimeError as exc:
                        # Memory growth must be configured before physical devices are initialized
                        logger.debug(
                            "TensorFlow GPU memory growth already set or deferred: %s", exc
                        )
        except Exception as exc:
            logger.debug("TensorFlow GPU configuration check skipped: %s", exc)

    def _get_predict_fn(self) -> Any:
        """Lazy loader for basic_pitch inference predict function."""
        if self._predict_fn is None:
            self._configure_tf_gpu()
            try:
                from basic_pitch.inference import predict

                self._predict_fn = predict
            except ImportError:
                logger.warning("basic-pitch module is not installed or failed to import.")
                self._predict_fn = None
        return self._predict_fn

    def transcribe(
        self,
        audio_path: Path,
        onset_threshold: float | None = None,
        frame_threshold: float | None = None,
        min_note_len: float | None = None,
    ) -> list[NoteEvent]:
        """Transcribe polyphonic audio into a sorted list of NoteEvent instances."""
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file for transcription not found: {audio_path}")

        on_thresh = onset_threshold if onset_threshold is not None else self.onset_threshold
        frame_thresh = frame_threshold if frame_threshold is not None else self.frame_threshold
        min_len = min_note_len if min_note_len is not None else self.min_note_len

        predict_fn = self._get_predict_fn()
        if predict_fn is None:
            raise RuntimeError(
                "Basic Pitch inference engine is not available. Please install basic-pitch."
            )

        # Call basic-pitch inference
        _model_output, _midi_data, note_events_raw = predict_fn(
            audio_path,
            onset_threshold=on_thresh,
            frame_threshold=frame_thresh,
            minimum_note_length=min_len,
        )

        notes: list[NoteEvent] = []
        for raw in note_events_raw:
            # raw is tuple: (start_time_s, end_time_s, pitch_midi, amplitude, pitch_bends)
            start_time = float(raw[0])
            end_time = float(raw[1])
            pitch = int(round(raw[2]))
            amplitude = float(raw[3])

            # Clamp and ensure strictly valid boundaries
            start_time = max(0.0, start_time)
            if end_time <= start_time:
                end_time = start_time + 0.01
            pitch = max(0, min(127, pitch))
            amplitude = max(0.0, min(1.0, amplitude))

            notes.append(
                NoteEvent(
                    start_time=start_time,
                    end_time=end_time,
                    pitch=pitch,
                    amplitude=amplitude,
                )
            )

        # Sort chronologically by start_time ascending, then by pitch ascending
        notes.sort(key=lambda n: (n.start_time, n.pitch))
        return notes
