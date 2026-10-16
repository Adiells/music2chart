"""Native Little-Endian binary packager and unpacker for Clone Hero .sng container (v1)."""

from __future__ import annotations

import os
import struct
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np

from src.models.sng import SngFileEntry, SngMetadata, SngPackage
from src.serialization.ini_writer import IniWriter

SNG_IDENTIFIER = b"SNGPKG"
SNG_VERSION = 1
XOR_MASK_SIZE = 16


class SngPacker:
    """Packer and unpacker for Clone Hero .sng binary containers."""

    @staticmethod
    def mask_bytes(file_bytes: bytes, xor_mask: bytes) -> bytes:
        """Apply or invert XOR obfuscation mask on byte sequences.

        Uses the official algorithm:
            xor_key = xor_mask[i % 16] ^ (i & 0xFF)
            masked_byte = raw_byte ^ xor_key

        Because the key repeats with a period of 256 bytes, this implementation
        pre-computes the 256-byte keystream cycle and vectorizes XOR with NumPy
        for maximum performance on large audio tracks.

        Args:
            file_bytes: Raw or masked input bytes.
            xor_mask: 16-byte pseudo-random mask.

        Returns:
            Masked (or unmasked) bytes.
        """
        if not file_bytes:
            return b""
        if len(xor_mask) != XOR_MASK_SIZE:
            raise ValueError(f"xor_mask must be exactly {XOR_MASK_SIZE} bytes, got {len(xor_mask)}")

        n = len(file_bytes)
        # Precompute the 256-byte repeating cycle
        cycle = bytes(xor_mask[j % 16] ^ j for j in range(256))
        repeats = (n // 256) + 1
        keystream = (cycle * repeats)[:n]

        # Fast bitwise XOR using numpy
        arr_in = np.frombuffer(file_bytes, dtype=np.uint8)
        arr_key = np.frombuffer(keystream, dtype=np.uint8)
        return np.bitwise_xor(arr_in, arr_key).tobytes()

    @classmethod
    def pack_files(
        cls,
        files: Mapping[str, bytes | Path],
        output_sng_path: Path | str,
        metadata: SngMetadata | Mapping[str, Any] | None = None,
        xor_mask: bytes | None = None,
    ) -> Path:
        """Pack a mapping of filenames to byte contents (or Paths) into a .sng container.

        Args:
            files: Dict mapping relative filename string to bytes or source file Path.
            output_sng_path: Output file path for .sng package.
            metadata: Optional SngMetadata or dict with metadata.
            xor_mask: Optional 16-byte mask (generated randomly if None).

        Returns:
            Path to the written .sng container.
        """
        out_path = Path(output_sng_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        if xor_mask is None:
            xor_mask = os.urandom(XOR_MASK_SIZE)
        elif len(xor_mask) != XOR_MASK_SIZE:
            raise ValueError(f"xor_mask must be exactly {XOR_MASK_SIZE} bytes, got {len(xor_mask)}")

        # Normalize metadata
        sng_meta: SngMetadata
        if isinstance(metadata, SngMetadata):
            sng_meta = metadata
        elif isinstance(metadata, Mapping):
            meta_dict = {str(k): str(v) for k, v in metadata.items() if v is not None}
            sng_meta = SngMetadata(
                name=meta_dict.get("name", ""),
                artist=meta_dict.get("artist", ""),
                charter=meta_dict.get("charter", ""),
                album=meta_dict.get("album", ""),
                year=meta_dict.get("year", ""),
                genre=meta_dict.get("genre", ""),
                diff_guitar=int(meta_dict["diff_guitar"]) if "diff_guitar" in meta_dict else -1,
                extra={
                    k: v
                    for k, v in meta_dict.items()
                    if k
                    not in [
                        "name",
                        "artist",
                        "charter",
                        "album",
                        "year",
                        "genre",
                        "diff_guitar",
                    ]
                },
            )
        else:
            sng_meta = SngMetadata()

        # -------------------------------------------------------------------
        # 1. Prepare Metadata Section Bytes
        # -------------------------------------------------------------------
        meta_dict = sng_meta.to_dict()
        meta_count = len(meta_dict)
        meta_payload = bytearray()
        meta_payload += struct.pack("<Q", meta_count)

        for k, v in meta_dict.items():
            k_bytes = k.encode("utf-8")
            v_bytes = str(v).encode("utf-8")
            meta_payload += struct.pack("<i", len(k_bytes))
            meta_payload += k_bytes
            meta_payload += struct.pack("<i", len(v_bytes))
            meta_payload += v_bytes

        metadata_len = len(meta_payload)

        # -------------------------------------------------------------------
        # 2. Prepare Files & Masking
        # -------------------------------------------------------------------
        file_entries: list[SngFileEntry] = []
        masked_data_blocks: list[bytes] = []
        current_offset = 0

        for file_name, file_source in files.items():
            clean_name = file_name.replace("\\", "/")
            if clean_name.startswith("/"):
                clean_name = clean_name.lstrip("/")

            raw_bytes: bytes
            if isinstance(file_source, (str, Path)):
                raw_bytes = Path(file_source).read_bytes()
            elif isinstance(file_source, bytes):
                raw_bytes = file_source
            else:
                raise TypeError(
                    f"Unsupported file source type for {file_name}: {type(file_source)}"
                )

            masked_bytes = cls.mask_bytes(raw_bytes, xor_mask)
            file_len = len(raw_bytes)

            file_entries.append(
                SngFileEntry(
                    file_name=clean_name,
                    file_length=file_len,
                    file_offset=current_offset,
                    contents=raw_bytes,
                )
            )
            masked_data_blocks.append(masked_bytes)
            current_offset += file_len

        # -------------------------------------------------------------------
        # 3. Prepare FileIndex Section Bytes
        # -------------------------------------------------------------------
        file_count = len(file_entries)
        index_payload = bytearray()
        index_payload += struct.pack("<Q", file_count)

        for entry in file_entries:
            name_bytes = entry.file_name.encode("utf-8")
            if len(name_bytes) > 255:
                raise ValueError(f"Filename exceeds 255 bytes UTF-8 encoded: {entry.file_name}")
            index_payload += struct.pack("<B", len(name_bytes))
            index_payload += name_bytes
            index_payload += struct.pack("<Q", entry.file_length)
            index_payload += struct.pack("<Q", entry.file_offset)

        file_index_len = len(index_payload)

        # -------------------------------------------------------------------
        # 4. Prepare Binary Data Section Bytes
        # -------------------------------------------------------------------
        binary_section_len = sum(entry.file_length for entry in file_entries)
        binary_payload = b"".join(masked_data_blocks)

        # -------------------------------------------------------------------
        # 5. Assemble and Write Full Container
        # -------------------------------------------------------------------
        with open(out_path, "wb") as f:
            # Header: Identifier (6 bytes) + version (uint32) + xorMask (16 bytes)
            f.write(SNG_IDENTIFIER)
            f.write(struct.pack("<I", SNG_VERSION))
            f.write(xor_mask)

            # Metadata Section
            f.write(struct.pack("<Q", metadata_len))
            f.write(meta_payload)

            # FileIndex Section
            f.write(struct.pack("<Q", file_index_len))
            f.write(index_payload)

            # Binary Data Section
            f.write(struct.pack("<Q", binary_section_len))
            f.write(binary_payload)

        return out_path

    @classmethod
    def pack_dir(
        cls,
        input_dir: Path | str,
        output_sng_path: Path | str,
        metadata: SngMetadata | Mapping[str, Any] | None = None,
        xor_mask: bytes | None = None,
    ) -> Path:
        """Package a directory containing Clone Hero chart files into a .sng container.

        Automatically inspects song.ini in the directory if metadata is omitted.

        Args:
            input_dir: Directory containing notes.chart, song.ini, audio files, etc.
            output_sng_path: Destination path for .sng file.
            metadata: Optional SngMetadata or dict.
            xor_mask: Optional 16-byte XOR mask.

        Returns:
            Path to generated .sng container.
        """
        src_dir = Path(input_dir)
        if not src_dir.is_dir():
            raise FileNotFoundError(f"Input directory does not exist: {src_dir}")

        # Gather files
        files_dict: dict[str, Path] = {}
        for path in src_dir.rglob("*"):
            if path.is_file() and not path.name.endswith(".sng"):
                rel_name = path.relative_to(src_dir).as_posix()
                files_dict[rel_name] = path

        # Auto-extract metadata from song.ini if not supplied
        if metadata is None:
            ini_candidates = [p for p in files_dict.values() if p.name.lower() == "song.ini"]
            if ini_candidates:
                metadata = IniWriter.parse_file(ini_candidates[0])

        return cls.pack_files(
            files=files_dict,
            output_sng_path=output_sng_path,
            metadata=metadata,
            xor_mask=xor_mask,
        )

    pack_directory = pack_dir
    pack = pack_dir

    @classmethod
    def read(cls, sng_path: Path | str) -> SngPackage:
        """Read and parse .sng container into memory without writing to filesystem.

        Args:
            sng_path: Path to .sng container file.

        Returns:
            SngPackage domain object containing metadata, files, and unmasked contents.
        """
        path = Path(sng_path)
        data = path.read_bytes()

        if len(data) < len(SNG_IDENTIFIER) + 4 + XOR_MASK_SIZE:
            raise ValueError(f"Corrupted or truncated SNG container ({len(data)} bytes)")

        # Read Header
        offset = 0
        ident = data[offset : offset + 6]
        offset += 6
        if ident != SNG_IDENTIFIER:
            raise ValueError(f"Invalid SNG identifier: {ident!r}, expected {SNG_IDENTIFIER!r}")

        (version,) = struct.unpack_from("<I", data, offset)
        offset += 4
        if version != SNG_VERSION:
            raise ValueError(f"Unsupported SNG version: {version}, expected {SNG_VERSION}")

        xor_mask = data[offset : offset + XOR_MASK_SIZE]
        offset += XOR_MASK_SIZE

        # Read Metadata Section
        (metadata_len,) = struct.unpack_from("<Q", data, offset)
        offset += 8
        meta_end = offset + metadata_len
        if meta_end > len(data):
            raise ValueError("Truncated metadata section")

        (metadata_count,) = struct.unpack_from("<Q", data, offset)
        offset += 8

        meta_dict: dict[str, str] = {}
        for _ in range(metadata_count):
            (k_len,) = struct.unpack_from("<i", data, offset)
            offset += 4
            k = data[offset : offset + k_len].decode("utf-8")
            offset += k_len

            (v_len,) = struct.unpack_from("<i", data, offset)
            offset += 4
            v = data[offset : offset + v_len].decode("utf-8")
            offset += v_len

            meta_dict[k] = v

        offset = meta_end  # ensure positioned at end of metadata section

        # Read FileIndex Section
        (file_index_len,) = struct.unpack_from("<Q", data, offset)
        offset += 8
        index_end = offset + file_index_len
        if index_end > len(data):
            raise ValueError("Truncated file index section")

        (file_count,) = struct.unpack_from("<Q", data, offset)
        offset += 8

        files: list[SngFileEntry] = []
        for _ in range(file_count):
            (name_len,) = struct.unpack_from("<B", data, offset)
            offset += 1
            name = data[offset : offset + name_len].decode("utf-8")
            offset += name_len

            (file_len, file_offset) = struct.unpack_from("<QQ", data, offset)
            offset += 16

            files.append(
                SngFileEntry(
                    file_name=name,
                    file_length=file_len,
                    file_offset=file_offset,
                )
            )

        offset = index_end

        # Read Binary Data Section
        (binary_section_len,) = struct.unpack_from("<Q", data, offset)
        offset += 8
        binary_start = offset
        binary_end = binary_start + binary_section_len
        if binary_end > len(data):
            raise ValueError("Truncated binary data section")

        # Extract and unmask each file's data
        for entry in files:
            entry_start = binary_start + entry.file_offset
            entry_end = entry_start + entry.file_length
            if entry_end > len(data):
                raise ValueError(
                    f"File entry {entry.file_name} offset+length exceeds container boundary"
                )
            masked_file_bytes = data[entry_start:entry_end]
            entry.contents = cls.mask_bytes(masked_file_bytes, xor_mask)

        sng_metadata = SngMetadata(
            name=meta_dict.get("name", ""),
            artist=meta_dict.get("artist", ""),
            charter=meta_dict.get("charter", ""),
            album=meta_dict.get("album", ""),
            year=meta_dict.get("year", ""),
            genre=meta_dict.get("genre", ""),
            diff_guitar=int(meta_dict["diff_guitar"]) if "diff_guitar" in meta_dict else -1,
            extra={
                k: v
                for k, v in meta_dict.items()
                if k
                not in [
                    "name",
                    "artist",
                    "charter",
                    "album",
                    "year",
                    "genre",
                    "diff_guitar",
                ]
            },
        )

        return SngPackage(
            version=version,
            xor_mask=xor_mask,
            metadata=sng_metadata,
            files=files,
        )

    @classmethod
    def unpack(cls, sng_path: Path | str, output_dir: Path | str) -> SngPackage:
        """Unpack a .sng container to the filesystem, restoring exact original files.

        Args:
            sng_path: Path to the .sng file to unpack.
            output_dir: Target directory where unpacked files are created.

        Returns:
            The parsed SngPackage object with metadata and files.
        """
        pkg = cls.read(sng_path)
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        for entry in pkg.files:
            file_path = out / entry.file_name
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_bytes(entry.contents)

        return pkg

    unpack_dir = unpack
    unpack_files = unpack
