"""Unit tests for Little-Endian .sng binary packager and unpacker."""

from __future__ import annotations

import hashlib
import os
import struct
from pathlib import Path

import pytest

from src.models.sng import SngMetadata
from src.serialization.sng_packer import (
    SNG_IDENTIFIER,
    SngPacker,
)


def _reference_mask_bytes(file_bytes: bytes, xor_mask: bytes) -> bytes:
    """Exact reference loop specified in AGENTS.md Section 6.2."""
    masked = bytearray(len(file_bytes))
    for i in range(len(file_bytes)):
        xor_key = xor_mask[i % 16] ^ (i & 0xFF)
        masked[i] = file_bytes[i] ^ xor_key
    return bytes(masked)


class TestSngPackerMasking:
    """Test suite for XOR masking implementation and edge cases."""

    def test_mask_bytes_matches_specification_reference(self) -> None:
        """Verify optimized vector masking produces byte-for-byte identical output to spec reference."""
        mask = os.urandom(16)
        # Test various lengths: empty, small, around 16, around 256, and larger
        test_lengths = [0, 1, 7, 15, 16, 17, 32, 255, 256, 257, 1024, 65536]
        for length in test_lengths:
            data = os.urandom(length)
            vectorized_res = SngPacker.mask_bytes(data, mask)
            reference_res = _reference_mask_bytes(data, mask)
            assert vectorized_res == reference_res, f"Mismatch at length {length}"

    def test_mask_bytes_symmetry(self) -> None:
        """Verify masking twice with identical xor_mask yields original unmasked bytes."""
        mask = os.urandom(16)
        original_data = b"Clone Hero High Fidelity Audio and Chart Container Test" * 50
        masked = SngPacker.mask_bytes(original_data, mask)
        unmasked = SngPacker.mask_bytes(masked, mask)

        assert masked != original_data
        assert unmasked == original_data

    def test_mask_bytes_invalid_mask_length_raises(self) -> None:
        """Verify invalid mask lengths raise ValueError."""
        with pytest.raises(ValueError, match="xor_mask must be exactly 16 bytes"):
            SngPacker.mask_bytes(b"data", b"too_short")

        with pytest.raises(ValueError, match="xor_mask must be exactly 16 bytes"):
            SngPacker.mask_bytes(b"data", b"too_long_sixteen_bytes_exceeded!")


class TestSngPackerPackaging:
    """Test suite for full SNG packaging, metadata persistence, and unpacking."""

    @pytest.fixture
    def sample_files(self) -> dict[str, bytes]:
        """Synthesize sample chart, metadata, and audio binary files."""
        return {
            "notes.chart": b'[Song]\n{\n  Name = "Test Song"\n}\n[SyncTrack]\n{\n  0 = B 120000\n}\n',
            "song.ini": b"[Song]\nname = Test Song\nartist = Test Artist\ncharter = music2chart AI\n",
            "song.ogg": os.urandom(32768),  # 32KB simulated audio
            "album.png": os.urandom(4096),  # 4KB simulated art
        }

    @pytest.fixture
    def sample_metadata(self) -> SngMetadata:
        """Standard metadata with extra properties."""
        return SngMetadata(
            name="Test Song",
            artist="Test Artist",
            charter="music2chart AI",
            album="Test Album",
            year="2024",
            genre="Rock",
            diff_guitar=3,
            extra={"icon": "csc", "loading_phrase": "Rock On!"},
        )

    def test_pack_files_and_unpack_sha256_identical(
        self,
        sample_files: dict[str, bytes],
        sample_metadata: SngMetadata,
        tmp_path: Path,
    ) -> None:
        """Verify packed files are restored bit-for-bit identical via SHA-256 checksums."""
        sng_file = tmp_path / "song.sng"
        unpack_dir = tmp_path / "unpacked"

        # Pack
        packed_path = SngPacker.pack_files(
            files=sample_files,
            output_sng_path=sng_file,
            metadata=sample_metadata,
        )
        assert packed_path.is_file()

        # Unpack
        pkg = SngPacker.unpack(sng_file, unpack_dir)

        # Verify package domain model
        assert pkg.version == 1
        assert pkg.metadata.name == "Test Song"
        assert pkg.metadata.artist == "Test Artist"
        assert pkg.metadata.charter == "music2chart AI"
        assert pkg.metadata.album == "Test Album"
        assert pkg.metadata.year == "2024"
        assert pkg.metadata.genre == "Rock"
        assert pkg.metadata.diff_guitar == 3
        assert pkg.metadata.extra.get("icon") == "csc"
        assert pkg.metadata.extra.get("loading_phrase") == "Rock On!"

        # Verify SHA-256 identical restoration for each file
        for name, expected_bytes in sample_files.items():
            restored_file = unpack_dir / name
            assert restored_file.is_file()
            restored_bytes = restored_file.read_bytes()

            orig_hash = hashlib.sha256(expected_bytes).hexdigest()
            restored_hash = hashlib.sha256(restored_bytes).hexdigest()
            assert restored_hash == orig_hash
            assert restored_bytes == expected_bytes

    def test_read_in_memory(
        self,
        sample_files: dict[str, bytes],
        sample_metadata: SngMetadata,
        tmp_path: Path,
    ) -> None:
        """Verify in-memory read without filesystem unpacking."""
        sng_file = tmp_path / "song.sng"
        SngPacker.pack_files(
            files=sample_files,
            output_sng_path=sng_file,
            metadata=sample_metadata,
        )

        pkg = SngPacker.read(sng_file)
        assert len(pkg.files) == len(sample_files)

        file_map = {f.file_name: f.contents for f in pkg.files}
        for name, expected_bytes in sample_files.items():
            assert name in file_map
            assert file_map[name] == expected_bytes

    def test_pack_directory_with_auto_ini(self, tmp_path: Path) -> None:
        """Verify packing a physical directory parses song.ini metadata automatically."""
        src_dir = tmp_path / "source_folder"
        src_dir.mkdir()

        # Write files into directory
        (src_dir / "notes.chart").write_text("[Song]\n{\n}\n", encoding="utf-8")
        (src_dir / "song.ini").write_text(
            "[Song]\nname = Directory Song\nartist = Direct Artist\ngold = true\n",
            encoding="utf-8",
        )
        (src_dir / "song.ogg").write_bytes(b"FAKE_OGG_HEADER_DATA")

        out_sng = tmp_path / "dir_song.sng"
        SngPacker.pack_dir(input_dir=src_dir, output_sng_path=out_sng)

        # Read back
        pkg = SngPacker.read(out_sng)
        assert pkg.metadata.name == "Directory Song"
        assert pkg.metadata.artist == "Direct Artist"
        assert pkg.metadata.extra.get("gold") == "true"

        file_names = {f.file_name for f in pkg.files}
        assert "notes.chart" in file_names
        assert "song.ini" in file_names
        assert "song.ogg" in file_names


class TestSngPackerErrors:
    """Test suite for error detection, corrupted files, and format boundary violations."""

    def test_invalid_magic_identifier(self, tmp_path: Path) -> None:
        """Verify corrupted magic identifier raises ValueError."""
        bad_sng = tmp_path / "corrupt_magic.sng"
        # Write "NOTSNG" instead of "SNGPKG"
        bad_data = b"NOTSNG" + struct.pack("<I", 1) + os.urandom(16) + b"\x00" * 32
        bad_sng.write_bytes(bad_data)

        with pytest.raises(ValueError, match="Invalid SNG identifier"):
            SngPacker.read(bad_sng)

    def test_unsupported_version(self, tmp_path: Path) -> None:
        """Verify unsupported version raises ValueError."""
        bad_sng = tmp_path / "bad_version.sng"
        bad_data = SNG_IDENTIFIER + struct.pack("<I", 999) + os.urandom(16) + b"\x00" * 32
        bad_sng.write_bytes(bad_data)

        with pytest.raises(ValueError, match="Unsupported SNG version: 999"):
            SngPacker.read(bad_sng)

    def test_truncated_file_raises(self, tmp_path: Path) -> None:
        """Verify truncated file raises ValueError."""
        bad_sng = tmp_path / "truncated.sng"
        bad_sng.write_bytes(b"SNG")  # incomplete header

        with pytest.raises(ValueError, match="Corrupted or truncated"):
            SngPacker.read(bad_sng)

    def test_filename_exceeds_255_bytes_raises(self, tmp_path: Path) -> None:
        """Verify filename exceeding 255 bytes UTF-8 raises ValueError."""
        long_name = "a" * 256 + ".chart"
        files = {long_name: b"content"}
        out_sng = tmp_path / "too_long.sng"

        with pytest.raises(ValueError, match=r"(?i)exceeds 255 bytes"):
            SngPacker.pack_files(files=files, output_sng_path=out_sng)

    def test_nonexistent_directory_raises(self, tmp_path: Path) -> None:
        """Verify pack_dir raises FileNotFoundError for missing directory."""
        with pytest.raises(FileNotFoundError):
            SngPacker.pack_dir(tmp_path / "nonexistent", tmp_path / "out.sng")
