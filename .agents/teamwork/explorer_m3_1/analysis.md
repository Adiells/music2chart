# Milestone 3 Analysis: Polyphonic Cluster Simplification & Canonical Chord Preservation

## 1. Executive Summary

In Clone Hero chart generation (Phase 4, Milestone 3), `ChordBuilder` (`src/game_design/chord_builder.py`) sits between `PitchToFretMapper` and `HopoEngine`. It receives a chronological sequence of `ChartNote`s and groups concurrent notes at identical ticks into playable, ergonomic Clone Hero chords.

The physical constraints of Clone Hero guitar controllers and standard charting conventions mandate:
1. **Max Concurrent Frets ($\le 3$)**: Chords cannot have 4 or 5 notes. Human plastic guitar controllers have 5 fret buttons operated by 4 fingers, making $\ge 4$ simultaneous frets physically unplayable.
2. **Elimination of Unplayable (0, 4) Stretches**: Simultaneous pressing of Green (0) and Orange (4) spans 5 buttons. This is prohibited in AGENTS.md §7.3 and SCOPE.md R3.3.
3. **Preservation of Canonical Shapes**:
   - **Power Chords (2 frets)**: `(0, 1), (0, 2), (1, 2), (1, 3), (2, 3), (2, 4), (3, 4)`
   - **Triads (3 frets)**: `(0, 1, 2), (0, 2, 3), (1, 2, 3), (2, 3, 4)`
4. **Open Note Exclusivity**: Open strum (fret 7, purple bar) physically cannot coexist with fretted notes (0-4) at the same tick. If fretted notes are present, Open notes must be discarded. If only Open notes are present, deduplicate to a single Open note.

---

## 2. Canonical Chord Shape Catalog

### 2.1 Canonical Power Chords (Dyads, $k = 2$)
Clone Hero power chords consist of adjacent frets ($\Delta = 1$) or a single-skip fret ($\Delta = 2$):

| Chord Shape | Fret Names | Interval Span ($\Delta$) | Musical Meaning in Clone Hero |
|---|---|---|---|
| `(0, 1)` | Green + Red | 1 (adjacent) | Compact power chord / semitone/tone dyad on Green |
| `(0, 2)` | Green + Yellow | 2 (skip 1) | Standard classic 5th power chord on Green |
| `(1, 2)` | Red + Yellow | 1 (adjacent) | Compact power chord on Red |
| `(1, 3)` | Red + Blue | 2 (skip 1) | Standard classic 5th power chord on Red |
| `(2, 3)` | Yellow + Blue | 1 (adjacent) | Compact power chord on Yellow |
| `(2, 4)` | Yellow + Orange | 2 (skip 1) | Standard classic 5th power chord on Yellow |
| `(3, 4)` | Blue + Orange | 1 (adjacent) | Compact power chord on Blue |

**Disallowed 2-Note Pairs:**
- `(0, 4)`: **Strictly Prohibited** (span 4, unplayable stretch spanning all 5 buttons).
- `(0, 3)`: Span 3 (skip 2). Non-canonical wide dyad; should be simplified if strict power chords are enforced.
- `(1, 4)`: Span 3 (skip 2). Non-canonical wide dyad; should be simplified if strict power chords are enforced.

### 2.2 Canonical Triads ($k = 3$)
Clone Hero triads consist of compact 3-fret blocks or the classic root + 5th + octave power chord shape:

| Triad Shape | Fret Names | Structure | Musical Meaning |
|---|---|---|---|
| `(0, 1, 2)` | Green + Red + Yellow | Adjacent block (0, 1, 2) | Compact triad rooted at Green |
| `(0, 2, 3)` | Green + Yellow + Blue | Skip 1 + Adjacent (0, 2, 3) | Quintessential GH/CH Extended Power Chord (Root + 5th + Octave) |
| `(1, 2, 3)` | Red + Yellow + Blue | Adjacent block (1, 2, 3) | Compact triad rooted at Red |
| `(2, 3, 4)` | Yellow + Blue + Orange | Adjacent block (2, 3, 4) | Compact triad rooted at Yellow |
| `(1, 3, 4)`* | Red + Blue + Orange | Skip 1 + Adjacent (1, 3, 4) | Transposed Extended Power Chord on Red (*Extended Canonical Triad*) |

*Note: While PROMPTS.md 4.3 and the dispatch specifically enumerate `(0, 1, 2), (0, 2, 3), (1, 2, 3), (2, 3, 4)`, `(1, 3, 4)` is identical in shape to `(0, 2, 3)` shifted by +1 fret. The scoring system naturally handles both.*

---

## 3. Polyphonic Cluster Simplification Heuristics

When polyphonic sources (such as piano chords or full 6-string guitar strums) produce 4 or 5 concurrent frets at the same tick, `ChordBuilder` must reduce the cluster $F$ to $|C| \le \text{max\_frets}$ (default 3).

### 3.1 Why Naive Truncation Fails
- Truncating from the bottom (dropping lowest notes) loses the bass root note, confusing the harmonic anchor.
- Truncating from the top (dropping highest notes) loses the vocal or lead melody line.
- Random or arbitrary deletion can create unplayable `(0, 4)` stretches or non-canonical finger-breaking shapes.

### 3.2 Multi-Objective Heuristic Formulation
To determine the optimal subset $C \subset F$ of size $k = \min(|F|, \text{max\_frets})$, we employ a multi-objective scoring function:

$$\text{Score}(C) = W_{\text{canonical}} \cdot I_{\text{canonical}}(C) + W_{\text{root}} \cdot I_{\text{root}}(C) + W_{\text{power}} \cdot I_{\text{power}}(C) + W_{\text{melody}} \cdot I_{\text{melody}}(C) - W_{\text{span}} \cdot \text{span}(C)$$

#### Hard Disqualification Filter:
$$C \text{ is INVALID if } (0 \in C \land 4 \in C)$$

#### Scoring Components:
1. **Canonical Shape Bonus ($W_{\text{canonical}} = 1000$)**:
   - $I_{\text{canonical}}(C) = 1$ if $C \in \text{CANONICAL\_TRIADS}$ (for $k=3$) or $C \in \text{CANONICAL\_POWER\_CHORDS}$ (for $k=2$).
2. **Root Preservation Bonus ($W_{\text{root}} = 100$)**:
   - $I_{\text{root}}(C) = 1$ if $\min(F) \in C$.
   - Preserves the harmonic bass anchor.
3. **Power Voicing Bonus ($W_{\text{power}} = 20$)**:
   - $I_{\text{power}}(C) = 1$ if $C$ matches root + 5th + octave shape (e.g. `(0, 2, 3)` or `(0, 2)` or `(1, 3)`).
4. **Melody Preservation Bonus ($W_{\text{melody}} = 10$)**:
   - $I_{\text{melody}}(C) = 1$ if $\max(F) \in C$ (only when no stretch conflict with root).
5. **Span Compactness Penalty ($W_{\text{span}} = 1$)**:
   - $\text{span}(C) = \max(C) - \min(C)$. Penalizes unnecessary finger stretches.

---

## 4. Exhaustive Truth Table for Polyphonic Clusters

There are exactly 6 possible fret clusters with $\ge 4$ frets from $\{0, 1, 2, 3, 4\}$:

| Input Cluster $F$ | Size | Has (0, 4) Stretch? | Valid 3-Fret Candidates (No Stretch) | Canonical Candidates | Selected Optimal Triad $C$ | Rationale |
|---|---|---|---|---|---|---|
| `{0, 1, 2, 3, 4}` | 5 | Yes | (0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3), (1, 2, 4), (1, 3, 4), (2, 3, 4) | (0, 2, 3), (0, 1, 2), (1, 2, 3), (2, 3, 4) | **`(0, 2, 3)`** | Preserves root (0), matches canonical power triad (Root+5th+Octave), eliminates stretch. |
| `{0, 1, 2, 3}` | 4 | No | (0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3) | (0, 2, 3), (0, 1, 2), (1, 2, 3) | **`(0, 2, 3)`** | Preserves root (0) AND melody (3); matches canonical power triad shape. |
| `{0, 1, 2, 4}` | 4 | Yes | (0, 1, 2), (1, 2, 4) | (0, 1, 2) | **`(0, 1, 2)`** | Only canonical triad without (0, 4) stretch; anchors on root (0). |
| `{0, 2, 3, 4}` | 4 | Yes | (0, 2, 3), (2, 3, 4) | (0, 2, 3), (2, 3, 4) | **`(0, 2, 3)`** | Preserves root (0); matches canonical power triad shape. |
| `{1, 2, 3, 4}` | 4 | No | (1, 2, 3), (1, 2, 4), (1, 3, 4), (2, 3, 4) | (1, 2, 3), (2, 3, 4) | **`(1, 2, 3)`** | Preserves root (1); matches compact canonical triad. |
| `{0, 1, 3, 4}` | 4 | Yes | (0, 1, 3), (1, 3, 4) | (1, 3, 4)* or (0, 1) dyad | **`(1, 3, 4)`** / **`(0, 1)`** | Eliminates stretch. If (1, 3, 4) allowed -> (1, 3, 4). If strict 4 triads -> simplifies to root power chord (0, 1). |

---

## 5. Non-Canonical 2- and 3-Fret Simplification

### 5.1 Dyads with Forbidden (0, 4) Stretch
If input cluster is `{0, 4}`:
- Simultaneous 0 and 4 cannot be played.
- Eliminating stretch leaves candidates `{0}` and `{4}`.
- Root note `{0}` is retained as a single note `ChartNote(tick=tick, fret=FretType.GREEN)`.

### 5.2 Triads with Forbidden (0, 4) Stretch
- `{0, 2, 4}`: Disqualifies (0, 4). 2-note candidates are `(0, 2)` and `(2, 4)`. Both are canonical power chords. Anchoring on root selects `(0, 2)`.
- `{0, 1, 4}`: Disqualifies (0, 4). 2-note candidate `(0, 1)` is a canonical power chord. Selects `(0, 1)`.
- `{0, 3, 4}`: Disqualifies (0, 4). 2-note candidate `(3, 4)` is a canonical power chord. Selects `(3, 4)`.

---

## 6. Implementation Architecture & Data Flow

```
Input: list[ChartNote]
   │
   ▼
1. Chronological Tick Grouping: defaultdict(list)
   │
   ▼
2. For each tick:
   ├── Separate OPEN notes (fret 7) from Fretted notes (0-4)
   ├── Open Note Exclusivity:
   │   ├── If fretted notes present -> discard OPEN
   │   └── If only OPEN notes -> deduplicate to single OPEN note, preserve max(sustain)
   │
   ├── Deduplicate fretted notes at same tick:
   │   └── Unique frets F = sorted(set(n.fret.value))
   │
   ├── If |F| == 1:
   │   └── Single note -> ChartNote(tick, F[0], sustain)
   │
   ├── If 2 <= |F| <= max_frets:
   │   ├── Check for (0, 4) stretch
   │   │   ├── If no stretch and canonical -> preserve C = F
   │   │   └── If stretch exists -> simplify via heuristic
   │
   └── If |F| > max_frets (4 or 5 notes):
       └── Evaluate all subsets C of size min(|F|, max_frets)
           ├── Filter out any C with (0 in C and 4 in C)
           ├── Score candidates with Multi-Objective Function
           └── Select top-scoring candidate C
   │
   ▼
3. Reconstruct ChartNotes for chosen frets:
   ├── Map back to FretType
   ├── Preserve corresponding note sustain_length
   └── Sort all notes chronologically and by fret
   │
   ▼
Output: list[ChartNote]
```

---

## 7. Precise Worker Pseudo-Code

```python
"""Algorithmic pseudo-code for ChordBuilder in src/game_design/chord_builder.py."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
import itertools
from typing import Final

from src.models.chart import ChartNote, FretType

DEFAULT_MAX_FRETS: Final[int] = 3

CANONICAL_POWER_CHORDS: Final[tuple[tuple[int, int], ...]] = (
    (0, 1),
    (0, 2),
    (1, 2),
    (1, 3),
    (2, 3),
    (2, 4),
    (3, 4),
)

CANONICAL_TRIADS: Final[tuple[tuple[int, int, int], ...]] = (
    (0, 1, 2),
    (0, 2, 3),
    (1, 2, 3),
    (2, 3, 4),
)

EXTENDED_TRIADS: Final[tuple[tuple[int, int, int], ...]] = (
    *CANONICAL_TRIADS,
    (1, 3, 4),
)


class ChordBuilder:
    """Groups simultaneous notes into playable, ergonomic Clone Hero chords."""

    DEFAULT_MAX_FRETS: Final[int] = DEFAULT_MAX_FRETS
    CANONICAL_POWER_CHORDS: Final[tuple[tuple[int, int], ...]] = CANONICAL_POWER_CHORDS
    CANONICAL_TRIADS: Final[tuple[tuple[int, int, int], ...]] = CANONICAL_TRIADS

    def __init__(self, max_frets: int = DEFAULT_MAX_FRETS) -> None:
        if max_frets < 1 or max_frets > 5:
            raise ValueError(f"max_frets must be between 1 and 5, got {max_frets}")
        self.max_frets = max_frets

    @staticmethod
    def _score_candidate(
        candidate: tuple[int, ...],
        original_frets: list[int],
    ) -> float:
        """Score candidate chord subset according to game design heuristics."""
        # 1. Hard disqualification for unplayable (0, 4) stretch
        if 0 in candidate and 4 in candidate:
            return -1e9

        score = 0.0
        k = len(candidate)

        # 2. Canonical shape bonus
        if k == 3 and candidate in EXTENDED_TRIADS:
            score += 1000.0
        elif k == 2 and candidate in CANONICAL_POWER_CHORDS:
            score += 1000.0

        # 3. Root note preservation bonus
        min_fret = min(original_frets)
        if min_fret in candidate:
            score += 100.0

        # 4. Power chord voicing bonus (0, 2, 3) or (0, 2) or (1, 3)
        if candidate in ((0, 2, 3), (0, 2), (1, 3), (1, 3, 4)):
            score += 20.0

        # 5. Top melody note preservation bonus (if not in stretch conflict)
        max_fret = max(original_frets)
        if max_fret in candidate and not (0 in candidate and max_fret == 4):
            score += 10.0

        # 6. Ergonomic compactness (lower span preferred)
        span = max(candidate) - min(candidate)
        score -= float(span)

        return score

    def _simplify_cluster(self, frets: list[int]) -> tuple[int, ...]:
        """Simplify a cluster of frets to <= max_frets without stretches."""
        unique_frets = sorted(set(frets))
        n = len(unique_frets)

        # Single note
        if n == 1:
            return (unique_frets[0],)

        # If already <= max_frets and no (0, 4) stretch and canonical
        if n <= self.max_frets and not (0 in unique_frets and 4 in unique_frets):
            tup = tuple(unique_frets)
            if (n == 2 and tup in CANONICAL_POWER_CHORDS) or (n == 3 and tup in EXTENDED_TRIADS):
                return tup

        # Target size is min(n, max_frets)
        target_size = min(n, self.max_frets)

        # Try target_size down to 1
        best_candidate: tuple[int, ...] | None = None
        best_score = -1e9

        for size in range(target_size, 0, -1):
            candidates = list(itertools.combinations(unique_frets, size))
            for cand in candidates:
                s = self._score_candidate(cand, unique_frets)
                if s > best_score and s > -1e8:
                    best_score = s
                    best_candidate = cand

            if best_candidate is not None:
                return best_candidate

        # Fallback: root note
        return (unique_frets[0],)

    def build_chords(self, notes: Sequence[ChartNote]) -> list[ChartNote]:
        """Group and simplify notes into valid Clone Hero chords."""
        if not notes:
            return []

        # Group by tick
        tick_map: dict[int, list[ChartNote]] = defaultdict(list)
        for note in notes:
            tick_map[note.tick].append(note)

        result: list[ChartNote] = []

        for tick in sorted(tick_map.keys()):
            chord_notes = tick_map[tick]

            open_notes = [n for n in chord_notes if n.fret == FretType.OPEN]
            fretted_notes = [n for n in chord_notes if 0 <= n.fret.value <= 4]

            # Open Note Exclusivity
            if fretted_notes:
                # Fretted notes take priority; Open notes dropped
                sustain_by_fret: dict[int, int] = {}
                for n in fretted_notes:
                    fv = n.fret.value
                    sustain_by_fret[fv] = max(sustain_by_fret.get(fv, 0), n.sustain_length)

                chosen_frets = self._simplify_cluster(list(sustain_by_fret.keys()))

                for f in chosen_frets:
                    result.append(
                        ChartNote(
                            tick=tick,
                            fret=FretType(f),
                            sustain_length=sustain_by_fret.get(f, 0),
                            is_hopo=False,
                        )
                    )
            elif open_notes:
                # Isolated Open note: keep max sustain
                max_sus = max(n.sustain_length for n in open_notes)
                result.append(
                    ChartNote(
                        tick=tick,
                        fret=FretType.OPEN,
                        sustain_length=max_sus,
                        is_hopo=False,
                    )
                )

        result.sort()
        return result

    build = build_chords
    process = build_chords
```
