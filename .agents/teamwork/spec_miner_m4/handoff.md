# Handoff Report: Milestone 4 Game Design Specification (HopoEngine, SustainProcessor, StarPowerGenerator)

**Agent**: `spec_miner_m4`  
**Date**: 2026-10-13  
**Status**: Task Complete (Hard Handoff)  
**Deliverable**: `/home/adiel/Projects/music2chart/.agents/teamwork/spec_miner_m4/spec_report.md`

---

## 1. Observation

1. **System & Working Environment**:
   - Repository: `/home/adiel/Projects/music2chart`
   - Python environment: Python 3.12 under `.venv` at `/home/adiel/Projects/music2chart/.venv/bin/python`.
   - Active tools: `.venv/bin/pytest`, `.venv/bin/mypy`, `.venv/bin/ruff`.
   - Existing test status: Running `.venv/bin/pytest tests/test_game_design/` returned `94 passed in 0.12s`.
   - Existing lint/type status: Running `.venv/bin/mypy src/game_design tests/test_game_design` returned `Success: no issues found in 8 source files`. Running `.venv/bin/ruff check src/game_design tests/test_game_design` returned `All checks passed!`.

2. **Core Domain Models (`src/models/chart.py`)**:
   - Lines 7–18: `FretType` defines `GREEN = 0`, `RED = 1`, `YELLOW = 2`, `BLUE = 3`, `ORANGE = 4`, `HOPO_FORCE = 5`, `STRUM_FORCE = 6`, `OPEN = 7`.
   - Lines 20–43: `ChartNote` defines `tick: int`, `fret: FretType`, `sustain_length: int = 0`, `is_hopo: bool = False`. `__lt__` sorts primarily by `tick` and secondarily by `fret`.
   - Lines 45–57: `StarPowerPhrase` defines `tick: int`, `length: int`.
   - Lines 59–79: `SongTrack` defines `name: str`, `notes: list[ChartNote]`, `star_power: list[StarPowerPhrase]`.

3. **Authoritative Requirements**:
   - `AGENTS.md` §7.4: "O motor de Clone Hero ativa HOPO nativo se a distância entre notas consecutivas for menor ou igual a 65 ticks (aprox. semicolcheia em andamento moderado) E houver variação de traste. Se uma nota for repetida no mesmo traste (ex: Verde seguido de Verde), ela deve ser tocada com palheta (Strum)."
   - `AGENTS.md` §7.5: "Notas curtas (duração inferior a 90 ticks) devem ter sustain_length = 0 (notas de impacto imediato). Notas sustentadas devem ter seu comprimento calculado subtraindo uma margem de liberação de 24 ticks antes da próxima nota."
   - `ORIGINAL_REQUEST.md` R4: "Automatic Hammer-On / Pull-Off detection (intervals <= 65 ticks with fret variation, forcing strums on repeated frets) and sustain length calculation cutting a 24-tick release margin prior to consecutive notes."
   - `PROMPTS.md` Prompt 4.4:
     - `HopoEngine`: Evaluate notes chronologically; $\Delta \le 65$ and different fret $\implies$ HOPO; identical fret $\implies$ forced Strum.
     - `SustainProcessor`: If duration $< 90$, `sustain_length = 0`; if $\ge 90$, `sustain_length = duration - 24`; clamp so sustain does not exceed next note tick minus 24 ticks.
     - `StarPowerGenerator`: Allocate `StarPowerPhrase` every ~16 to 32 measures in active continuous sections.
   - `SCOPE.md` lines 85–94: Public interface contracts and signatures for `HopoEngine`, `SustainProcessor`, and `StarPowerGenerator`.

---

## 2. Logic Chain

1. **HopoEngine Logic**:
   - From Observation 3 (`AGENTS.md` §7.4 and `PROMPTS.md` 4.4), natural HOPO is only triggered when interval between consecutive notes is $\le 65$ ticks and the fret changes.
   - Therefore, notes separated by $> 65$ ticks (such as 66, 96, 192 ticks) are strums (`is_hopo=False`).
   - The first note of a track has no preceding note; by guitar mechanics and Clone Hero standards, it must be strummed (`is_hopo=False`).
   - Repeated frets (e.g. Green followed by Green at 48 ticks) must be strummed (`is_hopo=False`).
   - Open notes (7) can hammer-on from or pull-off to fretted notes (0-4), but consecutive Open notes within $\le 65$ ticks must be strummed.
   - Chords: Simultaneous notes at the same tick require a strum; transitioning into a chord requires a strum; transitioning from a chord to a single note is a HOPO only if the single note is a new fret not held in the chord.

2. **SustainProcessor Logic**:
   - From Observation 3 (`AGENTS.md` §7.5), durations $< 90$ ticks are impact strums, requiring `sustain_length = 0`.
   - Sustained notes ($\ge 90$ ticks) have nominal sustain $S_{\text{nom}} = \text{duration} - 24$.
   - When a note at $t_1$ is followed by a note at $t_2$, the sustain tail cannot collide with the next note. A release margin of 24 ticks must precede $t_2$. Thus $S \le \max(0, t_2 - t_1 - 24)$.
   - Clamping rule: $S = \min(S_{\text{nom}}, \max(0, t_2 - t_1 - 24))$.
   - If spacing $t_2 - t_1 \le 24$ ticks, sustain clamps to 0.
   - If there is no subsequent note in the track (terminal note), no collision clamping occurs; $S = \text{duration} - 24$.
   - Notes in the same chord (identical tick) sustain concurrently and do not clamp each other.

3. **StarPowerGenerator Logic**:
   - From Observation 3 (`AGENTS.md` §4.2 and `PROMPTS.md` 4.4), Star Power phrases are rewarded for playing continuous dense sections.
   - 1 beat = 192 PPQ; 1 measure (4/4) = 768 ticks. 16 measures = 12,288 ticks.
   - Phrases must strictly fall within active note regions (no phrases during silent passages).
   - Songs that are empty or have fewer than `min_notes` produce empty `StarPowerPhrase` lists.
   - Phrases must not overlap: $\text{phrase}_k.\text{tick} + \text{phrase}_k.\text{length} \le \text{phrase}_{k+1}.\text{tick}$.

4. **Test Suite Design Logic**:
   - By structuring tests into 4 distinct groups (`TestHopoEngine`, `TestSustainProcessor`, `TestStarPowerGenerator`, and `test_game_design_end_to_end_pipeline`), every individual rule, boundary condition, and pipeline dependency is thoroughly isolated and validated.

---

## 3. Caveats

1. **Chord HOPO Modifiers**: In custom Clone Hero charts, specialized modifiers (such as N 5 0 for Chord HOPO) exist. Standard Clone Hero game design defaults to chord strumming unless explicitly forced. The specification enforces standard Clone Hero chord strumming (`is_hopo=False` on chords).
2. **Tempo Signatures in Star Power**: In charts with irregular time signatures (e.g. 3/4 or 6/8), measure duration in ticks differs from $768$. `StarPowerGenerator` accepts configurable `measure_ticks` (defaulting to 768 for standard 4/4).

---

## 4. Conclusion

1. The authoritative specifications for Milestone 4 components (`HopoEngine`, `SustainProcessor`, and `StarPowerGenerator`) are fully mapped and detailed in `/home/adiel/Projects/music2chart/.agents/teamwork/spec_miner_m4/spec_report.md`.
2. A complete, runnable pytest test suite containing 38 granular test cases plus an end-to-end game design integration test is fully specified and documented in `spec_report.md`.
3. The test suite strictly conforms to `mypy` strict type checking, `ruff` formatting, and existing codebase conventions.
4. Downstream agents (`test_writer_m4` and `coder_m4`) can directly utilize the interface contracts and test implementations from `spec_report.md`.

---

## 5. Verification Method

To verify the test suite once placed in `tests/test_game_design/test_hopo_engine.py`:

```bash
# 1. Execute the new Milestone 4 test suite:
.venv/bin/pytest tests/test_game_design/test_hopo_engine.py -v

# 2. Execute full game design regression:
.venv/bin/pytest tests/test_game_design/ -v

# 3. Verify static typing:
.venv/bin/mypy src/game_design tests/test_game_design

# 4. Verify formatting and linting:
.venv/bin/ruff check src/game_design tests/test_game_design
.venv/bin/ruff format --check src/game_design tests/test_game_design
```

**Invalidation Conditions**:
- If `HopoEngine` marks repeated frets $\le 65$ ticks as HOPO.
- If `SustainProcessor` fails to clamp notes with next-note spacing $\le 24$ ticks to 0.
- If `StarPowerGenerator` generates overlapping phrases or phrases in silent gaps.
