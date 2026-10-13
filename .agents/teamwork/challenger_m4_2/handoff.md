# Handoff Report — Milestone 4 Empirical Challenger 2: Formal Property Invariant Oracle

**Agent**: `challenger_m4_2`  
**Milestone**: Phase 4 — Milestone 4 (HOPO, Strum & Sustain Duration Engine)  
**Date**: 2026-10-13  
**Recipient**: Orchestrator (`parent`), QA / Auditor  
**Verdict**: **APPROVE**

---

## 1. Observation

### 1.1 Evaluated Scope
Implementation files evaluated:
- `src/game_design/hopo_engine.py` (133 lines)
- `src/game_design/sustain_processor.py` (143 lines)
- `src/game_design/star_power_generator.py` (134 lines)
- `tests/test_game_design/test_hopo_engine.py` (449 lines)
- `tests/test_game_design/test_sustain_processor.py` (402 lines)

### 1.2 Verification Harness
An independent formal property verification oracle harness was authored and executed at:
`/home/adiel/Projects/music2chart/.agents/teamwork/challenger_m4_2/oracle_harness.py`

The harness executes 4 rigorous test suites evaluating the required invariants:
1. **Suite 1: HopoEngine Formal Oracle & Invariants** (10,556 tests):
   - `[1.1]` Exact Threshold Boundaries: 360 combinatorial transitions testing $\Delta \in \{1, 24, 32, 48, 64, 65, 66, 67, 96, 192\}$ across all 36 $(f_{prev}, f_{curr})$ fret pairs with $\Delta \le 65$ marked HOPO and $\Delta > 65$ marked Strum.
   - `[1.2]` Combinatorial Chord & Single Transitions: 125 tests covering all 10 two-fret chords $\times$ 5 frets testing that single notes sharing a fret with previous chords are Strums, new frets are HOPOs, and chords following singles or chords are unconditionally Strums.
   - `[1.3]` Custom Hopo Thresholds: 20 tests verifying threshold boundaries for thresholds in $\{0, 1, 10, 48, 65, 96, 192\}$.
   - `[1.4]` Permutation Invariance & Force Modifiers: 51 tests verifying chronological order invariance under random shuffling and generation of `STRUM_FORCE` (6) notes on rapid repeat frets.
   - `[1.5]` Property-Based Randomized Fuzzing: 10,000 randomized note sequences (arbitrary note counts, ticks, sustains, frets) asserting 100% agreement against the formal ground truth oracle predicate.
2. **Suite 2: SustainProcessor Formal Oracle & Invariants** (10,025 tests):
   - `[2.1]` Exact Cutoff & Collision Margin Boundaries: 21 tests verifying $dur < 90 \implies sustain = 0$, $dur \ge 90 \implies sustain = dur - 24$, collision clearance $\Delta_{next} \le 24 \implies sustain = 0$, and collision clamping $\min(dur - 24, \Delta_{next} - 24)$.
   - `[2.2]` Heterogeneous Mappings & Unsorted Inputs: 4 tests verifying `Sequence[int]`, `Mapping[(tick, fret), int]` with `int` and `FretType` keys, and `Mapping[tick, int]` formats with unsorted input orderings.
   - `[2.3]` Property-Based Randomized Fuzzing: 10,000 randomized note sequences verifying sustain non-negativity, exact mathematical oracle agreement, and zero collision tail overlap (`note.tick + sustain <= next_unique_tick - 24`).
3. **Suite 3: StarPowerGenerator Formal Oracle & Invariants** (5,000 trials):
   - `[3.1]` Randomized Track Cadence & Non-Overlap Invariants: 5,000 random song layouts verifying:
     - No overlapping phrases: $p_i.tick + p_i.length \le p_{i+1}.tick$ for all $i$.
     - Minimum note density: $\text{count}(\text{notes in } [p.tick, p.tick + p.length)) \ge min\_notes$.
     - Strictly positive length matching $phrase\_length\_measures \times measure\_ticks$.
     - Non-negative tick coinciding with an actual note onset tick.
     - Empty phrase list when total notes $< min\_notes$.
4. **Suite 4: Adversarial Edge Cases & Parameter Validation** (27 tests):
   - Parameter validation asserting `ValueError` on negative `hopo_threshold`, negative `min_sustain_ticks`, negative `release_margin`, and non-positive `StarPowerGenerator` parameters (`measure_ticks`, `interval_measures`, `phrase_length_measures`, `min_notes`).
   - Graceful handling of empty inputs and single note tracks.
   - Zero-threshold edge cases (`hopo_threshold = 0`, `min_sustain_ticks = 0`).
   - Complete verification of backward-compatible API aliases (`calculate_hopos`, `process_hopos`, `calculate_sustains`, `process_notes`, `generate_phrases`, `generate_star_power`, `__call__`).
   - Extreme tick values ($10,000,000$ ticks).

### 1.3 Verbatim Command Execution Outputs

#### Command 1: Property Oracle Harness Execution
Command: `.venv/bin/python .agents/teamwork/challenger_m4_2/oracle_harness.py`
```text
========================================================================
MILESTONE 4 EMPIRICAL ADVERSARIAL ORACLE HARNESS
========================================================================

--- Running Suite 1: HopoEngine Formal Oracle & Invariants ---
  [1.1] Exact Threshold Boundaries: 360 tests passed.
  [1.2] Combinatorial Chord & Single Transitions: 125 tests passed.
  [1.3] Custom Hopo Thresholds: 20 tests passed.
  [1.4] Permutation Invariance & Force Modifiers: 51 tests passed.
  [1.5] Property-Based Randomized Fuzzing: 10000 trials passed.

--- Running Suite 2: SustainProcessor Formal Oracle & Invariants ---
  [2.1] Exact Cutoff & Collision Margin Boundaries: 21 tests passed.
  [2.2] Heterogeneous Mappings & Unsorted Inputs: 4 tests passed.
  [2.3] Property-Based Randomized Fuzzing: 10000 trials passed.

--- Running Suite 3: StarPowerGenerator Formal Oracle & Invariants ---
  [3.1] Randomized Track Cadence & Non-Overlap Invariants: 5000 trials passed.

--- Running Suite 4: Adversarial Edge Cases & Parameter Validation ---
  [4.1] Edge Cases, Validations & Aliases: 27 tests passed.

========================================================================
FINAL ORACLE HARNESS RESULTS: 25608 PASSED, 0 FAILED in 1.65s
Speed: 15520.9 verifications/second
========================================================================
```

#### Command 2: Game Design Unit Tests
Command: `.venv/bin/pytest tests/test_game_design/ -v`
```text
============================= test session starts ==============================
platform linux -- Python 3.12.14, pytest-9.1.1, pluggy-1.6.0
rootdir: /home/adiel/Projects/music2chart
configfile: pyproject.toml
collected 156 items

tests/test_game_design/test_chord_builder.py ........................... [ 17%]
...........................                                              [ 34%]
tests/test_game_design/test_hopo_engine.py ............................. [ 53%]
.                                                                        [ 53%]
tests/test_game_design/test_pitch_to_fret.py ......................      [ 67%]
tests/test_game_design/test_quantizer.py ..................              [ 79%]
tests/test_game_design/test_sustain_processor.py ....................... [ 94%]
.........                                                                [100%]

============================= 156 passed in 0.17s ==============================
```

#### Command 3: Full Project Regression Suite
Command: `.venv/bin/pytest tests/ -v`
```text
============================= test session starts ==============================
platform linux -- Python 3.12.14, pytest-9.1.1, pluggy-1.6.0
rootdir: /home/adiel/Projects/music2chart
configfile: pyproject.toml
collected 213 items

tests/test_audio_processing/test_harmonic_filter.py .....                [  2%]
tests/test_audio_processing/test_pitch_transcriber.py ...                [  3%]
tests/test_audio_processing/test_separator.py ....                       [  5%]
tests/test_audio_processing/test_tempo_tracker.py .....                  [  7%]
tests/test_config.py ....                                                [  9%]
tests/test_dataset/test_chart_parser.py .....                            [ 12%]
tests/test_dataset/test_chorus_scraper.py .........                      [ 16%]
tests/test_dataset/test_evaluator.py .......                             [ 19%]
tests/test_game_design/test_chord_builder.py ........................... [ 32%]
...........................                                              [ 45%]
tests/test_game_design/test_hopo_engine.py ............................. [ 58%]
.                                                                        [ 59%]
tests/test_game_design/test_pitch_to_fret.py ......................      [ 69%]
tests/test_game_design/test_quantizer.py ..................              [ 77%]
tests/test_game_design/test_sustain_processor.py ....................... [ 88%]
.........                                                                [ 92%]
tests/test_models.py ...............                                     [100%]

============================= 213 passed in 2.00s ==============================
```

#### Command 4: Strict Static Type Checking
Command: `.venv/bin/mypy src/game_design tests/test_game_design`
```text
Success: no issues found in 13 source files
```

#### Command 5: Ruff Quality and Formatting Checks
Command: `.venv/bin/ruff check src/game_design tests/test_game_design && .venv/bin/ruff format --check src/game_design tests/test_game_design`
```text
All checks passed!
13 files already formatted
```

---

## 2. Logic Chain

1. **Adversarial Invariant Verification — HopoEngine**:
   - The required invariant states: `is_hopo is True IF AND ONLY IF (delta <= hopo_threshold AND note is not chord AND previous is not same single fret AND previous chord does not contain current fret AND not first note)`.
   - Verified across exact delta boundaries (65 vs 66 ticks), all 36 single fret combinations, 125 chord-to-single / single-to-chord transitions, and 10,000 property fuzzing iterations. In every trial, output matched the mathematical oracle with 0 discrepancy.
2. **Adversarial Invariant Verification — SustainProcessor**:
   - The required invariant states: `If duration < 90: sustain == 0. If duration >= 90: sustain == min(duration - 24, max(0, next_tick - tick - 24)) (or duration - 24 if terminal)`.
   - Verified across cutoff thresholds (89 -> 0, 90 -> 66), collision margins (delta <= 24 -> 0, delta = 25 -> 1), terminal notes (full duration - 24 preserved), and 10,000 fuzzing trials. In addition, the collision tail non-overlap invariant (`note.tick + sustain <= next_unique_tick - 24`) was directly asserted and passed 100% of trials.
3. **Adversarial Invariant Verification — StarPowerGenerator**:
   - The required invariant states: `No overlapping phrases (p[i].tick + p[i].length <= p[i+1].tick). Each phrase has >= min_notes. Phrase length > 0`.
   - Verified across 5,000 random song layouts with alternating dense passages, sparse passages, and multi-measure silence gaps. In all 5,000 trials, zero phrase overlaps occurred, all phrases encompassed $\ge min\_notes$, all phrase lengths were strictly positive, and all phrase starts aligned with actual note onsets.
4. **Boundary and Defensive Engineering**:
   - Input permutation invariance was verified: unsorted input sequences produce identical, correctly sorted outputs.
   - Parameter validations properly reject negative or non-positive arguments with `ValueError`.
   - Zero regressions across the entire 213-test regression suite.

---

## 3. Caveats

- **No Caveats**: All requested invariants were empirically tested across 25,608 automated trials. No defects, edge case failures, or performance bottlenecks were detected.

---

## 4. Conclusion

The Milestone 4 implementation (`hopo_engine.py`, `sustain_processor.py`, `star_power_generator.py`) satisfies all mathematical invariants and game design specifications from `AGENTS.md` and `PROMPTS.md`.

Verdict: **APPROVE**

---

## 5. Verification Method

To independently reproduce the empirical findings:

1. **Run the Independent Formal Property Oracle Harness**:
   ```bash
   .venv/bin/python .agents/teamwork/challenger_m4_2/oracle_harness.py
   ```
   *Expected: 25,608 passed, 0 failed in ~1.6s.*

2. **Run Game Design Unit Tests**:
   ```bash
   .venv/bin/pytest tests/test_game_design/ -v
   ```
   *Expected: 156 passed in ~0.2s.*

3. **Run Full Project Regression Suite**:
   ```bash
   .venv/bin/pytest tests/ -v
   ```
   *Expected: 213 passed in ~2.0s.*

4. **Run Mypy & Ruff Checks**:
   ```bash
   .venv/bin/mypy src/game_design tests/test_game_design
   .venv/bin/ruff check src/game_design tests/test_game_design
   .venv/bin/ruff format --check src/game_design tests/test_game_design
   ```
   *Expected: Success / All checks passed.*
