import { useEffect } from 'react';
import { cn } from '../../lib/utils';
import { PushButton } from '../controls/PushButton';
import { LedIndicator } from '../rack/LedIndicator';
import { Screw } from '../rack/Screw';

export interface SupportModalProps {
  isOpen: boolean;
  onClose: () => void;
  className?: string;
}

/**
 * Industrial Support & Infrastructure Modal:
 * Explains Cloud GPU compute costs (Demucs v4, Basic Pitch) and provides
 * direct links to sponsor on GitHub or star the repository.
 */
export function SupportModal({ isOpen, onClose, className }: SupportModalProps) {
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent): void => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="support-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className={cn(
          'relative flex w-full max-w-2xl flex-col border border-hw-border bg-panel shadow-lift',
          className,
        )}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Chassis Top Mounting Screws & Header Bar */}
        <div className="flex items-center justify-between border-b border-hw-border bg-chassis px-4 py-2.5">
          <div className="flex items-center gap-3">
            <Screw size={11} angle={42} />
            <div className="flex items-center gap-2">
              <span className="font-grotesk text-xs font-bold uppercase tracking-silk-wide text-silk">
                MUSIC2CHART
              </span>
              <span className="text-hw-screw">/</span>
              <span id="support-modal-title" className="silk-wide text-xs text-fret-yellow">
                INFRASTRUCTURE // COMPUTE &amp; GPU UPGRADE FUND
              </span>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <LedIndicator color="orange" on blink="slow" size="xs" label="CLOUD RUN (4 vCPU / 8GB)" />
            <Screw size={11} angle={83} />
          </div>
        </div>

        {/* Chassis Modal Body */}
        <div className="flex flex-col gap-4 p-5 sm:p-6">
          {/* Status Alert Banner */}
          <div className="border border-fret-yellow/40 bg-[#161208] p-3.5 shadow-recess">
            <div className="flex items-center gap-2.5">
              <LedIndicator color="orange" on size="xs" />
              <span className="font-mono text-[10px] font-bold uppercase tracking-silk text-fret-yellow">
                100% Free &amp; Open Source // Current Tier: Cloud Run CPU (4 vCPU / 8 GiB)
              </span>
            </div>
            <p className="mt-2 font-mono text-[11px] leading-relaxed tracking-silk text-silk-neutral">
              Music2Chart is completely free software released under the permissive <strong className="text-silk">MIT License</strong>.
              Currently, our live demo runs on serverless Google Cloud Run CPU instances (4 vCPU, 8 GiB RAM). Because deep neural models
              (Meta Demucs v4 and Spotify Basic Pitch) run purely on CPU cores without GPU acceleration, chart processing takes 1–2 minutes per track.
            </p>
          </div>

          {/* Technical Cost Explanation */}
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="flex flex-col justify-between border border-hw-border bg-chassis p-3.5 shadow-recess">
              <div>
                <div className="flex items-center justify-between border-b border-hw-border pb-1.5">
                  <span className="silk-wide text-[9px]">TARGET: GPU ACCELERATION</span>
                  <LedIndicator color="green" on size="xs" />
                </div>
                <h4 className="mt-2 font-mono text-xs font-bold uppercase tracking-silk text-silk">
                  Migrating to Dedicated GPU
                </h4>
                <p className="mt-1.5 font-mono text-[10px] leading-relaxed tracking-silk text-silk-neutral">
                  Running stem isolation and polyphonic transcription on CPU is computationally heavy. Community sponsorships
                  are specifically dedicated to evolving our backend to dedicated Cloud GPU instances (NVIDIA Tensor Core),
                  slashing processing times from 90s to under 15s.
                </p>
              </div>
              <div className="mt-3 border-t border-hw-border pt-2 font-mono text-[9px] uppercase tracking-silk text-silk-dim">
                MILESTONE: DEDICATED T4 / A10G GPU UPGRADE
              </div>
            </div>

            <div className="flex flex-col justify-between border border-hw-border bg-chassis p-3.5 shadow-recess">
              <div>
                <div className="flex items-center justify-between border-b border-hw-border pb-1.5">
                  <span className="silk-wide text-[9px]">COMMUNITY MISSION</span>
                  <LedIndicator color="blue" on size="xs" />
                </div>
                <h4 className="mt-2 font-mono text-xs font-bold uppercase tracking-silk text-silk">
                  Zero Paywalls &amp; Zero Ads
                </h4>
                <p className="mt-1.5 font-mono text-[10px] leading-relaxed tracking-silk text-silk-neutral">
                  We believe Clone Hero and YARG charting should remain open to all players worldwide.
                  Community sponsorships directly offset monthly Cloud Run compute costs, domain hosting, and accelerate our GPU migration milestone.
                </p>
              </div>
              <div className="mt-3 border-t border-hw-border pt-2 font-mono text-[9px] uppercase tracking-silk text-silk-dim">
                CURRENT SPEC: 4 vCPU • 8 GiB RAM • MAX 2 INSTANCES
              </div>
            </div>
          </div>

          {/* Telemetry Specs Row */}
          <div className="flex flex-wrap items-center justify-between gap-3 border border-hw-border bg-chassis px-3.5 py-2 font-mono text-[9px] uppercase tracking-silk text-silk-dim">
            <div>
              CURRENT: <span className="text-silk">CLOUD RUN CPU (4 vCPU / 8 GiB RAM)</span>
            </div>
            <div>
              TARGET: <span className="text-fret-yellow">DEDICATED CLOUD GPU INSTANCES</span>
            </div>
            <div>
              LICENSE: <span className="text-fret-green">MIT (FULL OPEN SOURCE)</span>
            </div>
          </div>

          {/* Action Button Deck */}
          <div className="mt-2 flex flex-col gap-2.5 sm:flex-row sm:items-center sm:justify-end">
            <a
              href="https://github.com/Adiells/music2chart"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center justify-center gap-2 border border-hw-border bg-chassis px-4 py-2.5 font-mono text-[11px] font-semibold uppercase tracking-silk text-silk hover:border-silk hover:bg-module transition-colors"
            >
              <svg className="h-4 w-4 fill-current" viewBox="0 0 24 24" aria-hidden="true">
                <path fillRule="evenodd" clipRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
              </svg>
              <span>Star on GitHub</span>
            </a>

            <a
              href="https://github.com/sponsors/Adiells"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center justify-center gap-2 border border-fret-yellow bg-[#26200F] px-5 py-2.5 font-mono text-[11px] font-bold uppercase tracking-silk text-fret-yellow hover:bg-[#382F15] transition-colors shadow-recess"
            >
              <span className="text-sm">⚡</span>
              <span>Sponsor on GitHub</span>
              <span className="text-fret-yellow">↗</span>
            </a>

            <PushButton
              size="md"
              variant="standard"
              label="Dismiss"
              sublabel="Close Modal"
              onClick={onClose}
            />
          </div>
        </div>

        {/* Chassis Bottom Mounting Screws & Footer */}
        <div className="flex items-center justify-between border-t border-hw-border bg-chassis px-4 py-2">
          <Screw size={11} angle={15} />
          <span className="font-mono text-[9px] uppercase tracking-silk text-silk-dim">
            PRESS [ESC] OR CLICK OUTSIDE TO RETURN
          </span>
          <Screw size={11} angle={67} />
        </div>
      </div>
    </div>
  );
}
