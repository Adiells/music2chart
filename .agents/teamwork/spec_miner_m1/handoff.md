# Handoff Report: Milestone 1 Quantizer Specification & Test Plan

**Agent**: `spec_miner_m1` (Specification Miner)  
**Milestone**: Milestone 1 (Quantization & Grid Snapping)  
**Target Files**:
- Specifications: `.agents/teamwork/spec_miner_m1/spec_report.md`
- Target Test File: `tests/test_game_design/test_quantizer.py`
- Target Implementation: `src/game_design/quantizer.py`

---

## 1. Observation

1. **Environment and Base Health**:
   - Running `.venv/bin/pytest tests/` produced:
     ```
     57 passed in 1.86s
     ```
   - Running `.venv/bin/mypy src tests` and `.venv/bin/ruff check src tests` produced:
     ```
     Success: no issues found in 31 source files
     All checks passed!
     ```
2. **Authoritative Sources**:
   - `AGENTS.md` (Lines 77, 101, 161–171): Defines 192 PPQ resolution, subdivisions (1/4 = 192, 1/8 = 96, 1/16 = 48, 1/12 = 64, 1/24 = 32, 1/32 = 24), and onset snapping tolerance.
   - `ORIGINAL_REQUEST.md` (Lines 14–16, 29–30):
     > "R1. Musical Quantization & Grid Snapping: Snapping raw onset timestamps to standard 192 PPQ subdivisions (1/4, 1/8, 1/12, 1/16, 1/24, 1/32) with a 16-tick tolerance window, eliminating duplicates while preserving velocity and amplitude."
     > "test_quantizer.py: validates grid snapping for quarter, 1/8, 1/12, 1/16, 1/24, 1/32 notes and deduplication."
   - `PROMPTS.md` (Lines 176–194, Prompt 4.1):
     > "1. Crie src/game_design/quantizer.py com a classe `NoteQuantizer`: Receba a lista de `NoteEvent` e o `TempoMap`... Defina os grids válidos de subdivisão musical para 192 ticks... se o tick calculado estiver a uma distância menor que `tolerance_ticks = 16` de um ponto de grade válido, mova-o para a grade. Elimine notas duplicadas no mesmo tick com o mesmo pitch (mesclando amplitudes). 2. Escreva testes em tests/test_game_design/test_quantizer.py testando notas levemente atrasadas (ex: 50 ticks -> deve snapar para 48) e notas em tercinas."
   - `SCOPE.md` (Lines 65–70):
     > "`NoteQuantizer` (`src/game_design/quantizer.py`): Input: `notes: list[NoteEvent]`, `tempo_map: TempoMap`. Output: `list[QuantizedNote]` where `QuantizedNote(tick: int, pitch: int, duration_ticks: int, amplitude: float)`. Subdivisions: 192 (1/4), 96 (1/8), 64 (1/12), 48 (1/16), 32 (1/24), 24 (1/32). Tolerance: `tolerance_ticks: int = 16`. Deduplication: identical `(tick, pitch)` -> merged with `max(amplitude)` and `max(duration_ticks)`."
   - `src/models/tempo.py` (Lines 64–116): Provides methods `tick_to_seconds(tick: int) -> float` and `seconds_to_tick(seconds: float) -> int` handling dynamic piecewise BPM calculations.
   - `src/models/midi_events.py` (Lines 6–26): `NoteEvent(start_time, end_time, pitch, amplitude)`.

---

## 2. Logic Chain

1. **Subdivision and Tolerance Math**:
   - From Obs 2, the grid subdivisions are multiples of $[192, 96, 64, 48, 32, 24]$.
   - For an arbitrary tick $t$, the candidate grid points are $k \cdot s$ for $s \in S$. The minimum distance $d^* = \min_{s, k} |k \cdot s - t|$.
   - When $d^* \le 16$, the note snaps to the nearest candidate point $k^* \cdot s$.
   - When $d^* > 16$ (e.g. against quarter note grid or 1/16 grid at midpoint, or with custom tolerance like `tolerance_ticks=8`), the note is unsnapped and remains at $t$.
2. **Deduplication Constraints**:
   - Multiple note events with identical `(tick, pitch)` occur from basic-pitch transcription jitter.
   - Per Obs 2 (`SCOPE.md:70`), duplicate `(tick, pitch)` pairs must merge into a single `QuantizedNote` taking `max(amplitude)` and `max(duration_ticks)`.
   - Distinct pitches occurring at the same `tick` represent chords and must NOT be deduplicated; both notes must be preserved.
   - The same pitch at different `tick`s represents consecutive distinct notes and must be preserved.
3. **Multi-Tempo Synchronization**:
   - Notes occurring after a BPM change boundary must be converted to ticks via `tempo_map.seconds_to_tick()`.
   - Per Obs 2 (`src/models/tempo.py`), `seconds_to_tick` already handles cumulative segment integration, which `NoteQuantizer` must utilize.
4. **Test Suite Completeness**:
   - To guarantee complete coverage without regression, 16 distinct test functions were authored in `spec_report.md`:
     - 6 subdivision snapping tests (1/4, 1/8, 1/12, 1/16, 1/24, 1/32)
     - 2 tolerance boundary tests ($\le 16$ snaps, $> 16$ unsnapped, custom tolerance)
     - 2 deduplication tests (identical merge, chord retention)
     - 2 list handling tests (empty input, chronological sorting)
     - 1 multi-tempo map test (120 -> 140 BPM)
     - 2 model & class validation tests (`QuantizedNote`, `NoteQuantizer`)
   - All tests conform strictly to `pyproject.toml` (type annotations, ruff formatting, pytest idioms).

---

## 3. Caveats

1. The quantizer module `src/game_design/quantizer.py` is not yet implemented (scheduled for the developer subagent in M1). The authored test suite in `spec_report.md` will become runnable once `src/game_design/quantizer.py` and `tests/test_game_design/test_quantizer.py` are created.
2. If `subdivisions` contains both 24 and 32 simultaneously, the maximum distance between any integer and the nearest subdivision multiple is at most 12 ticks. Thus, boundary testing for unsnapped notes ($> 16$ ticks) must be validated against restricted subdivision sets (e.g., `subdivisions=[192]` or `[48]`) or tighter tolerances (e.g., `tolerance_ticks=8`). This is fully addressed in test cases 8 and 9.

---

## 4. Conclusion

The specification mining for Milestone 1 is complete. All behavioral rules, mathematical equations, data structures, and edge cases are documented in `.agents/teamwork/spec_miner_m1/spec_report.md`. The concrete test plan and full recommended source code for `tests/test_game_design/test_quantizer.py` are authored and ready for immediate deployment by the developer agent.

---

## 5. Verification Method

To verify this specification report and future implementation:
1. **Inspect Artifacts**:
   - `.agents/teamwork/spec_miner_m1/spec_report.md`
   - `.agents/teamwork/spec_miner_m1/handoff.md`
2. **Post-Implementation Test Execution**:
   ```bash
   .venv/bin/pytest tests/test_game_design/test_quantizer.py
   .venv/bin/mypy src/game_design tests/test_game_design
   .venv/bin/ruff check src/game_design tests/test_game_design
   .venv/bin/pytest tests/
   ```
3. **Invalidation Conditions**:
   - Any failure of the 16 test cases to run or pass once `src/game_design/quantizer.py` is implemented.
   - Any typing violation under strict mypy or linting violation under ruff.
