# Music2Chart

<div align="center">

[![Live Web App](https://img.shields.io/badge/Live_App-music2chart.adiels.me-00f5d4?style=for-the-badge&logo=googlechrome&logoColor=black)](https://music2chart.adiels.me/)
[![GitHub Stars](https://img.shields.io/github/stars/Adiells/music2chart?style=for-the-badge&color=ffd166&logo=github)](https://github.com/Adiells/music2chart/stargazers)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB.svg?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![PyTorch 2.2+](https://img.shields.io/badge/PyTorch-2.2+-EE4C2C.svg?style=flat-square&logo=pytorch&logoColor=white)](https://pytorch.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Docker Ready](https://img.shields.io/badge/Docker-Ready-2496ED.svg?style=flat-square&logo=docker&logoColor=white)](https://www.docker.com/)
[![Clone Hero & YARG](https://img.shields.io/badge/Compatible-Clone_Hero_%7C_YARG-9d4edd.svg?style=flat-square)](https://clonehero.net/)
[![Sponsor](https://img.shields.io/badge/Sponsor-GitHub_Sponsors-ea4c89.svg?style=flat-square&logo=githubsponsors&logoColor=white)](https://github.com/sponsors/Adiells)

**Automated high-fidelity audio-to-chart workstation for Clone Hero and YARG.**  
Convert any audio track (MP3, WAV, FLAC, OGG) into tournament-grade `.chart` and `.sng` packages in seconds, powered by neural stem separation, 192 PPQ dynamic beat grids, and authentic Guitar Hero game design heuristics.

[🚀 **Try It Live**](#try-it-live) • [⚡ **Quickstart**](#quickstart) • [🧠 **Architecture**](#pipeline-architecture) • [🔧 **REST API**](#rest-api) • [💖 **Sponsor Compute**](#sponsoring-server-infrastructure)

</div>

---

<a id="try-it-live"></a>
## ⚡ Try It Live

No local installation, Python environment, or GPU needed. Run songs through the full audio-to-chart workstation directly in your web browser:

👉 **[https://music2chart.adiels.me/](https://music2chart.adiels.me/)**

- **Drag-and-Drop Ingestion**: Upload any MP3, WAV, FLAC, or OGG file up to 50MB.
- **Interactive 3D Highway**: Preview notes on a real-time perspective highway before downloading.
- **One-Click Deliverables**: Download `.sng` (SongBinary v1) files or `.chart` zip archives ready to drop into your `Clone Hero/Songs/` folder.
- **Live Pipeline Telemetry**: Real-time progress bar powered by Server-Sent Events (SSE).

---

<a id="pipeline-architecture"></a>
## 🧠 Pipeline Architecture

```
[ Raw Audio: MP3 / WAV / FLAC / OGG ]
                    │
                    ▼
[ 1. Stem Separation: Meta Demucs v4 (htdemucs) ] ───► Isolates Lead Electric Guitar Stem
                    │
                    ▼
[ 2. Tempo Tracking & Beat Grid: Librosa / BeatNet ] ───► Dynamic BPM Changes & 192 PPQ Resolution
                    │
                    ▼
[ 3. Neural Pitch Transcription: Spotify Basic Pitch ] ──► Frame-level Polyphonic MIDI (0–127)
                    │
                    ▼
[ 4. Harmonic Filtering & Overtone Suppression ] ────► Strips 2nd (+12st) & 3rd (+19st) Overtones
                    │
                    ▼
[ 5. Game Design Mapping Engine (Expert Heuristics) ]
    ├─ 35ms Chord Fusion Window (eliminates string-roll micro-staircases)
    ├─ 192 PPQ Quantization (1/4=192, 1/8=96, 1/12=64, 1/16=48, 1/24=32, 1/32=24 ticks)
    ├─ 5-Fret Sliding Tessitura Projection (Green → Orange)
    ├─ Power Chord Ergonomics & Fast-Run Triad Collapsing
    ├─ Natural HOPO Engine with Explicit N 5 0 Forcers
    └─ Mandatory 24-Tick Re-Strum Sustain Release Margins
                    │
                    ▼
[ 6. Dual Container Serialization ]
    ├─ Strict notes.chart (milli-BPM SyncTrack, Events, ExpertSingle) + song.ini
    └─ Little-Endian .sng v1 Container with 16-byte XOR Stream Masking
                    │
                    ▼
[ 7. Asynchronous FastAPI Server & Web Workstation ] ──► Instant Web / REST / Docker Delivery
```

---

## 🔬 Key Engineering Highlights

`music2chart` is designed from the ground up to solve the longstanding flaws of naive audio-to-chart converters:

- **Meta Demucs v4 (`htdemucs`) Stem Isolation**: Eliminates transcription bleed by cleanly extracting the lead guitar track from dense mixes, with graceful fallback to stereo/mono mix in CPU environments.
- **Spotify Basic Pitch Polyphonic Model**: State-of-the-art neural transcription delivering precise onset, offset, and velocity detection.
- **Distortion Harmonic Suppression**: High-gain guitar amplifiers introduce strong 2nd harmonic (octave / +12 semitones) and 3rd harmonic (perfect 5th / +19 semitones) resonance. Our DSP filter identifies and removes these acoustic artifacts before mapping.
- **35ms Chord Fusion Window**: Acoustic pick drags across guitar strings create 10–30ms inter-string onset delays. Without fusion, naive algorithms output unplayable 8-tick micro-staircases ("walls of notes"). We fuse onsets within 35ms into unified chord events.
- **192 PPQ Strict Quantization**: Snaps onsets exclusively to musically valid subdivisions (192, 96, 64, 48, 32, 24 ticks) while maintaining a strict 24-tick minimum note spacing.
- **Natural HOPO Engine with `N 5 0` Forcers**: Fast single-note runs ($\le$ 96 ticks) anchor on an initial strum, followed by explicit `<tick> = N 5 0` HOPO forcers on subsequent notes for effortless fret tapping. Same-fret repetitions automatically enforce physical strumming.
- **24-Tick Sustain Release Margins**: Sustains subtract 24 ticks prior to subsequent onsets, ensuring the Clone Hero engine registers physical re-strums cleanly without note tail collision.
- **Little-Endian `.sng` Container (v1)**: Generates native binary `.sng` packages complete with metadata, file indexing, and byte-level 16-byte pseudo-random XOR stream masking (`xor_key = xor_mask[i % 16] ^ (i & 0xFF)`).

---

<a id="quickstart"></a>
## ⚡ Quickstart

### Tier 1: Web Workstation (Zero Setup)
Open [https://music2chart.adiels.me/](https://music2chart.adiels.me/) in your browser, drag and drop your song, and download the `.sng` file.

---

### Tier 2: Docker Compose (Recommended for Self-Hosting)
Run the complete containerized stack (FastAPI backend + Vite web frontend + CUDA/PyTorch support):

```bash
# Clone the repository
git clone https://github.com/Adiells/music2chart.git
cd music2chart

# Build and start services
docker compose up --build -d

# Check live logs
docker compose logs -f
```
The web workstation is now accessible at `http://localhost:8000` (or frontend dev server at `http://localhost:5173`).

---

### Tier 3: Local Python Environment

```bash
# Prerequisites: Python 3.11+ and FFmpeg installed on PATH
git clone https://github.com/Adiells/music2chart.git
cd music2chart

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install package and development tools
pip install -e ".[dev]"

# Launch the FastAPI server
uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload
```
Interactive API documentation will be available at `http://localhost:8000/docs`.

---

<a id="rest-api"></a>
### Tier 4: REST API (cURL / Automation)

#### 1. Submit Audio Track for Processing
```bash
curl -X POST "http://localhost:8000/api/v1/chart/generate" \
  -F "file=@solitude.mp3" \
  -F "song_name=Solitude" \
  -F "artist=Black Sabbath" \
  -F "format=both"
```

**Response (`202 Accepted`):**
```json
{
  "task_id": "8f484ddf-9988-47a8-a53b-e3c3b03f0b24",
  "status": "PENDING",
  "message": "Chart generation task submitted successfully.",
  "song_name": "Solitude",
  "artist": "Black Sabbath"
}
```

#### 2. Stream Live Progress (Server-Sent Events)
```bash
curl -N "http://localhost:8000/api/v1/chart/stream/8f484ddf-9988-47a8-a53b-e3c3b03f0b24"
```

#### 3. Download Generated Packages
```bash
# Download .sng binary package
curl -O -J "http://localhost:8000/api/v1/chart/download/8f484ddf-9988-47a8-a53b-e3c3b03f0b24?format=sng"

# Download .zip bundle (notes.chart + song.ini + song.ogg)
curl -O -J "http://localhost:8000/api/v1/chart/download/8f484ddf-9988-47a8-a53b-e3c3b03f0b24?format=chart"
```

---

## 🐍 Python API Usage

You can embed `music2chart` directly into your own Python pipelines or Jupyter/Colab notebooks:

```python
from pathlib import Path
from src.pipeline import Music2ChartPipeline

# Initialize pipeline (loads neural models into cache/device)
pipeline = Music2ChartPipeline()

# Process audio track
artifacts = pipeline.process_song(
    audio_path=Path("audio/my_track.mp3"),
    song_name="Free Bird Solo",
    artist="Lynyrd Skynyrd",
    output_format="both",  # "sng", "chart", or "both"
)

print(f"Chart generated: {artifacts['chart']}")
print(f"SNG container: {artifacts['sng']}")
```

---

## 📊 Dataset & Benchmarking Tools

`music2chart` includes automated validation tools to compare AI charts against verified human-authored charts from the Chorus/Encore community:

```python
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

<a id="contributing"></a>
## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for local environment setup, architecture guidelines, test execution (`pytest`), and the Conventional Commits standard.

Please also review our [Code of Conduct](CODE_OF_CONDUCT.md) and [Security Policy](SECURITY.md).

---

<a id="license"></a>
## 📄 License

This project is licensed under the [MIT License](LICENSE) — Copyright © 2026 Adiel Emilson.
