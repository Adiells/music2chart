# Music2Chart

<div align="center">

[![Live Web App](https://img.shields.io/badge/Live_App-music2chart.adiels.me-00f5d4?style=for-the-badge&logo=googlechrome&logoColor=black)](https://music2chart.adiels.me/)
[![GitHub Stars](https://img.shields.io/github/stars/Adiells/music2chart?style=for-the-badge&color=ffd166&logo=github)](https://github.com/Adiells/music2chart/stargazers)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB.svg?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![PyTorch 2.2+](https://img.shields.io/badge/PyTorch-2.2+-EE4C2C.svg?style=flat-square&logo=pytorch&logoColor=white)](https://pytorch.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React 19](https://img.shields.io/badge/React-19.2+-61DAFB.svg?style=flat-square&logo=react&logoColor=black)](https://react.dev/)
[![Three.js](https://img.shields.io/badge/Three.js-0.186+-000000.svg?style=flat-square&logo=three.js&logoColor=white)](https://threejs.org/)
[![Docker Ready](https://img.shields.io/badge/Docker-Ready-2496ED.svg?style=flat-square&logo=docker&logoColor=white)](https://www.docker.com/)
[![Clone Hero & YARG](https://img.shields.io/badge/Compatible-Clone_Hero_%7C_YARG-9d4edd.svg?style=flat-square)](https://clonehero.net/)
[![Sponsor](https://img.shields.io/badge/Sponsor-GitHub_Sponsors-ea4c89.svg?style=flat-square&logo=githubsponsors&logoColor=white)](https://github.com/sponsors/Adiells)

**Automated high-fidelity audio-to-chart workstation for Clone Hero and YARG.**  
Convert any audio track (MP3, WAV, FLAC, OGG) into tournament-grade `.chart` and `.sng` packages in seconds, powered by neural stem separation, 192 PPQ dynamic beat grids, authentic Guitar Hero game design heuristics, and a real-time interactive 3D Highway visualizer.

[🚀 **Try It Live**](#try-it-live) • [🎛️ **Studio Workstation**](#studio-workstation-frontend) • [⚙️ **Presets**](#presets-engine) • [⚡ **Quickstart**](#quickstart) • [🧠 **Architecture**](#pipeline-architecture) • [🔧 **REST API**](#rest-api) • [⚙️ **Configuration**](#configuration--environment-variables) • [💖 **Sponsor**](#sponsoring-server-infrastructure)

</div>

---

<a id="try-it-live"></a>
## ⚡ Try It Live

No local installation, Python environment, or GPU needed. Run songs through the full audio-to-chart workstation directly in your web browser:

👉 **[https://music2chart.adiels.me/](https://music2chart.adiels.me/)**

- **Drag-and-Drop Ingestion**: Upload any MP3, WAV, FLAC, or OGG file up to 50MB (up to 15 minutes duration).
- **Tactile Studio Rack**: Physical audio hardware aesthetic with rotary knobs, toggle switches, and push buttons.
- **Interactive 3D Highway**: Real-time perspective highway powered by Three.js with synchronized audio preview, seek controls, and strike bar animations.
- **Tournament Calibration**: Fine-tune noise gates, BPM scaling, Star Power thresholds, and chord fusion windows in real time.
- **One-Click Deliverables**: Download `.sng` (SongBinary v1) files, standalone `notes.chart`, or complete `.zip` bundles ready to drop into your `Clone Hero/Songs/` directory.
- **Live Pipeline Telemetry**: Real-time stage monitoring powered by Server-Sent Events (SSE).

---

<a id="studio-workstation-frontend"></a>
## 🎛️ Studio Workstation (Frontend)

`music2chart` features an industrial audio workstation inspired by vintage studio rack hardware, designed with tactile mechanical controls, haptic audio feedback, and a seamless 4-step workflow:

```
[ Step 1: Ingestion ] ──► [ Step 2: Calibration ] ──► [ Step 3: 3D Highway ] ──► [ Step 4: Export Bay ]
  • File Dropzone            • Preset Selection          • Real-time 3D Lane        • .sng Container
  • Audio Validation         • Noise Gate & Sens         • Audio Playback Sync      • notes.chart
  • Metadata Tagging         • BPM Scale (0.65x)         • Fret Gems & Sustains     • Full Song ZIP
  • Duration Limits          • Chord Fusion Engine       • Strike Bar Hits          • NPS & Note Stats
```

- **Step 1 — Ingestion & Tagging**: Instant client-side format inspection, magic byte verification, and automatic song/artist metadata inference.
- **Step 2 — Acoustic Calibration**: Select from tuned presets or adjust rotary knobs to modify minimum amplitude (noise gate), BPM scaling, sustain thresholds, and HOPO sensitivity.
- **Step 3 — 3D Highway Preview**: Inspect generated note patterns in an authentic Guitar Hero-style perspective lane rendered in Three.js, synchronized with the original audio stream.
- **Step 4 — Hardware Export Bay**: Monitor note-per-second (NPS) density graphs, total note statistics, and instantly trigger downloads for Clone Hero and YARG.
- **Bilingual Interface**: Full localization support for both **English** and **Portuguese (pt-BR)**.

---

<a id="presets-engine"></a>
## ⚙️ Presets Engine

`music2chart` includes pre-tuned calibration presets tailored for different musical genres and playing preferences:

| Preset Profile | Focus | Noise Gate (`min_amplitude`) | BPM Scale | HOPO Distance | Chord Fusion | Recommended For |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **`the_best`** *(Default)* | **Tournament Grade** | **`0.41`** | **`0.65`** | **`48 ticks`** | **`40 ms`** | High-precision playability, clean chord transitions, comfortable scroll speed, eliminating ghost notes. |
| **`standard`** | Balanced Baseline | `0.10` | `1.00` | `65 ticks` | `35 ms` | General rock and metal tracks with standard natural tempo tracking. |
| **`strict_rhythm`** | Rhythm & Chords | `0.20` | `1.00` | `48 ticks` | `40 ms` | Heavy rhythm riffs, punk, and power-chord tracks requiring tight strum discipline. |
| **`dynamic_solo`** | Lead & Shredding | `0.08` | `1.00` | `80 ticks` | `30 ms` | Fast guitar solos, sweep picking, and virtuosic runs without chord collapsing. |

All presets automatically enforce **192 PPQ quantization**, **24-tick sustain release margins**, and **sliding tessitura projection**.

---

<a id="pipeline-architecture"></a>
## 🧠 Pipeline Architecture

```
[ Raw Audio: MP3 / WAV / FLAC / OGG (Max 50MB, 15 min) ]
                         │
                         ▼
[ 1. Stem Separation: Meta Demucs v4 (htdemucs) ] ───────► Isolates Lead Electric Guitar Stem (GPU / CPU Fallback)
                         │
                         ▼
[ 2. Tempo Tracking & Beat Grid: Librosa / BeatNet ] ─────► Dynamic BPM Changes & 192 PPQ Resolution
                         │
                         ▼
[ 3. Neural Pitch Transcription: Spotify Basic Pitch ] ──► Frame-level Polyphonic Note Probabilities (0–127)
                         │
                         ▼
[ 4. Harmonic Filtering & Overtone Suppression ] ────────► Strips 2nd (+12st) & 3rd (+19st) Distortion Overtones
                         │
                         ▼
[ 5. Game Design Mapping Engine (Expert Heuristics) ]
    ├─ 35–40ms Chord Fusion Window (eliminates string-roll micro-staircases)
    ├─ 192 PPQ Strict Quantization (1/4=192, 1/8=96, 1/12=64, 1/16=48, 1/24=32, 1/32=24 ticks)
    ├─ 5-Fret Sliding Tessitura Projection (Green → Orange)
    ├─ Power Chord Ergonomics & Fast-Run Triad Collapsing
    ├─ Natural HOPO Engine with Explicit N 5 0 Forcers
    ├─ Star Power Phrase Allocation & Rhythmic Anchor Points
    └─ Mandatory 24-Tick Re-Strum Sustain Release Margins
                         │
                         ▼
[ 6. Dual Container Serialization ]
    ├─ Strict notes.chart (milli-BPM SyncTrack, Events, ExpertSingle) + song.ini
    └─ Little-Endian .sng v1 Container with 16-byte XOR Stream Masking
                         │
                         ▼
[ 7. Asynchronous FastAPI Server & 3D Web Workstation ] ─► SSE Telemetry / Real-time Three.js Preview / Delivery
```

---

## 🔬 Key Engineering Highlights

`music2chart` is designed from the ground up to solve the longstanding flaws of naive audio-to-chart converters:

- **Meta Demucs v4 (`htdemucs`) Stem Isolation**: Eliminates transcription bleed by cleanly extracting the lead guitar track from dense mixes, with graceful fallback to stereo/mono mix in CPU-only environments.
- **Spotify Basic Pitch Polyphonic Model**: State-of-the-art neural transcription delivering precise onset, offset, and velocity detection with custom frame and onset confidence thresholds.
- **Distortion Harmonic Suppression**: High-gain guitar amplifiers introduce strong 2nd harmonic (octave / +12 semitones) and 3rd harmonic (perfect 5th / +19 semitones) resonance. Our DSP filter identifies and removes these acoustic artifacts before mapping.
- **Acoustic Chord Fusion Window (35–40ms)**: Acoustic pick drags across guitar strings create 10–30ms inter-string onset delays. Without fusion, naive algorithms output unplayable 8-tick micro-staircases ("walls of notes"). We fuse onsets within 35–40ms into unified, ergonomic chords.
- **192 PPQ Strict Quantization**: Snaps onsets exclusively to musically valid subdivisions (192, 96, 64, 48, 32, 24 ticks) while maintaining a strict 24-tick minimum note spacing.
- **Natural HOPO Engine with `N 5 0` Forcers**: Fast single-note runs ($\le$ 48–65 ticks) anchor on an initial strum, followed by explicit `<tick> = N 5 0` HOPO forcers on subsequent notes for effortless fret tapping. Same-fret repetitions automatically enforce physical strumming.
- **24-Tick Sustain Release Margins**: Sustains subtract 24 ticks prior to subsequent onsets, ensuring the Clone Hero engine registers physical re-strums cleanly without note tail collision.
- **Little-Endian `.sng` Container (v1)**: Generates native binary `.sng` packages complete with metadata, file indexing, and byte-level 16-byte pseudo-random XOR stream masking (`xor_key = xor_mask[i % 16] ^ (i & 0xFF)`).
- **Concurrency & Security Safeguards**: Built-in IP rate limiting (20 chart conversions/hour), task deduplication (1 active task per IP), audio magic bytes validation, and automatic temporary file garbage collection.

---

<a id="quickstart"></a>
## ⚡ Quickstart

### Tier 1: Web Workstation (Zero Setup)
Open [https://music2chart.adiels.me/](https://music2chart.adiels.me/) in your browser, drag and drop your song, tune settings, preview in 3D, and download.

---

### Tier 2: Docker Compose (Recommended for Self-Hosting)
Run the complete containerized stack (FastAPI backend + Vite web frontend + PyTorch/Demucs):

```bash
# Clone the repository
git clone https://github.com/Adiells/music2chart.git
cd music2chart

# Build and start services
docker compose up --build -d

# Follow live server logs
docker compose logs -f
```
The application will be accessible at `http://localhost:8000` (or frontend dev server at `http://localhost:5173`).

---

### Tier 3: Local Development (Python + Node.js)

#### 1. Backend Setup
```bash
# Prerequisites: Python 3.11+ and FFmpeg installed on PATH
git clone https://github.com/Adiells/music2chart.git
cd music2chart

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies in editable mode
pip install -e ".[dev]"

# Launch the FastAPI server
uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload
```
Interactive API documentation will be available at `http://localhost:8000/docs`.

#### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
The frontend dev server runs at `http://localhost:5173` with instant Hot Module Replacement (HMR).

---

<a id="rest-api"></a>
## 🔧 REST API Reference

Comprehensive documentation for programmatic consumption and automation:

### 1. Submit Audio Track for Processing
```bash
curl -X POST "http://localhost:8000/api/v1/chart/generate" \
  -F "file=@solitude.mp3" \
  -F "song_name=Solitude" \
  -F "artist=Black Sabbath" \
  -F "preset=the_best" \
  -F "bpm_scale=0.65" \
  -F "min_amplitude=0.41" \
  -F "format=both"
```

**Parameters (`multipart/form-data`):**
| Parameter | Type | Default | Description |
| :--- | :--- | :---: | :--- |
| `file` | `UploadFile` | *Required* | Audio track (`.mp3`, `.wav`, `.flac`, `.ogg`, max 50MB). |
| `song_name` | `string` | File stem | Title of the song. |
| `artist` | `string` | File stem | Artist / band name. |
| `preset` | `string` | `the_best` | Preset profile (`the_best`, `standard`, `strict_rhythm`, `dynamic_solo`). |
| `output_format` | `string` | `both` | Output artifact packaging: `sng`, `chart`, or `both`. |
| `bpm_scale` | `float` | `0.65` | Tempo multiplier / scroll speed scaler (0.1 to 2.0). |
| `min_amplitude` | `float` | `0.41` | Noise gate threshold (0.0 to 1.0) for acoustic filtering. |
| `max_frets` | `int` | `2` | Maximum simultaneous frets for chords (1 to 3). |
| `hopo_threshold` | `int` | `48` | Maximum tick distance between notes to trigger HOPOs. |
| `chord_fusion_window_s` | `float` | `0.040` | Time window (seconds) to merge rolled pick onsets into chords. |
| `min_sustain_ticks` | `int` | `96` | Minimum length (ticks) to render sustain trails. |
| `release_margin` | `int` | `24` | Safety margin (ticks) subtracted before subsequent onsets. |
| `auto_calibrate_bpm` | `bool` | `true` | Halve excessive detected tempos (> 160 BPM) for playable scroll speeds. |
| `merge_sustained_notes` | `bool` | `true` | Merge identical consecutive notes into prolonged sustains. |

**Response (`202 Accepted`):**
```json
{
  "task_id": "8f484ddf-9988-47a8-a53b-e3c3b03f0b24",
  "status": "PENDING",
  "message": "Chart generation task queued successfully.",
  "song_name": "Solitude",
  "artist": "Black Sabbath"
}
```

---

### 2. Stream Live Progress (Server-Sent Events)
Stream real-time progress percentages and pipeline stage transitions:
```bash
curl -N "http://localhost:8000/api/v1/chart/stream/8f484ddf-9988-47a8-a53b-e3c3b03f0b24"
```

**SSE Event Payload:**
```json
data: {"task_id": "8f484ddf...", "status": "PROCESSING", "progress": 0.45, "stage": "Spotify Basic Pitch polyphonic transcription", "error": null, "result_files": null}
```

---

### 3. Check Task Status (Polling)
```bash
curl "http://localhost:8000/api/v1/chart/status/8f484ddf-9988-47a8-a53b-e3c3b03f0b24"
```

---

### 4. Stream Preview Audio
Stream the processed `song.ogg` directly for in-browser playback or highway synchronization:
```bash
curl "http://localhost:8000/api/v1/chart/preview/8f484ddf-9988-47a8-a53b-e3c3b03f0b24/audio" --output preview.ogg
```

---

### 5. Download Deliverable Packages
```bash
# Download .sng binary package (Ready for Clone Hero & YARG)
curl -O -J "http://localhost:8000/api/v1/chart/download/8f484ddf-9988-47a8-a53b-e3c3b03f0b24?format=sng"

# Download standalone notes.chart
curl -O -J "http://localhost:8000/api/v1/chart/download/8f484ddf-9988-47a8-a53b-e3c3b03f0b24?format=chart"

# Download complete ZIP bundle (notes.chart + song.ini + song.ogg)
curl -O -J "http://localhost:8000/api/v1/chart/download/8f484ddf-9988-47a8-a53b-e3c3b03f0b24?format=zip"
```

---

### 6. Health & Liveness Probes
```bash
curl "http://localhost:8000/health"
# Returns: {"status": "ok", "app_name": "music2chart", "version": "0.1.0"}
```

---

<a id="configuration--environment-variables"></a>
## ⚙️ Configuration & Environment Variables

All settings can be configured via environment variables or a `.env` file in the project root:

| Variable | Type | Default | Description |
| :--- | :---: | :---: | :--- |
| `APP_ENV` | `string` | `development` | Environment mode (`development`, `production`). |
| `DEVICE` | `string` | `cuda` (auto) | Compute device for PyTorch and Demucs (`cuda` or `cpu`). |
| `DEMUCS_MODEL_NAME` | `string` | `htdemucs` | Model architecture for stem separation. |
| `DEFAULT_RESOLUTION` | `int` | `192` | Chart pulses per quarter note (PPQ). |
| `MAX_UPLOAD_SIZE_BYTES` | `int` | `52428800` | Maximum file upload size in bytes (50 MB). |
| `MAX_AUDIO_DURATION_SECONDS` | `float` | `900.0` | Maximum allowed audio track length (15 minutes). |
| `MAX_CONCURRENT_TASKS` | `int` | `1` | Maximum parallel neural inference tasks. |
| `TASK_QUEUE_CAPACITY` | `int` | `10` | Task queue limit before rejecting with HTTP 429. |
| `TASK_TTL_SECONDS` | `int` | `7200` | Retention duration (2 hours) before disk cleanup. |
| `CLEANUP_INTERVAL_SECONDS` | `int` | `300` | Frequency of background cache cleanup (5 minutes). |
| `RATE_LIMIT_GENERATE` | `string` | `20/hour` | Rate limit per client IP for chart generation. |
| `ENABLE_AUTO_STEM_CLEANUP` | `bool` | `true` | Automatically delete intermediate stems after packaging. |
| `ALLOWED_ORIGINS` | `list[str]` | `localhost,adiels.me` | Permitted CORS origins (comma-separated). |

---

## 🐍 Python API Usage

Embed `music2chart` directly into your custom Python workflows or data science pipelines:

```python
from pathlib import Path
from src.pipeline import Music2ChartPipeline

# Initialize pipeline (loads neural models into cache/device)
pipeline = Music2ChartPipeline()

# Process audio track with tournament-grade calibration
artifacts = pipeline.process_song(
    audio_path=Path("audio/my_track.mp3"),
    song_name="Free Bird Solo",
    artist="Lynyrd Skynyrd",
    preset="the_best",
    bpm_scale=0.65,
    min_amplitude=0.41,
    output_format="both",  # "sng", "chart", or "both"
)

print(f"Chart generated: {artifacts['chart']}")
print(f"SNG container: {artifacts['sng']}")
```

---

## 📊 Dataset & Benchmarking Tools

`music2chart` includes automated validation tools to compare AI-generated charts against verified human-authored charts from the Chorus/Encore community:

```python
from pathlib import Path
from dataset.chorus_scraper import ChorusScraper
from dataset.evaluate_mapping import evaluate_chart_alignment

# 1. Download human-authored ground truth
scraper = ChorusScraper()
charts = scraper.search_charts(query="Cliffs of Dover", instrument="guitar")
package_dir = scraper.download_chart_package(charts[0]["id"], destination_dir=Path("dataset/downloads"))

# 2. Evaluate Onset F1, Fret Accuracy & Chord Similarity
metrics = evaluate_chart_alignment(predicted_notes, ground_truth_notes, tempo_map)
print(f"Onset F1: {metrics['onset_f1']:.3f} | Fret Accuracy: {metrics['fret_accuracy']:.2%}")
```

---

<a id="sponsoring-server-infrastructure"></a>
## 💖 Sponsoring Server Infrastructure & GPU Upgrade

[![GitHub Sponsors](https://img.shields.io/badge/Sponsor_on-GitHub_Sponsors-ea4c89?style=for-the-badge&logo=githubsponsors&logoColor=white)](https://github.com/sponsors/Adiells)

**music2chart** is and will always remain **100% free and open-source software** under the permissive MIT License.

Currently, the public live demo at **[music2chart.adiels.me](https://music2chart.adiels.me/)** runs on serverless **Google Cloud Run CPU instances** (`4 vCPU`, `8 GiB RAM`, `us-central1`). Because state-of-the-art neural models (Meta Demucs v4 and Spotify Basic Pitch) run purely on CPU cores without hardware acceleration, processing a full track takes roughly 1–2 minutes.

**We do not have dedicated GPU instances yet.** The primary purpose of our GitHub Sponsors fund is to evolve our infrastructure:
- 🚀 **Upgrade to Dedicated Cloud GPU instances (NVIDIA Tensor Core)** to slash chart generation times from ~90 seconds down to sub-15 seconds.
- ⚡ **Eliminate concurrency bottlenecks and cold-start latency** for rhythm game charters worldwide.
- 🌐 **Offset monthly Cloud Run and bandwidth costs** to guarantee zero paywalls and zero advertisements.

If you find this tool helpful for your Clone Hero or YARG sessions, consider supporting the GPU upgrade fund:

👉 **[Sponsor on GitHub Sponsors (`https://github.com/sponsors/Adiells`)](https://github.com/sponsors/Adiells)**

Every contribution directly accelerates the milestone to bring real-time, GPU-accelerated charting to the entire community. Thank you!

---

<a id="documentation"></a>
## 📚 Additional Documentation

- [**Frontend Documentation**](frontend/README.md): React 19 architecture, Three.js 3D highway, tactile rack components, and Web Audio API integration.
- [**System Architecture Guide**](docs/ARCHITECTURE.md): Deep-dive into DSP filters, neural inference, 192 PPQ quantization heuristics, and `.sng` container specifications.
- [**REST API Guide**](docs/API.md): Detailed API reference, payload examples, and error handling.
- [**Contributing Guidelines**](CONTRIBUTING.md): Environment setup, coding standards, testing instructions, and pull request workflows.
- [**Code of Conduct**](CODE_OF_CONDUCT.md): Community standards and pledge.
- [**Security Policy**](SECURITY.md): Vulnerability reporting and security protocols.

---

<a id="license"></a>
## 📄 License

This project is licensed under the [MIT License](LICENSE) — Copyright © 2026 Adiel Emilson.
