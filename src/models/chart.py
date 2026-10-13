"""Clone Hero chart representations, fret enums, notes, and song tracks."""

from dataclasses import dataclass, field
from enum import IntEnum


class FretType(IntEnum):
    """Fret and modifier button enumeration for 5-fret guitar charts."""

    GREEN = 0
    RED = 1
    YELLOW = 2
    BLUE = 3
    ORANGE = 4
    HOPO_FORCE = 5  # Note modifier: Force Hammer-On / Pull-Off
    STRUM_FORCE = 6  # Note modifier: Force Strum
    OPEN = 7  # Open note (purple bar)


@dataclass
class ChartNote:
    """A note or modifier ready for serialization into .chart format."""

    tick: int
    fret: FretType
    sustain_length: int = 0
    is_hopo: bool = False

    def __post_init__(self) -> None:
        if self.tick < 0:
            raise ValueError(f"tick must be non-negative, got {self.tick}")
        if self.sustain_length < 0:
            raise ValueError(f"sustain_length cannot be negative, got {self.sustain_length}")
        if not isinstance(self.fret, FretType):
            self.fret = FretType(self.fret)

    def __lt__(self, other: "ChartNote") -> bool:
        if not isinstance(other, ChartNote):
            return NotImplemented
        if self.tick != other.tick:
            return self.tick < other.tick
        return self.fret < other.fret


@dataclass(frozen=True)
class StarPowerPhrase:
    """Star power phrase allocation."""

    tick: int
    length: int  # Duration in ticks

    def __post_init__(self) -> None:
        if self.tick < 0:
            raise ValueError(f"tick must be non-negative, got {self.tick}")
        if self.length < 0:
            raise ValueError(f"length cannot be negative, got {self.length}")


@dataclass
class SongTrack:
    """A single instrument difficulty track (e.g., ExpertSingle)."""

    name: str
    notes: list[ChartNote] = field(default_factory=list)
    star_power: list[StarPowerPhrase] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.notes.sort()
        self.star_power.sort(key=lambda sp: sp.tick)

    def add_note(self, note: ChartNote) -> None:
        """Add a note and maintain chronological order."""
        self.notes.append(note)
        self.notes.sort()

    def notes_at_tick(self, tick: int) -> list[ChartNote]:
        """Return all notes present at a specific tick."""
        return [n for n in self.notes if n.tick == tick]
