# Review & Challenge Report — Milestone 3: ChordBuilder

**Subagent**: `reviewer_m3_1`  
**Roles**: Reviewer, Adversarial Critic  
**Working Directory**: `/home/adiel/Projects/music2chart/.agents/teamwork/reviewer_m3_1`  
**Date**: 2026-10-13  
**Target Recipient**: Orchestrator (`parent`: `c32a8c2d-046d-4e36-96ca-60cf3fc9e81f`)

---

## Review Summary

**Verdict**: **`APPROVE`**

The implementation of `ChordBuilder` in `src/game_design/chord_builder.py`, its export in `src/game_design/__init__.py`, and the accompanying test suite in `tests/test_game_design/test_chord_builder.py` fully satisfy all functional requirements, game design specifications, and quality standards. No integrity violations, code style defects, or regressions were detected.

---

## 1. Observation

### 1.1 Reviewed Artifacts
- `src/game_design/chord_builder.py` (270 lines):
  - Defines `ChordBuilder` with configurable `max_frets` (1–5, default 3), `allow_wide_triads` (default False), and `open_note_precedence` (default True, with alias `prefer_open`).
  - Constants: `CANONICAL_POWER_CHORDS` (7 dyads) and `CANONICAL_TRIADS` (4 triads).
  - Internal reduction helpers: `_clamp_dyad`, `_clamp_triad`, `_simplify_polyphonic`, `_reduce_cluster`.
  - Main transformation: `build_chords(notes: Sequence[ChartNote]) -> list[ChartNote]` with convenience aliases `build`, `process`, and `__call__`.
- `src/game_design/__init__.py` (13 lines):
  - Cleanly exports `ChordBuilder` alongside `NoteQuantizer`, `PitchToFretMapper`, and `QuantizedNote`.
- `tests/test_game_design/test_chord_builder.py` (612 lines):
  - 35 test functions expanding to 54 parameterized test cases covering tick grouping, sorting, deduplication, canonical power chords and triads, cluster simplification, stretch elimination, open note exclusivity, edge cases, and high-volume stress testing.

### 1.2 Independent Verification Tool Execution Results

All commands executed using `.venv` within sandbox constraints:

#### Command 1: Pytest on `test_chord_builder.py`
Command: `.venv/bin/pytest tests/test_game_design/test_chord_builder.py -v`
```text
============================= test session starts ==============================
platform linux -- Python 3.12.14, pytest-9.1.1, pluggy-1.6.0
cachedir: /tmp/.pytest_cache
rootdir: /home/adiel/Projects/music2chart
configfile: pyproject.toml
plugins: asyncio-1.4.0, anyio-4.15.1, platformdirs-4.13.0
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 54 items

tests/test_game_design/test_chord_builder.py ........................... [ 50%]
...........................                                              [100%]

============================== 54 passed in 0.09s ==============================
```

#### Command 2: Full Project Pytest Suite (Regression Check)
Command: `.venv/bin/pytest tests/`
```text
........................................................................ [ 47%]
........................................................................ [ 95%]
.......                                                                  [100%]
151 passed in 2.01s
```

#### Command 3: Mypy Strict Type Checking
Command: `.venv/bin/mypy src/game_design tests/test_game_design`
```text
Success: no issues found in 8 source files
```

#### Command 4: Ruff Linting
Command: `.venv/bin/ruff check src/game_design tests/test_game_design`
```text
All checks passed!
```

#### Command 5: Ruff Formatting Check
Command: `.venv/bin/ruff format --check src/game_design tests/test_game_design`
```text
8 files already formatted
```

---

## 2. Logic Chain

1. **Integrity Audit**:
   - Inspected `src/game_design/chord_builder.py` and `tests/test_game_design/test_chord_builder.py`.
   - Verified that no hardcoded test outputs or mock shortcuts are present.
   - Algorithms implement actual set-based and distance-based clamping (`high - low > 2 -> high = low + 2`), exhaustive mapping of 4- and 5-note combinations to canonical triads, Open note conflict resolution, and attribute preservation.
   - Independent verification via `.venv/bin/pytest` confirmed genuine execution of all 54 chord builder tests and all 151 repository tests.
   - Verdict: **PASS (Zero integrity violations).**

2. **Core Correctness Verification**:
   - **Simultaneous Grouping**: Notes are grouped by identical `note.tick` via `defaultdict(list)`.
   - **Cluster Size Limit**: 4-note and 5-note clusters are reduced to $\le 3$ frets via `_simplify_polyphonic`. If `max_frets < 3`, `_reduce_cluster` further reduces to $\le \text{max\_frets}$.
   - **Canonical Preservations**:
     - All 7 canonical power chords (`(0, 1), (0, 2), (1, 2), (1, 3), (2, 3), (2, 4), (3, 4)`) have span $\le 2$ and pass through `_clamp_dyad` unchanged.
     - All 4 canonical triads (`(0, 1, 2), (0, 2, 3), (1, 2, 3), (2, 3, 4)`) are membership-tested in `CANONICAL_TRIADS` and pass through `_clamp_triad` unchanged.
   - **Stretch Elimination**:
     - Dyads with span $> 2$ are clamped (`(0, 4) -> (0, 2)`, `(0, 3) -> (0, 2)`, `(1, 4) -> (1, 3)`).
     - Triads containing both 0 and 4 are clamped: `(0, 1, 4) -> (0, 1, 2)`, `(0, 3, 4) -> (2, 3, 4)`, and `(0, 2, 4) -> (0, 2, 3)` (or `(0, 2, 4)` if `allow_wide_triads=True`).
   - **Open Note Exclusivity**:
     - When Open notes (7) and fretted notes (0–4) occur at the same tick, `open_note_precedence=True` emits a single Open note with `max(sustain_length)` and drops fretted notes. When `False`, the Open note is dropped. Open notes and fretted notes never coexist at the same tick.

3. **Invariants Verification**:
   - **Single Notes**: Monophonic notes (frets 0–4 or 7) pass through unmodified.
   - **Deduplication**: Duplicate frets at the same tick are deduplicated into a single note taking `max(sustain_length)` and `any(is_hopo)`. Multiple Open notes at the same tick are merged into one Open note with `max(sustain_length)`.
   - **Sorting**: `result.sort()` sorts using `ChartNote.__lt__`, ensuring strict ascending order by `tick`, then by `fret`.

4. **Adversarial Stress Testing**:
   - Tested generator and tuple inputs: cleanly handled.
   - Tested input immutability: input notes are not modified in-place; new `ChartNote` instances are constructed.
   - Tested high-volume 1000-note stress pipeline: executed cleanly with all invariants preserved in $< 0.1\text{s}$.
   - Tested invalid `max_frets` (0, -1, 6): correctly raises `ValueError`.

---

## 3. Caveats

- **No caveats.** The implementation meets or exceeds all criteria defined in `AGENTS.md` (§7.3), `SCOPE.md`, `PROJECT.md`, and `ORIGINAL_REQUEST.md`.

---

## 4. Conclusion

- Milestone 3 is complete and robust.
- The `ChordBuilder` component is thoroughly verified, conforms to the pipeline contract, and is ready for integration with Milestone 4 (`HopoEngine`, `SustainProcessor`, and `StarPowerGenerator`).
- **Verdict**: **`APPROVE`**.

---

## 5. Verification Method

To independently reproduce and verify this review:

```bash
# 1. Run unit tests for ChordBuilder (54 tests)
.venv/bin/pytest tests/test_game_design/test_chord_builder.py -v

# 2. Run full regression test suite (151 tests)
.venv/bin/pytest tests/

# 3. Check strict types
.venv/bin/mypy src/game_design tests/test_game_design

# 4. Check formatting and linting
.venv/bin/ruff check src/game_design tests/test_game_design
.venv/bin/ruff format --check src/game_design tests/test_game_design
```

Invalidation conditions:
- Any failure in `pytest tests/test_game_design/test_chord_builder.py` or `pytest tests/`.
- Any output note containing `{0, 4}` simultaneously or Open note (7) coexisting with fretted notes (0–4).
- Any mypy or ruff errors.
