# Handoff Report: Adaptive Pitch-to-Fret Percentile Projection Design

**Agent**: `explorer_m2_1`  
**Milestone**: Phase 4 — Milestone 2 (Adaptive Pitch-to-Fret Projection)  
**Type**: Hard Handoff (Investigation & Architecture Design Complete)  
**Date**: 2026-10-13  
**Target Recipient**: Milestone 2 Worker (`worker_m2_1`) and Orchestrator  

---

## 1. Observation

1. **Sliding Window & Game Design Specifications**:
   - In `AGENTS.md` (lines 328-339):
     > "7.2. Pitch Projection to 5 Frets (Expert Difficulty)
     > - The Clone Hero guitar features 5 buttons ordered by tonal pitch:
     >   - Green (0): Lowest notes of the passage (e.g., low E string, rhythm base notes).
     >   - Red (1): Mid-low.
     >   - Yellow (2): Mid.
     >   - Blue (3): Mid-high.
     >   - Orange (4): Extreme highs and high-register solo notes.
     >   - Open (7): Reserved for heavy sub-bass palm-muted riffs or open bass notes.
     > - Relative Window: Mapping must not be static (e.g., C4 is not permanently Yellow). It must use an adaptive sliding tessitura window of 1 to 2 measures, projecting the active pitch percentiles to frets [0, 4]. This ensures high-register guitar solos dynamically utilize all 5 frets naturally."
   - In `PROMPTS.md` (lines 201-214):
     > "1. Create src/game_design/pitch_to_fret.py containing the `PitchToFretMapper` class:
     >    - Implement an adaptive dynamic sliding window pitch projection algorithm calculated across 2 to 4 measure sections.
     >    - For each window, compute active note pitch percentiles (minimum, 25%, 50%, 75%, maximum).
     >    - Map continuous pitch to the 5 fret buttons:
     >      * Lowest percentile / bass fundamental -> Green (0)
     >      * Mid-low -> Red (1)
     >      * Mid -> Yellow (2)
     >      * Mid-high -> Blue (3)
     >      * Upper percentile / extreme highs -> Orange (4)
     >    - Add Open Note (7) rule: very low pitch notes (< MIDI 40) occurring isolated in fast rhythmic passages must be mapped as Fret 7.
     >    - Add transition smoothness constraint: penalize impossible jumps of >3 frets in intervals < 48 ticks (prevent consecutive jumps from Green to Orange in sixteenth notes).
     > 2. Write tests in tests/test_game_design/test_pitch_to_fret.py covering:
     >    - Ascending guitar scale (must produce fluid 0 -> 1 -> 2 -> 3 -> 4 progression).
     >    - High-register guitar solo (notes must populate frets relatively rather than clustering exclusively on Orange)."
   - In `SCOPE.md` (lines 72-78):
     > "### `PitchToFretMapper` (`src/game_design/pitch_to_fret.py`)
     > - Input: `notes: list[QuantizedNote]`
     > - Output: `list[ChartNote]` where `ChartNote(tick: int, fret: FretType, sustain_length: int, is_hopo: bool)`
     > - Parameters: `window_ticks: int = 1536`, `max_jump: int = 3`, `rapid_interval: int = 48`, `open_threshold: int = 40`
     > - Open Note: `pitch < 40` -> `FretType.OPEN` (7)
     > - Jump penalty: if `tick - prev_tick < 48` and `abs(fret - prev_fret) > 3`, clamp leap to `<= 3` frets."

2. **Domain Model Contracts**:
   - `src/game_design/quantizer.py` (lines 20-38):
     > `@dataclass(frozen=True, slots=True, order=True)`
     > `class QuantizedNote:`
     > `    tick: int`
     > `    pitch: int`
     > `    duration_ticks: int`
     > `    amplitude: float`
   - `src/models/chart.py` (lines 7-18 and lines 20-43):
     > `class FretType(IntEnum):`
     > `    GREEN = 0`
     > `    RED = 1`
     > `    YELLOW = 2`
     > `    BLUE = 3`
     > `    ORANGE = 4`
     > `    HOPO_FORCE = 5`
     > `    STRUM_FORCE = 6`
     > `    OPEN = 7`
     > `class ChartNote:`
     > `    tick: int`
     > `    fret: FretType`
     > `    sustain_length: int = 0`
     > `    is_hopo: bool = False`

3. **Empirical Benchmarks & Simulation Results**:
   - Execution of Python simulation across 14 canonical musical suites (recorded in `analysis.md` §3.2):
     - Ascending scale `[60, 62, 64, 67, 69]` maps to `[0, 1, 2, 3, 4]`.
     - High solo `[76, 79, 81, 83, 88]` maps to `[0, 1, 2, 3, 4]`.
     - Monotone pedal `[60, 60, 60, 60]` maps to `[0, 0, 0, 0]`.
     - Narrow trill `[60, 62]` maps to `[0, 1]` (adjacent Green-Red).
     - Wide multi-octave sweep `[40, 52, 64, 76, 88]` maps to `[0, 1, 2, 3, 4]`.
   - Bisect window selection over 3,000 notes executed in **1.71 ms** with $O(N \log N)$ total complexity.
   - Current test suite passes 18/18 tests in `tests/test_game_design/test_quantizer.py` and 57/57 tests in regression suite `tests/`.

---

## 2. Logic Chain

1. **Window Centering & Offline Context** (supported by Observation 1):
   - At 192 PPQ in 4/4 meter, 1 measure is 768 ticks; 2 measures is 1536 ticks (`window_ticks`).
   - In offline batch processing, future musical context is available without latency penalty.
   - Using a symmetric centered window $[t - 768, t + 768]$ guarantees that ascending register changes are anticipated smoothly, preventing the phase lag observed in causal windows where the first high-register notes spiked to Orange (4).
   - Window extraction via `bisect_left` and `bisect_right` on the sorted `tick` array runs in $O(\log N)$ time, completing in $< 2\text{ ms}$ for standard tracks.

2. **Open Note Exclusion from Tessitura** (supported by Observation 1):
   - Sub-bass notes ($\text{pitch} < 40$) are mapped directly to `FretType.OPEN = 7`.
   - If sub-bass notes are included in the fretted pool $\mathcal{P}_w$, $p_{\min}$ drops artificially (e.g. to 36), which causes the lowest playable fretted note (e.g. 55) to be mapped to Yellow (2) or Blue (3) rather than Green (0).
   - Therefore, filtering $\mathcal{P}_w = \{ p \in W_i \mid p \ge \text{open\_threshold} \}$ isolates the fretted tessitura and anchors the lowest playable guitar riff to Green (0).

3. **Controller Geometry & 5-Point Quartile Anchoring** (supported by Observations 1 & 3):
   - The 5 buttons of Clone Hero are symmetric: Green (0), Red (1), Yellow (2), Blue (3), Orange (4).
   - Setting reference points to $[T_0, T_1, T_2, T_3, T_4] = [\min, Q_{25}, Q_{50}, Q_{75}, \max]$ anchors:
     - Minimum pitch $\to$ Green (0)
     - Median pitch ($Q_{50}$) $\to$ Yellow (2), the physical center button
     - Maximum pitch $\to$ Orange (4)
     - Intermediate quartiles $\to$ Red (1) and Blue (3)
   - Continuous linear interpolation matches standard percentile definitions while remaining 100% pure-Python.

4. **Resolution of Degenerate Cases via Hybrid Adaptation** (supported by Observations 1 & 3):
   - **Monotone / Single Note** ($S = p_{\max} - p_{\min} == 0$): Maps to `FretType.GREEN = 0` as the index-finger pedal anchor.
   - **Narrow Pitch Range** ($S < 5$ semitones):
     - In 12-TET, an integer span $< 5$ can contain at most $K \le 5$ unique pitches.
     - Pure percentiles naively map a 2-semitone trill `[60, 62]` to $[0, 4]$ (a 4-fret stretch across the controller).
     - In contrast, mapping unique pitch ranks directly to frets assigns `[60, 62]` to $[0, 1]$ (Green-Red index-middle alternating) and `[60, 61, 62, 63]` to $[0, 1, 2, 3]$. This guarantees strictly monotonic, adjacent finger ergonomics for all narrow passages.
   - **Wide Pitch Range** ($S \ge 5$ and $> 24$ semitones):
     - The scale-invariant quartile reference partition distributes large arpeggios and multi-octave solos evenly across the 5 frets without overflow.

---

## 3. Caveats

1. **Downstream Rapid Jump Enforcement**:
   - `PitchToFretMapper` includes the rapid jump clamping rule (`tick - prev_tick < 48` and $|fret - prev\_fret| > 3 \implies \text{clamp to } \le 3$). Peer agent `explorer_m2_2` is specifying the precise interaction between Open notes and rapid jumps (Open notes do not count towards fretted leaps).
2. **Downstream Chord Harmonization**:
   - Simultaneous notes (chords) are projected independently by `PitchToFretMapper` at the same tick. Downstream `ChordBuilder` (Milestone 3) is responsible for pruning clusters $> 3$ notes and enforcing power chord canonical shapes.
3. **Empty Input**:
   - If `notes` is empty, `map_notes([])` must return `[]` without error.

---

## 4. Conclusion

1. **Architecture & Class Contract**:
   - Class: `PitchToFretMapper` in `src/game_design/pitch_to_fret.py`.
   - Constructor:
     ```python
     PitchToFretMapper(
         window_ticks: int = 1536,
         max_jump: int = 3,
         rapid_interval: int = 48,
         open_threshold: int = 40,
     )
     ```
   - Main method: `map_notes(self, notes: Sequence[QuantizedNote]) -> list[ChartNote]`.
2. **Algorithmic Rule**:
   - If `note.pitch < open_threshold`: emit `ChartNote(tick=note.tick, fret=FretType.OPEN, sustain_length=0, is_hopo=False)`.
   - Select window $[note.tick - 768, note.tick + 768]$ via `bisect`.
   - Extract $\mathcal{P}_w = [p \text{ for } p \in W \text{ if } p \ge \text{open\_threshold}]$.
   - If $p_{\max} - p_{\min} == 0$: fret = 0.
   - Else if $p_{\max} - p_{\min} < 5$: fret = `sorted(unique(P_w)).index(note.pitch)`.
   - Else: 5-point quartile reference nearest-neighbor with median tie-breaking.
   - Apply rapid jump clamping if $\Delta t < 48$ ticks and $|\Delta f| > 3$.
   - Emit `ChartNote(tick=note.tick, fret=FretType(fret), sustain_length=0, is_hopo=False)`.
3. The complete reference pseudo-code is documented in Section 5 of `analysis.md` and is immediately ready for implementation by the Worker.

---

## 5. Verification Method

1. **Independent Verification Commands**:
   ```bash
   # Run full existing test suite
   .venv/bin/pytest tests/

   # Run M2 unit tests once implemented by Worker
   .venv/bin/pytest tests/test_game_design/test_pitch_to_fret.py -v

   # Run static type checking
   .venv/bin/mypy src/game_design tests/test_game_design

   # Run linter and formatting checks
   .venv/bin/ruff check src/game_design tests/test_game_design
   .venv/bin/ruff format --check src/game_design tests/test_game_design
   ```

2. **Artifact Locations**:
   - Analysis & Pseudo-code: `/home/adiel/Projects/music2chart/.agents/teamwork/explorer_m2_1/analysis.md`
   - Handoff Report: `/home/adiel/Projects/music2chart/.agents/teamwork/explorer_m2_1/handoff.md`

3. **Invalidation Conditions**:
   - The design is invalidated if an ascending 5-note scale does not map to `[0, 1, 2, 3, 4]`.
   - The design is invalidated if a high solo (`[76, 79, 81, 83, 88]`) is pegged to Orange (4) instead of spanning all 5 frets.
   - The design is invalidated if a 2-semitone trill produces a 4-fret leap (`[0, 4]`).
   - The design is invalidated if sub-bass notes (< 40) displace fretted notes away from Green (0).
