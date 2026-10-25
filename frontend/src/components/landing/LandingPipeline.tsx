import type { Language } from '../../lib/language';
import { cn } from '../../lib/utils';

const STAGES = [
  { code: 'DSP-STEM', color: 'bg-fret-orange', en: ['Demucs v4 stem separation', 'Isolates the lead guitar from full stereo masters, stripping drums, vocals and sub-bass bleed.'], pt: ['Separação de stems Demucs v4', 'Isola a guitarra solo de masters estéreo completos, removendo bateria, vocais e vazamento de sub-graves.'] },
  { code: 'DSP-BEAT', color: 'bg-fret-yellow', en: ['Tempo & beat tracking', 'Detects BPM and the beat grid so every note lands on a clean 192 PPQ timeline.'], pt: ['Rastreio de tempo e batidas', 'Detecta BPM e a grade de batidas para que cada nota caia em uma linha do tempo limpa de 192 PPQ.'] },
  { code: 'NN-PITCH', color: 'bg-fret-green', en: ['Polyphonic transcription', 'Spotify Basic Pitch turns the isolated stem into note events with onset and duration.'], pt: ['Transcrição polifônica', 'O Basic Pitch da Spotify transforma o stem isolado em eventos de nota com início e duração.'] },
  { code: 'DSP-HARM', color: 'bg-fret-blue', en: ['Harmonic suppression', 'Removes distortion overtones and ghost notes before they reach the chart.'], pt: ['Supressão harmônica', 'Remove harmônicos de distorção e notas fantasma antes que cheguem à chart.'] },
  { code: 'GAME-MAP', color: 'bg-fret-red', en: ['Game design mapping', 'Maps pitch to 5 frets with chord fusion, natural HOPOs and ergonomic limits.'], pt: ['Mapeamento de game design', 'Mapeia notas em 5 trastes com fusão de acordes, HOPOs naturais e limites ergonômicos.'] },
  { code: 'IO-PACK', color: 'bg-fret-open', en: ['Chart & package writing', 'Writes notes.chart, song.ini and a ready-to-play .zip or .sng package.'], pt: ['Escrita de chart e pacote', 'Gera notes.chart, song.ini e um pacote .zip ou .sng pronto para jogar.'] },
];

export function LandingPipeline({ language = 'en' }: { language?: Language }) {
  const pt = language === 'pt-BR';
  return (
    <section id="pipeline" className="scroll-mt-16 border-t border-hw-border bg-chassis py-16">
      <div className="mx-auto max-w-6xl px-4">
        <div className="silk-wide mb-2">01 // {pt ? 'Fluxo de sinal' : 'Signal flow'}</div>
        <h2 className="font-grotesk text-3xl font-bold text-silk sm:text-4xl">
          {pt ? 'Seis etapas. Uma chart limpa.' : 'Six stages. One clean chart.'}
        </h2>
        <p className="mt-3 max-w-2xl text-sm text-silk-dim">
          {pt
            ? 'Todo upload percorre o pipeline completo de DSP + redes neurais, com progresso ao vivo via Server-Sent Events.'
            : 'Every upload runs the full DSP + neural pipeline, streaming progress live over Server-Sent Events.'}
        </p>
        <div className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {STAGES.map((s, i) => {
            const [title, body] = pt ? s.pt : s.en;
            return (
              <article key={s.code} className="border border-hw-border bg-module p-4 shadow-bevel">
                <div className="mb-3 flex items-center justify-between">
                  <span className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-silk text-silk">
                    <span className={cn('inline-block h-2 w-2 rounded-full', s.color)} aria-hidden="true" />
                    {s.code}
                  </span>
                  <span className="silk">{pt ? 'Etapa' : 'Stage'} {String(i + 1).padStart(2, '0')}</span>
                </div>
                <h3 className="font-grotesk text-base font-semibold text-silk">{title}</h3>
                <p className="mt-2 text-xs leading-relaxed text-silk-dim">{body}</p>
              </article>
            );
          })}
        </div>
      </div>
    </section>
  );
}
