import { useRef, useState } from 'react';
import type { ChangeEvent, DragEvent } from 'react';
import { cn } from '../../lib/utils';
import { playMechanicalClick } from '../../lib/mechanicalClick';
import { PushButton } from '../controls/PushButton';
import { LedIndicator } from '../rack/LedIndicator';

const MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024; // 100 MB (104,857,600 bytes)

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
 * Industrial tape/media bay dropzone for raw audio ingestion (.mp3, .wav, .flac, .ogg).
 * Features sharp 1px recessed framing, status LEDs, format readout, and mechanical eject.
 */
export function AudioDropzone({
  file,
  onFileSelect,
  disabled = false,
  className,
}: AudioDropzoneProps) {
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
        `INVALID EXTENSION (${ext || 'UNKNOWN'}) — ALLOWED AUDIO FORMATS: .MP3, .WAV, .FLAC, .OGG`
      );
      if (inputRef.current) inputRef.current.value = '';
      onFileSelect(null);
      playMechanicalClick(1400, 0.28);
      return;
    }

    const cleanMime = candidate.type.split(';')[0].trim().toLowerCase();
    if (cleanMime && !ALLOWED_MIME_TYPES.includes(cleanMime as (typeof ALLOWED_MIME_TYPES)[number])) {
      setErrorMsg(
        `UNSUPPORTED MIME TYPE (${cleanMime}) — ONLY MP3, WAV, FLAC, AND OGG AUDIO ARE ACCEPTED`
      );
      if (inputRef.current) inputRef.current.value = '';
      onFileSelect(null);
      playMechanicalClick(1400, 0.28);
      return;
    }

    if (candidate.size === 0) {
      setErrorMsg('EMPTY AUDIO STREAM (0 BYTES) — PLEASE SELECT A VALID AUDIO FILE');
      if (inputRef.current) inputRef.current.value = '';
      onFileSelect(null);
      playMechanicalClick(1400, 0.28);
      return;
    }

    if (candidate.size > MAX_FILE_SIZE_BYTES) {
      setErrorMsg(
        `FILE SIZE (${formatByteSize(candidate.size)}) EXCEEDS 100 MB LIMIT — MAXIMUM ALLOWED IS 100 MB`
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

  const extBadge = file ? getExtension(file.name).replace('.', '').toUpperCase() : 'NO MEDIA';

  return (
    <div className={cn('flex flex-col gap-2.5', className)}>
      <div className="flex items-center justify-between">
        <span className="silk">Audio Input Deck</span>
        <div className="flex items-center gap-3">
          <span className="silk-wide tabular-nums text-[9px]">
            {file ? `${extBadge} / ${formatByteSize(file.size)}` : 'BAY EMPTY'}
          </span>
          <LedIndicator
            color={errorMsg ? 'red' : file ? 'green' : 'yellow'}
            on={Boolean(errorMsg || file || dragActive)}
            blink={errorMsg ? 'fast' : dragActive ? 'slow' : false}
            size="xs"
            label={errorMsg ? 'ERR' : file ? 'LOCKED' : 'STBY'}
          />
        </div>
      </div>

      <div
        role="button"
        tabIndex={disabled ? -1 : 0}
        aria-label="Audio file dropzone. Click or drag an MP3, WAV, FLAC, or OGG file."
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
          'no-select relative flex flex-col gap-2.5 border bg-chassis p-3 shadow-recess transition-colors',
          dragActive
            ? 'border-fret-green bg-[#111916]'
            : errorMsg
              ? 'border-fret-red bg-[#1A1014]'
              : file
                ? 'border-hw-screw bg-chassis'
                : 'border-hw-border hover:border-hw-screw',
          disabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer',
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

        {/* Top mechanical bay slot graphic */}
        <div className="flex items-center justify-between border-b border-hw-border pb-2">
          <div className="flex items-center gap-2">
            <span className="inline-block h-2 w-2 border border-hw-screw bg-panel" aria-hidden="true" />
            <span className="silk-wide text-[9px]">
              {dragActive ? 'DROP STREAM TO LOCK BAY' : file ? 'SOURCE STREAM MOUNTED' : 'INSERT MASTER AUDIO'}
            </span>
          </div>
          <span className="border border-hw-border bg-panel px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-silk text-silk-neutral">
            {extBadge}
          </span>
        </div>

        {/* Center readout */}
        {file ? (
          <div className="flex items-center justify-between gap-3 py-1">
            <div className="min-w-0 flex-1">
              <div className="truncate font-mono text-xs font-semibold tracking-silk text-silk" title={file.name}>
                {file.name}
              </div>
              <div className="mt-1 flex items-center gap-3 font-mono text-[10px] uppercase tracking-silk text-silk-dim">
                <span>SIZE: {formatByteSize(file.size)}</span>
                <span>|</span>
                <span>CODEC: {extBadge} PCM/STREAM</span>
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
                label="Eject"
                led="red"
                ledOn={false}
                disabled={disabled}
                onClick={handleEject}
              />
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center gap-1 py-2 text-center">
            <div className="font-mono text-[11px] font-medium uppercase tracking-silk-wide text-silk">
              DRAG &amp; DROP AUDIO MASTER OR CLICK TO LOAD
            </div>
            <div className="silk-wide text-[9px]">
              ACCEPTED CONTAINERS: .MP3 / .WAV / .FLAC / .OGG (MAX 100 MB)
            </div>
          </div>
        )}

        {/* Bottom signal path bar */}
        <div className="flex items-center justify-between border-t border-hw-border pt-2 text-[9px]">
          <span className="silk-wide">INPUT BUS: CH 1-2 STEREO</span>
          <span className="font-mono uppercase tracking-silk text-silk-neutral">
            {file ? 'READY FOR DEMUCS STEM SPLIT' : 'AWAITING SIGNAL'}
          </span>
        </div>
      </div>

      {errorMsg ? (
        <div
          role="alert"
          className="border border-fret-red bg-[#1B0F13] px-2.5 py-1.5 font-mono text-[10px] uppercase tracking-silk text-fret-red"
        >
          {errorMsg}
        </div>
      ) : null}
    </div>
  );
}
