import { useState } from 'react';
import { cn } from '../../lib/utils';
import { PushButton } from '../controls/PushButton';
import { RotaryKnob } from '../controls/RotaryKnob';
import { ToggleSwitch } from '../controls/ToggleSwitch';
import { LedIndicator } from './LedIndicator';
import { ModulePanel } from './ModulePanel';
import type { Language } from '../../lib/language';

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
  language?: Language;
}

/**
 * Expandable hardware calibration drawer housing 6 precision RotaryKnobs
 * and 6 mechanical ToggleSwitches, plus an intuitive Parameter Guide.
 */
export function CalibrationBay({
  value,
  onChange,
  defaultExpanded = false,
  disabled = false,
  className,
  language = 'en',
}: CalibrationBayProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const portuguese = language === 'pt-BR';

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
      title={portuguese ? 'Painel de Calibração e Roteamento de Sinal' : 'Calibration Bay & Signal Routing'}
      className={className}
      headerRight={
        <div className="flex items-center gap-2.5">
          <LedIndicator
            color={isModified ? 'yellow' : 'green'}
            on
            size="xs"
            label={isModified ? (portuguese ? 'PERSONALIZADO' : 'CUSTOM') : 'NOMINAL'}
          />
          <PushButton
            size="sm"
            label={
              expanded
                ? (portuguese ? 'Recolher Painel' : 'Collapse Bay')
                : (portuguese ? 'Expandir Painel' : 'Expand Bay')
            }
            led="orange"
            ledOn={expanded}
            latched={expanded}
            onClick={() => setExpanded((prev) => !prev)}
          />
        </div>
      }
      footer={
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span>
            {portuguese
              ? 'ARRASTE O KNOB / SHIFT = AJUSTE FINO / DUPLO CLIQUE = RESTAURAR'
              : 'DRAG KNOB / SHIFT = FINE / DBL-CLICK = RESET'}
          </span>
          <span className="tabular-nums text-silk-neutral">
            {portuguese ? 'FUS' : 'FUS'} {value.fusionMs}MS | GATE {value.noiseGateSensitivity.toFixed(2)} |{' '}
            {portuguese ? 'CRIAT' : 'CREAT'} {value.creativity}% | HOPO {value.hopoThreshold}T |{' '}
            {portuguese ? 'SUST' : 'SUS'} {value.minSustainTicks}T | BPM {value.bpmScale.toFixed(2)}X
          </span>
        </div>
      }
    >
      {/* Parameter Explanations Drawer (Retractable Guide) */}
      <details className="border border-hw-border bg-chassis/90 p-3 shadow-recess mb-3">
        <summary className="cursor-pointer font-mono text-xs font-semibold text-silk hover:text-fret-green transition-colors flex items-center gap-2">
          <span className="inline-block h-1.5 w-1.5 bg-fret-green" aria-hidden="true" />
          <span>
            {portuguese
              ? 'Guia Simplificado de Parâmetros (Entenda o que cada controle faz)'
              : 'Quick Parameter Guide (What each control does)'}
          </span>
        </summary>

        <div className="mt-3 flex flex-col gap-4 font-mono text-[11px] leading-relaxed text-silk-neutral border-t border-hw-border/80 pt-3">
          {/* Knobs Section */}
          <div>
            <h4 className="font-bold uppercase tracking-silk text-silk mb-2 flex items-center gap-1.5">
              <LedIndicator color="yellow" on size="xs" />
              <span>{portuguese ? 'Controles Giratórios (Knobs)' : 'Rotary Controls (Knobs)'}</span>
            </h4>
            <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
              <div className="border border-hw-border/70 bg-panel p-2.5">
                <span className="font-bold text-silk">
                  {portuguese ? 'Janela de Fusão' : 'Chord Fusion Window'}
                </span>
                <p className="mt-1">
                  {portuguese ? (
                    <>
                      <strong>Mais alto:</strong> junta notas próximas no tempo em acordes.
                      <br />
                      <strong>Mais baixo:</strong> separa notas individuais com precisão.
                    </>
                  ) : (
                    <>
                      <strong>Higher:</strong> merges close notes into chords.
                      <br />
                      <strong>Lower:</strong> keeps individual notes strictly separated.
                    </>
                  )}
                </p>
              </div>

              <div className="border border-hw-border/70 bg-panel p-2.5">
                <span className="font-bold text-silk">
                  {portuguese ? 'Noise Gate' : 'Noise Gate'}
                </span>
                <p className="mt-1">
                  {portuguese ? (
                    <>
                      <strong>Mais alto:</strong> corta ruídos e palhetadas fantasmas, focando nas notas principais.
                      <br />
                      <strong>Mais baixo:</strong> capta dedilhados sutis e notas mais fracas.
                    </>
                  ) : (
                    <>
                      <strong>Higher:</strong> cuts ghost notes & noise, focusing on main hits.
                      <br />
                      <strong>Lower:</strong> captures quiet picking and subtle transients.
                    </>
                  )}
                </p>
              </div>

              <div className="border border-hw-border/70 bg-panel p-2.5">
                <span className="font-bold text-silk">
                  {portuguese ? 'Criatividade' : 'Creativity'}
                </span>
                <p className="mt-1">
                  {portuguese ? (
                    <>
                      <strong>Mais alto:</strong> solo expressivo e dinâmico distribuído pelas 5 cores.
                      <br />
                      <strong>Mais baixo:</strong> foco no ritmo base e padrões econômicos de fretes.
                    </>
                  ) : (
                    <>
                      <strong>Higher:</strong> expressive solos across all 5 fret colors.
                      <br />
                      <strong>Lower:</strong> keeps mapping tight to base rhythm and compact frets.
                    </>
                  )}
                </p>
              </div>

              <div className="border border-hw-border/70 bg-panel p-2.5">
                <span className="font-bold text-silk">
                  {portuguese ? 'Sensibilidade HOPO' : 'HOPO Sensitivity'}
                </span>
                <p className="mt-1">
                  {portuguese ? (
                    <>
                      <strong>Mais alto:</strong> mais notas viram HOPO (sem palhetar).
                      <br />
                      <strong>Mais baixo:</strong> exige palhetar a maioria das notas.
                    </>
                  ) : (
                    <>
                      <strong>Higher:</strong> more notes trigger as HOPOs (no strumming).
                      <br />
                      <strong>Lower:</strong> requires picking for almost every note.
                    </>
                  )}
                </p>
              </div>

              <div className="border border-hw-border/70 bg-panel p-2.5">
                <span className="font-bold text-silk">
                  {portuguese ? 'Corte de Notas Longas (Sustain)' : 'Sustain Tail Cutoff'}
                </span>
                <p className="mt-1">
                  {portuguese ? (
                    <>
                      <strong>Mais alto:</strong> só notas bem compridas ganham cauda na highway.
                      <br />
                      <strong>Mais baixo:</strong> notas curtas também ganham cauda de sustentação.
                    </>
                  ) : (
                    <>
                      <strong>Higher:</strong> only truly long notes receive sustain tails.
                      <br />
                      <strong>Lower:</strong> shorter notes receive sustain tails too.
                    </>
                  )}
                </p>
              </div>

              <div className="border border-hw-border/70 bg-panel p-2.5">
                <span className="font-bold text-silk">
                  {portuguese ? 'Multiplicador BPM' : 'BPM Multiplier'}
                </span>
                <p className="mt-1">
                  {portuguese ? (
                    <>
                      <strong>Mais alto:</strong> aumenta velocidade de rolagem para ritmos rápidos.
                      <br />
                      <strong>Mais baixo:</strong> reduz pela metade para músicas lentas.
                    </>
                  ) : (
                    <>
                      <strong>Higher:</strong> speeds up highway scrolling for fast rhythms.
                      <br />
                      <strong>Lower:</strong> halves tempo for slower, relaxed rhythms.
                    </>
                  )}
                </p>
              </div>
            </div>
          </div>

          {/* Switches Section */}
          <div className="border-t border-hw-border/60 pt-3">
            <h4 className="font-bold uppercase tracking-silk text-silk mb-2 flex items-center gap-1.5">
              <LedIndicator color="blue" on size="xs" />
              <span>{portuguese ? 'Chaves Seletoras (Switches)' : 'Toggle Switches'}</span>
            </h4>
            <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
              <div className="border border-hw-border/70 bg-panel p-2.5">
                <span className="font-bold text-silk">
                  {portuguese ? 'Notas Abertas (Open Notes)' : 'Open Notes'}
                </span>
                <p className="mt-1">
                  {portuguese ? (
                    <>
                      <strong>Ligado (Permitir):</strong> gera notas roxas de corda aberta (sem frete).
                      <br />
                      <strong>Desligado (Silenciar):</strong> mapeia para os 5 fretes tradicionais.
                    </>
                  ) : (
                    <>
                      <strong>On (Allow):</strong> enables purple open strum bars.
                      <br />
                      <strong>Off (Mute):</strong> maps all notes to standard 5 frets.
                    </>
                  )}
                </p>
              </div>

              <div className="border border-hw-border/70 bg-panel p-2.5">
                <span className="font-bold text-silk">
                  {portuguese ? 'Escalas Rápidas (Fast Runs)' : 'Fast Runs'}
                </span>
                <p className="mt-1">
                  {portuguese ? (
                    <>
                      <strong>Ligado (Colapsar):</strong> converte acordes em notas simples em corridas 1/16.
                      <br />
                      <strong>Desligado (Acordes):</strong> mantém acordes mesmo em alta velocidade.
                    </>
                  ) : (
                    <>
                      <strong>On (Collapse):</strong> collapses chords into single notes in 1/16 runs.
                      <br />
                      <strong>Off (Chords):</strong> maintains chords even during shred runs.
                    </>
                  )}
                </p>
              </div>

              <div className="border border-hw-border/70 bg-panel p-2.5">
                <span className="font-bold text-silk">
                  {portuguese ? 'Trava de Padrão (Motif Lock)' : 'Motif Lock'}
                </span>
                <p className="mt-1">
                  {portuguese ? (
                    <>
                      <strong>Ligado (Travado):</strong> riffs repetidos mantêm o mesmo dedilhado visual.
                      <br />
                      <strong>Desligado (Livre):</strong> varia livremente conforme a transcrição bruta.
                    </>
                  ) : (
                    <>
                      <strong>On (Locked):</strong> repeating riffs preserve consistent fret patterns.
                      <br />
                      <strong>Off (Free):</strong> varies freely according to raw audio transcription.
                    </>
                  )}
                </p>
              </div>

              <div className="border border-hw-border/70 bg-panel p-2.5">
                <span className="font-bold text-silk">
                  {portuguese ? 'Auto BPM (Auto-Calibrate BPM)' : 'Auto-Calibrate BPM'}
                </span>
                <p className="mt-1">
                  {portuguese ? (
                    <>
                      <strong>Ligado (Auto):</strong> divide andamentos &gt;160 BPM para rolagem confortável.
                      <br />
                      <strong>Desligado (Bruto):</strong> mantém a velocidade bruta detectada.
                    </>
                  ) : (
                    <>
                      <strong>On (Auto):</strong> halves detected tempos &gt;160 BPM for comfortable scroll.
                      <br />
                      <strong>Off (Raw):</strong> keeps raw detected tempo speed.
                    </>
                  )}
                </p>
              </div>

              <div className="border border-hw-border/70 bg-panel p-2.5">
                <span className="font-bold text-silk">
                  {portuguese ? 'Mesclar Sustentadas (Sustain Merge)' : 'Sustain Merge'}
                </span>
                <p className="mt-1">
                  {portuguese ? (
                    <>
                      <strong>Ligado (Mesclar):</strong> unifica repetições da mesma nota em uma só sustentada.
                      <br />
                      <strong>Desligado (Staccato):</strong> mantém cada ataque como nota separada.
                    </>
                  ) : (
                    <>
                      <strong>On (Merge):</strong> fuses re-triggered identical notes into single holds.
                      <br />
                      <strong>Off (Staccato):</strong> treats each re-trigger as an individual gem.
                    </>
                  )}
                </p>
              </div>

              <div className="border border-hw-border/70 bg-panel p-2.5">
                <span className="font-bold text-silk">
                  {portuguese ? 'Tríades (Triad Chords)' : 'Triad Chords'}
                </span>
                <p className="mt-1">
                  {portuguese ? (
                    <>
                      <strong>Ligado (Tríades):</strong> permite acordes de 3 notas em batidas fortes.
                      <br />
                      <strong>Desligado (Power):</strong> limita a no máximo 2 notas por acorde.
                    </>
                  ) : (
                    <>
                      <strong>On (Triads):</strong> allows 3-note chords on accented beats.
                      <br />
                      <strong>Off (Power):</strong> limits chords to 2-note power chords.
                    </>
                  )}
                </p>
              </div>
            </div>
          </div>
        </div>
      </details>

      {expanded ? (
        <div className="flex flex-col gap-3.5">
          {/* Upper Bank: 6 Analog Rotary Potentiometers */}
          <div>
            <div className="mb-3 flex items-center justify-between border-b border-hw-border pb-1.5">
              <span className="silk-wide text-[9px]">
                {portuguese
                  ? 'BANCO DE 6 POTENCIÔMETROS ANALÓGICOS // DSP E ERGONOMIA'
                  : '6-CH ANALOG POTENTIOMETER BANK // DSP & ERGONOMICS'}
              </span>
              <PushButton
                size="sm"
                label={portuguese ? 'Restaurar Padrão' : 'Factory Reset'}
                led="yellow"
                ledOn={isModified}
                disabled={disabled || !isModified}
                onClick={resetDefaults}
              />
            </div>

            <div className="grid grid-cols-2 justify-items-center gap-3 sm:grid-cols-3 lg:grid-cols-6">
              <RotaryKnob
                label={portuguese ? 'Fusão de Acordes' : 'Chord Fusion Window'}
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
                label={portuguese ? 'Noise Gate' : 'Noise Gate / Sensitivity'}
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
                label={portuguese ? 'Criatividade' : 'Creativity'}
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
                label={portuguese ? 'Sensibilidade HOPO' : 'HOPO Distance Cutoff'}
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
                label={portuguese ? 'Corte de Sustentação' : 'Sustain Tail Cutoff'}
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
                label={portuguese ? 'Multiplicador BPM' : 'BPM Scale'}
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
              <span className="silk-wide text-[9px]">
                {portuguese
                  ? 'MATRIZ DE ROTEAMENTO HEURÍSTICO 6-CH // REGRAS CLONE HERO'
                  : '6-CH HEURISTIC ROUTING MATRIX // CLONE HERO RULESET'}
              </span>
              <span className="silk-wide text-[9px]">
                {portuguese ? '192 PPQ AJUSTE EXATO' : '192 PPQ STRICT SNAP'}
              </span>
            </div>

            <div className="grid grid-cols-2 justify-items-center gap-3 sm:grid-cols-3 lg:grid-cols-6">
              <ToggleSwitch
                label={portuguese ? 'Notas Abertas' : 'Open Notes'}
                onLabel={portuguese ? 'PERMITIR' : 'ALLOW'}
                offLabel={portuguese ? 'SILENCIAR' : 'MUTE'}
                checked={!value.disableOpenNotes}
                onChange={(allowOpen) => updateField('disableOpenNotes', !allowOpen)}
                led="open"
                disabled={disabled}
              />
              <ToggleSwitch
                label={portuguese ? 'Escalas Rápidas' : 'Fast Runs'}
                onLabel={portuguese ? 'COLAPSAR' : 'COLLAPSE'}
                offLabel={portuguese ? 'ACORDES' : 'CHORDS'}
                checked={value.collapseFastRuns}
                onChange={(v) => updateField('collapseFastRuns', v)}
                led="green"
                disabled={disabled}
              />
              <ToggleSwitch
                label={portuguese ? 'Trava de Padrão' : 'Motif Lock'}
                onLabel={portuguese ? 'TRAVADO' : 'LOCKED'}
                offLabel={portuguese ? 'LIVRE' : 'FREE'}
                checked={value.consistentPatterns}
                onChange={(v) => updateField('consistentPatterns', v)}
                led="blue"
                disabled={disabled}
              />
              <ToggleSwitch
                label={portuguese ? 'Auto BPM' : 'Auto-Calibrate BPM'}
                onLabel="AUTO"
                offLabel={portuguese ? 'BRUTO' : 'RAW'}
                checked={value.autoCalibrateBpm}
                onChange={(v) => updateField('autoCalibrateBpm', v)}
                led="orange"
                disabled={disabled}
              />
              <ToggleSwitch
                label={portuguese ? 'Mesclar Sustentadas' : 'Sustain Merge'}
                onLabel={portuguese ? 'MESCLAR' : 'MERGE'}
                offLabel="STACCATO"
                checked={value.mergeSustainedNotes}
                onChange={(v) => updateField('mergeSustainedNotes', v)}
                led="yellow"
                disabled={disabled}
              />
              <ToggleSwitch
                label={portuguese ? 'Tríades' : 'Triad Chords'}
                onLabel={portuguese ? 'TRÍADES' : 'TRIADS'}
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
            <span className="text-silk-dim">{portuguese ? 'FUSÃO: ' : 'FUSION: '}</span>
            <span className="tabular-nums">{value.fusionMs} MS</span>
          </div>
          <div>
            <span className="text-silk-dim">GATE: </span>
            <span className="tabular-nums">{value.noiseGateSensitivity.toFixed(2)}</span>
          </div>
          <div>
            <span className="text-silk-dim">{portuguese ? 'CRIAT: ' : 'CREAT: '}</span>
            <span className="tabular-nums">{value.creativity}%</span>
          </div>
          <div>
            <span className="text-silk-dim">HOPO: </span>
            <span className="tabular-nums">{value.hopoThreshold}T</span>
          </div>
          <div>
            <span className="text-silk-dim">{portuguese ? 'SUST: ' : 'SUSTAIN: '}</span>
            <span className="tabular-nums">{value.minSustainTicks}T</span>
          </div>
          <div>
            <span className="text-silk-dim">BPM: </span>
            <span className="tabular-nums">{value.bpmScale.toFixed(2)}X</span>
          </div>
          <div>
            <span className="text-silk-dim">{portuguese ? 'ABERTAS: ' : 'OPEN: '}</span>
            <span>
              {value.disableOpenNotes
                ? (portuguese ? 'SILENCIAR' : 'MUTE')
                : (portuguese ? 'PERMITIR' : 'ALLOW')}
            </span>
          </div>
          <div>
            <span className="text-silk-dim">{portuguese ? 'ESCALAS: ' : 'RUNS: '}</span>
            <span>
              {value.collapseFastRuns
                ? (portuguese ? 'COLAPSAR' : 'COLLAPSE')
                : (portuguese ? 'ACORDES' : 'CHORDS')}
            </span>
          </div>
          <div>
            <span className="text-silk-dim">{portuguese ? 'PADRÃO: ' : 'MOTIF: '}</span>
            <span>
              {value.consistentPatterns
                ? (portuguese ? 'TRAVADO' : 'LOCKED')
                : (portuguese ? 'LIVRE' : 'FREE')}
            </span>
          </div>
          <div>
            <span className="text-silk-dim">AUTO BPM: </span>
            <span>{value.autoCalibrateBpm ? 'AUTO' : (portuguese ? 'BRUTO' : 'RAW')}</span>
          </div>
          <div>
            <span className="text-silk-dim">{portuguese ? 'MESCLAR: ' : 'MERGE: '}</span>
            <span>{value.mergeSustainedNotes ? (portuguese ? 'MESCLAR' : 'MERGE') : 'STAC'}</span>
          </div>
          <div>
            <span className="text-silk-dim">{portuguese ? 'ACORDES: ' : 'CHORDS: '}</span>
            <span>{value.allowTriads ? (portuguese ? 'TRÍADES' : 'TRIADS') : 'POWER'}</span>
          </div>
        </div>
      )}
    </ModulePanel>
  );
}
