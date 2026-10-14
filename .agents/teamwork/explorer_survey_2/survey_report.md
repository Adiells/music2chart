# Phase 4 Survey Report: Codebase & Test Architecture

**Author**: `explorer_survey_2`  
**Timestamp**: 2026-10-13T18:45:00Z  
**Scope**: Code and unit test survey for Phase 4 (Game Design and Note Mapping Engine) of `music2chart`

---

## 1. Executive Summary

Phase 4 is responsible for converting raw polyphonic audio/MIDI transcription events (`NoteEvent`s) into musically playable, ergonomic 5-fret Clone Hero charts (`ChartNote`s).

A comprehensive filesystem and codebase inspection confirms:
1. **Source directory (`src/game_design/`)**: Contains ONLY `__init__.py` (55 bytes). No implementation files (`quantizer.py`, `pitch_to_fret.py`, `chord_builder.py`, `hopo_engine.py`, `sustain_processor.py`, `star_power_generator.py`) currently exist. All modules must be authored from scratch.
2. **Test directory (`tests/test_game_design/`)**: Contains ONLY `__init__.py` (37 bytes). No test suites (`test_quantizer.py`, `test_pitch_to_fret.py`, `test_chord_builder.py`, `test_hopo_engine.py`, `test_sustain_processor.py`) currently exist.
3. **Existing test suite baseline**:
   - `pytest`: 57 tests passing in 1.84s across `test_audio_processing`, `test_config`, `test_dataset`, and `test_models`.
   - `mypy src tests`: 0 issues found in 31 source files.
   - `ruff check src tests` & `ruff format --check src tests`: 0 issues, fully formatted.
4. **Domain dependencies in `src/models/`**: Completely implemented and tested:
   - `NoteEvent` (`src/models/midi_events.py`): validated `start_time`, `end_time`, `pitch` [0-127], `amplitude` [0.0-1.0], `duration`.
   - `TempoMap`, `BPMChange`, `TimeSignature` (`src/models/tempo.py`): tick-to-seconds conversion (`tick_to_seconds`, `seconds_to_tick`) with 192 PPQ default resolution.
   - `ChartNote`, `FretType`, `StarPowerPhrase`, `SongTrack` (`src/models/chart.py`): `FretType` enums (GREEN=0, RED=1, YELLOW=2, BLUE=3, ORANGE=4, HOPO_FORCE=5, STRUM_FORCE=6, OPEN=7).

---

## 2. Inventory of `src/game_design/`

| File | Status | Size | Content Summary |
|---|---|---|---|
| `__init__.py` | Present | 55 B | Package docstring: `"""Game design mapping intelligence for Clone Hero."""` |
| `quantizer.py` | Missing | 0 B | Greenfield — needs implementation for Prompt 4.1 / R1 |
| `pitch_to_fret.py` | Missing | 0 B | Greenfield — needs implementation for Prompt 4.2 / R2 |
| `chord_builder.py` | Missing | 0 B | Greenfield — needs implementation for Prompt 4.3 / R3 |
| `hopo_engine.py` | Missing | 0 B | Greenfield — needs implementation for Prompt 4.4 / R4 |
| `sustain_processor.py` | Missing | 0 B | Greenfield — needs implementation for Prompt 4.4 / R4 |
| `star_power_generator.py` | Missing | 0 B | Greenfield — needs implementation for Prompt 4.4 / Phase 4 |

---

## 3. Inventory of `tests/test_game_design/`

| File | Status | Size | Content Summary |
|---|---|---|---|
| `__init__.py` | Present | 37 B | Package docstring: `"""Tests for game design modules."""` |
| `test_quantizer.py` | Missing | 0 B | Needs authoring to validate R1 (grid subdivisions, snapping tolerance, deduplication) |
| `test_pitch_to_fret.py` | Missing | 0 B | Needs authoring to validate R2 (scale flow, relative sliding window, jump penalty) |
| `test_chord_builder.py` | Missing | 0 B | Needs authoring to validate R3 (polyphonic cluster simplification, <=3 frets, stretch limits) |
| `test_hopo_engine.py` | Missing | 0 B | Needs authoring to validate R4 (HOPO threshold <=65 ticks, strum forcing on repeat) |
| `test_sustain_processor.py` | Missing | 0 B | Needs authoring to validate R4 (>=90 ticks threshold, 24-tick cut, next note release margin) |

---

## 4. Inspection of `tests/conftest.py` & Test Helpers

### 4.1 `tests/conftest.py`
The project fixture file currently provides a single fixture:
- `realistic_chart_content() -> str`:
  - Contains complete Clone Hero `.chart` text:
    - `[Song]` metadata (Name="Test Anthem", Resolution=192, MusicStream="song.ogg").
    - `[SyncTrack]` with 120 BPM at tick 0 and 140 BPM at tick 768.
    - `[Events]` with intro and verse 1 markers.
    - `[ExpertSingle]` with Open note (tick 0), Green (tick 96), Red with 96 sustain (tick 192), Green+Yellow chord + Star Power phrase (tick 384), Blue (tick 768), Orange with 48 sustain (tick 864).

### 4.2 Reusable Helpers from Other Tests
- `tests/test_dataset/test_evaluator.py`:
  - Fixture `standard_tempo_map()`: clean 120.0 BPM tempo map at 192 PPQ (`resolution=192`, `bpm_changes=[BPMChange(tick=0, bpm=120.0)]`).
- `tests/test_audio_processing/test_tempo_tracker.py`:
  - Function `_create_pulse_train(bpm, duration_seconds, sample_rate)`: generating synthetic click tracks.

---

## 5. Architectural Specifications & Detailed Signatures

Based on `AGENTS.md` (Sections 4 & 7), `PROMPTS.md` (Prompts 4.1 to 4.4), and `ORIGINAL_REQUEST.md` (R1 to R4), below are the exact class definitions, method signatures, data structures, and algorithmic contracts required.

---

### 5.1 Milestone 1: Musical Quantization & Grid Snapping (`src/game_design/quantizer.py`)

#### Contract & Data Structure
```python
@dataclass(frozen=True)
class QuantizedNote:
    """Note with quantized tick positions on the 192 PPQ grid."""
    tick: int
    pitch: int
    duration_ticks: int
    amplitude: float

class NoteQuantizer:
    VALID_SUBDIVISIONS = (192, 96, 64, 48, 32, 24)
    # 1/4 (192), 1/8 (96), 1/12 (64), 1/16 (48), 1/24 (32), 1/32 (24)

    def __init__(self, resolution: int = 192, tolerance_ticks: int = 16) -> None:
        ...

    def snap_tick(self, tick: int) -> int:
        """Find closest subdivision grid point; snap if abs(delta) <= tolerance_ticks, else return tick."""
        ...

    def quantize(
        self,
        notes: list[NoteEvent],
        tempo_map: TempoMap,
    ) -> list[QuantizedNote]:
        """Convert NoteEvents to ticks, snap onsets, calculate duration_ticks, and deduplicate."""
        ...
```

#### Expected Behaviors & Test Cases (`test_quantizer.py`)
1. **Subdivision Snapping**:
   - Quarter note: raw tick 190 -> 192 (delta 2 <= 16).
   - Eighth note (1/8): raw tick 98 -> 96 (delta 2 <= 16).
   - Eighth triplet (1/12): raw tick 66 -> 64, raw tick 126 -> 128 (delta 2 <= 16).
   - Sixteenth note (1/16): raw tick 50 -> 48 (delta 2 <= 16).
   - Sixteenth triplet (1/24): raw tick 31 -> 32 (delta 1 <= 16).
   - Thirty-second note (1/32): raw tick 23 -> 24, raw tick 71 -> 72 (delta 1 <= 16).
2. **Tolerance Window Enforcement**:
   - With `tolerance_ticks = 16`, any point with distance <= 16 snaps to the nearest valid grid point.
   - If custom `tolerance_ticks` is smaller (e.g. 5) and a note is at distance 12, it must not snap.
3. **Deduplication**:
   - If two notes share the same snapped `tick` and `pitch`, merge into a single `QuantizedNote`.
   - Merged amplitude preserves velocity (e.g., `max(amplitude)` or sum capped at 1.0).
   - Merged duration preserves length (e.g., `max(duration_ticks)`).
4. **Edge Cases**:
   - Empty input list `[]` -> returns `[]`.
   - Single note at tick 0 -> remains at tick 0.
   - Preserves strict ascending ordering: `(tick, pitch)`.

---

### 5.2 Milestone 2: Adaptive Pitch-to-Fret Projection (`src/game_design/pitch_to_fret.py`)

#### Contract & Data Structure
```python
class PitchToFretMapper:
    OPEN_NOTE_PITCH_THRESHOLD = 40  # Below MIDI 40 (low E on guitar)
    MAX_RAPID_FRET_JUMP = 3         # Max fret distance jump in rapid passages
    RAPID_PASSAGE_TICKS = 48        # 16th note threshold

    def __init__(
        self,
        window_ticks: int = 1536,    # ~2 measures at 4/4 (192 * 4 * 2)
        max_jump: int = 3,
        rapid_interval: int = 48,
        open_threshold: int = 40,
    ) -> None:
        ...

    def map_notes(
        self,
        notes: list[QuantizedNote],
    ) -> list[ChartNote]:
        """Map pitches to Clone Hero frets (0-4, 7) using sliding tessitura percentiles."""
        ...
```

#### Expected Behaviors & Test Cases (`test_pitch_to_fret.py`)
1. **Ascending Scale Flow**:
   - Chromatic or diatonic scale (e.g., C4 to G4) must map smoothly to `GREEN (0) -> RED (1) -> YELLOW (2) -> BLUE (3) -> ORANGE (4)`.
2. **Relative Tessitura Sliding Window**:
   - High register solo (e.g., pitches spanning MIDI 75 to 90):
     Because of local percentile normalization across the window, the lowest notes of the solo map toward Green/Red and highest toward Blue/Orange, rather than all clustering strictly on Orange (4).
3. **Open Note Assignment**:
   - Extreme sub-bass notes (< MIDI 40, e.g. Drop D, 7-string B0/E1) map to `FretType.OPEN` (7).
4. **Rapid Passage Jump Penalty**:
   - If interval between consecutive notes is `< 48` ticks and pitch jump would produce a leap `> 3` frets (e.g., Green 0 to Orange 4, span 4), the target fret is constrained/penalized to a maximum leap of 3 (e.g., clamped to Blue 3).
5. **Edge Cases**:
   - Empty input list `[]` -> returns `[]`.
   - Monophonic constant pitch sequence -> stays on middle/base fret consistently without erratic oscillation.

---

### 5.3 Milestone 3: Ergonomic Chord Formation & Constraints (`src/game_design/chord_builder.py`)

#### Contract & Data Structure
```python
class ChordBuilder:
    MAX_CONCURRENT_FRETS = 3
    CANONICAL_POWER_CHORDS = frozenset({
        (0, 1), (0, 2), (1, 2), (1, 3), (2, 3), (2, 4), (3, 4)
    })
    CANONICAL_TRIADS = frozenset({
        (0, 1, 2), (0, 2, 3), (1, 2, 3), (2, 3, 4)
    })
    FORBIDDEN_STRETCHES = frozenset({(0, 4)})

    def __init__(self, max_frets: int = 3) -> None:
        ...

    def build_chords(self, notes: list[ChartNote]) -> list[ChartNote]:
        """Group simultaneous notes at identical ticks, constrain to <= 3 frets, eliminate unplayable stretches."""
        ...
```

#### Expected Behaviors & Test Cases (`test_chord_builder.py`)
1. **Grouping Simultaneous Notes**:
   - Notes with identical `tick` are grouped into a chord cluster.
2. **Polyphonic Cluster Simplification**:
   - When a 4-note or 5-note cluster occurs at the same tick (e.g., frets 0, 1, 2, 3), simplify to at most 3 frets (e.g., root 0, 1, 3 or canonical triad 0, 1, 2).
   - Never output > 3 frets at a single tick.
3. **Canonical Chord Preservation**:
   - Power chords (0+1, 0+2, 1+2, 1+3, 2+3, 2+4, 3+4) are preserved.
   - Triads (0+1+2, 0+2+3, 1+2+3, 2+3+4) are preserved.
4. **Forbidden Stretch Elimination**:
   - Wide unnatural stretches like Green + Orange (0+4) without intermediate frets in fast passages are simplified (e.g. to Green + Yellow 0+2 or single note).
5. **Open Note Coexistence**:
   - In Clone Hero, an Open note (7) cannot be struck simultaneously with a fretted note (0-4). The engine must ensure Open notes remain single notes.
6. **Order Preservation**:
   - Notes returned are sorted primarily by `tick`, secondarily by `fret`.

---

### 5.4 Milestone 4: HOPO, Strum & Sustain Duration Engine (`src/game_design/hopo_engine.py` & `sustain_processor.py`)

#### Contract 1: `HopoEngine` (`src/game_design/hopo_engine.py`)
```python
class HopoEngine:
    HOPO_THRESHOLD_TICKS = 65  # Distance <= 65 ticks allows natural HOPO

    def __init__(self, hopo_threshold: int = 65) -> None:
        ...

    def process_hopos(self, notes: list[ChartNote]) -> list[ChartNote]:
        """Evaluate chronological note transitions and set is_hopo flags."""
        ...
```

#### Expected Behaviors & Test Cases (`test_hopo_engine.py`)
1. **Natural HOPO Detection**:
   - If `tick_current - tick_prev <= 65` ticks AND `fret_current != fret_prev`:
     `note.is_hopo = True`.
2. **Strum on Slow Tempo**:
   - If `tick_current - tick_prev > 65` ticks:
     `note.is_hopo = False`.
3. **Forced Strum on Repeated Frets**:
   - If `tick_current - tick_prev <= 65` ticks BUT `fret_current == fret_prev` (e.g., Green followed by Green):
     `note.is_hopo = False` (MUST require a strum, never natural HOPO).
4. **First Note Rule**:
   - The first note of a song or section is always a strum (`is_hopo = False`).
5. **Chord Transitions**:
   - Identical chords repeated at fast tempo are always strums (`is_hopo = False`).

---

#### Contract 2: `SustainProcessor` (`src/game_design/sustain_processor.py`)
```python
class SustainProcessor:
    MIN_SUSTAIN_THRESHOLD = 90  # Duration < 90 ticks -> sustain_length = 0
    RELEASE_MARGIN_TICKS = 24   # Release cut before next note

    def __init__(self, min_threshold: int = 90, release_margin: int = 24) -> None:
        ...

    def process_sustains(
        self,
        notes: list[ChartNote],
        durations: list[int] | dict[int, int] | None = None,
    ) -> list[ChartNote]:
        """Compute sustain lengths with 90-tick cutoff and 24-tick release margin."""
        ...
```

#### Expected Behaviors & Test Cases (`test_sustain_processor.py`)
1. **Short Note Filter**:
   - Duration < 90 ticks (e.g., 48 ticks, 16th note) -> `sustain_length = 0`.
2. **Release Margin Calculation**:
   - Duration >= 90 ticks (e.g., quarter note = 192 ticks) -> `sustain_length = 192 - 24 = 168` ticks.
3. **Collision Avoidance with Subsequent Note**:
   - If note A is at tick 0 with duration 200, and note B is at tick 96:
     Sustain of note A must not overlap note B: `sustain_length = max(0, 96 - 0 - 24) = 72` ticks.
4. **Non-negative Clamping**:
   - If subsequent note is within 24 ticks, sustain is clamped to 0.

---

### 5.5 Supporting Module: `StarPowerGenerator` (`src/game_design/star_power_generator.py`)
```python
class StarPowerGenerator:
    DEFAULT_INTERVAL_MEASURES = 16
    DEFAULT_PHRASE_LENGTH_TICKS = 768  # 1 measure in 4/4 (4 * 192)

    def __init__(self, interval_measures: int = 16, phrase_length_ticks: int = 768) -> None:
        ...

    def generate(
        self,
        notes: list[ChartNote],
        resolution: int = 192,
    ) -> list[StarPowerPhrase]:
        """Allocate Star Power phrases periodically over dense note passages."""
        ...
```

---

## 6. Synthesis and Integration Architecture

The following pipeline flow is specified for integration in `src/pipeline.py` (Prompt 6.1):
```
NoteEvents (from PitchTranscriber / HarmonicFilter)
    │
    ▼
[NoteQuantizer.quantize(notes, tempo_map)] ──> QuantizedNotes (snapped to 192 PPQ grid)
    │
    ▼
[PitchToFretMapper.map_notes(quantized_notes)] ──> ChartNotes (frets 0-4 or 7, jump penalized)
    │
    ▼
[ChordBuilder.build_chords(mapped_notes)] ──> ChartNotes (grouped, <=3 frets, valid chords)
    │
    ▼
[HopoEngine.process_hopos(chord_notes)] ──> ChartNotes (is_hopo flags set)
    │
    ▼
[SustainProcessor.process_sustains(hopo_notes, durations)] ──> ChartNotes (sustain lengths set)
    │
    ▼
[StarPowerGenerator.generate(final_notes)] ──> StarPowerPhrases
    │
    ▼
SongTrack(name="ExpertSingle", notes=final_notes, star_power=star_power)
```

---

## 7. Recommendations for Milestone Implementation

1. **Test-First Implementation (TDD)**:
   - For each milestone (M1 through M4), write the corresponding test file first in `tests/test_game_design/`.
   - Run `.venv/bin/pytest tests/test_game_design/<test_file>.py` (expect failures).
   - Implement the module in `src/game_design/`.
   - Re-run pytest until 100% passing.
2. **Linter & Type Verification**:
   - Verify with `.venv/bin/mypy src/game_design tests/test_game_design`.
   - Verify with `.venv/bin/ruff check src/game_design tests/test_game_design`.
   - Verify with `.venv/bin/ruff format --check src/game_design tests/test_game_design`.
3. **Full Regression Check**:
   - Run complete suite `.venv/bin/pytest tests/` after each milestone to ensure zero regressions across the 57 existing passing tests.
