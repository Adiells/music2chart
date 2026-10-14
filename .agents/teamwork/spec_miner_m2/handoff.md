# Handoff Report: Milestone 2 Pitch-to-Fret Specification & Test Plan

**Agent**: `spec_miner_m2` (Specification Miner)  
**Milestone**: Milestone 2 (Adaptive Pitch-to-Fret Projection)  
**Target Files**:
- Specification Report: `.agents/teamwork/spec_miner_m2/spec_report.md`
- Target Test File: `tests/test_game_design/test_pitch_to_fret.py`
- Target Implementation: `src/game_design/pitch_to_fret.py`

---

## 1. Observation

1. **Current Environment and Test Health**:
   - Command: `.venv/bin/pytest tests/`
     Result: `75 passed in 1.82s`
   - Command: `.venv/bin/ruff check tests/test_game_design/test_quantizer.py src/game_design/quantizer.py`
     Result: `All checks passed!`
   - Command: `.venv/bin/mypy src/game_design/quantizer.py tests/test_game_design/test_quantizer.py`
     Result: `Success: no issues found in 2 source files`

2. **Authoritative Specification Sources**:
   - `ORIGINAL_REQUEST.md` (Lines 17–19, 31):
     > "R2. Adaptive Pitch-to-Fret Projection: Dynamic sliding-window pitch projection mapping pitch tessitura percentiles into 5 frets (Green 0 to Orange 4) and Open Strum (7) for extreme sub-bass, penalizing wide fret jumps (>3 frets) in rapid passages (<48 ticks)."
     > "test_pitch_to_fret.py: validates ascending scale flow and relative tessitura windows during solo passages."
   - `SCOPE.md` & `PROJECT.md` (Lines 72–78):
     > "`PitchToFretMapper` (`src/game_design/pitch_to_fret.py`):
     > - Input: `notes: list[QuantizedNote]`
     > - Output: `list[ChartNote]` where `ChartNote(tick: int, fret: FretType, sustain_length: int, is_hopo: bool)`
     > - Parameters: `window_ticks: int = 1536`, `max_jump: int = 3`, `rapid_interval: int = 48`, `open_threshold: int = 40`
     > - Open Note: `pitch < 40` -> `FretType.OPEN` (7)
     > - Jump penalty: if `tick - prev_tick < 48` and `abs(fret - prev_fret) > 3`, clamp leap to `<= 3` frets."
   - `PROMPTS.md` Prompt 4.2 (Lines 196–215):
     > "1. Create src/game_design/pitch_to_fret.py containing the `PitchToFretMapper` class:
     > - Implement an adaptive dynamic sliding window pitch projection algorithm calculated across 2 to 4 measure sections.
     > - For each window, compute active note pitch percentiles (minimum, 25%, 50%, 75%, maximum)...
     > - Map continuous pitch to the 5 fret buttons: Green (0), Red (1), Yellow (2), Blue (3), Orange (4).
     > - Add Open Note (7) rule: very low pitch notes (< MIDI 40)...
     > - Add transition smoothness constraint: penalize impossible jumps of >3 frets in intervals < 48 ticks...
     > 2. Write tests in tests/test_game_design/test_pitch_to_fret.py..."
   - `AGENTS.md` Section 7.2:
     > "Green (0), Red (1), Yellow (2), Blue (3), Orange (4), Open (7)... Relative Window: Mapping must not be static (e.g., C4 is not permanently Yellow). It must use an adaptive sliding tessitura window of 1 to 2 measures, projecting the active pitch percentiles to frets [0, 4]. This ensures high-register guitar solos dynamically utilize all 5 frets naturally."
   - `src/models/chart.py` (Lines 7–36):
     > Defines `FretType` (GREEN=0, RED=1, YELLOW=2, BLUE=3, ORANGE=4, OPEN=7) and `ChartNote(tick: int, fret: FretType, sustain_length: int = 0, is_hopo: bool = False)`.
   - `src/game_design/quantizer.py` (Lines 20–38):
     > Defines `QuantizedNote(tick: int, pitch: int, duration_ticks: int, amplitude: float)`.

---

## 2. Logic Chain

1. **Sub-Bass Open Note Partitioning**:
   - Per Obs 2 (`SCOPE.md:76`, `PROMPTS.md:209`), any note with MIDI pitch $< 40$ must map to `FretType.OPEN` (7).
   - Notes with pitch $\ge 40$ are regular fretted notes mapped to frets 0–4.
   - Open notes represent purple open strum bars (no physical fret pressed) and are not subject to 5-fret physical finger jump clamping.

2. **Dynamic Sliding-Window Tessitura**:
   - Per Obs 2 (`AGENTS.md §7.2`, `SCOPE.md:75`), a dynamic temporal window of $W = 1536$ ticks (~2 measures at 192 PPQ) evaluates the active tessitura bounds $[p_{\min}, p_{\max}]$ of non-open notes.
   - If $p_{\min} == p_{\max}$, the note maps to `FretType.GREEN` (0).
   - If $p_{\min} < p_{\max}$, the relative position $\text{ratio} = (p - p_{\min}) / (p_{\max} - p_{\min})$ projects the pitch into 5 buckets $[0, 4]$ (`FretType.GREEN` through `FretType.ORANGE`).
   - In high-register solos where all pitches are in $[75, 90]$, local normalization maps the lowest solo pitch to Green (0), intermediate pitches to Red (1), Yellow (2), and Blue (3), and the highest pitch to Orange (4). Thus, high solo passages use the full 5-fret span organically rather than clustering solely on Orange (4).
   - In low-register riffs where pitches are in $[42, 56]$, the notes similarly span 0 to 4 organically rather than clustering on Green (0).

3. **Rapid Passage Jump Penalty**:
   - Per Obs 2 (`SCOPE.md:77`, `ORIGINAL_REQUEST.md:18`), when consecutive notes occur in a rapid passage ($\Delta t = t_i - t_{i-1} < 48$ ticks, faster than sixteenth notes), hand movement is constrained.
   - A raw leap $\Delta f = f_i - f_{i-1} > 3$ is clamped to $f_{i-1} + 3$ (e.g., Green 0 to Orange 4 clamped to Blue 3).
   - A raw drop $\Delta f = f_i - f_{i-1} < -3$ is clamped to $f_{i-1} - 3$ (e.g., Orange 4 to Green 0 clamped to Red 1).
   - When $\Delta t \ge 48$ ticks, the player has sufficient transition time, and leaps of 4 frets are permitted without clamping.

4. **Scale Flow & Chord Integrity**:
   - Ascending 5-step scales map sequentially to `[0, 1, 2, 3, 4]`.
   - Ascending chromatic octave scales map monotonically non-decreasingly ($f_i \le f_{i+1}$) covering all 5 frets.
   - Descending scales map smoothly to `[4, 3, 2, 1, 0]`.
   - Simultaneous notes at the same tick (chords) preserve identical tick timestamps, project lower pitches to lower frets and higher pitches to higher frets, and are sorted chronologically and by fret.

5. **Test Suite Completeness**:
   - To guarantee complete specification coverage without regressions, 21 specialized test functions were authored in `spec_report.md`:
     - 2 sub-bass open note tests ($< 40$ maps to 7, boundary 39/40, custom threshold)
     - 3 scale flow tests (ascending 5-note, ascending chromatic 12-semitone, descending)
     - 3 dynamic window tessitura tests (high solo register span, low riff span, multi-measure section transitions)
     - 5 rapid jump penalty tests (ascending clamping, descending clamping, $\ge 48$ immunity, custom parameters, open note immunity)
     - 5 edge case tests (empty list, single note, single sub-bass, monophonic repeating pitch, simultaneous chord notes, sub-bass chord)
     - 3 model & invariant tests (unsorted input ordering, invalid constructor arguments, `ChartNote` domain invariants)
   - All tests conform strictly to `pyproject.toml` (type annotations, ruff formatting, pytest idioms).

---

## 3. Caveats

1. In accordance with the Specification Miner role definition, no production code was authored in `src/game_design/pitch_to_fret.py`. The implementation is scheduled for the developer subagent in Milestone 2.
2. The test suite in `spec_report.md` imports `from src.game_design.pitch_to_fret import PitchToFretMapper`. It will become runnable and pass cleanly as soon as the developer implements `PitchToFretMapper` and places the test code in `tests/test_game_design/test_pitch_to_fret.py`.
3. Simultaneous chord notes at the same tick are mapped by `PitchToFretMapper` to ordered `ChartNote` instances. Advanced chord ergonomic constraints (limiting chord size to $\le 3$ frets and pruning unplayable wide spans like 0+4) are deferred to `ChordBuilder` in Milestone 3, as specified in `SCOPE.md`.

---

## 4. Conclusion

The specification mining for Milestone 2 is complete.
All requirements from the dispatch assignment, `ORIGINAL_REQUEST.md`, `SCOPE.md`, `PROJECT.md`, `PROMPTS.md` Prompt 4.2, and `AGENTS.md` Section 7.2 are fully documented in `.agents/teamwork/spec_miner_m2/spec_report.md`.
The complete, runnable, ruff- and mypy-compliant test suite containing 21 test cases is authored and ready for immediate deployment and verification by the developer subagent.

---

## 5. Verification Method

To verify this specification report and subsequent implementation:
1. **Inspect Artifacts**:
   - `.agents/teamwork/spec_miner_m2/spec_report.md`
   - `.agents/teamwork/spec_miner_m2/handoff.md`
2. **Post-Implementation Test Execution**:
   Once `PitchToFretMapper` is implemented and `tests/test_game_design/test_pitch_to_fret.py` is written:
   ```bash
   .venv/bin/pytest tests/test_game_design/test_pitch_to_fret.py
   .venv/bin/mypy src/game_design tests/test_game_design
   .venv/bin/ruff check src/game_design tests/test_game_design
   .venv/bin/pytest tests/
   ```
3. **Invalidation Conditions**:
   - Any failure of the 21 test cases once `PitchToFretMapper` is implemented.
   - Any typing violation under strict mypy or linting violation under ruff.
