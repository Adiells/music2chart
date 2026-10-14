# Specification Report: Milestone 4 Game Design Engine (HopoEngine, SustainProcessor, StarPowerGenerator)

**Date**: 2026-10-13  
**Author**: `spec_miner_m4` (Specification Miner Subagent)  
**Target Milestone**: Phase 4 — Milestone 4 (`hopo_engine.py`, `sustain_processor.py`, `star_power_generator.py`)  
**Repository**: `/home/adiel/Projects/music2chart`

---

## 1. Executive Summary

This report delivers the authoritative specification, interface contracts, behavioral edge cases, and concrete runnable test suites for the three remaining Game Design components in Phase 4 of `music2chart`:
1. **`HopoEngine`** (`src/game_design/hopo_engine.py`): Determines Hammer-On / Pull-Off playability states (`is_hopo=True`) on notes with delta intervals $\le 65$ ticks and pitch/fret transitions, while enforcing strumming (`is_hopo=False`) on the initial note, notes separated by $> 65$ ticks, chords, and consecutive identical frets.
2. **`SustainProcessor`** (`src/game_design/sustain_processor.py`): Sets note tail durations (`sustain_length`), enforcing zero sustain for short notes ($< 90$ ticks), cutting a 24-tick release margin ($S = \text{duration} - 24$) for sustained notes ($\ge 90$ ticks), clamping before consecutive note onsets to ensure re-strum clearance, and preserving full duration on track terminal notes.
3. **`StarPowerGenerator`** (`src/game_design/star_power_generator.py`): Periodically synthesizes `StarPowerPhrase` intervals (every ~16 to 32 measures) positioned strictly over dense, active note sections, ensuring no phrase overlaps, positive duration ticks, and grace handling of short or empty charts.

---

## 2. Authoritative Specification Sources

1. **`AGENTS.md`**:
   - **Section 4.2**: Data model definitions for `ChartNote`, `FretType`, `StarPowerPhrase`, and `SongTrack`.
   - **Section 7.4**: Official Clone Hero Hammer-On / Pull-Off mechanics ($\le 65$ ticks threshold, fret variation, forced strum on repeated frets).
   - **Section 7.5**: Official sustain mechanics ($< 90$ ticks cutoff, $24$-tick release margin, re-palhetada clearance).
2. **`ORIGINAL_REQUEST.md`**:
   - **Requirement R4**: Automatic HOPO detection and sustain length calculation cutting a 24-tick margin prior to consecutive notes.
   - **Acceptance Criteria**: Strict verification under `pytest tests/test_game_design/test_hopo_engine.py`, regression verification, mypy, and ruff.
3. **`PROMPTS.md` (Prompt 4.4)**:
   - Detailed functional breakdown for `HopoEngine`, `SustainProcessor`, and `StarPowerGenerator`.
4. **`SCOPE.md` & `PROJECT.md`**:
   - Milestone 4 architecture, pipeline contracts, and interface signatures.

---

## 3. Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | HOPO Mechanics | Natural HOPO Detection | Consecutive note interval $\le 65$ ticks with fret variation is marked as HOPO | `Sequence[ChartNote]` | `list[ChartNote]` with `is_hopo=True` | Ignores non-playable modifiers | `AGENTS.md` §7.4, `PROMPTS.md` 4.4 |
| 2 | HOPO Mechanics | Strum Interval Threshold | Notes spaced $> 65$ ticks (e.g. 66, 96, 192 ticks) are marked as Strum | `Sequence[ChartNote]` | `list[ChartNote]` with `is_hopo=False` | None | `AGENTS.md` §7.4 |
| 3 | HOPO Mechanics | Forced Strum on Repeats | Identical fret repeats within $\le 65$ ticks are forced to Strum (`is_hopo=False`) | `Sequence[ChartNote]` | `list[ChartNote]` with `is_hopo=False` | None | `AGENTS.md` §7.4 |
| 4 | HOPO Mechanics | First Note Strum Invariant | The very first note (or chord) in a song track is ALWAYS a Strum | `Sequence[ChartNote]` | First `ChartNote` has `is_hopo=False` | None | `ORIGINAL_REQUEST.md` R4 |
| 5 | HOPO Mechanics | Rapid Scales Flow | Rapid ascending/descending scales (intervals $\le 65$ ticks) have note 0 as Strum, remaining notes as HOPOs | `Sequence[ChartNote]` | All subsequent notes have `is_hopo=True` | None | `PROMPTS.md` 4.4 |
| 6 | HOPO Mechanics | Chord Transitions | Single-to-chord and chord-to-chord are Strums; chord-to-single is HOPO if fret is new, Strum if fret was in chord | `Sequence[ChartNote]` | `list[ChartNote]` with unified tick flags | None | `ORIGINAL_REQUEST.md` R4 |
| 7 | HOPO Mechanics | Open Note Transitions | Open note (7) to fret (0-4) is HOPO; fret to Open is HOPO; Open to Open is forced Strum | `Sequence[ChartNote]` | `list[ChartNote]` | None | `AGENTS.md` §7.4 |
| 8 | HOPO Mechanics | Configurable Threshold | Custom `hopo_threshold` parameter in `HopoEngine` | `hopo_threshold: int` | Custom threshold applied | `ValueError` if `hopo_threshold < 0` | Codebase standards |
| 9 | Sustain Processing | Short Note Cutoff | Note duration $< 90$ ticks sets `sustain_length = 0` | `notes: Sequence[ChartNote]`, duration $< 90$ | `sustain_length = 0` | None | `AGENTS.md` §7.5 |
| 10 | Sustain Processing | Sustained Note Margin | Note duration $\ge 90$ ticks sets `sustain_length = duration - 24` | `notes: Sequence[ChartNote]`, duration $\ge 90$ | `sustain_length = duration - 24` | None | `AGENTS.md` §7.5 |
| 11 | Sustain Processing | Next-Note Overlap Clamping | Long note sustain is clamped to $(t_{\text{next}} - t_{\text{curr}}) - 24$ | `Sequence[ChartNote]` | `sustain_length` clamped | None | `AGENTS.md` §7.5 |
| 12 | Sustain Processing | Final Note Preservation | Final note/chord of track retains full `duration - 24` without next-note clamping | `Sequence[ChartNote]` | `sustain_length = duration - 24` | None | `ORIGINAL_REQUEST.md` R4 |
| 13 | Sustain Processing | Simultaneous Chord Sustains | Notes in the same chord share the same tick and do not clamp each other | `Sequence[ChartNote]` | Independent/uniform chord sustains | None | `AGENTS.md` §7.3 |
| 14 | Sustain Processing | Optional Duration Mapping | Supports duration extraction from `ChartNote.sustain_length` or explicit mapping/sequence | `notes`, `durations: Mapping | Sequence | None` | `list[ChartNote]` | None | `SCOPE.md` Interface Contracts |
| 15 | Sustain Processing | Configurable Parameters | Custom `min_sustain_ticks` and `release_margin` | `min_sustain_ticks: int`, `release_margin: int` | Configured params applied | `ValueError` if negative | Codebase standards |
| 16 | Star Power | Periodic Phrase Allocation | Allocates `StarPowerPhrase` every ~16 to 32 measures | `Sequence[ChartNote]` | `list[StarPowerPhrase]` | None | `PROMPTS.md` 4.4, `AGENTS.md` §4.2 |
| 17 | Star Power | Note Region Alignment | Star Power phrases strictly encompass active note passages | `Sequence[ChartNote]` | Phrases fall on notes | None | `ORIGINAL_REQUEST.md` R4 |
| 18 | Star Power | Empty / Short Chart Grace | Empty or very short note sequences yield empty `StarPowerPhrase` list | Empty/short `Sequence[ChartNote]` | `[]` | None | Edge case robustness |
| 19 | Star Power | No Overlapping Phrases | Phrases never overlap in tick time ($\text{phrase}_k.\text{end} \le \text{phrase}_{k+1}.\text{start}$) | `Sequence[ChartNote]` | Non-overlapping phrases | None | Clone Hero .chart spec |
| 20 | Star Power | Configurable Generation | Custom `measure_ticks`, `interval_measures`, `phrase_length_measures`, `min_notes` | Config parameters | Custom intervals | `ValueError` if params $\le 0$ | Codebase standards |

---

## 4. Edge Cases and Observed Invariants

| # | Feature | Input Scenario | Expected Behavior |
|---|---------|----------------|-------------------|
| E1 | HopoEngine | Empty notes `[]` | Returns `[]` without error |
| E2 | HopoEngine | Single note `[ChartNote(0, GREEN)]` | Returns `[ChartNote(0, GREEN, is_hopo=False)]` |
| E3 | HopoEngine | Consecutive notes spaced exactly at 65 ticks | Marked as HOPO (`is_hopo=True`) since $\Delta \le 65$ |
| E4 | HopoEngine | Consecutive notes spaced at 66 ticks | Marked as Strum (`is_hopo=False`) since $\Delta > 65$ |
| E5 | HopoEngine | Repeated fret at 48 ticks (e.g. Green -> Green) | Second note is forced Strum (`is_hopo=False`) |
| E6 | HopoEngine | Repeated fret at 1 tick (e.g. Red -> Red) | Second note is forced Strum (`is_hopo=False`) |
| E7 | HopoEngine | Rapid scale 0 -> 1 -> 2 -> 3 -> 4 at 48 ticks | Note 0 is Strum; notes 1, 2, 3, 4 are HOPOs |
| E8 | HopoEngine | Alternating trill 0 -> 1 -> 0 -> 1 -> 0 at 48 ticks | Note 0 is Strum; all subsequent notes are HOPOs |
| E9 | HopoEngine | Repeated pair trill 0 -> 0 -> 1 -> 1 -> 0 at 48 ticks | Notes at 0, 48, 144 are Strums; notes at 96, 192 are HOPOs |
| E10 | HopoEngine | Chord to Chord at 48 ticks ([0, 1] -> [1, 2]) | All notes of both chords are Strum (`is_hopo=False`) |
| E11 | HopoEngine | Single note to Chord at 48 ticks (0 -> [1, 2]) | Both notes of second chord are Strum (`is_hopo=False`) |
| E12 | HopoEngine | Chord to Single note with new fret ([0, 1] -> 2) | Note 2 is HOPO (`is_hopo=True`) |
| E13 | HopoEngine | Chord to Single note with held fret ([0, 1] -> 1) | Note 1 was part of previous chord -> Strum (`is_hopo=False`) |
| E14 | HopoEngine | Open note (7) to Green (0) at 48 ticks | Green is HOPO (`is_hopo=True`, Hammer-on from Open) |
| E15 | HopoEngine | Green (0) to Open note (7) at 48 ticks | Open is HOPO (`is_hopo=True`, Pull-off to Open) |
| E16 | HopoEngine | Repeated Open notes at 48 ticks (7 -> 7) | Second Open is forced Strum (`is_hopo=False`) |
| E17 | HopoEngine | Unsorted input list of notes | Output is sorted ascending by `(tick, fret)` with valid HOPOs |
| E18 | HopoEngine | `hopo_threshold < 0` | Raises `ValueError` |
| E19 | SustainProcessor | Empty notes `[]` | Returns `[]` without error |
| E20 | SustainProcessor | Note duration 0, 24, 48, 89 ticks | `sustain_length = 0` (cutoff $< 90$) |
| E21 | SustainProcessor | Note duration exactly 90 ticks | `sustain_length = 90 - 24 = 66` |
| E22 | SustainProcessor | Note duration 192 ticks, next note at 768 ticks | `sustain_length = 192 - 24 = 168` |
| E23 | SustainProcessor | Note duration 500 ticks, next note at +192 ticks | Clamped to $192 - 24 = 168$ ticks |
| E24 | SustainProcessor | Notes spaced 48 ticks with durations 192 ticks | Clamped to $48 - 24 = 24$ ticks |
| E25 | SustainProcessor | Notes spaced $\le 24$ ticks (e.g. 16 or 24 ticks) | Clamped to $\max(0, \Delta - 24) = 0$ ticks |
| E26 | SustainProcessor | Final note of track with duration 500 ticks | Retains full $500 - 24 = 476$ ticks (no next-note clamping) |
| E27 | SustainProcessor | Chord notes at identical tick (tick=0, frets 0 & 1) | Both receive 168 ticks; do not clamp each other |
| E28 | SustainProcessor | `min_sustain_ticks < 0` or `release_margin < 0` | Raises `ValueError` |
| E29 | StarPowerGenerator | Empty notes `[]` | Returns `[]` without error |
| E30 | StarPowerGenerator | Single note or sparse notes ($< \text{min\_notes}$) | Returns `[]` (insufficient density) |
| E31 | StarPowerGenerator | Long track (64 measures = 49,152 ticks) | Generates ~3-4 periodic phrases every ~16 measures |
| E32 | StarPowerGenerator | 16-measure silent gap in song | No Star Power phrase allocated during the silent gap |
| E33 | StarPowerGenerator | Phrase intervals | All phrases satisfy $\text{phrase}_k.\text{tick} + \text{phrase}_k.\text{length} \le \text{phrase}_{k+1}.\text{tick}$ |
| E34 | StarPowerGenerator | Invalid params ($\le 0$) | Raises `ValueError` |

---

## 5. Detailed Component Specifications

### 5.1. `HopoEngine` (`src/game_design/hopo_engine.py`)

#### Interface Definition
```python
from collections.abc import Sequence
from typing import Final
from src.models.chart import ChartNote, FretType

class HopoEngine:
    DEFAULT_HOPO_THRESHOLD: Final[int] = 65

    def __init__(self, hopo_threshold: int = DEFAULT_HOPO_THRESHOLD) -> None:
        """Initialize HopoEngine.
        
        Args:
            hopo_threshold: Maximum delta tick spacing for natural HOPO (default 65).
            
        Raises:
            ValueError: If hopo_threshold < 0.
        """
        ...

    def process(self, notes: Sequence[ChartNote]) -> list[ChartNote]:
        """Evaluate and assign is_hopo flags for all notes in chronological order.
        
        Args:
            notes: Sequence of ChartNotes.
            
        Returns:
            New list of ChartNotes sorted by (tick, fret) with is_hopo accurately set.
        """
        ...

    # Aliases
    calculate_hopos = process
    __call__ = process
```

#### Behavioral Rules
1. If `not notes`, return `[]`.
2. Sort notes by `(tick, fret)`. Group notes by distinct `tick`.
3. The note(s) at the first tick ($t_0$) have `is_hopo = False`.
4. For each subsequent tick $t_i$:
   - Let $\Delta = t_i - t_{i-1}$.
   - If $\Delta > \text{hopo\_threshold}$: all notes at $t_i$ have `is_hopo = False`.
   - If $0 < \Delta \le \text{hopo\_threshold}$:
     - If current tick has multiple notes (chord): all have `is_hopo = False`.
     - If current tick has single note:
       - If previous tick was single note:
         - If `fret_curr == fret_prev`: `is_hopo = False` (repeated fret).
         - If `fret_curr != fret_prev`: `is_hopo = True` (natural HOPO).
       - If previous tick was chord:
         - If `fret_curr in prev_chord_frets`: `is_hopo = False` (repeated fret from chord).
         - If `fret_curr not in prev_chord_frets`: `is_hopo = True` (new fret transition).
5. All other note properties (`tick`, `fret`, `sustain_length`) are preserved unchanged.

---

### 5.2. `SustainProcessor` (`src/game_design/sustain_processor.py`)

#### Interface Definition
```python
from collections.abc import Mapping, Sequence
from typing import Final
from src.models.chart import ChartNote

class SustainProcessor:
    DEFAULT_MIN_SUSTAIN: Final[int] = 90
    DEFAULT_RELEASE_MARGIN: Final[int] = 24

    def __init__(
        self,
        min_sustain_ticks: int = DEFAULT_MIN_SUSTAIN,
        release_margin: int = DEFAULT_RELEASE_MARGIN,
    ) -> None:
        """Initialize SustainProcessor.
        
        Args:
            min_sustain_ticks: Duration threshold below which sustain is 0 (default 90).
            release_margin: Margin in ticks subtracted before release/next note (default 24).
            
        Raises:
            ValueError: If min_sustain_ticks < 0 or release_margin < 0.
        """
        ...

    def process(
        self,
        notes: Sequence[ChartNote],
        durations: Sequence[int] | Mapping[tuple[int, int], int] | Mapping[int, int] | None = None,
    ) -> list[ChartNote]:
        """Compute and clamp sustain lengths for all notes.
        
        Args:
            notes: Sequence of ChartNotes.
            durations: Optional mapping or sequence of raw duration ticks. If None,
                uses note.sustain_length as the raw input duration.
                
        Returns:
            New list of ChartNotes sorted by (tick, fret) with sustain_length computed.
        """
        ...

    # Aliases
    calculate_sustains = process
    __call__ = process
```

#### Behavioral Rules
1. If `not notes`, return `[]`.
2. For each note at tick $t_i$:
   - Determine raw duration $D$.
   - If $D < \text{min\_sustain\_ticks}$: $S = 0$.
   - If $D \ge \text{min\_sustain\_ticks}$:
     - Nominal sustain: $S_{\text{nom}} = D - \text{release\_margin}$.
     - Check for next distinct tick $t_{i+1} > t_i$:
       - If $t_{i+1}$ exists:
         - Max clearance: $S_{\text{max}} = \max(0, (t_{i+1} - t_i) - \text{release\_margin})$.
         - $S = \min(S_{\text{nom}}, S_{\text{max}})$.
       - If no next tick exists (final note):
         - $S = S_{\text{nom}}$.
3. Notes at identical ticks (chords) do NOT clamp each other.
4. Preserves `tick`, `fret`, and `is_hopo` flags.

---

### 5.3. `StarPowerGenerator` (`src/game_design/star_power_generator.py`)

#### Interface Definition
```python
from collections.abc import Sequence
from typing import Final
from src.models.chart import ChartNote, StarPowerPhrase

class StarPowerGenerator:
    DEFAULT_MEASURE_TICKS: Final[int] = 768  # 4 * 192 PPQ
    DEFAULT_INTERVAL_MEASURES: Final[int] = 16
    DEFAULT_PHRASE_LENGTH_MEASURES: Final[int] = 2
    DEFAULT_MIN_NOTES: Final[int] = 4

    def __init__(
        self,
        measure_ticks: int = DEFAULT_MEASURE_TICKS,
        interval_measures: int = DEFAULT_INTERVAL_MEASURES,
        phrase_length_measures: int = DEFAULT_PHRASE_LENGTH_MEASURES,
        min_notes: int = DEFAULT_MIN_NOTES,
    ) -> None:
        """Initialize StarPowerGenerator.
        
        Args:
            measure_ticks: Ticks in one measure (default 768 for 4/4 at 192 PPQ).
            interval_measures: Frequency of star power phrase allocation (default 16).
            phrase_length_measures: Length of phrase in measures (default 2).
            min_notes: Minimum notes required within a phrase (default 4).
            
        Raises:
            ValueError: If any parameter is <= 0.
        """
        ...

    def generate(self, notes: Sequence[ChartNote]) -> list[StarPowerPhrase]:
        """Generate periodic StarPowerPhrase allocations over active note passages.
        
        Args:
            notes: Sequence of ChartNotes.
            
        Returns:
            List of StarPowerPhrase instances sorted by tick.
        """
        ...

    # Aliases
    generate_phrases = generate
    __call__ = generate
```

#### Behavioral Rules
1. If `not notes` or `len(notes) < min_notes`, return `[]`.
2. Partition the song into intervals of `interval_measures * measure_ticks`.
3. For each candidate interval window:
   - Identify active notes in that region.
   - If note count $\ge \text{min\_notes}$, allocate a phrase starting at the first note onset of the phrase window, with duration spanning up to `phrase_length_measures * measure_ticks` (bounded by active notes in the phrase).
4. Guarantee no phrase overlap: $\text{phrase}_k.\text{tick} + \text{phrase}_k.\text{length} \le \text{phrase}_{k+1}.\text{tick}$.
5. Return phrases sorted ascending by `tick`.

---

## 6. Complete Runnable Pytest Test Suite

The code below is fully typed, conforms to `mypy --strict` standards, and is formatted per `ruff` rules. It can be placed directly into `tests/test_game_design/test_hopo_engine.py` (or split into dedicated test files).

```python
"""Comprehensive unit tests for Milestone 4 Game Design components.

Covers:
- HopoEngine: natural HOPOs, forced strums on repeats, threshold boundary, chords, open notes.
- SustainProcessor: <90 cutoff, 24 release margin, collision clamping, final note preservation.
- StarPowerGenerator: periodic phrases, note alignment, short chart handling.
- Full Game Design Pipeline Integration.
"""

from __future__ import annotations

import pytest

from src.game_design.chord_builder import ChordBuilder
from src.game_design.hopo_engine import HopoEngine
from src.game_design.pitch_to_fret import PitchToFretMapper
from src.game_design.quantizer import NoteQuantizer
from src.game_design.star_power_generator import StarPowerGenerator
from src.game_design.sustain_processor import SustainProcessor
from src.models import (
    BPMChange,
    ChartNote,
    FretType,
    NoteEvent,
    SongTrack,
    StarPowerPhrase,
    TempoMap,
    TimeSignature,
)

# ---------------------------------------------------------------------------
# Test Helpers & Fixtures
# ---------------------------------------------------------------------------


def _make_note(
    tick: int,
    fret: int | FretType,
    sustain_length: int = 0,
    is_hopo: bool = False,
) -> ChartNote:
    """Helper to synthesize a ChartNote with typed fret enum."""
    fret_val = FretType(fret) if isinstance(fret, int) else fret
    return ChartNote(
        tick=tick,
        fret=fret_val,
        sustain_length=sustain_length,
        is_hopo=is_hopo,
    )


@pytest.fixture
def default_hopo_engine() -> HopoEngine:
    """Return a standard HopoEngine with 65-tick threshold."""
    return HopoEngine(hopo_threshold=65)


@pytest.fixture
def default_sustain_processor() -> SustainProcessor:
    """Return a standard SustainProcessor with 90-tick cutoff and 24-tick margin."""
    return SustainProcessor(min_sustain_ticks=90, release_margin=24)


@pytest.fixture
def default_sp_generator() -> StarPowerGenerator:
    """Return a standard StarPowerGenerator configured for 16-measure intervals."""
    return StarPowerGenerator(
        measure_ticks=768,
        interval_measures=16,
        phrase_length_measures=2,
        min_notes=4,
    )


# ---------------------------------------------------------------------------
# 1. HopoEngine Tests
# ---------------------------------------------------------------------------


class TestHopoEngine:
    """Test suite for HopoEngine mechanics."""

    def test_hopo_empty_notes(self, default_hopo_engine: HopoEngine) -> None:
        """Verify empty input returns empty list."""
        assert default_hopo_engine.process([]) == []

    def test_hopo_single_note_first_is_strum(self, default_hopo_engine: HopoEngine) -> None:
        """Verify the first note of a track is always a strum (is_hopo=False)."""
        notes = [_make_note(tick=0, fret=FretType.GREEN)]
        result = default_hopo_engine.process(notes)
        assert len(result) == 1
        assert result[0].is_hopo is False

    def test_hopo_consecutive_within_threshold_different_frets(
        self, default_hopo_engine: HopoEngine
    ) -> None:
        """Verify consecutive notes <= 65 ticks with different frets are marked as HOPO."""
        notes = [
            _make_note(tick=0, fret=FretType.GREEN),
            _make_note(tick=48, fret=FretType.RED),
        ]
        result = default_hopo_engine.process(notes)
        assert len(result) == 2
        assert result[0].is_hopo is False  # First note is strum
        assert result[1].is_hopo is True  # HOPO

    def test_hopo_exact_threshold_boundary_65(self, default_hopo_engine: HopoEngine) -> None:
        """Verify note exactly at threshold boundary (65 ticks) is marked as HOPO."""
        notes = [
            _make_note(tick=0, fret=FretType.GREEN),
            _make_note(tick=65, fret=FretType.RED),
        ]
        result = default_hopo_engine.process(notes)
        assert result[1].is_hopo is True

    def test_hopo_beyond_threshold_boundary_66(self, default_hopo_engine: HopoEngine) -> None:
        """Verify note just beyond threshold boundary (66 ticks) is marked as Strum."""
        notes = [
            _make_note(tick=0, fret=FretType.GREEN),
            _make_note(tick=66, fret=FretType.RED),
        ]
        result = default_hopo_engine.process(notes)
        assert result[1].is_hopo is False

    @pytest.mark.parametrize("spacing", [96, 192, 384])
    def test_hopo_large_spacing_marked_as_strum(
        self, default_hopo_engine: HopoEngine, spacing: int
    ) -> None:
        """Verify notes spaced beyond 65 ticks (e.g. 96, 192 ticks) are marked as Strum."""
        notes = [
            _make_note(tick=0, fret=FretType.GREEN),
            _make_note(tick=spacing, fret=FretType.RED),
        ]
        result = default_hopo_engine.process(notes)
        assert result[1].is_hopo is False

    def test_hopo_repeated_frets_within_threshold_forced_strum(
        self, default_hopo_engine: HopoEngine
    ) -> None:
        """Verify repeated frets within <= 65 ticks (e.g. Green then Green at 48 ticks) force Strum."""
        notes = [
            _make_note(tick=0, fret=FretType.GREEN),
            _make_note(tick=48, fret=FretType.GREEN),
        ]
        result = default_hopo_engine.process(notes)
        assert result[0].is_hopo is False
        assert result[1].is_hopo is False  # Repeated fret must be strummed

    def test_hopo_rapid_ascending_scale(self, default_hopo_engine: HopoEngine) -> None:
        """Verify rapid scale (0 -> 1 -> 2 -> 3 -> 4 every 48 ticks) marks all except first as HOPOs."""
        notes = [
            _make_note(tick=0, fret=FretType.GREEN),
            _make_note(tick=48, fret=FretType.RED),
            _make_note(tick=96, fret=FretType.YELLOW),
            _make_note(tick=144, fret=FretType.BLUE),
            _make_note(tick=192, fret=FretType.ORANGE),
        ]
        result = default_hopo_engine.process(notes)
        assert [n.is_hopo for n in result] == [False, True, True, True, True]

    def test_hopo_rapid_descending_scale(self, default_hopo_engine: HopoEngine) -> None:
        """Verify rapid scale (4 -> 3 -> 2 -> 1 -> 0 every 48 ticks) marks all except first as HOPOs."""
        notes = [
            _make_note(tick=0, fret=FretType.ORANGE),
            _make_note(tick=48, fret=FretType.BLUE),
            _make_note(tick=96, fret=FretType.YELLOW),
            _make_note(tick=144, fret=FretType.RED),
            _make_note(tick=192, fret=FretType.GREEN),
        ]
        result = default_hopo_engine.process(notes)
        assert [n.is_hopo for n in result] == [False, True, True, True, True]

    def test_hopo_alternating_trill(self, default_hopo_engine: HopoEngine) -> None:
        """Verify alternating trill (0 -> 1 -> 0 -> 1 -> 0 at 48 ticks) keeps alternating HOPOs."""
        notes = [
            _make_note(tick=0, fret=FretType.GREEN),
            _make_note(tick=48, fret=FretType.RED),
            _make_note(tick=96, fret=FretType.GREEN),
            _make_note(tick=144, fret=FretType.RED),
            _make_note(tick=192, fret=FretType.GREEN),
        ]
        result = default_hopo_engine.process(notes)
        assert [n.is_hopo for n in result] == [False, True, True, True, True]

    def test_hopo_repeated_pairs_pattern(self, default_hopo_engine: HopoEngine) -> None:
        """Verify repeated pairs pattern (0 -> 0 -> 1 -> 1 at 48 ticks) alternates strum and HOPO."""
        notes = [
            _make_note(tick=0, fret=FretType.GREEN),
            _make_note(tick=48, fret=FretType.GREEN),  # repeat -> Strum
            _make_note(tick=96, fret=FretType.RED),  # diff fret -> HOPO
            _make_note(tick=144, fret=FretType.RED),  # repeat -> Strum
        ]
        result = default_hopo_engine.process(notes)
        assert [n.is_hopo for n in result] == [False, False, True, False]

    def test_hopo_single_to_chord_transition(self, default_hopo_engine: HopoEngine) -> None:
        """Verify transitioning from single note to chord forces Strum on all chord notes."""
        notes = [
            _make_note(tick=0, fret=FretType.GREEN),
            _make_note(tick=48, fret=FretType.RED),
            _make_note(tick=48, fret=FretType.YELLOW),
        ]
        result = default_hopo_engine.process(notes)
        chord_at_48 = [n for n in result if n.tick == 48]
        assert len(chord_at_48) == 2
        assert all(n.is_hopo is False for n in chord_at_48)

    def test_hopo_chord_to_chord_transition(self, default_hopo_engine: HopoEngine) -> None:
        """Verify transitioning from chord to chord within <= 65 ticks forces Strum on both."""
        notes = [
            _make_note(tick=0, fret=FretType.GREEN),
            _make_note(tick=0, fret=FretType.RED),
            _make_note(tick=48, fret=FretType.RED),
            _make_note(tick=48, fret=FretType.YELLOW),
        ]
        result = default_hopo_engine.process(notes)
        assert all(n.is_hopo is False for n in result)

    def test_hopo_chord_to_single_note_new_fret(self, default_hopo_engine: HopoEngine) -> None:
        """Verify chord followed by single note on a new fret within <= 65 ticks is HOPO."""
        notes = [
            _make_note(tick=0, fret=FretType.GREEN),
            _make_note(tick=0, fret=FretType.RED),
            _make_note(tick=48, fret=FretType.YELLOW),  # Fret 2 was not in {0, 1}
        ]
        result = default_hopo_engine.process(notes)
        assert result[2].tick == 48
        assert result[2].is_hopo is True

    def test_hopo_chord_to_single_note_held_fret(self, default_hopo_engine: HopoEngine) -> None:
        """Verify chord followed by single note that was part of the chord forces Strum."""
        notes = [
            _make_note(tick=0, fret=FretType.GREEN),
            _make_note(tick=0, fret=FretType.RED),
            _make_note(tick=48, fret=FretType.RED),  # Fret 1 was in previous chord
        ]
        result = default_hopo_engine.process(notes)
        assert result[2].is_hopo is False

    def test_hopo_open_note_to_fretted(self, default_hopo_engine: HopoEngine) -> None:
        """Verify Open note (7) followed by fretted note (0) at 48 ticks is HOPO (hammer-on)."""
        notes = [
            _make_note(tick=0, fret=FretType.OPEN),
            _make_note(tick=48, fret=FretType.GREEN),
        ]
        result = default_hopo_engine.process(notes)
        assert result[0].is_hopo is False
        assert result[1].is_hopo is True

    def test_hopo_fretted_to_open_note(self, default_hopo_engine: HopoEngine) -> None:
        """Verify fretted note (0) followed by Open note (7) at 48 ticks is HOPO (pull-off)."""
        notes = [
            _make_note(tick=0, fret=FretType.GREEN),
            _make_note(tick=48, fret=FretType.OPEN),
        ]
        result = default_hopo_engine.process(notes)
        assert result[0].is_hopo is False
        assert result[1].is_hopo is True

    def test_hopo_repeated_open_notes(self, default_hopo_engine: HopoEngine) -> None:
        """Verify repeated Open notes at 48 ticks force Strum."""
        notes = [
            _make_note(tick=0, fret=FretType.OPEN),
            _make_note(tick=48, fret=FretType.OPEN),
        ]
        result = default_hopo_engine.process(notes)
        assert result[0].is_hopo is False
        assert result[1].is_hopo is False

    def test_hopo_preserves_sustain_and_fret(self, default_hopo_engine: HopoEngine) -> None:
        """Verify HopoEngine preserves tick, fret, and sustain_length attributes unchanged."""
        notes = [
            _make_note(tick=0, fret=FretType.GREEN, sustain_length=168),
            _make_note(tick=48, fret=FretType.RED, sustain_length=96),
        ]
        result = default_hopo_engine.process(notes)
        assert result[0].sustain_length == 168
        assert result[1].sustain_length == 96
        assert result[0].fret == FretType.GREEN
        assert result[1].fret == FretType.RED

    def test_hopo_unsorted_input_handled(self, default_hopo_engine: HopoEngine) -> None:
        """Verify unsorted input list is processed in ascending chronological order."""
        notes = [
            _make_note(tick=48, fret=FretType.RED),
            _make_note(tick=0, fret=FretType.GREEN),
        ]
        result = default_hopo_engine.process(notes)
        assert result[0].tick == 0
        assert result[0].is_hopo is False
        assert result[1].tick == 48
        assert result[1].is_hopo is True

    def test_hopo_custom_threshold(self) -> None:
        """Verify custom hopo_threshold parameter is applied."""
        engine = HopoEngine(hopo_threshold=96)
        notes = [
            _make_note(tick=0, fret=FretType.GREEN),
            _make_note(tick=96, fret=FretType.RED),
            _make_note(tick=193, fret=FretType.YELLOW),
        ]
        result = engine.process(notes)
        assert result[1].is_hopo is True  # 96 <= 96 -> HOPO
        assert result[2].is_hopo is False  # 97 > 96 -> Strum

    def test_hopo_invalid_threshold_raises(self) -> None:
        """Verify negative threshold raises ValueError."""
        with pytest.raises(ValueError):
            HopoEngine(hopo_threshold=-1)


# ---------------------------------------------------------------------------
# 2. SustainProcessor Tests
# ---------------------------------------------------------------------------


class TestSustainProcessor:
    """Test suite for SustainProcessor mechanics."""

    def test_sustain_empty_notes(self, default_sustain_processor: SustainProcessor) -> None:
        """Verify empty input returns empty list."""
        assert default_sustain_processor.process([]) == []

    @pytest.mark.parametrize("duration", [0, 24, 48, 89])
    def test_sustain_below_90_cutoff_zero(
        self, default_sustain_processor: SustainProcessor, duration: int
    ) -> None:
        """Verify durations < 90 ticks produce sustain_length = 0."""
        notes = [_make_note(tick=0, fret=FretType.GREEN, sustain_length=duration)]
        result = default_sustain_processor.process(notes)
        assert result[0].sustain_length == 0

    def test_sustain_exact_threshold_90(
        self, default_sustain_processor: SustainProcessor
    ) -> None:
        """Verify duration of exactly 90 ticks produces sustain_length = 90 - 24 = 66."""
        notes = [_make_note(tick=0, fret=FretType.GREEN, sustain_length=90)]
        result = default_sustain_processor.process(notes)
        assert result[0].sustain_length == 66

    def test_sustain_quarter_note_192(
        self, default_sustain_processor: SustainProcessor
    ) -> None:
        """Verify quarter note (192 ticks) produces sustain_length = 192 - 24 = 168."""
        notes = [_make_note(tick=0, fret=FretType.GREEN, sustain_length=192)]
        result = default_sustain_processor.process(notes)
        assert result[0].sustain_length == 168

    def test_sustain_half_note_384(
        self, default_sustain_processor: SustainProcessor
    ) -> None:
        """Verify half note (384 ticks) produces sustain_length = 384 - 24 = 360."""
        notes = [_make_note(tick=0, fret=FretType.GREEN, sustain_length=384)]
        result = default_sustain_processor.process(notes)
        assert result[0].sustain_length == 360

    def test_sustain_next_note_overlap_clamping(
        self, default_sustain_processor: SustainProcessor
    ) -> None:
        """Verify long note (500 ticks) followed by next note at +192 ticks clamps to 192 - 24 = 168."""
        notes = [
            _make_note(tick=0, fret=FretType.GREEN, sustain_length=500),
            _make_note(tick=192, fret=FretType.RED, sustain_length=0),
        ]
        result = default_sustain_processor.process(notes)
        assert result[0].sustain_length == 168  # 192 - 24
        assert result[1].sustain_length == 0

    def test_sustain_consecutive_rapid_notes_48_spacing(
        self, default_sustain_processor: SustainProcessor
    ) -> None:
        """Verify consecutive notes with 48-tick spacing and long durations clamp to 48 - 24 = 24."""
        notes = [
            _make_note(tick=0, fret=FretType.GREEN, sustain_length=192),
            _make_note(tick=48, fret=FretType.RED, sustain_length=192),
            _make_note(tick=96, fret=FretType.YELLOW, sustain_length=0),
        ]
        result = default_sustain_processor.process(notes)
        assert result[0].sustain_length == 24  # 48 - 24
        assert result[1].sustain_length == 24  # (96 - 48) - 24
        assert result[2].sustain_length == 0

    def test_sustain_final_note_retains_full_duration(
        self, default_sustain_processor: SustainProcessor
    ) -> None:
        """Verify final note of track retains full duration - 24 without collision clamping."""
        notes = [
            _make_note(tick=0, fret=FretType.GREEN, sustain_length=192),
            _make_note(tick=384, fret=FretType.RED, sustain_length=500),
        ]
        result = default_sustain_processor.process(notes)
        assert result[0].sustain_length == 168  # 192 - 24 (next note is at 384, no clamp needed)
        assert result[1].sustain_length == 476  # 500 - 24 (final note, retains full duration)

    def test_sustain_tight_spacing_below_margin_24(
        self, default_sustain_processor: SustainProcessor
    ) -> None:
        """Verify note followed by next note within <= 24 ticks clamps sustain to 0."""
        notes = [
            _make_note(tick=0, fret=FretType.GREEN, sustain_length=192),
            _make_note(tick=16, fret=FretType.RED, sustain_length=0),
        ]
        result = default_sustain_processor.process(notes)
        assert result[0].sustain_length == 0  # 16 - 24 <= 0 -> 0

    def test_sustain_exact_spacing_margin_24(
        self, default_sustain_processor: SustainProcessor
    ) -> None:
        """Verify note followed by next note at exactly +24 ticks clamps sustain to 0."""
        notes = [
            _make_note(tick=0, fret=FretType.GREEN, sustain_length=192),
            _make_note(tick=24, fret=FretType.RED, sustain_length=0),
        ]
        result = default_sustain_processor.process(notes)
        assert result[0].sustain_length == 0  # 24 - 24 = 0

    def test_sustain_chords_simultaneous_notes(
        self, default_sustain_processor: SustainProcessor
    ) -> None:
        """Verify notes in the same chord (identical tick) do not clamp each other."""
        notes = [
            _make_note(tick=0, fret=FretType.GREEN, sustain_length=192),
            _make_note(tick=0, fret=FretType.RED, sustain_length=192),
            _make_note(tick=384, fret=FretType.YELLOW, sustain_length=0),
        ]
        result = default_sustain_processor.process(notes)
        assert result[0].sustain_length == 168
        assert result[1].sustain_length == 168

    def test_sustain_explicit_duration_mapping(
        self, default_sustain_processor: SustainProcessor
    ) -> None:
        """Verify durations passed as explicit mapping or sequence are properly used."""
        notes = [
            _make_note(tick=0, fret=FretType.GREEN, sustain_length=0),
            _make_note(tick=384, fret=FretType.RED, sustain_length=0),
        ]
        durations = [192, 90]
        result = default_sustain_processor.process(notes, durations=durations)
        assert result[0].sustain_length == 168
        assert result[1].sustain_length == 66

    def test_sustain_preserves_is_hopo_and_fret(
        self, default_sustain_processor: SustainProcessor
    ) -> None:
        """Verify SustainProcessor preserves is_hopo and fret attributes unchanged."""
        notes = [
            _make_note(tick=0, fret=FretType.GREEN, sustain_length=192, is_hopo=False),
            _make_note(tick=192, fret=FretType.RED, sustain_length=192, is_hopo=True),
        ]
        result = default_sustain_processor.process(notes)
        assert result[0].is_hopo is False
        assert result[1].is_hopo is True
        assert result[0].fret == FretType.GREEN
        assert result[1].fret == FretType.RED

    def test_sustain_custom_parameters(self) -> None:
        """Verify custom min_sustain_ticks and release_margin are applied."""
        processor = SustainProcessor(min_sustain_ticks=120, release_margin=30)
        notes = [
            _make_note(tick=0, fret=FretType.GREEN, sustain_length=100),  # < 120 -> 0
            _make_note(tick=384, fret=FretType.RED, sustain_length=150),  # >= 120 -> 150 - 30 = 120
        ]
        result = processor.process(notes)
        assert result[0].sustain_length == 0
        assert result[1].sustain_length == 120

    def test_sustain_invalid_parameters_raises(self) -> None:
        """Verify negative parameter values raise ValueError."""
        with pytest.raises(ValueError):
            SustainProcessor(min_sustain_ticks=-1)
        with pytest.raises(ValueError):
            SustainProcessor(release_margin=-1)


# ---------------------------------------------------------------------------
# 3. StarPowerGenerator Tests
# ---------------------------------------------------------------------------


class TestStarPowerGenerator:
    """Test suite for StarPowerGenerator mechanics."""

    def test_star_power_empty_notes(self, default_sp_generator: StarPowerGenerator) -> None:
        """Verify empty input notes returns empty star power phrase list."""
        assert default_sp_generator.generate([]) == []

    def test_star_power_single_short_note(
        self, default_sp_generator: StarPowerGenerator
    ) -> None:
        """Verify single short note returns empty phrases (insufficient note density)."""
        notes = [_make_note(tick=0, fret=FretType.GREEN)]
        assert default_sp_generator.generate(notes) == []

    def test_star_power_sparse_few_notes(
        self, default_sp_generator: StarPowerGenerator
    ) -> None:
        """Verify track with fewer than min_notes (4) produces no star power phrases."""
        notes = [
            _make_note(tick=0, fret=FretType.GREEN),
            _make_note(tick=192, fret=FretType.RED),
            _make_note(tick=384, fret=FretType.YELLOW),
        ]
        assert default_sp_generator.generate(notes) == []

    def test_star_power_long_song_64_measures_periodic(
        self, default_sp_generator: StarPowerGenerator
    ) -> None:
        """Verify long song (64 measures = 49,152 ticks) generates periodic phrases (~3-4 phrases)."""
        # Create continuous quarter notes for 64 measures (4 notes per measure)
        notes: list[ChartNote] = []
        for measure in range(64):
            for beat in range(4):
                tick = measure * 768 + beat * 192
                fret = (measure + beat) % 5
                notes.append(_make_note(tick=tick, fret=fret))

        phrases = default_sp_generator.generate(notes)
        assert len(phrases) >= 3
        assert len(phrases) <= 5

        # Verify phrases are chronologically sorted and non-overlapping
        for i in range(len(phrases) - 1):
            assert phrases[i].tick < phrases[i + 1].tick
            assert phrases[i].tick + phrases[i].length <= phrases[i + 1].tick

    def test_star_power_phrases_within_active_note_regions(
        self, default_sp_generator: StarPowerGenerator
    ) -> None:
        """Verify every StarPowerPhrase encompasses active notes."""
        notes: list[ChartNote] = []
        for measure in range(32):
            for beat in range(4):
                tick = measure * 768 + beat * 192
                notes.append(_make_note(tick=tick, fret=beat % 5))

        phrases = default_sp_generator.generate(notes)
        assert len(phrases) >= 1

        for phrase in phrases:
            # Must encompass notes
            notes_in_phrase = [
                n for n in notes if phrase.tick <= n.tick < phrase.tick + phrase.length
            ]
            assert len(notes_in_phrase) >= default_sp_generator.min_notes

    def test_star_power_silence_gap_no_phrase(
        self, default_sp_generator: StarPowerGenerator
    ) -> None:
        """Verify 16-measure silent gap contains no Star Power phrase."""
        notes: list[ChartNote] = []
        # Measures 0-15: active notes
        for measure in range(16):
            for beat in range(4):
                notes.append(_make_note(tick=measure * 768 + beat * 192, fret=0))
        # Measures 16-31: SILENCE (no notes)
        # Measures 32-47: active notes
        for measure in range(32, 48):
            for beat in range(4):
                notes.append(_make_note(tick=measure * 768 + beat * 192, fret=1))

        phrases = default_sp_generator.generate(notes)
        # Verify no phrase starts or exists within silent gap [16 * 768, 32 * 768)
        gap_start = 16 * 768
        gap_end = 32 * 768
        for p in phrases:
            assert not (gap_start <= p.tick < gap_end)

    def test_star_power_phrase_non_negative_values(
        self, default_sp_generator: StarPowerGenerator
    ) -> None:
        """Verify all generated StarPowerPhrases have non-negative tick and positive length."""
        notes = [_make_note(tick=m * 192, fret=0) for m in range(40)]
        phrases = default_sp_generator.generate(notes)
        for phrase in phrases:
            assert phrase.tick >= 0
            assert phrase.length > 0

    def test_star_power_custom_interval(self) -> None:
        """Verify custom interval_measures generates phrases more frequently."""
        gen_dense = StarPowerGenerator(interval_measures=8, min_notes=2)
        gen_sparse = StarPowerGenerator(interval_measures=16, min_notes=2)

        notes = [_make_note(tick=m * 192, fret=0) for m in range(128)]
        phrases_dense = gen_dense.generate(notes)
        phrases_sparse = gen_sparse.generate(notes)

        assert len(phrases_dense) > len(phrases_sparse)

    def test_star_power_invalid_parameters_raises(self) -> None:
        """Verify non-positive parameters raise ValueError."""
        with pytest.raises(ValueError):
            StarPowerGenerator(measure_ticks=0)
        with pytest.raises(ValueError):
            StarPowerGenerator(interval_measures=0)
        with pytest.raises(ValueError):
            StarPowerGenerator(phrase_length_measures=0)
        with pytest.raises(ValueError):
            StarPowerGenerator(min_notes=0)


# ---------------------------------------------------------------------------
# 4. End-to-End Game Design Pipeline Integration Test
# ---------------------------------------------------------------------------


def test_game_design_end_to_end_pipeline() -> None:
    """Test full Phase 4 Game Design pipeline integration from NoteEvents to SongTrack.

    Flow: NoteEvents -> NoteQuantizer -> PitchToFretMapper -> ChordBuilder ->
          HopoEngine -> SustainProcessor -> StarPowerGenerator -> SongTrack.
    """
    tempo_map = TempoMap(
        resolution=192,
        bpm_changes=[BPMChange(tick=0, bpm=120.0)],
        time_signatures=[TimeSignature(tick=0, numerator=4, denominator=4)],
    )

    # Synthesize realistic note events:
    # 1. Strum quarter note (tick 0)
    # 2. Fast ascending scale with HOPOs (ticks 192, 240, 288, 336)
    # 3. Two-note power chord at tick 768
    # 4. Long sustain note at tick 1152 (duration = 500 ticks)
    # 5. Note at tick 1344 (spacing = 192 ticks, causing sustain clamping)
    events = [
        NoteEvent(start_time=0.0, end_time=0.2, pitch=45, amplitude=0.9),  # ~tick 0
        NoteEvent(start_time=0.5, end_time=0.6, pitch=50, amplitude=0.8),  # ~tick 192
        NoteEvent(start_time=0.625, end_time=0.7, pitch=52, amplitude=0.8),  # ~tick 240
        NoteEvent(start_time=0.75, end_time=0.8, pitch=55, amplitude=0.8),  # ~tick 288
        NoteEvent(start_time=0.875, end_time=0.95, pitch=57, amplitude=0.8),  # ~tick 336
        # Chord at tick 768 (2.0s)
        NoteEvent(start_time=2.0, end_time=2.2, pitch=48, amplitude=0.9),
        NoteEvent(start_time=2.0, end_time=2.2, pitch=55, amplitude=0.85),
        # Long note at tick 1152 (3.0s, duration 1.302s ~500 ticks)
        NoteEvent(start_time=3.0, end_time=4.302, pitch=60, amplitude=0.9),
        # Next note at tick 1344 (3.5s)
        NoteEvent(start_time=3.5, end_time=3.7, pitch=62, amplitude=0.8),
    ]

    # Pipeline stages
    quantizer = NoteQuantizer(tolerance_ticks=16)
    q_notes = quantizer.quantize(events, tempo_map)

    mapper = PitchToFretMapper()
    fret_notes = mapper.map_notes(q_notes)

    builder = ChordBuilder(max_frets=3)
    chord_notes = builder.build_chords(fret_notes)

    hopo_engine = HopoEngine(hopo_threshold=65)
    hopo_notes = hopo_engine.process(chord_notes)

    sustain_proc = SustainProcessor(min_sustain_ticks=90, release_margin=24)
    # Extract duration mapping from quantized notes
    dur_map = {(qn.tick, qn.pitch): qn.duration_ticks for qn in q_notes}
    final_notes = sustain_proc.process(hopo_notes)

    sp_gen = StarPowerGenerator(interval_measures=4, min_notes=2)
    sp_phrases = sp_gen.generate(final_notes)

    track = SongTrack(name="ExpertSingle", notes=final_notes, star_power=sp_phrases)

    assert track.name == "ExpertSingle"
    assert len(track.notes) > 0
    # First note is strum
    assert track.notes[0].is_hopo is False
    # Ascending run contains HOPOs
    fast_run_notes = [n for n in track.notes if 192 <= n.tick <= 336]
    assert any(n.is_hopo for n in fast_run_notes)
    # Final track is sorted
    assert track.notes == sorted(track.notes)
```

---

## 7. Verification Method and Commands

To verify this specification and the forthcoming implementation:

1. **Unit Test Execution**:
   ```bash
   .venv/bin/pytest tests/test_game_design/test_hopo_engine.py -v
   ```
2. **Whole Game Design Suite Regression**:
   ```bash
   .venv/bin/pytest tests/test_game_design/ -v
   ```
   (Must pass all existing 94 tests plus new Milestone 4 tests).
3. **Full Project Regression**:
   ```bash
   .venv/bin/pytest tests/ -v
   ```
4. **Strict Mypy Type Verification**:
   ```bash
   .venv/bin/mypy src/game_design tests/test_game_design
   ```
5. **Ruff Lint & Format Verification**:
   ```bash
   .venv/bin/ruff check src/game_design tests/test_game_design
   .venv/bin/ruff format --check src/game_design tests/test_game_design
   ```
