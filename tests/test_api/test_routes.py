"""Tests for REST API endpoints using httpx.AsyncClient."""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.app import app, create_app
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
    import wave

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(44100)
        wf.writeframes(b"\x00\x00" * 4410)  # 100ms of silence
    return buffer.getvalue()


@pytest.mark.asyncio
async def test_health_check():
    """Verify health probe returns status 200 and expected payload."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res1 = await client.get("/health")
        assert res1.status_code == 200
        data1 = res1.json()
        assert data1["status"] == "ok"
        assert data1["app_name"] == "music2chart"

        res2 = await client.get("/api/v1/health")
        assert res2.status_code == 200
        assert res2.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_generate_chart_success(dummy_wav_bytes: bytes):
    """Verify successful submission of audio file for chart generation."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"file": ("test_song.wav", dummy_wav_bytes, "audio/wav")}
        data = {
            "song_name": "Test Track",
            "artist": "Test Artist",
            "output_format": "both",
        }

        with patch("src.api.routes.run_pipeline_task"):
            response = await client.post("/api/v1/chart/generate", files=files, data=data)

        assert response.status_code == 202
        payload = response.json()
        assert "task_id" in payload
        assert payload["status"] == "PENDING"
        assert "queued successfully" in payload["message"].lower()

        task_id = payload["task_id"]
        record = task_manager.get_task(task_id)
        assert record is not None
        assert record.song_name == "Test Track"
        assert record.artist == "Test Artist"


@pytest.mark.asyncio
async def test_generate_chart_unsupported_format():
    """Verify rejection of files with invalid extensions."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"file": ("malicious.exe", b"binary content", "application/octet-stream")}
        response = await client.post("/api/v1/chart/generate", files=files)
        assert response.status_code == 400
        assert "Unsupported file format" in response.json()["detail"]


@pytest.mark.asyncio
async def test_generate_chart_empty_file():
    """Verify rejection of empty audio files."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"file": ("empty.wav", b"", "audio/wav")}
        response = await client.post("/api/v1/chart/generate", files=files)
        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_generate_chart_auto_derive_metadata(dummy_wav_bytes: bytes):
    """Verify artist and song title derivation from filename when omitted."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"file": ("Muse - Hysteria.mp3", dummy_wav_bytes, "audio/mpeg")}
        with patch("src.api.routes.run_pipeline_task"):
            response = await client.post("/api/v1/chart/generate", files=files)

        assert response.status_code == 202
        task_id = response.json()["task_id"]
        record = task_manager.get_task(task_id)
        assert record is not None
        assert record.artist == "Muse"
        assert record.song_name == "Hysteria"


@pytest.mark.asyncio
async def test_get_task_status_lifecycle():
    """Verify status polling reflects task state transitions."""
    task_id = "test-task-123"
    task_manager.create_task(task_id, song_name="Track", artist="Artist")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. PENDING
        res = await client.get(f"/api/v1/chart/status/{task_id}")
        assert res.status_code == 200
        assert res.json()["status"] == "PENDING"
        assert res.json()["progress"] == 0.0

        # 2. PROCESSING
        task_manager.update_task(task_id, status=TaskStatus.PROCESSING, progress=0.45)
        res = await client.get(f"/api/v1/chart/status/{task_id}")
        assert res.status_code == 200
        assert res.json()["status"] == "PROCESSING"
        assert res.json()["progress"] == 0.45

        # 3. COMPLETED
        task_manager.set_completed(task_id, output_files={"chart": Path("/tmp/notes.chart")})
        res = await client.get(f"/api/v1/chart/status/{task_id}")
        assert res.status_code == 200
        assert res.json()["status"] == "COMPLETED"
        assert res.json()["progress"] == 1.0
        assert "chart" in res.json()["result_files"]


@pytest.mark.asyncio
async def test_get_task_status_failed():
    """Verify failed status reporting with error message."""
    task_id = "fail-task-456"
    task_manager.create_task(task_id)
    task_manager.set_failed(task_id, error="Demucs memory error")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get(f"/api/v1/chart/status/{task_id}")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "FAILED"
        assert data["error"] == "Demucs memory error"


@pytest.mark.asyncio
async def test_get_task_status_not_found():
    """Verify 404 returned for unknown task IDs."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/chart/status/non-existent-uuid")
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_download_not_completed(tmp_path: Path):
    """Verify downloading pending or running tasks yields 409 Conflict."""
    task_id = "pending-download-task"
    task_manager.create_task(task_id)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get(f"/api/v1/chart/download/{task_id}?format=chart")
        assert res.status_code == 409
        assert "processing" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_download_artifacts(tmp_path: Path):
    """Verify download endpoint streams .chart, .sng, and .zip files."""
    task_id = "ready-download-task"
    task_manager.create_task(task_id, song_name="Rock Anthem", artist="The Rockers")

    # Prepare mock artifact files
    pkg_dir = tmp_path / "The Rockers - Rock Anthem"
    pkg_dir.mkdir(parents=True)
    chart_file = pkg_dir / "notes.chart"
    chart_file.write_text('[Song]\n{\n  Name = "Rock Anthem"\n}\n', encoding="utf-8")
    ini_file = pkg_dir / "song.ini"
    ini_file.write_text("[Song]\nname = Rock Anthem\n", encoding="utf-8")
    ogg_file = pkg_dir / "song.ogg"
    ogg_file.write_bytes(b"dummy ogg content")

    sng_file = tmp_path / "The Rockers - Rock Anthem.sng"
    sng_file.write_bytes(b"SNGPKG\x01\x00\x00\x00" + b"\x00" * 32)

    task_manager.set_completed(
        task_id,
        output_files={
            "chart": chart_file,
            "ini": ini_file,
            "audio": ogg_file,
            "sng": sng_file,
            "package_dir": pkg_dir,
        },
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Download .chart
        res_chart = await client.get(f"/api/v1/chart/download/{task_id}?format=chart")
        assert res_chart.status_code == 200
        assert "text/plain" in res_chart.headers["content-type"]
        assert b'Name = "Rock Anthem"' in res_chart.content

        # Download .sng
        res_sng = await client.get(f"/api/v1/chart/download/{task_id}?format=sng")
        assert res_sng.status_code == 200
        assert "application/octet-stream" in res_sng.headers["content-type"]
        assert res_sng.content.startswith(b"SNGPKG")

        # Download .zip
        res_zip = await client.get(f"/api/v1/chart/download/{task_id}?format=zip")
        assert res_zip.status_code == 200
        assert "application/zip" in res_zip.headers["content-type"]
        assert len(res_zip.content) > 0

        # Invalid format
        res_invalid = await client.get(f"/api/v1/chart/download/{task_id}?format=midi")
        assert res_invalid.status_code == 400


@pytest.mark.asyncio
async def test_cors_headers():
    """Verify CORS preflight and response headers are present."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.options(
            "/api/v1/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert res.status_code == 200
        assert res.headers.get("access-control-allow-origin") in ("*", "http://localhost:3000")


@pytest.mark.asyncio
async def test_serve_web_ui():
    """Verify root / serves the interactive web interface with the progress bar or React root."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/")
        assert res.status_code == 200
        assert "text/html" in res.headers["content-type"]
        body = res.text
        assert "music2chart" in body.lower()
        assert ('id="root"' in body) or ('id="progress-bar"' in body)


@pytest.mark.asyncio
async def test_task_status_tracks_stage():
    """Verify task status polling reports dynamic pipeline stage."""
    task_id = "test-stage-tracking"
    task_manager.create_task(task_id, song_name="Track", artist="Artist")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Initial queued state
        res0 = await client.get(f"/api/v1/chart/status/{task_id}")
        assert res0.json()["stage"] == "Queued"

        # Intermediate progress update with step name
        task_manager.update_task(
            task_id,
            status=TaskStatus.PROCESSING,
            progress=0.45,
            stage="Transcribing notes via Spotify Basic Pitch",
        )
        res1 = await client.get(f"/api/v1/chart/status/{task_id}")
        assert res1.json()["progress"] == 0.45
        assert res1.json()["stage"] == "Transcribing notes via Spotify Basic Pitch"

        # Completion state
        task_manager.set_completed(task_id, output_files={"sng": Path("/tmp/track.sng")})
        res2 = await client.get(f"/api/v1/chart/status/{task_id}")
        assert res2.json()["status"] == "COMPLETED"
        assert res2.json()["stage"] == "Completed successfully"


@pytest.mark.asyncio
async def test_stream_task_progress_sse():
    """Verify Server-Sent Events (SSE) stream emits real-time progress updates."""
    task_id = "test-sse-stream"
    task_manager.create_task(task_id, song_name="SSE Song", artist="SSE Artist")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Mark completed right away so the stream finishes
        task_manager.set_completed(task_id, output_files={"chart": Path("/tmp/notes.chart")})

        response = await client.get(f"/api/v1/chart/stream/{task_id}")
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        assert "data:" in response.text
        assert "COMPLETED" in response.text
        assert "Completed successfully" in response.text


@pytest.mark.asyncio
async def test_stream_task_progress_not_found():
    """Verify 404 returned when attempting to stream non-existent task."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/chart/stream/non-existent-task-id")
        assert res.status_code == 404


@pytest.mark.asyncio
async def test_generate_chart_with_fitting_parameters(dummy_wav_bytes: bytes):
    """Verify custom chart fitting parameters are parsed and passed to background task."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"file": ("speed_solo.wav", dummy_wav_bytes, "audio/wav")}
        data = {
            "song_name": "Speed Solo",
            "artist": "Guitar Master",
            "output_format": "sng",
            "max_frets": "1",
            "hopo_threshold": "96",
            "disable_open_notes": "false",
            "collapse_fast_runs": "false",
            "consistent_patterns": "true",
            "difficulty": "5",
            "genre": "heavy metal",
        }

        with patch("src.api.routes.run_pipeline_task") as mock_task:
            response = await client.post("/api/v1/chart/generate", files=files, data=data)

        assert response.status_code == 202
        payload = response.json()
        assert "task_id" in payload

        # Verify background task was queued with the fitting parameter overrides
        mock_task.assert_called_once()
        _, kwargs = mock_task.call_args
        assert kwargs["max_frets"] == 1
        assert kwargs["hopo_threshold"] == 96
        assert kwargs["disable_open_notes"] is False
        assert kwargs["collapse_fast_runs"] is False
        assert kwargs["consistent_patterns"] is True
        assert kwargs["difficulty"] == 5
        assert kwargs["genre"] == "heavy metal"


@pytest.mark.asyncio
async def test_generate_chart_fitting_parameter_validation_bounds(dummy_wav_bytes: bytes):
    """Verify 422 Unprocessable Entity when parameters violate validation constraints."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"file": ("solo.wav", dummy_wav_bytes, "audio/wav")}

        # max_frets > 3 should fail validation
        res_frets = await client.post(
            "/api/v1/chart/generate", files=files, data={"max_frets": "5"}
        )
        assert res_frets.status_code == 422

        # difficulty > 6 should fail validation
        res_diff = await client.post(
            "/api/v1/chart/generate", files=files, data={"difficulty": "8"}
        )
        assert res_diff.status_code == 422


def test_format_terminal_progress_bar():
    """Verify ASCII terminal progress bar formatting."""
    from src.api.routes import _format_terminal_progress_bar

    bar_0 = _format_terminal_progress_bar(0.0, "Queued", length=10)
    assert "[░░░░░░░░░░]   0% - Queued" == bar_0

    bar_50 = _format_terminal_progress_bar(0.5, "Halfway", length=10)
    assert "[█████░░░░░]  50% - Halfway" == bar_50

    bar_100 = _format_terminal_progress_bar(1.0, "Done", length=10)
    assert "[██████████] 100% - Done" == bar_100


@pytest.mark.asyncio
async def test_generate_chart_with_preset_and_overrides(dummy_wav_bytes: bytes):
    """Verify preset selection and explicit overrides are passed to run_pipeline_task."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"file": ("solo.wav", dummy_wav_bytes, "audio/wav")}
        data = {
            "preset": "dynamic_solo",
            "creativity": "0.95",
            "bpm_scale": "1.25",
            "min_amplitude": "0.15",
            "min_sustain_ticks": "80",
            "release_margin": "30",
            "chord_fusion_window_s": "0.040",
            "auto_calibrate_bpm": "false",
            "merge_sustained_notes": "true",
        }

        with patch("src.api.routes.run_pipeline_task") as mock_task:
            response = await client.post("/api/v1/chart/generate", files=files, data=data)

        assert response.status_code == 202
        mock_task.assert_called_once()
        _, kwargs = mock_task.call_args
        assert kwargs["preset"] == "dynamic_solo"
        assert kwargs["creativity"] == 0.95
        assert kwargs["bpm_scale"] == 1.25
        assert kwargs["min_amplitude"] == 0.15
        assert kwargs["min_sustain_ticks"] == 80
        assert kwargs["release_margin"] == 30
        assert kwargs["chord_fusion_window_s"] == 0.040
        assert kwargs["auto_calibrate_bpm"] is False
        assert kwargs["merge_sustained_notes"] is True


@pytest.mark.asyncio
async def test_generate_chart_new_validation_bounds(dummy_wav_bytes: bytes):
    """Verify validation boundaries for new chart fitting parameters."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"file": ("test.wav", dummy_wav_bytes, "audio/wav")}

        # creativity > 1.0 -> 422
        res = await client.post("/api/v1/chart/generate", files=files, data={"creativity": "1.5"})
        assert res.status_code == 422

        # creativity < 0.0 -> 422
        res = await client.post("/api/v1/chart/generate", files=files, data={"creativity": "-0.1"})
        assert res.status_code == 422

        # bpm_scale <= 0.0 -> 422
        res = await client.post("/api/v1/chart/generate", files=files, data={"bpm_scale": "0.0"})
        assert res.status_code == 422

        # bpm_scale > 2.0 -> 422
        res = await client.post("/api/v1/chart/generate", files=files, data={"bpm_scale": "2.5"})
        assert res.status_code == 422

        # min_sustain_ticks > 768 -> 422
        res = await client.post(
            "/api/v1/chart/generate", files=files, data={"min_sustain_ticks": "800"}
        )
        assert res.status_code == 422

        # release_margin > 96 -> 422
        res = await client.post(
            "/api/v1/chart/generate", files=files, data={"release_margin": "100"}
        )
        assert res.status_code == 422

        # chord_fusion_window_s < 0.005 -> 422
        res = await client.post(
            "/api/v1/chart/generate", files=files, data={"chord_fusion_window_s": "0.001"}
        )
        assert res.status_code == 422


@pytest.mark.asyncio
async def test_generate_chart_swagger_string_placeholders_sanitized(dummy_wav_bytes: bytes):
    """Verify default Swagger UI 'string' placeholders are sanitized to valid defaults."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"file": ("Band - Awesome Song.wav", dummy_wav_bytes, "audio/wav")}
        data = {
            "song_name": "string",
            "artist": "string",
            "preset": "string",
            "genre": "string",
        }

        with patch("src.api.routes.run_pipeline_task") as mock_task:
            response = await client.post("/api/v1/chart/generate", files=files, data=data)

        assert response.status_code == 202
        mock_task.assert_called_once()
        _, kwargs = mock_task.call_args
        # Should derive from filename 'Band - Awesome Song.wav' instead of 'string'
        assert kwargs["song_name"] == "Awesome Song"
        assert kwargs["artist"] == "Band"
        assert kwargs["preset"] is None
        assert kwargs["genre"] == "rock"


@pytest.mark.asyncio
async def test_preview_audio_success(tmp_path: Path):
    """Verify GET /preview/{task_id}/audio returns song.ogg with media_type audio/ogg."""
    task_id = "test-preview-audio-id"
    pkg_dir = tmp_path / task_id
    pkg_dir.mkdir(parents=True)
    audio_file = pkg_dir / "song.ogg"
    audio_file.write_bytes(b"OggS_fake_audio_stream_data")

    task_manager.create_task(task_id, song_name="Preview Song", artist="Preview Artist")
    task_manager.set_completed(task_id, output_files={"audio": audio_file, "package_dir": pkg_dir})

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Test root /preview/{task_id}/audio
        res = await client.get(f"/preview/{task_id}/audio")
        assert res.status_code == 200
        assert "audio/ogg" in res.headers["content-type"]
        assert res.content == b"OggS_fake_audio_stream_data"

        # Test API v1 chart route /api/v1/chart/preview/{task_id}/audio
        res_v1 = await client.get(f"/api/v1/chart/preview/{task_id}/audio")
        assert res_v1.status_code == 200
        assert "audio/ogg" in res_v1.headers["content-type"]
        assert res_v1.content == b"OggS_fake_audio_stream_data"


@pytest.mark.asyncio
async def test_preview_audio_task_not_found():
    """Verify 404 is returned when task_id does not exist."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/preview/non-existent-task-id/audio")
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_preview_audio_task_not_completed():
    """Verify 404 is returned when task is still pending or processing."""
    task_id = "task-still-running"
    task_manager.create_task(task_id, song_name="Track", artist="Artist")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get(f"/preview/{task_id}/audio")
        assert res.status_code == 404
        assert "not completed" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_preview_audio_file_missing_when_completed(tmp_path: Path):
    """Verify 404 is returned when task is completed but audio file is missing on disk."""
    task_id = "task-missing-audio-file"
    task_manager.create_task(task_id, song_name="Track", artist="Artist")
    task_manager.set_completed(
        task_id, output_files={"audio": tmp_path / "does_not_exist.ogg"}
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get(f"/preview/{task_id}/audio")
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_serve_web_ui_fallback_when_dist_missing(tmp_path: Path):
    """Verify root / falls back to src/api/static/index.html when frontend/dist is absent."""
    non_existent_dist = tmp_path / "non_existent_dist"
    custom_app = create_app(frontend_dist=non_existent_dist)
    async with AsyncClient(transport=ASGITransport(app=custom_app), base_url="http://test") as client:
        res = await client.get("/")
        assert res.status_code == 200
        assert "text/html" in res.headers["content-type"]
        body = res.text
        assert "music2chart" in body.lower()
        assert 'id="progress-bar"' in body


@pytest.mark.asyncio
async def test_serve_web_ui_compiled_frontend(tmp_path: Path):
    """Verify root / and static assets are served from compiled frontend/dist."""
    custom_dist = tmp_path / "custom_frontend_dist"
    custom_dist.mkdir()
    (custom_dist / "index.html").write_text("<!doctype html><html><body><div id=\"root\">CUSTOM SPA</div></body></html>")
    assets_dir = custom_dist / "assets"
    assets_dir.mkdir()
    (assets_dir / "bundle.js").write_text("console.log('spa bundle');")

    custom_app = create_app(frontend_dist=custom_dist)
    async with AsyncClient(transport=ASGITransport(app=custom_app), base_url="http://test") as client:
        res_root = await client.get("/")
        assert res_root.status_code == 200
        assert "CUSTOM SPA" in res_root.text

        res_asset = await client.get("/assets/bundle.js")
        assert res_asset.status_code == 200
        assert "console.log('spa bundle');" in res_asset.text
