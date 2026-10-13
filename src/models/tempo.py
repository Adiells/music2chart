"""Musical timing, BPM changes, time signatures, and tick-to-second synchronization."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class BPMChange:
    """Tempo change event on the timeline."""

    tick: int  # Position on the musical grid (PPQ)
    bpm: float  # Beats per minute

    def __post_init__(self) -> None:
        if self.tick < 0:
            raise ValueError(f"tick must be non-negative, got {self.tick}")
        if self.bpm <= 0.0:
            raise ValueError(f"bpm must be strictly positive, got {self.bpm}")


@dataclass(frozen=True)
class TimeSignature:
    """Time signature marking."""

    tick: int
    numerator: int = 4
    denominator: int = 4

    def __post_init__(self) -> None:
        if self.tick < 0:
            raise ValueError(f"tick must be non-negative, got {self.tick}")
        if self.numerator <= 0:
            raise ValueError(f"numerator must be positive, got {self.numerator}")
        if self.denominator <= 0:
            raise ValueError(f"denominator must be positive, got {self.denominator}")


@dataclass
class TempoMap:
    """Rhythmic synchronization map with tick <-> second conversion."""

    resolution: int = 192  # Pulses (ticks) per quarter note (PPQ)
    bpm_changes: list[BPMChange] = field(default_factory=list)
    time_signatures: list[TimeSignature] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.resolution <= 0:
            raise ValueError(f"resolution must be positive, got {self.resolution}")

        # Ensure at least one default BPM change at tick 0
        if not self.bpm_changes:
            self.bpm_changes = [BPMChange(tick=0, bpm=120.0)]
        else:
            self.bpm_changes = sorted(self.bpm_changes, key=lambda c: c.tick)
            if self.bpm_changes[0].tick != 0:
                # Prepend tick 0 with initial bpm
                self.bpm_changes.insert(0, BPMChange(tick=0, bpm=self.bpm_changes[0].bpm))

        # Ensure default time signature
        if not self.time_signatures:
            self.time_signatures = [TimeSignature(tick=0, numerator=4, denominator=4)]
        else:
            self.time_signatures = sorted(self.time_signatures, key=lambda ts: ts.tick)

    def tick_to_seconds(self, tick: int) -> float:
        """Convert a grid tick position into time in seconds."""
        if tick <= 0:
            return 0.0

        elapsed_seconds = 0.0
        changes = self.bpm_changes

        for i in range(len(changes)):
            curr_change = changes[i]
            if tick <= curr_change.tick:
                break

            # Determine upper tick bound for this tempo segment
            if i + 1 < len(changes) and tick > changes[i + 1].tick:
                segment_ticks = changes[i + 1].tick - curr_change.tick
            else:
                segment_ticks = tick - curr_change.tick

            seconds_per_tick = 60.0 / (curr_change.bpm * self.resolution)
            elapsed_seconds += segment_ticks * seconds_per_tick

        return elapsed_seconds

    def seconds_to_tick(self, seconds: float) -> int:
        """Convert time in seconds to the nearest grid tick position."""
        if seconds <= 0.0:
            return 0

        changes = self.bpm_changes
        accumulated_seconds = 0.0

        for i in range(len(changes)):
            curr_change = changes[i]
            seconds_per_tick = 60.0 / (curr_change.bpm * self.resolution)

            if i + 1 < len(changes):
                next_change = changes[i + 1]
                segment_ticks = next_change.tick - curr_change.tick
                segment_duration = segment_ticks * seconds_per_tick

                if accumulated_seconds + segment_duration >= seconds:
                    remaining_sec = seconds - accumulated_seconds
                    ticks = remaining_sec / seconds_per_tick
                    return int(round(curr_change.tick + ticks))

                accumulated_seconds += segment_duration
            else:
                # Last tempo change extends indefinitely
                remaining_sec = seconds - accumulated_seconds
                ticks = remaining_sec / seconds_per_tick
                return int(round(curr_change.tick + ticks))

        return 0
