"""Data models for SNG binary file container (v1 specification)."""

from dataclasses import dataclass, field


@dataclass
class SngMetadata:
    """Song container metadata key-value properties."""

    name: str = ""
    artist: str = ""
    charter: str = ""
    album: str = ""
    year: str = ""
    genre: str = ""
    diff_guitar: int = -1
    extra: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, str]:
        """Convert all non-empty metadata fields to key-value string pairs."""
        data: dict[str, str] = {}
        if self.name:
            data["name"] = self.name
        if self.artist:
            data["artist"] = self.artist
        if self.charter:
            data["charter"] = self.charter
        if self.album:
            data["album"] = self.album
        if self.year:
            data["year"] = self.year
        if self.genre:
            data["genre"] = self.genre
        if self.diff_guitar >= 0:
            data["diff_guitar"] = str(self.diff_guitar)

        # Merge additional custom properties
        data.update(self.extra)
        return data


@dataclass
class SngFileEntry:
    """An individual file packed within an .sng binary container."""

    file_name: str
    file_length: int
    file_offset: int
    contents: bytes = b""

    def __post_init__(self) -> None:
        encoded = self.file_name.encode("utf-8")
        if len(encoded) > 255:
            raise ValueError(
                f"file_name length exceeds 255 bytes when UTF-8 encoded ({len(encoded)} bytes)"
            )
        if "\\" in self.file_name:
            raise ValueError(f"file_name cannot contain backslashes: {self.file_name}")
        if self.file_length < 0:
            raise ValueError(f"file_length cannot be negative, got {self.file_length}")
        if self.file_offset < 0:
            raise ValueError(f"file_offset cannot be negative, got {self.file_offset}")


@dataclass
class SngPackage:
    """Full .sng container payload representation."""

    version: int = 1
    xor_mask: bytes | None = None
    metadata: SngMetadata = field(default_factory=SngMetadata)
    files: list[SngFileEntry] = field(default_factory=list)
