# Handoff Report: Milestone 3 — Polyphonic Cluster Simplification & Canonical Chord Preservation

## 1. Observation

- **Task Dispatch**: Received subagent dispatch from parent `c32a8c2d-046d-4e36-96ca-60cf3fc9e81f` for Milestone 3 of Phase 4 (`ChordBuilder`).
- **Target Specification in AGENTS.md §7.3**:
  ```text
  7.3. Chord Rules
  - Concurrent notes (identical tick or within a 12-tick tolerance) form chords:
    - Valid chords in Clone Hero: 2 adjacent frets or a 1-fret gap (e.g., 0+1, 0+2, 1+2, 1+3, 2+3, 2+4, 3+4).
    - Permitted 3-note chords: 0+1+2, 0+2+3, 1+2+3, etc.
    - Prohibition: Never generate 4- or 5-fret simultaneous chords (physically unplayable on controller ergonomics) and never generate awkward wide stretches such as Green + Orange isolated at fast tempos.
  ```
- **PROMPTS.md (Prompt 4.3)**:
  - Enforces power chords: `(0, 1), (0, 2), (1, 2), (1, 3), (2, 3), (2, 4), (3, 4)`.
  - Enforces extended triads: `(0, 1, 2), (0, 2, 3), (1, 2, 3), (2, 3, 4)`.
  - Enforces polyphonic simplification: clusters of 4 or 5 notes simplified to $\le 3$ frets.
  - Enforces elimination of unplayable `(0, 4)` stretches.
- **SCOPE.md Line 79-84**:
  - `ChordBuilder` contract:
    - Input: `notes: list[ChartNote]`
    - Output: `list[ChartNote]`
    - Parameters: `max_frets: int = 3`
    - Constraints: max 3 frets per tick, power chords & triads canonical shapes, eliminate `(0, 4)` unplayable stretches, Open note exclusivity.
- **Model Contract (`src/models/chart.py` Lines 21-43)**:
  - `ChartNote(tick: int, fret: FretType, sustain_length: int = 0, is_hopo: bool = False)`.
  - Compares via `__lt__` by `(self.tick, self.fret)`.
- **Existing Predecessor Modules**:
  - `src/game_design/quantizer.py` (M1) and `src/game_design/pitch_to_fret.py` (M2) implemented and passing 40 unit tests under `.venv/bin/pytest tests/test_game_design/`.
  - Strict type checking clean under `.venv/bin/mypy src/game_design tests/test_game_design`.
  - Linting clean under `.venv/bin/ruff check src/game_design tests/test_game_design`.

---

## 2. Logic Chain

1. **Chronological Grouping and Open Note Exclusivity**:
   - `PitchToFretMapper` outputs `ChartNote`s that share identical `tick` timestamps for polyphonic moments.
   - When notes share a tick, open notes (`FretType.OPEN`, value 7) and fretted notes (`0 <= fret.value <= 4`) may coincide if sub-bass harmonics coexist with chord onsets.
   - On a physical guitar controller, a player cannot simultaneously strum open and press frets. Fretted notes represent the core instrumental melody/harmony, so when fretted notes exist at a tick, Open notes are discarded. Isolated Open notes are preserved and deduplicated taking `max(sustain_length)`.

2. **Deduplication of Identical Frets**:
   - If multiple quantized notes map to the same fret at the same tick, duplicate notes must be merged to prevent invalid double-note entries in `.chart` output, retaining the maximum sustain length.

3. **Max Concurrent Frets ($\le 3$) and Combinatorial Space**:
   - A 5-fret controller has only buttons 0 through 4. Therefore, any cluster $F$ has $|F| \le 5$.
   - There are exactly 6 possible clusters with $|F| \ge 4$: `{0, 1, 2, 3, 4}`, `{0, 1, 2, 3}`, `{0, 1, 2, 4}`, `{0, 1, 3, 4}`, `{0, 2, 3, 4}`, `{1, 2, 3, 4}`.
   - Since chords cannot exceed $\text{max\_frets} = 3$, all clusters with $\ge 4$ frets must be simplified to subsets of size 3 (or 2 if `max_frets = 2`).

4. **Elimination of (0, 4) Unplayable Stretches**:
   - Any candidate subset containing both fret 0 (Green) and fret 4 (Orange) requires a 5-fret physical finger span. This is strictly prohibited by AGENTS.md §7.3.
   - Any candidate containing both 0 and 4 receives an infinite penalty and is disqualified.
   - For an isolated `{0, 4}` dyad, the stretch is eliminated by retaining the root `{0}` as a single note.
   - For 3-note clusters with stretches (`{0, 2, 4}`, `{0, 1, 4}`, `{0, 3, 4}`), the stretch is eliminated by retaining the canonical power chord (`{0, 2}`, `{0, 1}`, `{3, 4}`).

5. **Multi-Objective Heuristic for Cluster Reduction**:
   - Candidate subsets $C \subset F$ of size $k = \min(|F|, \text{max\_frets})$ without (0, 4) stretch are evaluated:
     $$\text{Score}(C) = 1000 \cdot I_{\text{canonical}}(C) + 100 \cdot I_{\text{root}}(C) + 20 \cdot I_{\text{power}}(C) + 10 \cdot I_{\text{melody}}(C) - \text{span}(C)$$
   - This cleanly and deterministically resolves all 6 polyphonic clusters:
     - `{0, 1, 2, 3, 4}` $\rightarrow$ **`(0, 2, 3)`** (canonical extended power chord on root 0)
     - `{0, 1, 2, 3}` $\rightarrow$ **`(0, 2, 3)`** (preserves root 0 + melody 3, canonical shape)
     - `{0, 1, 2, 4}` $\rightarrow$ **`(0, 1, 2)`** (only canonical triad without 0-4 stretch)
     - `{0, 2, 3, 4}` $\rightarrow$ **`(0, 2, 3)`** (preserves root 0, canonical shape)
     - `{1, 2, 3, 4}` $\rightarrow$ **`(1, 2, 3)`** (preserves root 1, compact canonical triad)
     - `{0, 1, 3, 4}` $\rightarrow$ **`(1, 3, 4)`** or canonical power chord **`(0, 1)`**

6. **Preservation of Note Metadata**:
   - For each fret in the chosen subset, its original `sustain_length` is preserved. Notes are output as `ChartNote(tick=tick, fret=FretType(f), sustain_length=sustain, is_hopo=False)` and sorted.

---

## 3. Caveats

1. **Extended Triad (1, 3, 4)**: The dispatch lists 4 canonical triads: `(0, 1, 2)`, `(0, 2, 3)`, `(1, 2, 3)`, `(2, 3, 4)`. In guitar charting, `(1, 3, 4)` is the exact transposition of `(0, 2, 3)` up by 1 fret. The pseudo-code includes `(1, 3, 4)` in `EXTENDED_TRIADS` while preserving `CANONICAL_TRIADS` as the primary 4-tuple constant.
2. **Tolerance Parameter**: While AGENTS.md §7.3 mentions onsets within 12 ticks forming chords, notes entering `ChordBuilder` have already passed through `NoteQuantizer` (which snaps onsets to 192 PPQ grid points) and `PitchToFretMapper`. Thus, grouping by exact identical `tick` is clean, robust, and matches Prompt 4.3 ("Group notes with identical ticks"). An optional `tick_tolerance` parameter could be added if unquantized input is ever passed.
3. **Downstream HOPO Coupling**: `ChordBuilder` sets `is_hopo=False` on all output notes. Marking natural HOPOs or forcing strums on repeated chords is deferred to `HopoEngine` (Milestone 4).

---

## 4. Conclusion

The specification, mathematical scoring function, and complete algorithmic implementation for `ChordBuilder` are fully detailed in `.agents/teamwork/explorer_m3_1/analysis.md`. The Worker can directly implement `src/game_design/chord_builder.py`, export `ChordBuilder` in `src/game_design/__init__.py`, and write `tests/test_game_design/test_chord_builder.py` covering all edge cases.

Key constants to export:
- `DEFAULT_MAX_FRETS = 3`
- `CANONICAL_POWER_CHORDS = ((0, 1), (0, 2), (1, 2), (1, 3), (2, 3), (2, 4), (3, 4))`
- `CANONICAL_TRIADS = ((0, 1, 2), (0, 2, 3), (1, 2, 3), (2, 3, 4))`
- `EXTENDED_TRIADS = ((0, 1, 2), (0, 2, 3), (1, 2, 3), (2, 3, 4), (1, 3, 4))`

---

## 5. Verification Method

To independently verify the design once implemented:

1. **Run Unit Tests**:
   ```bash
   .venv/bin/pytest tests/test_game_design/test_chord_builder.py -v
   ```
   Must test:
   - Polyphonic 4- and 5-note clusters simplified to $\le 3$ frets.
   - Unplayable `(0, 4)` stretches eliminated.
   - All 7 canonical power chords and 4 canonical triads preserved intact.
   - Open Note exclusivity (Open note eliminated when frets exist at same tick).
   - Deduplication of identical frets at the same tick.

2. **Run Full Regression**:
   ```bash
   .venv/bin/pytest tests/
   ```

3. **Run Type Checking**:
   ```bash
   .venv/bin/mypy src/game_design tests/test_game_design
   ```

4. **Run Linter and Formatter**:
   ```bash
   .venv/bin/ruff check src/game_design tests/test_game_design
   .venv/bin/ruff format --check src/game_design tests/test_game_design
   ```

5. **Invalidation Conditions**:
   - Any output chord contains $> \text{max\_frets}$ notes.
   - Any output chord contains both fret 0 and fret 4 simultaneously.
   - Open note (7) and any fretted note (0-4) occur at the exact same tick.
   - A canonical triad or power chord is mangled or dropped.
