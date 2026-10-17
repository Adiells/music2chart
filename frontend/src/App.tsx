import { useCallback, useState } from 'react';
import {
  AboutPage,
  AudioDropzone,
  CalibrationBay,
  ExportPanel,
  FloatingActionDock,
  HighwayScene,
  LedIndicator,
  MetadataInputs,
  ModulePanel,
  NpsGraph,
  PipelineTelemetry,
  PresetSelector,
  PushButton,
  RackChassis,
  StatsCard,
  SupportModal,
  TempoDisplay,
  WaveformBar,
  WorkflowStepper,
} from './components';
import type {
  CalibrationState,
  DerivedTrackMeta,
  PresetItem,
  TrackMetadataState,
  WorkflowStepId,
} from './components';
import { useAudioPlayer } from './hooks/useAudioPlayer';
import { useChartParser } from './hooks/useChartParser';
import { getApiUrl } from './lib/api';
import { cn } from './lib/utils';

type PresetId = 'standard' | 'strict_rhythm' | 'dynamic_solo' | 'melodic' | 'chord_heavy';
type ActiveView = 'workstation' | 'about';

const MAX_UPLOAD_SIZE = 50 * 1024 * 1024;

const PRESET_OPTIONS: readonly PresetItem<PresetId>[] = [
  {
    value: 'standard',
    label: 'Standard',
    description: 'Balanced 5-fret mapping with 35ms chord fusion and standard HOPO logic.',
    tag: 'BALANCED',
  },
  {
    value: 'strict_rhythm',
    label: 'Strict Rhythm',
    description: 'Tight 40ms quantization, lower creativity tolerance, and solid chord foundation.',
    tag: 'RHYTHM',
  },
  {
    value: 'dynamic_solo',
    label: 'Dynamic Solo',
    description: 'Expressive lead solo mapping, expanded HOPO threshold, and rapid runs.',
    tag: 'EXPRESSIVE',
  },
  {
    value: 'melodic',
    label: 'Melodic',
    description: 'Lead motif recognition with adaptive sliding tessitura and balanced sustains.',
    tag: 'MOTIF',
  },
  {
    value: 'chord_heavy',
    label: 'Chord Heavy',
    description: 'Full polyphonic triad support, 45ms fusion, and authentic power chord voicings.',
    tag: 'POLYPHONIC',
  },
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
  /* Navigation View & 4-Step Linear Workflow State */
  const [activeView, setActiveView] = useState<ActiveView>('workstation');
  const [activeStep, setActiveStep] = useState<WorkflowStepId>(1);
  const [isSupportOpen, setIsSupportOpen] = useState(false);

  /* Audio Ingestion, Metadata, Preset, Calibration, and Task State */
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

  /* Chart Parser & Synchronized Audio Player */
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

    if (audioFile.size > MAX_UPLOAD_SIZE) {
      setSubmitError(
        'Payload Too Large: File exceeds 50 MB limit. Please select a smaller audio file.'
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

      const backendPreset =
        preset === 'strict_rhythm' || preset === 'dynamic_solo' ? preset : 'standard';
      form.append('preset', backendPreset);

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
              errorDetail || 'File exceeds server 50 MB limit. Please select a smaller file.'
            }`
          );
        }

        if (response.status === 429) {
          throw new Error(
            `Too Many Requests (HTTP 429): ${
              errorDetail || 'Server overloaded or processing queue full. Please wait a moment and try again.'
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
    setActiveStep(3); // Auto-navigate to 3D Player!
  }, [player]);

  const handleAbort = useCallback((): void => {
    setActiveTaskId(null);
    setSubmitting(false);
    setSubmitError(null);
  }, []);

  const handleTelemetryCompleted = useCallback((taskId: string): void => {
    setCompletedTaskId(taskId);
    setActiveStep(3); // Auto-advance to 3D Highway upon completion!
  }, []);

  const isBusy = submitting || (activeTaskId !== null && activeTaskId !== completedTaskId);
  const hasAudio = Boolean(audioFile);
  const hasChart = chart.notes.length > 0;

  return (
    <RackChassis
      brand="MUSIC2CHART"
      model="STUDIO WORKSTATION"
      onOpenSupport={() => setIsSupportOpen(true)}
      headerRight={
        <div className="flex flex-wrap items-center gap-2.5">
          {/* View Selector: Workstation vs About */}
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
              label="Documentation"
              sublabel="Technical Spec"
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
            label={player.isPlaying ? 'PLAYING' : 'SYNC 192 PPQ'}
          />
          <LedIndicator
            color={isBusy ? 'orange' : 'green'}
            on
            blink={isBusy ? 'fast' : false}
            size="xs"
            label={isBusy ? 'DSP ACTIVE' : 'SYSTEM READY'}
          />
        </div>
      }
    >
      {activeView === 'about' ? (
        <AboutPage onReturnToWorkstation={() => setActiveView('workstation')} />
      ) : (
        <div className="flex flex-col gap-3.5 pb-28 sm:pb-32">
          {/* 4-Step Guided Linear Workflow Navigation */}
          <WorkflowStepper
            currentStep={activeStep}
            onStepChange={setActiveStep}
            hasAudio={hasAudio}
            hasChart={hasChart}
            isProcessing={isBusy}
          />

          {/* Active Error Notice */}
          {submitError ? (
            <div
              role="alert"
              className="border border-fret-red bg-[#1B0F13] px-4 py-2.5 font-mono text-xs uppercase tracking-silk text-fret-red"
            >
              PIPELINE ERROR // {submitError}
            </div>
          ) : null}

          {/* ========================================================================= */}
          {/* STEP 1: INGESTION & MASTER AUDIO METADATA                                  */}
          {/* ========================================================================= */}
          {activeStep === 1 && (
            <div className="flex flex-col gap-3.5">
              <ModulePanel
                code="M-01"
                title="Master Ingestion & Track Metadata"
                headerRight={
                  <LedIndicator
                    color={hasAudio ? 'green' : 'yellow'}
                    on
                    size="xs"
                    label={hasAudio ? 'AUDIO MOUNTED' : 'AWAITING MASTER'}
                  />
                }
                footer="ACCEPTED CONTAINERS: .MP3 / .WAV / .FLAC / .OGG (MAX 50 MB)"
              >
                <div className="flex flex-col gap-4">
                  <AudioDropzone
                    file={audioFile}
                    onFileSelect={handleFileSelect}
                    disabled={isBusy}
                  />

                  <div className="border-t border-hw-border pt-4">
                    <MetadataInputs
                      value={metadata}
                      onChange={handleMetadataChange}
                      disabled={isBusy}
                    />
                  </div>

                  <div className="flex flex-wrap items-center justify-between gap-3 border-t border-hw-border pt-3">
                    <span className="silk-wide text-[9px]">
                      {hasAudio
                        ? 'SOURCE READY -> PROCEED TO STEP 2 OR EXECUTE GENERATE DIRECTLY'
                        : 'SELECT AN AUDIO FILE TO UNLOCK CHART GENERATION'}
                    </span>
                    <button
                      type="button"
                      onClick={() => setActiveStep(2)}
                      className="border border-hw-border bg-module px-3 py-1.5 font-mono text-[10px] font-semibold uppercase tracking-silk text-silk hover:border-silk hover:bg-panel transition-colors"
                    >
                      PROCEED TO MAPPING &gt;
                    </button>
                  </div>
                </div>
              </ModulePanel>
            </div>
          )}

          {/* ========================================================================= */}
          {/* STEP 2: MAPPING PROFILE & ENGINE CALIBRATION                              */}
          {/* ========================================================================= */}
          {activeStep === 2 && (
            <div className="flex flex-col gap-3.5">
              <ModulePanel
                code="M-02"
                title="Mapping Profile & Difficulty Tuning"
                headerRight={
                  <span className="silk-wide text-[9px]">
                    PRESET: {preset.toUpperCase()}
                  </span>
                }
                footer="CALIBRATED FOR PHYSICAL GUITAR CONTROLLERS // ERGONOMIC CHORD & HOPO RULES"
              >
                <div className="flex flex-col gap-5">
                  {/* Linear Tactile Preset Selection */}
                  <PresetSelector
                    options={PRESET_OPTIONS}
                    value={preset}
                    onChange={handlePresetChange}
                    disabled={isBusy}
                  />

                  {/* Difficulty Tier Selection */}
                  <div className="border-t border-hw-border pt-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="silk">Target Difficulty Tier</span>
                      <span className="silk-wide text-[9px]">
                        SELECTED: {DIFFICULTY_TIERS.find((d) => d.level === metadata.difficulty)?.label.toUpperCase()}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-2 sm:grid-cols-4" role="radiogroup" aria-label="Difficulty Tiers">
                      {DIFFICULTY_TIERS.map((d) => (
                        <PushButton
                          key={d.level}
                          size="md"
                          label={d.label}
                          sublabel={d.tag}
                          led="green"
                          ledOn={metadata.difficulty === d.level}
                          latched={metadata.difficulty === d.level}
                          disabled={isBusy}
                          role="radio"
                          aria-checked={metadata.difficulty === d.level}
                          onClick={() => setMetadata((prev) => ({ ...prev, difficulty: d.level }))}
                          className="w-full"
                        />
                      ))}
                    </div>
                  </div>
                </div>
              </ModulePanel>

              {/* M-03: Advanced Calibration Bay */}
              <CalibrationBay
                value={calibration}
                onChange={handleCalibrationChange}
                defaultExpanded={false}
                disabled={isBusy}
              />

              {/* Live Pipeline Telemetry if task is running or available */}
              {(isBusy || activeTaskId) && (
                <PipelineTelemetry
                  taskId={activeTaskId}
                  submitting={submitting}
                  canGenerate={hasAudio}
                  onGenerate={() => {
                    void handleGenerate();
                  }}
                  onRunDemo={handleRunDemo}
                  onAbort={handleAbort}
                  onCompleted={handleTelemetryCompleted}
                />
              )}
            </div>
          )}

          {/* ========================================================================= */}
          {/* STEP 3: 3D THREE.JS HIGHWAY VISUALIZER & SYNCHRONIZED PLAYER               */}
          {/* ========================================================================= */}
          {activeStep === 3 && (
            <div className="flex flex-col gap-3.5">
              {/* Notice when chart has not been generated yet */}
              {!completedTaskId && (
                <div
                  role="alert"
                  className={cn(
                    'border p-3.5 shadow-lift transition-colors',
                    isBusy
                      ? 'border-fret-orange bg-[#181612]'
                      : hasAudio
                        ? 'border-fret-orange/90 bg-[#17130E]'
                        : 'border-hw-border bg-panel'
                  )}
                >
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <div className="flex items-start gap-3">
                      <LedIndicator
                        color={isBusy ? 'orange' : hasAudio ? 'orange' : 'yellow'}
                        on
                        blink={isBusy ? 'fast' : false}
                        size="sm"
                      />
                      <div className="flex flex-col gap-1">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs font-bold uppercase tracking-silk text-fret-orange">
                            {isBusy
                              ? 'PIPELINE PROCESSING // GENERATING 3D HIGHWAY'
                              : 'NOTICE // CLICK "GENERATE CHART" TO RENDER HIGHWAY'}
                          </span>
                          <span className="border border-hw-border bg-chassis px-1.5 py-0.5 font-mono text-[8px] uppercase tracking-silk text-silk-dim">
                            {isBusy ? 'PROCESSING' : 'ACTION REQUIRED'}
                          </span>
                        </div>
                        <p className="font-mono text-[11px] leading-relaxed text-silk-neutral">
                          {isBusy ? (
                            'AI pipeline is transcribing and mapping your audio in real time. Your 3D note highway will load automatically once conversion completes.'
                          ) : hasAudio ? (
                            'Audio master is mounted, but notes have not been generated yet. Click "GENERATE CHART" to run AI transcription and render your interactive 3D highway.'
                          ) : (
                            'To view your custom 3D note highway, go to Step 01, load an audio file, and click "GENERATE CHART" (or click "Load Demo" to preview the reference chart).'
                          )}
                        </p>
                      </div>
                    </div>

                    <div className="flex shrink-0 flex-wrap items-center gap-2 pt-1 sm:pt-0">
                      {!isBusy && hasAudio && (
                        <button
                          type="button"
                          onClick={() => {
                            void handleGenerate();
                          }}
                          className="flex items-center gap-2 border border-fret-green bg-fret-green px-3.5 py-2 font-mono text-[11px] font-bold uppercase tracking-silk text-black shadow-[0_0_15px_rgba(0,230,118,0.3)] hover:bg-[#00c864] transition-colors"
                        >
                          <span className="inline-block h-2 w-2 border border-black bg-black animate-ping" />
                          <span>GENERATE CHART NOW</span>
                        </button>
                      )}
                      {!hasAudio && !isBusy && (
                        <>
                          <button
                            type="button"
                            onClick={() => setActiveStep(1)}
                            className="border border-hw-border bg-module px-3 py-1.5 font-mono text-[10px] font-semibold uppercase tracking-silk text-silk hover:border-silk hover:bg-panel transition-colors"
                          >
                            &lt; GO TO STEP 01
                          </button>
                          <button
                            type="button"
                            onClick={handleRunDemo}
                            className="border border-fret-blue/60 bg-module px-3 py-1.5 font-mono text-[10px] font-semibold uppercase tracking-silk text-silk hover:border-fret-blue hover:text-silk transition-colors"
                          >
                            LOAD DEMO
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              )}

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

              <WaveformBar
                peaks={player.waveformPeaks}
                currentTime={player.currentTime}
                duration={player.duration}
                sections={chart.sections}
                starPower={chart.starPower}
                audioSourceLabel={player.audioSourceLabel}
                onSeek={player.seek}
              />

              <div className="flex flex-wrap items-center justify-between gap-3 border border-hw-border bg-panel p-3">
                <div className="flex items-center gap-3">
                  <LedIndicator
                    color={hasChart ? 'green' : 'yellow'}
                    on
                    size="xs"
                    label={hasChart ? 'CHART LOADED' : 'WAITING FOR DATA'}
                  />
                  <span className="silk-wide text-[9px]">
                    {completedTaskId
                      ? `${chart.notes.length} NOTES // ${chart.starPower.length} STAR POWER PHRASES`
                      : 'SHOWING REFERENCE DEMO // RUN "GENERATE CHART" FOR YOUR CUSTOM AUDIO'}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => setActiveStep(4)}
                  className="border border-hw-border bg-module px-3 py-1.5 font-mono text-[10px] font-semibold uppercase tracking-silk text-silk hover:border-silk hover:bg-panel transition-colors"
                >
                  PROCEED TO EXPORT &amp; AUDIT &gt;
                </button>
              </div>
            </div>
          )}

          {/* ========================================================================= */}
          {/* STEP 4: MASTER EXPORT, AUDIT METRICS & CRT TELEMETRY LOG                   */}
          {/* ========================================================================= */}
          {activeStep === 4 && (
            <div className="flex flex-col gap-3.5">
              <ExportPanel
                completedTaskId={completedTaskId}
                rawChartText={chart.rawText}
                songName={metadata.songName || chart.songName}
                artist={metadata.artist || chart.artist}
              />

              <div className="grid grid-cols-1 items-stretch gap-3.5 lg:grid-cols-12">
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

              <NpsGraph
                buckets={chart.npsBuckets}
                peakNps={chart.stats.peakNps}
                avgNps={chart.stats.avgNps}
                currentTime={player.currentTime}
                duration={player.duration}
                onSeek={player.seek}
              />

              <PipelineTelemetry
                taskId={activeTaskId}
                submitting={submitting}
                canGenerate={hasAudio}
                onGenerate={() => {
                  void handleGenerate();
                }}
                onRunDemo={handleRunDemo}
                onAbort={handleAbort}
                onCompleted={handleTelemetryCompleted}
              />
            </div>
          )}

          {/* Permanent High-Contrast Master Floating Action Dock */}
          <FloatingActionDock
            currentStep={activeStep}
            onStepChange={setActiveStep}
            canGenerate={hasAudio}
            isProcessing={isBusy}
            submitting={submitting}
            onGenerate={() => {
              void handleGenerate();
            }}
            onAbort={handleAbort}
            onRunDemo={handleRunDemo}
          />
        </div>
      )}

      {/* Cloud GPU Infrastructure & GitHub Support Modal */}
      <SupportModal isOpen={isSupportOpen} onClose={() => setIsSupportOpen(false)} />
    </RackChassis>
  );
}
