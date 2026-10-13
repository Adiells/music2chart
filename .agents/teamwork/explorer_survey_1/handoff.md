# Handoff Report: Phase 4 Survey & Specification

**Subagent**: `explorer_survey_1`  
**Working Directory**: `/home/adiel/Projects/music2chart/.agents/teamwork/explorer_survey_1`  
**Recipient**: Orchestrator (`c32a8c2d-046d-4e36-96ca-60cf3fc9e81f`)  
**Date**: 2026-10-13T18:48:00Z  

---

## 1. Observation

1. **Original Request (`/home/adiel/Projects/music2chart/.agents/teamwork/ORIGINAL_REQUEST.md:14-25`)**:
   Specifies requirements R1 to R4:
   - R1: Musical Quantization & Grid Snapping to 192 PPQ subdivisions (1/4, 1/8, 1/12, 1/16, 1/24, 1/32) with a 16-tick tolerance window, eliminating duplicates.
   - R2: Adaptive Pitch-to-Fret Projection mapping pitch tessitura percentiles into 5 frets (0 to 4) and Open Strum (7) for sub-bass, penalizing jumps >3 frets in rapid passages (<48 ticks).
   - R3: Ergonomic Chord Formation grouping simultaneous notes into canonical chords $\le 3$ concurrent frets.
   - R4: HOPO, Strum & Sustain Duration Engine (HOPO threshold $\le 65$ ticks, strum on repeated frets, 24-tick sustain release cut).

2. **Phase 4 Prompt Specifications (`/home/adiel/Projects/music2chart/PROMPTS.md:174-250`)**:
   - Prompt 4.1 specifies `NoteQuantizer` in `src/game_design/quantizer.py` with `tolerance_ticks = 16`, subdivisions 192, 96, 64, 48, 32, 24, merging amplitudes on duplicates.
   - Prompt 4.2 specifies `PitchToFretMapper` in `src/game_design/pitch_to_fret.py` with sliding window of 2 to 4 measures, percentiles (min, 25%, 50%, 75%, max), Open note (7) for pitch < 40, jump penalty >3 frets for intervals < 48 ticks.
   - Prompt 4.3 specifies `ChordBuilder` in `src/game_design/chord_builder.py` with limit of $\le 3$ frets, canonical power chords `(0, 1)`, `(0, 2)`, `(1, 2)`, `(1, 3)`, `(2, 3)`, `(2, 4)`, `(3, 4)` and triads `(0, 1, 2)`, `(0, 2, 3)`, `(1, 2, 3)`, `(2, 3, 4)`, eliminating 0+4 fast stretches.
   - Prompt 4.4 specifies `HopoEngine` in `src/game_design/hopo_engine.py` (threshold $\le 65$ ticks, forced strums on repeat frets), `SustainProcessor` in `src/game_design/sustain_processor.py` (< 90 ticks sustain = 0, sustain length = duration - 24, next note clearance), and `StarPowerGenerator` in `src/game_design/star_power_generator.py`.
   - Prompt 6.1 (`PROMPTS.md:309-314`) explicitly chains these modules into the pipeline stages 5 through 8.

3. **Game Design Guidelines (`/home/adiel/Projects/music2chart/AGENTS.md:316-350`)**:
   - Section 7.1 defines 192 PPQ grid constants (192, 96, 48, 64, 24).
   - Section 7.2 defines 5 frets (0 to 4) and Open (7), plus sliding tessitura window of 1 to 2 measures.
   - Section 7.3 defines forbidden chord stretches (e.g. 0+4 isolated) and strictly forbids 4-fret or 5-fret chords.
   - Section 7.4 defines HOPO distance $\le 65$ ticks with fret change.
   - Section 7.5 defines 90-tick sustain threshold and 24-tick release cut before consecutive notes.

4. **Upstream Data Models (`/home/adiel/Projects/music2chart/src/models/`)**:
   - `midi_events.py`: `NoteEvent(start_time, end_time, pitch, amplitude)`.
   - `tempo.py`: `TempoMap(resolution=192, bpm_changes, time_signatures)` with `tick_to_seconds(tick)` and `seconds_to_tick(seconds)`.
   - `chart.py`: `FretType` (GREEN=0, RED=1, YELLOW=2, BLUE=3, ORANGE=4, HOPO_FORCE=5, STRUM_FORCE=6, OPEN=7), `ChartNote(tick, fret, sustain_length, is_hopo)`, `StarPowerPhrase(tick, length)`, `SongTrack(name, notes, star_power)`.

5. **Tooling & Environment (`./.venv/bin/`)**:
   - `./.venv/bin/pytest tests/` executed successfully: `57 passed in 1.94s`.
   - Python virtual environment is located at `/home/adiel/Projects/music2chart/.venv/bin/python` (Python 3.12.14).
   - Currently `src/game_design/` contains only `__init__.py` (55 bytes), and `tests/test_game_design/` contains only `__init__.py` (37 bytes).

---

## 2. Logic Chain

1. **From Observation 1, 2, and 3 to Module Architecture**:
   The requirements for Phase 4 naturally decompose into four decoupled, sequentially executed algorithmic modules plus one supporting generator:
   - Module 1: `NoteQuantizer` (`quantizer.py`) snaps raw timestamps to the 192 PPQ grid and eliminates duplicates.
   - Module 2: `PitchToFretMapper` (`pitch_to_fret.py`) projects quantized pitch numbers to 5 frets + Open strum via relative local percentiles and smooths rapid leaps.
   - Module 3: `ChordBuilder` (`chord_builder.py`) resolves polyphony into valid, ergonomic guitar chords ($\le 3$ frets).
   - Module 4A: `HopoEngine` (`hopo_engine.py`) marks HOPO vs Strum.
   - Module 4B: `SustainProcessor` (`sustain_processor.py`) calculates playability sustain tails and enforces release gaps.
   - Module 4C: `StarPowerGenerator` (`star_power_generator.py`) allocates periodic reward phrases.

2. **From Observation 1 and 2 to Grid Snapping Math**:
   Subdivisions 192, 96, 48, 24 are multiples of 24. Subdivisions 64, 32 are multiples of 32.
   Therefore, any tick $T$ can be evaluated against nearest candidate straight tick $\operatorname{round}(T / 24) \times 24$ and candidate triplet tick $\operatorname{round}(T / 32) \times 32$. If minimum distance $\le 16$, snap to candidate. This satisfies R1 and Prompt 4.1 exactly.

3. **From Observation 2 and 3 to Adaptive Pitch Projection**:
   Evaluating local percentiles over a 2-measure sliding window guarantees that both low-pitch rhythm sections and high-pitch solos use the full 5-fret span ($0 \dots 4$) organically, avoiding static bias. Sub-bass $< \text{MIDI } 40$ maps cleanly to Open note (7). Clamping jumps $> 3$ frets over intervals $< 48$ ticks guarantees ergonomic hand mechanics on the controller.

4. **From Observation 2, 3, and 4 to Chord Constraints**:
   Clone Hero controls cannot physically support 4 or 5 fret chords. Truncating clusters $> 3$ notes to canonical triads (e.g. root + 5th + octave or contiguous 3 frets) and eliminating $(0, 4)$ isolated wide stretches satisfies R3 and Clone Hero chart standards.

5. **From Observation 4 and 5 to Execution Readiness**:
   Existing domain models in `src/models/` require zero modifications. New modules in `src/game_design/` can directly import `NoteEvent`, `TempoMap`, `ChartNote`, `FretType`, and `StarPowerPhrase`. Testing can proceed using `./.venv/bin/pytest` under a strict test-driven development (TDD) workflow.

---

## 3. Caveats

- **Network Isolation**: The execution environment does not have access to external pip/PyPI registries; all work must use the existing virtual environment at `./.venv/bin/`.
- **Ruff Documentation Formatting**: Running `ruff format --check .` checks markdown code blocks in `AGENTS.md`. Code formatting checks must target `src` and `tests` (`./.venv/bin/ruff format --check src tests`).
- **Read-Only Investigation**: As an Explorer subagent, no source code in `src/game_design/` or tests in `tests/test_game_design/` were modified or created. Implementation is reserved for Worker subagents in subsequent milestones.

---

## 4. Conclusion

The specification survey for Phase 4 is 100% complete:
- Exact data contracts and method signatures have been defined for `NoteQuantizer`, `PitchToFretMapper`, `ChordBuilder`, `HopoEngine`, `SustainProcessor`, and `StarPowerGenerator`.
- All mathematical rules (192 PPQ subdivisions, 16-tick tolerance, 2-measure sliding window, MIDI 40 threshold, $\le 3$ fret chords, 65-tick HOPO threshold, 90-tick sustain threshold, 24-tick release margin) are documented in detail.
- Full details are preserved in `/home/adiel/Projects/music2chart/.agents/teamwork/explorer_survey_1/survey_report.md`.

---

## 5. Verification Method

To verify the findings of this survey independently:
1. **Inspect Documentation & Models**:
   - `view_file` on `/home/adiel/Projects/music2chart/.agents/teamwork/explorer_survey_1/survey_report.md`
   - `view_file` on `/home/adiel/Projects/music2chart/src/models/chart.py`
   - `view_file` on `/home/adiel/Projects/music2chart/src/models/tempo.py`
2. **Verify Tooling & Baseline**:
   - Run `./.venv/bin/pytest tests/` (must pass 57 tests).
   - Run `./.venv/bin/mypy src tests` (must report 0 errors).
   - Run `./.venv/bin/ruff check src tests` (must report 0 errors).
