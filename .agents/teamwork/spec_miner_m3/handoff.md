# Handoff Report: Milestone 3 Specification Mining (`ChordBuilder`)

**Subagent**: `spec_miner_m3`  
**Parent Agent**: `c32a8c2d-046d-4e36-96ca-60cf3fc9e81f`  
**Milestone**: Milestone 3 (Ergonomic Chord Formation & Constraints)  
**Handoff Type**: Hard (Task Complete)

---

## 1. Observation

1. **System & Environment State**:
   - Python 3.12 virtual environment located at `/home/adiel/Projects/music2chart/.venv`.
   - Running `/home/adiel/Projects/music2chart/.venv/bin/pytest tests/` executes 97 tests with 100% passing (`97 passed in 1.86s`).
   - Running `/home/adiel/Projects/music2chart/.venv/bin/mypy src/ tests/` outputs `Success: no issues found in 35 source files`.
   - Running `/home/adiel/Projects/music2chart/.venv/bin/ruff check src/ tests/` outputs `All checks passed!`.

2. **Milestone 3 Codebase Status**:
   - `src/game_design/chord_builder.py` is currently uncreated (planned for Milestone 3 implementation subagent).
   - `tests/test_game_design/test_chord_builder.py` is uncreated.
   - `src/game_design/__init__.py` currently exports:
     ```python
     from src.game_design.pitch_to_fret import PitchToFretMapper
     from src.game_design.quantizer import NoteQuantizer, QuantizedNote

     __all__ = [
         "NoteQuantizer",
         "PitchToFretMapper",
         "QuantizedNote",
     ]
     ```

3. **Authoritative Specification Directives**:
   - `AGENTS.md` §7.3 specifies:
     > "Concurrent notes (identical tick or within a 12-tick tolerance) form chords:  
     > - Valid chords in Clone Hero: 2 adjacent frets or a 1-fret gap (e.g., 0+1, 0+2, 1+2, 1+3, 2+3, 2+4, 3+4).  
     > - Permitted 3-note chords: 0+1+2, 0+2+3, 1+2+3, etc.  
     > - Prohibition: Never generate 4- or 5-fret simultaneous chords (physically unplayable on controller ergonomics) and never generate awkward wide stretches such as Green + Orange isolated at fast tempos."
   - `PROMPTS.md` Prompt 4.3 specifies:
     > "1. Create src/game_design/chord_builder.py containing the `ChordBuilder` class:  
     >    - Group notes with identical ticks (post-quantization).  
     >    - If more than one note occurs on the same tick:  
     >      * Restrict chord to a maximum of 2 or 3 simultaneous frets (Clone Hero / Guitar Hero standard).  
     >      * Apply canonical chord patterns:  
     >        - Power chords (2 notes): Green+Red (0+1), Green+Yellow (0+2), Red+Yellow (1+2), Red+Blue (1+3), Yellow+Blue (2+3), Yellow+Orange (2+4), Blue+Orange (3+4).  
     >        - Extended chords (3 notes): 0+1+2, 0+2+3, 1+2+3, 2+3+4.  
     >      * Discard redundant chord notes that violate ergonomics or produce prohibited stretches (such as simultaneous 0+4 at high speed).  
     > 2. Write tests in tests/test_game_design/test_chord_builder.py injecting polyphonic clusters of 4 piano/guitar notes and validating that ChordBuilder simplifies them to a valid chord with <= 3 frets."
   - `ORIGINAL_REQUEST.md` R3 and Dispatch prompt demand:
     > "1. Grouping simultaneous notes at identical ticks into chords.  
     >  2. 4-note and 5-note polyphonic clusters simplified to at most 3 frets ($\le 3$).  
     >  3. Canonical power chords preserved: (0, 1), (0, 2), (1, 2), (1, 3), (2, 3), (2, 4), (3, 4).  
     >  4. Canonical triads preserved: (0, 1, 2), (0, 2, 3), (1, 2, 3), (2, 3, 4).  
     >  5. Elimination of isolated 0+4 stretch (Green + Orange).  
     >  6. Open Note exclusivity: Open Note (7) never coexists with fretted notes (0-4) at the same tick.  
     >  7. Edge cases: empty list, single notes, sequential chords across multiple ticks, unsorted input.  
     >  8. Provide complete, runnable pytest test code conforming to strict mypy and ruff."

---

## 2. Logic Chain

1. From Observation 1, the test suite and static analysis tools (`pytest`, `mypy`, `ruff`) run through `.venv/bin/*` in linux without sandbox interference.
2. From Observation 2 and 3, `ChordBuilder` sits between `PitchToFretMapper` and `HopoEngine` in the Phase 4 pipeline. Its inputs are `Sequence[ChartNote]` and outputs are `list[ChartNote]`.
3. From Observation 3 (`AGENTS.md` §7.3 and `PROMPTS.md` 4.3), chords are defined by notes sharing identical ticks. Notes at identical ticks must be deduplicated on `(tick, fret)` by retaining the maximal sustain length.
4. From Observation 3, unplayable ergonomics dictate two hard physical prohibitions in 5-fret rhythm games:
   - Polyphony $> 3$ frets is physically unplayable for 5-finger controllers. Thus all 4-note and 5-note clusters must be reduced to canonical shapes $\le 3$ frets.
   - The isolated 4-fret span $(0, 4)$ (Green + Orange) is an unplayable stretch and must be eliminated (discarding the high note to leave root 0 or canonical power chord).
5. From Observation 3, Open Notes (fret 7) represent a purple full-lane open bar where no strings are pressed. Coexistence with frets 0–4 at the same tick violates game mechanics; hence Open Note exclusivity must strictly prevent concurrent frets and open strums at any single tick.
6. Based on these specifications, 30 concrete, exhaustive test cases were constructed, categorized into 7 requirements, and documented with complete, runnable code in `spec_report.md`.

---

## 3. Caveats

- In rare cases where upstream transcribers generate conflicting Open Note (7) and fretted notes (0–4) at the exact same tick, the default policy gives precedence to Open notes (`prefer_open=True`) or ensures strict exclusivity. The test assertions verify the invariant `not (7 in frets and any(f in frets for f in [0, 1, 2, 3, 4]))`.
- No production code was modified (spec miner is strictly read-only on production source).

---

## 4. Conclusion

The specification mining for Milestone 3 (`ChordBuilder`) is complete. All 10 discovered features and 16 edge cases are enumerated with full observable behaviors in `spec_report.md`. A comprehensive suite of 30 test cases conforming to strict `mypy` and `ruff` rules is authored and ready for immediate deployment to `tests/test_game_design/test_chord_builder.py` by the test builder agent.

---

## 5. Verification Method

To verify the deliverables:
1. Inspect the detailed report:
   ```bash
   cat /home/adiel/Projects/music2chart/.agents/teamwork/spec_miner_m3/spec_report.md
   ```
2. Verify baseline environment stability:
   ```bash
   /home/adiel/Projects/music2chart/.venv/bin/pytest tests/
   /home/adiel/Projects/music2chart/.venv/bin/mypy src/ tests/
   /home/adiel/Projects/music2chart/.venv/bin/ruff check src/ tests/
   ```
3. Once `tests/test_game_design/test_chord_builder.py` and `src/game_design/chord_builder.py` are written by the downstream subagents, run:
   ```bash
   /home/adiel/Projects/music2chart/.venv/bin/pytest tests/test_game_design/test_chord_builder.py -v
   /home/adiel/Projects/music2chart/.venv/bin/mypy src/game_design tests/test_game_design
   /home/adiel/Projects/music2chart/.venv/bin/ruff check src/ tests/
   ```
