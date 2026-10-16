"""FastAPI routes for chart generation, polling, and downloading."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import shutil
import threading
import time
import zipfile
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse, StreamingResponse

from config.settings import get_settings
from src.api.schemas import (
    DownloadFormat,
    GenerateResponse,
    OutputFormat,
    TaskStatus,
    TaskStatusResponse,
)
from src.utils.security import probe_audio_duration, validate_audio_magic_bytes

if TYPE_CHECKING:
    from src.pipeline import Music2ChartPipeline

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".mp3", ".wav", ".ogg", ".flac"}


@dataclass
class TaskRecord:
    """Internal representation of a chart generation task."""

    task_id: str
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0
    stage: str = "Queued"
    error: str | None = None
    output_files: dict[str, Path] = field(default_factory=dict)
    song_name: str = ""
    artist: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


class TaskManager:
    """Thread-safe in-memory task repository."""

    def __init__(self) -> None:
        self._tasks: dict[str, TaskRecord] = {}
        self._lock = threading.Lock()

    def create_task(self, task_id: str, song_name: str = "", artist: str = "") -> TaskRecord:
        record = TaskRecord(
            task_id=task_id,
            song_name=song_name,
            artist=artist,
            stage="Queued",
        )
        with self._lock:
            self._tasks[task_id] = record
        return record

    def get_task(self, task_id: str) -> TaskRecord | None:
        with self._lock:
            return self._tasks.get(task_id)

    def update_task(
        self,
        task_id: str,
        status: TaskStatus | None = None,
        progress: float | None = None,
        stage: str | None = None,
        error: str | None = None,
    ) -> None:
        with self._lock:
            record = self._tasks.get(task_id)
            if record is not None:
                if status is not None:
                    record.status = status
                if progress is not None:
                    record.progress = max(0.0, min(1.0, progress))
                if stage is not None:
                    record.stage = stage
                if error is not None:
                    record.error = error
                record.updated_at = time.time()

    def set_completed(self, task_id: str, output_files: dict[str, Path]) -> None:
        with self._lock:
            record = self._tasks.get(task_id)
            if record is not None:
                record.status = TaskStatus.COMPLETED
                record.progress = 1.0
                record.stage = "Completed successfully"
                record.output_files = output_files
                record.updated_at = time.time()

    def set_failed(self, task_id: str, error: str) -> None:
        with self._lock:
            record = self._tasks.get(task_id)
            if record is not None:
                record.status = TaskStatus.FAILED
                record.stage = "Failed"
                record.error = error
                record.updated_at = time.time()

    def get_active_task_count(self) -> int:
        """Return total count of tasks currently PENDING or PROCESSING."""
        with self._lock:
            return sum(
                1
                for task in self._tasks.values()
                if task.status in (TaskStatus.PENDING, TaskStatus.PROCESSING)
            )

    def get_pending_task_count(self) -> int:
        """Return count of tasks currently waiting in queue (PENDING)."""
        with self._lock:
            return sum(1 for task in self._tasks.values() if task.status == TaskStatus.PENDING)

    def cleanup_expired_tasks(self, ttl_seconds: float = 7200.0) -> list[str]:
        """Remove tasks older than ttl_seconds and delete their files from disk."""
        now = time.time()
        expired_ids: list[str] = []
        records_to_clean: list[TaskRecord] = []

        with self._lock:
            for task_id, record in list(self._tasks.items()):
                if (now - record.updated_at) > ttl_seconds:
                    expired_ids.append(task_id)
                    records_to_clean.append(record)
                    del self._tasks[task_id]

        settings = get_settings()
        for record in records_to_clean:
            tid = record.task_id
            # 1. Delete upload task dir
            upload_task_dir = settings.UPLOAD_DIR / tid
            if upload_task_dir.exists():
                shutil.rmtree(upload_task_dir, ignore_errors=True)

            # 2. Delete stems task dir
            stems_task_dir = settings.STEMS_DIR / tid
            if stems_task_dir.exists():
                shutil.rmtree(stems_task_dir, ignore_errors=True)

            # 3. Delete output task dir
            output_task_dir = settings.OUTPUT_DIR / tid
            if output_task_dir.exists():
                shutil.rmtree(output_task_dir, ignore_errors=True)

            # 4. Clean recorded output files
            for p in record.output_files.values():
                path = Path(p)
                try:
                    if path.is_file():
                        path.unlink(missing_ok=True)
                    elif path.is_dir():
                        shutil.rmtree(path, ignore_errors=True)
                except Exception:
                    pass

        return expired_ids

    def clear(self) -> None:
        """Clear all tasks (primarily for unit test isolation)."""
        with self._lock:
            self._tasks.clear()


task_manager = TaskManager()

_semaphore_lock = threading.Lock()
_pipeline_semaphore: threading.Semaphore | None = None
_current_max_concurrent: int = 0


def get_pipeline_semaphore() -> threading.Semaphore:
    """Return the global pipeline concurrency semaphore."""
    global _pipeline_semaphore, _current_max_concurrent
    settings = get_settings()
    with _semaphore_lock:
        if _pipeline_semaphore is None or _current_max_concurrent != settings.MAX_CONCURRENT_TASKS:
            _current_max_concurrent = settings.MAX_CONCURRENT_TASKS
            _pipeline_semaphore = threading.Semaphore(_current_max_concurrent)
        return _pipeline_semaphore


def _format_terminal_progress_bar(progress: float, stage: str, length: int = 20) -> str:
    """Format visual ASCII progress bar for server console logs."""
    clamped = max(0.0, min(1.0, progress))
    filled = int(length * clamped)
    bar = "█" * filled + "░" * (length - filled)
    percent = int(clamped * 100)
    return f"[{bar}] {percent:>3}% - {stage}"


def _sanitize_string(val: str) -> str:
    """Sanitize string for filenames."""
    return re.sub(r'[\\/*?:"<>|]', "_", val).strip() or "track"


def _create_zip_archive(package_dir: Path, zip_output_path: Path) -> Path:
    """Create a ZIP archive containing all files from the package directory."""
    zip_output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_output_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file_path in package_dir.rglob("*"):
            if file_path.is_file() and not file_path.name.endswith(".zip"):
                arcname = file_path.relative_to(package_dir).as_posix()
                zipf.write(file_path, arcname=arcname)
    return zip_output_path


def run_pipeline_task(
    task_id: str,
    audio_path: Path,
    song_name: str,
    artist: str,
    output_format: str,
    pipeline: Music2ChartPipeline | None = None,
    max_frets: int = 2,
    hopo_threshold: int | None = None,
    disable_open_notes: bool = True,
    collapse_fast_runs: bool | None = None,
    consistent_patterns: bool | None = None,
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
) -> None:
    """Execute pipeline in worker threadpool with real-time progress updates and concurrency control."""
    sem = get_pipeline_semaphore()
    with sem:
        initial_stage = "Initializing pipeline"
        task_manager.update_task(
            task_id,
            status=TaskStatus.PROCESSING,
            progress=0.05,
            stage=initial_stage,
        )
        logger.info("Task %s %s", task_id[:8], _format_terminal_progress_bar(0.05, initial_stage))
        if pipeline is not None:
            pipe = pipeline
        else:
            from src.pipeline import Music2ChartPipeline

            pipe = Music2ChartPipeline()

        def on_progress(p: float, step: str) -> None:
            task_manager.update_task(task_id, progress=p, stage=step)
            logger.info("Task %s %s", task_id[:8], _format_terminal_progress_bar(p, step))

        try:
            results = pipe.process_song(
                audio_path=audio_path,
                song_name=song_name,
                artist=artist,
                output_format=output_format,
                progress_callback=on_progress,
                max_frets=max_frets,
                hopo_threshold=hopo_threshold,
                disable_open_notes=disable_open_notes,
                collapse_fast_runs=collapse_fast_runs,
                consistent_patterns=consistent_patterns,
                difficulty=difficulty,
                genre=genre,
                preset=preset,
                creativity=creativity,
                min_amplitude=min_amplitude,
                min_sustain_ticks=min_sustain_ticks,
                release_margin=release_margin,
                chord_fusion_window_s=chord_fusion_window_s,
                bpm_scale=bpm_scale,
                auto_calibrate_bpm=auto_calibrate_bpm,
                merge_sustained_notes=merge_sustained_notes,
            )
            task_manager.set_completed(task_id, output_files=results)
            logger.info(
                "Task %s %s",
                task_id[:8],
                _format_terminal_progress_bar(1.0, "Completed successfully"),
            )
        except Exception as exc:
            logger.exception("Pipeline execution failed for task %s: %s", task_id, exc)
            task_manager.set_failed(task_id, error=str(exc))
        finally:
            settings = get_settings()
            if settings.ENABLE_AUTO_STEM_CLEANUP:
                task_stems = settings.STEMS_DIR / task_id
                if task_stems.exists():
                    shutil.rmtree(task_stems, ignore_errors=True)


router = APIRouter(prefix="/api/v1/chart", tags=["Chart Generation"])
preview_router = APIRouter(tags=["Chart Preview"])


@router.post(
    "/generate",
    response_model=GenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit an audio file for automated Clone Hero chart generation",
)
async def generate_chart(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Audio file (MP3, WAV, FLAC, OGG)"),
    song_name: str | None = Form(default=None, description="Optional title of the song"),
    artist: str | None = Form(default=None, description="Optional artist name"),
    output_format: str = Form(
        default=OutputFormat.BOTH.value,
        description="Packaging format: 'chart', 'sng', or 'both'",
    ),
    max_frets: int = Form(default=2, ge=1, le=3, description="Maximum simultaneous frets (1-3)"),
    hopo_threshold: int | None = Form(
        default=None, ge=0, le=192, description="HOPO trigger tick distance threshold"
    ),
    disable_open_notes: bool = Form(default=True, description="Suppress open notes on lead guitar"),
    collapse_fast_runs: bool | None = Form(
        default=None, description="Collapse chords in fast sixteenth-note runs"
    ),
    consistent_patterns: bool | None = Form(
        default=None, description="Enforce identical fret sequences on repeating musical riffs"
    ),
    difficulty: int = Form(
        default=6, ge=1, le=6, description="Guitar track difficulty level (1-6)"
    ),
    genre: str = Form(default="rock", description="Song genre"),
    preset: str | None = Form(default=None, description="Preset configuration name"),
    creativity: float | None = Form(
        default=None, ge=0.0, le=1.0, description="Creativity / solo expression factor (0.0 to 1.0)"
    ),
    min_amplitude: float | None = Form(
        default=None, ge=0.0, le=1.0, description="Minimum amplitude confidence threshold"
    ),
    min_sustain_ticks: int | None = Form(
        default=None, ge=0, le=768, description="Minimum duration in ticks to render sustain tail"
    ),
    release_margin: int | None = Form(
        default=None, ge=0, le=96, description="Release margin ticks before subsequent note"
    ),
    chord_fusion_window_s: float | None = Form(
        default=None, ge=0.005, le=0.100, description="Acoustic chord fusion window in seconds"
    ),
    bpm_scale: float | None = Form(
        default=None, gt=0.0, le=2.0, description="Tempo multiplier / scroll speed scaler"
    ),
    auto_calibrate_bpm: bool | None = Form(
        default=None, description="Auto-halve excessive BPM (> 160.0) for comfortable scroll speed"
    ),
    merge_sustained_notes: bool | None = Form(
        default=None, description="Merge consecutive notes on same pitch into prolonged sustains"
    ),
) -> GenerateResponse:
    """Accept audio upload, validate extension, and schedule background chart generation."""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a valid filename.",
        )

    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported file format '{file_ext}'. Allowed formats: "
                f"{', '.join(sorted(ALLOWED_EXTENSIONS))}"
            ),
        )

    # Derive song title and artist if omitted (handling Swagger UI 'string' placeholders)
    base_stem = Path(file.filename).stem
    final_song = song_name.strip() if song_name and song_name.strip() else ""
    final_artist = artist.strip() if artist and artist.strip() else ""
    if final_song.lower() == "string":
        final_song = ""
    if final_artist.lower() == "string":
        final_artist = ""

    if not final_song or not final_artist:
        if " - " in base_stem:
            parsed_artist, parsed_song = base_stem.split(" - ", 1)
            final_artist = final_artist or parsed_artist.strip()
            final_song = final_song or parsed_song.strip()
        else:
            final_song = final_song or base_stem
            final_artist = final_artist or "Unknown Artist"

    # Sanitize preset, genre and amplitude against Swagger UI defaults
    clean_preset = preset.strip().lower() if preset and preset.strip() else None
    if clean_preset in ("string", "none", "null", ""):
        clean_preset = None

    clean_genre = genre.strip() if genre and genre.strip().lower() not in ("string", "") else "rock"
    clean_min_amplitude = min(0.5, min_amplitude) if min_amplitude is not None else None

    settings = get_settings()

    # 1. Check queue capacity before accepting upload
    active_tasks = task_manager.get_active_task_count()
    if active_tasks >= (settings.MAX_CONCURRENT_TASKS + settings.TASK_QUEUE_CAPACITY):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Server is at full capacity (queue limit of {settings.TASK_QUEUE_CAPACITY} reached). "
                "Please try again later."
            ),
        )

    import uuid

    task_id = str(uuid.uuid4())
    upload_dir = settings.UPLOAD_DIR / task_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    # Secure filename decoupling: avoid storing unvalidated user filenames directly
    destination = upload_dir / f"audio_input{file_ext}"

    # Stream upload in chunks with strict size limit enforcement
    max_upload_size = settings.MAX_UPLOAD_SIZE_BYTES
    chunk_size = 64 * 1024  # 64 KB
    total_bytes = 0
    header_bytes = bytearray()

    try:
        with open(destination, "wb") as f:
            while chunk := await file.read(chunk_size):
                total_bytes += len(chunk)
                if len(header_bytes) < 64:
                    header_bytes.extend(chunk[: 64 - len(header_bytes)])
                if total_bytes > max_upload_size:
                    f.close()
                    destination.unlink(missing_ok=True)
                    try:
                        upload_dir.rmdir()
                    except OSError:
                        pass
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=(
                            f"Uploaded file exceeds maximum allowed size of "
                            f"{max_upload_size // (1024 * 1024)}MB."
                        ),
                    )
                f.write(chunk)

        if total_bytes == 0:
            destination.unlink(missing_ok=True)
            try:
                upload_dir.rmdir()
            except OSError:
                pass
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded audio file is empty.",
            )
    except HTTPException:
        raise
    except Exception as exc:
        destination.unlink(missing_ok=True)
        try:
            upload_dir.rmdir()
        except OSError:
            pass
        logger.error("Failed to persist upload %s: %s", destination, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save uploaded file to disk.",
        ) from exc

    # 2. Inspect audio signature magic bytes
    if not validate_audio_magic_bytes(bytes(header_bytes)):
        destination.unlink(missing_ok=True)
        try:
            upload_dir.rmdir()
        except OSError:
            pass
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File signature does not match supported audio format '{file_ext}'.",
        )

    # 3. Pre-flight lightweight duration probe
    try:
        duration = probe_audio_duration(destination)
        if duration > settings.MAX_AUDIO_DURATION_SECONDS:
            destination.unlink(missing_ok=True)
            try:
                upload_dir.rmdir()
            except OSError:
                pass
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Audio duration ({duration:.1f}s) exceeds maximum allowed limit "
                    f"of {settings.MAX_AUDIO_DURATION_SECONDS:.0f}s (15 minutes)."
                ),
            )
    except HTTPException:
        raise
    except Exception as exc:
        destination.unlink(missing_ok=True)
        try:
            upload_dir.rmdir()
        except OSError:
            pass
        logger.warning("Audio duration probe failed for %s: %s", destination, exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded audio file could not be decoded or is corrupted.",
        ) from exc

    # Register task and queue background processing
    task_manager.create_task(task_id=task_id, song_name=final_song, artist=final_artist)
    background_tasks.add_task(
        run_pipeline_task,
        task_id=task_id,
        audio_path=destination,
        song_name=final_song,
        artist=final_artist,
        output_format=output_format,
        max_frets=max_frets,
        hopo_threshold=hopo_threshold,
        disable_open_notes=disable_open_notes,
        collapse_fast_runs=collapse_fast_runs,
        consistent_patterns=consistent_patterns,
        difficulty=difficulty,
        genre=clean_genre,
        preset=clean_preset,
        creativity=creativity,
        min_amplitude=clean_min_amplitude,
        min_sustain_ticks=min_sustain_ticks,
        release_margin=release_margin,
        chord_fusion_window_s=chord_fusion_window_s,
        bpm_scale=bpm_scale,
        auto_calibrate_bpm=auto_calibrate_bpm,
        merge_sustained_notes=merge_sustained_notes,
    )

    return GenerateResponse(
        task_id=task_id,
        status=TaskStatus.PENDING.value,
        message="Chart generation task queued successfully.",
    )


@router.get(
    "/status/{task_id}",
    response_model=TaskStatusResponse,
    summary="Query processing status and progress for a task",
)
async def get_task_status(task_id: str) -> TaskStatusResponse:
    """Retrieve current progress, lifecycle status, or error report for a task."""
    record = task_manager.get_task(task_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{task_id}' not found.",
        )

    res_files: dict[str, str] | None = None
    if record.status == TaskStatus.COMPLETED:
        res_files = {k: str(v) for k, v in record.output_files.items()}

    settings = get_settings()
    err_msg = record.error
    if err_msg and settings.APP_ENV.lower() == "production":
        err_msg = "Pipeline processing failed. Please check your audio file or try again."

    return TaskStatusResponse(
        task_id=record.task_id,
        status=record.status.value,
        progress=round(record.progress, 2),
        stage=record.stage,
        error=err_msg,
        result_files=res_files,
    )


@router.get(
    "/stream/{task_id}",
    summary="Stream real-time progress events for a task via Server-Sent Events (SSE)",
)
async def stream_task_progress(task_id: str) -> StreamingResponse:
    """Stream SSE events with progress updates and stage changes until task finishes."""
    record = task_manager.get_task(task_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{task_id}' not found.",
        )

    settings = get_settings()

    async def event_generator() -> AsyncGenerator[str, None]:
        last_progress = -1.0
        last_status = None
        last_stage = None

        while True:
            current = task_manager.get_task(task_id)
            if current is None:
                yield f"event: error\ndata: {json.dumps({'error': 'Task not found'})}\n\n"
                break

            # Send event when state changes
            if (
                current.progress != last_progress
                or current.status != last_status
                or current.stage != last_stage
            ):
                last_progress = current.progress
                last_status = current.status
                last_stage = current.stage

                err_msg = current.error
                if err_msg and settings.APP_ENV.lower() == "production":
                    err_msg = "Pipeline processing failed. Please check your audio file or try again."

                payload = {
                    "task_id": current.task_id,
                    "status": current.status.value,
                    "progress": round(current.progress, 2),
                    "stage": current.stage,
                    "error": err_msg,
                    "result_files": {k: str(v) for k, v in current.output_files.items()}
                    if current.status == TaskStatus.COMPLETED
                    else None,
                }
                yield f"data: {json.dumps(payload)}\n\n"

            if current.status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                break

            await asyncio.sleep(0.3)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/download/{task_id}",
    summary="Download generated chart artifacts (.sng, notes.chart, or .zip archive)",
)
async def download_chart(
    task_id: str,
    format: str = Query(
        default=DownloadFormat.SNG.value,
        description="Desired download format: 'sng', 'chart', or 'zip'",
    ),
) -> FileResponse:
    """Stream generated artifacts to the client."""
    record = task_manager.get_task(task_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{task_id}' not found.",
        )

    if record.status == TaskStatus.FAILED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Task failed: {record.error}",
        )

    if record.status != TaskStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Task is still processing (current status: {record.status.value}).",
        )

    fmt = format.lower().strip()
    safe_name = _sanitize_string(f"{record.artist} - {record.song_name}")

    if fmt == DownloadFormat.SNG.value:
        sng_path = record.output_files.get("sng")
        if sng_path and Path(sng_path).exists():
            return FileResponse(
                path=Path(sng_path),
                media_type="application/octet-stream",
                filename=f"{safe_name}.sng",
            )
        # If .sng was not requested at generate time, pack directory now
        pkg_dir = record.output_files.get("package_dir")
        if pkg_dir and Path(pkg_dir).exists():
            from src.serialization.sng_packer import SngPacker

            target_sng = Path(pkg_dir).parent / f"{safe_name}.sng"
            SngPacker.pack_dir(input_dir=pkg_dir, output_sng_path=target_sng)
            record.output_files["sng"] = target_sng
            return FileResponse(
                path=target_sng,
                media_type="application/octet-stream",
                filename=f"{safe_name}.sng",
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generated .sng file not found.",
        )

    if fmt == DownloadFormat.CHART.value:
        chart_path = record.output_files.get("chart")
        if chart_path and Path(chart_path).exists():
            return FileResponse(
                path=Path(chart_path),
                media_type="text/plain; charset=utf-8",
                filename="notes.chart",
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generated notes.chart file not found.",
        )

    if fmt == DownloadFormat.ZIP.value:
        pkg_dir = record.output_files.get("package_dir")
        if not pkg_dir or not Path(pkg_dir).exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chart package directory not found.",
            )
        zip_path = Path(pkg_dir).parent / f"{safe_name}.zip"
        _create_zip_archive(Path(pkg_dir), zip_path)
        return FileResponse(
            path=zip_path,
            media_type="application/zip",
            filename=f"{safe_name}.zip",
        )

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Invalid download format '{format}'. Supported formats: sng, chart, zip.",
    )


@router.get(
    "/preview/{task_id}/audio",
    summary="Stream or download preview audio for a completed task",
)
@preview_router.get(
    "/preview/{task_id}/audio",
    summary="Stream or download preview audio for a completed task",
)
async def preview_audio(task_id: str) -> FileResponse:
    """Return the 'song.ogg' audio file from the completed task directory as a streamable FileResponse."""
    record = task_manager.get_task(task_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{task_id}' not found.",
        )

    if record.status != TaskStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{task_id}' is not completed (current status: {record.status.value}).",
        )

    audio_path: Path | None = None
    if "audio" in record.output_files:
        candidate = Path(record.output_files["audio"])
        if candidate.is_file():
            audio_path = candidate

    if audio_path is None and "package_dir" in record.output_files:
        candidate = Path(record.output_files["package_dir"]) / "song.ogg"
        if candidate.is_file():
            audio_path = candidate

    if audio_path is None:
        settings = get_settings()
        candidate = settings.OUTPUT_DIR / task_id / "song.ogg"
        if candidate.is_file():
            audio_path = candidate

    if audio_path is None or not audio_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Preview audio file 'song.ogg' not found for task '{task_id}'.",
        )

    return FileResponse(
        path=audio_path,
        media_type="audio/ogg",
        filename="song.ogg",
        content_disposition_type="inline",
    )
