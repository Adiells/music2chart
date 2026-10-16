import { cn } from '../../lib/utils';
import type { LedColorName } from '../../theme/tokens';
import { PushButton } from '../controls/PushButton';
import { LedIndicator } from '../rack/LedIndicator';
import { ModulePanel } from '../rack/ModulePanel';

export interface AboutPageProps {
  onReturnToWorkstation?: () => void;
  className?: string;
}

interface PipelineStageDoc {
  step: string;
  code: string;
  title: string;
  engine: string;
  led: LedColorName;
  description: string;
  spec: string;
}

interface KnobDoc {
  channel: string;
  name: string;
  range: string;
  defaultVal: string;
  apiParam: string;
  led: LedColorName;
  purpose: string;
  mechanics: string;
}

interface SwitchDoc {
  channel: string;
  name: string;
  states: string;
  defaultVal: string;
  apiParam: string;
  led: LedColorName;
  purpose: string;
  mechanics: string;
}

interface PresetDoc {
  id: string;
  name: string;
  targetGenre: string;
  led: LedColorName;
  knobsSummary: string;
  switchesSummary: string;
  rationale: string;
}

const PIPELINE_DOCS: readonly PipelineStageDoc[] = [
  {
    step: 'STAGE 01',
    code: 'DSP-STEM',
    title: 'Demucs v4 Stem Separation',
    engine: 'META HTDEMUCS (HYBRID TRANSFORMER)',
    led: 'orange',
    description:
      'Isolates the electric/lead guitar stem from full stereo masters (MP3, WAV, FLAC, OGG) prior to pitch extraction, eliminating drum transients, vocal formants, and sub-bass bleed.',
    spec: '44.1 / 48 kHz FP32 Tensor -> Isolated Guitar Stem + Automatic Mono Fallback',
  },
  {
    step: 'STAGE 02',
    code: 'DSP-SYNC',
    title: 'BeatNet & Librosa Tempo Tracking',
    engine: 'VARIABLE BPM & 192 PPQ TICK GRID',
    led: 'yellow',
    description:
      'Extracts dynamic tempo maps, beat positions, and meter signatures ([SyncTrack]). Converts continuous audio timestamps (seconds) into discrete 192 Pulses-Per-Quarter-Note (PPQ) grid ticks.',
    spec: 'Resolution: 192 PPQ | Milli-BPM Serialization (e.g. 120.0 BPM -> B 120000)',
  },
  {
    step: 'STAGE 03',
    code: 'AI-MIDI',
    title: 'Spotify Basic Pitch Transcription',
    engine: 'POLYPHONIC CNN AUDIO-TO-MIDI',
    led: 'blue',
    description:
      'Predicts polyphonic note events (MIDI pitch 0–127, onset time, offset time, and normalized confidence amplitude) directly from the isolated guitar stem.',
    spec: 'Output: NoteEvent(start_time, end_time, pitch, amplitude [0.0..1.0])',
  },
  {
    step: 'STAGE 04',
    code: 'DSP-FILT',
    title: 'Harmonic Overtone Suppression',
    engine: 'SPECTRAL & OCTAVE ARTIFACT FILTER',
    led: 'red',
    description:
      'Removes high-gain guitar distortion harmonics (octave +12 semitones and fifth +19 semitones) and sub-threshold pick noise that would otherwise produce false multi-note chords.',
    spec: 'Suppresses concurrent overtone spikes within 25 ms of fundamental onset',
  },
  {
    step: 'STAGE 05',
    code: 'MAP-5FRT',
    title: 'Game Design Mapping Engine',
    engine: 'TESSITURA PROJECTION & HOPO HEURISTICS',
    led: 'green',
    description:
      'Fuses string-roll micro-delays into unified chords, snaps onsets to valid 192 PPQ subdivisions, projects MIDI pitches onto the 5 Clone Hero frets (Green 0 -> Orange 4), and calculates HOPOs, sustains, and Star Power.',
    spec: 'Subdivisions: 1/4 (192), 1/8 (96), 1/12 (64), 1/16 (48), 1/24 (32), 1/32 (24)',
  },
  {
    step: 'STAGE 06',
    code: 'PKG-BIN',
    title: 'ChartWriter & SngPacker Serialization',
    engine: 'CLONE HERO .CHART & SONGBINARY V1',
    led: 'starpower',
    description:
      'Generates industry-standard text notes.chart, song.ini metadata, and Vorbis song.ogg streams, then packs them into a single Little-Endian .sng binary package with XOR payload masking.',
    spec: 'Outputs: .sng (SNGPKG v1), notes.chart (UTF-8), and .zip full archive',
  },
];

const KNOB_DOCS: readonly KnobDoc[] = [
  {
    channel: 'POT-01',
    name: 'Chord Fusion Window',
    range: '10 .. 60 MS (STEP 1 MS)',
    defaultVal: '35 MS (0.035 S)',
    apiParam: 'chord_fusion_window_s',
    led: 'green',
    purpose: 'Prevents physical guitar string-roll strumming delays from rendering as unplayable micro-staircases.',
    mechanics:
      'When a guitarist strums across multiple strings, individual string onsets arrive 10–35 ms apart. All note onsets detected within this sliding window are fused into a single unified chord hit at the earliest onset tick before 192 PPQ quantization.',
  },
  {
    channel: 'POT-02',
    name: 'Noise Gate / Sensitivity',
    range: '0.00 .. 0.50 (STEP 0.01)',
    defaultVal: '0.10',
    apiParam: 'min_amplitude',
    led: 'red',
    purpose: 'Filters out ghost notes, palm-mute transients, string buzz, and background stem bleed.',
    mechanics:
      'Discards any transcribed NoteEvent whose normalized Basic Pitch velocity/confidence falls below this threshold. Higher values (0.20–0.35) yield cleaner rhythm charts; lower values (0.05–0.10) preserve delicate legato and tapping nuances.',
  },
  {
    channel: 'POT-03',
    name: 'Creativity Factor',
    range: '0 .. 100 % (STEP 1 %)',
    defaultVal: '50 % (0.50)',
    apiParam: 'creativity',
    led: 'yellow',
    purpose: 'Balances strict positional fret economy against wide, expressive solo movement across Green -> Orange.',
    mechanics:
      'Controls dynamic pitch-to-fret projection spread across the 1–2 measure sliding tessitura window. Lower values keep rhythm riffs anchored tightly on lower frets; higher values expand melodic contour transitions and solo lane traversal.',
  },
  {
    channel: 'POT-04',
    name: 'HOPO Distance Cutoff',
    range: '32 .. 192 TICKS (STEP 4)',
    defaultVal: '96 TICKS (1/8 NOTE)',
    apiParam: 'hopo_threshold',
    led: 'blue',
    purpose: 'Defines the maximum rhythmic interval between consecutive single notes that automatically become Hammer-Ons / Pull-Offs.',
    mechanics:
      'At 192 PPQ, 65 ticks is the classic Guitar Hero natural HOPO cutoff (~1/12th note), while 96 ticks covers full eighth-note runs. Notes within this tick delta on a different fret receive HOPO state and explicit N 5 0 forcers when needed.',
  },
  {
    channel: 'POT-05',
    name: 'Sustain Tail Cutoff',
    range: '0 .. 256 TICKS (STEP 6)',
    defaultVal: '90 TICKS (~1/8 NOTE)',
    apiParam: 'min_sustain_ticks',
    led: 'open',
    purpose: 'Prevents short staccato eighth/sixteenth notes from cluttering the highway with stubby sustain tails.',
    mechanics:
      'Any note whose quantized duration is shorter than this tick threshold has its sustain_length clamped to 0 (immediate impact gem). Notes meeting or exceeding the cutoff render full sustain ribbons minus the mandatory 24-tick release margin.',
  },
  {
    channel: 'POT-06',
    name: 'BPM / Scroll Scale',
    range: '0.50 .. 2.00 X (STEP 0.05X)',
    defaultVal: '1.00 X',
    apiParam: 'bpm_scale',
    led: 'orange',
    purpose: 'Scales the internal [SyncTrack] tempo grid multiplier to fine-tune highway scroll speed and subdivision density.',
    mechanics:
      'Multiplies detected BPM markers by the chosen factor before grid snapping. Useful for half-time feel tracks (0.50x–0.75x) or double-time metal transcriptions (1.25x–2.00x).',
  },
];

const SWITCH_DOCS: readonly SwitchDoc[] = [
  {
    channel: 'SW-01',
    name: 'Open Notes',
    states: 'ALLOW (UP) // MUTE (DOWN)',
    defaultVal: 'MUTE (DISABLE_OPEN = TRUE)',
    apiParam: 'disable_open_notes',
    led: 'open',
    purpose: 'Controls whether lowest-register pitches emit purple Open Strum bars (N 7 0) or standard Green (N 0 0) gems.',
    mechanics:
      'Lead guitar charts in Clone Hero traditionally restrict purple Open notes to bass/rhythm tracks or heavy djent breakdowns. Keeping Open Notes muted remaps sub-bass roots to Fret 0 (Green) to preserve classic 5-fret hand positioning.',
  },
  {
    channel: 'SW-02',
    name: 'Fast Runs',
    states: 'COLLAPSE (UP) // CHORDS (DOWN)',
    defaultVal: 'COLLAPSE (TRUE)',
    apiParam: 'collapse_fast_runs',
    led: 'green',
    purpose: 'Protects player ergonomics by preventing multi-fret chords inside rapid sixteenth-note shred passages.',
    mechanics:
      'When enabled, any tick whose distance to the preceding or succeeding onset is <= 48 ticks (1/16 note at 192 PPQ) has concurrent chord notes collapsed into a single dominant melodic root gem.',
  },
  {
    channel: 'SW-03',
    name: 'Motif Lock',
    states: 'LOCKED (UP) // FREE (DOWN)',
    defaultVal: 'LOCKED (TRUE)',
    apiParam: 'consistent_patterns',
    led: 'blue',
    purpose: 'Ensures repeating verse and chorus guitar riffs map to identical fret color sequences throughout the song.',
    mechanics:
      'Applies pattern-hashing and local root anchoring across 1–2 measure windows so slight pitch vibrato or Basic Pitch confidence fluctuations never shift a recurring riff onto different fret buttons.',
  },
  {
    channel: 'SW-04',
    name: 'Auto-Calibrate BPM',
    states: 'AUTO (UP) // RAW (DOWN)',
    defaultVal: 'AUTO (TRUE)',
    apiParam: 'auto_calibrate_bpm',
    led: 'orange',
    purpose: 'Automatically folds excessive double-time tempo detections (> 160.0 BPM) into comfortable highway scroll speeds.',
    mechanics:
      'When BeatNet/Librosa locks onto eighth-note hi-hats at 180–240 BPM, AUTO mode halves the base tempo map into the 90–120 BPM range while preserving exact note timing in seconds.',
  },
  {
    channel: 'SW-05',
    name: 'Sustain Merge',
    states: 'MERGE (UP) // STACCATO (DOWN)',
    defaultVal: 'MERGE (TRUE)',
    apiParam: 'merge_sustained_notes',
    led: 'yellow',
    purpose: 'Fuses artificial re-triggers caused by guitar vibrato or ringing string decay into a single continuous hold.',
    mechanics:
      'When Basic Pitch splits a long ringing bend or vibrato note into adjacent identical-pitch segments, MERGE coalesces them into one sustained note head prior to sustain tail calculation.',
  },
  {
    channel: 'SW-06',
    name: 'Triad Chords',
    states: 'TRIADS (UP) // POWER (DOWN)',
    defaultVal: 'POWER (MAX_FRETS = 2)',
    apiParam: 'max_frets (3 vs 2)',
    led: 'red',
    purpose: 'Selects between canonical 2-button Power Chords (dyads) and full 3-button Triads on accented beats.',
    mechanics:
      'POWER mode clamps all simultaneous hits to ergonomic 2-note dyads (0+1, 0+2, 1+2, 1+3, 2+3, 2+4, 3+4). TRIADS mode permits 3-note chords (0+1+2, 0+2+3, 1+2+3, 2+3+4) exclusively on accented beats with sustain >= 96 ticks. 4- and 5-note chords are strictly prohibited.',
  },
];

const PRESET_DOCS: readonly PresetDoc[] = [
  {
    id: 'POS 01 // STANDARD',
    name: 'Standard (Balanced Studio Default)',
    targetGenre: 'CLASSIC ROCK / ALTERNATIVE / GENERAL LEAD',
    led: 'green',
    knobsSummary: 'FUSION 35MS | GATE 0.10 | CREAT 50% | HOPO 96T | SUS 90T | BPM 1.00X',
    switchesSummary: 'OPEN: MUTE | RUNS: COLLAPSE | MOTIF: LOCKED | AUTO BPM: AUTO | MERGE: ON | CHORDS: POWER (2)',
    rationale:
      'Reference all-rounder profile. Balances clean 2-note power chords on rhythm sections with responsive eighth/sixteenth-note HOPO runs and strict motif consistency.',
  },
  {
    id: 'POS 02 // STRICT RHYTHM',
    name: 'Strict Rhythm (Tight Riffing & Downstrokes)',
    targetGenre: 'PUNK / HARD ROCK / RHYTHM GUITAR',
    led: 'yellow',
    knobsSummary: 'FUSION 40MS | GATE 0.20 | CREAT 15% | HOPO 64T | SUS 120T | BPM 1.00X',
    switchesSummary: 'OPEN: MUTE | RUNS: COLLAPSE | MOTIF: LOCKED | AUTO BPM: AUTO | MERGE: ON | CHORDS: POWER (2)',
    rationale:
      'Raises the Noise Gate (0.20) and Chord Fusion Window (40 ms) while tightening the HOPO cutoff (64 ticks) so palm-muted eighth-note chugs remain deliberate strummed patterns.',
  },
  {
    id: 'POS 03 // DYNAMIC SOLO',
    name: 'Dynamic Solo (Virtuoso Lead & Shred)',
    targetGenre: 'PROG METAL / SHRED / GUITAR SOLOS',
    led: 'red',
    knobsSummary: 'FUSION 30MS | GATE 0.08 | CREAT 85% | HOPO 128T | SUS 60T | BPM 1.00X',
    switchesSummary: 'OPEN: MUTE | RUNS: CHORDS | MOTIF: FREE | AUTO BPM: AUTO | MERGE: STACCATO | CHORDS: POWER (2)',
    rationale:
      'Lowers the Noise Gate (0.08) to capture fast legato tapping, expands Creativity (85%) and HOPO cutoff (128 ticks) for sweeping fluid runs, and disables Sustain Merge to preserve rapid alternate-picking articulation.',
  },
  {
    id: 'POS 04 // MELODIC',
    name: 'Melodic (Expressive Phrasing & Sustains)',
    targetGenre: 'INDIE / BLUES ROCK / POST-ROCK / SYNTH LEAD',
    led: 'blue',
    knobsSummary: 'FUSION 35MS | GATE 0.12 | CREAT 65% | HOPO 96T | SUS 72T | BPM 1.00X',
    switchesSummary: 'OPEN: MUTE | RUNS: COLLAPSE | MOTIF: LOCKED | AUTO BPM: AUTO | MERGE: ON | CHORDS: POWER (2)',
    rationale:
      'Lowers the Sustain Tail Cutoff (72 ticks) and enables Sustain Merge so vocal-like guitar bends and ringing melodic hooks render with smooth, expressive sustain ribbons.',
  },
  {
    id: 'POS 05 // CHORD HEAVY',
    name: 'Chord Heavy (Full Triads & Open Breakdowns)',
    targetGenre: 'DJENT / MODERN METAL / POLYPHONIC PROG',
    led: 'open',
    knobsSummary: 'FUSION 45MS | GATE 0.15 | CREAT 35% | HOPO 64T | SUS 96T | BPM 1.00X',
    switchesSummary: 'OPEN: ALLOW | RUNS: CHORDS | MOTIF: LOCKED | AUTO BPM: AUTO | MERGE: ON | CHORDS: TRIADS (3)',
    rationale:
      'Widens the Chord Fusion Window (45 ms) to capture wide multi-string voicings, enables 3-note Triad Chords on accented beats, and unlocks purple Open Notes (N 7 0) for low-tuned breakdown riffs.',
  },
];

const GRID_SUBDIVISIONS: readonly { note: string; ratio: string; ticks: string; usage: string }[] = [
  { note: 'Quarter Note', ratio: '1/4 BEAT', ticks: '192 TICKS', usage: 'Primary beat anchor & downbeat pulse' },
  { note: 'Eighth Note', ratio: '1/8 BEAT', ticks: '96 TICKS', usage: 'Standard rock chugs, triad minimum sustain' },
  { note: 'Eighth Triplet', ratio: '1/12 BEAT', ticks: '64 TICKS', usage: 'Shuffle grooves & natural HOPO boundary' },
  { note: 'Sixteenth Note', ratio: '1/16 BEAT', ticks: '48 TICKS', usage: 'Fast-run chord collapse threshold' },
  { note: 'Sixteenth Triplet', ratio: '1/24 BEAT', ticks: '32 TICKS', usage: 'Sextuplet shred runs & rapid fills' },
  { note: 'Thirty-Second Note', ratio: '1/32 BEAT', ticks: '24 TICKS', usage: 'Minimum note spacing & sustain release margin' },
];

/**
 * Exhaustive English Technical Reference Manual & Architecture Specification
 * for the music2chart Studio Workstation.
 */
export function AboutPage({ onReturnToWorkstation, className }: AboutPageProps) {
  return (
    <div className={cn('flex flex-col gap-4', className)}>
      {/* Top Manual Banner */}
      <div className="flex flex-wrap items-center justify-between gap-4 border border-hw-border bg-module px-6 py-4 shadow-bevel">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-3">
            <span className="silk-wide text-fret-green">MANUAL REV 1.0 // SPECIFICATION DOCUMENT</span>
            <span className="h-3 w-px bg-hw-border" aria-hidden="true" />
            <span className="silk-wide">CLONE HERO 192 PPQ &amp; SONGBINARY V1 STANDARD</span>
          </div>
          <h1 className="font-grotesk text-base font-bold uppercase tracking-silk-wide text-silk sm:text-lg">
            MUSIC2CHART // TECHNICAL REFERENCE &amp; DSP CALIBRATION MANUAL
          </h1>
          <p className="font-mono text-[11px] leading-relaxed tracking-silk text-silk-neutral">
            Complete operational documentation for the AI audio-to-chart synthesis pipeline, 6-channel analog
            potentiometer calibration bank, 6-channel heuristic routing matrix, and binary packaging containers.
          </p>
        </div>

        {onReturnToWorkstation ? (
          <PushButton
            size="md"
            variant="master"
            label="Return To Workstation"
            sublabel="Open Studio Console"
            led="green"
            ledOn
            onClick={onReturnToWorkstation}
          />
        ) : null}
      </div>

      {/* ================================================================== */}
      {/* MODULE 01: SYSTEM PIPELINE & ARCHITECTURE                          */}
      {/* ================================================================== */}
      <ModulePanel
        code="DOC-01"
        title="System Pipeline & Architecture"
        headerRight={<LedIndicator color="green" on size="xs" label="6-STAGE DSP" />}
        footer="SIGNAL FLOW: RAW AUDIO -> HTDEMUCS -> BEATNET (192 PPQ) -> BASIC PITCH -> HARMONIC FILTER -> 5-FRET MAPPER -> .SNG / .CHART"
      >
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
          {PIPELINE_DOCS.map((item) => (
            <div
              key={item.code}
              className="flex flex-col justify-between gap-2.5 border border-hw-border bg-chassis p-3.5 shadow-recess"
            >
              <div className="flex items-center justify-between border-b border-hw-border pb-2">
                <div className="flex items-center gap-2">
                  <span className="border border-hw-screw bg-panel px-1.5 py-0.5 font-mono text-[9px] font-semibold uppercase tracking-silk text-silk">
                    {item.step}
                  </span>
                  <span className="silk-wide text-[9px]">{item.code}</span>
                </div>
                <LedIndicator color={item.led} on size="xs" />
              </div>

              <div>
                <h3 className="font-mono text-xs font-bold uppercase tracking-silk text-silk">
                  {item.title}
                </h3>
                <div className="mt-0.5 font-mono text-[9px] uppercase tracking-silk text-fret-yellow">
                  {item.engine}
                </div>
                <p className="mt-2 font-mono text-[10px] leading-relaxed tracking-silk text-silk-neutral">
                  {item.description}
                </p>
              </div>

              <div className="border-t border-hw-border pt-2 font-mono text-[9px] uppercase tracking-silk text-silk-dim">
                {item.spec}
              </div>
            </div>
          ))}
        </div>
      </ModulePanel>

      {/* ================================================================== */}
      {/* MODULE 02: 6-CH ANALOG POTENTIOMETER BANK                          */}
      {/* ================================================================== */}
      <ModulePanel
        code="DOC-02"
        title="6-Ch Analog Potentiometer Bank // Rotary Knob Specifications"
        headerRight={<LedIndicator color="yellow" on size="xs" label="POT-01..06" />}
        footer="INTERACTION: DRAG VERTICAL OR HORIZONTAL | HOLD SHIFT FOR FINE PRECISION | DOUBLE-CLICK TO RESTORE FACTORY DEFAULT"
      >
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
          {KNOB_DOCS.map((knob) => (
            <div
              key={knob.channel}
              className="flex flex-col justify-between gap-2.5 border border-hw-border bg-chassis p-3.5 shadow-recess"
            >
              <div className="flex items-center justify-between border-b border-hw-border pb-2">
                <div className="flex items-center gap-2">
                  <span className="border border-hw-screw bg-panel px-1.5 py-0.5 font-mono text-[9px] font-semibold uppercase tracking-silk text-silk">
                    {knob.channel}
                  </span>
                  <span className="font-mono text-xs font-bold uppercase tracking-silk text-silk">
                    {knob.name}
                  </span>
                </div>
                <LedIndicator color={knob.led} on size="xs" />
              </div>

              <div className="grid grid-cols-2 gap-2 border border-hw-border/70 bg-panel px-2.5 py-1.5 font-mono text-[9px] uppercase tracking-silk">
                <div>
                  <span className="text-silk-dim">RANGE: </span>
                  <span className="tabular-nums text-silk">{knob.range}</span>
                </div>
                <div>
                  <span className="text-silk-dim">DEFAULT: </span>
                  <span className="tabular-nums text-fret-green">{knob.defaultVal}</span>
                </div>
              </div>

              <div className="flex flex-col gap-1.5 font-mono text-[10px] leading-relaxed tracking-silk">
                <div className="font-semibold text-silk">{knob.purpose}</div>
                <p className="text-silk-neutral">{knob.mechanics}</p>
              </div>

              <div className="border-t border-hw-border pt-1.5 font-mono text-[9px] uppercase tracking-silk text-silk-dim">
                API FIELD: <span className="text-silk">{knob.apiParam}</span>
              </div>
            </div>
          ))}
        </div>
      </ModulePanel>

      {/* ================================================================== */}
      {/* MODULE 03: 6-CH HEURISTIC ROUTING MATRIX                           */}
      {/* ================================================================== */}
      <ModulePanel
        code="DOC-03"
        title="6-Ch Heuristic Routing Matrix // Toggle Switch Specifications"
        headerRight={<LedIndicator color="blue" on size="xs" label="SW-01..06" />}
        footer="BAT-HANDLE TOGGLE SWITCHES CONTROL BOOLEAN ERGONOMIC CONSTRAINTS IN THE CLONE HERO MAPPING ENGINE"
      >
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
          {SWITCH_DOCS.map((sw) => (
            <div
              key={sw.channel}
              className="flex flex-col justify-between gap-2.5 border border-hw-border bg-chassis p-3.5 shadow-recess"
            >
              <div className="flex items-center justify-between border-b border-hw-border pb-2">
                <div className="flex items-center gap-2">
                  <span className="border border-hw-screw bg-panel px-1.5 py-0.5 font-mono text-[9px] font-semibold uppercase tracking-silk text-silk">
                    {sw.channel}
                  </span>
                  <span className="font-mono text-xs font-bold uppercase tracking-silk text-silk">
                    {sw.name}
                  </span>
                </div>
                <LedIndicator color={sw.led} on size="xs" />
              </div>

              <div className="grid grid-cols-2 gap-2 border border-hw-border/70 bg-panel px-2.5 py-1.5 font-mono text-[9px] uppercase tracking-silk">
                <div>
                  <span className="text-silk-dim">POSITIONS: </span>
                  <span className="text-silk">{sw.states}</span>
                </div>
                <div>
                  <span className="text-silk-dim">DEFAULT: </span>
                  <span className="text-fret-green">{sw.defaultVal}</span>
                </div>
              </div>

              <div className="flex flex-col gap-1.5 font-mono text-[10px] leading-relaxed tracking-silk">
                <div className="font-semibold text-silk">{sw.purpose}</div>
                <p className="text-silk-neutral">{sw.mechanics}</p>
              </div>

              <div className="border-t border-hw-border pt-1.5 font-mono text-[9px] uppercase tracking-silk text-silk-dim">
                API FIELD: <span className="text-silk">{sw.apiParam}</span>
              </div>
            </div>
          ))}
        </div>
      </ModulePanel>

      {/* ================================================================== */}
      {/* MODULE 04: MAPPING PRESET PROFILES                                 */}
      {/* ================================================================== */}
      <ModulePanel
        code="DOC-04"
        title="Mapping Preset Profiles // Detented Rotary Selector Matrix"
        headerRight={<LedIndicator color="orange" on size="xs" label="5 PROFILES" />}
        footer="SELECTING A PRESET ON MODULE M-02 AUTOMATICALLY CALIBRATES ALL 12 CONTROLS ON MODULE M-03"
      >
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
          {PRESET_DOCS.map((preset) => (
            <div
              key={preset.id}
              className="flex flex-col justify-between gap-2.5 border border-hw-border bg-chassis p-3.5 shadow-recess"
            >
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-hw-border pb-2">
                <div>
                  <span className="silk-wide text-[9px] text-silk-dim">{preset.id}</span>
                  <h3 className="font-mono text-xs font-bold uppercase tracking-silk text-silk">
                    {preset.name}
                  </h3>
                </div>
                <div className="flex items-center gap-2">
                  <span className="border border-hw-border bg-panel px-2 py-0.5 font-mono text-[9px] uppercase tracking-silk text-silk-neutral">
                    {preset.targetGenre}
                  </span>
                  <LedIndicator color={preset.led} on size="xs" />
                </div>
              </div>

              <p className="font-mono text-[10px] leading-relaxed tracking-silk text-silk-neutral">
                {preset.rationale}
              </p>

              <div className="flex flex-col gap-1 border border-hw-border/70 bg-panel p-2 font-mono text-[9px] tabular-nums uppercase tracking-silk">
                <div className="text-fret-green">KNOBS // {preset.knobsSummary}</div>
                <div className="text-starpower">SWITCHES // {preset.switchesSummary}</div>
              </div>
            </div>
          ))}
        </div>
      </ModulePanel>

      {/* ================================================================== */}
      {/* MODULE 05 & MODULE 06 SIDE-BY-SIDE                                 */}
      {/* ================================================================== */}
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-12">
        {/* MODULE 05: CLONE HERO PLAYABILITY SPECIFICATION */}
        <ModulePanel
          code="DOC-05"
          title="Clone Hero Playability Specification (192 PPQ)"
          className="xl:col-span-7"
          headerRight={<LedIndicator color="starpower" on size="xs" label="192 PPQ" />}
          footer="ALL GENERATED CHARTS ENFORCE OFFICIAL CLONE HERO & GUITAR HERO ENGINE CONSTRAINTS"
        >
          <div className="flex flex-col gap-3">
            {/* Subdivision Table */}
            <div className="overflow-x-auto border border-hw-border bg-chassis shadow-recess">
              <table className="w-full border-collapse text-left font-mono text-[10px] uppercase tracking-silk">
                <thead>
                  <tr className="border-b border-hw-border bg-panel text-silk-dim">
                    <th className="px-3 py-2">Musical Subdivision</th>
                    <th className="px-3 py-2">Meter Ratio</th>
                    <th className="px-3 py-2">Grid Delta (192 PPQ)</th>
                    <th className="px-3 py-2">Engine Application</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-hw-border/60">
                  {GRID_SUBDIVISIONS.map((sub) => (
                    <tr key={sub.ratio} className="text-silk">
                      <td className="px-3 py-1.5 font-semibold">{sub.note}</td>
                      <td className="px-3 py-1.5 tabular-nums text-fret-yellow">{sub.ratio}</td>
                      <td className="px-3 py-1.5 tabular-nums text-fret-green">{sub.ticks}</td>
                      <td className="px-3 py-1.5 text-silk-neutral">{sub.usage}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Core Engine Rules */}
            <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
              <div className="border border-hw-border bg-chassis p-3 shadow-recess">
                <div className="font-mono text-[10px] font-bold uppercase tracking-silk text-fret-green">
                  24-TICK RE-STRUM RELEASE MARGIN
                </div>
                <p className="mt-1 font-mono text-[10px] leading-relaxed tracking-silk text-silk-neutral">
                  Every sustained note subtracts a mandatory 24-tick (1/32 note) release gap before the next note
                  onset. This prevents sustain tails from overlapping subsequent note heads and guarantees clean
                  re-strum registration.
                </p>
              </div>

              <div className="border border-hw-border bg-chassis p-3 shadow-recess">
                <div className="font-mono text-[10px] font-bold uppercase tracking-silk text-fret-yellow">
                  HOPO &amp; STRUM FORCERS (N 5 0 / N 6 0)
                </div>
                <p className="mt-1 font-mono text-[10px] leading-relaxed tracking-silk text-silk-neutral">
                  In rapid single-note runs, note 1 is anchored as a Strum note while notes 2..N emit explicit
                  HOPO force modifiers (N 5 0). Repeated notes on the same fret emit Strum forcers (N 6 0) to
                  override native engine auto-HOPO states.
                </p>
              </div>
            </div>
          </div>
        </ModulePanel>

        {/* MODULE 06: OUTPUT CONTAINERS & COMPATIBILITY */}
        <ModulePanel
          code="DOC-06"
          title="Output Containers & Binary Compatibility"
          className="xl:col-span-5"
          headerRight={<LedIndicator color="green" on size="xs" label="SNGPKG V1" />}
          footer="COMPATIBLE WITH CLONE HERO (V1.0+) AND YARG (YET ANOTHER RHYTHM GAME)"
        >
          <div className="flex flex-col gap-3">
            <div className="border border-hw-border bg-chassis p-3 shadow-recess">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-bold uppercase tracking-silk text-fret-green">
                  .SNG // SONGBINARY V1 CONTAINER
                </span>
                <span className="border border-hw-screw bg-panel px-1.5 py-0.5 font-mono text-[8px] uppercase tracking-silk text-silk">
                  LITTLE-ENDIAN XOR
                </span>
              </div>
              <p className="mt-1.5 font-mono text-[10px] leading-relaxed tracking-silk text-silk-neutral">
                Single-file binary package starting with the 6-byte ASCII magic header &quot;SNGPKG&quot; (uint32
                version = 1), followed by a 16-byte xorMask, length-prefixed UTF-8 metadata pairs, FileIndex
                offsets, and uncompressed XOR-masked payloads (notes.chart, song.ini, song.ogg) for zero-copy
                memory-mapped streaming:
              </p>
              <pre className="mt-2 overflow-x-auto border border-hw-border bg-[#07080A] p-2 font-mono text-[9px] leading-4 text-silk">
                {`xor_key = xor_mask[i % 16] ^ (i & 0xFF)\nmasked[i] = file_bytes[i] ^ xor_key`}
              </pre>
            </div>

            <div className="border border-hw-border bg-chassis p-3 shadow-recess">
              <div className="font-mono text-xs font-bold uppercase tracking-silk text-fret-blue">
                .CHART // 192 PPQ STRUCTURED TEXT SPECIFICATION
              </div>
              <p className="mt-1 font-mono text-[10px] leading-relaxed tracking-silk text-silk-neutral">
                Human-readable section-delimited file containing [Song] metadata, [SyncTrack] milli-BPM and time
                signature markers, [Events] navigable practice sections (Intro, Verse, Chorus, Solo), and
                [ExpertSingle] note events (N 0..4, N 5/6 modifiers, N 7 Open, and S 2 Star Power phrases).
              </p>
            </div>

            <div className="border border-hw-border bg-chassis p-3 shadow-recess">
              <div className="font-mono text-xs font-bold uppercase tracking-silk text-fret-orange">
                .ZIP // FULL STUDIO PACKAGE ARCHIVE
              </div>
              <p className="mt-1 font-mono text-[10px] leading-relaxed tracking-silk text-silk-neutral">
                Standard deflated archive bundling notes.chart, song.ini, and Vorbis-encoded song.ogg for direct
                extraction into the Clone Hero Songs directory or external chart editors (Moonscraper).
              </p>
            </div>
          </div>
        </ModulePanel>
      </div>
    </div>
  );
}
