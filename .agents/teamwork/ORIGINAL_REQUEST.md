# Original User Request

## Initial Request — 2026-10-13T18:36:09Z

Implement the complete Game Design and Note Mapping engine (Phase 4 of chartgen) for Clone Hero charts, translating raw MIDI NoteEvents into musically playable, ergonomic 5-fret charts.

Working directory: /home/adiel/Projects/music2chart
Integrity mode: development

Reference specifications: AGENTS.md (Sections 4 and 7) and PROMPTS.md (Phase 4: Prompts 4.1 to 4.4).

## Requirements

### R1. Musical Quantization & Grid Snapping
Snapping raw onset timestamps to standard 192 PPQ subdivisions (1/4, 1/8, 1/12, 1/16, 1/24, 1/32) with a 16-tick tolerance window, eliminating duplicates while preserving velocity and amplitude.

### R2. Adaptive Pitch-to-Fret Projection
Dynamic sliding-window pitch projection mapping pitch tessitura percentiles into 5 frets (Green 0 to Orange 4) and Open Strum (7) for extreme sub-bass, penalizing wide fret jumps (>3 frets) in rapid passages (<48 ticks).

### R3. Ergonomic Chord Formation & Constraints
Grouping simultaneous notes into canonical Clone Hero chords (power chords, extended triads) with a maximum of 3 concurrent frets, eliminating unplayable stretches.

### R4. HOPO, Strum & Sustain Duration Engine
Automatic Hammer-On / Pull-Off detection (intervals <= 65 ticks with fret variation, forcing strums on repeated frets) and sustain length calculation cutting a 24-tick release margin prior to consecutive notes.

## Acceptance Criteria

### Automated Verification
- [ ] 100% of unit tests pass under `pytest tests/test_game_design/`:
  - `test_quantizer.py`: validates grid snapping for quarter, 1/8, 1/12, 1/16, 1/24, 1/32 notes and deduplication.
  - `test_pitch_to_fret.py`: validates ascending scale flow and relative tessitura windows during solo passages.
  - `test_chord_builder.py`: validates polyphonic clusters simplified into ergonomic chords <= 3 frets.
  - `test_hopo_engine.py`: validates HOPO threshold (<= 65 ticks) and strum forcing on identical fret repetitions.
- [ ] Complete project regression test suite passes (`pytest tests/`)
- [ ] Strict type checking passes (`mypy src/game_design tests/test_game_design`)
- [ ] Ruff linting and formatting conform to pyproject.toml rules (`ruff check` and `ruff format --check`)
