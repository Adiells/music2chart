import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import type { PlaybackSpeed } from '../../hooks/useAudioPlayer';
import type { ParsedChart } from '../../hooks/useChartParser';
import { getInstantTempoAtTime } from '../../hooks/useChartParser';
import { cn } from '../../lib/utils';
import { FRET_LANES } from '../../theme/tokens';
import { PushButton } from '../controls/PushButton';
import { LedIndicator } from '../rack/LedIndicator';
import { NoteRenderer } from './NoteRenderer';
import { LANE_HEX_COLORS, LANE_X_POSITIONS, StrikeBar } from './StrikeBar';

export interface HighwaySceneProps {
  chart: ParsedChart;
  isPlaying: boolean;
  currentTime: number;
  duration: number;
  playbackRate: PlaybackSpeed;
  getCurrentTime: () => number;
  onTogglePlay: () => void;
  onStop: () => void;
  onChangeSpeed: (rate: PlaybackSpeed) => void;
  isDemoChart?: boolean;
  className?: string;
}

const SPEED_OPTIONS: readonly PlaybackSpeed[] = [0.5, 0.75, 1.0];

/**
 * Three.js 3D Clone Hero Highway Visualizer:
 *  - Inclined perspective camera over 5 dark recessed channels ("5 canaletas escuras")
 *  - Metallic lane dividers and outer chassis rails
 *  - StrikeBar at the base (z = 0) with 5 color receptors and Open-note flash bar
 *  - NoteRenderer for 5-color gems, HOPOs without strum ring, translucent sustains, and Open bars
 *  - Rigorous frame-accurate audio synchronization via `getCurrentTime()`
 */
export function HighwayScene({
  chart,
  isPlaying,
  currentTime,
  duration,
  playbackRate,
  getCurrentTime,
  onTogglePlay,
  onStop,
  onChangeSpeed,
  isDemoChart = false,
  className,
}: HighwaySceneProps) {
  const mountRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<ParsedChart>(chart);
  const getTimeRef = useRef<() => number>(getCurrentTime);

  const [hitLanes, setHitLanes] = useState<[boolean, boolean, boolean, boolean, boolean]>([
    false,
    false,
    false,
    false,
    false,
  ]);
  const [openHit, setOpenHit] = useState(false);
  const [viewMode, setViewMode] = useState<'compact' | 'focus'>('focus');

  useEffect(() => {
    chartRef.current = chart;
  }, [chart]);

  useEffect(() => {
    getTimeRef.current = getCurrentTime;
  }, [getCurrentTime]);

  useEffect(() => {
    const container = mountRef.current;
    if (!container) return undefined;

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({
        antialias: true,
        powerPreference: 'high-performance',
      });
    } catch {
      container.innerHTML =
        '<div class="flex h-full w-full items-center justify-center bg-chassis p-6 text-center font-mono text-xs uppercase tracking-silk text-silk-dim">3D WEBGL CONTEXT UNAVAILABLE</div>';
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

    // Calibrated inclined Clone Hero highway perspective for compact & focus viewports
    const camera = new THREE.PerspectiveCamera(46, width / height, 0.1, 45);
    camera.position.set(0, 3.85, 3.45);
    camera.lookAt(0, -0.15, -6.8);

    // Studio Hardware Lighting
    const ambientLight = new THREE.AmbientLight('#D5D9E2', 0.85);
    scene.add(ambientLight);

    const keyLight = new THREE.DirectionalLight('#FFFFFF', 1.35);
    keyLight.position.set(2.5, 9.0, 5.5);
    scene.add(keyLight);

    const rimLight = new THREE.DirectionalLight('#6A759B', 0.65);
    rimLight.position.set(-3.0, 5.0, -10.0);
    scene.add(rimLight);

    // Highway Deck & 5 Dark Recessed Channels ("5 canaletas escuras")
    const highwayGroup = new THREE.Group();
    const deckLength = 28;
    const deckCenterZ = -11.5;

    // Sub-chassis bed
    const bedGeo = new THREE.BoxGeometry(5.32, 0.08, deckLength);
    const bedMat = new THREE.MeshStandardMaterial({
      color: new THREE.Color('#14171E'),
      metalness: 0.6,
      roughness: 0.45,
    });
    const bedMesh = new THREE.Mesh(bedGeo, bedMat);
    bedMesh.position.set(0, -0.045, deckCenterZ);
    highwayGroup.add(bedMesh);

    // 5 dark recessed channels (lanes 0..4)
    const channelGeo = new THREE.PlaneGeometry(0.9, deckLength);
    channelGeo.rotateX(-Math.PI / 2);
    const channelMat = new THREE.MeshStandardMaterial({
      color: new THREE.Color('#0B0C10'),
      metalness: 0.25,
      roughness: 0.8,
    });

    const guideGeo = new THREE.PlaneGeometry(0.035, deckLength);
    guideGeo.rotateX(-Math.PI / 2);

    for (let i = 0; i < 5; i += 1) {
      const laneX = LANE_X_POSITIONS[i];
      const channelMesh = new THREE.Mesh(channelGeo, channelMat);
      channelMesh.position.set(laneX, 0.001, deckCenterZ);
      highwayGroup.add(channelMesh);

      // Subtle color-coded center trace inside each dark channel
      const guideMat = new THREE.MeshBasicMaterial({
        color: new THREE.Color(LANE_HEX_COLORS[i]),
        transparent: true,
        opacity: 0.14,
      });
      const guideMesh = new THREE.Mesh(guideGeo, guideMat);
      guideMesh.position.set(laneX, 0.003, deckCenterZ);
      highwayGroup.add(guideMesh);
    }

    // 6 Lane Divider Rails (-2.5, -1.5, -0.5, +0.5, +1.5, +2.5)
    const innerRailGeo = new THREE.BoxGeometry(0.04, 0.03, deckLength);
    const outerRailGeo = new THREE.BoxGeometry(0.11, 0.09, deckLength);
    const innerRailMat = new THREE.MeshStandardMaterial({
      color: new THREE.Color('#252934'),
      metalness: 0.7,
      roughness: 0.35,
    });
    const outerRailMat = new THREE.MeshStandardMaterial({
      color: new THREE.Color('#383E4E'),
      metalness: 0.8,
      roughness: 0.28,
    });

    const dividerXs = [-2.5, -1.5, -0.5, 0.5, 1.5, 2.5];
    for (const x of dividerXs) {
      const isOuter = Math.abs(x) > 2.4;
      const railMesh = new THREE.Mesh(
        isOuter ? outerRailGeo : innerRailGeo,
        isOuter ? outerRailMat : innerRailMat,
      );
      railMesh.position.set(x, isOuter ? 0.025 : 0.01, deckCenterZ);
      highwayGroup.add(railMesh);
    }

    scene.add(highwayGroup);

    // StrikeBar (z = 0) & NoteRenderer
    const strikeBar = new StrikeBar();
    scene.add(strikeBar.group);

    const noteRenderer = new NoteRenderer();
    scene.add(noteRenderer.group);

    // Resize Observer
    const resizeObserver = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) return;
      const nextW = Math.max(280, Math.floor(entry.contentRect.width));
      const nextH = Math.max(180, Math.floor(entry.contentRect.height));
      camera.aspect = nextW / nextH;
      camera.updateProjectionMatrix();
      renderer.setSize(nextW, nextH);
    });
    resizeObserver.observe(container);

    // Frame-accurate render loop synchronized with `getTimeRef.current()`
    let rafId = 0;
    let lastMaskKey = '';

    const animate = (): void => {
      rafId = requestAnimationFrame(animate);
      const nowSec = getTimeRef.current();
      const activeChart = chartRef.current;

      const hitState = noteRenderer.update(
        nowSec,
        activeChart.notes,
        activeChart.beatLines,
      );
      strikeBar.update(hitState.activeLanes, hitState.openHit);

      const maskKey = `${hitState.activeLanes.map((b) => (b ? '1' : '0')).join('')}-${hitState.openHit ? '1' : '0'}`;
      if (maskKey !== lastMaskKey) {
        lastMaskKey = maskKey;
        setHitLanes(hitState.activeLanes);
        setOpenHit(hitState.openHit);
      }

      renderer.render(scene, camera);
    };

    rafId = requestAnimationFrame(animate);

    return () => {
      cancelAnimationFrame(rafId);
      resizeObserver.disconnect();
      strikeBar.dispose();
      noteRenderer.dispose();
      bedGeo.dispose();
      bedMat.dispose();
      channelGeo.dispose();
      channelMat.dispose();
      guideGeo.dispose();
      innerRailGeo.dispose();
      outerRailGeo.dispose();
      innerRailMat.dispose();
      outerRailMat.dispose();
      renderer.dispose();
    };
  }, []);

  const tempoSnap = getInstantTempoAtTime(currentTime, chart);

  return (
    <div className={cn('flex flex-col border border-hw-border bg-module shadow-bevel', className)}>
      {/* Top Viewport Bezel: Active Track, Section, Receptor Telemetry & View Mode Toggle */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-hw-border bg-panel px-4 py-2">
        <div className="flex items-center gap-3">
          <span className="silk-wide tabular-nums">V-01 // 3D HIGHWAY DECK</span>
          <span className="h-3 w-px bg-hw-border" aria-hidden="true" />
          <span className="font-mono text-[11px] font-semibold uppercase tracking-silk text-silk">
            {chart.artist} — {chart.songName}
          </span>
          {isDemoChart ? (
            <span className="border border-hw-screw bg-chassis px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-silk text-starpower">
              STUDIO REF CHART
            </span>
          ) : (
            <span className="border border-fret-green/50 bg-[#0D1914] px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-silk text-fret-green">
              GENERATED .CHART
            </span>
          )}
        </div>

        {/* Live Strike Receptor LED Mirror & Compact/Focus Toggle */}
        <div className="flex flex-wrap items-center gap-3">
          <span className="silk-wide text-[9px]">SECTION: {tempoSnap.activeSection.toUpperCase()}</span>
          <span className="h-3 w-px bg-hw-border" aria-hidden="true" />
          <div className="flex items-center gap-2" aria-label="Active Strike Line Receptors">
            {FRET_LANES.map((lane, idx) => (
              <LedIndicator
                key={lane}
                color={lane}
                on={hitLanes[idx]}
                size="xs"
                label={String(idx)}
              />
            ))}
            <LedIndicator color="open" on={openHit} size="xs" label="OPEN" />
          </div>
          <span className="h-3 w-px bg-hw-border" aria-hidden="true" />
          <div className="hidden xl:flex items-center gap-1.5 border border-hw-border bg-chassis px-2 py-0.5 font-mono text-[9px] uppercase tracking-silk text-starpower">
            <span className="inline-block h-1.5 w-1.5 bg-starpower" aria-hidden="true" />
            <span>STUDIO FOCUS VIEW</span>
          </div>
          <div className="xl:hidden">
            <PushButton
              size="sm"
              label={viewMode === 'focus' ? 'Compact View' : 'Focus View'}
              sublabel={viewMode === 'focus' ? '220px' : '320px'}
              led="blue"
              ledOn={viewMode === 'focus'}
              latched={viewMode === 'focus'}
              onClick={() => setViewMode((m) => (m === 'compact' ? 'focus' : 'compact'))}
            />
          </div>
        </div>
      </div>

      {/* Three.js 3D Inclined Highway Canvas */}
      <div
        className={cn(
          'relative w-full overflow-hidden bg-[#090A0D] transition-[height] duration-150',
          viewMode === 'focus' ? 'h-[320px] sm:h-[340px]' : 'h-[220px] sm:h-[240px]',
          'xl:h-[340px]',
        )}
      >
        <div ref={mountRef} className="h-full w-full" />

        {/* Corner HUD Visual Spec Legend (Compact 8px) */}
        <div className="pointer-events-none absolute left-2.5 top-2 flex flex-col gap-0.5 border border-hw-border bg-chassis/85 px-2 py-1 font-mono text-[8px] uppercase tracking-silk text-silk-dim">
          <div className="text-silk">5-LANE INCLINED // 192 PPQ</div>
          <div>STRUM RING | HOPO DOME | SUSTAIN 24T</div>
        </div>

        <div className="pointer-events-none absolute right-2.5 top-2 flex items-center gap-1.5 border border-hw-border bg-chassis/85 px-2 py-1 font-mono text-[8px] tabular-nums uppercase tracking-silk text-silk">
          <span className="text-silk-dim">BAR</span>
          <span>{String(tempoSnap.measure).padStart(3, '0')}:{tempoSnap.beat}</span>
          <span className="text-hw-screw">|</span>
          <span className="text-silk-dim">TICK</span>
          <span>{String(tempoSnap.tick).padStart(6, '0')}</span>
        </div>

        {isDemoChart ? (
          <div className="pointer-events-none absolute inset-x-0 bottom-2.5 flex justify-center px-4">
            <div className="border border-fret-orange/80 bg-[#120F0A]/95 px-3 py-1 font-mono text-[9px] font-semibold uppercase tracking-silk text-fret-orange shadow-lg backdrop-blur-sm">
              DEMO MODE // CLICK "GENERATE CHART" TO PROCESS AND RENDER YOUR CUSTOM AUDIO
            </div>
          </div>
        ) : null}
      </div>

      {/* Lower Transport & Speed Deck */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-hw-border bg-panel px-4 py-2.5">
        <div className="flex items-center gap-2">
          <PushButton
            size="sm"
            variant="master"
            label={isPlaying ? 'Pause' : 'Play'}
            led={isPlaying ? 'green' : 'yellow'}
            ledOn
            latched={isPlaying}
            onClick={onTogglePlay}
          />
          <PushButton
            size="sm"
            variant="standard"
            label="Stop / Zero"
            led="red"
            ledOn={false}
            onClick={onStop}
          />
          <div className="ml-2 border border-hw-border bg-chassis px-2.5 py-1 font-mono text-[11px] tabular-nums tracking-silk text-silk shadow-recess">
            {currentTime.toFixed(2)}S <span className="text-silk-dim">/ {duration.toFixed(2)}S</span>
          </div>
        </div>

        {/* Speed Selector (0.5x, 0.75x, 1.0x) */}
        <div className="flex items-center gap-2">
          <span className="silk">Speed</span>
          <div className="flex items-center gap-1" role="radiogroup" aria-label="Playback Speed">
            {SPEED_OPTIONS.map((spd) => (
              <PushButton
                key={spd}
                size="sm"
                label={`${spd.toFixed(2).replace(/\.00$/, '.0')}X`}
                led="orange"
                ledOn={playbackRate === spd}
                latched={playbackRate === spd}
                role="radio"
                aria-checked={playbackRate === spd}
                onClick={() => onChangeSpeed(spd)}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
