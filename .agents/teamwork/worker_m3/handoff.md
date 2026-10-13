# Handoff Report — Milestone 3: Chord Formation & Playability Constraints Engine (`ChordBuilder`)

**Agent**: `worker_m3`  
**Milestone**: Phase 4 — Milestone 3  
**Date**: 2026-10-13  
**Target Recipient**: Orchestrator (`parent`), QA / Auditor (`teamwork_preview_auditor`)

---

## 1. Observation

### 1.1 Context and Requirements
From `ORIGINAL_REQUEST.md` (§R3) and `DISPATCH.md`:
- Group simultaneous notes at identical ticks into chords $\le 3$ frets.
- Enforce Open Note exclusivity (Open Note 7 never coexists with frets 0–4 at the same tick).
- Preserve canonical power chords: `(0, 1), (0, 2), (1, 2), (1, 3), (2, 3), (2, 4), (3, 4)`.
- Preserve canonical triads: `(0, 1, 2), (0, 2, 3), (1, 2, 3), (2, 3, 4)`.
- Eliminate forbidden stretches:
  - Isolated `(0, 4)` dyad simplified to `(0, 2)`.
  - Generalized dyad clamping: `if high - low > 2: high = low + 2`.
  - Triad stretch clamping: `(0, 1, 4) -> (0, 1, 2)`, `(0, 3, 4) -> (2, 3, 4)`, and `(0, 2, 4) -> (0, 2, 3)` unless `allow_wide_triads=True`.
- Deduplicate duplicate frets at the same tick, merging sustain to `max(sustain_length)` and preserving `is_hopo`.
- Strictly sort outputs by `(tick, fret)` ascending.
- Export `ChordBuilder` in `src/game_design/__init__.py`.
- Implement unit tests covering all 30 specification cases from `spec_miner_m3/spec_report.md`.

### 1.2 Implemented Files
1. `src/game_design/chord_builder.py` (228 lines):
   - Implemented `ChordBuilder` class with `max_frets`, `allow_wide_triads`, `open_note_precedence`, and `prefer_open` parameters.
   - Implemented `CANONICAL_POWER_CHORDS` and `CANONICAL_TRIADS` frozenset constants.
   - Implemented helper methods `_clamp_dyad`, `_clamp_triad`, `_simplify_polyphonic`, and `_reduce_cluster`.
   - Implemented primary method `build_chords` and aliases `build`, `process`, and `__call__`.
2. `src/game_design/__init__.py` (13 lines):
   - Exported `ChordBuilder` alongside `NoteQuantizer`, `PitchToFretMapper`, and `QuantizedNote`.
3. `tests/test_game_design/test_chord_builder.py` (377 lines):
   - Implemented 35 test functions expanding to 54 test executions with pytest parameterization covering all 30 spec cases from `spec_miner_m3` and edge cases from `explorer_m3_2`.

### 1.3 Verbatim Tool Command Outputs

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

============================== 54 passed in 0.08s ==============================
```

#### Command 2: Pytest on full test suite
Command: `.venv/bin/pytest tests/`
```text
============================= test session starts ==============================
platform linux -- Python 3.12.14, pytest-9.1.1, pluggy-1.6.0
cachedir: /tmp/.pytest_cache
rootdir: /home/adiel/Projects/music2chart
configfile: pyproject.toml
plugins: asyncio-1.4.0, anyio-4.15.1, platformdirs-4.13.0
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 151 items

tests/test_audio_processing/test_harmonic_filter.py ..............       [  9%]
tests/test_audio_processing/test_pitch_transcriber.py ...........        [ 16%]
tests/test_audio_processing/test_tempo_tracker.py .                      [ 17%]
tests/test_game_design/test_chord_builder.py ........................... [ 35%]
...........................                                              [ 52%]
tests/test_game_design/test_pitch_to_fret.py ......................      [ 67%]
tests/test_game_design/test_quantizer.py ..................              [ 79%]
tests/test_serialization/test_chart_writer.py .................          [ 90%]
tests/test_serialization/test_sng_packer.py ..............               [100%]

============================= 151 passed in 1.91s ==============================
```

#### Command 3: Mypy Strict Type Checking
Command: `.venv/bin/mypy src/game_design tests/test_game_design`
```text
Success: no issues found in 8 source files
```

Command: `.venv/bin/mypy src tests`
```text
Success: no issues found in 37 source files
```

#### Command 4: Ruff Linting and Formatting
Command: `.venv/bin/ruff check src tests && .venv/bin/ruff format --check src tests`
```text
All checks passed!
37 files already formatted
```

---

## 2. Logic Chain

1. **Step 1: Tick Grouping**:
   - As observed in §1.1, Clone Hero chords occur at the identical `tick`. `ChordBuilder.build_chords` indexes input notes into `tick_map: dict[int, list[ChartNote]] = defaultdict(list)` using `note.tick`.

2. **Step 2: Open Note Exclusivity Handling**:
   - In accordance with R3.4 and §1.1, if a tick contains both Open notes (`FretType.OPEN = 7`) and fretted notes (`0..4`), `self.open_note_precedence` determines the behavior. When `True` (default), all fretted notes at that tick are dropped, and a single Open note is emitted with `max(sustain_length)` across the cluster. When `False`, the Open note is dropped, allowing fretted notes to proceed. If only Open notes are present at that tick, duplicate Open notes are merged taking `max(sustain_length)`.

3. **Step 3: Monophonic Passthrough and Deduplication**:
   - Single fretted notes pass through untouched. Duplicate frets at the same tick are deduplicated via `sustain_by_fret[fv] = max(existing, note.sustain_length)` and `hopo_by_fret[fv] = existing or note.is_hopo`. If deduplication leaves a single unique fret, it is emitted directly without modification.

4. **Step 4: Polyphonic Cluster Simplification**:
   - When a tick contains 4 or 5 frets, `_simplify_polyphonic` maps them deterministically to canonical triads:
     - `(0, 1, 2, 3, 4) -> (0, 1, 2)`
     - `(0, 1, 2, 3) -> (0, 1, 2)`
     - `(0, 1, 2, 4) -> (0, 1, 2)`
     - `(0, 1, 3, 4) -> (0, 1, 2)`
     - `(0, 2, 3, 4) -> (0, 2, 3)`
     - `(1, 2, 3, 4) -> (1, 2, 3)`
   - This eliminates all 4- and 5-fret clusters and all `(0, 4)` stretches while preserving harmonic anchors.

5. **Step 5: Forbidden Stretch Clamping**:
   - Dyad clamping: For any 2-note dyad `(low, high)`, if `high - low > 2`, `high` is clamped to `low + 2`. This transforms `(0, 4) -> (0, 2)`, `(0, 3) -> (0, 2)`, and `(1, 4) -> (1, 3)`. All 7 canonical power chords satisfy `span <= 2` and remain intact.
   - Triad clamping: For 3-note chords containing both 0 and 4:
     - `(0, 1, 4) -> (0, 1, 2)`
     - `(0, 3, 4) -> (2, 3, 4)`
     - `(0, 2, 4) -> (0, 2, 4)` if `allow_wide_triads=True`, else `(0, 2, 3)`.
   - If `self.max_frets < len(frets)` (e.g. `max_frets=2`), triads are reduced to the nearest root-anchored power chord `(low, low + 1)` or `(low, low + 2)`.

6. **Step 6: Output Reconstruction & Sorting**:
   - For each selected fret, `ChartNote` is instantiated with its corresponding or inherited sustain length and hopo flag.
   - Finally, `result.sort()` sorts notes primarily by `tick` ascending and secondarily by `fret` ascending (via `ChartNote.__lt__`), guaranteeing strict `.chart` formatting.

---

## 3. Caveats

- **No caveats.** The implementation addresses all requirements from `AGENTS.md`, `PROMPTS.md`, `ORIGINAL_REQUEST.md`, `SCOPE.md`, and `DISPATCH.md`. All 151 tests in the repository pass with zero errors, zero type issues, and zero lint warnings.

---

## 4. Conclusion

- `ChordBuilder` has been fully implemented in `src/game_design/chord_builder.py` with genuine, ergonomic game design logic.
- `src/game_design/__init__.py` properly exports `ChordBuilder`.
- `tests/test_game_design/test_chord_builder.py` contains 54 comprehensive unit tests verifying all 30 specification cases and additional edge cases.
- All acceptance criteria for Milestone 3 are satisfied and verified against the complete test suite, strict mypy type checking, and ruff linting.

---

## 5. Verification Method

To independently verify the implementation, run:

```bash
# 1. Run unit tests for ChordBuilder
.venv/bin/pytest tests/test_game_design/test_chord_builder.py -v

# 2. Run full regression test suite
.venv/bin/pytest tests/

# 3. Verify strict type checking
.venv/bin/mypy src/game_design tests/test_game_design

# 4. Verify ruff linting and formatting
.venv/bin/ruff check src/game_design tests/test_game_design
.venv/bin/ruff format --check src/game_design tests/test_game_design
```

Files to inspect:
- `src/game_design/chord_builder.py`
- `src/game_design/__init__.py`
- `tests/test_game_design/test_chord_builder.py`

Invalidation conditions:
- Any test failure in `test_chord_builder.py` or regression failure in `tests/`.
- Any mypy error or ruff lint/format error.
- Any output note containing `{0, 4}` simultaneously or Open note (7) coexisting with frets `0..4`.
