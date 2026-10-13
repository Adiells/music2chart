"""Unit tests for ChorusScraper client and package extraction."""

import io
import zipfile
from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pytest

from dataset.chorus_scraper import ChorusScraper


def test_search_charts_success() -> None:
    """Test successful API search query returning chart records."""
    mock_data = [
        {"id": "c1", "name": "Through the Fire and Flames", "artist": "DragonForce"},
        {"id": "c2", "name": "Cliffs of Dover", "artist": "Eric Johnson"},
    ]

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": mock_data}

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = mock_response

    scraper = ChorusScraper(client=mock_client)
    results = scraper.search_charts(query="DragonForce", instrument="guitar")

    assert len(results) == 2
    assert results[0]["name"] == "Through the Fire and Flames"
    mock_client.get.assert_called_once()


def test_search_charts_rate_limit_retry() -> None:
    """Test rate limit 429 response handling with retry."""
    resp_429 = MagicMock(spec=httpx.Response)
    resp_429.status_code = 429
    resp_429.headers = {"Retry-After": "0.01"}

    resp_200 = MagicMock(spec=httpx.Response)
    resp_200.status_code = 200
    resp_200.json.return_value = [{"id": "c1", "name": "Song"}]

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.side_effect = [resp_429, resp_200]

    scraper = ChorusScraper(client=mock_client, backoff_factor=0.01)
    results = scraper.search_charts(query="Song")

    assert len(results) == 1
    assert mock_client.get.call_count == 2


def test_search_charts_failure_after_retries() -> None:
    """Test persistent errors trigger RuntimeError."""
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.side_effect = httpx.ConnectError("Network offline")

    scraper = ChorusScraper(client=mock_client, max_retries=2, backoff_factor=0.01)
    with pytest.raises(RuntimeError, match="Failed to search charts"):
        scraper.search_charts(query="Fail")


def test_download_chart_package(tmp_path: Path) -> None:
    """Test downloading package bytes directly to destination directory."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.iter_bytes.return_value = [b"PK\x03\x04test_zip_data"]

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.stream.return_value.__enter__.return_value = mock_response

    scraper = ChorusScraper(client=mock_client)
    dest_dir = tmp_path / "downloads"
    saved_file = scraper.download_chart_package("chart_123", dest_dir)

    assert saved_file.exists()
    assert saved_file.name == "chart_123.zip"
    assert saved_file.read_bytes() == b"PK\x03\x04test_zip_data"


def test_extract_valid_zip_package(tmp_path: Path) -> None:
    """Test extracting a valid zip containing both .chart and audio file."""
    zip_path = tmp_path / "test_song.zip"
    extract_dir = tmp_path / "extracted"

    # Create test zip archive in memory
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("notes.chart", "[Song]\nName = Test\n")
        zf.writestr("song.ogg", b"OggS_fake_audio_stream")
    zip_path.write_bytes(buf.getvalue())

    scraper = ChorusScraper()
    res_dir = scraper.extract_chart_package(zip_path, extract_dir)

    assert (res_dir / "notes.chart").exists()
    assert (res_dir / "song.ogg").exists()


def test_extract_missing_audio_fails(tmp_path: Path) -> None:
    """Test error is raised if package lacks an audio file."""
    zip_path = tmp_path / "no_audio.zip"
    extract_dir = tmp_path / "extracted"

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("notes.chart", "[Song]\nName = Test\n")
    zip_path.write_bytes(buf.getvalue())

    scraper = ChorusScraper()
    with pytest.raises(ValueError, match="missing an audio track"):
        scraper.extract_chart_package(zip_path, extract_dir)


def test_extract_missing_chart_fails(tmp_path: Path) -> None:
    """Test error is raised if package lacks a chart file."""
    zip_path = tmp_path / "no_chart.zip"
    extract_dir = tmp_path / "extracted"

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("song.ogg", b"OggS_audio")
    zip_path.write_bytes(buf.getvalue())

    scraper = ChorusScraper()
    with pytest.raises(ValueError, match="missing a chart file"):
        scraper.extract_chart_package(zip_path, extract_dir)


def test_extract_zip_slip_prevention(tmp_path: Path) -> None:
    """Test zip entry with path traversal attempt is blocked."""
    zip_path = tmp_path / "malicious.zip"
    extract_dir = tmp_path / "extracted"

    # Construct mock ZipInfo with malicious path
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("../../evil.txt", b"malicious content")
    zip_path.write_bytes(buf.getvalue())

    scraper = ChorusScraper()
    with pytest.raises(ValueError, match="Malicious zip entry"):
        scraper.extract_chart_package(zip_path, extract_dir)


def test_extract_sng_file(tmp_path: Path) -> None:
    """Test direct handling of .sng package."""
    sng_path = tmp_path / "test.sng"
    sng_path.write_bytes(b"SNGPKG_mock_content")

    extract_dir = tmp_path / "extracted"
    scraper = ChorusScraper()
    res = scraper.extract_chart_package(sng_path, extract_dir)
    assert (res / "test.sng").exists()
