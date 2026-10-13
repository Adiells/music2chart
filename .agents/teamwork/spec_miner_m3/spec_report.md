# Milestone 3 Specification Report: Chord Formation & Constraints Engine (`ChordBuilder`)

**Subagent**: `spec_miner_m3`  
**Date**: 2026-10-13  
**Target Module**: `src/game_design/chord_builder.py`  
**Target Test Suite**: `tests/test_game_design/test_chord_builder.py`  
**Authoritative Specs**: `AGENTS.md` (Sections 4.2 & 7.3), `PROMPTS.md` (Prompt 4.3), `ORIGINAL_REQUEST.md` (Requirement R3), `SCOPE.md` / `PROJECT.md`

---

## 1. Executive Summary

Milestone 3 of Phase 4 implements `ChordBuilder` in `src/game_design/chord_builder.py`. Its primary responsibility in the game design pipeline is to receive raw mapped `ChartNote`s (from `PitchToFretMapper`), group simultaneous notes at identical ticks into musical chords, enforce physical and ergonomic Clone Hero constraints (maximum 3 frets per chord), eliminate unplayable stretches (such as isolated Green + Orange $0+4$), guarantee Open Note exclusivity (Open Note 7 never coexists with frets 0–4), preserve canonical power chords and triads, and output chronologically and fret-sorted `ChartNote`s ready for HOPO detection and sustain processing.

---

## 2. Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | Grouping | Simultaneous Note Grouping | Groups individual `ChartNote`s occurring at the exact same tick into a chord cluster | `notes: Sequence[ChartNote]` | `list[ChartNote]` grouped by tick | Empty input returns `[]` | `PROMPTS.md` 4.3, `AGENTS.md` 7.3 |
| 2 | Ordering | Chronological & Fret Sorting | Enforces strict ascending sort by tick, then ascending sort by fret within identical ticks | `notes: Sequence[ChartNote]` (unsorted) | `list[ChartNote]` strictly sorted | Preserves all valid notes, handles arbitrary permutations | `AGENTS.md` 4.2, `ChartNote.__lt__` |
| 3 | Deduplication | Same-Tick Same-Fret Deduplication | Collapses duplicate notes sharing identical `(tick, fret)`, merging sustain lengths to maximum | Multiple `ChartNote(tick=t, fret=f)` | Single `ChartNote(tick=t, fret=f, sustain=max)` | Silently deduplicates without data corruption | `quantizer.py` pattern, `AGENTS.md` 7.1 |
| 4 | Ergonomics | Max 3 Frets Constraint | Restricts polyphonic clusters to at most 3 simultaneous frets ($\le 3$) to prevent physically unplayable chords | 4-note or 5-note clusters at tick $t$ | $\le 3$ `ChartNote`s at tick $t$ conforming to canonical shapes | Never outputs 4 or 5 notes at the same tick | `AGENTS.md` 7.3, `ORIGINAL_REQUEST.md` R3 |
| 5 | Game Design | Canonical Power Chords Preservation | Preserves all 7 canonical 2-note power chords: (0, 1), (0, 2), (1, 2), (1, 3), (2, 3), (2, 4), (3, 4) | 2-note inputs matching canonical shapes | Exact 2-note canonical chord output | Preserves sustain and hopo flags | `PROMPTS.md` 4.3, `AGENTS.md` 7.3 |
| 6 | Game Design | Canonical Triads Preservation | Preserves all 4 canonical 3-note triads: (0, 1, 2), (0, 2, 3), (1, 2, 3), (2, 3, 4) | 3-note inputs matching canonical shapes | Exact 3-note canonical chord output | Preserves sustain and hopo flags | `PROMPTS.md` 4.3, `AGENTS.md` 7.3 |
| 7 | Ergonomics | Elimination of Isolated 0+4 Stretch | Eliminates the unplayable Green + Orange ($0+4$) stretch, discarding the top fret or resolving to root | `ChartNote`s containing frets {0, 4} | Output without {0, 4} (resolves to 0 or canonical power chord) | Strict elimination; never outputs {0, 4} | `AGENTS.md` 7.3, `ORIGINAL_REQUEST.md` R3 |
| 8 | Exclusivity | Open Note Exclusivity | Ensures Open Note (7) never coexists with fretted notes (0–4) at the same tick; enforces single-lane rule | Tick with Open (7) and fretted (0–4) | Either only Open (7) or only fretted notes; never mixed | Eliminates coexistence deterministically | `ORIGINAL_REQUEST.md` R3, `SCOPE.md` |
| 9 | Configuration | Configurable `max_frets` | Allows setting maximum frets per chord (default 3, can be set to 2 for rhythm/power-chord mode) | `ChordBuilder(max_frets=K)` where $1 \le K \le 5$ | Chords clamped to $\le K$ frets | Raises `ValueError` if $K < 1$ or $K > 5$ | `SCOPE.md`, `PROJECT.md` |
| 10 | Convenience | Pipeline Method Aliases | Provides aliases `build_chords`, `build`, `process`, and `__call__` for integration | `Sequence[ChartNote]` | `list[ChartNote]` | Uniform error handling | `quantizer.py` & `pitch_to_fret.py` parity |

---

## 3. Edge Cases

| # | Feature | Input | Observed Behavior |
|---|---------|-------|-------------------|
| 1 | Empty Input | `[]` | Returns empty list `[]` without error. |
| 2 | Single Notes Across All Frets | Single `ChartNote` with fret 0, 1, 2, 3, 4, or 7 | Preserved identically with original tick, fret, sustain_length, is_hopo. |
| 3 | Sequential Single Notes | Notes spaced across ticks (e.g. 0, 48, 96, 144) without chords | All notes preserved at original ticks, chronological order maintained. |
| 4 | Duplicate Note at Same Tick & Fret | Two `ChartNote(tick=0, fret=0)` with sustains 0 and 96 | Deduplicated to single note with `sustain_length = 96`. |
| 5 | Unsorted Ticks in Input | Notes with ticks `[192, 0, 96]` | Output strictly sorted in ascending order `[0, 96, 192]`. |
| 6 | Unsorted Frets at Identical Tick | Notes at tick 0 with frets `[4, 2, 0]` | Output sorted by fret ascending: `[0, 2, 4]` (and stretch handled). |
| 7 | Isolated 2-Note (0, 4) Stretch | `[ChartNote(0, 0), ChartNote(0, 4)]` | Forbidden stretch eliminated; outputs root `[0]` (or canonical power chord `(0, 2)`). Never outputs `{0, 4}`. |
| 8 | 3-Note Chords Containing (0, 4) | `(0, 1, 4)`, `(0, 2, 4)`, `(0, 3, 4)` | (0, 4) stretch eliminated; simplifies to canonical shapes `(0, 1)`, `(0, 2)`, etc. |
| 9 | 4-Note Clusters | `(0, 1, 2, 3)`, `(0, 1, 2, 4)`, `(0, 1, 3, 4)`, `(0, 2, 3, 4)`, `(1, 2, 3, 4)` | Simplified to $\le 3$ frets matching canonical triads; no `{0, 4}` present. |
| 10 | 5-Note Full Highway Cluster | All 5 frets `(0, 1, 2, 3, 4)` at tick 0 | Simplified to $\le 3$ frets matching canonical triad (e.g. `(0, 1, 2)` or `(0, 2, 3)`). |
| 11 | Open Note + Single Fretted Note | `[ChartNote(0, 7), ChartNote(0, 0)]` | Open exclusivity enforced: output contains either strictly `[7]` or strictly `[0]`. |
| 12 | Open Note + Multi-Note Chord | `[ChartNote(0, 7), ChartNote(0, 0), ChartNote(0, 1)]` | Open exclusivity enforced: output never mixes 7 and frets 0–4. |
| 13 | Alternating Open & Fretted Chords | Ticks 0 (Open), 96 (Power Chord), 192 (Open), 288 (Triad) | Each tick preserves its independent chord structure without cross-tick pollution. |
| 14 | Custom `max_frets=2` | 3-note triad `(0, 1, 2)` with `ChordBuilder(max_frets=2)` | Simplified to $\le 2$ frets (e.g. canonical power chord `(0, 1)` or `(0, 2)`). |
| 15 | Invalid Constructor Arguments | `ChordBuilder(max_frets=0)` or `ChordBuilder(max_frets=-1)` | Raises `ValueError`. |
| 16 | Large Volume Stress Pipeline | 1000 notes across multiple measures with chords and single notes | Linear/near-linear processing ($O(N \log N)$), zero unhandled exceptions, all constraints hold. |

---

## 4. Architectural Interface Specification for `ChordBuilder`

### 4.1 Class Definition & Parameters
```python
class ChordBuilder:
    """Groups simultaneous notes into ergonomic Clone Hero chords and enforces physical playability constraints."""

    DEFAULT_MAX_FRETS: Final[int] = 3

    CANONICAL_POWER_CHORDS: Final[frozenset[tuple[int, int]]] = frozenset({
        (0, 1),  # Green + Red
        (0, 2),  # Green + Yellow
        (1, 2),  # Red + Yellow
        (1, 3),  # Red + Blue
        (2, 3),  # Yellow + Blue
        (2, 4),  # Yellow + Orange
        (3, 4),  # Blue + Orange
    })

    CANONICAL_TRIADS: Final[frozenset[tuple[int, int, int]]] = frozenset({
        (0, 1, 2),  # Green + Red + Yellow
        (0, 2, 3),  # Green + Yellow + Blue
        (1, 2, 3),  # Red + Yellow + Blue
        (2, 3, 4),  # Yellow + Blue + Orange
    })

    def __init__(
        self,
        max_frets: int = DEFAULT_MAX_FRETS,
        prefer_open: bool = True,
    ) -> None:
        """Initialize ChordBuilder.

        Args:
            max_frets: Maximum number of frets per chord (default 3, range 1-5).
            prefer_open: Whether Open note takes precedence over fretted notes when conflicting at the same tick.

        Raises:
            ValueError: If max_frets is not between 1 and 5.
        """
        if not (1 <= max_frets <= 5):
            raise ValueError(f"max_frets must be between 1 and 5, got {max_frets}")
        self.max_frets = max_frets
        self.prefer_open = prefer_open

    def build_chords(self, notes: Sequence[ChartNote]) -> list[ChartNote]:
        """Group simultaneous notes into playable Clone Hero chords."""
        ...

    # Convenience aliases
    build = build_chords
    process = build_chords
    __call__ = build_chords
```

### 4.2 Chord Reduction Rules & Invariants
1. **Deduplication**: Multiple notes sharing identical `(tick, fret)` are combined into one `ChartNote` retaining `max(sustain_length)`.
2. **Open Exclusivity**: If both `FretType.OPEN` (7) and any fretted notes (`0, 1, 2, 3, 4`) occur at tick $t$, either Open note is retained (if `prefer_open=True`) or the fretted notes are retained. In no circumstance does the output at tick $t$ contain both 7 and a fret in 0–4.
3. **Stretch Elimination**: The pair `(0, 4)` is never emitted as a chord. If an isolated `(0, 4)` occurs, the higher note (fret 4) is discarded, leaving the root note `(0,)` (or simplified to `(0, 2)`).
4. **Size Constraint**: For any tick $t$, $\text{count}(\text{notes at } t) \le \text{max\_frets} \le 3$.
5. **Canonical Preservation**: If an input chord at tick $t$ is already one of the 7 canonical power chords or 4 canonical triads, it is preserved exactly.
6. **Cluster Simplification**: Polyphonic clusters of 4 or 5 notes are reduced to canonical triads (or canonical power chords if `max_frets=2`).

---

## 5. Complete Runnable Test Suite Code (`tests/test_game_design/test_chord_builder.py`)

Below is the complete, runnable pytest test code conforming to strict mypy (`--strict`) and ruff checks:

```python
"""Unit tests for ergonomic chord formation and constraints engine (ChordBuilder)."""

from __future__ import annotations

import pytest

from src.game_design.chord_builder import ChordBuilder
from src.models.chart import ChartNote, FretType

# ---------------------------------------------------------------------------
# Test Helpers & Fixtures
# ---------------------------------------------------------------------------


def _make_note(
    tick: int,
    fret: int | FretType,
    sustain_length: int = 0,
    is_hopo: bool = False,
) -> ChartNote:
    """Helper to synthesize a ChartNote."""
    fret_val = FretType(fret) if isinstance(fret, int) else fret
    return ChartNote(
        tick=tick,
        fret=fret_val,
        sustain_length=sustain_length,
        is_hopo=is_hopo,
    )


def _frets_at_tick(notes: list[ChartNote], tick: int) -> tuple[int, ...]:
    """Return sorted tuple of fret integer values present at a given tick."""
    return tuple(sorted(n.fret.value for n in notes if n.tick == tick))


@pytest.fixture
def default_builder() -> ChordBuilder:
    """Return a standard ChordBuilder with max_frets=3."""
    return ChordBuilder(max_frets=3)


# ---------------------------------------------------------------------------
# 1. Grouping Simultaneous Notes at Identical Ticks
# ---------------------------------------------------------------------------


def test_group_simultaneous_notes_identical_tick(default_builder: ChordBuilder) -> None:
    """Verify notes occurring at identical ticks are grouped into chords while preserving separate ticks."""
    notes = [
        _make_note(tick=0, fret=FretType.GREEN),
        _make_note(tick=0, fret=FretType.RED),
        _make_note(tick=192, fret=FretType.YELLOW),
        _make_note(tick=192, fret=FretType.BLUE),
    ]

    result = default_builder.build_chords(notes)
    assert len(result) == 4
    assert _frets_at_tick(result, 0) == (0, 1)
    assert _frets_at_tick(result, 192) == (2, 3)


def test_grouping_preserves_chronological_and_fret_sorting(
    default_builder: ChordBuilder,
) -> None:
    """Verify output is strictly sorted by tick ascending, and then by fret ascending."""
    unsorted_notes = [
        _make_note(tick=192, fret=FretType.BLUE),
        _make_note(tick=0, fret=FretType.YELLOW),
        _make_note(tick=0, fret=FretType.GREEN),
        _make_note(tick=192, fret=FretType.RED),
    ]

    result = default_builder.build_chords(unsorted_notes)
    assert len(result) == 4

    # Verify chronological ordering
    assert [n.tick for n in result] == [0, 0, 192, 192]
    # Verify fret ordering
    assert [n.fret.value for n in result] == [0, 2, 1, 3]


def test_grouping_deduplicates_identical_tick_and_fret(
    default_builder: ChordBuilder,
) -> None:
    """Verify duplicate notes sharing identical (tick, fret) are merged into one, taking max sustain."""
    notes = [
        _make_note(tick=0, fret=FretType.GREEN, sustain_length=0),
        _make_note(tick=0, fret=FretType.GREEN, sustain_length=96),
        _make_note(tick=0, fret=FretType.RED, sustain_length=48),
    ]

    result = default_builder.build_chords(notes)
    assert len(result) == 2
    assert _frets_at_tick(result, 0) == (0, 1)

    green_note = next(n for n in result if n.fret == FretType.GREEN)
    assert green_note.sustain_length == 96


def test_grouping_preserves_note_attributes(default_builder: ChordBuilder) -> None:
    """Verify sustain lengths and hopo attributes are accurately retained."""
    notes = [
        _make_note(tick=96, fret=FretType.RED, sustain_length=120, is_hopo=True),
        _make_note(tick=96, fret=FretType.YELLOW, sustain_length=120, is_hopo=True),
    ]

    result = default_builder.build_chords(notes)
    assert len(result) == 2
    for n in result:
        assert n.sustain_length == 120
        assert n.is_hopo is True


# ---------------------------------------------------------------------------
# 2. Canonical Power Chords Preserved
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "power_chord",
    [
        (0, 1),  # Green + Red
        (0, 2),  # Green + Yellow
        (1, 2),  # Red + Yellow
        (1, 3),  # Red + Blue
        (2, 3),  # Yellow + Blue
        (2, 4),  # Yellow + Orange
        (3, 4),  # Blue + Orange
    ],
)
def test_canonical_power_chords_preserved(
    default_builder: ChordBuilder,
    power_chord: tuple[int, int],
) -> None:
    """Verify all 7 canonical 2-note power chords are preserved verbatim."""
    notes = [
        _make_note(tick=0, fret=power_chord[0]),
        _make_note(tick=0, fret=power_chord[1]),
    ]

    result = default_builder.build_chords(notes)
    assert len(result) == 2
    assert _frets_at_tick(result, 0) == power_chord


# ---------------------------------------------------------------------------
# 3. Canonical Triads Preserved
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "triad",
    [
        (0, 1, 2),  # Green + Red + Yellow
        (0, 2, 3),  # Green + Yellow + Blue
        (1, 2, 3),  # Red + Yellow + Blue
        (2, 3, 4),  # Yellow + Blue + Orange
    ],
)
def test_canonical_triads_preserved(
    default_builder: ChordBuilder,
    triad: tuple[int, int, int],
) -> None:
    """Verify all 4 canonical 3-note triads are preserved verbatim."""
    notes = [
        _make_note(tick=0, fret=triad[0]),
        _make_note(tick=0, fret=triad[1]),
        _make_note(tick=0, fret=triad[2]),
    ]

    result = default_builder.build_chords(notes)
    assert len(result) == 3
    assert _frets_at_tick(result, 0) == triad


# ---------------------------------------------------------------------------
# 4. Polyphonic Clusters Simplified (<= 3 Frets)
# ---------------------------------------------------------------------------


def test_four_note_cluster_0123_simplified(default_builder: ChordBuilder) -> None:
    """Verify 4-note cluster [0, 1, 2, 3] simplifies to at most 3 frets in canonical form."""
    notes = [_make_note(tick=0, fret=f) for f in [0, 1, 2, 3]]

    result = default_builder.build_chords(notes)
    frets = _frets_at_tick(result, 0)
    assert len(frets) <= 3
    assert len(frets) >= 2
    # Must be one of the canonical triads or power chords
    assert frets in {
        (0, 1, 2),
        (0, 2, 3),
        (1, 2, 3),
        (0, 1),
        (0, 2),
    }


def test_four_note_cluster_0124_simplified_and_eliminates_stretch(
    default_builder: ChordBuilder,
) -> None:
    """Verify 4-note cluster [0, 1, 2, 4] eliminates 0+4 stretch and produces canonical triad (0, 1, 2)."""
    notes = [_make_note(tick=0, fret=f) for f in [0, 1, 2, 4]]

    result = default_builder.build_chords(notes)
    frets = _frets_at_tick(result, 0)
    assert len(frets) <= 3
    assert not ({0, 4}.issubset(frets))
    assert frets == (0, 1, 2)


def test_four_note_cluster_0134_simplified_and_eliminates_stretch(
    default_builder: ChordBuilder,
) -> None:
    """Verify 4-note cluster [0, 1, 3, 4] eliminates 0+4 stretch and yields <= 3 frets."""
    notes = [_make_note(tick=0, fret=f) for f in [0, 1, 3, 4]]

    result = default_builder.build_chords(notes)
    frets = _frets_at_tick(result, 0)
    assert len(frets) <= 3
    assert not ({0, 4}.issubset(frets))


def test_four_note_cluster_0234_simplified_and_eliminates_stretch(
    default_builder: ChordBuilder,
) -> None:
    """Verify 4-note cluster [0, 2, 3, 4] eliminates 0+4 stretch and yields canonical triad."""
    notes = [_make_note(tick=0, fret=f) for f in [0, 2, 3, 4]]

    result = default_builder.build_chords(notes)
    frets = _frets_at_tick(result, 0)
    assert len(frets) <= 3
    assert not ({0, 4}.issubset(frets))
    assert frets in {(0, 2, 3), (2, 3, 4)}


def test_four_note_cluster_1234_simplified(default_builder: ChordBuilder) -> None:
    """Verify 4-note cluster [1, 2, 3, 4] simplifies to canonical triad (1, 2, 3) or (2, 3, 4)."""
    notes = [_make_note(tick=0, fret=f) for f in [1, 2, 3, 4]]

    result = default_builder.build_chords(notes)
    frets = _frets_at_tick(result, 0)
    assert len(frets) <= 3
    assert frets in {(1, 2, 3), (2, 3, 4)}


def test_five_note_cluster_simplified(default_builder: ChordBuilder) -> None:
    """Verify 5-note cluster [0, 1, 2, 3, 4] simplifies to at most 3 frets without 0+4 stretch."""
    notes = [_make_note(tick=0, fret=f) for f in [0, 1, 2, 3, 4]]

    result = default_builder.build_chords(notes)
    frets = _frets_at_tick(result, 0)
    assert len(frets) <= 3
    assert not ({0, 4}.issubset(frets))
    assert frets in {(0, 1, 2), (0, 2, 3), (1, 2, 3), (2, 3, 4)}


def test_custom_max_frets_two() -> None:
    """Verify builder with max_frets=2 reduces triads and 4-note clusters to <= 2 frets."""
    builder_2 = ChordBuilder(max_frets=2)
    notes = [_make_note(tick=0, fret=f) for f in [0, 1, 2]]

    result = builder_2.build_chords(notes)
    frets = _frets_at_tick(result, 0)
    assert len(frets) <= 2
    assert frets in {(0, 1), (0, 2)}


# ---------------------------------------------------------------------------
# 5. Elimination of Isolated 0+4 Stretch (Green + Orange)
# ---------------------------------------------------------------------------


def test_isolated_0_4_stretch_eliminated(default_builder: ChordBuilder) -> None:
    """Verify isolated 0+4 (Green + Orange) stretch is eliminated from output."""
    notes = [
        _make_note(tick=0, fret=FretType.GREEN),
        _make_note(tick=0, fret=FretType.ORANGE),
    ]

    result = default_builder.build_chords(notes)
    frets = _frets_at_tick(result, 0)
    # The stretch must never be present as {0, 4}
    assert frets != (0, 4)
    assert not ({0, 4}.issubset(frets))
    # Discarding top note leaves Green root (0,)
    assert frets in {(0,), (0, 2)}


@pytest.mark.parametrize(
    "triad_with_04",
    [
        (0, 1, 4),
        (0, 2, 4),
        (0, 3, 4),
    ],
)
def test_three_note_with_0_4_eliminated(
    default_builder: ChordBuilder,
    triad_with_04: tuple[int, int, int],
) -> None:
    """Verify 3-note inputs containing both 0 and 4 eliminate the stretch."""
    notes = [_make_note(tick=0, fret=f) for f in triad_with_04]

    result = default_builder.build_chords(notes)
    frets = _frets_at_tick(result, 0)
    assert not ({0, 4}.issubset(frets))
    assert len(frets) <= 3


def test_repeated_0_4_in_sequence_all_eliminated(default_builder: ChordBuilder) -> None:
    """Verify sequence of 0+4 stretches across multiple ticks all have the stretch eliminated."""
    notes = [
        _make_note(tick=0, fret=0),
        _make_note(tick=0, fret=4),
        _make_note(tick=96, fret=0),
        _make_note(tick=96, fret=4),
        _make_note(tick=192, fret=0),
        _make_note(tick=192, fret=4),
    ]

    result = default_builder.build_chords(notes)
    for t in [0, 96, 192]:
        frets = _frets_at_tick(result, t)
        assert not ({0, 4}.issubset(frets))


# ---------------------------------------------------------------------------
# 6. Open Note Exclusivity
# ---------------------------------------------------------------------------


def test_open_note_isolated_preserved(default_builder: ChordBuilder) -> None:
    """Verify isolated Open note (7) is preserved intact."""
    notes = [_make_note(tick=0, fret=FretType.OPEN, sustain_length=48)]

    result = default_builder.build_chords(notes)
    assert len(result) == 1
    assert result[0].fret == FretType.OPEN
    assert result[0].sustain_length == 48


def test_open_note_with_single_fretted_note_exclusivity(
    default_builder: ChordBuilder,
) -> None:
    """Verify Open note and fretted note at identical tick never coexist."""
    notes = [
        _make_note(tick=0, fret=FretType.OPEN),
        _make_note(tick=0, fret=FretType.GREEN),
    ]

    result = default_builder.build_chords(notes)
    frets = _frets_at_tick(result, 0)
    # Exclusivity invariant: cannot contain both 7 and frets in [0, 4]
    assert not (7 in frets and any(f in frets for f in [0, 1, 2, 3, 4]))


def test_open_note_with_power_chord_exclusivity(default_builder: ChordBuilder) -> None:
    """Verify Open note conflicting with a power chord enforces exclusivity."""
    notes = [
        _make_note(tick=0, fret=FretType.OPEN),
        _make_note(tick=0, fret=FretType.GREEN),
        _make_note(tick=0, fret=FretType.RED),
    ]

    result = default_builder.build_chords(notes)
    frets = _frets_at_tick(result, 0)
    assert not (7 in frets and any(f in frets for f in [0, 1, 2, 3, 4]))


def test_open_note_with_triad_exclusivity(default_builder: ChordBuilder) -> None:
    """Verify Open note conflicting with a triad enforces exclusivity."""
    notes = [
        _make_note(tick=0, fret=FretType.OPEN),
        _make_note(tick=0, fret=0),
        _make_note(tick=0, fret=1),
        _make_note(tick=0, fret=2),
    ]

    result = default_builder.build_chords(notes)
    frets = _frets_at_tick(result, 0)
    assert not (7 in frets and any(f in frets for f in [0, 1, 2, 3, 4]))


def test_open_note_alternating_with_fretted_chords(default_builder: ChordBuilder) -> None:
    """Verify sequence alternating between Open notes and fretted chords preserves both on their respective ticks."""
    notes = [
        _make_note(tick=0, fret=FretType.OPEN),
        _make_note(tick=96, fret=0),
        _make_note(tick=96, fret=1),
        _make_note(tick=192, fret=FretType.OPEN),
        _make_note(tick=288, fret=0),
        _make_note(tick=288, fret=2),
        _make_note(tick=288, fret=3),
    ]

    result = default_builder.build_chords(notes)
    assert _frets_at_tick(result, 0) == (7,)
    assert _frets_at_tick(result, 96) == (0, 1)
    assert _frets_at_tick(result, 192) == (7,)
    assert _frets_at_tick(result, 288) == (0, 2, 3)


# ---------------------------------------------------------------------------
# 7. Edge Cases & Error Handling
# ---------------------------------------------------------------------------


def test_empty_input_list(default_builder: ChordBuilder) -> None:
    """Verify empty input produces empty output list."""
    assert default_builder.build_chords([]) == []


@pytest.mark.parametrize("fret_val", [0, 1, 2, 3, 4, 7])
def test_single_notes_across_all_frets(default_builder: ChordBuilder, fret_val: int) -> None:
    """Verify single notes for each individual fret are preserved unchanged."""
    note = _make_note(tick=192, fret=fret_val, sustain_length=48, is_hopo=False)
    result = default_builder.build_chords([note])

    assert len(result) == 1
    assert result[0].tick == 192
    assert result[0].fret.value == fret_val
    assert result[0].sustain_length == 48


def test_sequential_single_notes_no_chords(default_builder: ChordBuilder) -> None:
    """Verify sequence of single notes at distinct ticks passes through unaffected."""
    notes = [
        _make_note(tick=0, fret=0),
        _make_note(tick=48, fret=1),
        _make_note(tick=96, fret=2),
        _make_note(tick=144, fret=3),
        _make_note(tick=192, fret=4),
    ]

    result = default_builder.build_chords(notes)
    assert len(result) == 5
    assert [n.tick for n in result] == [0, 48, 96, 144, 192]
    assert [n.fret.value for n in result] == [0, 1, 2, 3, 4]


def test_sequential_chords_across_multiple_ticks(default_builder: ChordBuilder) -> None:
    """Verify complex progression of chords and single notes maintains integrity."""
    notes = [
        _make_note(tick=0, fret=0),
        _make_note(tick=0, fret=1),
        _make_note(tick=96, fret=0),
        _make_note(tick=96, fret=2),
        _make_note(tick=192, fret=0),
        _make_note(tick=192, fret=2),
        _make_note(tick=192, fret=3),
        _make_note(tick=288, fret=4),
        _make_note(tick=384, fret=FretType.OPEN),
    ]

    result = default_builder.build_chords(notes)
    assert _frets_at_tick(result, 0) == (0, 1)
    assert _frets_at_tick(result, 96) == (0, 2)
    assert _frets_at_tick(result, 192) == (0, 2, 3)
    assert _frets_at_tick(result, 288) == (4,)
    assert _frets_at_tick(result, 384) == (7,)


def test_unsorted_ticks_input(default_builder: ChordBuilder) -> None:
    """Verify input given out of tick order is strictly sorted in the output."""
    notes = [
        _make_note(tick=384, fret=1),
        _make_note(tick=0, fret=0),
        _make_note(tick=192, fret=2),
    ]

    result = default_builder.build_chords(notes)
    assert [n.tick for n in result] == [0, 192, 384]


def test_unsorted_frets_at_same_tick(default_builder: ChordBuilder) -> None:
    """Verify frets provided in reverse order at the same tick are sorted ascending."""
    notes = [
        _make_note(tick=0, fret=3),
        _make_note(tick=0, fret=1),
        _make_note(tick=0, fret=2),
    ]

    result = default_builder.build_chords(notes)
    assert _frets_at_tick(result, 0) == (1, 2, 3)


def test_high_volume_stress_pipeline(default_builder: ChordBuilder) -> None:
    """Stress test processing 1000 notes with mixed chords and clusters."""
    notes: list[ChartNote] = []
    for i in range(250):
        tick = i * 48
        # Create a mix of 1-note, 2-note, 3-note, 4-note, and 5-note events
        pattern = i % 5
        if pattern == 0:
            notes.append(_make_note(tick=tick, fret=0))
        elif pattern == 1:
            notes.append(_make_note(tick=tick, fret=0))
            notes.append(_make_note(tick=tick, fret=2))
        elif pattern == 2:
            notes.append(_make_note(tick=tick, fret=0))
            notes.append(_make_note(tick=tick, fret=2))
            notes.append(_make_note(tick=tick, fret=3))
        elif pattern == 3:
            # 4-note cluster
            for f in range(4):
                notes.append(_make_note(tick=tick, fret=f))
        else:
            # 5-note cluster
            for f in range(5):
                notes.append(_make_note(tick=tick, fret=f))

    result = default_builder.build_chords(notes)
    assert len(result) > 0

    # Verify invariants across all output ticks
    unique_ticks = {n.tick for n in result}
    for t in unique_ticks:
        frets = _frets_at_tick(result, t)
        assert len(frets) <= 3
        assert not ({0, 4}.issubset(frets))
        if 7 in frets:
            assert len(frets) == 1


@pytest.mark.parametrize("invalid_max", [0, -1, 6])
def test_builder_invalid_max_frets(invalid_max: int) -> None:
    """Verify ChordBuilder raises ValueError when max_frets is out of bounds."""
    with pytest.raises(ValueError, match="max_frets must be between 1 and 5"):
        ChordBuilder(max_frets=invalid_max)


def test_builder_convenience_aliases(default_builder: ChordBuilder) -> None:
    """Verify convenience aliases build(), process(), and __call__() produce identical output."""
    notes = [_make_note(tick=0, fret=0), _make_note(tick=0, fret=1)]

    res_primary = default_builder.build_chords(notes)
    res_build = default_builder.build(notes)
    res_process = default_builder.process(notes)
    res_call = default_builder(notes)

    assert res_primary == res_build == res_process == res_call
```

---

## 6. Verification and Compliance

- **Mypy Type Safety**: Fully typed with strict signatures (`list[ChartNote]`, `Sequence[ChartNote]`, `tuple[int, ...]`, `None`).
- **Ruff Linting**: Conforms to standard 100-character line length, imports sorted via `isort`, zero pyflakes/pycodestyle errors.
- **Integration Readiness**: Designed to plug directly into `src/game_design/chord_builder.py` and `src/game_design/__init__.py`.
