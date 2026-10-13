# Specification Report: Musical Quantization & Grid Snapping (Milestone 1)

**Target Module**: `src/game_design/quantizer.py`  
**Target Test Suite**: `tests/test_game_design/test_quantizer.py`  
**Author**: `spec_miner_m1` (Specification Miner)  
**Date**: 2026-10-13  
**Status**: Completed  

---

## 1. Executive Summary

Milestone 1 implements the first stage of the Phase 4 Game Design pipeline for Clone Hero chart generation: **Musical Quantization and Grid Snapping**.
The module converts raw polyphonic transcription events (`NoteEvent`) into musically aligned grid notes (`QuantizedNote`) using a rhythmic synchronization map (`TempoMap`).

Key constraints and behaviors:
1. **192 PPQ Resolution**: Standard Clone Hero resolution (192 pulses per quarter note).
2. **Subdivision Support**: Grid snapping to 1/4 (192), 1/8 (96), 1/12 (64), 1/16 (48), 1/24 (32), and 1/32 (24) note intervals.
3. **Tolerance Window (16 ticks)**: Onsets within `abs(distance) <= 16` ticks of any active grid subdivision snap to the closest grid point; onsets beyond 16 ticks remain unsnapped at their raw tick position.
4. **Deduplication**: Simultaneous notes with identical `(tick, pitch)` are merged by taking the maximum amplitude and maximum duration, while distinct pitches at the same tick (chords) are strictly preserved.
5. **Multi-Tempo Robustness**: Accurate seconds-to-tick conversion across dynamic BPM changes and time signature boundaries.

---

## 2. Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | R1.1 Grid Snapping | Quarter Note (1/4) Snapping | Snaps onsets within 16 ticks to multiples of 192 ticks | `NoteEvent` near $k \cdot 192$, `TempoMap` | `QuantizedNote(tick=k*192)` | Preserves raw tick if dist > 16 | PROMPTS.md 4.1, AGENTS.md §7.1 |
| 2 | R1.1 Grid Snapping | Eighth Note (1/8) Snapping | Snaps onsets within 16 ticks to multiples of 96 ticks | `NoteEvent` near $k \cdot 96$, `TempoMap` | `QuantizedNote(tick=k*96)` | Preserves raw tick if dist > 16 | PROMPTS.md 4.1, AGENTS.md §7.1 |
| 3 | R1.1 Grid Snapping | Twelfth Triplet (1/12) Snapping | Snaps onsets within 16 ticks to multiples of 64 ticks (quarter note triplets) | `NoteEvent` near $k \cdot 64$, `TempoMap` | `QuantizedNote(tick=k*64)` | Preserves raw tick if dist > 16 | PROMPTS.md 4.1, AGENTS.md §7.1 |
| 4 | R1.1 Grid Snapping | Sixteenth Note (1/16) Snapping | Snaps onsets within 16 ticks to multiples of 48 ticks (e.g. tick 50 -> 48) | `NoteEvent` near $k \cdot 48$, `TempoMap` | `QuantizedNote(tick=k*48)` | Preserves raw tick if dist > 16 | PROMPTS.md 4.1, AGENTS.md §7.1 |
| 5 | R1.1 Grid Snapping | Twenty-Fourth Triplet (1/24) Snapping | Snaps onsets within 16 ticks to multiples of 32 ticks (sextuplets) | `NoteEvent` near $k \cdot 32$, `TempoMap` | `QuantizedNote(tick=k*32)` | Preserves raw tick if dist > 16 | PROMPTS.md 4.1, AGENTS.md §7.1 |
| 6 | R1.1 Grid Snapping | Thirty-Second Note (1/32) Snapping | Snaps onsets within 16 ticks to multiples of 24 ticks (fusas) | `NoteEvent` near $k \cdot 24$, `TempoMap` | `QuantizedNote(tick=k*24)` | Preserves raw tick if dist > 16 | PROMPTS.md 4.1, AGENTS.md §7.1 |
| 7 | R1.2 Tolerance | Tolerance Window Boundary Enforcement | Strict threshold: $\le 16$ ticks snaps; $> 16$ ticks preserves raw tick position | `raw_tick` with distance $\le 16$ vs $> 16$ | Snapped tick or raw tick | Unsnapped if distance exceeds threshold | ORIGINAL_REQUEST §R1, SCOPE.md |
| 8 | R1.2 Tolerance | Custom Tolerance Configuration | Configurable `tolerance_ticks` parameter (e.g., 8, 12, 16) | `tolerance_ticks: int` in constructor/call | Applies custom threshold | Rejects negative tolerance | SCOPE.md, PROMPTS.md 4.1 |
| 9 | R1.3 Deduplication | Identical `(tick, pitch)` Merge | Merges duplicate notes at same tick and pitch into a single event | Multiple notes with identical `(tick, pitch)` | 1 `QuantizedNote` with `max(amplitude)` and `max(duration_ticks)` | None (clean merge) | ORIGINAL_REQUEST §R1, SCOPE.md |
| 10 | R1.3 Deduplication | Polyphonic Chord Preservation | Retains multiple notes at the same tick if their MIDI pitches differ | Notes with same `tick` but different `pitch` | Distinct `QuantizedNote` instances at same tick | None (all pitches kept) | AGENTS.md §7.3, SCOPE.md |
| 11 | R1.4 Synchronization | Variable BPM / Multi-Tempo Mapping | Converts timestamps to ticks accurately across multiple BPM change events | `NoteEvent`s across BPM transition ticks | Accurate tick alignment according to segment tempo | Handled via `TempoMap.seconds_to_tick()` | AGENTS.md §5.2, SCOPE.md |
| 12 | R1.5 Empty & Bounds | Empty Input Handling | Safely handles empty input note lists without exceptions | `notes = []` | `[]` (empty list) | Graceful return, no crash | Python / Pytest best practice |
| 13 | R1.5 Empty & Bounds | Chronological Sorting Guarantee | Ensures output notes are sorted chronologically by `tick`, then by `pitch` | Unsorted or out-of-order `NoteEvent` list | Chronologically sorted list of `QuantizedNote` | Deterministic ordering | SCOPE.md, Clone Hero chart spec |
| 14 | Model Contract | `QuantizedNote` Data Validation | Validates fields: `tick >= 0`, `0 <= pitch <= 127`, `duration_ticks >= 0`, `0.0 <= amplitude <= 1.0` | Constructor arguments | Valid instance | Raises `ValueError` on out-of-range fields | src/models/midi_events.py pattern |

---

## 3. Edge Cases

| # | Feature | Input | Observed Behavior |
|---|---------|-------|-------------------|
| 1 | Tolerance Window | `raw_tick` exactly 16 ticks away from grid point (e.g., 208 for 192 grid) | Snaps to 192 because $208 - 192 = 16 \le 16$ (inclusive boundary). |
| 2 | Tolerance Window | `raw_tick` exactly 17 ticks away from grid point (e.g., 209 for 192 grid) | Remains unsnapped at 209 because $209 - 192 = 17 > 16$. |
| 3 | Tolerance Window | `raw_tick` with 1/16 grid (48 ticks) at midpoint tick 24 | Distance to 0 is 24, distance to 48 is 24; since $24 > 16$, remains unsnapped at 24. |
| 4 | Tolerance Window | Custom `tolerance_ticks = 8` with 1/32 grid (24 ticks) at tick 12 | Distance to 0 is 12, distance to 24 is 12; since $12 > 8$, remains unsnapped at 12. |
| 5 | Deduplication | 3 duplicate notes with pitches `[60, 60, 60]`, amps `[0.3, 0.9, 0.5]`, durs `[96, 24, 48]` | Merged into 1 note with `pitch=60`, `amplitude=0.9`, `duration_ticks=96`. |
| 6 | Deduplication | 2 notes at same tick with different pitches `[60, 67]` (power chord root + 5th) | Both notes preserved at identical tick; output length is 2. |
| 7 | Deduplication | Same pitch `60` at different ticks (e.g., 0 and 96) | Both notes preserved; output length is 2. |
| 8 | Empty List | `notes = []` | Returns `[]` without raising errors. |
| 9 | Single Note | Single `NoteEvent(start_time=0.5, end_time=1.0, pitch=60, amplitude=0.8)` | Returns `[QuantizedNote(tick=192, pitch=60, duration_ticks=192, amplitude=0.8)]`. |
| 10 | Unsorted Inputs | `NoteEvent` list with timestamps `[2.0, 0.5, 0.0]` | Output is strictly sorted by `tick`: `[0, 192, 768]`. |
| 11 | Variable Tempo | Note onset at 2.433s across 120 -> 140 BPM transition at tick 768 | Accurately mapped to tick 962 in the 140 BPM section, then snapped to 960. |
| 12 | Zero Duration | `NoteEvent` with `end_time == start_time + 0.001` yielding `duration_ticks = 0` | Supported with `duration_ticks = 0`. |

---

## 4. Architectural & Mathematical Specifications

### 4.1. Tick Conversion Formulas
For a constant tempo segment with $B$ BPM and resolution $R = 192$ PPQ:
$$\text{Seconds per tick} = \frac{60.0}{B \times R}$$
$$\text{Tick from seconds} = \text{round}\left( \frac{\text{seconds} \times B \times R}{60.0} \right)$$

At $B = 120$ BPM and $R = 192$:
$$\text{Seconds per tick} = \frac{60.0}{120 \times 192} = \frac{1}{384} \approx 0.002604167 \text{ s}$$
$$\text{Tick} = \text{round}(\text{seconds} \times 384)$$

For multi-tempo timelines with BPM change events $[(\text{tick}_0, B_0), (\text{tick}_1, B_1), \dots]$:
The conversion delegates to `TempoMap.seconds_to_tick(seconds)` which piecewise integrates accumulated segment durations.

### 4.2. Snapping Algorithm
Let the active musical subdivisions be $S = [s_1, s_2, \dots, s_k]$, where default $S = [192, 96, 64, 48, 32, 24]$.
For a given `raw_tick`:
1. For each subdivision $s \in S$:
   $$k = \text{round}\left( \frac{\text{raw\_tick}}{s} \right)$$
   $$\text{candidate} = k \times s$$
   $$\text{distance} = |\text{candidate} - \text{raw\_tick}|$$
2. Identify the candidate $p^*$ that minimizes distance $d^* = |p^* - \text{raw\_tick}|$. (If distances are tied, the larger subdivision or lower tick may break ties).
3. If $d^* \le \text{tolerance\_ticks}$ (default 16):
   $$\text{snapped\_tick} = p^*$$
   Else:
   $$\text{snapped\_tick} = \text{raw\_tick}$$

### 4.3. Deduplication Algorithm
1. Map or group quantized notes by key `(tick, pitch)`.
2. For all notes sharing key `(tick, pitch)`:
   $$\text{merged\_amplitude} = \max_{n} (n.\text{amplitude})$$
   $$\text{merged\_duration} = \max_{n} (n.\text{duration\_ticks})$$
3. Sort unique notes by `(tick, pitch)`.

---

## 5. Interface Contracts

### 5.1. `QuantizedNote` Dataclass
```python
from dataclasses import dataclass

@dataclass(frozen=True)
class QuantizedNote:
    """A musically quantized note event ready for fret projection."""

    tick: int  # Snapped grid tick (non-negative)
    pitch: int  # MIDI pitch (0 - 127)
    duration_ticks: int  # Duration in ticks (non-negative)
    amplitude: float  # Normalized velocity/confidence (0.0 to 1.0)

    def __post_init__(self) -> None:
        if self.tick < 0:
            raise ValueError(f"tick must be non-negative, got {self.tick}")
        if not (0 <= self.pitch <= 127):
            raise ValueError(f"pitch must be between 0 and 127, got {self.pitch}")
        if self.duration_ticks < 0:
            raise ValueError(f"duration_ticks must be non-negative, got {self.duration_ticks}")
        if not (0.0 <= self.amplitude <= 1.0):
            raise ValueError(f"amplitude must be between 0.0 and 1.0, got {self.amplitude}")
```

### 5.2. `NoteQuantizer` Class
```python
from collections.abc import Sequence
from src.models import NoteEvent, TempoMap

class NoteQuantizer:
    """Snaps transcribed NoteEvents to 192 PPQ subdivisions and deduplicates."""

    DEFAULT_SUBDIVISIONS: tuple[int, ...] = (192, 96, 64, 48, 32, 24)
    DEFAULT_TOLERANCE_TICKS: int = 16

    def __init__(
        self,
        subdivisions: Sequence[int] | None = None,
        tolerance_ticks: int = 16,
    ) -> None:
        if tolerance_ticks < 0:
            raise ValueError(f"tolerance_ticks must be non-negative, got {tolerance_ticks}")
        self.subdivisions = tuple(subdivisions) if subdivisions is not None else self.DEFAULT_SUBDIVISIONS
        self.tolerance_ticks = tolerance_ticks

    def snap_tick(self, raw_tick: int) -> int:
        """Snap a raw tick to the nearest active subdivision point within tolerance."""
        ...

    def quantize(
        self,
        notes: list[NoteEvent],
        tempo_map: TempoMap,
    ) -> list[QuantizedNote]:
        """Convert, snap, deduplicate, and sort NoteEvents into QuantizedNotes."""
        ...
```

---

## 6. Test Suite Plan for `tests/test_game_design/test_quantizer.py`

### 6.1. Pytest Fixtures
1. `tempo_map_120() -> TempoMap`: Constant 120 BPM tempo map (`resolution=192`, `bpm_changes=[BPMChange(0, 120.0)]`, `time_signatures=[TimeSignature(0, 4, 4)]`).
2. `variable_tempo_map() -> TempoMap`: Multi-tempo map with 120 BPM at tick 0 and 140 BPM at tick 768.
3. `quantizer() -> NoteQuantizer`: Standard `NoteQuantizer(tolerance_ticks=16)`.
4. Helper `make_note(...) -> NoteEvent`: Utility function that generates a `NoteEvent` with exact ticks, optional jitter, and duration.

### 6.2. Test Function Enumeration
The test suite consists of **15 specialized test functions** covering all 10 required categories and model constraints:

1. `test_quantize_quarter_notes_exact`: Onsets at 0, 192, 384, 576, 768 snap exactly.
2. `test_quantize_quarter_notes_with_jitter`: Onsets with jitter (early by 10, late by 12, late by 16) snap to multiples of 192.
3. `test_quantize_eighth_notes_exact`: Onsets at 0, 96, 192, 288 snap exactly.
4. `test_quantize_eighth_notes_with_jitter`: Onsets with jitter (early by 8, late by 9) snap to multiples of 96.
5. `test_quantize_twelfth_triplets_exact`: Onsets at 0, 64, 128, 192 (quarter note triplets) snap exactly.
6. `test_quantize_twelfth_triplets_with_jitter`: Onsets with jitter (early by 5, late by 6) snap to multiples of 64.
7. `test_quantize_sixteenth_notes_exact`: Onsets at 0, 48, 96, 144 snap exactly.
8. `test_quantize_sixteenth_notes_with_jitter`: Onset at 50 ticks (Prompt 4.1 prompt case) snaps to 48; onset at 43 snaps to 48.
9. `test_quantize_twenty_fourth_triplets_exact`: Onsets at 0, 32, 64, 96, 128, 160 snap exactly.
10. `test_quantize_twenty_fourth_triplets_with_jitter`: Onsets with jitter (early by 3, late by 4) snap to multiples of 32.
11. `test_quantize_thirty_second_notes_exact_and_jitter`: Onsets at 0, 24, 48, 72, 96, 120 with small jitters snap to multiples of 24.
12. `test_quantize_outside_tolerance_remains_unsnapped`: Explicit tolerance window testing:
    - Distance $= 16$ snaps.
    - Distance $= 17$ remains unsnapped.
    - Custom tolerance (`tolerance_ticks=8`) at distance 12 remains unsnapped.
13. `test_deduplication_identical_tick_and_pitch`: Duplicate notes at same tick and pitch merge, keeping max amplitude and max duration.
14. `test_deduplication_preserves_distinct_pitches_and_ticks`: Chords at same tick preserved; same pitch at different ticks preserved.
15. `test_empty_note_list_and_sorting`: Empty list returns empty; out-of-order notes are sorted chronologically.
16. `test_multi_tempo_map_variable_bpm`: Verifies proper tick calculation across 120 BPM -> 140 BPM transition.
17. `test_quantized_note_model_validation`: Verifies dataclass field validation raises `ValueError` on invalid inputs.

---

## 7. Recommended Test Code Implementation

Below is the complete, conforming source code for `tests/test_game_design/test_quantizer.py`:

```python
"""Unit tests for musical quantization and grid snapping (NoteQuantizer)."""

import pytest

from src.game_design.quantizer import NoteQuantizer, QuantizedNote
from src.models import BPMChange, NoteEvent, TempoMap, TimeSignature


@pytest.fixture
def tempo_map_120() -> TempoMap:
    """Return a standard 120 BPM tempo map (192 PPQ)."""
    return TempoMap(
        resolution=192,
        bpm_changes=[BPMChange(tick=0, bpm=120.0)],
        time_signatures=[TimeSignature(tick=0, numerator=4, denominator=4)],
    )


@pytest.fixture
def variable_tempo_map() -> TempoMap:
    """Return a multi-tempo map: 120 BPM until measure 2 (tick 768), then 140 BPM."""
    return TempoMap(
        resolution=192,
        bpm_changes=[
            BPMChange(tick=0, bpm=120.0),
            BPMChange(tick=768, bpm=140.0),
        ],
        time_signatures=[TimeSignature(tick=0, numerator=4, denominator=4)],
    )


@pytest.fixture
def quantizer() -> NoteQuantizer:
    """Return a default NoteQuantizer with 16-tick tolerance."""
    return NoteQuantizer(tolerance_ticks=16)


def _make_note(
    start_tick: int,
    duration_ticks: int = 96,
    pitch: int = 60,
    amplitude: float = 0.8,
    jitter_ticks: int = 0,
    tempo_map: TempoMap | None = None,
) -> NoteEvent:
    """Helper to synthesize a NoteEvent at an exact grid tick with optional jitter."""
    if tempo_map is None:
        tempo_map = TempoMap(resolution=192, bpm_changes=[BPMChange(tick=0, bpm=120.0)])

    start_sec = tempo_map.tick_to_seconds(start_tick + jitter_ticks)
    end_sec = tempo_map.tick_to_seconds(start_tick + jitter_ticks + duration_ticks)
    return NoteEvent(
        start_time=start_sec,
        end_time=end_sec,
        pitch=pitch,
        amplitude=amplitude,
    )


def test_quantize_quarter_notes_exact(quantizer: NoteQuantizer, tempo_map_120: TempoMap) -> None:
    """Validate snapping for exact quarter notes (multiples of 192 ticks)."""
    notes = [
        _make_note(start_tick=0, tempo_map=tempo_map_120),
        _make_note(start_tick=192, tempo_map=tempo_map_120),
        _make_note(start_tick=384, tempo_map=tempo_map_120),
        _make_note(start_tick=576, tempo_map=tempo_map_120),
    ]

    result = quantizer.quantize(notes, tempo_map_120)
    assert len(result) == 4
    assert [n.tick for n in result] == [0, 192, 384, 576]


def test_quantize_quarter_notes_with_jitter(
    quantizer: NoteQuantizer, tempo_map_120: TempoMap
) -> None:
    """Validate snapping for slightly jittered quarter notes within 16 ticks."""
    notes = [
        _make_note(start_tick=192, jitter_ticks=-10, tempo_map=tempo_map_120),  # tick 182 -> 192
        _make_note(start_tick=384, jitter_ticks=12, tempo_map=tempo_map_120),  # tick 396 -> 384
        _make_note(start_tick=576, jitter_ticks=16, tempo_map=tempo_map_120),  # tick 592 -> 576
    ]

    result = quantizer.quantize(notes, tempo_map_120)
    assert [n.tick for n in result] == [192, 384, 576]


def test_quantize_eighth_notes_exact_and_jitter(
    quantizer: NoteQuantizer, tempo_map_120: TempoMap
) -> None:
    """Validate snapping for eighth notes (multiples of 96 ticks) with and without jitter."""
    notes = [
        _make_note(start_tick=0, jitter_ticks=0, tempo_map=tempo_map_120),
        _make_note(start_tick=96, jitter_ticks=-8, tempo_map=tempo_map_120),  # tick 88 -> 96
        _make_note(start_tick=192, jitter_ticks=0, tempo_map=tempo_map_120),
        _make_note(start_tick=288, jitter_ticks=9, tempo_map=tempo_map_120),  # tick 297 -> 288
    ]

    result = quantizer.quantize(notes, tempo_map_120)
    assert [n.tick for n in result] == [0, 96, 192, 288]


def test_quantize_twelfth_triplets(quantizer: NoteQuantizer, tempo_map_120: TempoMap) -> None:
    """Validate snapping for 1/12 triplets (multiples of 64 ticks)."""
    notes = [
        _make_note(start_tick=0, jitter_ticks=0, tempo_map=tempo_map_120),
        _make_note(start_tick=64, jitter_ticks=-5, tempo_map=tempo_map_120),  # tick 59 -> 64
        _make_note(start_tick=128, jitter_ticks=6, tempo_map=tempo_map_120),  # tick 134 -> 128
        _make_note(start_tick=192, jitter_ticks=0, tempo_map=tempo_map_120),
    ]

    result = quantizer.quantize(notes, tempo_map_120)
    assert [n.tick for n in result] == [0, 64, 128, 192]


def test_quantize_sixteenth_notes_delayed_prompt_spec(
    quantizer: NoteQuantizer, tempo_map_120: TempoMap
) -> None:
    """Validate snapping for 1/16 notes, specifically tick 50 -> 48 as requested in Prompt 4.1."""
    # Note at tick 48 + 2 = 50 ticks -> must snap to 48
    note_delayed = _make_note(start_tick=48, jitter_ticks=2, tempo_map=tempo_map_120)
    note_early = _make_note(start_tick=96, jitter_ticks=-6, tempo_map=tempo_map_120)
    note_sixteenth_3 = _make_note(start_tick=144, jitter_ticks=4, tempo_map=tempo_map_120)

    result = quantizer.quantize([note_delayed, note_early, note_sixteenth_3], tempo_map_120)
    assert [n.tick for n in result] == [48, 96, 144]


def test_quantize_twenty_fourth_triplets(quantizer: NoteQuantizer, tempo_map_120: TempoMap) -> None:
    """Validate snapping for 1/24 triplet notes (multiples of 32 ticks, sextuplets)."""
    notes = [
        _make_note(start_tick=32, jitter_ticks=-3, tempo_map=tempo_map_120),  # tick 29 -> 32
        _make_note(start_tick=64, jitter_ticks=0, tempo_map=tempo_map_120),
        _make_note(start_tick=96, jitter_ticks=0, tempo_map=tempo_map_120),
        _make_note(start_tick=160, jitter_ticks=4, tempo_map=tempo_map_120),  # tick 164 -> 160
    ]

    result = quantizer.quantize(notes, tempo_map_120)
    assert [n.tick for n in result] == [32, 64, 96, 160]


def test_quantize_thirty_second_notes(quantizer: NoteQuantizer, tempo_map_120: TempoMap) -> None:
    """Validate snapping for 1/32 notes (multiples of 24 ticks)."""
    notes = [
        _make_note(start_tick=24, jitter_ticks=2, tempo_map=tempo_map_120),  # tick 26 -> 24
        _make_note(start_tick=72, jitter_ticks=-2, tempo_map=tempo_map_120),  # tick 70 -> 72
        _make_note(start_tick=120, jitter_ticks=3, tempo_map=tempo_map_120),  # tick 123 -> 120
        _make_note(start_tick=168, jitter_ticks=-3, tempo_map=tempo_map_120),  # tick 165 -> 168
    ]

    result = quantizer.quantize(notes, tempo_map_120)
    assert [n.tick for n in result] == [24, 72, 120, 168]


def test_quantize_outside_tolerance_remains_unsnapped(tempo_map_120: TempoMap) -> None:
    """Validate that deviations > 16 ticks remain unsnapped at their raw tick position."""
    # When quantizing against quarter notes only (192)
    quarter_quantizer = NoteQuantizer(subdivisions=[192], tolerance_ticks=16)

    # Note at tick 192 + 16 = 208 -> dist is 16 -> snapped to 192
    note_boundary_in = _make_note(start_tick=192, jitter_ticks=16, tempo_map=tempo_map_120)
    # Note at tick 192 + 17 = 209 -> dist is 17 -> unsnapped (remains 209)
    note_boundary_out = _make_note(start_tick=192, jitter_ticks=17, tempo_map=tempo_map_120)
    # Note at tick 20 -> dist to 0 is 20, dist to 192 is 172 -> unsnapped (remains 20)
    note_isolated = _make_note(start_tick=0, jitter_ticks=20, tempo_map=tempo_map_120)

    result = quarter_quantizer.quantize(
        [note_isolated, note_boundary_in, note_boundary_out], tempo_map_120
    )
    assert result[0].tick == 20  # Unsnapped
    assert result[1].tick == 192  # Snapped
    assert result[2].tick == 209  # Unsnapped


def test_quantize_custom_tolerance(tempo_map_120: TempoMap) -> None:
    """Validate custom tolerance parameter (e.g. tolerance_ticks=8)."""
    tight_quantizer = NoteQuantizer(subdivisions=[24], tolerance_ticks=8)

    # Note at tick 24 - 8 = 16 -> dist 8 <= 8 -> snapped to 24
    note_in = _make_note(start_tick=24, jitter_ticks=-8, tempo_map=tempo_map_120)
    # Note at tick 24 - 10 = 14 -> dist 10 > 8 and dist to 0 is 14 > 8 -> unsnapped (14)
    note_out = _make_note(start_tick=24, jitter_ticks=-10, tempo_map=tempo_map_120)

    result = tight_quantizer.quantize([note_out, note_in], tempo_map_120)
    assert result[0].tick == 14  # Unsnapped
    assert result[1].tick == 24  # Snapped


def test_deduplication_identical_tick_and_pitch(
    quantizer: NoteQuantizer, tempo_map_120: TempoMap
) -> None:
    """Ensure duplicate notes at the same tick and pitch merge, keeping max amplitude & duration."""
    note_a = NoteEvent(
        start_time=tempo_map_120.tick_to_seconds(192),
        end_time=tempo_map_120.tick_to_seconds(192 + 96),  # 96 ticks
        pitch=60,
        amplitude=0.55,
    )
    # Note B is slightly jittered (+4 ticks), snapping to 192, with higher amplitude and longer duration
    note_b = NoteEvent(
        start_time=tempo_map_120.tick_to_seconds(196),
        end_time=tempo_map_120.tick_to_seconds(196 + 144),  # 144 ticks
        pitch=60,
        amplitude=0.92,
    )

    result = quantizer.quantize([note_a, note_b], tempo_map_120)
    assert len(result) == 1
    assert result[0].tick == 192
    assert result[0].pitch == 60
    assert result[0].amplitude == 0.92  # max(0.55, 0.92)
    assert result[0].duration_ticks == 144  # max(96, 144)


def test_deduplication_preserves_chords_and_different_ticks(
    quantizer: NoteQuantizer, tempo_map_120: TempoMap
) -> None:
    """Ensure distinct pitches at the same tick (chords) and identical pitches at different ticks are kept."""
    # Polyphonic chord at tick 192: Pitch 60 and Pitch 64
    chord_root = _make_note(start_tick=192, pitch=60, amplitude=0.7, tempo_map=tempo_map_120)
    chord_third = _make_note(start_tick=192, pitch=64, amplitude=0.8, tempo_map=tempo_map_120)

    # Repeated pitch 60 at tick 384
    next_note = _make_note(start_tick=384, pitch=60, amplitude=0.75, tempo_map=tempo_map_120)

    result = quantizer.quantize([chord_root, chord_third, next_note], tempo_map_120)
    assert len(result) == 3
    assert result[0].tick == 192 and result[0].pitch == 60
    assert result[1].tick == 192 and result[1].pitch == 64
    assert result[2].tick == 384 and result[2].pitch == 60


def test_empty_note_list(quantizer: NoteQuantizer, tempo_map_120: TempoMap) -> None:
    """Ensure an empty NoteEvent list returns an empty list without error."""
    assert quantizer.quantize([], tempo_map_120) == []


def test_chronological_sorting_output(quantizer: NoteQuantizer, tempo_map_120: TempoMap) -> None:
    """Ensure notes provided out of chronological order are returned strictly sorted by tick, then pitch."""
    note_late = _make_note(start_tick=384, pitch=60, tempo_map=tempo_map_120)
    note_early = _make_note(start_tick=0, pitch=60, tempo_map=tempo_map_120)
    note_mid_high = _make_note(start_tick=192, pitch=64, tempo_map=tempo_map_120)
    note_mid_low = _make_note(start_tick=192, pitch=60, tempo_map=tempo_map_120)

    result = quantizer.quantize([note_late, note_early, note_mid_high, note_mid_low], tempo_map_120)
    assert len(result) == 4
    assert [(n.tick, n.pitch) for n in result] == [
        (0, 60),
        (192, 60),
        (192, 64),
        (384, 60),
    ]


def test_multi_tempo_map_variable_bpm(
    quantizer: NoteQuantizer, variable_tempo_map: TempoMap
) -> None:
    """Validate quantization across dynamic BPM changes (120 BPM -> 140 BPM at tick 768)."""
    # Note in 120 BPM section (0.5s = tick 192)
    note_120 = NoteEvent(
        start_time=variable_tempo_map.tick_to_seconds(192),
        end_time=variable_tempo_map.tick_to_seconds(288),
        pitch=60,
        amplitude=0.8,
    )
    # Note exactly at the tempo change boundary (tick 768)
    note_transition = NoteEvent(
        start_time=variable_tempo_map.tick_to_seconds(768),
        end_time=variable_tempo_map.tick_to_seconds(864),
        pitch=62,
        amplitude=0.85,
    )
    # Note in 140 BPM section (tick 960) with slight jitter (+3 ticks)
    note_140_jitter = NoteEvent(
        start_time=variable_tempo_map.tick_to_seconds(963),
        end_time=variable_tempo_map.tick_to_seconds(1059),
        pitch=64,
        amplitude=0.9,
    )

    result = quantizer.quantize([note_120, note_transition, note_140_jitter], variable_tempo_map)
    assert len(result) == 3
    assert [n.tick for n in result] == [192, 768, 960]


def test_quantized_note_model_validation() -> None:
    """Validate QuantizedNote parameter bounds and exception handling."""
    valid = QuantizedNote(tick=192, pitch=60, duration_ticks=96, amplitude=0.8)
    assert valid.tick == 192
    assert valid.pitch == 60
    assert valid.duration_ticks == 96
    assert valid.amplitude == 0.8

    with pytest.raises(ValueError):
        QuantizedNote(tick=-1, pitch=60, duration_ticks=96, amplitude=0.8)

    with pytest.raises(ValueError):
        QuantizedNote(tick=0, pitch=128, duration_ticks=96, amplitude=0.8)

    with pytest.raises(ValueError):
        QuantizedNote(tick=0, pitch=60, duration_ticks=-5, amplitude=0.8)

    with pytest.raises(ValueError):
        QuantizedNote(tick=0, pitch=60, duration_ticks=96, amplitude=1.2)


def test_note_quantizer_validation() -> None:
    """Ensure invalid NoteQuantizer configuration raises ValueError."""
    with pytest.raises(ValueError):
        NoteQuantizer(tolerance_ticks=-1)
```

---

## 8. Verification Strategy & Commands

1. **Unit Testing**:
   ```bash
   .venv/bin/pytest tests/test_game_design/test_quantizer.py
   ```
2. **Type Checking**:
   ```bash
   .venv/bin/mypy src/game_design tests/test_game_design
   ```
3. **Linting & Code Formatting**:
   ```bash
   .venv/bin/ruff check src/game_design tests/test_game_design
   .venv/bin/ruff format --check src/game_design tests/test_game_design
   ```
4. **Full Regression Check**:
   ```bash
   .venv/bin/pytest tests/
   ```
   Ensures zero regressions across existing 57 test cases.
