# Specification Report: Adaptive Pitch-to-Fret Projection (Milestone 2)

**Target Module**: `src/game_design/pitch_to_fret.py`  
**Target Test Suite**: `tests/test_game_design/test_pitch_to_fret.py`  
**Author**: `spec_miner_m2` (Specification Miner)  
**Date**: 2026-10-13  
**Status**: Completed  

---

## 1. Executive Summary

Milestone 2 implements the second stage of the Phase 4 Game Design pipeline for Clone Hero chart generation: **Adaptive Pitch-to-Fret Projection (`PitchToFretMapper`)**.
This module translates quantized acoustic events (`QuantizedNote` from Milestone 1) into ergonomically playable 5-fret Clone Hero note representations (`ChartNote`).

Key architectural requirements and game design behaviors:
1. **Dynamic Sliding-Window Tessitura (`window_ticks: int = 1536`)**:
   - Rather than static pitch-to-fret mapping, frets are allocated relative to the pitch distribution within a local temporal window (~2 measures at 192 PPQ = 1536 ticks).
   - High-register passages (e.g., solos with pitches 75 to 90) use the full 5-fret span organically across Green (0) to Orange (4), rather than clustering exclusively on Orange (4).
   - Low-register passages (pitches 42 to 58) similarly use the 5-fret span organically across 0 to 4.
2. **Sub-Bass Open Note Mapping (`open_threshold: int = 40`)**:
   - Extreme sub-bass notes (`pitch < 40`, e.g., low E1, low bass open strings) are projected directly to `FretType.OPEN` (7 / purple open strum bar).
   - Boundary condition: `pitch = 39` maps to `FretType.OPEN`, while `pitch = 40` maps to standard frets (0–4).
3. **Rapid Passage Jump Penalty (`rapid_interval: int = 48`, `max_jump: int = 3`)**:
   - In rapid melodic lines where consecutive notes occur within an interval of less than 48 ticks (`tick - prev_tick < 48`, i.e., faster than sixteenth notes), physical hand repositioning is ergonomically constrained.
   - Any raw leap exceeding 3 frets (`abs(fret - prev_fret) > 3`, e.g., Green 0 to Orange 4, leap of 4) is clamped to $\le 3$ frets (Green 0 leaps to at most Blue 3; Orange 4 drops to at most Red 1).
   - When interval is $\ge 48$ ticks, the player has sufficient transition time, and the leap is unconstrained.
   - Open notes (`FretType.OPEN = 7`) are played without fretting and are exempt from physical fret jump clamping.
4. **Ascending / Descending Scale Flow**:
   - Diatonic and chromatic scales transition smoothly between Green (0) and Orange (4).
5. **Polyphonic & Simultaneous Note Integrity**:
   - Multiple notes occurring at the same tick (chords) preserve identical tick timestamps, project lower pitches to lower frets and higher pitches to higher frets, and are sorted chronologically and by fret.

---

## 2. Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | R2.1 Sliding Window | Dynamic Tessitura Normalization | Maps relative pitch rank/percentiles in active window ($W=1536$ ticks) to frets 0–4 | `Sequence[QuantizedNote]` | `list[ChartNote]` with frets 0–4 | Flat pitch window maps to Green (0) without error | ORIGINAL_REQUEST §R2, AGENTS.md §7.2, PROMPTS.md 4.2 |
| 2 | R2.1 Sliding Window | High Solo Register Span | Solos in high register (pitches 75–90) use full 5-fret span organically rather than clustering on Orange (4) | High register notes in $[75, 90]$ | Notes spanning frets 0, 1, 2, 3, 4 | Never clusters only on Orange (4) | Dispatch Task 2, AGENTS.md §7.2, PROMPTS.md 4.2 |
| 3 | R2.1 Sliding Window | Low Riff Register Span | Low riffs (pitches 42–56) use full 5-fret span organically rather than clustering on Green (0) | Low register notes in $[42, 56]$ | Notes spanning frets 0 through 4 | Never clusters only on Green (0) | AGENTS.md §7.2 |
| 4 | R2.1 Sliding Window | Section Transition Tracking | Window shifts dynamically across multi-measure boundaries (e.g. verse to solo) | Notes across measures ($> 1536$ ticks) | Locally normalized frets per section | Smooth section adaptation | AGENTS.md §7.2, PROMPTS.md 4.2 |
| 5 | R2.1 Scale Flow | Ascending 5-Note Scale Flow | Diatonic/pentatonic 5-step ascending scale produces sequential Green -> Red -> Yellow -> Blue -> Orange | 5 ascending pitches | Frets `[0, 1, 2, 3, 4]` | Deterministic progression | Dispatch Task 1, PROMPTS.md 4.2 |
| 6 | R2.1 Scale Flow | Ascending Chromatic Scale Flow | 12-semitone chromatic scale produces monotonically non-decreasing frets from Green (0) to Orange (4) | Octave chromatic pitches | Monotonic frets $f_i \le f_{i+1}$ covering 0..4 | Smooth progression | Dispatch Task 1, PROMPTS.md 4.2 |
| 7 | R2.1 Scale Flow | Descending Scale Flow | Descending pitch sequence maps smoothly from Orange (4) down to Green (0) | Descending pitches | Frets `[4, 3, 2, 1, 0]` | Smooth progression | PROMPTS.md 4.2 |
| 8 | R2.2 Sub-Bass | Sub-Bass Open Note Mapping | Notes with pitch $< 40$ map to `FretType.OPEN` (7) | `QuantizedNote(pitch < 40)` | `ChartNote(fret=FretType.OPEN)` | Deterministic mapping to 7 | Dispatch Task 3, ORIGINAL_REQUEST §R2, SCOPE.md:76 |
| 9 | R2.2 Sub-Bass | Open Threshold Boundary | Boundary test: pitch 39 -> OPEN (7), pitch 40 -> standard fret (0–4) | Notes at pitches 39 and 40 | Frets 7 and 0 | Strict boundary at threshold | SCOPE.md:76 |
| 10 | R2.2 Sub-Bass | Configurable Open Threshold | Allows custom `open_threshold` (e.g. 45) | `open_threshold: int` parameter | Evaluates against custom threshold | Rejects negative threshold | SCOPE.md:75 |
| 11 | R2.3 Jump Penalty | Rapid Ascending Jump Clamping | In rapid interval ($< 48$ ticks), fret leap $> 3$ is clamped to $\text{prev} + 3$ | Consecutive notes with $\Delta t < 48$, $\Delta f > 3$ | Clamped fret $f = \text{prev} + 3$ (e.g. Blue 3) | Clamped to $\le 3$ frets | Dispatch Task 4, ORIGINAL_REQUEST §R2, SCOPE.md:77 |
| 12 | R2.3 Jump Penalty | Rapid Descending Jump Clamping | In rapid interval ($< 48$ ticks), fret drop $> 3$ is clamped to $\text{prev} - 3$ | Consecutive notes with $\Delta t < 48$, $\Delta f < -3$ | Clamped fret $f = \text{prev} - 3$ (e.g. Red 1) | Clamped to $\ge -3$ frets | Dispatch Task 4, ORIGINAL_REQUEST §R2, SCOPE.md:77 |
| 13 | R2.3 Jump Penalty | Interval Threshold Immunity ($\ge 48$) | When interval $\ge 48$ ticks, wide fret jumps (e.g. 0 to 4) are fully permitted without clamping | Consecutive notes with $\Delta t \ge 48$ | Unclamped raw frets (e.g. 0 then 4) | Full leap permitted | ORIGINAL_REQUEST §R2, SCOPE.md:77 |
| 14 | R2.3 Jump Penalty | Configurable Jump Parameters | Allows custom `max_jump` and `rapid_interval` parameters | Constructor parameters | Evaluates against custom thresholds | Rejects invalid parameters | SCOPE.md:75 |
| 15 | R2.3 Jump Penalty | Open Note Jump Immunity | Sub-bass open strums do not constrain subsequent fret positions | Open note followed by regular note | Unconstrained fret position | No clamping across open strum | AGENTS.md §7.2 |
| 16 | Edge Cases | Empty Input List | Handles empty input note list cleanly | `notes = []` | `[]` (empty list) | Graceful return, no exception | Dispatch Task 5 |
| 17 | Edge Cases | Single Note Mapping | Single note maps cleanly to Green (0) or Open (7) | Single `QuantizedNote` | 1 `ChartNote` | No ZeroDivisionError | Dispatch Task 5 |
| 18 | Edge Cases | Monophonic Repeating Pitch | Repeating identical pitch across time consistently maps to Green (0) | Identical pitches over time | All notes mapped to Green (0) | No division-by-zero or jump trigger | Dispatch Task 5 |
| 19 | Edge Cases | Polyphonic Chord at Same Tick | Simultaneous notes at same tick mapped to ordered frets, preserving tick | Multiple notes at same tick | Multiple `ChartNote`s at same tick | Ordered by tick then fret | Dispatch Task 5, SCOPE.md §Interface |
| 20 | Edge Cases | Sub-Bass Simultaneous Chord | Multiple sub-bass notes at same tick both map to `FretType.OPEN` | Pitches $< 40$ at same tick | Multiple Open notes at same tick | Handled cleanly | AGENTS.md §7.2 |
| 21 | Edge Cases | Chronological Sorting | Unsorted inputs are sorted chronologically by tick and fret | Scrambled input notes | Chronologically sorted output | Deterministic ordering | Clone Hero chart specification |
| 22 | Model Contract | Parameter Validation | Validates constructor arguments | Constructor parameters | Valid `PitchToFretMapper` | Raises `ValueError` on invalid values | Python robust design |
| 23 | Model Contract | `ChartNote` Invariants | Output notes have valid `FretType`, `sustain_length=0`, `is_hopo=False` | Mapped notes | Conformant `ChartNote`s | Valid dataclass instances | SCOPE.md:74 |

---

## 3. Edge Cases

| # | Feature | Input | Observed Behavior |
|---|---------|-------|-------------------|
| 1 | Sub-Bass Boundary | `pitch = 39` vs `pitch = 40` at `open_threshold = 40` | `pitch = 39` yields `FretType.OPEN` (7); `pitch = 40` yields `FretType.GREEN` (0). |
| 2 | Sub-Bass Chord | Two notes at tick 0 with pitches 36 and 38 | Both notes map to `FretType.OPEN` (7) at tick 0. |
| 3 | Single Note Input | Single `QuantizedNote(tick=0, pitch=60, duration_ticks=48, amplitude=0.8)` | Returns `[ChartNote(tick=0, fret=FretType.GREEN, sustain_length=0, is_hopo=False)]`. |
| 4 | Single Sub-Bass Note | Single `QuantizedNote(tick=0, pitch=32, duration_ticks=48, amplitude=0.8)` | Returns `[ChartNote(tick=0, fret=FretType.OPEN, sustain_length=0, is_hopo=False)]`. |
| 5 | Monophonic Repeating | 8 notes with identical pitch 64 spaced by 48 ticks | All 8 notes map to `FretType.GREEN` (0); denominator range is 0, handled cleanly without `ZeroDivisionError`. |
| 6 | Rapid Passage Jump Boundary | Two notes separated by exactly 47 ticks vs 48 ticks (with raw frets 0 and 4) | At 47 ticks ($< 48$), clamped to Blue (3). At 48 ticks ($\ge 48$), permitted at Orange (4). |
| 7 | Rapid Passage Leap Clamping | First note at Green (0), second note at tick 24 with raw target Orange (4) | Jump distance is $4 > 3$; clamped to $0 + 3 = 3$ (`FretType.BLUE`). |
| 8 | Rapid Passage Drop Clamping | First note at Orange (4), second note at tick 24 with raw target Green (0) | Drop distance is $-4 < -3$; clamped to $4 - 3 = 1$ (`FretType.RED`). |
| 9 | Rapid Jump Within Limit | First note at Green (0), second note at tick 24 with raw target Yellow (2) | Jump distance is $2 \le 3$; not clamped, stays at Yellow (2). |
| 10 | Open Note in Rapid Passage | Note at tick 0 (Green 0), note at tick 24 with sub-bass pitch 36 | Mapped directly to `FretType.OPEN` (7); not clamped by physical fret constraint. |
| 11 | Simultaneous Chord Notes | Tick 192 with pitches 60, 64, 67 (C major triad) | All 3 notes retained at tick 192; mapped to strictly increasing frets `[GREEN (0), YELLOW (2), ORANGE (4)]`. |
| 12 | Unsorted Input Ticks | Notes provided out-of-order in time (ticks 384, 0, 192) | Output strictly sorted: ticks 0, 192, 384. |
| 13 | Custom Parameters | Mapper with `max_jump = 2, rapid_interval = 96, open_threshold = 45` | Pitch 42 maps to OPEN; leap of 4 at interval 72 is clamped to 2 (Yellow). |
| 14 | Negative Constructor Args | `window_ticks <= 0`, `max_jump < 1`, `rapid_interval < 0`, or `open_threshold < 0` | Raises `ValueError` with descriptive message. |

---

## 4. Architectural & Mathematical Specifications

### 4.1. Sub-Bass Open Note Decision Rule
For each note $n$ with MIDI pitch $p$:
$$\text{fret}(n) = \begin{cases} \text{FretType.OPEN} \ (7), & \text{if } p < \text{open\_threshold} \\ \text{project\_fret}(n), & \text{if } p \ge \text{open\_threshold} \end{cases}$$
Default `open_threshold` is 40 (approx. E1, low E on a standard bass guitar).

### 4.2. Dynamic Sliding-Window Tessitura Algorithm
Let the sequence of notes sorted chronologically be $N = [n_1, n_2, \dots, n_k]$.
For each non-open note $n_i$ at tick $t_i$ with pitch $p_i \ge \text{open\_threshold}$:
1. Define the active temporal window:
   $$W_{\text{start}} = \max(0, t_i - \lfloor\text{window\_ticks} / 2\rfloor)$$
   $$W_{\text{end}} = t_i + \lfloor\text{window\_ticks} / 2\rfloor$$
2. Extract the set of active non-open pitches within the window:
   $$P_{\text{win}} = \{ n_j.\text{pitch} \mid n_j \in N, \ W_{\text{start}} \le n_j.\text{tick} \le W_{\text{end}}, \ n_j.\text{pitch} \ge \text{open\_threshold} \}$$
3. Compute the active tessitura bounds:
   $$p_{\min} = \min(P_{\text{win}}), \quad p_{\max} = \max(P_{\text{win}})$$
4. If $p_{\min} = p_{\max}$ (flat register or single pitch):
   $$\text{raw\_fret}(n_i) = \text{FretType.GREEN} \ (0)$$
5. Otherwise, normalize the pitch within the local tessitura:
   $$\text{ratio} = \frac{p_i - p_{\min}}{p_{\max} - p_{\min}}$$
   $$\text{raw\_fret}(n_i) = \min(4, \lfloor\text{ratio} \times 5\rfloor)$$
   This maps relative pitch continuously into five bins:
   - $[0.0, 0.2) \to 0$ (`FretType.GREEN`)
   - $[0.2, 0.4) \to 1$ (`FretType.RED`)
   - $[0.4, 0.6) \to 2$ (`FretType.YELLOW`)
   - $[0.6, 0.8) \to 3$ (`FretType.BLUE`)
   - $[0.8, 1.0] \to 4$ (`FretType.ORANGE`)

### 4.3. Rapid Passage Jump Penalty Algorithm
Physical hand ergonomics require limiting wide fret spans across rapid successive notes:
Let the previous non-open note have tick $t_{\text{prev}}$ and assigned fret $f_{\text{prev}} \in [0, 4]$.
For the current note at tick $t_i$ with raw fret $f_i^{\text{raw}} \in [0, 4]$:
1. If $t_i > t_{\text{prev}}$ and $t_i - t_{\text{prev}} < \text{rapid\_interval}$ (default 48 ticks):
   $$\Delta = f_i^{\text{raw}} - f_{\text{prev}}$$
   $$\text{clamped\_fret} = \begin{cases} f_{\text{prev}} + \text{max\_jump}, & \text{if } \Delta > \text{max\_jump} \\ f_{\text{prev}} - \text{max\_jump}, & \text{if } \Delta < -\text{max\_jump} \\ f_i^{\text{raw}}, & \text{otherwise} \end{cases}$$
   $$f_i = \max(0, \min(4, \text{clamped\_fret}))$$
2. Otherwise (interval $\ge \text{rapid\_interval}$ or first regular note):
   $$f_i = f_i^{\text{raw}}$$
3. Update previous note trackers: $t_{\text{prev}} = t_i$, $f_{\text{prev}} = f_i$.

---

## 5. Interface & Class Contracts

### 5.1. Module Location
`src/game_design/pitch_to_fret.py`

### 5.2. Class Definition
```python
from collections.abc import Sequence
from src.game_design.quantizer import QuantizedNote
from src.models.chart import ChartNote, FretType

class PitchToFretMapper:
    """Adaptive pitch-to-fret mapper for Clone Hero charts using sliding-window tessitura."""

    DEFAULT_WINDOW_TICKS: int = 1536       # 2 measures at 192 PPQ
    DEFAULT_MAX_JUMP: int = 3              # Maximum allowed fret jump in rapid lines
    DEFAULT_RAPID_INTERVAL: int = 48       # Interval threshold (< 48 ticks triggers clamping)
    DEFAULT_OPEN_THRESHOLD: int = 40       # MIDI pitch < 40 maps to FretType.OPEN (7)

    def __init__(
        self,
        window_ticks: int = DEFAULT_WINDOW_TICKS,
        max_jump: int = DEFAULT_MAX_JUMP,
        rapid_interval: int = DEFAULT_RAPID_INTERVAL,
        open_threshold: int = DEFAULT_OPEN_THRESHOLD,
    ) -> None:
        """Initialize PitchToFretMapper with ergonomic parameters."""
        ...

    def map_notes(self, notes: Sequence[QuantizedNote]) -> list[ChartNote]:
        """Project quantized musical notes to 5-fret ChartNotes.

        Args:
            notes: Sequence of QuantizedNotes.

        Returns:
            Chronologically and fret-sorted list of ChartNotes.
        """
        ...

    # Optional convenience alias
    map_pitch_to_frets = map_notes
```

---

## 6. Test Suite Plan for `tests/test_game_design/test_pitch_to_fret.py`

The test suite consists of **21 specialized, isolated test functions** covering all requirements from the dispatch assignment, `ORIGINAL_REQUEST.md`, `SCOPE.md`, `PROJECT.md`, `PROMPTS.md` Prompt 4.2, and `AGENTS.md` Section 7.2:

1. `test_sub_bass_open_note`: Validates sub-bass notes ($< 40$) map to `FretType.OPEN` (7) and note at 40 maps to non-open fret.
2. `test_sub_bass_custom_open_threshold`: Validates configurable `open_threshold` (e.g. 45).
3. `test_ascending_5_fret_scale`: Validates 5-note diatonic/pentatonic scale maps smoothly to `[0, 1, 2, 3, 4]`.
4. `test_ascending_chromatic_scale`: Validates chromatic scale spans all 5 frets with non-decreasing order ($f_i \le f_{i+1}$).
5. `test_descending_scale_flow`: Validates descending scale produces `[4, 3, 2, 1, 0]`.
6. `test_relative_tessitura_high_solo_passage`: Validates solo passage (pitches 75–90) utilizes full 5-fret span $\{0, 1, 2, 3, 4\}$ rather than clustering on Orange (4).
7. `test_relative_tessitura_low_riff_passage`: Validates low riff (pitches 42–56) utilizes full 5-fret span rather than clustering on Green (0).
8. `test_rapid_passage_jump_penalty_ascending`: Validates interval $< 48$ ticks clamps raw jump from 0 to 4 down to $\le 3$ (Blue 3).
9. `test_rapid_passage_jump_penalty_descending`: Validates interval $< 48$ ticks clamps raw drop from 4 to 0 up to $\ge 1$ (Red 1).
10. `test_jump_penalty_not_applied_at_or_above_48_ticks`: Validates interval $\ge 48$ ticks permits full 0 to 4 leap.
11. `test_jump_penalty_custom_parameters`: Validates custom `max_jump=2` and `rapid_interval=96`.
12. `test_jump_penalty_does_not_clamp_open_notes`: Validates sub-bass open note directly after a regular fret is not clamped to a fret button.
13. `test_empty_input_list`: Validates empty input returns `[]`.
14. `test_single_note_input`: Validates single note input maps without error.
15. `test_single_sub_bass_note`: Validates single sub-bass note returns `FretType.OPEN`.
16. `test_monophonic_repeating_pitch`: Validates 8 identical pitches consistently map to Green (0) without `ZeroDivisionError`.
17. `test_simultaneous_notes_chord_mapping`: Validates multiple notes at identical tick (triad) map to ordered frets, preserving tick.
18. `test_sub_bass_chord_mapping`: Validates multiple sub-bass notes at identical tick both map to `FretType.OPEN`.
19. `test_sliding_window_section_transitions`: Validates window shifts dynamically between low verse and high solo across song sections.
20. `test_unsorted_inputs_sorted_chronologically`: Validates unsorted input notes are chronologically sorted.
21. `test_mapper_invalid_parameters`: Validates constructor raises `ValueError` on non-positive window, max_jump $< 1$, or negative interval/threshold.

---

## 7. Complete Runnable Pytest Test Code

Below is the complete, strictly typed, ruff-compliant test code for `tests/test_game_design/test_pitch_to_fret.py`:

```python
"""Unit tests for adaptive pitch-to-fret mapping engine (PitchToFretMapper)."""

import pytest

from src.game_design.pitch_to_fret import PitchToFretMapper
from src.game_design.quantizer import QuantizedNote
from src.models import ChartNote, FretType


@pytest.fixture
def default_mapper() -> PitchToFretMapper:
    """Return a standard PitchToFretMapper with default parameters."""
    return PitchToFretMapper(
        window_ticks=1536,
        max_jump=3,
        rapid_interval=48,
        open_threshold=40,
    )


def _make_qnote(
    tick: int,
    pitch: int,
    duration_ticks: int = 48,
    amplitude: float = 0.8,
) -> QuantizedNote:
    """Synthesize a QuantizedNote helper."""
    return QuantizedNote(
        tick=tick,
        pitch=pitch,
        duration_ticks=duration_ticks,
        amplitude=amplitude,
    )


# ---------------------------------------------------------------------------
# 1. Sub-Bass Open Note Mapping
# ---------------------------------------------------------------------------


def test_sub_bass_open_note(default_mapper: PitchToFretMapper) -> None:
    """Verify pitches < 40 map to FretType.OPEN (7) and pitch >= 40 maps to regular fret."""
    notes = [
        _make_qnote(tick=0, pitch=28),  # E1 (< 40) -> OPEN
        _make_qnote(tick=96, pitch=36),  # C2 (< 40) -> OPEN
        _make_qnote(tick=192, pitch=39),  # D#2 (< 40) -> OPEN
        _make_qnote(tick=288, pitch=40),  # E2 (>= 40) -> GREEN (0)
    ]

    result = default_mapper.map_notes(notes)
    assert len(result) == 4
    assert [n.fret for n in result] == [
        FretType.OPEN,
        FretType.OPEN,
        FretType.OPEN,
        FretType.GREEN,
    ]


def test_sub_bass_custom_open_threshold() -> None:
    """Verify custom open_threshold parameter correctly partitions sub-bass notes."""
    mapper = PitchToFretMapper(open_threshold=45)
    notes = [
        _make_qnote(tick=0, pitch=42),  # 42 < 45 -> OPEN
        _make_qnote(tick=96, pitch=45),  # 45 >= 45 -> GREEN
    ]

    result = mapper.map_notes(notes)
    assert result[0].fret == FretType.OPEN
    assert result[1].fret == FretType.GREEN


# ---------------------------------------------------------------------------
# 2. Scale Flow Mapping (Ascending & Descending)
# ---------------------------------------------------------------------------


def test_ascending_5_fret_scale(default_mapper: PitchToFretMapper) -> None:
    """Verify a 5-step ascending scale produces sequential frets 0 -> 1 -> 2 -> 3 -> 4."""
    # Pitches: C4 (60), D4 (62), E4 (64), G4 (67), A4 (69)
    notes = [
        _make_qnote(tick=i * 96, pitch=p)
        for i, p in enumerate([60, 62, 64, 67, 69])
    ]

    result = default_mapper.map_notes(notes)
    assert len(result) == 5
    assert [n.fret for n in result] == [
        FretType.GREEN,
        FretType.RED,
        FretType.YELLOW,
        FretType.BLUE,
        FretType.ORANGE,
    ]


def test_ascending_chromatic_scale(default_mapper: PitchToFretMapper) -> None:
    """Verify an octave chromatic scale produces monotonically non-decreasing frets."""
    notes = [_make_qnote(tick=i * 96, pitch=60 + i) for i in range(12)]

    result = default_mapper.map_notes(notes)
    assert len(result) == 12

    # Frets must be non-decreasing
    for i in range(len(result) - 1):
        assert result[i].fret <= result[i + 1].fret

    # Must start at Green and end at Orange
    assert result[0].fret == FretType.GREEN
    assert result[-1].fret == FretType.ORANGE

    # Must span all 5 frets
    fret_set = {n.fret for n in result}
    assert fret_set == {
        FretType.GREEN,
        FretType.RED,
        FretType.YELLOW,
        FretType.BLUE,
        FretType.ORANGE,
    }


def test_descending_scale_flow(default_mapper: PitchToFretMapper) -> None:
    """Verify a descending scale produces sequential frets 4 -> 3 -> 2 -> 1 -> 0."""
    notes = [
        _make_qnote(tick=i * 96, pitch=p)
        for i, p in enumerate([69, 67, 64, 62, 60])
    ]

    result = default_mapper.map_notes(notes)
    assert [n.fret for n in result] == [
        FretType.ORANGE,
        FretType.BLUE,
        FretType.YELLOW,
        FretType.RED,
        FretType.GREEN,
    ]


# ---------------------------------------------------------------------------
# 3. Dynamic Sliding-Window Tessitura (Solos & Riffs)
# ---------------------------------------------------------------------------


def test_relative_tessitura_high_solo_passage(default_mapper: PitchToFretMapper) -> None:
    """Verify high register solo passages use the full 5-fret span rather than clustering on Orange."""
    # Solo high on guitar neck: pitches 75 to 90
    solo_pitches = [75, 77, 80, 82, 85, 87, 89, 90]
    notes = [_make_qnote(tick=i * 96, pitch=p) for i, p in enumerate(solo_pitches)]

    result = default_mapper.map_notes(notes)
    assert len(result) == len(solo_pitches)

    # Must NOT cluster only on Orange
    assert set(n.fret for n in result) != {FretType.ORANGE}

    # Must use full 5-fret span organically
    fret_set = {n.fret for n in result}
    assert fret_set == {
        FretType.GREEN,
        FretType.RED,
        FretType.YELLOW,
        FretType.BLUE,
        FretType.ORANGE,
    }

    # Lowest note in solo maps to Green, highest to Orange
    assert result[0].fret == FretType.GREEN
    assert result[-1].fret == FretType.ORANGE


def test_relative_tessitura_low_riff_passage(default_mapper: PitchToFretMapper) -> None:
    """Verify low register riff passages use the full 5-fret span rather than clustering on Green."""
    # Low riff: pitches 42 to 56 (all >= 40)
    riff_pitches = [42, 45, 48, 52, 56]
    notes = [_make_qnote(tick=i * 96, pitch=p) for i, p in enumerate(riff_pitches)]

    result = default_mapper.map_notes(notes)
    assert len(result) == len(riff_pitches)

    # Must NOT cluster only on Green
    assert set(n.fret for n in result) != {FretType.GREEN}

    # Must span all 5 frets
    assert set(n.fret for n in result) == {
        FretType.GREEN,
        FretType.RED,
        FretType.YELLOW,
        FretType.BLUE,
        FretType.ORANGE,
    }


def test_sliding_window_section_transitions(default_mapper: PitchToFretMapper) -> None:
    """Verify dynamic sliding window adjusts tessitura between verse and solo across measures."""
    # Verse (ticks 0..384): low pitches 48..56
    verse_notes = [_make_qnote(tick=i * 96, pitch=48 + i * 2) for i in range(5)]
    # Solo (ticks 3072..3456, well beyond window 1536): high pitches 76..88
    solo_notes = [_make_qnote(tick=3072 + i * 96, pitch=76 + i * 3) for i in range(5)]

    all_notes = verse_notes + solo_notes
    result = default_mapper.map_notes(all_notes)

    # Pitch 56 (top of verse) maps to Orange (4) in its local window
    verse_result = [n for n in result if n.tick < 1000]
    assert verse_result[-1].fret == FretType.ORANGE

    # Pitch 76 (bottom of solo) maps to Green (0) in its local window
    solo_result = [n for n in result if n.tick >= 3000]
    assert solo_result[0].fret == FretType.GREEN


# ---------------------------------------------------------------------------
# 4. Rapid Passage Jump Penalty
# ---------------------------------------------------------------------------


def test_rapid_passage_jump_penalty_ascending(default_mapper: PitchToFretMapper) -> None:
    """Verify interval < 48 ticks clamps raw jumps > 3 frets (Green 0 -> Orange 4 clamped to Blue 3)."""
    notes = [
        _make_qnote(tick=0, pitch=60),  # Maps to Green (0)
        _make_qnote(tick=24, pitch=72),  # Interval = 24 < 48; raw Orange (4) clamped to Blue (3)
    ]

    result = default_mapper.map_notes(notes)
    assert len(result) == 2
    assert result[0].fret == FretType.GREEN
    assert result[1].fret == FretType.BLUE


def test_rapid_passage_jump_penalty_descending(default_mapper: PitchToFretMapper) -> None:
    """Verify interval < 48 ticks clamps raw drops > 3 frets (Orange 4 -> Green 0 clamped to Red 1)."""
    notes = [
        _make_qnote(tick=0, pitch=72),  # Maps to Orange (4)
        _make_qnote(tick=24, pitch=60),  # Interval = 24 < 48; raw Green (0) clamped to Red (1)
    ]

    result = default_mapper.map_notes(notes)
    assert len(result) == 2
    assert result[0].fret == FretType.ORANGE
    assert result[1].fret == FretType.RED


def test_jump_penalty_not_applied_at_or_above_48_ticks(
    default_mapper: PitchToFretMapper,
) -> None:
    """Verify interval >= 48 ticks permits full 4-fret leap without clamping."""
    notes = [
        _make_qnote(tick=0, pitch=60),  # Green (0)
        _make_qnote(tick=48, pitch=72),  # Interval = 48 >= 48; permitted at Orange (4)
    ]

    result = default_mapper.map_notes(notes)
    assert len(result) == 2
    assert result[0].fret == FretType.GREEN
    assert result[1].fret == FretType.ORANGE


def test_jump_penalty_custom_parameters() -> None:
    """Verify custom max_jump=2 and rapid_interval=96 parameters clamp correctly."""
    mapper = PitchToFretMapper(max_jump=2, rapid_interval=96)
    notes = [
        _make_qnote(tick=0, pitch=60),  # Green (0)
        _make_qnote(tick=72, pitch=72),  # Interval = 72 < 96; clamped by max_jump=2 to Yellow (2)
    ]

    result = mapper.map_notes(notes)
    assert result[0].fret == FretType.GREEN
    assert result[1].fret == FretType.YELLOW


def test_jump_penalty_does_not_clamp_open_notes(default_mapper: PitchToFretMapper) -> None:
    """Verify sub-bass open notes are immune to physical fret jump penalty."""
    notes = [
        _make_qnote(tick=0, pitch=60),  # Green (0)
        _make_qnote(tick=24, pitch=36),  # Interval = 24 < 48, pitch < 40 -> OPEN (7)
    ]

    result = default_mapper.map_notes(notes)
    assert result[0].fret == FretType.GREEN
    assert result[1].fret == FretType.OPEN


# ---------------------------------------------------------------------------
# 5. Edge Cases & Robustness
# ---------------------------------------------------------------------------


def test_empty_input_list(default_mapper: PitchToFretMapper) -> None:
    """Verify empty note list returns an empty list without raising exceptions."""
    result = default_mapper.map_notes([])
    assert result == []


def test_single_note_input(default_mapper: PitchToFretMapper) -> None:
    """Verify single note maps cleanly to Green (0) without division-by-zero."""
    notes = [_make_qnote(tick=0, pitch=60)]
    result = default_mapper.map_notes(notes)
    assert len(result) == 1
    assert result[0] == ChartNote(tick=0, fret=FretType.GREEN, sustain_length=0, is_hopo=False)


def test_single_sub_bass_note(default_mapper: PitchToFretMapper) -> None:
    """Verify single sub-bass note maps to FretType.OPEN."""
    notes = [_make_qnote(tick=0, pitch=35)]
    result = default_mapper.map_notes(notes)
    assert len(result) == 1
    assert result[0] == ChartNote(tick=0, fret=FretType.OPEN, sustain_length=0, is_hopo=False)


def test_monophonic_repeating_pitch(default_mapper: PitchToFretMapper) -> None:
    """Verify constant repeating pitch maps consistently to Green without errors."""
    notes = [_make_qnote(tick=i * 48, pitch=64) for i in range(8)]
    result = default_mapper.map_notes(notes)
    assert len(result) == 8
    assert all(n.fret == FretType.GREEN for n in result)


def test_simultaneous_notes_chord_mapping(default_mapper: PitchToFretMapper) -> None:
    """Verify simultaneous notes at identical tick preserve tick and map to ordered frets."""
    # C major triad at tick 192: pitches 60, 64, 67
    notes = [
        _make_qnote(tick=192, pitch=60),
        _make_qnote(tick=192, pitch=64),
        _make_qnote(tick=192, pitch=67),
    ]

    result = default_mapper.map_notes(notes)
    assert len(result) == 3

    # All notes retain tick 192
    assert all(n.tick == 192 for n in result)

    # Frets must be ordered strictly increasing
    assert result[0].fret < result[1].fret < result[2].fret
    assert [n.fret for n in result] == [
        FretType.GREEN,
        FretType.YELLOW,
        FretType.ORANGE,
    ]


def test_sub_bass_chord_mapping(default_mapper: PitchToFretMapper) -> None:
    """Verify multiple simultaneous sub-bass notes all map to FretType.OPEN."""
    notes = [
        _make_qnote(tick=0, pitch=36),
        _make_qnote(tick=0, pitch=38),
    ]

    result = default_mapper.map_notes(notes)
    assert len(result) == 2
    assert all(n.fret == FretType.OPEN for n in result)


def test_unsorted_inputs_sorted_chronologically(default_mapper: PitchToFretMapper) -> None:
    """Verify out-of-order input notes are returned chronologically sorted."""
    notes = [
        _make_qnote(tick=384, pitch=64),
        _make_qnote(tick=0, pitch=60),
        _make_qnote(tick=192, pitch=62),
    ]

    result = default_mapper.map_notes(notes)
    assert [n.tick for n in result] == [0, 192, 384]


def test_mapper_invalid_parameters() -> None:
    """Verify constructor validates parameters and raises ValueError on invalid inputs."""
    with pytest.raises(ValueError, match="window_ticks"):
        PitchToFretMapper(window_ticks=0)
    with pytest.raises(ValueError, match="window_ticks"):
        PitchToFretMapper(window_ticks=-100)
    with pytest.raises(ValueError, match="max_jump"):
        PitchToFretMapper(max_jump=0)
    with pytest.raises(ValueError, match="rapid_interval"):
        PitchToFretMapper(rapid_interval=-1)
    with pytest.raises(ValueError, match="open_threshold"):
        PitchToFretMapper(open_threshold=-5)


def test_output_chart_note_invariants(default_mapper: PitchToFretMapper) -> None:
    """Verify all returned ChartNotes satisfy domain contract invariants."""
    notes = [
        _make_qnote(tick=0, pitch=35),
        _make_qnote(tick=96, pitch=60),
        _make_qnote(tick=192, pitch=72),
    ]

    result = default_mapper.map_notes(notes)
    for note in result:
        assert isinstance(note, ChartNote)
        assert note.tick >= 0
        assert isinstance(note.fret, FretType)
        assert note.sustain_length == 0
        assert note.is_hopo is False
```
