# Milestone 2 Review & Adversarial Stress-Test Report: Pitch-to-Fret Engine

**Reviewer**: `reviewer_m2_1`  
**Milestone**: Phase 4 — Milestone 2 (Adaptive Pitch-to-Fret Projection)  
**Verdict**: `APPROVE`  
**Date**: 2026-10-13  
**Target Recipient**: Orchestrator (`c32a8c2d-046d-4e36-96ca-60cf3fc9e81f`)

---

## 1. Observation

1. **Delivered Source Files & Implementation**:
   - `src/game_design/pitch_to_fret.py` (235 lines):
     - Implements `PitchToFretMapper` with configurable constants `DEFAULT_WINDOW_TICKS = 1536`, `DEFAULT_MAX_JUMP = 3`, `DEFAULT_RAPID_INTERVAL = 48`, `DEFAULT_OPEN_THRESHOLD = 40`.
     - Validates constructor parameters with `ValueError` on non-positive window, non-positive max jump, negative rapid interval, or out-of-range open threshold (lines 51–58).
     - Sub-bass separation: `qn.pitch < open_threshold` directly maps to `FretType.OPEN` (7) and is filtered out of fretted sliding window percentiles (`valid = [p for p in window_pitches if p >= self.open_threshold]`, lines 92, 158–160).
     - Temporal sliding window $[tick - 768, tick + 768]$ implemented via `bisect.bisect_left` and `bisect.bisect_right` on sorted tick arrays (lines 162–166).
     - Hybrid percentile projection:
       - Flat/monotone window ($p_{\max} - p_{\min} == 0$) -> `FretType.GREEN` (0) (line 101).
       - Narrow span ($p_{\max} - p_{\min} < 5$) -> Rank-ordered mapping into consecutive frets $0 \dots K-1$ using `unique_p.index(target_pitch)` bounded to 4 (lines 105–107).
       - Standard/wide span ($p_{\max} - p_{\min} \ge 5$) -> Quartile reference thresholds $[p_{\min}, Q_{25}, Q_{50}, Q_{75}, p_{\max}]$ via linear interpolation with median-based tie-breaking (lines 109–138).
     - Rapid passage directional jump clamping: for intervals $0 < \Delta t < rapid\_interval$, if $|\Delta f| > max\_jump$ relative to the closest anchor fret in the previous fretted chord/note, leaps are clamped directionally: $0 \to 4$ clamped to $3$ (Blue), $4 \to 0$ clamped to $1$ (Red) (lines 197–210).
     - Open notes are exempt from jump penalty, never clamped, and reset the fretting anchor state (`last_fretted_tick = None`, line 226).
     - Output returns chronologically sorted `list[ChartNote]` with `sustain_length=0` and `is_hopo=False` (lines 188–194, 214–220, 229).
   - `src/game_design/__init__.py`:
     - Exports `PitchToFretMapper` alongside `NoteQuantizer` and `QuantizedNote`.
   - `tests/test_game_design/test_pitch_to_fret.py` (390 lines):
     - Contains 22 distinct unit tests covering sub-bass mapping, custom threshold partitioning, 5-fret ascending/descending scales, chromatic run monotonicity, solo high-register tessitura, low riff tessitura, section transitions, jump clamping directions, interval threshold boundaries, custom parameters, open note immunity, empty inputs, single notes, repeating pitches, simultaneous chord preservation, sub-bass chords, unsorted input handling, constructor validation, and `ChartNote` domain invariants.

2. **Automated Verification Command Execution**:
   - `pytest tests/test_game_design/test_pitch_to_fret.py -v`:
     ```
     ============================== 22 passed in 0.04s ==============================
     ```
   - Full regression suite `pytest tests/`:
     ```
     97 passed in 1.90s
     ```
   - Static type checking `mypy src/game_design tests/test_game_design`:
     ```
     Success: no issues found in 6 source files
     ```
   - Linting `ruff check src/game_design tests/test_game_design`:
     ```
     All checks passed!
     ```
   - Code formatting `ruff format --check src/game_design tests/test_game_design`:
     ```
     6 files already formatted
     ```

3. **Integrity & Code Quality Inspection**:
   - No hardcoded test values, shortcuts, facade implementations, or stubs detected.
   - Algorithms for linear percentile interpolation, sliding window search, and rapid jump clamping are fully implemented natively using standard library constructs (`bisect`, `collections`).

4. **Adversarial Stress-Testing Results**:
   - Small window ($window\_ticks = 24$): Correctly falls back to degenerate single-note / flat window mapping without division by zero.
   - Alternating open note passage (`[Green 0, Open 7, Orange 4]` at 24-tick intervals): Confirmed Open strum resets fretting anchor, allowing immediate Orange positioning at tick 48 without false jump penalty.
   - Consecutive rapid steps (`[Green 0, Orange 4, Orange 4]` at 24-tick intervals): Clamps first jump $0 \to 4$ to Blue 3 at tick 24, and then successfully transitions from Blue 3 to Orange 4 at tick 48 ($3 \to 4$, leap distance 1), demonstrating smooth musical contour tracking over consecutive intervals.
   - Narrow span trill tests: 1-note maps to Green, 2-note trills map to Green and Red, 3-note riffs map to Green, Red, Yellow, without artificially spreading across all 5 frets.
   - Performance benchmark: 2,000 notes in dense polyphony mapped in 0.0127 seconds (~12.7 ms), confirming $O(N \log N)$ complexity.
   - Generator/iterator input: `map_notes((x for x in []))` cleanly returns `[]`.

---

## 2. Logic Chain

1. **Verification of Correctness (supported by Obs 1, 2, 4)**:
   - Pitch $< 40$ mapping: `test_sub_bass_open_note` and `test_sub_bass_custom_open_threshold` confirm sub-bass frequencies cleanly translate to `FretType.OPEN`.
   - Sliding window percentiles: In high solo passages (pitches 75–90), notes organically utilize all 5 frets rather than clustering on Orange. In low riffs (pitches 42–56), notes utilize all 5 frets rather than clustering on Green.
   - Rapid passage jump clamping: `test_rapid_passage_jump_penalty_ascending` confirms $0 \to 4$ in 24 ticks is clamped to Blue (3). `test_rapid_passage_jump_penalty_descending` confirms $4 \to 0$ in 24 ticks is clamped to Red (1). Intervals $\ge 48$ ticks permit full leaps without restriction (`test_jump_penalty_not_applied_at_or_above_48_ticks`).

2. **Verification of Invariants (supported by Obs 1, 4)**:
   - Simultaneous notes: In `map_notes`, jump clamping checks `0 < tick - last_fretted_tick < self.rapid_interval`. Because simultaneous notes share identical `tick` ($\Delta t = 0$), they are never clamped against each other. Simultaneous notes form valid chord voicings preserved in `final_chart_notes` (`test_simultaneous_notes_chord_mapping`).
   - Open notes: Filtered out before computing `w_pitches` fretted percentiles, preventing sub-bass drops from skewing lead melodies. Open notes are never clamped and reset the fretting anchor state.

3. **Verification of Robustness & Quality (supported by Obs 2, 4)**:
   - Degenerate inputs (empty sequences, single notes, flat pitch windows, narrow spans) pass cleanly without exceptions or division-by-zero errors.
   - Strict typing is verified: 100% compliant with mypy in strict mode.
   - Code formatting and linting pass with zero warnings under ruff.
   - Regression suite: 97/97 tests pass with zero regressions.

4. **Integrity Validation (supported by Obs 3)**:
   - Genuine, generic implementations across all methods without test-specific branching or shortcuts.

---

## 3. Caveats

1. **Downstream Chord Constraints**:
   - `PitchToFretMapper` maps polyphonic notes at identical ticks independently based on their pitch percentiles. Chord simplification (pruning chords $> 3$ frets, canonical Clone Hero triad shapes, and eliminating unplayable $0+4$ stretches) is the responsibility of `ChordBuilder` in Milestone 3, as specified in `SCOPE.md`.
2. **HOPO and Sustain Deferral**:
   - `ChartNote` instances produced by this mapper initialize `sustain_length = 0` and `is_hopo = False`. HOPO detection and sustain release calculations are deferred to Milestone 4 (`HopoEngine` and `SustainProcessor`).

---

## 4. Conclusion

Milestone 2 deliverables in `src/game_design/pitch_to_fret.py`, `src/game_design/__init__.py`, and `tests/test_game_design/test_pitch_to_fret.py` are mathematically sound, musically authentic, rigorously tested, and fully conformant with project specifications and engineering guidelines.

**Verdict**: `APPROVE`

---

## 5. Verification Method

To independently reproduce and verify this assessment:

```bash
# 1. Run unit tests for pitch-to-fret engine (22 tests)
.venv/bin/pytest tests/test_game_design/test_pitch_to_fret.py -v

# 2. Run full regression test suite (97 tests)
.venv/bin/pytest tests/

# 3. Verify strict static typing
.venv/bin/mypy src/game_design tests/test_game_design

# 4. Verify ruff linting
.venv/bin/ruff check src/game_design tests/test_game_design

# 5. Verify ruff formatting
.venv/bin/ruff format --check src/game_design tests/test_game_design
```

**Invalidation Conditions**:
- Failure of any of the 22 tests in `test_pitch_to_fret.py`.
- Any regression in the 75 baseline tests in `tests/`.
- Any type error under `mypy` or formatting issue under `ruff`.
- Any detected integrity violation or hardcoded logic.
