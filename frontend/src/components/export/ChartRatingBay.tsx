import { useState } from 'react';
import { submitChartFeedback } from '../../lib/api';
import type { Language } from '../../lib/language';
import { cn } from '../../lib/utils';
import { PushButton } from '../controls/PushButton';

export interface ChartRatingBayProps {
  taskId: string | null;
  songName?: string;
  artist?: string;
  language?: Language;
  className?: string;
}

const TAGS = [
  { id: 'faithful_riffs', en: 'Faithful riffs', pt: 'Riffs fiéis' },
  { id: 'excellent_ergonomics', en: 'Excellent ergonomics', pt: 'Ergonomia excelente' },
  { id: 'too_many_chords', en: 'Too many chords', pt: 'Muitos acordes' },
  { id: 'too_few_chords', en: 'Too few chords', pt: 'Poucos acordes' },
  { id: 'too_fast', en: 'Too fast', pt: 'Muito rápido' },
  { id: 'out_of_sync', en: 'Out of sync', pt: 'Ritmo dessincronizado' },
] as const;

const FRET_COLORS = ['bg-fret-green', 'bg-fret-red', 'bg-fret-yellow', 'bg-fret-blue', 'bg-fret-orange'];
const STORAGE_PREFIX = 'm2c_chart_rating:';

interface StoredRating {
  rating: number;
  tags: string[];
  comment: string;
}

function loadStored(key: string): StoredRating | null {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as StoredRating) : null;
  } catch {
    return null;
  }
}

export function ChartRatingBay({ taskId, songName, artist, language = 'en', className }: ChartRatingBayProps) {
  const pt = language === 'pt-BR';
  const storageKey = `${STORAGE_PREFIX}${taskId ?? 'reference'}`;
  const [stored, setStored] = useState<StoredRating | null>(() => loadStored(storageKey));
  const [rating, setRating] = useState(stored?.rating ?? 0);
  const [tags, setTags] = useState<string[]>(stored?.tags ?? []);
  const [comment, setComment] = useState(stored?.comment ?? '');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submitted = stored !== null;

  const toggleTag = (id: string): void => {
    if (submitted) return;
    setTags((prev) => (prev.includes(id) ? prev.filter((t) => t !== id) : [...prev, id]));
  };

  const handleSubmit = async (): Promise<void> => {
    if (rating < 1 || sending) return;
    setSending(true);
    setError(null);
    try {
      await submitChartFeedback({
        task_id: taskId,
        rating,
        tags,
        comment: comment.trim() || undefined,
        song_name: songName,
        artist,
      });
      const record: StoredRating = { rating, tags, comment: comment.trim() };
      try {
        localStorage.setItem(storageKey, JSON.stringify(record));
      } catch {
        // Storage unavailable: keep in-memory state only.
      }
      setStored(record);
    } catch {
      setError(pt ? 'FALHA AO ENVIAR // TENTE NOVAMENTE' : 'SUBMIT FAILED // TRY AGAIN');
    } finally {
      setSending(false);
    }
  };

  return (
    <div className={cn('flex flex-col gap-3 border border-hw-border bg-chassis p-3 shadow-recess', className)}>
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-hw-border pb-1.5">
        <span className="silk-wide">{pt ? 'Avaliar esta chart' : 'Rate this chart'}</span>
        <span className="silk-wide text-[9px] text-silk-neutral">
          {submitted
            ? (pt ? 'AVALIAÇÃO REGISTRADA' : 'RATING LOGGED')
            : (pt ? 'AJUDE A MELHORAR O MOTOR' : 'HELP TUNE THE ENGINE')}
        </span>
      </div>

      <div className="flex items-center gap-2" role="radiogroup" aria-label={pt ? 'Nota de 1 a 5' : 'Rating from 1 to 5'}>
        {[1, 2, 3, 4, 5].map((n) => {
          const on = n <= rating;
          return (
            <button
              key={n}
              type="button"
              role="radio"
              aria-checked={rating === n}
              aria-label={`${n}`}
              disabled={submitted}
              onClick={() => setRating(n)}
              className="flex flex-col items-center gap-1 border border-hw-border bg-module px-3 py-1.5 disabled:cursor-default"
            >
              <span
                className={cn(
                  'h-3 w-3 rounded-full border border-black/50',
                  on ? FRET_COLORS[n - 1] : 'bg-hw-screw/40',
                  on && 'shadow-[0_0_8px_currentColor]',
                )}
              />
              <span className="font-mono text-[10px] text-silk-dim">{n}</span>
            </button>
          );
        })}
      </div>

      <div className="flex flex-wrap gap-1.5">
        {TAGS.map((t) => {
          const active = tags.includes(t.id);
          return (
            <button
              key={t.id}
              type="button"
              aria-pressed={active}
              disabled={submitted}
              onClick={() => toggleTag(t.id)}
              className={cn(
                'border px-2 py-1 font-mono text-[10px] uppercase tracking-silk disabled:cursor-default',
                active ? 'border-starpower bg-module text-starpower' : 'border-hw-border text-silk-dim hover:text-silk',
              )}
            >
              {pt ? t.pt : t.en}
            </button>
          );
        })}
      </div>

      <textarea
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        disabled={submitted}
        maxLength={500}
        rows={2}
        placeholder={pt ? 'Comentário opcional…' : 'Optional comment…'}
        className="w-full resize-none border border-hw-border bg-module px-2 py-1.5 font-mono text-xs text-silk placeholder:text-silk-dim"
      />

      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="font-mono text-[10px] uppercase tracking-silk text-fret-red">{error}</span>
        <PushButton
          size="sm"
          variant="master"
          label={
            submitted
              ? (pt ? 'Avaliação enviada' : 'Rating sent')
              : sending
                ? (pt ? 'Enviando…' : 'Sending…')
                : (pt ? 'Enviar Avaliação' : 'Submit Rating')
          }
          led="green"
          ledOn={submitted}
          disabled={submitted || sending || rating < 1}
          onClick={() => {
            void handleSubmit();
          }}
        />
      </div>
    </div>
  );
}
