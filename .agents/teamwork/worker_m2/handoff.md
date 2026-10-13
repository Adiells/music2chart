# Handoff Report: Milestone 2 Pitch-to-Fret Implementation

**Agent**: `worker_m2` (Milestone 2 Implementer)  
**Milestone**: Phase 4 — Milestone 2 (Adaptive Pitch-to-Fret Projection)  
**Type**: Hard Handoff (Implementation Complete & Verified)  
**Date**: 2026-10-13  
**Target Recipient**: Orchestrator (`c32a8c2d-046d-4e36-96ca-60cf3fc9e81f`)

---

## 1. Observation

1. **Delivered Source Files & Changes**:
   - `src/game_design/pitch_to_fret.py`:
     - Implemented `PitchToFretMapper` with constructor defaults `window_ticks=1536`, `max_jump=3`, `rapid_interval=48`, `open_threshold=40`.
     - Sub-bass separation: `pitch < open_threshold` directly maps to `FretType.OPEN` (7) and is excluded from fretted sliding window percentiles.
     - Centered sliding window $[tick - 768, tick + 768]$ with binary search (`bisect_left` and `bisect_right`).
     - Hybrid percentile projection:
       - Flat/monotone window ($p_{\max} - p_{\min} == 0$) -> `FretType.GREEN` (0).
       - Narrow span ($p_{\max} - p_{\min} < 5$) -> Rank-ordered assignment to consecutive frets $0$ to $K-1$.
       - Standard/wide span ($p_{\max} - p_{\min} \ge 5$) -> 5-point quartile references $[p_{\min}, Q_{25}, Q_{50}, Q_{75}, p_{\max}]$ using linear interpolation with median tie-breaking.
     - Rapid passage jump penalty: In rapid intervals ($0 < \Delta t < rapid\_interval$), leaps $|\Delta f| > max\_jump$ are directionally clamped toward the closest anchor fret from the previous fretted tick ($0 \to 4$ clamped to $3$ Blue, $4 \to 0$ clamped to $1$ Red).
     - Open notes are exempt from jump clamping and reset the fretting anchor state.
     - Output returns `list[ChartNote]` with `sustain_length=0` and `is_hopo=False`, deterministically sorted by `(tick, fret)`.
     - Convenience aliases provided: `map = map_notes`, `map_pitch_to_frets = map_notes`.
   - `src/game_design/__init__.py`:
     - Exported `PitchToFretMapper` alongside `NoteQuantizer` and `QuantizedNote`.
   - `tests/test_game_design/test_pitch_to_fret.py`:
     - Implemented 22 comprehensive unit tests covering sub-bass mapping, ascending/descending scales, solo and low-riff dynamic tessitura, section transitions, jump clamping, interval immunity, open note immunity, simultaneous chords, sub-bass chords, unsorted input, parameter validation, and `ChartNote` domain invariants.

2. **Verification Command Results**:
   - Unit tests:
     ```
     $ .venv/bin/pytest tests/test_game_design/test_pitch_to_fret.py -v
     ============================= test session starts ==============================
     platform linux -- Python 3.12.14, pytest-9.1.1, pluggy-1.6.0
     rootdir: /home/adiel/Projects/music2chart
     configfile: pyproject.toml
     plugins: asyncio-1.4.0, anyio-4.15.1, platformdirs-4.13.0
     collected 22 items

     tests/test_game_design/test_pitch_to_fret.py ......................      [100%]

     ============================== 22 passed in 0.04s ==============================
     ```
   - Full regression suite:
     ```
     $ .venv/bin/pytest tests/
     ============================= test session starts ==============================
     ........................................................................ [ 74%]
     .........................                                                [100%]
     97 passed in 1.91s
     ```
   - Strict static type checking:
     ```
     $ .venv/bin/mypy src/game_design tests/test_game_design
     Success: no issues found in 6 source files
     ```
   - Ruff linting:
     ```
     $ .venv/bin/ruff check src/game_design tests/test_game_design
     All checks passed!
     ```
   - Ruff formatting:
     ```
     $ .venv/bin/ruff format --check src/game_design tests/test_game_design
     6 files already formatted
     ```

---

## 2. Logic Chain

1. **Sub-Bass Open Note Isolation (supported by Obs 1 & 2)**:
   - Sub-bass frequencies ($< 40$ MIDI) correspond to unfretted open strums.
   - If sub-bass pitches were included in the fretted sliding window, the lower bound $p_{\min}$ would drop to 28-36, which would artificially compress and distort lead melodies (shifting middle C from Green to Yellow/Blue).
   - Isolating sub-bass notes before computing fretted percentiles anchors the lowest playable guitar riff at Green (0).
   - Open notes do not require neck fingering; therefore, open notes are excluded from fret leap distance metrics, never clamped, and reset the fretting anchor state machine (`last_fretted_tick = None`).

2. **Adaptive 5-Fret Tessitura (supported by Obs 1 & 2)**:
   - A symmetric centered window of 1536 ticks ($\pm 768$ ticks, 2 measures at 192 PPQ) provides smooth temporal context without causal phase lag.
   - For narrow intervals ($< 5$ semitones), rank ordering prevents 2-note trills from exploding across 4 frets.
   - For wide ranges ($\ge 5$ semitones), the 5-point quartile reference anchors minimum to Green (0), median ($Q_{50}$) to Yellow (2), and maximum to Orange (4), ensuring that high-register solos (pitches 75–90) and low riffs (pitches 42–56) organically utilize all 5 frets $\{0, 1, 2, 3, 4\}$ rather than clustering at a single extreme.

3. **Directional Jump Clamping (supported by Obs 1 & 2)**:
   - In rapid lines ($0 < \Delta t < 48$ ticks), transitions $> 3$ frets (specifically $0 \to 4$ and $4 \to 0$) exceed physical finger transition speeds.
   - Clamping leaps directionally ($0 \to 4$ becomes $3$ Blue, $4 \to 0$ becomes $1$ Red) preserves melodic contour while keeping notes ergonomically playable.
   - For simultaneous notes ($\Delta t = 0$), notes form chords and are not constrained by sequential jump penalties.

4. **Verification & Regression Invariance (supported by Obs 2)**:
   - All 22 new unit tests pass in 0.04s.
   - All 75 pre-existing tests continue to pass without regression (97 total passed in 1.91s).
   - Zero mypy issues across `src/game_design` and `tests/test_game_design`.
   - Zero ruff lint or formatting violations.

---

## 3. Caveats

1. **Chord Shape Constraints (Milestone 3)**:
   - `PitchToFretMapper` maps polyphonic notes at the same tick independently according to their pitch. Advanced chord simplification (limiting chords to $\le 3$ frets, canonical triad voicings, pruning unplayable $0+4$ stretches) is deferred to `ChordBuilder` in Milestone 3, as specified in `SCOPE.md`.
2. **HOPO and Sustain Tail Processing (Milestone 4)**:
   - All `ChartNote` instances emitted by `PitchToFretMapper` initialize `sustain_length = 0` and `is_hopo = False`. HOPO detection and sustain release calculations are deferred to Milestone 4 (`HopoEngine` and `SustainProcessor`).

---

## 4. Conclusion

Milestone 2 is complete. `PitchToFretMapper` is implemented in `src/game_design/pitch_to_fret.py`, exported in `src/game_design/__init__.py`, and verified with 22 unit tests in `tests/test_game_design/test_pitch_to_fret.py`. The implementation is fully compliant with all architectural, game design, and coding quality standards.

---

## 5. Verification Method

To independently verify this milestone:

```bash
# 1. Run unit tests for pitch-to-fret mapper (22 tests)
.venv/bin/pytest tests/test_game_design/test_pitch_to_fret.py -vv

# 2. Run full regression test suite (97 tests)
.venv/bin/pytest tests/

# 3. Verify static typing
.venv/bin/mypy src/game_design tests/test_game_design

# 4. Verify linting and formatting
.venv/bin/ruff check src/game_design tests/test_game_design
.venv/bin/ruff format --check src/game_design tests/test_game_design
```

**Invalidation Conditions**:
- Failure of any of the 22 tests in `test_pitch_to_fret.py`.
- Any regression in the existing 75 tests under `tests/`.
- Any type error under `mypy` or formatting violation under `ruff`.
