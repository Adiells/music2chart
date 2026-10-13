# Handoff Report — Milestone 3 Empirical Challenger 2: ChordBuilder Invariants

**Agent**: `challenger_m3_2`  
**Milestone**: Phase 4 — Milestone 3  
**Date**: 2026-10-13  
**Recipient**: Orchestrator (`parent`), QA / Auditor  
**Verdict**: **APPROVE**

---

## 1. Observation

### 1.1 Evaluated Scope
Implementation evaluated: `src/game_design/chord_builder.py` (270 lines) and corresponding tests `tests/test_game_design/test_chord_builder.py` (612 lines).

### 1.2 Verification Harness
An adversarial property oracle harness was authored and executed in:
`/home/adiel/Projects/music2chart/.agents/teamwork/challenger_m3_2/oracle_test.py`

The harness executes 7 test suites:
1. **Suite 1: Combinatorial Power Set**: All $2^6 = 64$ subsets of playable frets $\{0, 1, 2, 3, 4, 7\}$ at a single tick.
2. **Suite 2: Config Matrix Permutations**: 1,260 combinations of `max_frets` $\in [1..5]$, `allow_wide_triads` $\in [\text{False, True}]$, `open_note_precedence` $\in [\text{False, True}]$ across all fret combinations.
3. **Suite 3: Canonical Power Chords 100% Invariant**: 1,344 cases covering all 7 canonical power chords $\{(0, 1), (0, 2), (1, 2), (1, 3), (2, 3), (2, 4), (3, 4)\}$ across multiple ticks, sustains, hopo flags, and reversed fret input orderings.
4. **Suite 4: Canonical Triads 100% Invariant**: 288 cases covering all 4 canonical triads $\{(0, 1, 2), (0, 2, 3), (1, 2, 3), (2, 3, 4)\}$ across all 6 input permutations and various sustain lengths.
5. **Suite 5: Stretch Clamping & Ergonomic Reduction**: 30 cases covering dyad clamping, triad clamping, polyphonic clusters up to 5 frets, and isolated $\{0, 4\}$ prevention.
6. **Suite 6: Property-Based Randomized Fuzzing**: 10,000 randomized note sequences with arbitrary ticks, clusters of 1 to 15 notes, random sustains, and shuffled inputs.
7. **Suite 7: Deduplication, Max Sustain & Boundary Stress**: 4 stress tests including 100 duplicate notes, 50 duplicate open notes, empty inputs, and 100-step alternating sequences.

### 1.3 Verbatim Command Execution Outputs

#### Command 1: Property Oracle Harness Execution
Command: `.venv/bin/python .agents/teamwork/challenger_m3_2/oracle_test.py`
```text
======================================================================
CHORDBUILDER EMPIRICAL ORACLE & PROPERTY INVARIANT HARNESS
======================================================================

--- Running Suite 1: Full Combinatorial Power Set (64 subsets) ---
Suite 1 Complete: 64 passed, 0 failed out of 64 power-set cases.

--- Running Suite 2: Config Matrix Permutations ---
Suite 2 Complete: 1260 passed, 0 failed out of 1260 config combinations.

--- Running Suite 3: Canonical Power Chords 100% Invariant ---
Suite 3 Complete: 1344 passed, 0 failed (100% invariant verified).

--- Running Suite 4: Canonical Triads 100% Invariant ---
Suite 4 Complete: 288 passed, 0 failed (100% invariant verified).

--- Running Suite 5: Stretch Clamping & Ergonomic Reduction ---
Suite 5 Complete: 30 passed, 0 failed.

--- Running Suite 6: Property-Based Randomized Fuzzing (10000 cases) ---
Suite 6 Complete: 10000 passed, 0 failed in 0.91s (11047.7 trials/s).

--- Running Suite 7: Deduplication, Max Sustain & Boundary Stress ---
Suite 7 Complete: 4 passed, 0 failed.

======================================================================
FINAL ORACLE HARNESS RESULTS: 12990 PASSED, 0 FAILED in 0.92s
======================================================================

ALL ERGONOMIC INVARIANTS EMPIRICALLY CONFIRMED AND VERIFIED: APPROVE
```

#### Command 2: Unit Test Suite
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

============================== 54 passed in 0.10s ==============================
```

#### Command 3: Full Project Regression Suite
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

........................................................................ [ 47%]
........................................................................ [ 95%]
.......                                                                  [100%]

============================= 151 passed in 1.92s ==============================
```

#### Command 4: Strict Type Checking and Linting
Command: `.venv/bin/mypy src/game_design tests/test_game_design`
```text
Success: no issues found in 8 source files
```

Command: `.venv/bin/ruff check src tests && .venv/bin/ruff format --check src tests`
```text
All checks passed!
37 files already formatted
```

---

## 2. Logic Chain

1. **Premise 1 — Constraint `len(frets_at_tick) <= 3`**:
   - As observed in §1.3 (Suites 1, 2, 5, 6), across all 64 single-tick fret subsets and 10,000 randomized fuzz trials with up to 15 notes per tick, the output length of playable frets at any tick never exceeds `builder.max_frets` (default 3). In `src/game_design/chord_builder.py` lines 140–161, `_reduce_cluster` guarantees that clusters $\ge 4$ frets are simplified to canonical triads of length 3, and lines 152–160 further clamp to `max_frets` when `max_frets < 3`.

2. **Premise 2 — Prevention of Isolated `{0, 4}`**:
   - As observed in §1.3 (Suites 1, 3, 5, 6), in no trial was the isolated dyad `{0, 4}` emitted. In `src/game_design/chord_builder.py` lines 80–90, `_clamp_dyad` checks `if high - low > 2: return [low, low + 2]`, turning `[0, 4]` deterministically into `[0, 2]`. For 3-fret triads containing `{0, 4}`, `_clamp_triad` (lines 92–119) maps `(0, 1, 4) -> (0, 1, 2)`, `(0, 3, 4) -> (2, 3, 4)`, and `(0, 2, 4) -> (0, 2, 3)` (unless `allow_wide_triads=True`, in which case yellow fret 2 is present, so `{0, 4}` is never isolated).

3. **Premise 3 — Open Note Exclusivity**:
   - As observed in §1.3 (Suites 1, 2, 6, 7), if `FretType.OPEN` (7) appears at tick $t$, exactly one Open note is emitted and no frets in $\{0, 1, 2, 3, 4\}$ ever coexist with it. In `src/game_design/chord_builder.py` lines 193–218, open notes and fretted notes are segregated into separate collections. When both are present, `self.open_note_precedence` determines whether only a single merged Open note is emitted or only fretted notes proceed.

4. **Premise 4 — Canonical Power Chords 100% Invariance**:
   - As observed in §1.3 (Suite 3: 1,344 cases), all 7 canonical power chords `(0, 1), (0, 2), (1, 2), (1, 3), (2, 3), (2, 4), (3, 4)` pass through `ChordBuilder` with 100.0% fidelity. Fret values, ticks, individual sustain lengths, and hopo flags remain completely unchanged, even when the input list is presented in inverted fret order.

5. **Premise 5 — Canonical Triads 100% Invariance**:
   - As observed in §1.3 (Suite 4: 288 cases), all 4 canonical triads `(0, 1, 2), (0, 2, 3), (1, 2, 3), (2, 3, 4)` pass through with 100.0% fidelity across all 6 order permutations, maintaining per-fret sustain lengths and ascending sort order.

---

## 3. Caveats

- **No caveats.** The property oracle tested all mathematically possible combinations ($2^6 = 64$) for single-tick inputs, full parameter permutations, and 10,000 multi-tick randomized fuzz runs without a single failure or regression.

---

## 4. Conclusion

- **Verdict: APPROVE**
- `ChordBuilder` fully satisfies all game design rules, Clone Hero physical ergonomic constraints, and property invariants:
  1. `len(frets_at_tick) <= 3` (or `max_frets`) holds under all conditions.
  2. Isolated `{0, 4}` is never emitted.
  3. Open Note (7) exclusivity is strictly enforced.
  4. All canonical power chords and canonical triads are 100% invariant.
  5. Deterministic sorting and duplicate note merging operate correctly.

---

## 5. Verification Method

To independently reproduce and verify this challenger assessment:

```bash
# 1. Run the empirical oracle and property-based test harness (12,990 tests)
.venv/bin/python .agents/teamwork/challenger_m3_2/oracle_test.py

# 2. Run unit tests
.venv/bin/pytest tests/test_game_design/test_chord_builder.py -v

# 3. Run full regression test suite
.venv/bin/pytest tests/

# 4. Run mypy and ruff checks
.venv/bin/mypy src/game_design tests/test_game_design
.venv/bin/ruff check src tests
.venv/bin/ruff format --check src tests
```

Invalidation conditions:
- Any failure in `oracle_test.py`.
- Any output note containing `{0, 4}` isolated at any tick.
- Any output tick containing both Open Note (7) and fretted notes (0–4).
