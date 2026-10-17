import { cn } from '../../lib/utils';
import { playMechanicalClick } from '../../lib/mechanicalClick';
import { LedIndicator } from '../rack/LedIndicator';

export type WorkflowStepId = 1 | 2 | 3 | 4;

export interface StepItem {
  id: WorkflowStepId;
  code: string;
  label: string;
  sublabel: string;
  isReady?: boolean;
}

export interface WorkflowStepperProps {
  currentStep: WorkflowStepId;
  onStepChange: (step: WorkflowStepId) => void;
  hasAudio: boolean;
  hasChart: boolean;
  isProcessing: boolean;
  className?: string;
}

const WORKFLOW_STEPS: readonly StepItem[] = [
  {
    id: 1,
    code: '01',
    label: 'Ingest & Metadata',
    sublabel: 'Audio Input Deck',
  },
  {
    id: 2,
    code: '02',
    label: 'Mapping Profile',
    sublabel: 'Preset & Heuristics',
  },
  {
    id: 3,
    code: '03',
    label: '3D Preview & Player',
    sublabel: 'Highway Visualizer',
  },
  {
    id: 4,
    code: '04',
    label: 'Export & Audit',
    sublabel: 'Packages & Telemetry',
  },
];

/**
 * 4-Step Linear Workflow Stepper.
 * Replaces stacked multi-rack clutter with a focused, intuitive studio progression.
 */
export function WorkflowStepper({
  currentStep,
  onStepChange,
  hasAudio,
  hasChart,
  isProcessing,
  className,
}: WorkflowStepperProps) {
  const handleStepClick = (stepId: WorkflowStepId): void => {
    if (stepId === currentStep) return;
    playMechanicalClick(3800, 0.16);
    onStepChange(stepId);
  };

  return (
    <nav
      aria-label="Studio Workflow Progression"
      className={cn(
        'grid grid-cols-2 gap-1.5 border border-hw-border bg-panel p-1.5 sm:grid-cols-4',
        className
      )}
    >
      {WORKFLOW_STEPS.map((step) => {
        const isActive = currentStep === step.id;
        const isStepCompleted =
          (step.id === 1 && hasAudio) ||
          (step.id === 2 && hasAudio) ||
          ((step.id === 3 || step.id === 4) && hasChart);

        const ledColor = isProcessing && isActive ? 'orange' : isStepCompleted ? 'green' : isActive ? 'orange' : 'yellow';

        return (
          <button
            key={step.id}
            type="button"
            role="tab"
            aria-selected={isActive}
            onClick={() => handleStepClick(step.id)}
            className={cn(
              'group relative flex min-h-[46px] items-center justify-between border px-3 py-2 text-left transition-all duration-150',
              isActive
                ? 'border-fret-orange bg-module text-silk shadow-[0_0_10px_rgba(255,145,0,0.18)]'
                : 'border-hw-border/70 bg-chassis text-silk-dim hover:border-hw-screw hover:text-silk',
            )}
          >
            <div className="flex flex-col gap-0.5 min-w-0 pr-2">
              <div className="flex items-center gap-1.5">
                <span
                  className={cn(
                    'font-mono text-[9px] font-bold tabular-nums',
                    isActive ? 'text-fret-orange' : 'text-silk-dim'
                  )}
                >
                  {step.code}
                </span>
                <span className="truncate font-mono text-[10px] font-semibold uppercase tracking-silk">
                  {step.label}
                </span>
              </div>
              <span className="truncate silk-wide text-[8px]">{step.sublabel}</span>
            </div>

            <div className="flex shrink-0 items-center gap-1.5">
              <LedIndicator
                color={ledColor}
                on={isActive || isStepCompleted}
                blink={isProcessing && isActive ? 'fast' : false}
                size="xs"
              />
            </div>
          </button>
        );
      })}
    </nav>
  );
}
