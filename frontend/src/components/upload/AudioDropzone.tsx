import { useRef, useState } from 'react';
import type { ChangeEvent, DragEvent } from 'react';
import { cn } from '../../lib/utils';
import { playMechanicalClick } from '../../lib/mechanicalClick';
import { PushButton } from '../controls/PushButton';
import { LedIndicator } from '../rack/LedIndicator';
import type { Language } from '../../lib/language';

const MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024;

const ALLOWED_EXTENSIONS = ['.mp3', '.wav', '.flac', '.ogg'] as const;

const ALLOWED_MIME_TYPES = [
  'audio/mpeg',
  'audio/mp3',
  'audio/wav',
  'audio/x-wav',
  'audio/wave',
  'audio/vnd.wave',
  'audio/flac',
  'audio/x-flac',
  'audio/ogg',
  'application/ogg',
  'audio/opus',
  'audio/vorbis',
] as const;

export interface DerivedTrackMeta {
  songName: string;
  artist: string;
}

export interface AudioDropzoneProps {
  file: File | null;
  onFileSelect: (file: File | null, derivedMeta?: DerivedTrackMeta) => void;
  disabled?: boolean;
  className?: string;
  language?: Language;
}

function formatByteSize(bytes: number): string {
  if (bytes >= 1024 * 1024) {
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  }
  return `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

function getExtension(filename: string): string {
  const idx = filename.lastIndexOf('.');
  return idx >= 0 ? filename.slice(idx).toLowerCase() : '';
}

function deriveMetadataFromFilename(filename: string): DerivedTrackMeta {
  const stem = filename.replace(/\.[^/.]+$/, '').trim();
  if (stem.includes(' - ')) {
    const [rawArtist, ...rest] = stem.split(' - ');
    const artist = rawArtist.trim() || 'Unknown Artist';
    const songName = rest.join(' - ').trim() || stem;
    return { songName, artist };
  }
  return {
    songName: stem || 'Untitled Track',
    artist: 'Unknown Artist',
  };
}

/**
 * High-visibility audio ingestion deck for Clone Hero chart creation.
 * Features animated drag-and-drop feedback, technical SVG glyphs, and audio validation.
 */
export function AudioDropzone({
  file,
  onFileSelect,
  disabled = false,
  className,
  language = 'en',
}: AudioDropzoneProps) {
  const portuguese = language === 'pt-BR';
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragActive, setDragActive] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const validateAndCommit = (candidate: File | null): void => {
    if (!candidate) {
      setErrorMsg(null);
      onFileSelect(null);
      return;
    }

    const ext = getExtension(candidate.name);
    if (!ALLOWED_EXTENSIONS.includes(ext as (typeof ALLOWED_EXTENSIONS)[number])) {
      setErrorMsg(
        portuguese
          ? `FORMATO INVÁLIDO (${ext || 'DESCONHECIDO'}) — FORMATOS PERMITIDOS: .MP3, .WAV, .FLAC, .OGG`
          : `INVALID EXTENSION (${ext || 'UNKNOWN'}) — ALLOWED AUDIO FORMATS: .MP3, .WAV, .FLAC, .OGG`
      );
      if (inputRef.current) inputRef.current.value = '';
      onFileSelect(null);
      playMechanicalClick(1400, 0.28);
      return;
    }

    const cleanMime = candidate.type.split(';')[0].trim().toLowerCase();
    if (cleanMime && !ALLOWED_MIME_TYPES.includes(cleanMime as (typeof ALLOWED_MIME_TYPES)[number])) {
      setErrorMsg(
        portuguese
          ? `TIPO MIME NÃO SUPORTADO (${cleanMime}) — APENAS ÁUDIOS MP3, WAV, FLAC E OGG SÃO ACEITOS`
          : `UNSUPPORTED MIME TYPE (${cleanMime}) — ONLY MP3, WAV, FLAC, AND OGG AUDIO ARE ACCEPTED`
      );
      if (inputRef.current) inputRef.current.value = '';
      onFileSelect(null);
      playMechanicalClick(1400, 0.28);
      return;
    }

    if (candidate.size === 0) {
      setErrorMsg(
        portuguese
          ? 'FLUXO DE ÁUDIO VAZIO (0 BYTES) — SELECIONE UM ARQUIVO DE ÁUDIO VÁLIDO'
          : 'EMPTY AUDIO STREAM (0 BYTES) — PLEASE SELECT A VALID AUDIO FILE'
      );
      if (inputRef.current) inputRef.current.value = '';
      onFileSelect(null);
      playMechanicalClick(1400, 0.28);
      return;
    }

    if (candidate.size > MAX_FILE_SIZE_BYTES) {
      setErrorMsg(
        portuguese
          ? `TAMANHO DO ARQUIVO (${formatByteSize(candidate.size)}) EXCEDE O LIMITE DE 50 MB — O MÁXIMO PERMITIDO É 50 MB`
          : `FILE SIZE (${formatByteSize(candidate.size)}) EXCEEDS 50 MB LIMIT — MAXIMUM ALLOWED IS 50 MB`
      );
      if (inputRef.current) inputRef.current.value = '';
      onFileSelect(null);
      playMechanicalClick(1400, 0.28);
      return;
    }

    setErrorMsg(null);
    playMechanicalClick(3100, 0.22);
    const meta = deriveMetadataFromFilename(candidate.name);
    onFileSelect(candidate, meta);
  };

  const handleDragOver = (e: DragEvent<HTMLDivElement>): void => {
    e.preventDefault();
    e.stopPropagation();
    if (!disabled) setDragActive(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>): void => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>): void => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (disabled) return;
    const dropped = e.dataTransfer.files?.[0] ?? null;
    if (dropped) validateAndCommit(dropped);
  };

  const handleInputChange = (e: ChangeEvent<HTMLInputElement>): void => {
    const picked = e.target.files?.[0] ?? null;
    if (picked) validateAndCommit(picked);
  };

  const handleBrowse = (): void => {
    if (disabled) return;
    inputRef.current?.click();
  };

  const handleEject = (): void => {
    if (disabled) return;
    if (inputRef.current) inputRef.current.value = '';
    setErrorMsg(null);
    onFileSelect(null);
  };

  const extBadge = file ? getExtension(file.name).replace('.', '').toUpperCase() : (portuguese ? 'SEM MÍDIA' : 'NO MEDIA');

  return (
    <div className={cn('flex flex-col gap-2.5', className)}>
      <div className="flex items-center justify-between">
        <span className="silk">{portuguese ? 'Arquivo de áudio' : 'Audio file'}</span>
        <div className="flex items-center gap-3">
          <span className="silk-wide tabular-nums text-[9px]">
            {file ? `${extBadge} / ${formatByteSize(file.size)}` : (portuguese ? 'Nenhum arquivo' : 'No file selected')}
          </span>
          <LedIndicator
            color={errorMsg ? 'red' : file ? 'green' : dragActive ? 'green' : 'yellow'}
            on={Boolean(errorMsg || file || dragActive)}
            blink={errorMsg ? 'fast' : dragActive ? 'fast' : false}
            size="xs"
            label={
              errorMsg
                ? (portuguese ? 'ERRO' : 'FAULT')
                : file
                  ? (portuguese ? 'MONTADO' : 'MOUNTED')
                  : dragActive
                    ? (portuguese ? 'SOLTE' : 'DROP READY')
                    : (portuguese ? 'AGUARDANDO' : 'STANDBY')
            }
          />
        </div>
      </div>

      <div
        role="button"
        tabIndex={disabled ? -1 : 0}
        aria-label={portuguese ? 'Área para escolher ou arrastar um arquivo de áudio MP3, WAV, FLAC ou OGG.' : 'Choose or drag an MP3, WAV, FLAC, or OGG audio file.'}
        aria-disabled={disabled || undefined}
        onClick={handleBrowse}
        onKeyDown={(e) => {
          if (!disabled && (e.key === 'Enter' || e.key === ' ')) {
            e.preventDefault();
            handleBrowse();
          }
        }}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={cn(
          'no-select relative flex flex-col justify-between overflow-hidden p-5 transition-all duration-200',
          file
            ? 'border border-hw-border bg-chassis shadow-recess'
            : dragActive
              ? 'border-2 border-dashed border-fret-green bg-[#0D1C15] shadow-[0_0_25px_rgba(0,230,118,0.25)] ring-1 ring-fret-green'
              : 'border-2 border-dashed border-hw-screw/90 bg-chassis/80 hover:border-fret-green/70 hover:bg-chassis hover:shadow-[0_0_15px_rgba(0,230,118,0.1)]',
          errorMsg && 'border-fret-red bg-[#1A1014] ring-1 ring-fret-red',
          disabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'
        )}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".mp3,.wav,.flac,.ogg,audio/mpeg,audio/mp3,audio/wav,audio/x-wav,audio/wave,audio/flac,audio/x-flac,audio/ogg,application/ogg"
          onChange={handleInputChange}
          disabled={disabled}
          className="hidden"
          tabIndex={-1}
        />

        {/* Top Status Header */}
        <div className="flex items-center justify-between border-b border-hw-border/80 pb-2.5">
          <div className="flex items-center gap-2">
            <span
              className={cn(
                'inline-block h-2 w-2 border',
                file ? 'border-fret-green bg-fret-green' : dragActive ? 'animate-ping border-fret-green bg-fret-green' : 'border-hw-screw bg-panel'
              )}
              aria-hidden="true"
            />
            <span className="silk-wide text-[9px]">
              {dragActive
                ? (portuguese ? 'Solte o arquivo aqui' : 'Release to add your song')
                : file
                  ? (portuguese ? 'Áudio selecionado' : 'Audio selected')
                  : (portuguese ? 'Escolha sua música' : 'Choose your song')}
            </span>
          </div>
          <span className="border border-hw-border bg-panel px-2 py-0.5 font-mono text-[9px] uppercase tracking-silk text-silk-neutral">
            {file ? extBadge : (portuguese ? 'Máx. 50 MB' : 'Max 50 MB')}
          </span>
        </div>

        {/* Center Target Content */}
        {file ? (
          <div className="flex items-center justify-between gap-4 py-4">
            <div className="flex items-center gap-3.5 min-w-0 flex-1">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center border border-fret-green/40 bg-[#0F1E17] text-fret-green">
                <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
                </svg>
              </div>

              <div className="min-w-0 flex-1">
                <div className="truncate font-mono text-sm font-semibold tracking-silk text-silk" title={file.name}>
                  {file.name}
                </div>
                <div className="mt-1 flex flex-wrap items-center gap-2 font-mono text-[10px] uppercase tracking-silk text-silk-dim">
            <span>{portuguese ? 'Tamanho' : 'Size'}: {formatByteSize(file.size)}</span>
                  <span>|</span>
            <span>{portuguese ? 'Formato' : 'Format'}: {extBadge}</span>
                  <span>|</span>
            <span className="text-fret-green">{portuguese ? 'Pronto para gerar' : 'Ready to create'}</span>
                </div>
              </div>
            </div>

            <div
              onClick={(e) => {
                e.stopPropagation();
              }}
              onKeyDown={(e) => {
                e.stopPropagation();
              }}
            >
              <PushButton
                size="sm"
                variant="alert"
                label={portuguese ? 'Remover' : 'Remove'}
                led="red"
                ledOn={false}
                disabled={disabled}
                onClick={handleEject}
              />
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center gap-3 py-6 text-center">
            {/* Technical Audio Waveform / Upload Glyph */}
            <div
              className={cn(
                'flex h-12 w-12 items-center justify-center border transition-transform duration-200',
                dragActive
                  ? 'scale-110 border-fret-green bg-[#11241C] text-fret-green'
                  : 'border-hw-border bg-panel text-silk-neutral group-hover:border-silk'
              )}
            >
              <svg className="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 16.5V3m0 0L7.5 7.5M12 3l4.5 4.5M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5" />
              </svg>
            </div>

            <div className="flex flex-col items-center gap-1">
              <div
                className={cn(
                  'font-mono text-xs font-bold uppercase tracking-silk-wide transition-colors',
                  dragActive ? 'text-fret-green' : 'text-silk'
                )}
              >
                {dragActive ? (portuguese ? 'Solte o arquivo aqui' : 'Drop your audio file here') : (portuguese ? 'Arraste sua música até aqui' : 'Drag your song here')}
              </div>
              <div className="font-mono text-[10px] uppercase tracking-silk text-silk-dim">
                {portuguese ? 'ou clique para escolher um arquivo' : 'or click to choose a file'}
              </div>
            </div>

            {/* Allowed Formats Tag Bar */}
            <div className="mt-1 flex flex-wrap items-center justify-center gap-1.5" aria-label="Supported file extensions">
              {['.MP3', '.WAV', '.FLAC', '.OGG'].map((ext) => (
                <span
                  key={ext}
                  className="border border-hw-border bg-panel px-2 py-0.5 font-mono text-[9px] uppercase tracking-silk text-silk-neutral"
                >
                  {ext}
                </span>
              ))}
              <span className="border border-hw-border bg-chassis px-2 py-0.5 font-mono text-[9px] uppercase tracking-silk text-silk-dim">
                {portuguese ? 'Máx. 50 MB' : 'Max 50 MB'}
              </span>
            </div>
          </div>
        )}

        {/* Bottom Signal Path Strip */}
        <div className="flex items-center justify-between border-t border-hw-border/80 pt-2.5 text-[9px]">
          <span className="silk-wide">{portuguese ? 'Transformação automática do áudio em notas' : 'Audio is automatically converted into notes'}</span>
          <span className="font-mono uppercase tracking-silk text-silk-neutral">
            {file ? (portuguese ? 'Pronto para criar' : 'Ready to create') : (portuguese ? 'Aguardando arquivo' : 'Waiting for file')}
          </span>
        </div>
      </div>

      {errorMsg ? (
        <div
          role="alert"
          className="border border-fret-red bg-[#1B0F13] px-3 py-2 font-mono text-[10px] uppercase tracking-silk text-fret-red"
        >
          {errorMsg}
        </div>
      ) : null}
    </div>
  );
}
