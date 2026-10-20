# music2chart — Frontend Studio Workstation

<div align="center">

[![React 19](https://img.shields.io/badge/React-19.2+-61DAFB.svg?style=flat-square&logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6.svg?style=flat-square&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Vite 8](https://img.shields.io/badge/Vite-8.x-646CFF.svg?style=flat-square&logo=vite&logoColor=white)](https://vitejs.dev/)
[![Three.js](https://img.shields.io/badge/Three.js-0.186+-000000.svg?style=flat-square&logo=three.js&logoColor=white)](https://threejs.org/)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-3.4+-38B2AC.svg?style=flat-square&logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)

**Tactile Audio Rack Workstation & Interactive 3D Clone Hero Highway**

</div>

---

## 🎛️ Overview

The `music2chart` frontend is an industrial-grade web workstation built with **React 19**, **Three.js**, **TypeScript**, and **TailwindCSS**. It emulates high-end vintage audio rack gear with physical toggle switches, tactile rotary potentiometers, LED meters, and an authentic 3D Clone Hero note highway.

### Core Features
- **4-Step Linear Workflow**: Guided progression through Ingestion, Calibration, 3D Highway, and Deliverables Export.
- **Interactive 3D Highway**: Perspective fretboard rendered with Three.js featuring real-time audio playback synchronization, animated note gems, sustain tails, and dynamic strike bar hit effects.
- **Tactile Audio Controls**: Skeuomorphic rotary knobs (`RotaryKnob`), indexed selector switches (`RotarySelector`), metal toggle switches (`ToggleSwitch`), and backlit push buttons (`PushButton`).
- **Physical Mechanical Feedback**: Custom Web Audio API synthesizer synthesizing realistic mechanical relay and switch clicks (`mechanicalClick.ts`) upon user interaction.
- **Real-time Pipeline Telemetry**: Server-Sent Events (SSE) listener monitoring neural stem separation, tempo tracking, pitch transcription, and quantization progress.
- **Bilingual Interface**: Seamless instant toggle between **English** and **Portuguese (pt-BR)**.
- **Audio Diagnostics**: Real-time Note-Per-Second (NPS) density histogram, dynamic BPM display, and waveform visualization.

---

## 📐 Architecture & Directory Structure

```
frontend/src/
├── App.tsx                     # Main workstation layout, stage navigation, state machine
├── components/
│   ├── actions/
│   │   └── FloatingActionDock.tsx  # Persistent quick-action bar (submit, preview, reset)
│   ├── audit/
│   │   ├── NpsGraph.tsx            # Note-Per-Second interactive density histogram
│   │   ├── StatsCard.tsx           # Telemetry metrics display card
│   │   ├── TempoDisplay.tsx        # Dynamic BPM readout and pulse indicator
│   │   └── WaveformBar.tsx         # Audio amplitude envelope visualizer
│   ├── controls/
│   │   ├── KnobGraphic.tsx         # SVG rotary knob rendering with tick markers
│   │   ├── PresetSelector.tsx      # Quick-switch preset bank (the_best, standard, etc.)
│   │   ├── PushButton.tsx          # Backlit mechanical push button
│   │   ├── RotaryKnob.tsx          # Interactive drag-to-turn rotary potentiometer
│   │   ├── RotarySelector.tsx      # Stepped rotational selector switch
│   │   └── ToggleSwitch.tsx        # Metal toggle switch with LED state
│   ├── export/
│   │   └── ExportPanel.tsx         # Download hub for .sng, notes.chart, and full ZIP
│   ├── highway/
│   │   ├── HighwayScene.tsx        # Three.js Canvas container and render loop
│   │   ├── NoteRenderer.ts         # High-performance note gem and sustain geometry generator
│   │   └── StrikeBar.ts            # Fret strike line, hit flares, and receptor logic
│   ├── navigation/
│   │   └── WorkflowStepper.tsx     # 4-stage rack bay navigation header
│   ├── rack/
│   │   ├── CalibrationBay.tsx      # DSP & Game Design heuristic knobs panel
│   │   ├── LedIndicator.tsx        # Multi-state glowing LED lamps
│   │   ├── ModulePanel.tsx         # Brushed metal rack module frame
│   │   ├── RackChassis.tsx         # Heavy 19" studio rack chassis wrapper
│   │   └── Screw.tsx               # Industrial chassis mounting screws
│   ├── support/
│   │   └── SupportModal.tsx        # GitHub Sponsors / GPU upgrade fund modal
│   ├── telemetry/
│   │   └── PipelineTelemetry.tsx   # Live SSE stage progress bar and status readouts
│   └── upload/
│       ├── AudioDropzone.tsx       # Drag-and-drop file ingestion bay
│       └── MetadataInputs.tsx      # Song title and artist inputs
├── hooks/
│   ├── useAudioPlayer.ts       # Audio playback controller with preview stream support
│   └── useChartParser.ts       # Client-side .chart parser for highway rendering
├── lib/
│   ├── api.ts                  # Axios/Fetch API wrapper with URL resolution
│   ├── language.ts             # Internationalization dictionary (EN / PT-BR)
│   └── mechanicalClick.ts      # Web Audio mechanical switch audio feedback
└── theme/
    └── tokens.ts               # Color palettes, font definitions, and tactile styles
```

---

## 🚀 Getting Started

### Prerequisites
- **Node.js**: `v18.0.0` or higher (Node 20+ recommended)
- **npm**, **pnpm**, or **yarn**

### Installation

```bash
# Navigate to the frontend directory
cd frontend

# Install dependencies
npm install
```

### Development Server

```bash
npm run dev
```
The application will launch at `http://localhost:5173`. By default, it proxies API requests to the local backend at `http://localhost:8000`.

### Production Build

```bash
npm run build
```
Builds optimized, tree-shaken static assets into `frontend/dist/`.

### Linting

```bash
npm run lint
```
Runs high-performance linting using [Oxlint](https://oxc.rs/).

---

## 🌐 Environment Variables

| Variable | Default | Description |
| :--- | :--- | :--- |
| `VITE_API_BASE_URL` | `""` (Relative path) | Backend API base URL. Leave empty when serving behind the FastAPI reverse proxy or in production. |

Example `.env.local`:
```env
VITE_API_BASE_URL=http://localhost:8000
```

---

## 🎮 3D Highway Engine Details

The 3D note highway is implemented using native **Three.js** inside `HighwayScene.tsx`:

- **Perspective Camera**: Fixed isometric perspective angled at `45°` over the fretboard with subtle camera lag during tempo shifts.
- **Fret Rails & Grid**: 5 distinct lanes corresponding to the physical frets:
  - 🟢 **Green** (`fret 0`)
  - 🔴 **Red** (`fret 1`)
  - 🟡 **Yellow** (`fret 2`)
  - 🔵 **Blue** (`fret 3`)
  - 🟠 **Orange** (`fret 4`)
- **Note Gems (`NoteRenderer.ts`)**: Rendered using beveled cylinder geometries with metallic shaders and dynamic emissive glowing materials.
- **Sustain Trails**: Translucent extruded ribbon meshes anchored to the parent note gem, respecting the 24-tick release margin.
- **Strike Bar (`StrikeBar.ts`)**: Bottom strike line featuring particle rings and luminous pulse effects triggered when note onsets cross the zero-tick threshold.
- **Playback Synchronization**: Managed by `useAudioPlayer.ts`, mapping Web Audio API playback timestamps to chart ticks using the parsed `SyncTrack` BPM changes.

---

## 🔊 Mechanical Haptic Feedback

To elevate user immersion, every knob tick, toggle flip, and button press synthesizes an authentic physical click sound via the **Web Audio API**:

```typescript
import { playMechanicalClick } from './lib/mechanicalClick';

// Light switch toggle
playMechanicalClick('toggle');

// Heavy push button latch
playMechanicalClick('heavy');

// Rotary knob detent tick
playMechanicalClick('knob');
```

No external MP3/WAV assets are required; all acoustic waveforms are procedurally generated with micro-decay envelope filters.

---

## 🤝 Contributing

Contributions to the frontend are welcome! Please ensure:
1. All TypeScript types are strictly defined (`npm run build` succeeds).
2. Code follows existing styling and passes `npm run lint`.
3. Mechanical controls maintain skeuomorphic design consistency with the studio rack chassis.
