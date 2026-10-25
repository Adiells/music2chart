import { useEffect, useRef, useState } from 'react';
import type { CSSProperties } from 'react';
import { useLanguage } from '../../lib/language';
import { LandingEngine } from './LandingEngine';
import { LandingFinal } from './LandingFinal';
import { LandingFooter } from './LandingFooter';
import { LandingHeroHighway } from './LandingHeroHighway';
import { LandingPipeline } from './LandingPipeline';
import { LandingPresets } from './LandingPresets';
import { LandingSelfHost } from './LandingSelfHost';
import { LandingTicker } from './LandingTicker';
import { LandingWorkflow } from './LandingWorkflow';
import './landing.css';
import './landing-extras.css';

export interface LandingPageProps {
  onOpenStudio: () => void;
}


function BrandMark() {
  return (
    <span className="brand-mark" aria-hidden="true">
      <i />
      <i />
      <i />
      <i />
      <i />
    </span>
  );
}

export function LandingPage({ onOpenStudio }: LandingPageProps) {
  const [language, setLanguage] = useLanguage();
  const pt = language === 'pt-BR';
  const rootRef = useRef<HTMLDivElement>(null);
  const progressRef = useRef<HTMLDivElement>(null);
  const [toast, setToast] = useState<string | null>(null);

  /* Scroll progress bar */
  useEffect(() => {
    let ticking = false;
    const update = (): void => {
      const doc = document.documentElement;
      const max = doc.scrollHeight - doc.clientHeight;
      if (progressRef.current) progressRef.current.style.width = `${max > 0 ? (doc.scrollTop / max) * 100 : 0}%`;
      ticking = false;
    };
    const onScroll = (): void => {
      if (!ticking) {
        ticking = true;
        window.requestAnimationFrame(update);
      }
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    update();
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  /* Reveal on scroll */
  useEffect(() => {
    const root = rootRef.current;
    if (!root) return undefined;
    const els = Array.from(root.querySelectorAll<HTMLElement>('.reveal'));
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduced || !('IntersectionObserver' in window)) {
      els.forEach((el) => el.classList.add('in'));
      return undefined;
    }
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('in');
            io.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: '0px 0px -40px 0px' },
    );
    els.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);

  /* Copy terminal snippet */
  useEffect(() => {
    const root = rootRef.current;
    if (!root) return undefined;
    let timer = 0;
    const onClick = (event: MouseEvent): void => {
      const btn = (event.target as HTMLElement).closest<HTMLElement>('[data-copy]');
      if (!btn) return;
      const source = document.getElementById(btn.getAttribute('data-copy') ?? '');
      if (!source) return;
      const text = (source.textContent ?? '').replace(/\u00a0/g, ' ');
      navigator.clipboard
        .writeText(text)
        .then(() => {
          setToast(pt ? 'Comando copiado' : 'Command copied to clipboard');
        })
        .catch(() => setToast(pt ? 'Falha ao copiar — selecione manualmente' : 'Copy failed — select manually'))
        .finally(() => {
          window.clearTimeout(timer);
          timer = window.setTimeout(() => setToast(null), 1900);
        });
    };
    root.addEventListener('click', onClick);
    return () => {
      root.removeEventListener('click', onClick);
      window.clearTimeout(timer);
    };
  }, [pt]);

  const trust = [
    { c: '--green', label: pt ? 'PUREZA DE STEM >98%' : 'STEM PURITY >98%' },
    { c: '--yellow', label: pt ? 'MOTOR 192 PPQ' : '192 PPQ ENGINE' },
    { c: '--blue', label: pt ? 'FUSÃO DE ACORDES 35MS' : 'CHORD FUSION 35MS' },
    { c: '--power', label: pt ? 'SNG EM UM CLIQUE' : 'ONE-CLICK SNG' },
  ];

  return (
    <div className="m2c-landing" ref={rootRef} id="top">
      <div className="scroll-progress" ref={progressRef} aria-hidden="true" />

      <header className="site-header">
        <div className="wrap header-inner">
          <a className="brand" href="#top" aria-label="Music2Chart home">
            <BrandMark />
            <span className="brand-name">Music2Chart</span>
            <span className="brand-sub">AI Chart Studio // v1.0</span>
          </a>

          <nav className="site-nav" aria-label="Primary">
            <a href="#pipeline">Pipeline</a>
            <a href="#engine">{pt ? 'Motor' : 'Engine'}</a>
            <a href="#presets">Presets</a>
            <a href="#workflow">{pt ? 'Fluxo' : 'Workflow'}</a>
            <a href="#selfhost">Self-host</a>
          </nav>

          <div className="header-actions">
            <span className="lang" role="group" aria-label="Language">
              <button type="button" aria-pressed={!pt} onClick={() => setLanguage('en')}>
                EN
              </button>
              /
              <button type="button" aria-pressed={pt} onClick={() => setLanguage('pt-BR')}>
                PT-BR
              </button>
            </span>
            <button type="button" className="btn btn-sm btn-primary" onClick={onOpenStudio}>
              {pt ? 'Abrir Studio' : 'Open Studio'}
            </button>
          </div>
        </div>
      </header>

      <main>
        <section className="hero">
          <div className="wrap hero-inner">
            <div className="hero-copy">
              <div className="eyebrow reveal">
                <span className="led on" style={{ color: 'var(--green)' }} />
                {pt ? 'SISTEMA OPERACIONAL' : 'SYSTEM OPERATIONAL'} <span className="sep">//</span> DEMUCS V4 + BASIC
                PITCH
              </div>

              <h1 className="display reveal" style={{ '--delay': '.05s' } as CSSProperties}>
                {pt ? (
                  <>
                    Qualquer música. Uma chart de <span className="lit">nível campeonato</span> para{' '}
                    <span className="underline">Clone&nbsp;Hero</span>.
                  </>
                ) : (
                  <>
                    Any track. One
                    <br />
                    <span className="lit">tournament&#8209;grade</span>
                    <br />
                    <span className="underline">Clone&nbsp;Hero</span> chart.
                  </>
                )}
              </h1>

              <p className="hero-lead reveal" style={{ '--delay': '.1s' } as CSSProperties}>
                {pt ? (
                  <>
                    Envie um MP3, WAV, FLAC ou OGG. O Music2Chart isola a guitarra com <strong>Demucs v4</strong>,
                    transcreve com <strong>Spotify Basic Pitch</strong> e mapeia com heurísticas autênticas de game
                    design — depois você confere cada nota na <strong>highway 3D</strong> antes de exportar{' '}
                    <span className="nowrap">
                      <strong>.sng</strong> ou <strong>.chart</strong>
                    </span>
                    .
                  </>
                ) : (
                  <>
                    Drop in an MP3, WAV, FLAC or OGG. Music2Chart isolates the guitar with <strong>Demucs v4</strong>,
                    transcribes it with <strong>Spotify Basic Pitch</strong>, and maps it through authentic game-design
                    heuristics — then lets you preview every note on a <strong>3D highway</strong> before exporting{' '}
                    <span className="nowrap">
                      <strong>.sng</strong> or <strong>.chart</strong>
                    </span>
                    .
                  </>
                )}
              </p>

              <div className="hero-actions reveal" style={{ '--delay': '.15s' } as CSSProperties}>
                <button type="button" className="btn btn-primary" onClick={onOpenStudio}>
                  {pt ? 'Abrir Studio' : 'Open Studio'}{' '}
                  <span className="arrow" aria-hidden="true">
                    →
                  </span>
                </button>
                <a className="btn btn-ghost" href="#selfhost">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
                    <path d="M4 17l6-6-6-6M12 19h8" />
                  </svg>
                  {pt ? 'Hospede você mesmo' : 'Self-host it'}
                </a>
              </div>

              <div className="hero-trust reveal" style={{ '--delay': '.2s' } as CSSProperties}>
                {trust.map((t) => (
                  <span key={t.c}>
                    <i className="led" style={{ color: `var(${t.c})` }} /> {t.label}
                  </span>
                ))}
              </div>
            </div>

            <LandingHeroHighway language={language} />
          </div>
        </section>

        <LandingTicker />
        <LandingPipeline language={language} />
        <LandingEngine language={language} />
        <LandingPresets language={language} />
        <LandingWorkflow language={language} />
        <LandingSelfHost language={language} onOpenStudio={onOpenStudio} />
        <LandingFinal language={language} onOpenStudio={onOpenStudio} />
      </main>

      <LandingFooter language={language} onOpenStudio={onOpenStudio} />

      <div className={toast ? 'toast show' : 'toast'} role="status" aria-live="polite">
        {toast}
      </div>
    </div>
  );
}
