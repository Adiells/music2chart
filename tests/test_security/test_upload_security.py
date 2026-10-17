"""Tests for upload security, streaming size limits, magic bytes, and audio duration checks."""

from __future__ import annotations

import io
import wave
from pathlib import Path
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.requests import Request

from config.settings import get_settings
from src.api.app import app
from src.api.routes import limiter, task_manager
from src.utils.security import (
    detect_audio_format,
    get_client_ip,
    probe_audio_duration,
    validate_audio_file,
    validate_audio_magic_bytes,
)


@pytest.fixture(autouse=True)
def clean_tasks():
    """Ensure clean task manager state for every test."""
    task_manager.clear()
    limiter.reset()
    yield
    task_manager.clear()
    limiter.reset()


@pytest.fixture
def valid_wav_bytes() -> bytes:
    """Generate minimal valid 44.1kHz mono WAV file bytes."""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(44100)
        wf.writeframes(b"\x00\x00" * 4410)  # 100ms of silence
    return buffer.getvalue()


@pytest.mark.asyncio
async def test_upload_streaming_rejects_oversized_file(valid_wav_bytes: bytes):
    """Verify that uploading a file larger than MAX_UPLOAD_SIZE_BYTES returns HTTP 413."""
    settings = get_settings()
    # Temporarily set MAX_UPLOAD_SIZE_BYTES to a small threshold for testing
    original_limit = settings.MAX_UPLOAD_SIZE_BYTES
    try:
        settings.MAX_UPLOAD_SIZE_BYTES = 500  # 500 bytes limit
        oversized_data = valid_wav_bytes + b"\x00" * 1024  # > 500 bytes

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            files = {"file": ("oversized.wav", oversized_data, "audio/wav")}
            res = await client.post("/api/v1/chart/generate", files=files)
            assert res.status_code == 413
            assert "exceeds maximum allowed size" in res.json()["detail"].lower()
    finally:
        settings.MAX_UPLOAD_SIZE_BYTES = original_limit


@pytest.mark.asyncio
async def test_content_length_rejects_oversized_request_before_streaming(valid_wav_bytes: bytes):
    """Reject a request declared over the limit before reading the uploaded file."""
    settings = get_settings()
    original_limit = settings.MAX_UPLOAD_SIZE_BYTES
    try:
        settings.MAX_UPLOAD_SIZE_BYTES = 500
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            files = {"file": ("small.wav", valid_wav_bytes, "audio/wav")}
            response = await client.post(
                "/api/v1/chart/generate", files=files, headers={"Content-Length": "501"}
            )
        assert response.status_code == 413
        assert "exceeds maximum allowed size" in response.json()["detail"].lower()
    finally:
        settings.MAX_UPLOAD_SIZE_BYTES = original_limit


@pytest.mark.asyncio
async def test_upload_rejects_text_file_renamed_to_mp3():
    """Verify that text files disguised as MP3 are rejected with HTTP 400 Bad Request."""
    fake_audio = b"This is a plaintext script or exploit payload pretending to be an audio track."

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"file": ("malicious.mp3", fake_audio, "audio/mpeg")}
        res = await client.post("/api/v1/chart/generate", files=files)
        assert res.status_code == 400, res.text
        assert "signature does not match" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_upload_rejects_empty_file():
    """Verify that empty uploads return HTTP 400 Bad Request."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"file": ("empty.wav", b"", "audio/wav")}
        res = await client.post("/api/v1/chart/generate", files=files)
        assert res.status_code == 400
        assert "empty" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_upload_rejects_excessive_duration(valid_wav_bytes: bytes):
    """Verify that audio exceeding MAX_AUDIO_DURATION_SECONDS returns HTTP 400."""
    settings = get_settings()
    original_duration_limit = settings.MAX_AUDIO_DURATION_SECONDS
    try:
        settings.MAX_AUDIO_DURATION_SECONDS = 0.05  # 50ms limit, while valid_wav_bytes is 100ms
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            files = {"file": ("long_audio.wav", valid_wav_bytes, "audio/wav")}
            res = await client.post("/api/v1/chart/generate", files=files)
            assert res.status_code == 400
            assert "exceeds maximum allowed limit" in res.json()["detail"].lower()
    finally:
        settings.MAX_AUDIO_DURATION_SECONDS = original_duration_limit


@pytest.mark.asyncio
async def test_upload_saves_decoupled_safe_filename(valid_wav_bytes: bytes):
    """Verify that uploaded files are saved with safe decoupled filenames on disk."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"file": ("dangerous; rm -rf /; song.wav", valid_wav_bytes, "audio/wav")}
        with patch("src.api.routes.run_pipeline_task") as mock_pipeline:
            res = await client.post("/api/v1/chart/generate", files=files)
            assert res.status_code == 202
            task_id = res.json()["task_id"]
            assert bool(task_id) is True

            # Verify that the path passed to run_pipeline_task ends with audio_input.wav
            assert mock_pipeline.called
            call_kwargs = mock_pipeline.call_args[1]
            saved_audio_path = call_kwargs["audio_path"]
            assert saved_audio_path.name == "audio_input.wav"
            assert saved_audio_path.exists()

            # Clean up test upload
            saved_audio_path.unlink(missing_ok=True)
            saved_audio_path.parent.rmdir()


def test_magic_bytes_detection():
    """Verify format detection and magic byte verification across audio formats."""
    # MP3 ID3 tag
    assert detect_audio_format(b"ID3\x04\x00\x00") == "mp3"
    assert validate_audio_magic_bytes(b"ID3\x04\x00\x00", "mp3") is True
    # MP3 frame sync
    assert detect_audio_format(b"\xff\xfb\x90\x00") == "mp3"
    assert validate_audio_magic_bytes(b"\xff\xfb\x90\x00", "mp3") is True
    # WAV RIFF
    wav_header = b"RIFF\x24\x00\x00\x00WAVEfmt "
    assert detect_audio_format(wav_header) == "wav"
    assert validate_audio_magic_bytes(wav_header, "wav") is True
    # OGG
    assert detect_audio_format(b"OggS\x00\x02\x00") == "ogg"
    assert validate_audio_magic_bytes(b"OggS\x00\x02\x00", "ogg") is True
    # FLAC
    assert detect_audio_format(b"fLaC\x00\x00\x00") == "flac"
    assert validate_audio_magic_bytes(b"fLaC\x00\x00\x00", "flac") is True
    # Non-audio / HTML
    assert detect_audio_format(b"<!DOCTYPE html>") is None
    assert validate_audio_magic_bytes(b"<!DOCTYPE html>") is False


def test_get_client_ip_uses_forwarded_header_precedence():
    """Use the first forwarded address, then supported proxy headers, then the peer."""
    def request(headers: list[tuple[bytes, bytes]]) -> Request:
        return Request(
            {
                "type": "http",
                "http_version": "1.1",
                "method": "GET",
                "scheme": "http",
                "path": "/",
                "raw_path": b"/",
                "query_string": b"",
                "headers": headers,
                "client": ("127.0.0.1", 1234),
                "server": ("test", 80),
            }
        )

    assert get_client_ip(
        request([(b"x-forwarded-for", b"198.51.100.3, 10.0.0.1")])
    ) == "198.51.100.3"
    assert get_client_ip(request([(b"cf-connecting-ip", b"198.51.100.4")])) == "198.51.100.4"
    assert get_client_ip(request([(b"x-real-ip", b"198.51.100.5")])) == "198.51.100.5"
    assert get_client_ip(request([])) == "127.0.0.1"


def test_probe_audio_duration_and_validation(tmp_path: Path, valid_wav_bytes: bytes):
    """Verify probe_audio_duration and validate_audio_file functionality."""
    wav_file = tmp_path / "sample.wav"
    wav_file.write_bytes(valid_wav_bytes)

    duration = probe_audio_duration(wav_file)
    assert 0.09 <= duration <= 0.11

    # Validate audio file succeeds within threshold
    validated_dur = validate_audio_file(wav_file, max_duration_seconds=10.0)
    assert 0.09 <= validated_dur <= 0.11

    # Fails if duration limit is exceeded
    with pytest.raises(ValueError, match="exceeds maximum allowed limit"):
        validate_audio_file(wav_file, max_duration_seconds=0.05)

    # Fails if corrupted or invalid signature
    fake_file = tmp_path / "fake.wav"
    fake_file.write_bytes(b"RIFFjunk")
    with pytest.raises(ValueError):
        validate_audio_file(fake_file, max_duration_seconds=10.0)
