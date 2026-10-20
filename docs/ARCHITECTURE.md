# music2chart — System Architecture Guide

Comprehensive technical reference on the DSP filters, neural inference models, game design heuristics, and binary container serialization engines powering `music2chart`.

---

## 🏗️ High-Level Architectural Flow

```
[ Raw Audio Input (MP3 / WAV / FLAC / OGG) ]
                      │
                      ▼
┌───────────────────────────────────────────────────────────┐
│ 1. INGESTION & AUDIO VALIDATION                          │
│    • Magic byte header inspection                         │
│    • Duration & size limits (50MB / 15 min)               │
│    • Resampling to 44.1kHz / 22.05kHz                     │
└─────────────────────┬─────────────────────────────────────┘
                      │
                      ▼
┌───────────────────────────────────────────────────────────┐
│ 2. NEURAL STEM ISOLATION (Meta Demucs v4)                 │
│    • htdemucs hybrid transformer model                    │
│    • Guitar stem extraction                               │
│    • Graceful stereo fallback in CPU-limited environments │
└─────────────────────┬─────────────────────────────────────┘
                      │
                      ▼
┌───────────────────────────────────────────────────────────┐
│ 3. TEMPO TRACKING & BEAT GRID GENERATION                  │
│    • Dynamic beat detection (Librosa / BeatNet)           │
│    • Time-varying BPM curves                              │
│    • Auto-calibration of high-tempo tracks (> 160 BPM)    │
│    • 192 PPQ resolution grid generation                   │
└─────────────────────┬─────────────────────────────────────┘
                      │
                      ▼
┌───────────────────────────────────────────────────────────┐
│ 4. NEURAL POLYPHONIC PITCH TRANSCRIPTION                 │
│    • Spotify Basic Pitch neural network                   │
│    • Frame-by-frame pitch probabilities (MIDI 0–127)      │
│    • Onset confidence & velocity extraction               │
└─────────────────────┬─────────────────────────────────────┘
                      │
                      ▼
┌───────────────────────────────────────────────────────────┐
│ 5. DSP HARMONIC FILTERING & OVERTONE SUPPRESSION          │
│    • High-gain amplifier 2nd harmonic (+12st) stripping   │
│    • High-gain amplifier 3rd harmonic (+19st) stripping   │
│    • Acoustic pick-noise suppression                      │
└─────────────────────┬─────────────────────────────────────┘
                      │
                      ▼
┌───────────────────────────────────────────────────────────┐
│ 6. GAME DESIGN MAPPING INTELLIGENCE (Expert Heuristics)   │
│    • 35–40ms Acoustic Chord Fusion Window                 │
│    • 192 PPQ Musical Grid Quantization                    │
│    • 5-Fret Sliding Tessitura Projection (Green → Orange) │
│    • Ergonomic Chord Voicings & Power Chords              │
│    • Natural HOPO Engine with Explicit N 5 0 Forcers      │
│    • 24-Tick Mandatory Sustain Release Margins            │
│    • Periodic Star Power Phrase Allocation                │
└─────────────────────┬─────────────────────────────────────┘
                      │
                      ▼
┌───────────────────────────────────────────────────────────┐
│ 7. DUAL CONTAINER SERIALIZATION                          │
│    • Strict notes.chart (milli-BPM SyncTrack & Ini)       │
│    • Little-Endian .sng v1 Container with 16-byte XOR     │
│    • Streaming OGG Vorbis Audio Packaging                 │
└─────────────────────┬─────────────────────────────────────┘
                      │
                      ▼
┌───────────────────────────────────────────────────────────┐
│ 8. DELIVERY LAYER                                         │
│    • Server-Sent Events (SSE) telemetry                   │
│    • Real-time Three.js 3D Highway Preview                │
│    • Direct file download (.sng, .chart, .zip)            │
└───────────────────────────────────────────────────────────┘
```

---

## 🔬 Deep-Dive Subsystem Analysis

### 1. Audio Processing Layer (`src/audio_processing/`)

#### 1.1 Stem Isolation (`separator.py`)
Standard polyphonic pitch detectors fail on full rock mixes because cymbals, bass guitars, and lead vocals generate high harmonic energy that creates false note onsets.
- **Engine**: Meta Demucs v4 (`htdemucs`), a state-of-the-art hybrid convolutional/transformer model.
- **Workflow**: Splits the raw master audio into 4 stems: `drums`, `bass`, `other`, and `vocals`.
- **Guitar Extraction**: In rock arrangements, the `other` stem contains the dominant electric guitar content.
- **Hardware Acceleration**: Automatically selects CUDA when available; gracefully falls back to CPU execution or original audio downmixing when memory or compute constraints dictate.

#### 1.2 Tempo Tracking (`tempo_tracker.py`)
Clone Hero relies on a continuous pulses-per-quarter-note (`192 PPQ`) grid driven by a `[SyncTrack]` structure in milli-BPM (`BPM * 1000`).
- **Dynamic Beats**: Uses onset envelope correlation across dynamic tempo shifts.
- **Auto-BPM Calibration**: Rhythm games become unplayable if the highway scroll speed is excessively rapid. If the detected tempo exceeds 160 BPM, the engine offers automatic halving (e.g., 180 BPM $\rightarrow$ 90 BPM with 8th-note grid alignment), matching human charter conventions.
- **BPM Scaling**: Configurable via `bpm_scale` (e.g., `0.65` in `the_best` preset) for smooth, tournament-ready scroll velocities.

#### 1.3 Polyphonic Transcription (`pitch_transcriber.py`)
- **Engine**: Spotify Basic Pitch.
- **Model Output**: Generates note events with exact onset timestamp (seconds), offset timestamp, MIDI pitch index ($0 \le p \le 127$), and amplitude confidence ($0.0 \le c \le 1.0$).
- **Filtering**: Ignores notes below `min_note_length` (default 58ms) to discard pick transients.

#### 1.4 Harmonic Filter (`harmonic_filter.py`)
Heavy guitar distortion generates artificial overtone series that mimic real notes:
- **Second Harmonic (+12 Semitones / Octave)**: Filter searches for simultaneous notes spaced by 12 semitones. If the higher note's amplitude is lower than the root, it is flagged as an overtone artifact and pruned.
- **Third Harmonic (+19 Semitones / Perfect 12th)**: Removes spurious 5th intervals generated by non-linear clipping distortion.

---

### 2. Game Design Mapping Engine (`src/game_design/`)

#### 2.1 Acoustic Chord Fusion Window (`quantizer.py`)
When a guitarist strums a physical chord, the pick travels across strings sequentially, introducing a $10\text{–}30\text{ms}$ delay between individual string vibrations:
- Naive converters quantize these offsets onto adjacent 1/32nd or 1/64th ticks, producing unplayable staircases ("walls of notes").
- `music2chart` implements a **35–40ms Chord Fusion Window**. Onsets detected within this threshold are fused into a simultaneous chord event anchored to the earliest onset tick.

#### 2.2 192 PPQ Strict Quantization (`quantizer.py`)
Ensures every note snaps strictly to rhythmically valid subdivisions:
$$\text{Ticks per Beat} = 192$$
- Quarter Note: $192\text{ ticks}$
- Eighth Note: $96\text{ ticks}$
- Eighth Triplet: $64\text{ ticks}$
- Sixteenth Note: $48\text{ ticks}$
- Sixteenth Triplet: $32\text{ ticks}$
- Thirty-Second Note: $24\text{ ticks}$
Any note spaced closer than $24\text{ ticks}$ is clamped or resolved to protect physical strum limits.

#### 2.3 5-Fret Sliding Tessitura (`pitch_to_fret.py`)
A real guitar neck spans 4 octaves; Clone Hero provides only 5 physical fret buttons:
- **Tessitura Analysis**: Computes moving average pitch registers across musical phrases.
- **Adaptive Mapping**: Projects lower pitch clusters to Green/Red and higher register solos to Blue/Orange.
- **Open Notes**: Configurable via `disable_open_notes`. Kept disabled by default for lead guitar charts.

#### 2.4 Ergonomic Chord Voicings (`chord_builder.py`)
- Limits simultaneous frets to maximum `2` or `3` frets (configurable via `max_frets`).
- Identifies root-fifth power chords and maps them to standard 2-fret spans (e.g., Green+Red, Red+Yellow, Yellow+Blue).
- Collapses rapid 16th-note single-string runs to prevent impossible multi-fret acrobatics.

#### 2.5 Natural HOPO Engine (`hopo_engine.py`)
- Notes spaced $\le$ `hopo_threshold` ticks (e.g., $48$ or $65\text{ ticks}$) from the preceding note are marked as Hammer-Ons / Pull-Offs.
- Explicit `<tick> = N 5 0` HOPO forcers are written into the `.chart` stream to guarantee exact engine behavior regardless of user game settings.
- Identical same-fret repetitions automatically cancel HOPOs, requiring an intentional strum.

#### 2.6 24-Tick Sustain Release Margins (`sustain_processor.py`)
If a sustain tail extends all the way to the next note onset, Clone Hero's engine can miss the subsequent strum or drop the combo.
- `music2chart` systematically subtracts $24\text{ ticks}$ from the end of every sustained note, guaranteeing a clean gap for player re-strums.

---

### 3. Serialization Layer (`src/serialization/`)

#### 3.1 Strict `.chart` Writer (`chart_writer.py`)
Formats standard text charts parsed by Clone Hero, YARG, and Moonscraper:
- `[Song]`: Resolution (192), Offset (0), Player2 (Bass), Difficulty (6).
- `[SyncTrack]`: Tempo events with millihertz precision (`<tick> = B <milli_bpm>`) and time signatures.
- `[Events]`: Section labels and rehearsal markers.
- `[ExpertSingle]`: Fret events (`N 0` through `N 4`), HOPO forcers (`N 5 0`), and Star Power phrases (`S 2 <length>`).

#### 3.2 Little-Endian `.sng` v1 Container (`sng_packer.py`)
`.sng` (SongBinary) is a high-performance single-file package format:
- **Header**: 6-byte magic identifier `SNGPKG`, format version `1`.
- **Stream Masking**: 16-byte pseudo-random XOR key:
  $$\text{xor\_key}_i = \text{mask}[i \pmod{16}] \oplus (i \ \& \ \text{0xFF})$$
- **Index**: File entries detailing metadata (`song.ini`), audio (`song.ogg`), and chart data (`notes.chart`).

---

### 4. Asynchronous Task Lifecycle (`src/api/routes.py`)

```
State: [ PENDING ] ──► [ PROCESSING ] ──► [ COMPLETED ] ──► [ TTL EXPIRED ]
             │                 │                │                  │
             │                 ▼                ▼                  ▼
             └──────────► [ FAILED ]      Files Downloadable   Auto-Cleanup
```

1. **Submission**: Endpoint validates file extension, magic bytes, length, and IP active task limit.
2. **Queueing**: Pushed to `TaskManager` in `PENDING` state.
3. **Execution**: Thread worker acquires the global semaphore (`MAX_CONCURRENT_TASKS`), logs visual ASCII progress bar, and updates progress percentages.
4. **Completion**: Generates `.sng`, `.chart`, and `.zip` in `tmp/output/<task_id>/`.
5. **Periodic Cleanup**: Background task cleans expired artifacts after `TASK_TTL_SECONDS` (default: 2 hours).
