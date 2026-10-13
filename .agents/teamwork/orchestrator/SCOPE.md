# Scope: Phase 4 Game Design and Note Mapping Engine

## Architecture
The Game Design engine translates raw transcription events (`NoteEvent`s) into musically playable, ergonomic 5-fret Clone Hero charts (`ChartNote`s).

Data flow:
```
[Raw NoteEvents + TempoMap]
         │
         ▼
[NoteQuantizer (quantizer.py)] ──> QuantizedNote(tick, pitch, duration_ticks, amplitude)
         │                         Snaps to 192 PPQ subdivisions with 16-tick tolerance
         ▼
[PitchToFretMapper (pitch_to_fret.py)] ──> ChartNote(tick, fret [0-4, 7], sustain_length=0, is_hopo=False)
         │                                Adaptive 2-measure sliding window, sub-bass <40 -> 7, jump penalty
         ▼
[ChordBuilder (chord_builder.py)] ──> Groups simultaneous notes into chords <= 3 frets
         │                            Enforces canonical shapes, eliminates unplayable (0, 4) stretches
         ▼
[HopoEngine (hopo_engine.py)] ──> Sets is_hopo=True for intervals <= 65 ticks with fret change
         │                        Forces strum (is_hopo=False) on repeated frets/chords
         ▼
[SustainProcessor (sustain_processor.py)] ──> Sets sustain_length for notes >= 90 ticks
         │                                    Subtracts 24-tick release margin, clamps before next note
         ▼
[StarPowerGenerator (star_power_generator.py)] ──> StarPowerPhrase(tick, length)
         │                                        Periodic phrases every 16-32 measures
         ▼
[ExpertSingle SongTrack Output]
```

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | R1.1 Subdivision Snapping | Snap onsets to 1/4 (192), 1/8 (96), 1/12 (64), 1/16 (48), 1/24 (32), 1/32 (24) ticks | M1 | ORIGINAL_REQUEST §R1 |
| 2 | R1.2 Tolerance Window | Snap only if abs(distance) <= 16 ticks; keep raw tick otherwise | M1 | ORIGINAL_REQUEST §R1 |
| 3 | R1.3 Deduplication & Velocity | Merge duplicate (tick, pitch) notes taking max amplitude and max duration | M1 | ORIGINAL_REQUEST §R1 |
| 4 | R2.1 Sliding Window Tessitura | Adaptive 1536-tick (~2 measures) sliding window normalizing pitch percentiles to 5 frets (0-4) | M2 | ORIGINAL_REQUEST §R2 |
| 5 | R2.2 Sub-bass Open Note | Pitch < 40 mapped to FretType.OPEN (7) | M2 | ORIGINAL_REQUEST §R2 |
| 6 | R2.3 Rapid Passage Jump Penalty | Clamp fret jumps > 3 frets when interval < 48 ticks | M2 | ORIGINAL_REQUEST §R2 |
| 7 | R3.1 Simultaneous Grouping | Group notes at identical ticks into chord clusters | M3 | ORIGINAL_REQUEST §R3 |
| 8 | R3.2 Max 3 Frets Constraint | Simplify polyphonic clusters > 3 notes to canonical triads (<= 3 frets) | M3 | ORIGINAL_REQUEST §R3 |
| 9 | R3.3 Canonical Shapes & Stretches | Preserve canonical power chords/triads, eliminate unplayable (0, 4) stretches | M3 | ORIGINAL_REQUEST §R3 |
| 10 | R3.4 Open Note Exclusivity | Ensure Open notes (7) never coexist with frets 0-4 at the same tick | M3 | ORIGINAL_REQUEST §R3 |
| 11 | R4.1 Natural HOPO Detection | Interval <= 65 ticks with fret variation -> is_hopo = True | M4 | ORIGINAL_REQUEST §R4 |
| 12 | R4.2 Forced Strum on Repeats | Interval <= 65 ticks with identical fret/chord -> is_hopo = False | M4 | ORIGINAL_REQUEST §R4 |
| 13 | R4.3 Sustain Cutoff & Release | Notes < 90 ticks -> sustain 0; notes >= 90 ticks -> duration - 24 ticks | M4 | ORIGINAL_REQUEST §R4 |
| 14 | R4.4 Sustain Next-Note Clearance | Clamp sustain before consecutive note onset by at least 24 ticks | M4 | ORIGINAL_REQUEST §R4 |
| 15 | R4.5 Star Power Allocation | Allocate StarPowerPhrase periodically over dense passages | M4 | AGENTS.md §4.2 & PROMPTS.md 4.4 |
| 16 | R5.1 Full Test Suite Passing | 100% unit tests pass under pytest tests/test_game_design/ | M5 | Acceptance Criteria |
| 17 | R5.2 Full Regression Passing | 100% regression tests pass under pytest tests/ (all 57 existing + new) | M5 | Acceptance Criteria |
| 18 | R5.3 Strict Mypy Verification | Zero issues under mypy src/game_design tests/test_game_design | M5 | Acceptance Criteria |
| 19 | R5.4 Ruff Linting & Formatting | Zero issues under ruff check and ruff format --check src tests | M5 | Acceptance Criteria |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | M1: Quantization & Grid Snapping | `src/game_design/quantizer.py`, `tests/test_game_design/test_quantizer.py` | none | DONE |
| 2 | M2: Adaptive Pitch-to-Fret Projection | `src/game_design/pitch_to_fret.py`, `tests/test_game_design/test_pitch_to_fret.py` | M1 | DONE |
| 3 | M3: Ergonomic Chord Formation & Constraints | `src/game_design/chord_builder.py`, `tests/test_game_design/test_chord_builder.py` | M2 | DONE |
| 4 | M4: HOPO, Strum & Sustain Duration Engine | `src/game_design/hopo_engine.py`, `src/game_design/sustain_processor.py`, `src/game_design/star_power_generator.py`, `tests/test_game_design/test_hopo_engine.py` | M3 | DONE |
| 5 | M5: Full Project Verification & Regression | Full suite `pytest tests/`, `mypy src/game_design tests/test_game_design`, `ruff check`, `ruff format --check src tests` | M1, M2, M3, M4 | DONE |

## Interface Contracts
### `NoteQuantizer` (`src/game_design/quantizer.py`) [IMPLEMENTED & VERIFIED]
- Input: `notes: list[NoteEvent]`, `tempo_map: TempoMap`
- Output: `list[QuantizedNote]` where `QuantizedNote(tick: int, pitch: int, duration_ticks: int, amplitude: float)`
- Subdivisions: 192 (1/4), 96 (1/8), 64 (1/12), 48 (1/16), 32 (1/24), 24 (1/32)
- Tolerance: `tolerance_ticks: int = 16`
- Deduplication: identical `(tick, pitch)` -> merged with `max(amplitude)` and `max(duration_ticks)`

### `PitchToFretMapper` (`src/game_design/pitch_to_fret.py`) [IMPLEMENTED & VERIFIED]
- Input: `notes: list[QuantizedNote]`
- Output: `list[ChartNote]` where `ChartNote(tick: int, fret: FretType, sustain_length: int, is_hopo: bool)`
- Parameters: `window_ticks: int = 1536`, `max_jump: int = 3`, `rapid_interval: int = 48`, `open_threshold: int = 40`
- Open Note: `pitch < 40` -> `FretType.OPEN` (7)
- Jump penalty: if `0 < tick - prev_tick < 48` and `abs(fret - prev_fret) > 3`, clamp leap directionally to `<= 3` frets.

### `ChordBuilder` (`src/game_design/chord_builder.py`)
- Input: `notes: list[ChartNote]`
- Output: `list[ChartNote]`
- Parameters: `max_frets: int = 3`
- Constraints: max 3 frets per tick, power chords & triads canonical shapes, eliminate `(0, 4)` unplayable stretches, Open note exclusivity.

### `HopoEngine` (`src/game_design/hopo_engine.py`)
- Input: `notes: list[ChartNote]`
- Output: `list[ChartNote]` (sets `is_hopo`)
- Threshold: `<= 65` ticks. Repeated frets/chords forced strum (`is_hopo = False`). First note always strum.

### `SustainProcessor` (`src/game_design/sustain_processor.py`)
- Input: `notes: list[ChartNote]`, optional duration map
- Output: `list[ChartNote]` (updates `sustain_length`)
- Rules: `< 90` ticks -> 0. `>= 90` ticks -> `duration - 24`. Next note collision clearance -> `next_tick - tick - 24`.

## Code Layout
- `src/game_design/`
  - `__init__.py`: Package export of all game design classes (NoteQuantizer, QuantizedNote, PitchToFretMapper exported)
  - `quantizer.py`: `QuantizedNote`, `NoteQuantizer` [DONE]
  - `pitch_to_fret.py`: `PitchToFretMapper` [DONE]
  - `chord_builder.py`: `ChordBuilder` [PLANNED]
  - `hopo_engine.py`: `HopoEngine` [PLANNED]
  - `sustain_processor.py`: `SustainProcessor` [PLANNED]
  - `star_power_generator.py`: `StarPowerGenerator` [PLANNED]
- `tests/test_game_design/`
  - `__init__.py`
  - `test_quantizer.py` [DONE - 18 tests]
  - `test_pitch_to_fret.py` [DONE - 22 tests]
  - `test_chord_builder.py` [PLANNED]
  - `test_hopo_engine.py` [PLANNED]
