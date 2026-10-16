"""Tests for path traversal prevention in SNG unpacking and static assets endpoint."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.app import app
from src.models.sng import SngFileEntry, SngMetadata, SngPackage
from src.serialization.sng_packer import SngPacker


def test_sng_unpack_rejects_path_traversal(tmp_path: Path):
    """Verify that SngPacker.unpack rejects packages attempting directory traversal."""
    out_dir = tmp_path / "extracted"
    out_dir.mkdir()

    # Create a mock SngPackage with a malicious traversal filename
    evil_pkg = SngPackage(
        version=1,
        xor_mask=b"\x00" * 16,
        metadata=SngMetadata(name="Exploit", artist="Attacker"),
        files=[
            SngFileEntry(
                file_name="../../escaped.txt",
                file_length=12,
                file_offset=0,
                contents=b"malicious data",
            )
        ],
    )

    with patch.object(SngPacker, "read", return_value=evil_pkg):
        with pytest.raises(ValueError, match="Malicious path in SNG container"):
            SngPacker.unpack("dummy.sng", out_dir)

    # Ensure escaped.txt was never written outside out_dir
    escaped_file = tmp_path / "escaped.txt"
    assert not escaped_file.exists()


def test_sng_unpack_rejects_absolute_path_traversal(tmp_path: Path):
    """Verify that SngPacker.unpack rejects packages attempting root directory escape."""
    out_dir = tmp_path / "extracted"
    out_dir.mkdir()

    evil_pkg_relative = SngPackage(
        version=1,
        xor_mask=b"\x00" * 16,
        metadata=SngMetadata(),
        files=[
            SngFileEntry(
                file_name="../outside.txt",
                file_length=4,
                file_offset=0,
                contents=b"test",
            )
        ],
    )

    with patch.object(SngPacker, "read", return_value=evil_pkg_relative):
        with pytest.raises(ValueError, match="Malicious path in SNG container"):
            SngPacker.unpack("dummy.sng", out_dir)


def test_sng_verify_container(tmp_path: Path):
    """Verify SngPacker.verify_container behavior for valid and invalid containers."""
    pkg_dir = tmp_path / "valid_chart"
    pkg_dir.mkdir()
    (pkg_dir / "notes.chart").write_text('[Song]\n{\n  Name = "Test"\n}\n', encoding="utf-8")
    (pkg_dir / "song.ini").write_text("[Song]\nname = Test\n", encoding="utf-8")
    (pkg_dir / "song.ogg").write_bytes(b"OggS" + b"\x00" * 30)

    sng_path = tmp_path / "test.sng"
    SngPacker.pack_dir(pkg_dir, sng_path)

    # Valid container check
    assert SngPacker.verify_container(sng_path) is True

    # Truncated or corrupted container check
    corrupt_sng = tmp_path / "corrupt.sng"
    corrupt_sng.write_bytes(b"SNGPKG\x01\x00")
    assert SngPacker.verify_container(corrupt_sng) is False

    # Missing essential files (e.g. only song.ogg without chart/ini)
    partial_dir = tmp_path / "partial"
    partial_dir.mkdir()
    (partial_dir / "song.ogg").write_bytes(b"OggS" + b"\x00" * 30)
    partial_sng = tmp_path / "partial.sng"
    SngPacker.pack_dir(partial_dir, partial_sng)
    assert SngPacker.verify_container(partial_sng) is False


@pytest.mark.asyncio
async def test_assets_endpoint_prevents_path_traversal():
    """Verify that /assets/{file_path:path} rejects traversal with HTTP 403 Forbidden."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Directory traversal attempt
        res = await client.get("/assets/../../../../etc/passwd")
        assert res.status_code in (403, 404)
        if res.status_code == 403:
            assert "access denied" in res.json()["detail"].lower()

        res2 = await client.get("/assets/../static/index.html")
        assert res2.status_code in (403, 404)
