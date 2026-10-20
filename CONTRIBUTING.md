# Contributing to music2chart

Thank you for your interest in contributing to **music2chart**! 🎉

We welcome contributions from rhythm game enthusiasts, machine learning researchers, audio DSP engineers, and full-stack developers. Whether you want to improve chord heuristics, add new instrument tracks, optimize neural inference speed, or polish the 3D highway visualizer, your help is appreciated.

Please read this guide before submitting issues or pull requests.

---

## Code of Conduct

All contributors and maintainers are expected to follow our [Code of Conduct](CODE_OF_CONDUCT.md). By participating in this project, you agree to uphold its terms.

---

## Architecture Overview

`music2chart` is organized into several modular layers:

- **`src/audio_processing/`**: Core signal processing and neural inference.
  - `separator.py`: Meta Demucs v4 (`htdemucs`) stem isolation with CPU fallback.
  - `tempo_tracker.py`: Librosa and BeatNet dynamic BPM grid and time-signature tracking.
  - `pitch_transcriber.py`: Spotify Basic Pitch polyphonic pitch tracking.
  - `harmonic_filter.py`: 2nd/3rd harmonic overtone suppression for high-gain guitars.
- **`src/game_design/`**: Expert-difficulty Clone Hero / YARG mapping intelligence.
  - `quantizer.py`: Intelligent snapping to 192 PPQ grid (192, 96, 64, 48, 32, 24 ticks) with 35ms chord fusion window.
  - `pitch_to_fret.py`: Adaptive sliding tessitura projection to 5 physical frets (Green through Orange).
  - `chord_builder.py`: Power chords, ergonomic triads, and fast-run single-note collapsing.
  - `hopo_engine.py`: Hammer-On / Pull-Off detection with explicit `<tick> = N 5 0` HOPO forcers.
  - `sustain_processor.py`: Sustain duration clamping with mandatory 24-tick re-strum margins.
  - `star_power_generator.py`: Periodic Star Power phrase allocation.
- **`src/serialization/`**: Target file generation.
  - `chart_writer.py`: Industry-standard `.chart` text format.
  - `ini_writer.py`: `song.ini` metadata container.
  - `sng_packer.py`: Little-Endian `.sng` v1 binary container with 16-byte XOR stream masking.
- **`src/api/`**: Asynchronous FastAPI endpoints, Server-Sent Events (SSE) telemetry, and background workers.
- **`frontend/`**: Vite + React 19 + TypeScript + Three.js industrial audio workstation, tactile rack modules, and 3D Clone Hero highway visualizer.

---

## Local Development Setup

### 1. Prerequisites
- **Python 3.11+**
- **Node.js 18+** & **npm**
- **FFmpeg** installed and accessible on your `$PATH` (`ffmpeg -version`)
- *Optional / Recommended*: NVIDIA GPU with CUDA drivers for accelerated stem separation and pitch inference.

### 2. Python Backend Setup
```bash
# Clone the repository
git clone https://github.com/Adiells/music2chart.git
cd music2chart

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install editable package with development and testing dependencies
pip install -e ".[dev]"

# Alternatively using uv:
# uv pip install -e ".[dev]"
```

### 3. Frontend Web Workstation Setup
```bash
cd frontend

# Install dependencies
npm install

# Start Vite development server
npm run dev
```
The web workstation will be live at `http://localhost:5173`. It connects by default to the backend at `http://localhost:8000`.

### 4. Running the Backend API
From the repository root:
```bash
uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload
```
Interactive Swagger documentation is served at `http://localhost:8000/docs`.

### 5. Running with Docker Compose
If you prefer developing inside containerized environments:
```bash
docker compose up --build -d
docker compose logs -f
```

---

## Testing & Quality Assurance

Quality and correctness are non-negotiable for musical game charts. Every pull request must pass all tests and linting checks.

### Running Python Unit & Integration Tests
```bash
# Run complete test suite (245+ tests)
pytest -v

# Run with coverage report (target: >= 90% coverage on src/)
pytest --cov=src --cov-report=term-missing
```

### Linting and Code Formatting
We use [Ruff](https://docs.astral.sh/ruff/) for Python linting and formatting:
```bash
# Check code for lint violations
ruff check .

# Check code formatting without modifying files
ruff format --check src tests config dataset

# Automatically fix linting and formatting issues
ruff check --fix .
ruff format src tests config dataset
```

### Frontend Typechecking & Build Verification
```bash
cd frontend
npm run lint
npm run build
```

---

## Commit Guidelines (Conventional Commits)

We enforce the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) specification for clear, readable git logs and automated changelog generation.

### Commit Format
```text
<type>(<scope>): <short description in present tense>

[optional body explaining motivation and technical approach]

[optional footer(s), e.g., Fixes #123]
```

### Allowed Types
- `feat`: A new feature or mapping heuristic.
- `fix`: A bug fix in chart serialization, timing, or audio parsing.
- `docs`: Documentation changes (`README.md`, `CONTRIBUTING.md`, docstrings).
- `refactor`: Code restructure that neither fixes a bug nor adds a feature.
- `perf`: Performance improvements (e.g., vectorized numpy math, cached weights).
- `test`: Adding or updating test cases.
- `chore`: Build scripts, dependencies, CI configuration, or linting updates.

### Examples
- `feat(quantizer): implement 35ms sliding window for chord fusion`
- `fix(sng): correct little-endian file index offset calculation`
- `docs(readme): add hero badges and discreet sponsor tier`
- `test(hopo): add unit test for repeated fret strum enforcement`

---

## Pull Request Process

1. **Fork the repo** and create a descriptive feature branch from `main`:
   ```bash
   git checkout -b feat/sliding-tessitura-anchor
   ```
2. **Make your changes**, ensuring clean type annotations and descriptive docstrings.
3. **Verify the test suite**:
   ```bash
   pytest --cov=src
   ruff check .
   ruff format --check .
   ```
4. **Commit your changes** following the Conventional Commits style.
5. **Push to your fork** and submit a Pull Request against `main`.
6. Fill out the [Pull Request Template](.github/PULL_REQUEST_TEMPLATE.md), referencing any relevant issue numbers.
7. Maintainers will review your submission promptly and provide constructive feedback.

---

## Questions and Support

- Join our [GitHub Discussions](https://github.com/Adiells/music2chart/discussions) to ask questions or bounce ideas.
- Test charts live at [music2chart.adiels.me](https://music2chart.adiels.me/).
- Found a bug? Open an issue via our [Bug Report Form](.github/ISSUE_TEMPLATE/bug_report.yml).
