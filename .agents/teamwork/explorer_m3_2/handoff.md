# Handoff Report: Milestone 3 Forbidden Stretch Elimination & Open Note Exclusivity

**From**: `explorer_m3_2`  
**To**: Parent Orchestrator (`c32a8c2d-046d-4e36-96ca-60cf3fc9e81f`), Milestone 3 Worker (`worker_m3`), and Specification Miner (`spec_miner_m3`)  
**Milestone**: Phase 4 — Milestone 3 (Ergonomic Chord Formation & Constraints)  
**Date**: 2026-10-13  
**Handoff Type**: Hard (Investigation and Architecture Design Complete)  

---

## 1. Observation

1. **Physical Layout and Game Design Rules in `AGENTS.md`**:
   - `AGENTS.md` (lines 336–340):
     ```text
     ### 7.3. Chord Rules
     - Concurrent notes (identical tick or within a 12-tick tolerance) form chords:
       - Valid chords in Clone Hero: 2 adjacent frets or a 1-fret gap (e.g., 0+1, 0+2, 1+2, 1+3, 2+3, 2+4, 3+4).
       - Permitted 3-note chords: 0+1+2, 0+2+3, 1+2+3, etc.
       - Prohibition: Never generate 4- or 5-fret simultaneous chords (physically unplayable on controller ergonomics) and never generate awkward wide stretches such as Green + Orange isolated at fast tempos.
     ```
   - `AGENTS.md` (lines 328–333):
     ```text
     - Green (0): Lowest notes of the passage (e.g., low E string, rhythm base notes).
     - Red (1): Mid-low.
     - Yellow (2): Mid.
     - Blue (3): Mid-high.
     - Orange (4): Extreme highs and high-register solo notes.
     - Open (7): Reserved for heavy sub-bass palm-muted riffs or open bass notes.
     ```

2. **Milestone 3 Prompt Directives in `PROMPTS.md`**:
   - `PROMPTS.md` (lines 217–231, Prompt 4.3):
     ```text
     ### Prompt 4.3 — Chord Formation & Ergonomics (src/game_design/chord_builder.py)
     1. Create src/game_design/chord_builder.py containing the ChordBuilder class:
        - Group notes with identical ticks (post-quantization).
        - If more than one note occurs on the same tick:
          * Restrict chord to a maximum of 2 or 3 simultaneous frets (Clone Hero / Guitar Hero standard).
          * Apply canonical chord patterns:
            - Power chords (2 notes): Green+Red (0+1), Green+Yellow (0+2), Red+Yellow (1+2), Red+Blue (1+3), Yellow+Blue (2+3), Yellow+Orange (2+4), Blue+Orange (3+4).
            - Extended chords (3 notes): 0+1+2, 0+2+3, 1+2+3, 2+3+4.
          * Discard redundant chord notes that violate ergonomics or produce prohibited stretches (such as simultaneous 0+4 at high speed).
     ```

3. **Existing Model Implementation in `src/models/chart.py`**:
   - Lines 7–18 define `FretType`:
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
   - Lines 37–43 define `ChartNote.__lt__`:
     ```python
     def __lt__(self, other: "ChartNote") -> bool:
         if not isinstance(other, ChartNote):
             return NotImplemented
         if self.tick != other.tick:
             return self.tick < other.tick
         return self.fret < other.fret
     ```

4. **Upstream Collision Source in `src/game_design/pitch_to_fret.py`**:
   - Lines 185–220: `PitchToFretMapper.map_notes` processes each note independently. If a sub-bass note (`pitch < 40`) and a fretted note (`pitch >= 40`) share the same tick, both `ChartNote(tick, FretType.OPEN)` and `ChartNote(tick, FretType.GREEN)` are appended to `final_chart_notes`. This creates a tick with both Open and fretted notes, awaiting resolution in `ChordBuilder`.

5. **Test and Lint Tooling Status**:
   - Command: `.venv/bin/pytest tests/test_game_design`
     Result: 40 passed in 0.06s (18 in `test_quantizer.py`, 22 in `test_pitch_to_fret.py`).
   - Command: `.venv/bin/mypy src/game_design tests/test_game_design && .venv/bin/ruff check src/game_design tests/test_game_design`
     Result: Zero errors found.

---

## 2. Logic Chain

1. **Forbidden Stretch Elimination Reasoning**:
   - *Premise 1*: `AGENTS.md` §7.3 explicitly prohibits *"unnatural wide stretches such as Green + Orange isolated at fast tempos"*.
   - *Premise 2*: In Prompt 4.3, the complete set of canonical 2-note power chords is defined as:
     $$\{(0, 1), (0, 2), (1, 2), (1, 3), (2, 3), (2, 4), (3, 4)\}$$
   - *Observation*: Every canonical power chord has a span $f_{\text{high}} - f_{\text{low}} \le 2$. The dyad $(0, 4)$ has a span of 4 (maximum possible across 5 buttons), requiring index finger on 0 and pinky on 4 without intermediate fingers, which strains hand tendons and causes ghost fret strikes.
   - *Inference 1.1*: An isolated $(0, 4)$ dyad must be simplified. Reducing $(0, 4)$ to $(0, 2)$ preserves the root note (Green 0) and the polyphonic power chord texture, producing the standard Green-Yellow power chord.
   - *Inference 1.2*: Applying the generalized dyad clamping formula $f_{\text{high}} = f_{\text{low}} + 2$ whenever $f_{\text{high}} - f_{\text{low}} > 2$ maps $(0, 4) \to (0, 2)$, $(0, 3) \to (0, 2)$, and $(1, 4) \to (1, 3)$, while leaving all 7 canonical power chords invariant.
   - *Inference 1.3*: For triads spanning from 0 to 4:
     - `(0, 2, 4)` contains Yellow (2) as a center pivot, making it the symmetrical G-Y-O triad. It is not an *isolated* stretch. However, because Prompt 4.3 limits canonical triads to `{(0, 1, 2), (0, 2, 3), (1, 2, 3), (2, 3, 4)}`, strict mode simplifies `(0, 2, 4)` to `(0, 2, 3)`, while setting `allow_wide_triads=True` permits it.
     - Asymmetrical triads `(0, 1, 4)` and `(0, 3, 4)` contain 2-fret gaps and are simplified to `(0, 1, 2)` and `(2, 3, 4)` respectively.

2. **Open Note Exclusivity Reasoning**:
   - *Premise 1*: In Clone Hero, an Open Note (`FretType.OPEN = 7`) represents an open strum where the player must hit the strum bar without pressing any frets.
   - *Premise 2*: In the `.chart` file format, having `N 0 0` and `N 7 0` at the same tick causes rendering conflicts and fails rhythm game engine chart validation.
   - *Premise 3*: In `PitchToFretMapper`, Open Notes are emitted exclusively for pitches $< 40$ (sub-bass). When a sub-bass note coincides with higher pitches at the same tick, the sub-bass note is the true acoustic fundamental (e.g. open low string strum) and concurrent higher notes are harmonic overtones or bleed.
   - *Inference 2.1*: Open Note must be mutually exclusive with frets 0–4.
   - *Inference 2.2*: Open Note takes precedence (`open_note_precedence = True`), dropping all frets 0–4 at that tick and preserving the Open Note's `sustain_length`.

3. **Monophonic Passthrough & Output Ordering**:
   - *Premise 1*: Single notes at a tick are not chords and contain no forbidden stretches or open-note collisions.
   - *Inference 3.1*: Any single note passes through `ChordBuilder` with unchanged `tick`, `fret`, `sustain_length`, and `is_hopo`.
   - *Premise 2*: Clone Hero requires notes within a track to be ordered chronologically by `tick`, and for identical ticks, ascending by `fret`.
   - *Inference 3.2*: `ChartNote.__lt__` natively implements this exact lexicographical comparison. Calling `list.sort()` ensures 100% compliant ordering.

---

## 3. Caveats

1. **Sustain on Synthesized Frets**:
   When an isolated $(0, 4)$ dyad is simplified to $(0, 2)$, fret 2 (Yellow) did not exist in the raw input. Our design inherits the sustain length of the original chord cluster ($\max(\text{sustain})$) for the newly introduced fret 2, ensuring no sustain information is truncated.
2. **Triad Scope Definition**:
   Prompt 4.3 explicitly lists 4 canonical triads: `(0, 1, 2), (0, 2, 3), (1, 2, 3), (2, 3, 4)`. While Clone Hero Expert charters occasionally chart `(0, 2, 4)` (GYO), defaulting `allow_wide_triads = False` ensures strict adherence to Prompt 4.3 while providing an opt-in parameter for Expert charting flexibility.
3. **No Code Written to Source Files**:
   In strict compliance with our explorer role constraints, all code examples and architectural specifications are documented in `.agents/teamwork/explorer_m3_2/analysis.md` and this handoff. No source files under `src/` or `tests/` were altered.

---

## 4. Conclusion

1. **Architecture Blueprint Complete**:
   The full design for `ChordBuilder` in `src/game_design/chord_builder.py` is established with complete class signatures, helper algorithms, and edge-case handling.
2. **Forbidden Stretch Resolution**:
   - Isolated `(0, 4)` simplifies to canonical power chord `(0, 2)`.
   - Generalized dyad rule $f_{\text{high}} = f_{\text{low}} + 2$ eliminates all 2-note stretches with span $> 2$.
   - Symmetrical triad `(0, 2, 4)` is configurable via `allow_wide_triads: bool = False`.
3. **Open Note Exclusivity**:
   - Open Note (7) is strictly exclusive at any tick.
   - Open Note takes precedence by default, dropping concurrent fretted notes (0–4).
4. **Monophonic & Sorting Contracts**:
   - Single notes pass through invariant.
   - Output is sorted by `(tick, fret)` ascending.
5. **Ready for Worker Implementation**:
   The Worker (`worker_m3`) can directly implement `src/game_design/chord_builder.py` using the reference implementation in `analysis.md`.

---

## 5. Verification Method

Once `worker_m3` implements `src/game_design/chord_builder.py` and `spec_miner_m3` creates `tests/test_game_design/test_chord_builder.py`, the implementation can be independently verified using:

1. **Unit Test Suite**:
   ```bash
   .venv/bin/pytest tests/test_game_design/test_chord_builder.py -v
   ```
2. **Full Game Design Regression**:
   ```bash
   .venv/bin/pytest tests/test_game_design/ -v
   ```
   (Must pass all tests in `test_quantizer.py`, `test_pitch_to_fret.py`, and `test_chord_builder.py`).
3. **Strict Type Checking**:
   ```bash
   .venv/bin/mypy src/game_design tests/test_game_design
   ```
4. **Code Quality & Formatting**:
   ```bash
   .venv/bin/ruff check src/game_design tests/test_game_design
   .venv/bin/ruff format --check src/game_design tests/test_game_design
   ```

### Invalidation Conditions:
- If `ChordBuilder` generates a chart containing both Fret 7 and any fret in 0–4 at the same tick, Open Note exclusivity is invalidated.
- If `ChordBuilder` outputs a 2-note chord `(0, 4)` without intermediate frets, stretch elimination is invalidated.
- If single notes change tick, fret, or sustain when processed through `build_chords`, monophonic invariance is invalidated.
