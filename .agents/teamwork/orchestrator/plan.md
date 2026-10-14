# Execution Plan: Phase 4 Game Design and Note Mapping Engine

## Objective
Implement Phase 4 of `music2chart`: the complete game design and note mapping engine translating raw MIDI `NoteEvent`s into musically playable, ergonomic 5-fret Clone Hero charts (`src/game_design/`).

## Milestones
1. **Survey (Phase 0)**:
   - Spawn 3 parallel Explorers:
     - Explorer 1: Inspect `PROMPTS.md` (Phase 4), `AGENTS.md` (Sections 4 & 7), and data models in `src/models/` (`midi_events.py`, `tempo.py`, `chart.py`).
     - Explorer 2: Inspect existing tests under `tests/test_game_design/` (`test_quantizer.py`, `test_pitch_to_fret.py`, `test_chord_builder.py`, `test_hopo_engine.py`) and existing stubs/implementations in `src/game_design/`.
     - Explorer 3: Inspect `pyproject.toml`, full test suite baseline (`pytest tests/`), mypy and ruff configuration and current status.
   - Aggregate findings into `SCOPE.md`.

2. **Milestone 1: Musical Quantization & Grid Snapping (`src/game_design/quantizer.py`)**:
   - R1: Snapping raw onset timestamps to standard 192 PPQ subdivisions (1/4, 1/8, 1/12, 1/16, 1/24, 1/32) with a 16-tick tolerance window, eliminating duplicates while preserving velocity and amplitude.
   - Iteration: Explorer -> Worker -> 2 Reviewers -> 2 Challengers -> Forensic Auditor -> Gate.

3. **Milestone 2: Adaptive Pitch-to-Fret Projection (`src/game_design/pitch_to_fret.py`)**:
   - R2: Dynamic sliding-window pitch projection mapping pitch tessitura percentiles into 5 frets (Green 0 to Orange 4) and Open Strum (7) for extreme sub-bass, penalizing wide fret jumps (>3 frets) in rapid passages (<48 ticks).
   - Iteration: Explorer -> Worker -> 2 Reviewers -> 2 Challengers -> Forensic Auditor -> Gate.

4. **Milestone 3: Ergonomic Chord Formation & Constraints (`src/game_design/chord_builder.py`)**:
   - R3: Grouping simultaneous notes into canonical Clone Hero chords (power chords, extended triads) with a maximum of 3 concurrent frets, eliminating unplayable stretches.
   - Iteration: Explorer -> Worker -> 2 Reviewers -> 2 Challengers -> Forensic Auditor -> Gate.

5. **Milestone 4: HOPO, Strum & Sustain Duration Engine (`src/game_design/hopo_engine.py` & `src/game_design/sustain_processor.py`)**:
   - R4: Automatic Hammer-On / Pull-Off detection (intervals <= 65 ticks with fret variation, forcing strums on repeated frets) and sustain length calculation cutting a 24-tick release margin prior to consecutive notes.
   - Iteration: Explorer -> Worker -> 2 Reviewers -> 2 Challengers -> Forensic Auditor -> Gate.

6. **Milestone 5: Full Project Verification & Regression**:
   - Run complete test suite (`pytest tests/`), strict type checking (`mypy src/game_design tests/test_game_design`), and ruff checks (`ruff check`, `ruff format --check`).
   - Forensic Auditor final sign-off.
