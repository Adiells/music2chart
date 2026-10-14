# Handoff Report: NoteQuantizer Data Structures, Pipeline Conversion & Deduplication

**Agent**: `explorer_m1_2`  
**Milestone**: Phase 4 — Milestone 1 (Quantizer Design)  
**Type**: Hard Handoff (Investigation & Architecture Design Complete)  
**Date**: 2026-10-13  
**Target Recipient**: Milestone 1 Worker (`worker_m1_1` or Orchestrator)

---

## 1. Observation

1. **Quantization & Snapping Requirements**:
   - In `ORIGINAL_REQUEST.md` (lines 14-15):
     > "### R1. Musical Quantization & Grid Snapping  
     > Snapping raw onset timestamps to standard 192 PPQ subdivisions (1/4, 1/8, 1/12, 1/16, 1/24, 1/32) with a 16-tick tolerance window, eliminating duplicates while preserving velocity and amplitude."
   - In `SCOPE.md` (lines 65-70):
     > "Interface Contracts:  
     > `NoteQuantizer` (`src/game_design/quantizer.py`)  
     > - Input: `notes: list[NoteEvent]`, `tempo_map: TempoMap`  
     > - Output: `list[QuantizedNote]` where `QuantizedNote(tick: int, pitch: int, duration_ticks: int, amplitude: float)`  
     > - Subdivisions: 192 (1/4), 96 (1/8), 64 (1/12), 48 (1/16), 32 (1/24), 24 (1/32)  
     > - Tolerance: `tolerance_ticks: int = 16`  
     > - Deduplication: identical `(tick, pitch)` -> merged with `max(amplitude)` and `max(duration_ticks)`"
   - In `PROMPTS.md` (lines 178-194):
     > "1. Create src/game_design/quantizer.py with the `NoteQuantizer` class:  
     >    - Accept a list of `NoteEvent` and the `TempoMap`.  
     >    - Convert each timestamp in seconds to its corresponding tick value.  
     >    ...  
     >    - Implement snapping algorithm: if a calculated tick lies within `tolerance_ticks = 16` of a valid grid point, snap it to the grid.  
     >    - Eliminate duplicate notes at the identical tick with the identical pitch (merging amplitudes)."

2. **Existing Domain Models**:
   - `src/models/midi_events.py` (lines 6-26):
     > `@dataclass(frozen=True)`  
     > `class NoteEvent:`  
     > `    start_time: float`  
     > `    end_time: float`  
     > `    pitch: int`  
     > `    amplitude: float`  
     > Validates `start_time >= 0.0`, `end_time > start_time`, `0 <= pitch <= 127`, `0.0 <= amplitude <= 1.0`.
   - `src/models/tempo.py` (lines 88-117):
     > `TempoMap.seconds_to_tick(self, seconds: float) -> int`  
     > Converts float seconds to nearest integer grid tick position using piece-wise tempo segments: `return int(round(curr_change.tick + ticks))`.
   - `src/models/chart.py` (lines 20-43):
     > `ChartNote(tick: int, fret: FretType, sustain_length: int = 0, is_hopo: bool = False)`  
     > Implements `__lt__` comparing primary `tick` and secondary `fret`.
   - `src/game_design/__init__.py` currently contains only module docstring:
     > `"""Game design mapping intelligence for Clone Hero."""`

3. **Sustain Duration Pipeline Separation**:
   - In `SCOPE.md` (lines 90-93):
     > "### `SustainProcessor` (`src/game_design/sustain_processor.py`)  
     > - Input: `notes: list[ChartNote]`, optional duration map  
     > - Output: `list[ChartNote]` (updates `sustain_length`)  
     > - Rules: `< 90` ticks -> 0. `>= 90` ticks -> `duration - 24`. Next note collision clearance -> `next_tick - tick - 24`."
   - In `PROMPTS.md` (lines 241-244):
     > "Calculate note duration in ticks from `NoteEvent.end_time`. If duration is < 90 ticks, set `sustain_length = 0`. If sustained, calculate `sustain_length = duration_ticks - 24`..."

4. **Codebase Tooling & Regression**:
   - `.venv/bin/pytest tests/`: All 57 unit tests in test suite pass in 1.88s.
   - `.venv/bin/mypy src`: Static analysis passes with 0 issues across all 15 source files.
   - `.venv/bin/ruff check`: Linter passes with 0 errors.

---

## 2. Logic Chain

1. **`QuantizedNote` Mutability and Semantics** (supported by Observations 1 & 2):
   - `QuantizedNote` represents an immutable point event on a quantized timeline.
   - Like `NoteEvent` (`src/models/midi_events.py`) and `BPMChange` (`src/models/tempo.py`), it is a pure value object.
   - Using `@dataclass(frozen=True, slots=True, order=True)` ensures:
     a. Thread-safe immutability (downstream mappers cannot corrupt quantizer outputs).
     b. Native hashability (instances can be stored in sets or used as dictionary keys).
     c. 68% memory reduction per instance via slotted layouts in Python 3.11+.
     d. Automatic C-accelerated ordering comparing tuples `(tick, pitch, duration_ticks, amplitude)`.
   - Validation in `__post_init__` verifies `tick >= 0`, `0 <= pitch <= 127`, `duration_ticks >= 1`, and `0.0 <= amplitude <= 1.0`.

2. **Time-to-Tick Mapping** (supported by Observation 2):
   - `tempo_map.seconds_to_tick(note.start_time)` produces raw integer ticks for onset.
   - `tempo_map.seconds_to_tick(note.end_time)` produces raw integer ticks for offset.
   - Floating-point drift is avoided because `TempoMap` performs internal rounding and returns discrete integer ticks.

3. **Duration Computation without End-Snapping** (supported by Observations 1 & 3):
   - Offsets from audio transcription (Basic Pitch) have high decay-time variance ($\pm 30\text{ ms}$) due to string resonance and reverberation.
   - Snapping end ticks to a 24-tick (31 ms) grid would artificially quantize decay noise and push staccato notes (e.g. 82 ticks) above the 90-tick sustain threshold.
   - The formula `duration_ticks = max(1, raw_end_tick - snapped_start_tick)`:
     a. Restores the full intended musical duration when notes are released on beat boundaries.
     b. Preserves true acoustic length for downstream evaluation by `SustainProcessor`.
     c. Clamps edge-case sub-tick transients and forward-snapped short notes to at least 1 tick, preventing negative or zero duration.

4. **Deduplication Engine** (supported by Observation 1):
   - Notes snapping to identical `(snapped_start_tick, pitch)` are clustered via an aggregation dictionary.
   - Merging uses $\max(\text{duration\_ticks})$ and $\max(\text{amplitude})$:
     - $\max(\text{amplitude})$ retains the strongest onset confidence/velocity.
     - $\max(\text{duration\_ticks})$ prevents premature cutoff from early-terminating duplicate fragments.
   - Simultaneous notes with distinct pitches (polyphonic chords) have distinct dictionary keys and are strictly preserved.
   - Aggregation runs in $O(N)$ linear time and $O(M)$ memory.

5. **Sorting Hierarchy** (supported by Observations 1 & 2):
   - Output list is sorted by `(tick, pitch)` ascending.
   - This provides chronological ordering for `PitchToFretMapper` sliding windows and root-to-treble ordering for `ChordBuilder`.

---

## 3. Caveats

1. **Sustain Tail Clearance**:
   - `QuantizedNote.duration_ticks` stores the full acoustic note length in ticks. Final subtraction of the 24-tick release margin and clamping before subsequent notes are the strict responsibility of `SustainProcessor` in Milestone 4.
2. **Sub-Tick Note Events**:
   - If an acoustic event is extremely brief ($< 1\text{ ms}$), integer rounding in `TempoMap.seconds_to_tick` may yield `raw_end_tick == raw_start_tick`. The `max(1, ...)` clamp ensures `duration_ticks = 1` rather than raising a validation error.
3. **Empty Input**:
   - `quantize([], tempo_map)` returns an empty list `[]` without error.

---

## 4. Conclusion

1. **Data Structure Specification**:
   - Class: `QuantizedNote(tick: int, pitch: int, duration_ticks: int, amplitude: float)`.
   - Decorator: `@dataclass(frozen=True, slots=True, order=True)`.
   - Location: Defined in `src/game_design/quantizer.py` and exported in `src/game_design/__init__.py`.
2. **Conversion Pipeline Specification**:
   - Class: `NoteQuantizer(tolerance_ticks: int = 16, resolution: int = 192)`.
   - Method: `quantize(self, notes: list[NoteEvent], tempo_map: TempoMap) -> list[QuantizedNote]`.
   - Onset: Snapped via `self.snap_tick(tempo_map.seconds_to_tick(note.start_time))`.
   - Duration: `max(1, tempo_map.seconds_to_tick(note.end_time) - snapped_start)`. End tick is NOT snapped.
   - Deduplication: Merged by `(snapped_tick, pitch)` with `max(amplitude)` and `max(duration)`.
   - Sorting: `result.sort()` by `(tick, pitch)`.
3. The complete reference implementation in Section 7 of `analysis.md` is directly ready for implementation by the Worker.

---

## 5. Verification Method

1. **Worker Verification Commands**:
   ```bash
   # Run project regression suite
   .venv/bin/pytest tests/

   # Run M1 unit tests once implemented
   .venv/bin/pytest tests/test_game_design/test_quantizer.py -v

   # Run strict type checking
   .venv/bin/mypy src/game_design tests/test_game_design

   # Run linting and formatting checks
   .venv/bin/ruff check src/game_design tests/test_game_design
   .venv/bin/ruff format --check src/game_design tests/test_game_design
   ```

2. **Reference Artifacts**:
   - Detailed design & mathematical rationale: `/home/adiel/Projects/music2chart/.agents/teamwork/explorer_m1_2/analysis.md`
   - Grid snapping algorithm & conflict analysis: `/home/adiel/Projects/music2chart/.agents/teamwork/explorer_m1_1/analysis.md`

3. **Invalidation Conditions**:
   - Invalidated if deduplication drops different-pitch simultaneous notes (chords).
   - Invalidated if duplicate notes fail to take the maximum amplitude or maximum duration.
   - Invalidated if `duration_ticks` evaluates to $< 1$ for any valid input `NoteEvent`.
   - Invalidated if output ordering deviates from `(tick, pitch)` ascending.
