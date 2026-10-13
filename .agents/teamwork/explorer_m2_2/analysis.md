# Analysis: Jump Penalty, Open Note Mapping, and API Contract for `PitchToFretMapper`

**Author**: `explorer_m2_2`  
**Milestone**: Milestone 2 (Phase 4 Game Design Engine)  
**Target Module**: `src/game_design/pitch_to_fret.py`  
**Date**: 2026-10-13  

---

## Executive Summary

This document provides the complete architectural design and specification for the jump penalty constraint, Open Note mapping, and API contract of `PitchToFretMapper` in `src/game_design/pitch_to_fret.py`. 

Key determinations:
1. **Open Note Mapping (`pitch < 40`)**: Sub-bass notes (< MIDI 40, such as Drop D / 7-string bass notes) map directly to `FretType.OPEN` (7). Sub-bass notes must be **excluded** from the sliding window percentile calculations to prevent skewing playable fretted notes toward high frets. Open notes are **completely excluded** from fret leap distance calculations and reset the fretting anchor, preventing erroneous clamps on legitimate open-pedal riffs.
2. **Rapid Passage Jump Penalty (`interval < 48` ticks, `leap > 3` frets)**: When chronological intervals between consecutive fretted notes are strictly positive and `< 48` ticks (16th note threshold at 192 PPQ), fret leaps greater than 3 frets (specifically Green 0 to Orange 4, and Orange 4 to Green 0) are clamped in the direction of the jump:
   - Upward jump (0 -> 4) clamps to `prev_fret + 3 = 3` (Blue).
   - Downward jump (4 -> 0) clamps to `prev_fret - 3 = 1` (Red).
   - Simultaneous notes (interval = 0) are never clamped by the sequential jump penalty (chord constraints are handled in Milestone 3).
3. **API & Output Contract**: `PitchToFretMapper.map_notes(notes: Sequence[QuantizedNote]) -> list[ChartNote]` returns `ChartNote` instances with `sustain_length=0` and `is_hopo=False`, strictly sorted chronologically by `(tick, fret)`.

---

## 1. Open Note Mapping Architecture

### 1.1. Musical & Game Context
- **Standard Guitar vs Sub-Bass**: Standard 6-string guitar tuning (EADGBE) has its lowest note at E2 (MIDI 40, ~82.41 Hz). Rock and metal frequently utilize Drop D (D2 = MIDI 38), Drop C (C2 = MIDI 36), 7-string B1 (MIDI 35), and 8-string F#1 (MIDI 30), as well as bass guitar foundations.
- **Clone Hero Mechanic**: Clone Hero represents unfretted strums as Open Notes (`FretType.OPEN = 7`, rendered in-game as a full-width purple bar). Open notes are played by striking the strum bar without pressing any neck fret buttons.
- **Threshold Rule**: Any quantized note with `pitch < open_threshold` (default `open_threshold = 40`) is mapped to `FretType.OPEN` (7).

### 1.2. Interaction with the Sliding Window
A critical design question is whether sub-bass notes (`pitch < 40`) should be included when calculating the pitch percentiles of the sliding window for normal frets (0 to 4).

**Failure Mode of Including Sub-Bass in the Window**:
Consider a heavy riff where a guitarist alternates between Drop D pedal notes (pitch 38) and octave lead notes (pitches 60, 62, 64).
If pitch 38 is included in the window's pitch distribution:
- Pitch 38 dominates the lower percentiles (0th, 25th, 50th).
- A moderate lead note such as C4 (pitch 60) falls into the 80th+ percentile and is forced onto Orange (4).
- Subsequent higher notes (62, 64) all collide on Orange (4).
- Result: The melodic lead collapses into an unplayable cluster at Orange (4).

**Design Decision (Decoupled Pre-Filter)**:
1. When evaluating any note $N$:
   - If $N.\text{pitch} < \text{open\_threshold}$: $N$ is immediately assigned `FretType.OPEN` (7). It bypasses the percentile projection entirely.
2. When computing the local pitch window $[t - W/2, t + W/2]$ for fretted notes ($N.\text{pitch} \ge \text{open\_threshold}$):
   - Only notes with $\text{pitch} \ge \text{open\_threshold}$ are included in the percentile distribution.
   - If a window contains *only* sub-bass notes, all notes in that window naturally map to `FretType.OPEN` (7).
   - If a window contains fretted notes, the lowest fretted note (e.g. E2 = MIDI 40) anchors at Green (0), ensuring the full 5-fret span is dedicated to actual playable fretted notes.

### 1.3. Interaction with Jump Penalty & Fret Leap Distance
Should Open notes interact with fret leap tracking, and how?

**Physical Mechanism**:
- On a Guitar Hero / Clone Hero controller:
  - Frets 0 to 4 correspond to physical push-buttons on the neck (Green, Red, Yellow, Blue, Orange).
  - Open note (7) requires *releasing* all fret buttons and strumming.
- If Open (7) were treated as a numeric fret value:
  - Moving from Green (0) to Open (7) would produce $|7 - 0| = 7 > 3$. If clamped, Open (7) would be converted to Blue (3), destroying the Open note.
  - Moving from Open (7) to Green (0) would produce $|0 - 7| = 7 > 3$. If clamped, Green would be converted to Orange (4).
- **Rule 1 (Exclusion from Distance)**: `FretType.OPEN` (7) is **strictly excluded** from fret leap distance calculations. The distance $|f_1 - f_2|$ is only defined for frets $f_1, f_2 \in [0, 4]$.
- **Rule 2 (Immunity to Clamping)**: An Open note is **never clamped**. If a note is sub-bass, it always remains `FretType.OPEN` (7).
- **Rule 3 (Fretting Anchor State Reset)**:
  - When an Open note is encountered, it resets the tracked fretting anchor:
    $$\text{last\_fretted\_tick} = \text{None}, \quad \text{last\_fretted\_frets} = []$$
  - **Rationale**: When playing an open note, no fret button is held. The player's left hand is physically disengaged from any button anchor and is completely free to hover over or move to any fret on the neck. In Clone Hero charting (CSC and official charts), "open-pedal" patterns (e.g. Open -> Orange -> Open -> Orange, or Open -> Blue -> Open -> Orange) are standard and do not constitute hand stretches because the left hand is unconstrained during the open strum. Resetting the anchor ensures these legitimate riffs are never erroneously clamped.

---

## 2. Rapid Passage Jump Penalty Clamping

### 2.1. Trigger Conditions
The jump penalty is applied if and only if **all** of the following conditions are met:
1. **Chronological sequence**: $0 < \text{current\_tick} - \text{prev\_tick} < \text{rapid\_interval}$ (default `rapid_interval = 48` ticks, i.e., 1/16th note at 192 PPQ).
   - If $\text{current\_tick} - \text{prev\_tick} == 0$: The notes are simultaneous (chord). Chord ergonomics are governed by `ChordBuilder` in Milestone 3, not the sequential leap penalty.
   - If $\text{current\_tick} - \text{prev\_tick} \ge \text{rapid\_interval}$: The player has at least one 16th note duration of time to shift hand position. No clamp is applied.
2. **Both notes are fretted**: $\text{prev\_fret} \in [0, 4]$ and $\text{current\_fret} \in [0, 4]$.
3. **Leap threshold exceeded**: $|\text{current\_fret} - \text{prev\_fret}| > \text{max\_jump}$ (default `max_jump = 3`).

### 2.2. Mathematical Clamping Formulation
In the standard 5-fret domain $\{0, 1, 2, 3, 4\}$, the only pairs with distance $> 3$ are:
- $(0, 4)$: distance $|4 - 0| = 4 > 3$.
- $(4, 0)$: distance $|0 - 4| = 4 > 3$.
All other pairs (e.g. $(0, 3)$, $(1, 4)$, $(1, 3)$, $(0, 2)$) have distance $\le 3$.

To support arbitrary `max_jump` configurations while maintaining directional fidelity and domain bounds:

$$\Delta = \text{target\_fret} - \text{prev\_fret}$$

$$\text{If } |\Delta| > \text{max\_jump}:$$
$$\text{clamped\_fret} = \begin{cases} 
\text{prev\_fret} + \text{max\_jump}, & \text{if } \Delta > 0 \\ 
\text{prev\_fret} - \text{max\_jump}, & \text{if } \Delta < 0 
\end{cases}$$

$$\text{final\_fret} = \max(0, \min(4, \text{clamped\_fret}))$$

#### Concrete Verification:
- **Upward Leap (Green 0 to Orange 4)**:
  - $\Delta = 4 - 0 = +4 > 3$.
  - $\text{clamped} = 0 + 3 = 3$ (Blue).
  - Preserves upward motion: Note was higher than Green, clamped note is Blue (3), which is as high as ergonomically reachable in a 16th note.
- **Downward Leap (Orange 4 to Green 0)**:
  - $\Delta = 0 - 4 = -4 < -3$.
  - $\text{clamped} = 4 - 3 = 1$ (Red).
  - Preserves downward motion: Note was lower than Orange, clamped note is Red (1), which is as low as ergonomically reachable in a 16th note.

### 2.3. Multi-Note Rapid Runs (Sequential Propagation)
Consider a rapid 32nd-note sequence (interval 24 ticks):
- Tick 0: Green (0)
- Tick 24: Orange (4) -> Target is 4, clamped to Blue (3). Tracked fret becomes 3.
- Tick 48: Orange (4) -> Target is 4. Interval from tick 24 to 48 is 24 ticks (< 48). Previous fret is 3 (Blue). Fret distance is $|4 - 3| = 1 \le 3$. No clamp! Note remains Orange (4).
- Resulting sequence: `Green (0) -> Blue (3) -> Orange (4)`.
- **Game Design Impact**: Rather than completely flattening extreme pitch changes, this smoothly ramps the notes across the fretboard, creating an intuitive, playable sweep.

### 2.4. Handling Polyphony & Simultaneous Notes (Chords)
When transcription produces polyphonic notes at the same tick:
- Group notes by `tick`.
- Let $F_{\text{prev}}$ be the set of fretted values from the most recent fretted tick $T_{\text{prev}}$.
- For each note at the current tick $T_{\text{curr}}$ with initial fret $f \in [0, 4]$:
  - If $0 < T_{\text{curr}} - T_{\text{prev}} < \text{rapid\_interval}$ and $F_{\text{prev}} \ne \emptyset$:
    - Find the closest fret in $F_{\text{prev}}$: $f_{\text{anchor}} = \arg\min_{p \in F_{\text{prev}}} |f - p|$.
    - If $|f - f_{\text{anchor}}| > \text{max\_jump}$:
      - Apply directional clamping relative to $f_{\text{anchor}}$.
  - If multiple notes at $T_{\text{curr}}$ end up on the same fret due to clamping, deduplicate them so each fret appears at most once per tick.

---

## 3. API Contract and Specifications

### 3.1. Class Location & Imports
- Target file: `src/game_design/pitch_to_fret.py`
- Package export: `src/game_design/__init__.py` must export `PitchToFretMapper`.

### 3.2. Constructor Specification
```python
class PitchToFretMapper:
    """Projects quantized MIDI notes to 5 Clone Hero frets and Open strum."""

    DEFAULT_WINDOW_TICKS: int = 1536  # ~2 measures in 4/4 at 192 PPQ
    DEFAULT_MAX_JUMP: int = 3  # Maximum allowed fret leap in rapid passages
    DEFAULT_RAPID_INTERVAL: int = 48  # Threshold for rapid passage (1/16 note = 48 ticks)
    DEFAULT_OPEN_THRESHOLD: int = 40  # Pitches < 40 map to FretType.OPEN (7)

    def __init__(
        self,
        window_ticks: int = DEFAULT_WINDOW_TICKS,
        max_jump: int = DEFAULT_MAX_JUMP,
        rapid_interval: int = DEFAULT_RAPID_INTERVAL,
        open_threshold: int = DEFAULT_OPEN_THRESHOLD,
    ) -> None:
```

**Constructor Validation**:
- `if window_ticks <= 0: raise ValueError(...)`
- `if max_jump < 0: raise ValueError(...)`
- `if rapid_interval < 0: raise ValueError(...)`
- `if not (0 <= open_threshold <= 127): raise ValueError(...)`

### 3.3. Method Signatures & Contract
```python
def map_notes(self, notes: Sequence[QuantizedNote]) -> list[ChartNote]:
    """Map a sequence of QuantizedNotes to ChartNotes.

    Args:
        notes: Sequence of QuantizedNotes (from NoteQuantizer).

    Returns:
        List of ChartNotes with sustain_length=0 and is_hopo=False,
        sorted chronologically by (tick, fret).
    """
```
Provide the alias:
```python
map = map_notes
```

### 3.4. Output Data Structure
Every element in the returned list is a `src.models.chart.ChartNote`:
- `tick`: Exact grid tick from `QuantizedNote.tick`.
- `fret`: One of `FretType.GREEN (0)`, `FretType.RED (1)`, `FretType.YELLOW (2)`, `FretType.BLUE (3)`, `FretType.ORANGE (4)`, or `FretType.OPEN (7)`.
- `sustain_length`: Strictly `0` (sustain computation is deferred to Milestone 4 `SustainProcessor`).
- `is_hopo`: Strictly `False` (HOPO detection is deferred to Milestone 4 `HopoEngine`).
- Ordering: Strictly sorted in ascending order by `(tick, fret)`.

---

## 4. Comprehensive Algorithmic Pseudo-Code for Worker

```python
"""Reference implementation outline for PitchToFretMapper."""

from collections import defaultdict
from collections.abc import Sequence
import bisect
import numpy as np

from src.game_design.quantizer import QuantizedNote
from src.models.chart import ChartNote, FretType


class PitchToFretMapper:
    DEFAULT_WINDOW_TICKS: int = 1536
    DEFAULT_MAX_JUMP: int = 3
    DEFAULT_RAPID_INTERVAL: int = 48
    DEFAULT_OPEN_THRESHOLD: int = 40

    def __init__(
        self,
        window_ticks: int = DEFAULT_WINDOW_TICKS,
        max_jump: int = DEFAULT_MAX_JUMP,
        rapid_interval: int = DEFAULT_RAPID_INTERVAL,
        open_threshold: int = DEFAULT_OPEN_THRESHOLD,
    ) -> None:
        if window_ticks <= 0:
            raise ValueError(f"window_ticks must be positive, got {window_ticks}")
        if max_jump < 0:
            raise ValueError(f"max_jump must be non-negative, got {max_jump}")
        if rapid_interval < 0:
            raise ValueError(f"rapid_interval must be non-negative, got {rapid_interval}")
        if not (0 <= open_threshold <= 127):
            raise ValueError(f"open_threshold must be between 0 and 127, got {open_threshold}")

        self.window_ticks = window_ticks
        self.max_jump = max_jump
        self.rapid_interval = rapid_interval
        self.open_threshold = open_threshold

    def _map_pitch_in_window(self, pitch: int, window_pitches: list[int]) -> FretType:
        """Map pitch to FretType using local window percentiles or fallback."""
        if not window_pitches:
            return FretType.GREEN

        unique_pitches = sorted(set(window_pitches))
        if len(unique_pitches) == 1:
            return FretType.GREEN

        # Quantile thresholds (0%, 20%, 40%, 60%, 80%) or (min, 25%, 50%, 75%, max)
        # Using 5 bins across window pitch distribution:
        # If pitch matches unique scale:
        idx = bisect.bisect_right(unique_pitches, pitch) - 1
        rank_ratio = idx / max(1, len(unique_pitches) - 1)
        fret_val = min(4, int(rank_ratio * 5))
        return FretType(fret_val)

    def map_notes(self, notes: Sequence[QuantizedNote]) -> list[ChartNote]:
        if not notes:
            return []

        sorted_notes = sorted(notes, key=lambda n: (n.tick, n.pitch))
        half_window = self.window_ticks // 2

        # Step 1: Initial fret assignment per note
        raw_assignments: list[tuple[int, FretType]] = []
        
        # Pre-extract all fretted notes for fast window lookup
        fretted_pool = [(n.tick, n.pitch) for n in sorted_notes if n.pitch >= self.open_threshold]
        pool_ticks = [t for t, _ in fretted_pool]
        pool_pitches = [p for _, p in fretted_pool]

        for qn in sorted_notes:
            if qn.pitch < self.open_threshold:
                raw_assignments.append((qn.tick, FretType.OPEN))
                continue

            # Query fretted notes within [qn.tick - half_window, qn.tick + half_window]
            left_idx = bisect.bisect_left(pool_ticks, qn.tick - half_window)
            right_idx = bisect.bisect_right(pool_ticks, qn.tick + half_window)
            local_pitches = pool_pitches[left_idx:right_idx]

            fret = self._map_pitch_in_window(qn.pitch, local_pitches)
            raw_assignments.append((qn.tick, fret))

        # Step 2: Jump penalty enforcement across chronological ticks
        tick_groups: dict[int, list[FretType]] = defaultdict(list)
        for tick, fret in raw_assignments:
            tick_groups[tick].append(fret)

        final_chart_notes: list[ChartNote] = []
        last_fretted_tick: int | None = None
        last_fretted_frets: list[int] = []

        for tick in sorted(tick_groups.keys()):
            frets_at_tick = tick_groups[tick]
            has_fretted = False
            current_fretted_frets: list[int] = []

            for fret in frets_at_tick:
                if fret == FretType.OPEN:
                    final_chart_notes.append(
                        ChartNote(tick=tick, fret=FretType.OPEN, sustain_length=0, is_hopo=False)
                    )
                else:
                    target_val = fret.value
                    if (
                        last_fretted_tick is not None
                        and (0 < tick - last_fretted_tick < self.rapid_interval)
                        and last_fretted_frets
                    ):
                        # Find closest fret anchor from previous fretted tick
                        closest_prev = min(last_fretted_frets, key=lambda f: abs(target_val - f))
                        diff = target_val - closest_prev
                        if abs(diff) > self.max_jump:
                            if diff > 0:
                                clamped = closest_prev + self.max_jump
                            else:
                                clamped = closest_prev - self.max_jump
                            target_val = max(0, min(4, clamped))

                    has_fretted = True
                    current_fretted_frets.append(target_val)
                    final_chart_notes.append(
                        ChartNote(tick=tick, fret=FretType(target_val), sustain_length=0, is_hopo=False)
                    )

            if has_fretted:
                last_fretted_tick = tick
                last_fretted_frets = current_fretted_frets
            else:
                # Only Open notes at this tick -> reset fretting anchor
                last_fretted_tick = None
                last_fretted_frets = []

        # Step 3: Deduplication of identical (tick, fret) and sort
        deduped: dict[tuple[int, int], ChartNote] = {}
        for cn in final_chart_notes:
            key = (cn.tick, cn.fret.value)
            if key not in deduped:
                deduped[key] = cn

        result = sorted(deduped.values())
        return result

    map = map_notes
```

---

## 5. Architectural Checklist for Worker

- [x] Input type: `Sequence[QuantizedNote]`, zero mutations to input.
- [x] Output type: `list[ChartNote]` with `sustain_length=0`, `is_hopo=False`.
- [x] Sub-bass `< open_threshold` (default 40) mapped to `FretType.OPEN` (7).
- [x] Sub-bass notes excluded from fretted sliding window percentiles.
- [x] Open notes excluded from fret leap distance; never clamped.
- [x] Open notes reset fretting anchor state.
- [x] Rapid jump penalty triggers only on $0 < \Delta\text{tick} < 48$ with $|f_{\text{curr}} - f_{\text{prev}}| > 3$.
- [x] Directional clamping: $0 \to 4$ clamps to $3$ (Blue); $4 \to 0$ clamps to $1$ (Red).
- [x] Simultaneous notes at same tick ($\Delta\text{tick} = 0$) never clamp each other.
- [x] Export `PitchToFretMapper` in `src/game_design/__init__.py`.
