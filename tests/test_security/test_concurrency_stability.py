"""Tests for concurrency limits, queue saturation (HTTP 429), TTL task cleanup, and production error suppression."""

from __future__ import annotations

import io
import time
import wave
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from config.settings import get_settings
from src.api.app import app
from src.api.routes import TaskStatus, task_manager


@pytest.fixture(autouse=True)
def clean_tasks():
    """Ensure clean task manager state for every test."""
    task_manager.clear()
    yield
    task_manager.clear()


@pytest.fixture
def dummy_wav_bytes() -> bytes:
    """Generate minimal valid WAV file bytes."""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(44100)
        wf.writeframes(b"\x00\x00" * 4410)
    return buffer.getvalue()


@pytest.mark.asyncio
async def test_queue_saturation_returns_429(dummy_wav_bytes: bytes):
    """Verify that saturating the task queue returns HTTP 429 Too Many Requests."""
    settings = get_settings()
    orig_concurrent = settings.MAX_CONCURRENT_TASKS
    orig_queue = settings.TASK_QUEUE_CAPACITY

    try:
        settings.MAX_CONCURRENT_TASKS = 1
        settings.TASK_QUEUE_CAPACITY = 2  # Total capacity: 1 + 2 = 3

        # Simulate 3 active tasks currently pending/processing
        task_manager.create_task("task-1")
        task_manager.update_task("task-1", status=TaskStatus.PROCESSING)
        task_manager.create_task("task-2")
        task_manager.update_task("task-2", status=TaskStatus.PENDING)
        task_manager.create_task("task-3")
        task_manager.update_task("task-3", status=TaskStatus.PENDING)

        assert task_manager.get_active_task_count() == 3

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            files = {"file": ("song.wav", dummy_wav_bytes, "audio/wav")}
            res = await client.post("/api/v1/chart/generate", files=files)
            assert res.status_code == 429
            assert "full capacity" in res.json()["detail"].lower()
    finally:
        settings.MAX_CONCURRENT_TASKS = orig_concurrent
        settings.TASK_QUEUE_CAPACITY = orig_queue


def test_task_manager_cleanup_expired_tasks(tmp_path: Path):
    """Verify that TaskManager.cleanup_expired_tasks purges expired tasks and deletes their disk files."""
    settings = get_settings()

    # Create dummy upload and output files for task
    task_id = "expired-task-123"
    upload_task_dir = settings.UPLOAD_DIR / task_id
    upload_task_dir.mkdir(parents=True, exist_ok=True)
    (upload_task_dir / "audio_input.wav").write_bytes(b"dummy")

    output_task_dir = settings.OUTPUT_DIR / task_id
    output_task_dir.mkdir(parents=True, exist_ok=True)
    (output_task_dir / "notes.chart").write_text("chart", encoding="utf-8")

    rec = task_manager.create_task(task_id, song_name="Old", artist="Band")
    # Simulate age of 3 hours ago (10800 seconds)
    rec.updated_at = time.time() - 10800

    # Also create a recent task that should NOT be cleaned
    active_id = "recent-task-456"
    task_manager.create_task(active_id)

    # Purge tasks older than 7200 seconds (2 hours)
    expired = task_manager.cleanup_expired_tasks(ttl_seconds=7200)

    assert task_id in expired
    assert active_id not in expired
    assert task_manager.get_task(task_id) is None
    assert task_manager.get_task(active_id) is not None

    # Verify disk files were removed
    assert not upload_task_dir.exists()
    assert not output_task_dir.exists()


@pytest.mark.asyncio
async def test_error_sanitization_in_production():
    """Verify that internal traceback details are masked when APP_ENV is production."""
    settings = get_settings()
    orig_env = settings.APP_ENV
    task_id = "traceback-task"

    try:
        # Development mode: detailed error is returned
        settings.APP_ENV = "development"
        task_manager.create_task(task_id)
        raw_error = "Traceback (most recent call last):\n  File 'pipeline.py', line 99\nZeroDivisionError: division by zero"
        task_manager.set_failed(task_id, error=raw_error)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res_dev = await client.get(f"/api/v1/chart/status/{task_id}")
            assert res_dev.status_code == 200
            assert "Traceback" in res_dev.json()["error"]

        # Production mode: sanitized error is returned
        settings.APP_ENV = "production"
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res_prod = await client.get(f"/api/v1/chart/status/{task_id}")
            assert res_prod.status_code == 200
            error_returned = res_prod.json()["error"]
            assert "Traceback" not in error_returned
            assert "Pipeline processing failed" in error_returned
    finally:
        settings.APP_ENV = orig_env


@pytest.mark.asyncio
async def test_security_headers_present():
    """Verify that HTTP response includes all mandatory security headers."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/health")
        assert res.status_code == 200
        headers = res.headers
        assert headers.get("X-Content-Type-Options") == "nosniff"
        assert headers.get("X-Frame-Options") == "DENY"
        assert headers.get("X-XSS-Protection") == "1; mode=block"
        assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
