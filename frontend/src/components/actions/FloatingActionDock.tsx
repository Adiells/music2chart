import { cn } from '../../lib/utils';
import { playMechanicalClick } from '../../lib/mechanicalClick';
import { LedIndicator } from '../rack/LedIndicator';
import type { WorkflowStepId } from '../navigation/WorkflowStepper';

export interface FloatingActionDockProps {
  currentStep: WorkflowStepId;
  onStepChange: (step: WorkflowStepId) => void;
  canGenerate: boolean;
  isProcessing: boolean;
  submitting?: boolean;
  onGenerate: () => void;
  onAbort: () => void;
  onRunDemo?: () => void;
  className?: string;
}

/**
 * Fixed high-contrast floating action dock.
 * Ensures the primary Generate Chart, Abort, and Step Progression actions
 * remain permanently visible and instantly accessible across all workflow views.
 */
export function FloatingActionDock({
  currentStep,
  onStepChange,
  canGenerate,
  isProcessing,
  submitting = false,
  onGenerate,
  onAbort,
  onRunDemo,
  className,
}: FloatingActionDockProps) {
  const isBusy = isProcessing || submitting;

  const handlePrevStep = (): void => {
    if (currentStep > 1) {
      playMechanicalClick(3200, 0.16);
      onStepChange((currentStep - 1) as WorkflowStepId);
    }
  };

  const handleNextStep = (): void => {
    if (currentStep < 4) {
      playMechanicalClick(3200, 0.16);
      onStepChange((currentStep + 1) as WorkflowStepId);
    }
  };

  const handleGenerateClick = (): void => {
    if (!canGenerate || isBusy) return;
    playMechanicalClick(5000, 0.3);
    onGenerate();
  };

  const handleAbortClick = (): void => {
    playMechanicalClick(1400, 0.3);
    onAbort();
  };

  return (
    <aside
      aria-label="Master Action Dock"
      className={cn(
        'fixed bottom-3 right-3 z-40 flex max-w-[calc(100vw-1.5rem)] flex-wrap items-center gap-2 border border-hw-border bg-[#0B0C0F]/95 p-2 shadow-2xl backdrop-blur-md sm:bottom-5 sm:right-5 sm:gap-3 sm:p-2.5',
        className
      )}
    >
      {/* Step Progression Navigation Buttons */}
      <div className="flex items-center gap-1 border-r border-hw-border pr-2">
        <button
          type="button"
          onClick={handlePrevStep}
          disabled={currentStep <= 1}
          aria-label="Previous step"
          className={cn(
            'flex h-9 items-center justify-center border px-2.5 font-mono text-[10px] font-semibold uppercase tracking-silk transition-colors',
            currentStep > 1
              ? 'border-hw-border bg-module text-silk hover:border-silk hover:bg-panel'
              : 'cursor-not-allowed border-hw-border/40 bg-chassis text-silk-dim/50'
          )}
        >
          &lt; PREV
        </button>

        <span className="silk-wide px-1 text-[9px] tabular-nums">
          0{currentStep}/04
        </span>

        <button
          type="button"
          onClick={handleNextStep}
          disabled={currentStep >= 4}
          aria-label="Next step"
          className={cn(
            'flex h-9 items-center justify-center border px-2.5 font-mono text-[10px] font-semibold uppercase tracking-silk transition-colors',
            currentStep < 4
              ? 'border-hw-border bg-module text-silk hover:border-silk hover:bg-panel'
              : 'cursor-not-allowed border-hw-border/40 bg-chassis text-silk-dim/50'
          )}
        >
          NEXT &gt;
        </button>
      </div>

      {/* Demo Bench Quick Action (shown when no audio loaded and idle) */}
      {!canGenerate && !isBusy && onRunDemo ? (
        <button
          type="button"
          onClick={onRunDemo}
          className="flex h-9 items-center gap-1.5 border border-hw-border bg-module px-3 font-mono text-[10px] font-semibold uppercase tracking-silk text-silk hover:border-fret-blue hover:text-silk transition-colors"
        >
          <LedIndicator color="blue" on size="xs" />
          <span>TRY DEMO</span>
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
          <span>ABORT</span>
        </button>
      ) : null}

      {/* PRIMARY MASTER ACTION: HIGH-CONTRAST GENERATE BUTTON */}
      <button
        type="button"
        disabled={!canGenerate || isBusy}
        onClick={handleGenerateClick}
        aria-label="Generate Clone Hero Chart"
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
            ? 'UPLOADING...'
            : isBusy
              ? 'PROCESSING...'
              : canGenerate
                ? 'GENERATE CHART'
                : 'AWAITING AUDIO'}
        </span>
      </button>
    </aside>
  );
}
