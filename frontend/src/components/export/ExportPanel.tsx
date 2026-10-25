import { useEffect, useRef, useState } from 'react';
import { getApiUrl } from '../../lib/api';
import { cn } from '../../lib/utils';
import { PushButton } from '../controls/PushButton';
import { LedIndicator } from '../rack/LedIndicator';
import { ChartRatingBay } from './ChartRatingBay';
import type { Language } from '../../lib/language';

export type ExportFormat = 'chart' | 'zip';

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
  language?: Language;
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
 * Clone Hero artifacts in `.zip` archive or `.chart` (notes.chart) format.
 */
export function ExportPanel({
  completedTaskId,
  rawChartText,
  songName,
  artist,
  className,
  language = 'en',
}: ExportPanelProps) {
  const portuguese = language === 'pt-BR';
  const defaultIdleStatus = portuguese ? 'PRONTO PARA BAIXAR ARQUIVOS' : 'READY FOR PACKAGE DISPATCH';

  const [activeFormat, setActiveFormat] = useState<ExportFormat | null>(null);
  const [statusNote, setStatusNote] = useState<string | null>(null);
  const statusResetRef = useRef<number | null>(null);

  const displayStatusNote = statusNote ?? defaultIdleStatus;

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
      setStatusNote(null);
    }, STATUS_RESET_MS);
  };

  const handleDownload = (format: ExportFormat): void => {
    setActiveFormat(format);
    scheduleStatusReset();

    if (hasBackendPackage && completedTaskId) {
      const url = getApiUrl(`/api/v1/chart/download/${encodeURIComponent(completedTaskId)}?format=${format}`);
      setStatusNote(
        portuguese
          ? `BAIXANDO PACOTE .${format.toUpperCase()} // TAREFA ${completedTaskId.slice(0, 8).toUpperCase()}`
          : `DISPATCHING .${format.toUpperCase()} STREAM // TASK ${completedTaskId.slice(0, 8).toUpperCase()}`
      );
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
      setStatusNote(
        portuguese
          ? 'ARQUIVO .CHART EXPORTADO DO BUFFER DE MEMÓRIA'
          : 'EXPORTED REFERENCE NOTES.CHART FROM MEMORY BUFFER'
      );
      window.setTimeout(() => setActiveFormat(null), 900);
      return;
    }

    setStatusNote(
      portuguese
        ? `GERE UMA CHART PRIMEIRO PARA EMPACOTAR O .${format.toUpperCase()}`
        : `GENERATE AN AUDIO TASK FIRST TO PACK .${format.toUpperCase()}`
    );
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
          <span className="silk-wide">{portuguese ? 'Baixar arquivos para o jogo' : 'Download game files'}</span>
          <span className="h-3 w-px bg-hw-border" aria-hidden="true" />
          <span className="silk-wide text-[9px] text-silk-neutral">{displayStatusNote}</span>
        </div>

        <LedIndicator
          color={hasBackendPackage ? 'green' : 'yellow'}
          on
          size="xs"
          label={hasBackendPackage ? (portuguese ? 'PACOTE PRONTO' : 'PKG LOCKED') : (portuguese ? 'BUFFER REF' : 'REF BUFFER')}
        />
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <PushButton
          size="md"
          variant="master"
          label={portuguese ? 'Baixar .ZIP' : 'Download .ZIP'}
          sublabel={portuguese ? 'Pacote completo para Clone Hero' : 'Full Clone Hero package'}
          led="green"
          ledOn={hasBackendPackage}
          latched={activeFormat === 'zip'}
          disabled={!hasBackendPackage}
          onClick={() => handleDownload('zip')}
          className="w-full"
        />

        <PushButton
          size="md"
          variant="standard"
          label={portuguese ? 'Baixar .CHART' : 'Download .CHART'}
          sublabel={portuguese ? 'Arquivo de notas puro' : 'Pure notes file'}
          led="blue"
          ledOn
          latched={activeFormat === 'chart'}
          onClick={() => handleDownload('chart')}
          className="w-full"
        />
      </div>

      <ChartRatingBay
        taskId={hasBackendPackage ? completedTaskId : null}
        songName={songName}
        artist={artist}
        language={language}
      />

      <div className="flex flex-wrap items-center justify-between gap-2 border-t border-hw-border pt-1.5 text-[8px]">
        <span className="silk-wide">
          {portuguese ? 'Compatível com Clone Hero e YARG' : 'Compatible with Clone Hero and YARG'}
        </span>
        <span className="font-mono uppercase tracking-silk text-silk-dim">
          {hasBackendPackage && completedTaskId
            ? `TASK ID: ${completedTaskId}`
            : (portuguese ? 'ENVIE E GERE O ÁUDIO PARA BAIXAR O .ZIP' : 'UPLOAD & GENERATE AUDIO FOR .ZIP')}
        </span>
      </div>
    </div>
  );
}
