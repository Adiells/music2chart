import { useEffect, useMemo, useRef, useState } from 'react';
import type { CSSProperties } from 'react';
import * as THREE from 'three';
import { DEMO_CHART_TEXT, getInstantTempoAtTime, parseChartText } from '../../hooks/useChartParser';
import type { Language } from '../../lib/language';
import { cn } from '../../lib/utils';
import { NoteRenderer } from '../highway/NoteRenderer';
import { LANE_HEX_COLORS, LANE_X_POSITIONS, StrikeBar } from '../highway/StrikeBar';

export interface LandingHeroHighwayProps {
  language?: Language;
  className?: string;
}

/**
 * Hero 3D highway: same Three.js scene style as the studio preview (HighwayScene),
 * looping the built-in demo chart without any audio. Pauses when off-screen.
 */
export function LandingHeroHighway({ language = 'en', className }: LandingHeroHighwayProps) {
  const pt = language === 'pt-BR';
  const mountRef = useRef<HTMLDivElement>(null);
  const frameRef = useRef<HTMLDivElement>(null);
  const chart = useMemo(() => parseChartText(DEMO_CHART_TEXT), []);
  const chartRef = useRef(chart);
  const [hud, setHud] = useState({
    bpm: 120,
    nps: 0,
    progress: 0,
    time: 0,
    total: 0,
    lanes: [false, false, false, false, false] as boolean[],
  });

  useEffect(() => {
    const container = mountRef.current;
    const frame = frameRef.current;
    if (!container || !frame) return undefined;

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
    } catch {
      container.innerHTML =
        '<div class="flex h-full w-full items-center justify-center p-6 text-center font-mono text-xs uppercase tracking-silk text-silk-dim">3D WEBGL CONTEXT UNAVAILABLE</div>';
      return undefined;
    }

    const width = Math.max(280, container.clientWidth);
    const height = Math.max(180, container.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(width, height);
    renderer.setClearColor(new THREE.Color('#090A0D'), 1);
    container.innerHTML = '';
    container.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    scene.fog = new THREE.Fog('#090A0D', 13.5, 25.5);
    const camera = new THREE.PerspectiveCamera(46, width / height, 0.1, 45);
    camera.position.set(0, 3.85, 3.45);
    camera.lookAt(0, -0.15, -6.8);

    scene.add(new THREE.AmbientLight('#D5D9E2', 0.85));
    const keyLight = new THREE.DirectionalLight('#FFFFFF', 1.35);
    keyLight.position.set(2.5, 9.0, 5.5);
    scene.add(keyLight);
    const rimLight = new THREE.DirectionalLight('#6A759B', 0.65);
    rimLight.position.set(-3.0, 5.0, -10.0);
    scene.add(rimLight);

    const deck = new THREE.Group();
    const deckLength = 28;
    const deckZ = -11.5;
    const bedGeo = new THREE.BoxGeometry(5.32, 0.08, deckLength);
    const bedMat = new THREE.MeshStandardMaterial({ color: '#14171E', metalness: 0.6, roughness: 0.45 });
    const bed = new THREE.Mesh(bedGeo, bedMat);
    bed.position.set(0, -0.045, deckZ);
    deck.add(bed);

    const channelGeo = new THREE.PlaneGeometry(0.9, deckLength);
    channelGeo.rotateX(-Math.PI / 2);
    const channelMat = new THREE.MeshStandardMaterial({ color: '#0B0C10', metalness: 0.25, roughness: 0.8 });
    const guideGeo = new THREE.PlaneGeometry(0.035, deckLength);
    guideGeo.rotateX(-Math.PI / 2);
    const guideMats: THREE.MeshBasicMaterial[] = [];
    for (let i = 0; i < 5; i += 1) {
      const ch = new THREE.Mesh(channelGeo, channelMat);
      ch.position.set(LANE_X_POSITIONS[i], 0.001, deckZ);
      deck.add(ch);
      const gm = new THREE.MeshBasicMaterial({ color: LANE_HEX_COLORS[i], transparent: true, opacity: 0.14 });
      guideMats.push(gm);
      const g = new THREE.Mesh(guideGeo, gm);
      g.position.set(LANE_X_POSITIONS[i], 0.003, deckZ);
      deck.add(g);
    }

    const innerRailGeo = new THREE.BoxGeometry(0.04, 0.03, deckLength);
    const outerRailGeo = new THREE.BoxGeometry(0.11, 0.09, deckLength);
    const innerRailMat = new THREE.MeshStandardMaterial({ color: '#252934', metalness: 0.7, roughness: 0.35 });
    const outerRailMat = new THREE.MeshStandardMaterial({ color: '#383E4E', metalness: 0.8, roughness: 0.28 });
    for (const x of [-2.5, -1.5, -0.5, 0.5, 1.5, 2.5]) {
      const outer = Math.abs(x) > 2.4;
      const rail = new THREE.Mesh(outer ? outerRailGeo : innerRailGeo, outer ? outerRailMat : innerRailMat);
      rail.position.set(x, outer ? 0.025 : 0.01, deckZ);
      deck.add(rail);
    }
    scene.add(deck);

    const strikeBar = new StrikeBar();
    scene.add(strikeBar.group);
    const noteRenderer = new NoteRenderer();
    scene.add(noteRenderer.group);

    const resizeObserver = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) return;
      const w = Math.max(280, Math.floor(entry.contentRect.width));
      const h = Math.max(180, Math.floor(entry.contentRect.height));
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    });
    resizeObserver.observe(container);

    // Loop window: demo chart duration (with a short tail), rendered with a virtual clock.
    const loopLen = Math.max(8, chartRef.current.durationSeconds + 1.5);
    let virtualTime = 0;
    let lastTs = 0;
    let rafId = 0;
    let visible = true;
    let lastHudAt = 0;

    const animate = (ts: number): void => {
      rafId = requestAnimationFrame(animate);
      const dt = lastTs ? Math.min(0.1, (ts - lastTs) / 1000) : 0;
      lastTs = ts;
      virtualTime = (virtualTime + dt) % loopLen;
      const c = chartRef.current;
      const hit = noteRenderer.update(virtualTime, c.notes, c.beatLines);
      strikeBar.update(hit.activeLanes, hit.openHit);
      renderer.render(scene, camera);

      if (ts - lastHudAt > 120) {
        lastHudAt = ts;
        const snap = getInstantTempoAtTime(virtualTime, c);
        const bucket = c.npsBuckets.find((b) => virtualTime >= b.startTime && virtualTime < b.endTime);
        setHud({
          bpm: Math.round(snap.bpm),
          nps: bucket ? bucket.nps : 0,
          progress: virtualTime / loopLen,
          time: virtualTime,
          total: loopLen,
          lanes: hit.activeLanes.map(Boolean),
        });
      }
    };

    const start = (): void => {
      if (rafId) return;
      lastTs = 0;
      rafId = requestAnimationFrame(animate);
    };
    const stop = (): void => {
      if (rafId) cancelAnimationFrame(rafId);
      rafId = 0;
    };

    const io = new IntersectionObserver(
      (entries) => {
        visible = entries[0]?.isIntersecting ?? true;
        if (visible) start();
        else stop();
      },
      { threshold: 0.01 },
    );
    io.observe(frame);
    start();

    return () => {
      stop();
      io.disconnect();
      resizeObserver.disconnect();
      strikeBar.dispose();
      noteRenderer.dispose();
      bedGeo.dispose();
      bedMat.dispose();
      channelGeo.dispose();
      channelMat.dispose();
      guideGeo.dispose();
      guideMats.forEach((m) => m.dispose());
      innerRailGeo.dispose();
      outerRailGeo.dispose();
      innerRailMat.dispose();
      outerRailMat.dispose();
      renderer.dispose();
    };
  }, []);

  const fmt = (s: number): string => {
    const m = Math.floor(s / 60);
    const sec = s - m * 60;
    return `${String(m).padStart(2, '0')}:${sec.toFixed(2).padStart(5, '0')}`;
  };
  const FRET_VARS = ['--green', '--red', '--yellow', '--blue', '--orange'];
  const FRET_LABELS = ['G', 'R', 'Y', 'B', 'O'];
  const levelOn = Math.min(5, Math.max(1, Math.round(hud.nps / 2) + 3));

  return (
    <div
      ref={frameRef}
      className={cn('rig reveal', className)}
      style={{ '--delay': '.12s' } as CSSProperties}
    >
      <span className="screw tl" style={{ '--a': '24deg' } as CSSProperties} />
      <span className="screw tr" style={{ '--a': '67deg' } as CSSProperties} />
      <span className="screw bl" style={{ '--a': '108deg' } as CSSProperties} />
      <span className="screw br" style={{ '--a': '41deg' } as CSSProperties} />

      <div className="rig-head">
        <div className="rig-title">
          <span className="led on" style={{ color: 'var(--green)' }} />
          {pt ? 'Rig de prévia ao vivo' : 'Live preview rig'} <span className="sep">/</span>{' '}
          <span className="muted">Highway-3D</span>
        </div>
        <div className="rig-meta">
          <span>192 PPQ</span>
          <span className="dot" />
          <span>{pt ? 'Sync travado' : 'Sync locked'}</span>
        </div>
      </div>

      <div className="stage" role="img" aria-label={pt ? 'Prévia 3D da highway' : '3D highway preview'}>
        <div ref={mountRef} className="absolute inset-0" />

        <div className="hud hud-tl">
          <div className="hud-k">{pt ? 'Charteando agora' : 'Now charting'}</div>
          <div className="hud-v">
            {chart.songName || 'Demo'} <small>/ {chart.artist || 'Music2Chart'}</small>
          </div>
        </div>
        <div className="hud hud-tr">
          <div className="hud-duo">
            <div>
              <div className="hud-k">Tempo</div>
              <div className="hud-v">
                {hud.bpm} <small>BPM</small>
              </div>
            </div>
            <div>
              <div className="hud-k">{pt ? 'Densidade' : 'Density'}</div>
              <div className="hud-v">
                {hud.nps.toFixed(1)} <small>NPS</small>
              </div>
            </div>
          </div>
        </div>
        <div className="hud hud-bl">
          <div className="hud-k">Playhead</div>
          <div className="hud-v">
            {fmt(hud.time)} <small>/ {fmt(hud.total)}</small>
          </div>
        </div>
        <div className="hud hud-br">
          <div className="hud-k">{pt ? 'Dificuldade' : 'Difficulty'}</div>
          <div className="hud-v">Expert</div>
          <div className="level" aria-hidden="true">
            {[0, 1, 2, 3, 4].map((i) => (
              <i key={i} style={{ opacity: i < levelOn ? 1 : 0.25 }} />
            ))}
          </div>
        </div>
      </div>

      <div className="rig-foot">
        <div className="fret-leds">
          {FRET_VARS.map((v, i) => (
            <span key={v}>
              <i
                style={
                  {
                    '--c': `var(${v})`,
                    opacity: hud.lanes[i] ? 1 : 0.55,
                  } as CSSProperties
                }
              />
              {FRET_LABELS[i]}
            </span>
          ))}
        </div>
        <span style={{ color: 'var(--power)' }}>◈ {pt ? 'Star power pronto' : 'Star power ready'}</span>
      </div>
    </div>
  );
}
