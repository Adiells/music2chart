"""Security validation, audio probe, and string sanitization utilities."""

from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# Regular expressions for sanitization
CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f-\x9f]")
NEWLINE_RE = re.compile(r"[\r\n]+")
INI_ILLEGAL_KEY_CHARS_RE = re.compile(r"[\r\n=:\[\]\x00-\x1f\x7f-\x9f]")


def is_mp3_sync(header: bytes) -> bool:
    """Check whether bytes start with an MPEG audio sync word (MPEG-1/2/2.5 Layer I/II/III)."""
    if len(header) < 2:
        return False
    # Sync word is 11 bits set: 0xFF followed by top 3 bits set in second byte
    if header[0] != 0xFF or (header[1] & 0xE0) != 0xE0:
        return False
    # Version bits: 01 is reserved (invalid)
    if (header[1] & 0x18) == 0x08:
        return False
    # Layer bits: 00 is reserved (invalid)
    if (header[1] & 0x06) == 0x00:
        return False
    return True


def detect_audio_format(header: bytes) -> str | None:
    """Detect audio container format from raw initial bytes.

    Args:
        header: Leading bytes of the audio file (at least 12 bytes recommended).

    Returns:
        One of 'mp3', 'wav', 'ogg', 'flac', or None if unrecognized.
    """
    if len(header) < 2:
        return None

    if header.startswith(b"ID3") or is_mp3_sync(header):
        return "mp3"

    if header.startswith(b"RIFF") and (len(header) < 12 or header[8:12] == b"WAVE"):
        return "wav"

    if header.startswith(b"OggS"):
        return "ogg"

    if header.startswith(b"fLaC"):
        return "flac"

    return None


def validate_audio_magic_bytes(header: bytes, expected_format: str | None = None) -> bool:
    """Verify that file header matches supported audio container signatures.

    Args:
        header: Initial slice of file bytes.
        expected_format: Optional expected extension/format (e.g., 'mp3', '.wav').
            If None, verifies that header matches any supported audio format.

    Returns:
        True if signature is valid, False otherwise.
    """
    detected = detect_audio_format(header)
    if detected is None:
        return False

    if expected_format is not None:
        norm_expected = expected_format.lower().lstrip(".")
        return detected == norm_expected

    return True


def probe_audio_duration(file_path: Path | str) -> float:
    """Probe audio duration in seconds using lightweight metadata inspection.

    Args:
        file_path: Path to audio file on disk.

    Returns:
        Duration in seconds as a float.

    Raises:
        ValueError: If file does not exist, cannot be opened, or duration cannot be determined.
    """
    path = Path(file_path)
    if not path.is_file():
        raise ValueError(f"Audio file does not exist: {path}")

    # 1. Prefer soundfile.info (fast header read without loading samples into memory)
    try:
        import soundfile as sf

        info = sf.info(str(path))
        if info.duration > 0.0:
            return float(info.duration)
    except Exception as exc:
        logger.debug("soundfile.info failed on %s: %s; falling back to librosa", path, exc)

    # 2. Fallback to librosa.get_duration
    try:
        import librosa

        dur = librosa.get_duration(path=str(path))
        if dur > 0.0:
            return float(dur)
    except Exception as exc:
        logger.debug("librosa.get_duration failed on %s: %s", path, exc)

    raise ValueError(f"Unable to determine audio duration for file: {path}")


def validate_audio_file(
    file_path: Path | str,
    max_duration_seconds: float = 900.0,
    expected_format: str | None = None,
) -> float:
    """Perform pre-flight verification of audio file signature and playback duration.

    Args:
        file_path: Path to uploaded audio file.
        max_duration_seconds: Maximum permitted duration in seconds (default 900s = 15m).
        expected_format: Optional expected file format.

    Returns:
        Validated duration in seconds.

    Raises:
        ValueError: If magic bytes are invalid or duration exceeds the limit.
    """
    path = Path(file_path)
    if not path.is_file():
        raise ValueError(f"Audio file does not exist: {path}")

    with open(path, "rb") as f:
        header = f.read(64)

    if not validate_audio_magic_bytes(header, expected_format=expected_format):
        raise ValueError(
            f"File '{path.name}' signature does not match supported audio formats (MP3, WAV, OGG, FLAC)."
        )

    duration = probe_audio_duration(path)
    if duration > max_duration_seconds:
        raise ValueError(
            f"Audio duration ({duration:.1f}s) exceeds maximum allowed limit of {max_duration_seconds:.0f}s."
        )

    return duration


def sanitize_string(
    val: str,
    max_length: int = 128,
    escape_quotes: bool = True,
    strip_section_closers: bool = True,
) -> str:
    """Sanitize strings destined for .chart text serialization.

    Removes newlines and control characters, escapes quotes, removes closing braces,
    and limits string length to prevent injection attacks into game chart sections.

    Args:
        val: Input text string.
        max_length: Maximum allowed length (default 128).
        escape_quotes: Whether to escape unescaped double quotes (default True).
        strip_section_closers: Whether to strip closing braces '}' (default True).

    Returns:
        Clean, sanitized string safe for interpolation in .chart files.
    """
    if not val:
        return ""

    # Replace newlines with spaces and strip control characters
    cleaned = NEWLINE_RE.sub(" ", val)
    cleaned = CONTROL_CHAR_RE.sub("", cleaned).strip()

    if strip_section_closers:
        cleaned = cleaned.replace("}", "")

    if escape_quotes:
        # Escape any quote that is not already preceded by a backslash
        cleaned = re.sub(r'(?<!\\)"', r'\"', cleaned)

    return cleaned[:max_length].strip()


def sanitize_ini_value(val: str, max_length: int = 256) -> str:
    """Sanitize metadata values for song.ini files.

    Removes newlines and control characters to prevent INI section injection.

    Args:
        val: Input metadata value.
        max_length: Maximum string length (default 256).

    Returns:
        Sanitized value string.
    """
    if not val:
        return ""

    cleaned = NEWLINE_RE.sub(" ", str(val))
    cleaned = CONTROL_CHAR_RE.sub("", cleaned).strip()
    return cleaned[:max_length].strip()


def sanitize_ini_key(val: str, max_length: int = 64) -> str:
    """Sanitize property keys for song.ini files.

    Removes whitespace, delimiters (=, :), section markers ([, ]), and newlines.

    Args:
        val: Input key string.
        max_length: Maximum key length (default 64).

    Returns:
        Sanitized key string in lowercase.
    """
    if not val:
        return ""

    cleaned = INI_ILLEGAL_KEY_CHARS_RE.sub("", str(val)).strip()
    return cleaned[:max_length].strip().lower()


def is_safe_path(base_dir: Path | str, untrusted_path: Path | str) -> bool:
    """Verify that an untrusted path resolves strictly inside base_dir without traversal.

    Args:
        base_dir: Root directory boundary.
        untrusted_path: Untrusted file or relative path string.

    Returns:
        True if target is securely contained inside base_dir, False otherwise.
    """
    try:
        base = Path(base_dir).resolve()
        clean_rel = str(untrusted_path).replace("\\", "/").lstrip("/")
        target = (base / clean_rel).resolve()
        return target.is_relative_to(base)
    except Exception:
        return False
