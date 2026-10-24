import { cn } from '../../lib/utils';
import { playMechanicalClick } from '../../lib/mechanicalClick';
import { LedIndicator } from '../rack/LedIndicator';
import type { Language } from '../../lib/language';

export interface FloatingActionDockProps {
  language?: Language;
  canGenerate: boolean;
  isProcessing: boolean;
  submitting?: boolean;
  hasChart?: boolean;
  currentStep?: number;
  onGenerate: () => void;
  onAbort: () => void;
  onRunDemo?: () => void;
  onAdjustParameters?: () => void;
  onGoToDownload?: () => void;
  className?: string;
}

/**
 * Fixed high-contrast floating action dock.
 * Ensures the primary Generate Chart, Abort, and Step Progression actions
 * remain permanently visible and instantly accessible across all workflow views.
 */
export function FloatingActionDock({
  language = 'en',
  canGenerate,
  isProcessing,
  submitting = false,
  hasChart = false,
  currentStep = 1,
  onGenerate,
  onAbort,
  onRunDemo,
  onAdjustParameters,
  onGoToDownload,
  className,
}: FloatingActionDockProps) {
  const isBusy = isProcessing || submitting;
  const portuguese = language === 'pt-BR';
  const showReviewActions = hasChart && !isBusy && (currentStep === 3 || currentStep === 4);

  const handleGenerateClick = (): void => {
    if (!canGenerate || isBusy) return;
    playMechanicalClick(5000, 0.3);
    onGenerate();
  };

  const handleAbortClick = (): void => {
    playMechanicalClick(1400, 0.3);
    onAbort();
  };

  const handleAdjustClick = (): void => {
    playMechanicalClick(3200, 0.25);
    onAdjustParameters?.();
  };

  const handleGoToDownloadClick = (): void => {
    playMechanicalClick(5000, 0.3);
    onGoToDownload?.();
  };

  return (
    <aside
      aria-label="Master Action Dock"
      className={cn(
        'fixed bottom-3 left-1/2 -translate-x-1/2 z-40 flex max-w-[calc(100vw-1.5rem)] flex-wrap items-center justify-center gap-2 border border-hw-border bg-[#0B0C0F]/95 p-2 shadow-2xl backdrop-blur-md sm:bottom-4 sm:gap-3 sm:p-2.5',
        className
      )}
    >
      {/* Demo Bench Quick Action (shown when no audio loaded and idle) */}
      {!canGenerate && !isBusy && !hasChart && onRunDemo ? (
        <button
          type="button"
          onClick={onRunDemo}
          className="flex h-9 items-center gap-1.5 border border-hw-border bg-module px-3 font-mono text-[10px] font-semibold uppercase tracking-silk text-silk hover:border-fret-blue hover:text-silk transition-colors"
        >
          <LedIndicator color="blue" on size="xs" />
          <span>{portuguese ? 'Ver demonstração' : 'Try demo'}</span>
        </button>
      ) : null}

      {/* Abort / Reset Action (visible during processing or error) */}
      {isBusy ? (
        <button
          type="button"
          onClick={handleAbortClick}
          className="flex h-9 items-center gap-1.5 border border-fret-red/60 bg-[#210D12] px-3 font-mono text-[10px] font-semibold uppercase tracking-silk text-fret-red hover:bg-[#2F121A] transition-colors"
        >
          <LedIndicator color="red" on blink="fast" size="xs" />
          <span>{portuguese ? 'Cancelar' : 'Cancel'}</span>
        </button>
      ) : null}

      {/* Contextual actions when chart exists and user is previewing (Step 3) or downloading (Step 4) */}
      {showReviewActions ? (
        <div className="flex items-center gap-2 sm:gap-3">
          <button
            type="button"
            onClick={handleAdjustClick}
            aria-label={portuguese ? 'Ajustar Parâmetros' : 'Adjust Parameters'}
            className="flex h-10 items-center justify-center gap-2 border border-hw-border bg-module px-3.5 font-mono text-xs font-bold uppercase tracking-silk text-silk hover:border-fret-orange hover:text-fret-orange hover:bg-panel transition-all cursor-pointer shadow-md"
          >
            <span className="inline-block h-2 w-2 border border-hw-border bg-chassis" aria-hidden="true" />
            <span>{portuguese ? 'Ajustar Parâmetros' : 'Adjust Parameters'}</span>
          </button>

          <button
            type="button"
            onClick={handleGoToDownloadClick}
            aria-label={portuguese ? 'Baixar Chart' : 'Download Chart'}
            className={cn(
              'relative flex h-10 min-w-[140px] items-center justify-center gap-2 border border-fret-green bg-fret-green px-4 font-mono text-xs font-bold uppercase tracking-silk-wide text-black shadow-[0_0_20px_rgba(0,230,118,0.4)] ring-1 ring-fret-green hover:bg-[#00c864] transition-all cursor-pointer',
              currentStep === 4 && 'ring-2 ring-white'
            )}
          >
            <span className="inline-block h-2 w-2 border border-black bg-black animate-ping" aria-hidden="true" />
            <span>{portuguese ? 'Baixar Chart' : 'Download Chart'}</span>
          </button>
        </div>
      ) : (
        /* PRIMARY MASTER ACTION: HIGH-CONTRAST GENERATE / REGENERATE BUTTON */
        <button
          type="button"
          disabled={!canGenerate || isBusy}
          onClick={handleGenerateClick}
          aria-label={
            hasChart && currentStep === 1
              ? (portuguese ? 'Regerar Chart com Ajustes' : 'Regenerate Chart with Adjustments')
              : 'Generate Clone Hero Chart'
          }
          className={cn(
            'relative flex h-10 min-w-[170px] items-center justify-center gap-2 border px-4 font-mono text-xs font-bold uppercase tracking-silk-wide transition-all duration-150',
            isBusy
              ? 'border-fret-orange bg-fret-orange text-black shadow-[0_0_18px_rgba(255,145,0,0.4)] animate-pulse'
              : canGenerate
                ? 'border-fret-green bg-fret-green text-black hover:bg-[#00c864] shadow-[0_0_20px_rgba(0,230,118,0.4)] ring-1 ring-fret-green cursor-pointer'
                : 'cursor-not-allowed border-hw-border bg-module text-silk-dim opacity-70'
          )}
        >
          <span
            className={cn(
              'inline-block h-2 w-2 border',
              isBusy
                ? 'border-black bg-black'
                : canGenerate
                  ? 'border-black bg-black animate-ping'
                  : 'border-hw-screw bg-chassis'
            )}
            aria-hidden="true"
          />
          <span>
            {submitting
              ? (portuguese ? 'ENVIANDO…' : 'UPLOADING…')
              : isBusy
                ? (portuguese ? 'CRIANDO…' : 'CREATING…')
                : hasChart && currentStep === 1
                  ? (portuguese ? 'REGERAR CHART' : 'REGENERATE CHART')
                  : canGenerate
                    ? (portuguese ? 'CRIAR CHART' : 'CREATE CHART')
                    : (portuguese ? 'ESCOLHA UM ÁUDIO' : 'CHOOSE AUDIO')}
          </span>
        </button>
      )}
    </aside>
  );
}
