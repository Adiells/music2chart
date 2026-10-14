# Handoff Report: Jump Penalty, Open Note Mapping, and API Contract

**Agent**: `explorer_m2_2`  
**Milestone**: Milestone 2 (Phase 4 Game Design Engine)  
**Deliverable**: Design specification for `PitchToFretMapper` in `src/game_design/pitch_to_fret.py`  
**Date**: 2026-10-13  

---

## 1. Observation

Direct observations from source code, project specifications, and runtime tests:

1. **Model Contracts**:
   - `src/models/chart.py:7-18`:
     ```python
     class FretType(IntEnum):
         GREEN = 0
         RED = 1
         YELLOW = 2
         BLUE = 3
         ORANGE = 4
         HOPO_FORCE = 5
         STRUM_FORCE = 6
         OPEN = 7
     ```
   - `src/models/chart.py:20-28`:
     ```python
     @dataclass
     class ChartNote:
         tick: int
         fret: FretType
         sustain_length: int = 0
         is_hopo: bool = False
     ```
   - `src/game_design/quantizer.py:20-28`:
     ```python
     @dataclass(frozen=True, slots=True, order=True)
     class QuantizedNote:
         tick: int
         pitch: int
         duration_ticks: int
         amplitude: float
     ```
   - `src/game_design/__init__.py:1-8`: Currently only exports `NoteQuantizer` and `QuantizedNote`.

2. **Milestone Specifications**:
   - `orchestrator/SCOPE.md:72-78`:
     ```text
     PitchToFretMapper (src/game_design/pitch_to_fret.py)
     - Input: notes: list[QuantizedNote]
     - Output: list[ChartNote] where ChartNote(tick: int, fret: FretType, sustain_length: int, is_hopo: bool)
     - Parameters: window_ticks: int = 1536, max_jump: int = 3, rapid_interval: int = 48, open_threshold: int = 40
     - Open Note: pitch < 40 -> FretType.OPEN (7)
     - Jump penalty: if tick - prev_tick < 48 and abs(fret - prev_fret) > 3, clamp leap to <= 3 frets.
     ```
   - `PROMPTS.md:209-210`:
     ```text
     - Add Open Note (7) rule: very low pitch notes (< MIDI 40) occurring isolated in fast rhythmic passages must be mapped as Fret 7.
     - Add transition smoothness constraint: penalize impossible jumps of >3 frets in intervals < 48 ticks (prevent consecutive jumps from Green to Orange in sixteenth notes).
     ```

3. **Runtime Test Suite**:
   - `.venv/bin/pytest tests/test_game_design/`: 18 passing unit tests under `test_quantizer.py` verifying Milestone 1 completion.

---

## 2. Logic Chain

1. **Sub-Bass & Open Note Mapping (`pitch < 40`)**:
   - *Observation*: Standard 6-string guitar has E2 at MIDI 40. Lower notes represent Drop D (MIDI 38), 7-string bass fundamentals, or extreme sub-bass. Clone Hero uses `FretType.OPEN` (7) for unfretted strums.
   - *Inference 1 (Window Decoupling)*: If notes with `pitch < 40` were included in the local sliding window's pitch distribution for fretted notes ($[0, 4]$), they would artificially depress the lower percentiles. As a result, standard lead notes (e.g. MIDI 60) would be mapped to Orange (4), collapsing melodic solo ranges. Therefore, sub-bass notes must be mapped directly to `FretType.OPEN` (7) and **excluded** from the percentile calculation of the 5-fret sliding window.
   - *Inference 2 (Fret Leap Exclusion)*: `FretType.OPEN` (7) is an open strum requiring zero fret depression on the guitar neck. If $|7 - \text{fret}|$ were calculated, transitions between Open (7) and Green (0) would yield a distance of 7, causing erroneous clamping. Therefore, `FretType.OPEN` (7) is excluded from fret leap distance metrics, is never clamped, and resets the fretting anchor state machine (`last_fretted_tick = None`).

2. **Rapid Passage Jump Penalty (`interval < 48`, `leap > 3`)**:
   - *Observation*: `rapid_interval = 48` ticks is exactly a 16th note at 192 PPQ. In the 5-fret domain $\{0, 1, 2, 3, 4\}$, the only pairs with distance $> 3$ are $(0, 4)$ and $(4, 0)$ (Green and Orange).
   - *Inference 1 (Directional Clamping)*:
     - An upward leap from Green (0) to Orange (4) in $< 48$ ticks is clamped to `0 + 3 = 3` (Blue).
     - A downward leap from Orange (4) to Green (0) in $< 48$ ticks is clamped to `4 - 3 = 1` (Red).
     - Clamping preserves the direction of melodic movement while keeping the note at the closest ergonomically reachable fret.
   - *Inference 2 (Simultaneous Note Immunity)*: At $\Delta\text{tick} = 0$, simultaneous notes form chords. The jump penalty applies only to strictly positive chronological intervals ($0 < \Delta\text{tick} < 48$). Polyphonic cluster simplification is handled in Milestone 3 by `ChordBuilder`.
   - *Inference 3 (Chord-to-Note Transitions)*: When transitioning from a chord at tick $T_1$ to a note at tick $T_2$ ($0 < T_2 - T_1 < 48$), the reference anchor is the closest fret among the chord's fretted notes, accurately reflecting the physical proximity of the player's fingers.

3. **API & Output Contract**:
   - *Observation*: `ChartNote` requires `tick`, `fret`, `sustain_length`, and `is_hopo`.
   - *Inference*: In Phase 4's modular pipeline, `PitchToFretMapper` is solely responsible for pitch-to-fret projection. It outputs `ChartNote` with `sustain_length=0` and `is_hopo=False`. Downstream components (`ChordBuilder`, `HopoEngine`, `SustainProcessor`) modify chord shapes, HOPO flags, and sustain tails respectively.

---

## 3. Caveats

1. **Alternative State Persistence Across Open Notes**: We evaluated whether an Open note occurring between two fretted notes within $< 48$ ticks (e.g. Green 0 at tick 0, Open 7 at tick 12, Orange 4 at tick 24) should clamp Orange to Blue. We concluded that since playing an open note releases all fret buttons on the neck, the fretting hand is unconstrained and free to position over any fret. Resetting the fretting anchor on open notes correctly models this physical freedom and prevents false clamps on common open-pedal rock riffs.
2. **Percentile Algorithm Synergy**: While `explorer_m2_1` is detailing the sliding-window quantile binning formula, our jump penalty and open note logic operates cleanly regardless of whether quantile binning uses rank ratios or linear interpolation.
3. **Chord Spacing**: Wide chord stretches at the same tick (e.g. 0+4 simultaneous) are not modified by `PitchToFretMapper`. They are explicitly deferred to Milestone 3 (`ChordBuilder`).

---

## 4. Conclusion

The specification for `PitchToFretMapper` is complete, fully aligned with Clone Hero mechanics, and ready for Worker implementation:
- **Module**: `src/game_design/pitch_to_fret.py`
- **Class**: `PitchToFretMapper`
- **Constructor Defaults**: `window_ticks=1536`, `max_jump=3`, `rapid_interval=48`, `open_threshold=40`
- **Sub-bass Rule**: `pitch < 40 -> FretType.OPEN (7)`, excluded from fretted sliding window percentiles.
- **Jump Penalty Rule**: For $0 < \Delta\text{tick} < 48$, leaps $|f_{\text{curr}} - f_{\text{prev}}| > 3$ are directionally clamped: $0 \to 4$ becomes $3$ (Blue); $4 \to 0$ becomes $1$ (Red).
- **Open Note Immunity**: Open notes are never clamped and reset the fretting anchor.
- **Output Format**: Returns `list[ChartNote]` with `sustain_length=0`, `is_hopo=False`, sorted by `(tick, fret)`.

---

## 5. Verification Method

Once implemented by the Worker:

1. **Unit Test Execution**:
   Run the test suite using the project virtual environment:
   ```bash
   .venv/bin/pytest tests/test_game_design/test_pitch_to_fret.py -v
   ```
2. **Key Invariant Tests**:
   - Sub-bass test: Note with pitch 38 maps to `ChartNote(tick=..., fret=FretType.OPEN, sustain_length=0, is_hopo=False)`.
   - Rapid leap upward: Note at tick 0 (fret 0) followed by note at tick 24 (initially fret 4) results in tick 24 having `fret=FretType.BLUE (3)`.
   - Rapid leap downward: Note at tick 0 (fret 4) followed by note at tick 24 (initially fret 0) results in tick 24 having `fret=FretType.RED (1)`.
   - Normal interval leap: Note at tick 0 (fret 0) followed by note at tick 48 (fret 4) remains `fret=FretType.ORANGE (4)`.
   - Open note immunity: Rapid sequence `Open (tick 0) -> Orange (tick 24)` does not clamp Orange.
3. **Type & Lint Checking**:
   ```bash
   .venv/bin/mypy src/game_design tests/test_game_design
   .venv/bin/ruff check src/game_design tests/test_game_design
   ```
4. **Invalidation Conditions**:
   - If `PitchToFretMapper` clamps an Open note to any fretted value.
   - If simultaneous notes at the same tick clamp each other.
   - If `sustain_length != 0` or `is_hopo != False` in the output notes.
