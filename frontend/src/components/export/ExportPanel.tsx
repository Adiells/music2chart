import { useEffect, useRef, useState } from 'react';
import { getApiUrl } from '../../lib/api';
import { cn } from '../../lib/utils';
import { PushButton } from '../controls/PushButton';
import { LedIndicator } from '../rack/LedIndicator';

export type ExportFormat = 'sng' | 'chart' | 'zip';

const IDLE_STATUS_NOTE = 'READY FOR PACKAGE DISPATCH';
/** Delay before the status readout reverts to idle after a download action. */
const STATUS_RESET_MS = 3500;

export interface ExportPanelProps {
  /** Completed backend task UUID. */
  completedTaskId: string | null;
  /** Raw .chart text currently loaded in the visualizer (fallback for local .chart export). */
  rawChartText: string;
  songName: string;
  artist: string;
  className?: string;
}

function triggerBrowserDownload(url: string, filename?: string): void {
  const anchor = document.createElement('a');
  anchor.href = url;
  if (filename) anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
}

/**
 * Hardware export bay featuring tactile PushButtons to download the generated
 * Clone Hero artifacts in `.sng` (SongBinary v1), `.chart` (notes.chart), or `.zip` archive formats.
 */
export function ExportPanel({
  completedTaskId,
  rawChartText,
  songName,
  artist,
  className,
}: ExportPanelProps) {
  const [activeFormat, setActiveFormat] = useState<ExportFormat | null>(null);
  const [statusNote, setStatusNote] = useState<string>(IDLE_STATUS_NOTE);
  const statusResetRef = useRef<number | null>(null);

  useEffect(
    () => () => {
      if (statusResetRef.current !== null) window.clearTimeout(statusResetRef.current);
    },
    [],
  );

  const hasBackendPackage = Boolean(completedTaskId && !completedTaskId.startsWith('demo-'));

  /** Re-arms the idle-status timer so the readout reverts 3.5 s after the latest action. */
  const scheduleStatusReset = (): void => {
    if (statusResetRef.current !== null) window.clearTimeout(statusResetRef.current);
    statusResetRef.current = window.setTimeout(() => {
      statusResetRef.current = null;
      setStatusNote(IDLE_STATUS_NOTE);
    }, STATUS_RESET_MS);
  };

  const handleDownload = (format: ExportFormat): void => {
    setActiveFormat(format);
    scheduleStatusReset();

    if (hasBackendPackage && completedTaskId) {
      const url = getApiUrl(`/api/v1/chart/download/${encodeURIComponent(completedTaskId)}?format=${format}`);
      setStatusNote(`DISPATCHING .${format.toUpperCase()} STREAM // TASK ${completedTaskId.slice(0, 8).toUpperCase()}`);
      triggerBrowserDownload(url);
      window.setTimeout(() => setActiveFormat(null), 900);
      return;
    }

    if (format === 'chart') {
      const blob = new Blob([rawChartText], { type: 'text/plain;charset=utf-8' });
      const blobUrl = URL.createObjectURL(blob);
      const safeStem = `${artist || 'Artist'} - ${songName || 'Track'}`.replace(/[\\/*?:"<>|]/g, '_');
      triggerBrowserDownload(blobUrl, `${safeStem} (notes).chart`);
      window.setTimeout(() => URL.revokeObjectURL(blobUrl), 2500);
      setStatusNote('EXPORTED REFERENCE NOTES.CHART FROM MEMORY BUFFER');
      window.setTimeout(() => setActiveFormat(null), 900);
      return;
    }

    setStatusNote(`GENERATE AN AUDIO TASK FIRST TO PACK BINARY .${format.toUpperCase()}`);
    window.setTimeout(() => setActiveFormat(null), 900);
  };

  return (
    <div
      className={cn(
        'flex flex-col justify-between gap-3 border border-hw-border bg-module p-3.5 shadow-bevel',
        className,
      )}
    >
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-hw-border pb-1.5">
        <div className="flex items-center gap-3">
          <span className="silk-wide">E-01 // MASTER EXPORT BAY</span>
          <span className="h-3 w-px bg-hw-border" aria-hidden="true" />
          <span className="silk-wide text-[9px] text-silk-neutral">{statusNote}</span>
        </div>

        <LedIndicator
          color={hasBackendPackage ? 'green' : 'yellow'}
          on
          size="xs"
          label={hasBackendPackage ? 'PKG LOCKED' : 'REF BUFFER'}
        />
      </div>

      <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-3">
        <PushButton
          size="md"
          variant="master"
          label="Download .SNG"
          sublabel="SongBinary v1 XOR"
          led="green"
          ledOn={hasBackendPackage}
          latched={activeFormat === 'sng'}
          disabled={!hasBackendPackage}
          onClick={() => handleDownload('sng')}
          className="w-full"
        />

        <PushButton
          size="md"
          variant="standard"
          label="Download .CHART"
          sublabel="192 PPQ Text Spec"
          led="blue"
          ledOn
          latched={activeFormat === 'chart'}
          onClick={() => handleDownload('chart')}
          className="w-full"
        />

        <PushButton
          size="md"
          variant="standard"
          label="Download .ZIP"
          sublabel="Full Bundle Archive"
          led="orange"
          ledOn={hasBackendPackage}
          latched={activeFormat === 'zip'}
          disabled={!hasBackendPackage}
          onClick={() => handleDownload('zip')}
          className="w-full"
        />
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2 border-t border-hw-border pt-1.5 text-[8px]">
        <span className="silk-wide">
          TARGET: CLONE HERO / YARG COMPATIBLE
        </span>
        <span className="font-mono uppercase tracking-silk text-silk-dim">
          {hasBackendPackage && completedTaskId
            ? `TASK ID: ${completedTaskId}`
            : 'UPLOAD & GENERATE AUDIO FOR .SNG / .ZIP'}
        </span>
      </div>
    </div>
  );
}
