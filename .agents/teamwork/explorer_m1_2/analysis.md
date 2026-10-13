# Analysis Report: `NoteQuantizer` Data Structures, Conversion Pipeline & Deduplication

**Agent**: `explorer_m1_2`  
**Milestone**: Phase 4 — Milestone 1 (Quantizer Design)  
**Date**: 2026-10-13  
**Target Recipient**: Milestone 1 Worker (`worker_m1_1` or Orchestrator)

---

## 1. Executive Summary

This investigation designs the core data structures, time-to-tick conversion pipeline, duration computation, deduplication algorithm, and deterministic sorting logic for `NoteQuantizer` (`src/game_design/quantizer.py`).

`NoteQuantizer` acts as the first entry point of Phase 4 (Game Design & Note Mapping Engine), transforming raw acoustic transcription events (`NoteEvent`) into discrete musical units (`QuantizedNote`) synchronized to a Clone Hero 192 PPQ grid via `TempoMap`.

Key design outcomes:
1. **`QuantizedNote` Dataclass**: Immutable, slotted, ordered dataclass (`frozen=True, slots=True, order=True`) with fields `(tick: int, pitch: int, duration_ticks: int, amplitude: float)` and strict bounds validation in `__post_init__`.
2. **Time-to-Tick Conversion**: Accurate conversion of `start_time` and `end_time` using `tempo_map.seconds_to_tick()`, seamlessly supporting piece-wise variable BPM timelines.
3. **Duration Computation**: `duration_ticks = max(1, raw_end_tick - snapped_start_tick)`. Note releases (end ticks) are deliberately **not** snapped to grid subdivisions to prevent artificial sustain elongation and jitter artifacts, preserving true acoustic duration for `SustainProcessor` (Milestone 4).
4. **Deduplication Engine**: $O(N)$ hash-table grouping by `(snapped_start_tick, pitch)` preserving `max(duration_ticks)` and `max(amplitude)`, merging transcription flutter and re-trigger artifacts while strictly preserving simultaneous polyphonic chord notes (distinct pitches at the same tick).
5. **Deterministic Sorting**: Final output sorted by `(tick, pitch)` ascending, ensuring chronological playback and canonical root-to-soprano chord layout.

---

## 2. Data Structure Design: `QuantizedNote`

### 2.1 Specification and Fields

`QuantizedNote` represents an intermediate musical event on the quantized grid prior to fret assignment (`PitchToFretMapper`) and chord structuring (`ChordBuilder`).

```python
@dataclass(frozen=True, slots=True, order=True)
class QuantizedNote:
    """Quantized musical note aligned to a 192 PPQ timeline."""

    tick: int  # Grid tick position (non-negative)
    pitch: int  # MIDI pitch number (0 - 127)
    duration_ticks: int  # Acoustic duration in ticks (>= 1)
    amplitude: float  # Normalized confidence / velocity (0.0 to 1.0)
```

### 2.2 Frozen vs. Mutable Evaluation

| Consideration | `frozen=False` (Mutable) | `frozen=True` (Immutable) | Decision & Rationale |
| :--- | :--- | :--- | :--- |
| **Domain Semantics** | Represents an entity with state changes | Represents a pure value object | **Value object**: A quantized note is a fixed timestamped event on the score. |
| **Hashability & Dict Keys** | Unhashable by default | Automatically hashable (`__hash__` generated) | **Immutable**: Allows instances to be stored in sets or used as hash keys. |
| **Downstream Integrity** | Downstream mappers (`pitch_to_fret.py`) could mutate attributes, causing subtle race conditions | Downstream mappers cannot mutate values accidentally | **Immutable**: Prevents side-effects across the multi-stage pipeline. |
| **Architectural Uniformity** | Inconsistent with existing models | Matches `NoteEvent`, `BPMChange`, `TimeSignature` | **Immutable**: `NoteEvent`, `BPMChange`, and `StarPowerPhrase` are all `frozen=True`. |

**Conclusion**: `QuantizedNote` **must be `frozen=True`**. Downstream modifications (such as fret assignment or sustain trimming) construct new domain entities (`ChartNote`) rather than mutating `QuantizedNote`.

### 2.3 Slotted Dataclass Optimization (`slots=True`)

In Python 3.10+, `@dataclass(slots=True)` replaces `__dict__` with fixed memory slots:
- **Memory reduction**: Cuts per-instance memory overhead from ~152 bytes to ~48 bytes (68% memory savings).
- **Attribute access**: Attribute lookup is ~20% faster due to direct pointer offsets.
- **Strict safety**: Prevents accidental dynamic attribute attachment.

### 2.4 Ordering and Comparison Logic

In Python standard dataclasses, `@dataclass(order=True)` generates `__lt__`, `__le__`, `__gt__`, and `__ge__` by evaluating fields in declaration order:
$$\text{Tuple: } (\text{self.tick}, \text{self.pitch}, \text{self.duration\_ticks}, \text{self.amplitude})$$

1. **Primary Sort Key (`tick`)**: Guarantees chronological sequencing.
2. **Secondary Sort Key (`pitch`)**: Groups chords at the same tick in ascending tonal order (lowest pitch to highest pitch).
3. **Tertiary Keys (`duration_ticks`, `amplitude`)**: Act as deterministic tie-breakers. Because deduplication guarantees uniqueness of `(tick, pitch)`, tertiary keys are never required on deduplicated datasets, but provide complete deterministic ordering on arbitrary collections.

Compared to writing a manual `__lt__` method:
- `order=True` is native, C-accelerated in CPython 3.11, and requires 0 lines of boilerplate.
- Fully supported by `mypy` strict type checking.

### 2.5 Validation Invariants (`__post_init__`)

To prevent malformed data from propagating into the game design engine, `__post_init__` enforces strict bounds:

```python
def __post_init__(self) -> None:
    if self.tick < 0:
        raise ValueError(f"tick must be non-negative, got {self.tick}")
    if not (0 <= self.pitch <= 127):
        raise ValueError(f"pitch must be between 0 and 127, got {self.pitch}")
    if self.duration_ticks < 1:
        raise ValueError(f"duration_ticks must be at least 1, got {self.duration_ticks}")
    if not (0.0 <= self.amplitude <= 1.0):
        raise ValueError(f"amplitude must be between 0.0 and 1.0, got {self.amplitude}")
```

- Note: Because `self.duration_ticks` represents full acoustic duration, every real acoustic event has at least 1 tick of duration. `sustain_length = 0` (instant notes) is only applied later in `ChartNote` by `SustainProcessor`.

---

## 3. Conversion Pipeline Design: `quantize()`

### 3.1 Method Contract

```python
def quantize(
    self,
    notes: list[NoteEvent],
    tempo_map: TempoMap,
) -> list[QuantizedNote]:
    """Quantize raw NoteEvents into 192 PPQ grid-aligned QuantizedNotes.

    Args:
        notes: List of raw polyphonic NoteEvents extracted from audio.
        tempo_map: Rhythmic TempoMap providing variable BPM synchronization.

    Returns:
        List of QuantizedNotes snapped to subdivisions, deduplicated by
        (tick, pitch) with max amplitude and duration, sorted by (tick, pitch).
    """
```

### 3.2 Time-to-Tick Conversion via `TempoMap`

`NoteEvent` provides continuous floating-point timestamps in seconds:
- `note.start_time`: Note onset in seconds.
- `note.end_time`: Note release in seconds.

`TempoMap.seconds_to_tick(seconds: float) -> int` in `src/models/tempo.py` handles:
1. Sequential lookup across `self.bpm_changes` segments.
2. Accumulation of elapsed seconds per tempo segment.
3. Micro-second conversion: $\text{seconds\_per\_tick} = \frac{60.0}{\text{bpm} \times \text{resolution}}$.
4. Half-to-even rounding: `int(round(curr_change.tick + ticks))`.

Therefore, the conversion in `NoteQuantizer` is:
```python
raw_start_tick = tempo_map.seconds_to_tick(note.start_time)
raw_end_tick = tempo_map.seconds_to_tick(note.end_time)
```

**Edge Case: `raw_end_tick <= raw_start_tick`**:
While `NoteEvent` guarantees `end_time > start_time` in float seconds, an extremely brief transient (e.g. 1 ms at 60 BPM where 1 tick = 5.2 ms) might result in `raw_end_tick == raw_start_tick` due to integer tick rounding. The duration formula must account for this.

### 3.3 Grid Snapping Integration

The onset tick is snapped using the 16-tick tolerance window algorithm designed by `explorer_m1_1`:
```python
snapped_start_tick = self.snap_tick(raw_start_tick)
```
Where `snap_tick` checks candidates $\{s_1, s_2, t_1, t_2\}$ on the straight (24-tick) and triplet (32-tick) grids, selecting the closest within `tolerance_ticks = 16` and breaking equidistant ties via musical priority.

---

## 4. Duration Computation Analysis

The prompt requires evaluating:
> "How should `duration_ticks` be computed? Should duration also be snapped or preserved as raw tick duration? (Consider `max(1, end_tick - snapped_tick)` vs snapped end tick)."

### 4.1 Comparative Analysis of Alternatives

| Approach | Formula | Pros | Cons | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| **Approach 1: Relative to Snapped Onset (Recommended)** | `duration_ticks = max(1, raw_end_tick - snapped_start_tick)` | 1. If a note released at an exact grid boundary, snapping onset restores the full intended musical duration.<br>2. Preserves physical offset point: $\text{snapped} + \text{dur} = \text{end}$.<br>3. Naturally prevents negative spans with `max(1, ...)`. | If onset snapped forward past `raw_end_tick`, duration is clamped to 1 tick. | **Selected & Recommended** |
| **Approach 2: Pure Acoustic Duration** | `duration_ticks = max(1, raw_end_tick - raw_start_tick)` | 1. Exactly preserves acoustic duration measured by transcription model.<br>2. Independent of onset snapping distance. | If musician started late (tick 50 $\to$ 48) and ended on-beat (tick 96), raw duration (46 ticks) remains 2 ticks short of a clean 1/16th note. | Viable fallback, but inferior musical alignment |
| **Approach 3: Snapping Both Start and End Ticks** | `snapped_end = snap_tick(raw_end)`<br>`duration_ticks = max(1, snapped_end - snapped_start)` | Enforces clean grid alignment on both ends. | **Harmful in practice**: Audio transcription offsets (Basic Pitch) are noisy (20-50ms decay tail variance). Snapping to a 24-tick (31ms) grid artificially forces random decay tails into 32nd/16th boundaries, frequently inflating staccato notes (e.g., 80 ticks $\to$ 96 ticks) and triggering false sustains. | **Rejected** |

### 4.2 Why Note Offsets Must NOT Be Snapped

1. **Acoustic Reality vs Score Representation**:
   In guitar audio, note onsets are sharp, percussive transients easily localized in time. In contrast, note offsets are gradual amplitude decays influenced by string resonance, amplifier distortion, and reverberation. Basic Pitch sets offsets when energy falls below `frame_threshold` (0.3). This offset has inherent acoustic jitter ($\pm 30\text{ ms}$).
2. **Preventing False Sustains**:
   According to `AGENTS.md` §7.5 and `SCOPE.md` §R4.3:
   - Notes $< 90$ ticks: `sustain_length = 0` (staccato / non-sustained).
   - Notes $\ge 90$ ticks: sustained, cutting 24-tick release margin.
   If note offsets were snapped to the nearest 1/16th (48) or 1/32nd (24) grid point, an 82-tick staccato note would snap to 96 ticks, incorrectly converting a staccato note into a sustain note with playable tail!
3. **Pipeline Division of Labor**:
   Downstream milestone `SustainProcessor` (Milestone 4) is specifically dedicated to sustain duration logic (thresholding at 90 ticks, clamping before subsequent notes, cutting 24 ticks release margin). `NoteQuantizer` must provide faithful, acoustic duration in ticks without premature distortion.

### 4.3 Clamping Invariant

The formula:
$$\text{duration\_ticks} = \max(1, \text{raw\_end\_tick} - \text{snapped\_start\_tick})$$
guarantees:
- $\text{duration\_ticks} \ge 1$ for all valid inputs.
- Even if a short transient note snaps forward past its end time (e.g. onset 46 snapped to 48, note ended at 47), the resulting duration is safely clamped to 1 tick without violating `QuantizedNote` invariants.

---

## 5. Deduplication and Event Aggregation

### 5.1 Polyphonic Transcription Artifacts

Audio-to-MIDI transcription (Basic Pitch) often produces:
1. **Frame Dropping / Jitter**: A single plucked note where pitch confidence dips momentarily across an 11 ms frame, creating two adjacent `NoteEvent`s of the same pitch (e.g. at 0.122s and 0.128s). Both snap to the same tick (48).
2. **Overlapping Harmonics**: Harmonic overtones surviving filter stages with identical pitch at the same time slice.

### 5.2 Deduplication Invariant & Key

The deduplication key is the tuple:
$$\text{key} = (\text{snapped\_start\_tick}, \text{pitch})$$

- Notes with **identical** `(snapped_start_tick, pitch)` are duplicate representations of the same fret strike and **must be merged**.
- Notes with **identical** `snapped_start_tick` but **distinct** `pitch` represent harmonic chords (e.g., Root + Fifth, $E_2=40$ and $B_2=47$) and **must be preserved** as separate entries.

### 5.3 Merge Logic: Max Amplitude & Max Duration

Requirement R1.3 mandates:
> "Merge duplicate (tick, pitch) notes taking max amplitude and max duration"

When merging duplicate notes $A$ and $B$:
$$\text{merged\_amplitude} = \max(A.\text{amplitude}, B.\text{amplitude})$$
$$\text{merged\_duration} = \max(A.\text{duration\_ticks}, B.\text{duration\_ticks})$$

- Preserving `max(amplitude)` ensures that the strongest onset velocity / transcription confidence is retained.
- Preserving `max(duration_ticks)` ensures that the full acoustic sustain is not prematurely cut off by an early-terminating duplicate fragment.

### 5.4 Algorithmic Implementation

Using an aggregation dictionary:
```python
dedup_map: dict[tuple[int, int], tuple[int, float]] = {}

for note in notes:
    raw_start = tempo_map.seconds_to_tick(note.start_time)
    snapped_start = self.snap_tick(raw_start)
    raw_end = tempo_map.seconds_to_tick(note.end_time)
    dur_ticks = max(1, raw_end - snapped_start)

    key = (snapped_start, note.pitch)
    if key not in dedup_map:
        dedup_map[key] = (dur_ticks, note.amplitude)
    else:
        prev_dur, prev_amp = dedup_map[key]
        dedup_map[key] = (max(prev_dur, dur_ticks), max(prev_amp, note.amplitude))
```

- **Time Complexity**: $O(N)$ where $N$ is the number of input `NoteEvent`s.
- **Space Complexity**: $O(M)$ where $M \le N$ is the number of unique `(tick, pitch)` notes.

---

## 6. Deterministic Output Sorting

### 6.1 Sorting Requirement

The output of `quantize()` must be deterministically sorted by:
1. **Primary**: `tick` ascending.
2. **Secondary**: `pitch` ascending.

```python
result = [
    QuantizedNote(
        tick=tick,
        pitch=pitch,
        duration_ticks=dur,
        amplitude=amp,
    )
    for (tick, pitch), (dur, amp) in dedup_map.items()
]
result.sort()  # Relies on @dataclass(order=True) comparing (tick, pitch, dur, amp)
```

### 6.2 Downstream Pipeline Rationale

1. **`PitchToFretMapper` (Milestone 2)**:
   - Processes notes chronologically in sliding windows of 1536 ticks (~2 measures).
   - Enforces rapid passage jump constraints: if $\text{tick} - \text{prev\_tick} < 48$, fret jump $\le 3$.
   - Strict chronological ordering is mandatory.
2. **`ChordBuilder` (Milestone 3)**:
   - Groups notes occurring at the same `tick` into chord candidates.
   - Requires notes sorted by `pitch` so that the lowest pitch is processed as the chord root/bass note, enabling canonical power chord shapes (e.g. 0+1, 0+2, 1+3) and discarding higher dissonant clutter.

---

## 7. Complete Architecture Recommendation for Worker

Below is the complete, production-ready implementation plan for `src/game_design/quantizer.py` and `src/game_design/__init__.py`.

### 7.1 Proposed `src/game_design/quantizer.py`

```python
"""Musical quantization and grid snapping engine for Clone Hero charts."""

from dataclasses import dataclass
from typing import Final

from src.models.midi_events import NoteEvent
from src.models.tempo import TempoMap

# Subdivision priorities for resolving equidistant grid ties.
# Higher priority indicates a more fundamental musical division.
_PRIORITY_QUARTER: Final[int] = 6  # 192 PPQ (1/4 note)
_PRIORITY_EIGHTH: Final[int] = 5  # 96 PPQ (1/8 note)
_PRIORITY_SIXTEENTH: Final[int] = 4  # 48 PPQ (1/16 note)
_PRIORITY_EIGHTH_TRIPLET: Final[int] = 3  # 64 PPQ (1/12 note)
_PRIORITY_SIXTEENTH_TRIPLET: Final[int] = 2  # 32 PPQ (1/24 note)
_PRIORITY_THIRTY_SECOND: Final[int] = 1  # 24 PPQ (1/32 note)


@dataclass(frozen=True, slots=True, order=True)
class QuantizedNote:
    """A quantized musical note aligned to the 192 PPQ grid."""

    tick: int  # Snapped grid position in ticks (>= 0)
    pitch: int  # MIDI note number (0 - 127)
    duration_ticks: int  # Acoustic duration in ticks (>= 1)
    amplitude: float  # Normalized velocity / confidence (0.0 to 1.0)

    def __post_init__(self) -> None:
        if self.tick < 0:
            raise ValueError(f"tick must be non-negative, got {self.tick}")
        if not (0 <= self.pitch <= 127):
            raise ValueError(f"pitch must be between 0 and 127, got {self.pitch}")
        if self.duration_ticks < 1:
            raise ValueError(f"duration_ticks must be at least 1, got {self.duration_ticks}")
        if not (0.0 <= self.amplitude <= 1.0):
            raise ValueError(f"amplitude must be between 0.0 and 1.0, got {self.amplitude}")


class NoteQuantizer:
    """Snaps continuous NoteEvents to a 192 PPQ musical grid and deduplicates."""

    def __init__(
        self,
        tolerance_ticks: int = 16,
        resolution: int = 192,
    ) -> None:
        """Initialize NoteQuantizer.

        Args:
            tolerance_ticks: Maximum tick distance to snap to a grid point.
                Defaults to 16 ticks.
            resolution: Ticks per quarter note (PPQ). Defaults to 192.
        """
        if tolerance_ticks < 0:
            raise ValueError(f"tolerance_ticks must be non-negative, got {tolerance_ticks}")
        if resolution <= 0:
            raise ValueError(f"resolution must be positive, got {resolution}")

        self.tolerance_ticks = tolerance_ticks
        self.resolution = resolution

    @staticmethod
    def _get_grid_priority(tick: int) -> int:
        """Return musical hierarchy priority for tie-breaking equidistant grid points."""
        if tick % 192 == 0:
            return _PRIORITY_QUARTER
        if tick % 96 == 0:
            return _PRIORITY_EIGHTH
        if tick % 48 == 0:
            return _PRIORITY_SIXTEENTH
        if tick % 64 == 0:
            return _PRIORITY_EIGHTH_TRIPLET
        if tick % 32 == 0:
            return _PRIORITY_SIXTEENTH_TRIPLET
        if tick % 24 == 0:
            return _PRIORITY_THIRTY_SECOND
        return 0

    def snap_tick(self, tick: int) -> int:
        """Snap a raw tick position to the nearest 192 PPQ subdivision.

        Subdivisions checked:
        - Straight: 192 (1/4), 96 (1/8), 48 (1/16), 24 (1/32) -> step 24
        - Triplet: 64 (1/12), 32 (1/24) -> step 32

        Args:
            tick: Raw tick position.

        Returns:
            Snapped non-negative tick, or max(0, tick) if outside tolerance window.
        """
        t = int(round(tick))
        if t <= 0:
            return 0

        # Candidate straight grid points (multiples of 24)
        s1 = (t // 24) * 24
        s2 = s1 + 24

        # Candidate triplet grid points (multiples of 32)
        t1 = (t // 32) * 32
        t2 = t1 + 32

        candidates = {s1, s2, t1, t2}
        valid_candidates = [
            c for c in candidates if c >= 0 and abs(c - t) <= self.tolerance_ticks
        ]

        if not valid_candidates:
            return max(0, t)

        # Tie-breaker key:
        # 1. Primary: minimum absolute distance to candidate
        # 2. Secondary: maximum musical priority (-priority)
        # 3. Tertiary: smaller tick value
        return min(
            valid_candidates,
            key=lambda c: (abs(c - t), -self._get_grid_priority(c), c),
        )

    def quantize(
        self,
        notes: list[NoteEvent],
        tempo_map: TempoMap,
    ) -> list[QuantizedNote]:
        """Quantize and deduplicate NoteEvents into 192 PPQ grid QuantizedNotes.

        Args:
            notes: List of raw NoteEvents extracted from audio.
            tempo_map: TempoMap for timestamp to tick conversion.

        Returns:
            Chronologically sorted, deduplicated list of QuantizedNotes.
        """
        if not notes:
            return []

        # Deduplication map: (snapped_tick, pitch) -> (max_duration_ticks, max_amplitude)
        dedup_map: dict[tuple[int, int], tuple[int, float]] = {}

        for note in notes:
            raw_start = tempo_map.seconds_to_tick(note.start_time)
            snapped_start = self.snap_tick(raw_start)

            raw_end = tempo_map.seconds_to_tick(note.end_time)
            dur_ticks = max(1, raw_end - snapped_start)

            key = (snapped_start, note.pitch)
            if key not in dedup_map:
                dedup_map[key] = (dur_ticks, note.amplitude)
            else:
                prev_dur, prev_amp = dedup_map[key]
                dedup_map[key] = (
                    max(prev_dur, dur_ticks),
                    max(prev_amp, note.amplitude),
                )

        quantized_notes = [
            QuantizedNote(
                tick=tick,
                pitch=pitch,
                duration_ticks=dur,
                amplitude=amp,
            )
            for (tick, pitch), (dur, amp) in dedup_map.items()
        ]

        quantized_notes.sort()
        return quantized_notes
```

### 7.2 Proposed `src/game_design/__init__.py`

```python
"""Game design mapping intelligence for Clone Hero."""

from src.game_design.quantizer import NoteQuantizer, QuantizedNote

__all__ = [
    "NoteQuantizer",
    "QuantizedNote",
]
```

---

## 8. Summary of Interface Guarantees

| Invariant | Implementation Mechanism | Validation |
| :--- | :--- | :--- |
| **Grid Alignment** | `snap_tick(raw_start)` | Snaps to {192, 96, 64, 48, 32, 24} multiples within $\le 16$ ticks |
| **Non-Negative Ticks** | `snap_tick` returns $\ge 0$; `QuantizedNote.__post_init__` checks `tick >= 0` | `ValueError` if `tick < 0` |
| **Positive Duration** | `max(1, raw_end - snapped_start)` | `duration_ticks >= 1` guaranteed |
| **Pitch Bounds** | Preserves MIDI 0-127 | `ValueError` if `pitch < 0 or pitch > 127` |
| **Velocity Bounds** | Preserves normalized 0.0 - 1.0 | `ValueError` if `amplitude < 0.0 or amplitude > 1.0` |
| **No Same-Pitch Duplicates** | Dictionary key `(snapped_start, note.pitch)` | Exactly 1 note per `(tick, pitch)` |
| **Chords Preserved** | Different pitches at same tick have distinct dict keys | Multiple notes with identical `tick` but distinct pitches retained |
| **Deterministic Order** | `result.sort()` using `(tick, pitch, duration, amplitude)` | Identical output regardless of input array ordering |
