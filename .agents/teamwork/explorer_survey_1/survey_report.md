# Phase 4 Specification & Data Contracts Survey Report
**Game Design and Note Mapping Engine (Clone Hero)**

- **Subagent**: `explorer_survey_1`
- **Working Directory**: `/home/adiel/Projects/music2chart/.agents/teamwork/explorer_survey_1`
- **Target Subsystem**: `src/game_design/` and `tests/test_game_design/`
- **Timestamp**: 2026-10-13T18:46:00Z

---

## 1. Executive Summary

This report establishes the complete architectural specifications, mathematical formulations, algorithmic requirements, and strict Python typing contracts for **Phase 4 (Game Design & Note Mapping Engine)** of `chartgen`.

Phase 4 bridges raw polyphonic audio/MIDI transcription events (`NoteEvent`) with playable, ergonomic Clone Hero charts (`ChartNote`), translating raw physical sound into intuitive rhythm game mechanics.

### Core Requirements Matrix
| Requirement | Subsystem / Module | Primary Class | Key Algorithmic Mechanics |
|---|---|---|---|
| **R1** | `src/game_design/quantizer.py` | `NoteQuantizer` | Snapping to 192 PPQ grid (1/4, 1/8, 1/12, 1/16, 1/24, 1/32) with 16-tick tolerance; deduplication with amplitude merging. |
| **R2** | `src/game_design/pitch_to_fret.py` | `PitchToFretMapper` | Adaptive sliding tessitura window (2–4 measures); percentile projection to frets 0–4; Open Note (7) below MIDI 40; jump penalty (>3 frets at <48 ticks). |
| **R3** | `src/game_design/chord_builder.py` | `ChordBuilder` | Cluster simplification to $\le 3$ concurrent frets; canonical power chords & triads; forbidden stretch (0+4) elimination; open note exclusivity. |
| **R4** | `src/game_design/hopo_engine.py`<br>`src/game_design/sustain_processor.py`<br>`src/game_design/star_power_generator.py` | `HopoEngine`<br>`SustainProcessor`<br>`StarPowerGenerator` | HOPO marking ($\le 65$ ticks with fret change; force strum on repeats); sustain cut (<90 ticks $\to 0$; 24-tick release margin & collision clamp); periodic Star Power phrases. |

---

## 2. Upstream Data Models & Type Contracts (`src/models/`)

The following domain models already exist, are validated, and provide the foundational contracts:

### 2.1 `NoteEvent` (`src/models/midi_events.py`)
```python
@dataclass(frozen=True)
class NoteEvent:
    start_time: float   # Seconds, >= 0.0
    end_time: float     # Seconds, strictly > start_time
    pitch: int          # MIDI note number (0 - 127)
    amplitude: float    # Normalized velocity / confidence (0.0 to 1.0)
    
    @property
    def duration(self) -> float: ...
```

### 2.2 `TempoMap`, `BPMChange`, `TimeSignature` (`src/models/tempo.py`)
```python
@dataclass(frozen=True)
class BPMChange:
    tick: int           # Grid position (PPQ) >= 0
    bpm: float          # Strictly > 0.0

@dataclass(frozen=True)
class TimeSignature:
    tick: int           # Grid position >= 0
    numerator: int = 4  # > 0
    denominator: int = 4 # > 0

@dataclass
class TempoMap:
    resolution: int = 192   # PPQ resolution (standard: 192)
    bpm_changes: list[BPMChange] = field(default_factory=list)
    time_signatures: list[TimeSignature] = field(default_factory=list)

    def tick_to_seconds(self, tick: int) -> float: ...
    def seconds_to_tick(self, seconds: float) -> int: ...
```

### 2.3 `FretType`, `ChartNote`, `StarPowerPhrase`, `SongTrack` (`src/models/chart.py`)
```python
class FretType(IntEnum):
    GREEN = 0        # Lowest pitch fret
    RED = 1          # Mid-low fret
    YELLOW = 2       # Mid fret
    BLUE = 3         # Mid-high fret
    ORANGE = 4       # Highest pitch fret
    HOPO_FORCE = 5   # Modifier note: Force HOPO
    STRUM_FORCE = 6  # Modifier note: Force Strum
    OPEN = 7         # Open Strum (purple bar, sub-bass)

@dataclass
class ChartNote:
    tick: int
    fret: FretType
    sustain_length: int = 0
    is_hopo: bool = False

@dataclass(frozen=True)
class StarPowerPhrase:
    tick: int
    length: int  # Duration in ticks

@dataclass
class SongTrack:
    name: str    # e.g., "ExpertSingle"
    notes: list[ChartNote] = field(default_factory=list)
    star_power: list[StarPowerPhrase] = field(default_factory=list)
```

---

## 3. Requirement 1: Musical Quantization & Grid Snapping (`quantizer.py`)

### 3.1 Mathematical Formulation & Grid Subdivisions
Clone Hero charts standardize on **192 PPQ** (pulses/ticks per quarter note).
A full 4/4 measure contains $4 \times 192 = 768$ ticks.

The valid musical subdivisions and their step sizes are:
| Subdivision | Musical Value | Formula | Grid Step (Ticks) | Type |
|---|---|---|---|---|
| Half Note | $1/2$ | $192 \times 2$ | **384** | Straight |
| Quarter Note | $1/4$ | $192 \times 1$ | **192** | Straight |
| Eighth Note | $1/8$ | $192 / 2$ | **96** | Straight |
| Eighth Triplet | $1/12$ | $(192 \times 4) / 12$ | **64** | Triplet |
| Sixteenth Note | $1/16$ | $192 / 4$ | **48** | Straight |
| Sixteenth Triplet (Sextuplet) | $1/24$ | $(192 \times 4) / 24$ | **32** | Triplet |
| Thirty-Second Note | $1/32$ | $192 / 8$ | **24** | Straight |

#### Base Step Factoring:
Notice that:
- Every straight subdivision ($24, 48, 96, 192, 384$) is an integer multiple of **24**.
- Every triplet subdivision ($32, 64, 128$) is an integer multiple of **32**.
- Common multiples: $96$ ($4 \times 24 = 3 \times 32$), $192$ ($8 \times 24 = 6 \times 32$).

### 3.2 Snapping Algorithm
For any raw onset tick $T = \text{tempo\_map.seconds\_to\_tick}(\text{start\_time})$:
1. Candidate Straight Tick: $C_s = \operatorname{round}(T / 24) \times 24$.
2. Candidate Triplet Tick: $C_t = \operatorname{round}(T / 32) \times 32$.
3. Compute distance metrics: $\Delta_s = |T - C_s|$, $\Delta_t = |T - C_t|$.
4. Best Candidate $C^*$:
   - If $\Delta_s < \Delta_t$, $C^* = C_s$, $\Delta^* = \Delta_s$.
   - If $\Delta_t < \Delta_s$, $C^* = C_t$, $\Delta^* = \Delta_t$.
   - If $\Delta_s == \Delta_t$, break tie in favor of straight subdivision: $C^* = C_s$, $\Delta^* = \Delta_s$.
5. Tolerance Decision:
   - If $\Delta^* \le \text{tolerance\_ticks}$ (default `16`): snapped tick is $C^*$.
   - If $\Delta^* > \text{tolerance\_ticks}$: note remains at raw tick $T$ (or closest clamped point if strict grid mode is enabled).
6. Non-negativity: Snapped tick must be $\ge 0$.

### 3.3 Deduplication Algorithm
Multiple transcribed notes may snap to the exact same tick with the exact same pitch (e.g. transient noise or overlapping detections):
- Notes are partitioned by `(tick, pitch)`.
- If duplicates exist:
  - Preserved amplitude: $A_{\text{merged}} = \max(\{n.\text{amplitude}\})$.
  - Preserved duration: $D_{\text{merged}} = \max(\{n.\text{duration\_ticks}\})$.
- Output notes are strictly sorted by `(tick, pitch)`.

### 3.4 Data Contract
```python
@dataclass(frozen=True)
class QuantizedNote:
    """Note quantized onto the 192 PPQ musical grid."""
    tick: int
    pitch: int
    duration_ticks: int
    amplitude: float

class NoteQuantizer:
    VALID_SUBDIVISIONS: tuple[int, ...] = (192, 96, 64, 48, 32, 24)
    DEFAULT_TOLERANCE_TICKS: int = 16

    def __init__(self, resolution: int = 192, tolerance_ticks: int = 16) -> None:
        self.resolution = resolution
        self.tolerance_ticks = tolerance_ticks

    def snap_tick(self, raw_tick: int) -> int:
        """Snap a single raw tick to the closest valid subdivision within tolerance."""
        ...

    def quantize(
        self,
        notes: list[NoteEvent],
        tempo_map: TempoMap,
    ) -> list[QuantizedNote]:
        """Convert NoteEvents to ticks, snap onsets, compute durations, and deduplicate."""
        ...
```

---

## 4. Requirement 2: Adaptive Pitch-to-Fret Projection (`pitch_to_fret.py`)

### 4.1 Game Design Principles
In Clone Hero Expert difficulty, frets correspond to relative pitch heights:
- **Green (0)**: Lowest notes in passage
- **Red (1)**: Mid-low
- **Yellow (2)**: Mid
- **Blue (3)**: Mid-high
- **Orange (4)**: Highest notes in passage
- **Open (7)**: Extreme sub-bass / open string palm-mutes ($< \text{MIDI } 40$)

### 4.2 Dynamic Sliding Window Formulation
Static mapping (e.g. fixed MIDI $\to$ fret) fails on guitar solos: a solo played in octaves 5–6 would be pinned entirely to Orange (4).
Instead, an adaptive window spanning **2 to 4 measures** ($1536$ to $3072$ ticks) is used:
1. For each note at `tick`, gather all active note pitches in the temporal window $W = [\text{tick} - W_{\text{half}}, \text{tick} + W_{\text{half}}]$.
2. Compute pitch quantiles across active unique pitches in $W$:
   - Min ($p_0$), 25th percentile ($p_{25}$), Median ($p_{50}$), 75th percentile ($p_{75}$), Max ($p_{100}$).
3. Initial Fret Assignment:
   - If pitch $< p_{25}$: `FretType.GREEN` (0)
   - If $p_{25} \le \text{pitch} < p_{50}$: `FretType.RED` (1)
   - If $p_{50} \le \text{pitch} < p_{75}$: `FretType.YELLOW` (2)
   - If $p_{75} \le \text{pitch} < p_{100}$: `FretType.BLUE` (3)
   - If $\text{pitch} \ge p_{100}$: `FretType.ORANGE` (4)
4. Monophonic Single Pitch: If all notes in window have the same pitch, map to base fret (e.g., Green 0 or Yellow 2).
5. Scale Preservation: In an ascending sequence (e.g. C-D-E-F-G), notes sort strictly into $0 \to 1 \to 2 \to 3 \to 4$.

### 4.3 Open Note (7) Rule
If `pitch < OPEN_NOTE_PITCH_THRESHOLD` (default MIDI 40, low E on standard guitar):
- Assign `FretType.OPEN` (7).
- Open notes do not participate in fret jump penalties since open strums are performed by releasing the fretboard.

### 4.4 Ergonomic Jump Penalty in Rapid Passages
Physical guitar controller constraints make large lateral hand movements impossible in sixteenth notes:
- Rapid Passage Threshold: $\Delta_{\text{tick}} = \text{tick}_{\text{curr}} - \text{tick}_{\text{prev}} < 48$ ticks.
- Maximum Allowed Jump: $\le 3$ frets (e.g., jumping from Green 0 to Orange 4 is a leap of 4 frets).
- Penalty Rule:
  If $\Delta_{\text{tick}} < 48$ and both notes are fretted (frets $0 \dots 4$):
  - If $\text{fret}_{\text{curr}} - \text{fret}_{\text{prev}} > 3$: clamp $\text{fret}_{\text{curr}} = \text{fret}_{\text{prev}} + 3$.
  - If $\text{fret}_{\text{prev}} - \text{fret}_{\text{curr}} > 3$: clamp $\text{fret}_{\text{curr}} = \text{fret}_{\text{prev}} - 3$.
  - Clamp result to range $[0, 4]$.

### 4.5 Data Contract
```python
class PitchToFretMapper:
    OPEN_NOTE_THRESHOLD: int = 40
    MAX_RAPID_JUMP: int = 3
    RAPID_PASSAGE_INTERVAL: int = 48
    DEFAULT_WINDOW_TICKS: int = 1536  # 2 measures at 4/4 (192 * 4 * 2)

    def __init__(
        self,
        window_ticks: int = 1536,
        max_jump: int = 3,
        rapid_interval: int = 48,
        open_threshold: int = 40,
    ) -> None:
        self.window_ticks = window_ticks
        self.max_jump = max_jump
        self.rapid_interval = rapid_interval
        self.open_threshold = open_threshold

    def map_notes(
        self,
        notes: list[QuantizedNote],
    ) -> list[ChartNote]:
        """Project QuantizedNotes into ChartNotes with frets 0-4 or 7."""
        ...
```

---

## 5. Requirement 3: Chord Builder & Ergonomic Constraints (`chord_builder.py`)

### 5.1 Clone Hero Fretboard Ergonomics
In Guitar Hero / Clone Hero:
- A player has 4 fingers on 5 fret buttons.
- Maximum playable chord width is **3 concurrent frets**.
- Chords of 4 or 5 notes are unplayable and strictly prohibited by the chart specification.
- Wide gaps such as Green + Orange (`0 + 4`) isolated without intermediate anchors are ergonomically awkward and prohibited in fast passages.

### 5.2 Canonical Chord Shapes
Canonical Clone Hero chords fall into standard shapes:
1. **Power Chords (2 frets)**:
   - Adjacent pairs (span 1): `(0, 1)`, `(1, 2)`, `(2, 3)`, `(3, 4)`
   - Skip-1 pairs (span 2): `(0, 2)`, `(1, 3)`, `(2, 4)`
2. **Canonical Triads (3 frets)**:
   - Contiguous: `(0, 1, 2)`, `(1, 2, 3)`, `(2, 3, 4)`
   - Root + Skip: `(0, 2, 3)`, `(0, 1, 3)`, `(1, 2, 4)`

### 5.3 Polyphonic Cluster Simplification Algorithm
When polyphonic audio contains 4 or more notes at the same tick:
1. Collect unique fret values at that tick: $F = \{n.\text{fret}\}$.
2. If $|F| \le 3$:
   - Check for forbidden stretch: if $F == \{0, 4\}$, simplify to an ergonomic pair (e.g. $\{0, 2\}$ or single $\{0\}$).
   - Retain cluster.
3. If $|F| > 3$:
   - Select 3 most representative frets:
     - Anchor the root (lowest fret $\min(F)$).
     - Anchor the top lead note ($\max(F)$ unless it causes a 0+4 stretch).
     - Pick the best harmonic middle fret that forms a canonical power chord or triad.
4. Open Note Coexistence:
   - In Clone Hero, an Open Note (`7`) is an open string strum; it cannot be struck simultaneously with a fretted button (`0..4`).
   - If an open note and fretted notes collide at the same tick, enforce exclusivity: retain either the open note or the fretted chord based on amplitude or predominance.

### 5.4 Data Contract
```python
class ChordBuilder:
    MAX_CONCURRENT_FRETS: int = 3
    CANONICAL_POWER_CHORDS: frozenset[tuple[int, int]] = frozenset({
        (0, 1), (0, 2), (1, 2), (1, 3), (2, 3), (2, 4), (3, 4)
    })
    CANONICAL_TRIADS: frozenset[tuple[int, int, int]] = frozenset({
        (0, 1, 2), (0, 2, 3), (1, 2, 3), (2, 3, 4)
    })
    FORBIDDEN_STRETCHES: frozenset[tuple[int, int]] = frozenset({(0, 4)})

    def __init__(self, max_frets: int = 3) -> None:
        self.max_frets = max_frets

    def build_chords(self, notes: list[ChartNote]) -> list[ChartNote]:
        """Group simultaneous notes at identical ticks and enforce ergonomic chord limits."""
        ...
```

---

## 6. Requirement 4: HOPO, Strum & Sustain Duration Engine

### 6.1 Component A: `HopoEngine` (`hopo_engine.py`)
Clone Hero determines whether a note is a Hammer-On / Pull-Off (HOPO) or requires a Strum:
- **HOPO Interval Threshold**: $\le 65$ ticks (approx. 16th note at moderate tempo).
- **Fret Variation**: Must change frets between consecutive notes.

#### Algorithmic Rules:
1. **First Note Rule**: The very first note/chord of a chart is always a strum (`is_hopo = False`).
2. **Tempo Gap Rule**: If $\Delta_{\text{tick}} = \text{tick}_i - \text{tick}_{i-1} > 65$:
   `note.is_hopo = False`.
3. **Repeated Fret Rule**: If $\Delta_{\text{tick}} \le 65$ BUT $\text{fret}_i == \text{fret}_{i-1}$:
   `note.is_hopo = False` (Mandatory strum, never HOPO).
4. **Natural HOPO Rule**: If $\Delta_{\text{tick}} \le 65$ AND $\text{fret}_i \ne \text{fret}_{i-1}$:
   `note.is_hopo = True`.
5. **Chords**: Identical chords repeated in rapid succession are always strums (`is_hopo = False`).

#### Data Contract:
```python
class HopoEngine:
    HOPO_THRESHOLD_TICKS: int = 65

    def __init__(self, hopo_threshold: int = 65) -> None:
        self.hopo_threshold = hopo_threshold

    def process_hopos(self, notes: list[ChartNote]) -> list[ChartNote]:
        """Evaluate note transitions chronologically and assign is_hopo flags."""
        ...
```

---

### 6.2 Component B: `SustainProcessor` (`sustain_processor.py`)
In Clone Hero:
- Short notes (taps, quick strums) have `sustain_length = 0`.
- Sustained notes must not overlap the next note, or the game engine will fail to register the next strum.
- A release gap of **24 ticks** (a 32nd note) must be cleared prior to the next note onset.

#### Algorithmic Rules:
1. **Minimum Sustain Threshold**:
   If raw duration $D < 90$ ticks: `sustain_length = 0`.
2. **Release Margin Calculation**:
   If $D \ge 90$ ticks:
   $\text{sustain} = D - 24$.
3. **Next Note Collision Avoidance**:
   Find the next distinct note onset tick $T_{\text{next}} > \text{tick}_{\text{curr}}$.
   If $T_{\text{next}}$ exists:
   $\text{max\_allowed} = \max(0, (T_{\text{next}} - \text{tick}_{\text{curr}}) - 24)$.
   $\text{sustain} = \min(\text{sustain}, \text{max\_allowed})$.
4. **Non-negativity**: $\text{sustain} = \max(0, \text{sustain})$.

#### Data Contract:
```python
class SustainProcessor:
    MIN_SUSTAIN_THRESHOLD: int = 90
    RELEASE_MARGIN_TICKS: int = 24

    def __init__(self, min_threshold: int = 90, release_margin: int = 24) -> None:
        self.min_threshold = min_threshold
        self.release_margin = release_margin

    def process_sustains(
        self,
        notes: list[ChartNote],
        durations: list[int] | dict[int, int] | None = None,
    ) -> list[ChartNote]:
        """Compute sustain lengths applying 90-tick threshold and 24-tick release margin."""
        ...
```

---

### 6.3 Component C: `StarPowerGenerator` (`star_power_generator.py`)
Star Power phrases (`StarPowerPhrase(tick, length)`) grant bonus score multipliers:
- Allocated periodically every **16 to 32 measures** ($16 \times 768 = 12288$ ticks).
- Placed over dense rhythmic sections where notes are active.
- Phrase length: typically 1 to 2 measures ($768$ to $1536$ ticks).

#### Data Contract:
```python
class StarPowerGenerator:
    DEFAULT_INTERVAL_MEASURES: int = 16
    DEFAULT_PHRASE_LENGTH_TICKS: int = 768

    def __init__(self, interval_measures: int = 16, phrase_length_ticks: int = 768) -> None:
        self.interval_measures = interval_measures
        self.phrase_length_ticks = phrase_length_ticks

    def generate(
        self,
        notes: list[ChartNote],
        resolution: int = 192,
    ) -> list[StarPowerPhrase]:
        """Allocate Star Power phrases periodically over active note sections."""
        ...
```

---

## 7. Pipeline Integration Architecture (`src/pipeline.py`)

As specified in Prompt 6.1, Phase 4 connects directly into the end-to-end pipeline:
```
Raw NoteEvents (from Basic Pitch & HarmonicFilter)
    │
    ▼
[NoteQuantizer.quantize(notes, tempo_map)] ──> list[QuantizedNote]
    │
    ▼
[PitchToFretMapper.map_notes(quantized_notes)] ──> list[ChartNote]
    │
    ▼
[ChordBuilder.build_chords(notes)] ──> list[ChartNote] (<= 3 frets, valid shapes)
    │
    ▼
[HopoEngine.process_hopos(notes)] ──> list[ChartNote] (is_hopo set)
    │
    ▼
[SustainProcessor.process_sustains(notes)] ──> list[ChartNote] (sustain_length set)
    │
    ▼
[StarPowerGenerator.generate(notes)] ──> list[StarPowerPhrase]
    │
    ▼
SongTrack(name="ExpertSingle", notes=notes, star_power=star_power)
```

---

## 8. Verification Strategy & Tooling Baseline

- **Python Virtualenv**: `.venv/bin/` (Python 3.12.14).
- **Unit Test Runner**: `./.venv/bin/pytest tests/test_game_design/`
- **Full Regression**: `./.venv/bin/pytest tests/` (Baseline: 57 tests passing).
- **Strict Typing**: `./.venv/bin/mypy src/game_design tests/test_game_design`
- **Linting & Formatting**:
  - `./.venv/bin/ruff check src/game_design tests/test_game_design`
  - `./.venv/bin/ruff format --check src/game_design tests/test_game_design`

---

## 9. Conclusion

All data models, class contracts, constants, mathematical algorithms, and testing criteria for Phase 4 are fully specified and ready for implementation under strict TDD.
