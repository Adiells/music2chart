import { useState } from 'react';
import { cn } from '../../lib/utils';
import { PushButton } from '../controls/PushButton';
import { RotaryKnob } from '../controls/RotaryKnob';
import { ToggleSwitch } from '../controls/ToggleSwitch';
import { LedIndicator } from './LedIndicator';
import { ModulePanel } from './ModulePanel';

export interface CalibrationState {
  /** Acoustic chord fusion window in milliseconds (10..60 ms -> 0.010..0.060 s). */
  fusionMs: number;
  /** Minimum transcription amplitude / noise gate sensitivity (0.00..0.50). */
  noiseGateSensitivity: number;
  /** Solo/riff mapping expression percentage (0..100 % -> 0.0..1.0). */
  creativity: number;
  /** HOPO trigger tick distance cutoff (32..192 ticks). */
  hopoThreshold: number;
  /** Minimum duration in ticks to render a sustain tail (0..256 ticks). */
  minSustainTicks: number;
  /** Tempo multiplier scalar (0.50..2.00x). */
  bpmScale: number;
  /** Suppress purple open notes on lead guitar (default true). */
  disableOpenNotes: boolean;
  /** Collapse chords to single root notes in fast 1/16th runs (default true). */
  collapseFastRuns: boolean;
  /** Anchor repeating verse/chorus riffs to consistent fret motifs (default true). */
  consistentPatterns: boolean;
  /** Auto-halve excessive tempos (> 160 BPM) for comfortable scroll speed (default true). */
  autoCalibrateBpm: boolean;
  /** Merge consecutive re-triggered notes on same pitch into holds (default true). */
  mergeSustainedNotes: boolean;
  /** Allow 3-note triad chords on accented sustained hits (default false -> 2-note power chords). */
  allowTriads: boolean;
}

const DEFAULT_CALIBRATION_STATE: CalibrationState = {
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
};

export interface CalibrationBayProps {
  value: CalibrationState;
  onChange: (next: CalibrationState) => void;
  defaultExpanded?: boolean;
  disabled?: boolean;
  className?: string;
}

/**
 * Expandable hardware calibration drawer housing 6 precision RotaryKnobs
 * (Chord Fusion Window, Noise Gate / Sensitivity, Creativity, HOPO Distance Cutoff,
 * Sustain Tail Cutoff, BPM Scale) and 6 mechanical ToggleSwitches (Open Notes,
 * Fast Runs, Motif Lock, Auto-Calibrate BPM, Sustain Merge, Triad Chords).
 */
export function CalibrationBay({
  value,
  onChange,
  defaultExpanded = true,
  disabled = false,
  className,
}: CalibrationBayProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  const updateField = <K extends keyof CalibrationState>(key: K, fieldVal: CalibrationState[K]): void => {
    onChange({ ...value, [key]: fieldVal });
  };

  const resetDefaults = (): void => {
    onChange({ ...DEFAULT_CALIBRATION_STATE });
  };

  const isModified =
    value.fusionMs !== DEFAULT_CALIBRATION_STATE.fusionMs ||
    Math.abs(value.noiseGateSensitivity - DEFAULT_CALIBRATION_STATE.noiseGateSensitivity) > 0.001 ||
    value.creativity !== DEFAULT_CALIBRATION_STATE.creativity ||
    value.hopoThreshold !== DEFAULT_CALIBRATION_STATE.hopoThreshold ||
    value.minSustainTicks !== DEFAULT_CALIBRATION_STATE.minSustainTicks ||
    Math.abs(value.bpmScale - DEFAULT_CALIBRATION_STATE.bpmScale) > 0.001 ||
    value.disableOpenNotes !== DEFAULT_CALIBRATION_STATE.disableOpenNotes ||
    value.collapseFastRuns !== DEFAULT_CALIBRATION_STATE.collapseFastRuns ||
    value.consistentPatterns !== DEFAULT_CALIBRATION_STATE.consistentPatterns ||
    value.autoCalibrateBpm !== DEFAULT_CALIBRATION_STATE.autoCalibrateBpm ||
    value.mergeSustainedNotes !== DEFAULT_CALIBRATION_STATE.mergeSustainedNotes ||
    value.allowTriads !== DEFAULT_CALIBRATION_STATE.allowTriads;

  return (
    <ModulePanel
      code="M-03"
      title="Calibration Bay & Signal Routing"
      className={className}
      headerRight={
        <div className="flex items-center gap-2.5">
          <LedIndicator
            color={isModified ? 'yellow' : 'green'}
            on
            size="xs"
            label={isModified ? 'CUSTOM' : 'NOMINAL'}
          />
          <PushButton
            size="sm"
            label={expanded ? 'Collapse Bay' : 'Expand Bay'}
            led="orange"
            ledOn={expanded}
            latched={expanded}
            onClick={() => setExpanded((prev) => !prev)}
          />
        </div>
      }
      footer={
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span>DRAG KNOB / SHIFT = FINE / DBL-CLICK = RESET</span>
          <span className="tabular-nums text-silk-neutral">
            FUS {value.fusionMs}MS | GATE {value.noiseGateSensitivity.toFixed(2)} | CREAT {value.creativity}% | HOPO{' '}
            {value.hopoThreshold}T | SUS {value.minSustainTicks}T | BPM {value.bpmScale.toFixed(2)}X
          </span>
        </div>
      }
    >
      {expanded ? (
        <div className="flex flex-col gap-3.5">
          {/* Upper Bank: 6 Analog Rotary Potentiometers */}
          <div>
            <div className="mb-3 flex items-center justify-between border-b border-hw-border pb-1.5">
              <span className="silk-wide text-[9px]">6-CH ANALOG POTENTIOMETER BANK // DSP &amp; ERGONOMICS</span>
              <PushButton
                size="sm"
                label="Factory Reset"
                led="yellow"
                ledOn={isModified}
                disabled={disabled || !isModified}
                onClick={resetDefaults}
              />
            </div>

            <div className="grid grid-cols-2 justify-items-center gap-3 sm:grid-cols-3 lg:grid-cols-6">
              <RotaryKnob
                label="Chord Fusion Window"
                value={value.fusionMs}
                onChange={(v) => updateField('fusionMs', v)}
                min={10}
                max={60}
                step={1}
                defaultValue={DEFAULT_CALIBRATION_STATE.fusionMs}
                unit="MS"
                size={68}
                accent="green"
                disabled={disabled}
              />
              <RotaryKnob
                label="Noise Gate / Sensitivity"
                value={value.noiseGateSensitivity}
                onChange={(v) => updateField('noiseGateSensitivity', v)}
                min={0}
                max={0.5}
                step={0.01}
                defaultValue={DEFAULT_CALIBRATION_STATE.noiseGateSensitivity}
                format={(v) => v.toFixed(2)}
                size={68}
                accent="red"
                disabled={disabled}
              />
              <RotaryKnob
                label="Creativity"
                value={value.creativity}
                onChange={(v) => updateField('creativity', v)}
                min={0}
                max={100}
                step={1}
                defaultValue={DEFAULT_CALIBRATION_STATE.creativity}
                unit="%"
                size={68}
                accent="yellow"
                disabled={disabled}
              />
              <RotaryKnob
                label="HOPO Distance Cutoff"
                value={value.hopoThreshold}
                onChange={(v) => updateField('hopoThreshold', v)}
                min={32}
                max={192}
                step={4}
                defaultValue={DEFAULT_CALIBRATION_STATE.hopoThreshold}
                unit="TICKS"
                size={68}
                accent="blue"
                disabled={disabled}
              />
              <RotaryKnob
                label="Sustain Tail Cutoff"
                value={value.minSustainTicks}
                onChange={(v) => updateField('minSustainTicks', v)}
                min={0}
                max={256}
                step={6}
                defaultValue={DEFAULT_CALIBRATION_STATE.minSustainTicks}
                unit="TICKS"
                size={68}
                accent="open"
                disabled={disabled}
              />
              <RotaryKnob
                label="BPM Scale"
                value={value.bpmScale}
                onChange={(v) => updateField('bpmScale', v)}
                min={0.5}
                max={2.0}
                step={0.05}
                defaultValue={DEFAULT_CALIBRATION_STATE.bpmScale}
                format={(v) => v.toFixed(2)}
                unit="X"
                size={68}
                accent="orange"
                disabled={disabled}
              />
            </div>
          </div>

          {/* Lower Bank: 6 Mechanical Bat-Handle Toggle Switches */}
          <div className="border-t border-hw-border pt-3">
            <div className="mb-3 flex items-center justify-between">
              <span className="silk-wide text-[9px]">6-CH HEURISTIC ROUTING MATRIX // CLONE HERO RULESET</span>
              <span className="silk-wide text-[9px]">192 PPQ STRICT SNAP</span>
            </div>

            <div className="grid grid-cols-2 justify-items-center gap-3 sm:grid-cols-3 lg:grid-cols-6">
              <ToggleSwitch
                label="Open Notes"
                onLabel="ALLOW"
                offLabel="MUTE"
                checked={!value.disableOpenNotes}
                onChange={(allowOpen) => updateField('disableOpenNotes', !allowOpen)}
                led="open"
                disabled={disabled}
              />
              <ToggleSwitch
                label="Fast Runs"
                onLabel="COLLAPSE"
                offLabel="CHORDS"
                checked={value.collapseFastRuns}
                onChange={(v) => updateField('collapseFastRuns', v)}
                led="green"
                disabled={disabled}
              />
              <ToggleSwitch
                label="Motif Lock"
                onLabel="LOCKED"
                offLabel="FREE"
                checked={value.consistentPatterns}
                onChange={(v) => updateField('consistentPatterns', v)}
                led="blue"
                disabled={disabled}
              />
              <ToggleSwitch
                label="Auto-Calibrate BPM"
                onLabel="AUTO"
                offLabel="RAW"
                checked={value.autoCalibrateBpm}
                onChange={(v) => updateField('autoCalibrateBpm', v)}
                led="orange"
                disabled={disabled}
              />
              <ToggleSwitch
                label="Sustain Merge"
                onLabel="MERGE"
                offLabel="STACCATO"
                checked={value.mergeSustainedNotes}
                onChange={(v) => updateField('mergeSustainedNotes', v)}
                led="yellow"
                disabled={disabled}
              />
              <ToggleSwitch
                label="Triad Chords"
                onLabel="TRIADS"
                offLabel="POWER"
                checked={value.allowTriads}
                onChange={(v) => updateField('allowTriads', v)}
                led="red"
                disabled={disabled}
              />
            </div>
          </div>
        </div>
      ) : (
        <div
          className={cn(
            'grid grid-cols-2 gap-2 border border-hw-border bg-chassis p-3 font-mono text-[10px] uppercase tracking-silk text-silk shadow-recess sm:grid-cols-3 lg:grid-cols-6',
          )}
        >
          <div>
            <span className="text-silk-dim">FUSION: </span>
            <span className="tabular-nums">{value.fusionMs} MS</span>
          </div>
          <div>
            <span className="text-silk-dim">GATE: </span>
            <span className="tabular-nums">{value.noiseGateSensitivity.toFixed(2)}</span>
          </div>
          <div>
            <span className="text-silk-dim">CREAT: </span>
            <span className="tabular-nums">{value.creativity}%</span>
          </div>
          <div>
            <span className="text-silk-dim">HOPO: </span>
            <span className="tabular-nums">{value.hopoThreshold}T</span>
          </div>
          <div>
            <span className="text-silk-dim">SUSTAIN: </span>
            <span className="tabular-nums">{value.minSustainTicks}T</span>
          </div>
          <div>
            <span className="text-silk-dim">BPM: </span>
            <span className="tabular-nums">{value.bpmScale.toFixed(2)}X</span>
          </div>
          <div>
            <span className="text-silk-dim">OPEN: </span>
            <span>{value.disableOpenNotes ? 'MUTE' : 'ALLOW'}</span>
          </div>
          <div>
            <span className="text-silk-dim">RUNS: </span>
            <span>{value.collapseFastRuns ? 'COLLAPSE' : 'CHORDS'}</span>
          </div>
          <div>
            <span className="text-silk-dim">MOTIF: </span>
            <span>{value.consistentPatterns ? 'LOCKED' : 'FREE'}</span>
          </div>
          <div>
            <span className="text-silk-dim">AUTO BPM: </span>
            <span>{value.autoCalibrateBpm ? 'AUTO' : 'RAW'}</span>
          </div>
          <div>
            <span className="text-silk-dim">MERGE: </span>
            <span>{value.mergeSustainedNotes ? 'MERGE' : 'STAC'}</span>
          </div>
          <div>
            <span className="text-silk-dim">CHORDS: </span>
            <span>{value.allowTriads ? 'TRIADS' : 'POWER'}</span>
          </div>
        </div>
      )}
    </ModulePanel>
  );
}
