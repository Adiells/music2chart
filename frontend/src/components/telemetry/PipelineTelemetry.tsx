import { useEffect, useRef, useState } from 'react';
import { getApiUrl } from '../../lib/api';
import { clamp, cn } from '../../lib/utils';
import { PushButton } from '../controls/PushButton';
import { LedIndicator } from '../rack/LedIndicator';
import { ModulePanel } from '../rack/ModulePanel';

export type TelemetryStatus = 'IDLE' | 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';

export interface SseTelemetryPayload {
  task_id: string;
  status: TelemetryStatus;
  progress: number;
  stage: string;
  error: string | null;
  result_files?: Record<string, string> | null;
}

export interface PipelineTelemetryProps {
  /** Active backend task UUID (or `demo-*` for local simulation). */
  taskId: string | null;
  /** Previously completed task UUID to avoid repeating completed state streams. */
  completedTaskId?: string | null;
  /** Whether an upload request is currently in-flight before taskId is assigned. */
  submitting?: boolean;
  /** Whether an audio file is mounted and ready to process. */
  canGenerate: boolean;
  /** Triggered when the operator clicks Master Generate. */
  onGenerate: () => void;
  /** Triggered when the operator clicks Load Demo Track. */
  onRunDemo?: () => void;
  /** Triggered when the operator clicks Abort / Reset. */
  onAbort: () => void;
  /** Fired when SSE reports COMPLETED. */
  onCompleted?: (taskId: string, payload: SseTelemetryPayload) => void;
  /** Fired when SSE reports FAILED. */
  onFailed?: (error: string) => void;
  className?: string;
}

interface StageSpec {
  id: string;
  code: string;
  label: string;
  engine: string;
  description: string;
  thresholdStart: number;
  thresholdDone: number;
  keywords: readonly string[];
}

const TELEMETRY_STAGES: readonly StageSpec[] = [
  {
    id: 'demucs',
    code: '01',
    label: 'Demucs v4',
    engine: 'HTDEMUCS',
    description: 'Separating guitar, bass & drums stems',
    thresholdStart: 0.05,
    thresholdDone: 0.25,
    keywords: ['stem', 'demucs', 'separat'],
  },
  {
    id: 'beatnet',
    code: '02',
    label: 'BeatNet',
    engine: '192 PPQ SYNC',
    description: 'Variable BPM & beat grid tracking',
    thresholdStart: 0.25,
    thresholdDone: 0.44,
    keywords: ['tempo', 'beat', 'bpm'],
  },
  {
    id: 'basic_pitch',
    code: '03',
    label: 'Basic Pitch',
    engine: 'SPOTIFY ML',
    description: 'Polyphonic pitch & harmonic filtering',
    thresholdStart: 0.44,
    thresholdDone: 0.64,
    keywords: ['transcrib', 'pitch', 'harmonic', 'overtone'],
  },
  {
    id: 'quantization',
    code: '04',
    label: 'Quantization',
    engine: 'GAME HEURISTICS',
    description: '5-fret projection, HOPO & sustains',
    thresholdStart: 0.64,
    thresholdDone: 0.89,
    keywords: ['snap', 'quantiz', 'fret', 'chord', 'hopo', 'sustain'],
  },
  {
    id: 'packaging',
    code: '05',
    label: 'Packaging',
    engine: 'CHART & SNG',
    description: 'notes.chart, song.ini & XOR container',
    thresholdStart: 0.89,
    thresholdDone: 0.99,
    keywords: ['serializ', 'packag', 'sng', 'chart'],
  },
];

const DEMO_SEQUENCE: readonly { progress: number; stage: string }[] = [
  { progress: 0.12, stage: 'Separating audio stems (Demucs v4 htdemucs)' },
  { progress: 0.32, stage: 'Analyzing tempo and beat grid (192 PPQ)' },
  { progress: 0.52, stage: 'Transcribing notes via Spotify Basic Pitch' },
  { progress: 0.62, stage: 'Filtering harmonic distortion overtones' },
  { progress: 0.76, stage: 'Snapping notes to 192 PPQ & mapping 5 frets' },
  { progress: 0.86, stage: 'Calculating HOPO tags, sustains, and Star Power' },
  { progress: 0.95, stage: 'Packaging .chart and .sng binary container' },
  { progress: 1.0, stage: 'Completed successfully' },
];

const DEFAULT_IDLE_LOGS: readonly string[] = [
  '[T+00.0S] DSP ENGINE STANDBY // 192 PPQ CLOCK LOCKED',
  '[T+00.0S] DEMUCS V4 + BASIC PITCH WEIGHTS READY',
  '[T+00.0S] AWAITING MASTER AUDIO INGESTION OR SYNTH BENCH...',
];

const SEGMENT_COUNT = 28;
const MAX_LOG_LINES = 6;

function formatLogEntry(elapsed: number, progress: number, message: string): string {
  const t = `T+${elapsed.toFixed(1).padStart(4, '0')}S`;
  const pct = `${String(Math.round(clamp(progress, 0, 1) * 100)).padStart(3, '0')}%`;
  return `[${t}] [${pct}] ${message.toUpperCase()}`;
}

function appendUniqueLog(
  existing: readonly string[],
  elapsed: number,
  progress: number,
  stageMessage: string,
): string[] {
  const formatted = formatLogEntry(elapsed, progress, stageMessage);
  const last = existing[existing.length - 1];
  const stageSignature = `] ${stageMessage.toUpperCase()}`;
  if (last && last.endsWith(stageSignature)) {
    return [...existing];
  }
  return [...existing, formatted].slice(-MAX_LOG_LINES);
}

function resolveStageState(
  spec: StageSpec,
  index: number,
  status: TelemetryStatus,
  progress: number,
  stageText: string,
): 'idle' | 'active' | 'done' | 'error' {
  if (status === 'IDLE') return 'idle';
  if (status === 'COMPLETED') return 'done';

  const lower = stageText.toLowerCase();
  const keywordMatch = spec.keywords.some((kw) => lower.includes(kw));

  if (status === 'FAILED') {
    if (keywordMatch || (progress >= spec.thresholdStart && progress < spec.thresholdDone)) {
      return 'error';
    }
    return progress >= spec.thresholdDone ? 'done' : 'idle';
  }

  // Handle tempo and stem sequence smoothly
  if (index === 0 && (lower.includes('tempo') || lower.includes('beat')) && progress < 0.25) {
    return 'idle';
  }
  if (index === 1 && (lower.includes('tempo') || lower.includes('beat')) && progress < 0.25) {
    return 'active';
  }
  if (index === 1 && progress >= 0.25) {
    return 'done';
  }
  if (index === 0 && progress >= 0.4) {
    return 'done';
  }

  if (keywordMatch) return 'active';
  if (progress >= spec.thresholdDone) return 'done';
  if (progress >= spec.thresholdStart) return 'active';
  return 'idle';
}

function calculateStageProgress(
  state: 'idle' | 'active' | 'done' | 'error',
  overallProgress: number,
  start: number,
  done: number,
): number {
  if (state === 'done') return 100;
  if (state === 'idle') return 0;
  if (state === 'error') return 50;
  if (done <= start) return 50;
  const rel = (overallProgress - start) / (done - start);
  return Math.round(clamp(rel, 0.1, 0.95) * 100);
}

interface TaskTelemetrySnapshot {
  taskId: string;
  status: TelemetryStatus;
  progress: number;
  stageText: string;
  errorMsg: string | null;
  elapsedSec: number;
  logEntries: string[];
}

/**
 * Real-time SSE telemetry receiver connected to `/api/v1/chart/stream/{task_id}`.
 * Renders 5 responsive stage cards with pulsating indicators and individual progress meters,
 * an analytical 28-segment progress meter, an embedded CRT telemetry log monitor,
 * and master action controls.
 */
export function PipelineTelemetry({
  taskId,
  completedTaskId,
  submitting = false,
  canGenerate,
  onGenerate,
  onRunDemo,
  onAbort,
  onCompleted,
  onFailed,
  className,
}: PipelineTelemetryProps) {
  const [snapshot, setSnapshot] = useState<TaskTelemetrySnapshot | null>(null);
  const completedFiredRef = useRef<string | null>(null);

  const callbacksRef = useRef({ onCompleted, onFailed });
  useEffect(() => {
    callbacksRef.current = { onCompleted, onFailed };
  });

  // Subscribe to SSE stream when taskId is active
  useEffect(() => {
    // If task is not set or already completed, do not reopen stream or replay simulation
    if (!taskId || completedTaskId === taskId) {
      return undefined;
    }

    const startTime = Date.now();
    const initialLogs = [
      formatLogEntry(0, 0.02, `TASK ${taskId.slice(0, 8)} MOUNTED ON SSE BUS`),
      formatLogEntry(0, 0.05, 'INITIALIZING PIPELINE'),
    ];

    const timer = window.setInterval(() => {
      const nextElapsed = (Date.now() - startTime) / 1000;
      setSnapshot((prev) => ({
        taskId,
        status: prev?.taskId === taskId ? prev.status : 'PROCESSING',
        progress: prev?.taskId === taskId ? prev.progress : 0.05,
        stageText: prev?.taskId === taskId ? prev.stageText : 'INITIALIZING PIPELINE',
        errorMsg: prev?.taskId === taskId ? prev.errorMsg : null,
        elapsedSec: nextElapsed,
        logEntries: prev?.taskId === taskId ? prev.logEntries : initialLogs,
      }));
    }, 100);

    // Local demo simulation mode
    if (taskId.startsWith('demo-')) {
      let stepIdx = 0;
      const stepTimer = window.setInterval(() => {
        const entry = DEMO_SEQUENCE[stepIdx];
        if (!entry) {
          window.clearInterval(stepTimer);
          return;
        }
        const isDone = entry.progress >= 1.0;
        const nowElapsed = (Date.now() - startTime) / 1000;
        setSnapshot((prev) => {
          const prevLogs = prev?.taskId === taskId ? prev.logEntries : initialLogs;
          return {
            taskId,
            status: isDone ? 'COMPLETED' : 'PROCESSING',
            progress: entry.progress,
            stageText: entry.stage.toUpperCase(),
            errorMsg: null,
            elapsedSec: nowElapsed,
            logEntries: appendUniqueLog(prevLogs, nowElapsed, entry.progress, entry.stage),
          };
        });
        if (isDone) {
          window.clearInterval(stepTimer);
          window.clearInterval(timer);
          if (completedFiredRef.current !== taskId) {
            completedFiredRef.current = taskId;
            callbacksRef.current.onCompleted?.(taskId, {
              task_id: taskId,
              status: 'COMPLETED',
              progress: 1.0,
              stage: entry.stage,
              error: null,
            });
          }
        } else {
          stepIdx += 1;
        }
      }, 360);

      return () => {
        window.clearInterval(stepTimer);
        window.clearInterval(timer);
      };
    }

    // Live Backend SSE Stream: /api/v1/chart/stream/{task_id}
    let finished = false;
    let pollTimer: number | null = null;
    const streamUrl = getApiUrl(`/api/v1/chart/stream/${encodeURIComponent(taskId)}`);
    const es = new EventSource(streamUrl);

    const handlePayload = (payload: SseTelemetryPayload): void => {
      if (finished) return;
      const nextProgress = clamp(payload.progress ?? 0, 0, 1);
      const nextStatus = payload.status ?? 'PROCESSING';
      const nextStage = (payload.stage || 'PROCESSING').toUpperCase();
      const err = nextStatus === 'FAILED' ? payload.error || 'Pipeline execution failed' : null;
      const nowElapsed = (Date.now() - startTime) / 1000;

      setSnapshot((prev) => {
        const prevLogs = prev?.taskId === taskId ? prev.logEntries : initialLogs;
        const logMsg = err ? `FAULT: ${err}` : nextStage;
        return {
          taskId,
          status: nextStatus,
          progress: nextProgress,
          stageText: nextStage,
          errorMsg: err,
          elapsedSec: nowElapsed,
          logEntries: appendUniqueLog(prevLogs, nowElapsed, nextProgress, logMsg),
        };
      });

      if (nextStatus === 'COMPLETED') {
        finished = true;
        window.clearInterval(timer);
        if (pollTimer !== null) window.clearInterval(pollTimer);
        es.close();
        if (completedFiredRef.current !== taskId) {
          completedFiredRef.current = taskId;
          callbacksRef.current.onCompleted?.(taskId, payload);
        }
      } else if (nextStatus === 'FAILED') {
        finished = true;
        window.clearInterval(timer);
        if (pollTimer !== null) window.clearInterval(pollTimer);
        es.close();
        callbacksRef.current.onFailed?.(err ?? 'Pipeline execution failed');
      }
    };

    es.onmessage = (event: MessageEvent<string>) => {
      try {
        const parsed = JSON.parse(event.data) as SseTelemetryPayload;
        handlePayload(parsed);
      } catch {
        // Ignore malformed keep-alive frames
      }
    };

    es.onerror = () => {
      es.close();
      if (finished || pollTimer !== null) return;
      // Fallback status polling if SSE stream drops
      pollTimer = window.setInterval(async () => {
        try {
          const res = await fetch(getApiUrl(`/api/v1/chart/status/${encodeURIComponent(taskId)}`));
          if (!res.ok) {
            if (res.status === 429) {
              handlePayload({
                task_id: taskId,
                status: 'FAILED',
                progress: 0,
                stage: 'TOO MANY REQUESTS',
                error: 'Too Many Requests (HTTP 429): Servidor sobrecarregado ou fila cheia.',
              });
            }
            return;
          }
          const data = (await res.json()) as SseTelemetryPayload;
          handlePayload(data);
        } catch {
          // Wait for next poll cycle
        }
      }, 800);
    };

    return () => {
      finished = true;
      es.close();
      window.clearInterval(timer);
      if (pollTimer !== null) window.clearInterval(pollTimer);
    };
  }, [taskId, completedTaskId]);

  const isAlreadyCompleted = Boolean(taskId && completedTaskId === taskId);

  const activeSnap = isAlreadyCompleted
    ? {
        taskId: taskId ?? '',
        status: 'COMPLETED' as TelemetryStatus,
        progress: 1.0,
        stageText: 'COMPLETED SUCCESSFULLY',
        errorMsg: null,
        elapsedSec: snapshot?.taskId === taskId ? snapshot.elapsedSec : 0,
        logEntries: snapshot?.taskId === taskId ? snapshot.logEntries : [
          formatLogEntry(0, 1.0, `TASK ${taskId?.slice(0, 8) ?? ''} COMPLETED`),
          formatLogEntry(0, 1.0, 'PIPELINE ARTIFACTS READY FOR DOWNLOAD'),
        ],
      }
    : taskId && snapshot?.taskId === taskId
      ? snapshot
      : taskId
        ? {
            taskId,
            status: 'PROCESSING' as TelemetryStatus,
            progress: 0.05,
            stageText: 'INITIALIZING PIPELINE',
            errorMsg: null,
            elapsedSec: 0,
            logEntries: [
              formatLogEntry(0, 0.02, `TASK ${taskId.slice(0, 8)} MOUNTED ON SSE BUS`),
              formatLogEntry(0, 0.05, 'INITIALIZING PIPELINE'),
            ],
          }
        : null;

  const status: TelemetryStatus = activeSnap ? activeSnap.status : 'IDLE';
  const progress = activeSnap ? activeSnap.progress : 0;
  const stageText = activeSnap ? activeSnap.stageText : 'IDLE / AWAITING AUDIO MASTER';
  const errorMsg = activeSnap ? activeSnap.errorMsg : null;
  const elapsedSec = activeSnap ? activeSnap.elapsedSec : 0;
  const logEntries: readonly string[] = activeSnap ? activeSnap.logEntries : DEFAULT_IDLE_LOGS;

  const isRunning = submitting || status === 'PENDING' || status === 'PROCESSING';
  const percent = Math.round(clamp(progress, 0, 1) * 100);
  const litSegments = Math.round(clamp(progress, 0, 1) * SEGMENT_COUNT);

  const statusBadgeColor =
    status === 'FAILED'
      ? 'red'
      : status === 'COMPLETED'
        ? 'green'
        : isRunning
          ? 'orange'
          : 'yellow';

  return (
    <ModulePanel
      code="M-04"
      title="Pipeline Telemetry & Stage Progress"
      className={className}
      bodyClassName="flex-1 flex flex-col justify-between gap-3.5"
      headerRight={
        <div className="flex items-center gap-3">
          <span className="silk-wide tabular-nums text-[9px]">
            T+{elapsedSec.toFixed(1)}S
          </span>
          <LedIndicator
            color={statusBadgeColor}
            on={status !== 'IDLE' || submitting}
            blink={isRunning ? 'fast' : status === 'FAILED' ? 'fast' : false}
            size="xs"
            label={submitting ? 'UPLOADING' : status}
          />
        </div>
      }
      footer={
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span>TASK: {taskId ? taskId.slice(0, 8).toUpperCase() : 'STANDBY'}</span>
          <span className="tabular-nums text-silk">{percent}% COMPLETE</span>
        </div>
      }
    >
      <div className="flex flex-1 flex-col justify-between gap-3">
        {/* Enhanced 5-Stage Visual Cards with Pulsing Feedback & Stage Bars */}
        <div
          aria-label="Pipeline Processing Stages"
          className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-5"
        >
          {TELEMETRY_STAGES.map((spec, idx) => {
            const st = resolveStageState(spec, idx, status, progress, stageText);
            const stagePct = calculateStageProgress(st, progress, spec.thresholdStart, spec.thresholdDone);
            const ledColor =
              st === 'error' ? 'red' : st === 'done' ? 'green' : st === 'active' ? 'orange' : 'yellow';

            return (
              <div
                key={spec.id}
                className={cn(
                  'relative flex flex-col justify-between border p-2.5 transition-all duration-200',
                  st === 'active' &&
                    'border-fret-orange bg-[#181D26] shadow-[0_0_15px_rgba(255,145,0,0.25)] ring-1 ring-fret-orange',
                  st === 'done' && 'border-hw-border bg-[#0E1714]',
                  st === 'error' && 'border-fret-red bg-[#1E0F14] ring-1 ring-fret-red',
                  st === 'idle' && 'border-hw-border bg-chassis opacity-75'
                )}
              >
                {/* Stage Header */}
                <div className="flex items-center justify-between gap-1">
                  <div className="flex items-center gap-1.5">
                    <span className="silk-wide text-[8px] font-semibold tabular-nums text-silk-dim">
                      {spec.code}
                    </span>
                    <span className="font-mono text-[9px] font-bold uppercase tracking-silk text-silk">
                      {spec.label}
                    </span>
                  </div>
                  <div className="flex items-center gap-1">
                    {st === 'active' ? (
                      <span className="inline-block h-1.5 w-1.5 animate-ping bg-fret-orange" aria-hidden="true" />
                    ) : null}
                    <LedIndicator
                      color={ledColor}
                      on={st !== 'idle'}
                      blink={st === 'active' ? 'fast' : false}
                      size="xs"
                    />
                  </div>
                </div>

                {/* Subtitle / Engine Description */}
                <div className="my-2 flex flex-col gap-0.5">
                  <span className="silk-wide text-[8px] leading-tight text-silk-neutral">
                    {spec.engine}
                  </span>
                  <span className="truncate font-mono text-[9px] text-silk-dim">
                    {spec.description}
                  </span>
                </div>

                {/* Individual Stage Progress Bar */}
                <div className="mt-1 flex flex-col gap-1 border-t border-hw-border/70 pt-2">
                  <div className="flex items-center justify-between text-[8px] font-mono">
                    <span
                      className={cn(
                        'uppercase font-semibold tracking-silk',
                        st === 'done'
                          ? 'text-fret-green'
                          : st === 'active'
                            ? 'text-fret-orange animate-pulse'
                            : st === 'error'
                              ? 'text-fret-red'
                              : 'text-silk-dim'
                      )}
                    >
                      {st === 'done'
                        ? 'COMPLETED'
                        : st === 'active'
                          ? 'PROCESSING...'
                          : st === 'error'
                            ? 'FAULT'
                            : 'STANDBY'}
                    </span>
                    <span className="tabular-nums text-silk-dim">{stagePct}%</span>
                  </div>

                  <div className="h-1.5 w-full bg-[#07080A] p-[1px] border border-hw-border/60">
                    <div
                      className={cn(
                        'h-full transition-all duration-150',
                        st === 'done'
                          ? 'bg-fret-green w-full'
                          : st === 'active'
                            ? 'bg-fret-orange animate-pulse'
                            : st === 'error'
                              ? 'bg-fret-red w-full'
                              : 'bg-transparent'
                      )}
                      style={{ width: st === 'active' ? `${stagePct}%` : undefined }}
                    />
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Analytical Segmented Progress Meter */}
        <div className="flex flex-col gap-1.5 border border-hw-border bg-chassis p-2.5 shadow-recess">
          <div className="flex items-center justify-between text-[10px]">
            <span className="truncate font-mono uppercase tracking-silk text-silk">
              {submitting ? 'TRANSMITTING AUDIO PAYLOAD...' : stageText}
            </span>
            <span className="ml-2 shrink-0 font-mono font-semibold tabular-nums tracking-silk text-silk">
              {String(percent).padStart(3, '0')}%
            </span>
          </div>

          <div
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={percent}
            aria-label="Pipeline progress"
            className="grid gap-[2px] border border-hw-border bg-[#07080A] p-1"
            style={{ gridTemplateColumns: `repeat(${SEGMENT_COUNT}, minmax(0, 1fr))` }}
          >
            {Array.from({ length: SEGMENT_COUNT }, (_, i) => {
              const active = i < litSegments;
              const isHigh = i >= Math.floor(SEGMENT_COUNT * 0.82);
              const isMid = i >= Math.floor(SEGMENT_COUNT * 0.5);
              const segColor =
                status === 'FAILED'
                  ? 'bg-fret-red'
                  : status === 'COMPLETED'
                    ? 'bg-fret-green'
                    : isHigh
                      ? 'bg-fret-green'
                      : isMid
                        ? 'bg-fret-yellow'
                        : 'bg-fret-orange';
              return (
                <span
                  key={i}
                  className={cn(
                    'h-2.5 transition-colors duration-75',
                    active ? segColor : 'bg-[#181B22]'
                  )}
                />
              );
            })}
          </div>
        </div>

        {/* Embedded CRT System Telemetry Log Terminal */}
        <div className="flex flex-1 flex-col justify-between gap-1.5 border border-hw-border bg-[#07080A] p-2.5 shadow-recess">
          <div className="flex items-center justify-between border-b border-hw-border/70 pb-1">
            <span className="silk-wide text-[8px] text-silk-neutral">
              SYSTEM TELEMETRY LOG // EVENTSTREAM
            </span>
            <span className="font-mono text-[8px] uppercase tracking-silk text-fret-green">
              {isRunning ? 'RX ACTIVE' : status === 'COMPLETED' ? 'EOF LOCKED' : 'MONITOR'}
            </span>
          </div>

          <div
            aria-live="polite"
            className="flex min-h-[72px] flex-1 flex-col justify-end gap-0.5 font-mono text-[9px] leading-4 tracking-silk text-silk-neutral"
          >
            {logEntries.map((line, idx) => {
              const isLatest = idx === logEntries.length - 1;
              return (
                <div
                  key={`${idx}-${line}`}
                  className={cn(
                    'truncate tabular-nums',
                    isLatest
                      ? status === 'FAILED'
                        ? 'text-fret-red'
                        : status === 'COMPLETED'
                          ? 'text-fret-green'
                          : 'text-silk'
                      : 'text-silk-dim'
                  )}
                >
                  {line}
                  {isLatest ? (
                    <span
                      className="ml-1.5 inline-block h-2.5 w-1.5 translate-y-[1px] animate-led-blink bg-fret-green"
                      aria-hidden="true"
                    />
                  ) : null}
                </div>
              );
            })}
          </div>
        </div>

        {errorMsg ? (
          <div
            role="alert"
            className="border border-fret-red bg-[#1B0F13] px-3 py-2 font-mono text-[10px] uppercase tracking-silk text-fret-red"
          >
            TELEMETRY FAULT // {errorMsg}
          </div>
        ) : null}

        {/* Master Actuation Grid */}
        <div className="grid w-full grid-cols-1 gap-2.5 sm:grid-cols-3">
          <PushButton
            size="md"
            variant="master"
            label={isRunning ? 'Processing' : 'Generate Chart'}
            sublabel="Master Execute"
            led={isRunning ? 'orange' : 'green'}
            ledOn={canGenerate || isRunning}
            ledBlink={isRunning ? 'fast' : false}
            latched={isRunning}
            disabled={!canGenerate || isRunning}
            onClick={onGenerate}
            className="w-full"
          />

          <PushButton
            size="md"
            variant="standard"
            label="Synth Demo"
            sublabel="Test Bench"
            led="blue"
            ledOn={Boolean(taskId?.startsWith('demo-'))}
            disabled={isRunning || !onRunDemo}
            onClick={onRunDemo}
            className="w-full"
          />

          <PushButton
            size="md"
            variant="alert"
            label="Abort / Reset"
            sublabel="Halt Pipeline"
            led="red"
            ledOn={isRunning || status === 'FAILED'}
            disabled={!isRunning && status === 'IDLE'}
            onClick={onAbort}
            className="w-full"
          />
        </div>
      </div>
    </ModulePanel>
  );
}
