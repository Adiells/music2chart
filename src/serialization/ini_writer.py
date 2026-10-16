"""Serializer and parser for Clone Hero song.ini metadata files."""

from __future__ import annotations

import configparser
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from src.models.sng import SngMetadata

STANDARD_INI_KEYS = [
    "name",
    "artist",
    "charter",
    "album",
    "year",
    "genre",
    "diff_guitar",
]


class IniWriter:
    """Generates and parses song.ini companion metadata files."""

    @classmethod
    def generate_string(
        cls,
        metadata: SngMetadata | Mapping[str, Any] | None = None,
        **kwargs: Any,
    ) -> str:
        """Generate formatted INI content string for a Clone Hero song.

        Args:
            metadata: SngMetadata object or dict with metadata key-values.
            **kwargs: Additional or override metadata key-values.

        Returns:
            Formatted INI text string ending with a newline.
        """
        combined: dict[str, str] = {}

        if isinstance(metadata, SngMetadata):
            combined.update(metadata.to_dict())
        elif isinstance(metadata, Mapping):
            for k, v in metadata.items():
                if v is not None and v != "":
                    combined[str(k).lower()] = str(v)

        for k, v in kwargs.items():
            if v is not None and v != "":
                combined[k.lower()] = str(v)

        # Standard defaults if essential keys are missing
        if "charter" not in combined:
            combined["charter"] = "music2chart AI"

        lines: list[str] = ["[Song]"]

        # First output standard keys in canonical order
        handled_keys: set[str] = set()
        for key in STANDARD_INI_KEYS:
            if key in combined:
                lines.append(f"{key} = {combined[key]}")
                handled_keys.add(key)

        # Next output any extra keys sorted alphabetically
        for key in sorted(combined.keys()):
            if key not in handled_keys:
                lines.append(f"{key} = {combined[key]}")

        return "\n".join(lines) + "\n"

    @classmethod
    def write(
        cls,
        output_path: Path | str,
        metadata: SngMetadata | Mapping[str, Any] | None = None,
        **kwargs: Any,
    ) -> Path:
        """Write song.ini file to disk with standard UTF-8 encoding.

        Args:
            output_path: Destination path for song.ini.
            metadata: SngMetadata object or dict with metadata.
            **kwargs: Extra or override fields.

        Returns:
            The Path where song.ini was written.
        """
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        content = cls.generate_string(metadata=metadata, **kwargs)
        target.write_text(content, encoding="utf-8", newline="\n")
        return target

    @classmethod
    def parse_string(cls, content: str) -> dict[str, str]:
        """Parse raw song.ini content into a key-value dictionary.

        Args:
            content: Raw text of a song.ini file.

        Returns:
            Dictionary of key-value pairs (keys in lowercase).
        """
        parser = configparser.ConfigParser(interpolation=None)
        # Preserve case or use lowercase
        parser.optionxform = str  # type: ignore[assignment]
        try:
            parser.read_string(content)
        except configparser.MissingSectionHeaderError:
            # Wrap content with [Song] if header is missing
            parser.read_string(f"[Song]\n{content}")

        result: dict[str, str] = {}
        for section in parser.sections():
            for key, value in parser.items(section):
                result[key.lower()] = value.strip('"').strip("'")
        return result

    @classmethod
    def parse_file(cls, file_path: Path | str) -> dict[str, str]:
        """Read and parse song.ini file from disk.

        Args:
            file_path: Path to song.ini file.

        Returns:
            Dictionary of parsed metadata key-value pairs.
        """
        path = Path(file_path)
        try:
            content = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            content = path.read_text(encoding="latin-1")
        return cls.parse_string(content)
