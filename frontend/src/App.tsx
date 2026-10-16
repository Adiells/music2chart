import { useCallback, useState } from 'react';
import {
  AboutPage,
  AudioDropzone,
  CalibrationBay,
  ExportPanel,
  HighwayScene,
  LedIndicator,
  MetadataInputs,
  ModulePanel,
  NpsGraph,
  PipelineTelemetry,
  PushButton,
  RackChassis,
  RotarySelector,
  StatsCard,
  TempoDisplay,
  WaveformBar,
} from './components';
import type {
  CalibrationState,
  DerivedTrackMeta,
  RotarySelectorOption,
  TrackMetadataState,
} from './components';
import { useAudioPlayer } from './hooks/useAudioPlayer';
import { useChartParser } from './hooks/useChartParser';
import { getApiUrl } from './lib/api';

type PresetId = 'standard' | 'strict_rhythm' | 'dynamic_solo' | 'melodic' | 'chord_heavy';
type ActiveView = 'workstation' | 'about';

const PRESET_OPTIONS: readonly RotarySelectorOption<PresetId>[] = [
  { value: 'standard', label: 'Standard' },
  { value: 'strict_rhythm', label: 'Strict Rhythm' },
  { value: 'dynamic_solo', label: 'Dynamic Solo' },
  { value: 'melodic', label: 'Melodic' },
  { value: 'chord_heavy', label: 'Chord Heavy' },
];

const PRESET_CALIBRATION_MAP: Record<PresetId, CalibrationState> = {
  standard: {
    fusionMs: 35,
    noiseGateSensitivity: 0.1,
    creativity: 50,
    hopoThreshold: 96,
    minSustainTicks: 90,
    bpmScale: 1.0,
    disableOpenNotes: true,
    collapseFastRuns: true,
    consistentPatterns: true,
    autoCalibrateBpm: true,
    mergeSustainedNotes: true,
    allowTriads: false,
  },
  strict_rhythm: {
    fusionMs: 40,
    noiseGateSensitivity: 0.2,
    creativity: 15,
    hopoThreshold: 64,
    minSustainTicks: 120,
    bpmScale: 1.0,
    disableOpenNotes: true,
    collapseFastRuns: true,
    consistentPatterns: true,
    autoCalibrateBpm: true,
    mergeSustainedNotes: true,
    allowTriads: false,
  },
  dynamic_solo: {
    fusionMs: 30,
    noiseGateSensitivity: 0.08,
    creativity: 85,
    hopoThreshold: 128,
    minSustainTicks: 60,
    bpmScale: 1.0,
    disableOpenNotes: true,
    collapseFastRuns: false,
    consistentPatterns: false,
    autoCalibrateBpm: true,
    mergeSustainedNotes: false,
    allowTriads: false,
  },
  melodic: {
    fusionMs: 35,
    noiseGateSensitivity: 0.12,
    creativity: 65,
    hopoThreshold: 96,
    minSustainTicks: 72,
    bpmScale: 1.0,
    disableOpenNotes: true,
    collapseFastRuns: true,
    consistentPatterns: true,
    autoCalibrateBpm: true,
    mergeSustainedNotes: true,
    allowTriads: false,
  },
  chord_heavy: {
    fusionMs: 45,
    noiseGateSensitivity: 0.15,
    creativity: 35,
    hopoThreshold: 64,
    minSustainTicks: 96,
    bpmScale: 1.0,
    disableOpenNotes: false,
    collapseFastRuns: false,
    consistentPatterns: true,
    autoCalibrateBpm: true,
    mergeSustainedNotes: true,
    allowTriads: true,
  },
};

const DIFFICULTY_TIERS: readonly { level: number; label: string; tag: string }[] = [
  { level: 6, label: 'Expert', tag: 'TIER 6' },
  { level: 5, label: 'Hard', tag: 'TIER 5' },
  { level: 3, label: 'Medium', tag: 'TIER 3' },
  { level: 1, label: 'Easy', tag: 'TIER 1' },
];

interface GenerateApiResponse {
  task_id: string;
  status: string;
  message: string;
}

export default function App() {
  /* Navigation View State */
  const [activeView, setActiveView] = useState<ActiveView>('workstation');

  /* Left Rack State: Upload, Metadata, Preset, Calibration, and SSE Task */
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [metadata, setMetadata] = useState<TrackMetadataState>({
    songName: '',
    artist: '',
    genre: 'rock',
    difficulty: 6,
    maxFrets: 2,
    outputFormat: 'both',
  });
  const [preset, setPreset] = useState<PresetId>('standard');
  const [calibration, setCalibration] = useState<CalibrationState>(PRESET_CALIBRATION_MAP.standard);

  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
  const [completedTaskId, setCompletedTaskId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  /* Right Workstation State: Chart Parser & Synchronized Audio Player */
  const { chart, isDemoChart } = useChartParser(completedTaskId);

  const player = useAudioPlayer({
    taskId: completedTaskId,
    localFile: audioFile,
    fallbackDuration: chart.durationSeconds,
  });

  const handleFileSelect = useCallback((file: File | null, derived?: DerivedTrackMeta): void => {
    setAudioFile(file);
    setSubmitError(null);
    if (derived) {
      setMetadata((prev) => ({
        ...prev,
        songName: prev.songName || derived.songName,
        artist: prev.artist || derived.artist,
      }));
    }
  }, []);

  const handleMetadataChange = useCallback((nextMeta: TrackMetadataState): void => {
    setMetadata(nextMeta);
    setCalibration((prev) => ({
      ...prev,
      allowTriads: nextMeta.maxFrets >= 3,
    }));
  }, []);

  const handleCalibrationChange = useCallback((nextCal: CalibrationState): void => {
    setCalibration(nextCal);
    setMetadata((prev) => ({
      ...prev,
      maxFrets: nextCal.allowTriads ? 3 : prev.maxFrets === 1 ? 1 : 2,
    }));
  }, []);

  const handlePresetChange = useCallback((nextPreset: PresetId): void => {
    const presetCal = PRESET_CALIBRATION_MAP[nextPreset];
    setPreset(nextPreset);
    setCalibration({ ...presetCal });
    setMetadata((prev) => ({
      ...prev,
      maxFrets: presetCal.allowTriads ? 3 : 2,
    }));
  }, []);

  const handleGenerate = useCallback(async (): Promise<void> => {
    if (!audioFile || submitting) return;

    // Client-side guard against oversized payloads (>100MB) before starting upload
    const MAX_UPLOAD_SIZE = 100 * 1024 * 1024; // 100 MB
    if (audioFile.size > MAX_UPLOAD_SIZE) {
      setSubmitError(
        'Payload Too Large: O arquivo excede o limite de 100 MB. Por favor, selecione um arquivo de áudio menor.'
      );
      return;
    }

    setSubmitting(true);
    setSubmitError(null);
    player.pause();

    try {
      const form = new FormData();
      form.append('file', audioFile);
      if (metadata.songName.trim()) form.append('song_name', metadata.songName.trim());
      if (metadata.artist.trim()) form.append('artist', metadata.artist.trim());
      form.append('output_format', metadata.outputFormat);
      form.append('max_frets', String(calibration.allowTriads ? 3 : 2));
      form.append('difficulty', String(metadata.difficulty));
      form.append('genre', metadata.genre);

      // Map UI preset to backend preset profile
      const backendPreset =
        preset === 'strict_rhythm' || preset === 'dynamic_solo' ? preset : 'standard';
      form.append('preset', backendPreset);

      // 6 Knobs + 6 Switches Calibration Payload
      form.append('chord_fusion_window_s', (calibration.fusionMs / 1000).toFixed(3));
      form.append('min_amplitude', calibration.noiseGateSensitivity.toFixed(2));
      form.append('creativity', (calibration.creativity / 100).toFixed(2));
      form.append('hopo_threshold', String(calibration.hopoThreshold));
      form.append('min_sustain_ticks', String(calibration.minSustainTicks));
      form.append('bpm_scale', calibration.bpmScale.toFixed(2));
      form.append('disable_open_notes', String(calibration.disableOpenNotes));
      form.append('collapse_fast_runs', String(calibration.collapseFastRuns));
      form.append('consistent_patterns', String(calibration.consistentPatterns));
      form.append('auto_calibrate_bpm', String(calibration.autoCalibrateBpm));
      form.append('merge_sustained_notes', String(calibration.mergeSustainedNotes));

      const response = await fetch(getApiUrl('/api/v1/chart/generate'), {
        method: 'POST',
        body: form,
      });

      if (!response.ok) {
        let errorDetail = '';
        try {
          const errBody = (await response.json()) as { detail?: string | { msg?: string }[] };
          if (typeof errBody?.detail === 'string') {
            errorDetail = errBody.detail;
          } else if (Array.isArray(errBody?.detail)) {
            errorDetail = errBody.detail
              .map((d) => (typeof d === 'string' ? d : d.msg || JSON.stringify(d)))
              .join('; ');
          }
        } catch {
          // Response body was not JSON or could not be parsed
        }

        if (response.status === 413) {
          throw new Error(
            `Payload Too Large (HTTP 413): ${
              errorDetail || 'Arquivo excede o limite de 100 MB do servidor. Por favor, selecione um arquivo menor.'
            }`
          );
        }

        if (response.status === 429) {
          throw new Error(
            `Too Many Requests (HTTP 429): ${
              errorDetail || 'Servidor sobrecarregado ou fila de processamento cheia. Aguarde alguns instantes e tente novamente.'
            }`
          );
        }

        throw new Error(errorDetail || `HTTP ${response.status} submitting audio`);
      }

      const data = (await response.json()) as GenerateApiResponse;
      setActiveTaskId(data.task_id);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to dispatch generation task';
      setSubmitError(msg);
    } finally {
      setSubmitting(false);
    }
  }, [audioFile, calibration, metadata, player, preset, submitting]);

  const handleRunDemo = useCallback((): void => {
    setSubmitError(null);
    player.stop();
    setActiveTaskId(`demo-${Date.now()}`);
  }, [player]);

  const handleAbort = useCallback((): void => {
    setActiveTaskId(null);
    setSubmitting(false);
    setSubmitError(null);
  }, []);

  const handleTelemetryCompleted = useCallback((taskId: string): void => {
    setCompletedTaskId(taskId);
  }, []);

  const isBusy = submitting || (activeTaskId !== null && activeTaskId !== completedTaskId);

  return (
    <RackChassis
      brand="MUSIC2CHART"
      model="M2C-01 // DUAL-CHASSIS STUDIO WORKSTATION"
      serial="SN 2026-1016 / FW 1.0.0"
      headerRight={
        <div className="flex flex-wrap items-center gap-3">
          {/* Top Chassis View Selector */}
          <div className="flex items-center gap-1.5" role="navigation" aria-label="Chassis Mode Navigation">
            <PushButton
              size="sm"
              label="Workstation"
              sublabel="Console"
              led="green"
              ledOn={activeView === 'workstation'}
              latched={activeView === 'workstation'}
              onClick={() => setActiveView('workstation')}
            />
            <PushButton
              size="sm"
              label="Technical Manual"
              sublabel="About / Spec"
              led="blue"
              ledOn={activeView === 'about'}
              latched={activeView === 'about'}
              onClick={() => setActiveView('about')}
            />
          </div>

          <span className="hidden h-4 w-px bg-hw-border sm:inline-block" aria-hidden="true" />

          <LedIndicator
            color={player.isPlaying ? 'green' : 'blue'}
            on
            blink={player.isPlaying ? 'fast' : false}
            size="xs"
            label={player.isPlaying ? 'TRANSPORT PLAY' : 'SYNC LOCKED'}
          />
          <LedIndicator
            color={isBusy ? 'orange' : 'green'}
            on
            blink={isBusy ? 'fast' : false}
            size="xs"
            label={isBusy ? 'DSP BUSY' : 'READY'}
          />
        </div>
      }
    >
      {activeView === 'about' ? (
        <AboutPage onReturnToWorkstation={() => setActiveView('workstation')} />
      ) : (
        /* Dual-Chassis Studio Workstation Grid: Left Control Rack (5 cols) | Right 3D Highway & Audit Deck (7 cols) */
        <div className="grid grid-cols-1 items-stretch gap-3.5 xl:grid-cols-12">
          {/* ================================================================ */}
          {/* LEFT COLUMN: HARDWARE CONTROL RACK (UPLOAD, PRESETS, CALIB, SSE) */}
          {/* ================================================================ */}
          <div className="flex h-full flex-col gap-3 xl:col-span-5">
            {/* M-01: Audio Dropzone & Metadata Inputs */}
            <ModulePanel
              code="M-01"
              title="Master Ingestion & Track Metadata"
              headerRight={
                <LedIndicator
                  color={audioFile ? 'green' : 'yellow'}
                  on
                  size="xs"
                  label={audioFile ? 'SOURCE IN' : 'STANDBY'}
                />
              }
              footer="FORMATS: MP3 / WAV / FLAC / OGG (MAX 100MB) -> DEMUCS v4 + BASIC PITCH"
            >
              <div className="flex flex-col gap-4">
                <AudioDropzone
                  file={audioFile}
                  onFileSelect={handleFileSelect}
                  disabled={isBusy}
                />
                <div className="border-t border-hw-border pt-3.5">
                  <MetadataInputs
                    value={metadata}
                    onChange={handleMetadataChange}
                    disabled={isBusy}
                  />
                </div>
              </div>
            </ModulePanel>

            {/* M-03: Expandable Calibration Bay (6 RotaryKnobs + 6 ToggleSwitches) */}
            <CalibrationBay
              value={calibration}
              onChange={handleCalibrationChange}
              defaultExpanded
              disabled={isBusy}
            />

            {/* M-04: Real-time SSE Pipeline Telemetry */}
            <PipelineTelemetry
              taskId={activeTaskId}
              submitting={submitting}
              canGenerate={Boolean(audioFile)}
              onGenerate={() => {
                void handleGenerate();
              }}
              onRunDemo={handleRunDemo}
              onAbort={handleAbort}
              onCompleted={handleTelemetryCompleted}
              className="flex-1 flex flex-col"
            />

            {submitError ? (
              <div
                role="alert"
                className="border border-fret-red bg-[#1B0F13] px-3.5 py-2 font-mono text-[10px] uppercase tracking-silk text-fret-red"
              >
                UPLOAD / API ERROR // {submitError}
              </div>
            ) : null}
          </div>

          {/* ================================================================ */}
          {/* RIGHT COLUMN: 3D THREE.JS HIGHWAY VISUALIZER, AUDIT & EXPORT     */}
          {/* ================================================================ */}
          <div className="flex h-full flex-col gap-3 xl:col-span-7">
            {/* M-02: Master Preset Rotary Selector & Difficulty Tier */}
            <ModulePanel
              code="M-02"
              title="Mapping Profile & Difficulty"
              footer="ROTARY DETENT SELECTOR // AUTO-CALIBRATES M-03 PARAMETERS"
            >
              <div className="grid grid-cols-1 items-center gap-4 md:grid-cols-[1fr_auto]">
                <RotarySelector
                  label="Mapping Preset"
                  options={PRESET_OPTIONS}
                  value={preset}
                  onChange={handlePresetChange}
                  disabled={isBusy}
                />

                <div className="flex flex-col items-center gap-2 border-t border-hw-border pt-3 md:border-l md:border-t-0 md:pl-4 md:pt-0">
                  <span className="silk">Difficulty Tier</span>
                  <div className="grid grid-cols-2 gap-1.5" role="radiogroup" aria-label="Track Difficulty">
                    {DIFFICULTY_TIERS.map((d) => (
                      <PushButton
                        key={d.level}
                        size="sm"
                        label={d.label}
                        sublabel={d.tag}
                        led="green"
                        ledOn={metadata.difficulty === d.level}
                        latched={metadata.difficulty === d.level}
                        disabled={isBusy}
                        role="radio"
                        aria-checked={metadata.difficulty === d.level}
                        onClick={() => setMetadata((prev) => ({ ...prev, difficulty: d.level }))}
                      />
                    ))}
                  </div>
                </div>
              </div>
            </ModulePanel>

            {/* V-01: Three.js 3D Inclined Highway & Transport (Compact 220px / Focus 320px) */}
            <HighwayScene
              chart={chart}
              isPlaying={player.isPlaying}
              currentTime={player.currentTime}
              duration={player.duration}
              playbackRate={player.playbackRate}
              getCurrentTime={player.getCurrentTime}
              onTogglePlay={player.togglePlay}
              onStop={player.stop}
              onChangeSpeed={player.setPlaybackRate}
              isDemoChart={isDemoChart}
            />

            {/* A-01: Navigable Waveform Bar with [Events] Sections & Scrubbing */}
            <WaveformBar
              peaks={player.waveformPeaks}
              currentTime={player.currentTime}
              duration={player.duration}
              sections={chart.sections}
              starPower={chart.starPower}
              audioSourceLabel={player.audioSourceLabel}
              onSeek={player.seek}
            />

            {/* A-02 & A-04: Instantaneous BPM / Meter Display & Chart Audit Counters */}
            <div className="grid grid-cols-1 items-stretch gap-3 lg:grid-cols-12">
              <TempoDisplay
                chart={chart}
                currentTime={player.currentTime}
                isPlaying={player.isPlaying}
                className="h-full lg:col-span-5"
              />
              <StatsCard
                stats={chart.stats}
                className="h-full lg:col-span-7"
              />
            </div>

            {/* A-03: Notes-Per-Second (NPS) Timeline Density Graph */}
            <NpsGraph
              buckets={chart.npsBuckets}
              peakNps={chart.stats.peakNps}
              avgNps={chart.stats.avgNps}
              currentTime={player.currentTime}
              duration={player.duration}
              onSeek={player.seek}
            />

            {/* E-01: Master Export Panel (.sng, .chart, .zip) */}
            <ExportPanel
              completedTaskId={completedTaskId}
              rawChartText={chart.rawText}
              songName={metadata.songName || chart.songName}
              artist={metadata.artist || chart.artist}
            />
          </div>
        </div>
      )}
    </RackChassis>
  );
}
