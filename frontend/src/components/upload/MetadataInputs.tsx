import { cn } from '../../lib/utils';
import { PushButton } from '../controls/PushButton';
import type { Language } from '../../lib/language';

export type OutputFormatOption = 'both' | 'sng' | 'chart';

export interface TrackMetadataState {
  songName: string;
  artist: string;
  genre: string;
  difficulty: number;
  maxFrets: number;
  outputFormat: OutputFormatOption;
}

export interface MetadataInputsProps {
  value: TrackMetadataState;
  onChange: (next: TrackMetadataState) => void;
  disabled?: boolean;
  className?: string;
  language?: Language;
}

const GENRE_OPTIONS = ['rock', 'metal', 'prog', 'indie', 'electronic', 'punk', 'jazz'] as const;
const MAX_FRET_OPTIONS: readonly { value: number; label: string; sub: string }[] = [
  { value: 1, label: '1 Fret', sub: 'Mono' },
  { value: 2, label: '2 Frets', sub: 'Power' },
  { value: 3, label: '3 Frets', sub: 'Triad' },
];
const FORMAT_OPTIONS: readonly { value: OutputFormatOption; label: string; sub: string }[] = [
  { value: 'both', label: 'BOTH', sub: 'SNG + CHART' },
  { value: 'sng', label: 'SNG', sub: 'SONGBINARY V1' },
  { value: 'chart', label: 'CHART', sub: '192 PPQ TEXT' },
];

/**
 * Recessed terminal input bank for track metadata (Song Title, Artist, Genre,
 * Max Simultaneous Frets, and Output Packaging Format).
 */
export function MetadataInputs({
  value,
  onChange,
  disabled = false,
  className,
  language = 'en',
}: MetadataInputsProps) {
  const update = <K extends keyof TrackMetadataState>(key: K, fieldVal: TrackMetadataState[K]): void => {
    onChange({ ...value, [key]: fieldVal });
  };

  return (
    <div className={cn('flex flex-col gap-3', className)}>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <label className="flex flex-col gap-1">
          <div className="flex items-center justify-between">
            <span className="silk">{language === 'pt-BR' ? 'Nome da música' : 'Song title'}</span>
            <span className="silk-wide text-[8px]">SONG.INI / NAME</span>
          </div>
          <input
            type="text"
            value={value.songName}
            disabled={disabled}
            onChange={(e) => update('songName', e.target.value)}
            placeholder="AUTO-DETECT FROM FILE"
            className="border border-hw-border bg-chassis px-2.5 py-1.5 font-mono text-xs tracking-silk text-silk placeholder:text-silk-dim/40 shadow-recess outline-none focus:border-silk-neutral disabled:opacity-50"
          />
        </label>

        <label className="flex flex-col gap-1">
          <div className="flex items-center justify-between">
            <span className="silk">{language === 'pt-BR' ? 'Artista' : 'Artist'}</span>
            <span className="silk-wide text-[8px]">SONG.INI / ARTIST</span>
          </div>
          <input
            type="text"
            value={value.artist}
            disabled={disabled}
            onChange={(e) => update('artist', e.target.value)}
            placeholder="UNKNOWN ARTIST"
            className="border border-hw-border bg-chassis px-2.5 py-1.5 font-mono text-xs tracking-silk text-silk placeholder:text-silk-dim/40 shadow-recess outline-none focus:border-silk-neutral disabled:opacity-50"
          />
        </label>
      </div>

      <details className="border-t border-hw-border pt-3">
        <summary className="cursor-pointer font-mono text-xs text-silk-neutral">{language === 'pt-BR' ? 'Mais opções' : 'More options'}</summary>
        <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
        <label className="flex flex-col gap-1">
          <span className="silk">Genre Tag</span>
          <select
            value={value.genre}
            disabled={disabled}
            onChange={(e) => update('genre', e.target.value)}
            className="border border-hw-border bg-chassis px-2.5 py-1.5 font-mono text-xs uppercase tracking-silk text-silk shadow-recess outline-none focus:border-silk-neutral disabled:opacity-50"
          >
            {GENRE_OPTIONS.map((g) => (
              <option key={g} value={g} className="bg-chassis text-silk">
                {g.toUpperCase()}
              </option>
            ))}
          </select>
        </label>

        <div className="flex flex-col gap-1">
          <span className="silk">Chord Clamp</span>
          <div className="grid grid-cols-3 gap-1" role="radiogroup" aria-label="Max Simultaneous Frets">
            {MAX_FRET_OPTIONS.map((opt) => (
              <PushButton
                key={opt.value}
                size="sm"
                label={opt.label}
                sublabel={opt.sub}
                led="blue"
                ledOn={value.maxFrets === opt.value}
                latched={value.maxFrets === opt.value}
                disabled={disabled}
                role="radio"
                aria-checked={value.maxFrets === opt.value}
                onClick={() => update('maxFrets', opt.value)}
                className="w-full"
              />
            ))}
          </div>
        </div>
        </div>

        <div className="mt-3 flex w-full flex-col gap-1">
        <span className="silk">Container Mode</span>
        <div className="grid grid-cols-3 gap-1.5" role="radiogroup" aria-label="Output Format">
          {FORMAT_OPTIONS.map((opt) => (
            <PushButton
              key={opt.value}
              size="sm"
              label={opt.label}
              sublabel={opt.sub}
              led="green"
              ledOn={value.outputFormat === opt.value}
              latched={value.outputFormat === opt.value}
              disabled={disabled}
              role="radio"
              aria-checked={value.outputFormat === opt.value}
              onClick={() => update('outputFormat', opt.value)}
              className="w-full"
            />
          ))}
        </div>
        </div>
      </details>
    </div>
  );
}
