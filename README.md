# music2chart

Automated high-fidelity chart generator for Clone Hero.

`music2chart` turns an audio file (MP3, WAV, FLAC, OGG) into playable Clone Hero
packages in both `.chart` (industry-standard text) and `.sng` (SongBinary v1)
formats, served through a containerized FastAPI REST API.

## Pipeline

1. Stem separation (Demucs v4 `htdemucs`) — isolates guitar/bass/drums
2. Tempo tracking & beat grid (BeatNet / Librosa) — variable BPM, 192 PPQ ticks
3. Polyphonic transcription (Spotify Basic Pitch) — pitch, onsets, durations
4. Harmonic filtering & quantization to the musical grid
5. Game-design mapping engine — MIDI → 5 frets (Expert), chords, HOPOs, sustains
6. Serialization — `notes.chart`, `song.ini`, `song.ogg`, `.sng` packing
7. FastAPI + background workers — upload, status, download

## Features

- Expert-difficulty 5-fret mapping with adaptive sliding pitch window
- Chord building with playability constraints (no awkward wide stretches)
- Automatic HOPO/strum tagging following Clone Hero rules
- Sustain processing with re-strum release margins
- Star Power phrase generation
- `.chart` and `.sng` (XOR-masked) output

## Project Layout

```
config/          Pydantic settings
src/models/      Domain data models
src/audio_processing/  Separation, tempo, transcription, filtering
src/game_design/ Quantization, pitch→fret, chords, HOPO, sustains, star power
src/serialization/    .chart, .ini, .sng writers
src/api/         FastAPI app, schemas, routes
dataset/         Scraping, parsing, feature extraction, evaluation
tests/           Unit tests (pytest)
```

## Requirements

- Python 3.11+
- FFmpeg
- (Optional) CUDA for GPU acceleration

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Running

```bash
uvicorn src.api.app:app --host 0.0.0.0 --port 8000
```

API endpoints: `/generate`, `/status/{task_id}`, `/download/{task_id}`.

## Development

```bash
pytest
ruff check .
mypy src
```

## Docker

```bash
docker compose up --build
```

## License

See project configuration in `pyproject.toml`.
