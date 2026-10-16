import * as THREE from 'three';
import type { ParsedBeatLine, ParsedChartNote, PlayableFret } from '../../hooks/useChartParser';
import { LED_COLORS } from '../../theme/tokens';
import { LANE_HEX_COLORS, LANE_X_POSITIONS } from './StrikeBar';

export const HIGHWAY_SPEED_UNITS_PER_SEC = 11.5;
export const HIGHWAY_HORIZON_Z = -24.5;
export const HIGHWAY_PAST_Z = 2.0;

interface GemPoolItem {
  group: THREE.Group;
  bodyMat: THREE.MeshStandardMaterial;
  strumRingMesh: THREE.Mesh;
  strumCapMesh: THREE.Mesh;
  hopoDomeMesh: THREE.Mesh;
  spHaloMesh: THREE.Mesh;
}

interface OpenBarPoolItem {
  group: THREE.Group;
  bodyMat: THREE.MeshStandardMaterial;
}

interface SustainPoolItem {
  mesh: THREE.Mesh;
  mat: THREE.MeshBasicMaterial;
}

interface BeatLinePoolItem {
  mesh: THREE.Mesh;
  mat: THREE.MeshBasicMaterial;
}

export interface FrameHitState {
  activeLanes: [boolean, boolean, boolean, boolean, boolean];
  openHit: boolean;
}

const FRET_COLOR_LOOKUP: Record<PlayableFret, THREE.Color> = {
  0: new THREE.Color(LANE_HEX_COLORS[0]),
  1: new THREE.Color(LANE_HEX_COLORS[1]),
  2: new THREE.Color(LANE_HEX_COLORS[2]),
  3: new THREE.Color(LANE_HEX_COLORS[3]),
  4: new THREE.Color(LANE_HEX_COLORS[4]),
  7: new THREE.Color(LED_COLORS.open),
};

const STARPOWER_COLOR = new THREE.Color(LED_COLORS.starpower);

/**
 * High-performance pooled Three.js renderer for Clone Hero highway elements:
 *  - 5-color Fret Gems (Strum notes with outer strum ring vs HOPOs without strum ring)
 *  - Open Note horizontal purple bars spanning all 5 lanes
 *  - Translucent sustain tails with 24-tick release margin and strike-line burn-down
 *  - Synchronized [SyncTrack] beat and measure grid lines
 */
export class NoteRenderer {
  public readonly group: THREE.Group;

  private readonly gemPool: GemPoolItem[] = [];
  private readonly openPool: OpenBarPoolItem[] = [];
  private readonly sustainPool: SustainPoolItem[] = [];
  private readonly beatPool: BeatLinePoolItem[] = [];

  private readonly sharedGeometries: THREE.BufferGeometry[] = [];
  private readonly sharedMaterials: THREE.Material[] = [];

  public constructor(
    maxGems = 96,
    maxOpenBars = 24,
    maxSustains = 64,
    maxBeatLines = 48,
  ) {
    this.group = new THREE.Group();

    // Shared geometries
    const gemBodyGeo = new THREE.CylinderGeometry(0.28, 0.34, 0.14, 16);
    const strumRingGeo = new THREE.TorusGeometry(0.34, 0.042, 10, 24);
    strumRingGeo.rotateX(Math.PI / 2);

    const strumCapGeo = new THREE.CylinderGeometry(0.16, 0.18, 0.05, 16);
    const hopoDomeGeo = new THREE.CylinderGeometry(0.11, 0.24, 0.09, 16);
    const spHaloGeo = new THREE.RingGeometry(0.36, 0.43, 20);
    spHaloGeo.rotateX(-Math.PI / 2);

    const openBodyGeo = new THREE.BoxGeometry(4.68, 0.12, 0.24);
    const openTrimGeo = new THREE.BoxGeometry(4.72, 0.14, 0.05);

    const sustainGeo = new THREE.BoxGeometry(1, 0.045, 1);
    const beatLineGeo = new THREE.BoxGeometry(4.92, 0.01, 0.045);

    this.sharedGeometries.push(
      gemBodyGeo,
      strumRingGeo,
      strumCapGeo,
      hopoDomeGeo,
      spHaloGeo,
      openBodyGeo,
      openTrimGeo,
      sustainGeo,
      beatLineGeo,
    );

    // Shared accent materials
    const strumRingMat = new THREE.MeshStandardMaterial({
      color: new THREE.Color('#F2F4F8'),
      emissive: new THREE.Color('#D5D9E2'),
      emissiveIntensity: 0.35,
      metalness: 0.5,
      roughness: 0.25,
    });

    const strumCapMat = new THREE.MeshStandardMaterial({
      color: new THREE.Color('#14161B'),
      metalness: 0.7,
      roughness: 0.35,
    });

    const hopoDomeMat = new THREE.MeshBasicMaterial({
      color: new THREE.Color('#FFFFFF'),
    });

    const spHaloMat = new THREE.MeshBasicMaterial({
      color: STARPOWER_COLOR,
      transparent: true,
      opacity: 0.75,
    });

    const openTrimMat = new THREE.MeshBasicMaterial({
      color: new THREE.Color('#E0AAFF'),
    });

    this.sharedMaterials.push(strumRingMat, strumCapMat, hopoDomeMat, spHaloMat, openTrimMat);

    // 1. Pre-allocate Beat Lines
    for (let i = 0; i < maxBeatLines; i += 1) {
      const mat = new THREE.MeshBasicMaterial({
        color: new THREE.Color('#2A2E39'),
        transparent: true,
        opacity: 0.65,
      });
      const mesh = new THREE.Mesh(beatLineGeo, mat);
      mesh.visible = false;
      this.group.add(mesh);
      this.beatPool.push({ mesh, mat });
    }

    // 2. Pre-allocate Translucent Sustain Tails
    for (let i = 0; i < maxSustains; i += 1) {
      const mat = new THREE.MeshBasicMaterial({
        color: new THREE.Color(LED_COLORS.green),
        transparent: true,
        opacity: 0.68,
      });
      const mesh = new THREE.Mesh(sustainGeo, mat);
      mesh.visible = false;
      this.group.add(mesh);
      this.sustainPool.push({ mesh, mat });
    }

    // 3. Pre-allocate 5-Fret Gem Pool
    for (let i = 0; i < maxGems; i += 1) {
      const gemGroup = new THREE.Group();
      gemGroup.visible = false;

      const bodyMat = new THREE.MeshStandardMaterial({
        color: new THREE.Color(LED_COLORS.green),
        emissive: new THREE.Color(LED_COLORS.green),
        emissiveIntensity: 0.55,
        metalness: 0.25,
        roughness: 0.25,
      });

      const bodyMesh = new THREE.Mesh(gemBodyGeo, bodyMat);
      bodyMesh.position.y = 0.08;
      gemGroup.add(bodyMesh);

      // Outer strum ring — strictly shown ONLY on strum notes, hidden on HOPOs
      const strumRingMesh = new THREE.Mesh(strumRingGeo, strumRingMat);
      strumRingMesh.position.y = 0.05;
      gemGroup.add(strumRingMesh);

      const strumCapMesh = new THREE.Mesh(strumCapGeo, strumCapMat);
      strumCapMesh.position.y = 0.145;
      gemGroup.add(strumCapMesh);

      // Luminous bevel dome — shown ONLY on HOPO notes (without strum ring)
      const hopoDomeMesh = new THREE.Mesh(hopoDomeGeo, hopoDomeMat);
      hopoDomeMesh.position.y = 0.165;
      gemGroup.add(hopoDomeMesh);

      // Star Power cyan base aura
      const spHaloMesh = new THREE.Mesh(spHaloGeo, spHaloMat);
      spHaloMesh.position.y = 0.025;
      gemGroup.add(spHaloMesh);

      this.group.add(gemGroup);
      this.gemPool.push({
        group: gemGroup,
        bodyMat,
        strumRingMesh,
        strumCapMesh,
        hopoDomeMesh,
        spHaloMesh,
      });
    }

    // 4. Pre-allocate Open Note Horizontal Purple Bars
    for (let i = 0; i < maxOpenBars; i += 1) {
      const openGroup = new THREE.Group();
      openGroup.visible = false;

      const bodyMat = new THREE.MeshStandardMaterial({
        color: new THREE.Color(LED_COLORS.open),
        emissive: new THREE.Color(LED_COLORS.open),
        emissiveIntensity: 0.75,
        metalness: 0.3,
        roughness: 0.2,
      });

      const bodyMesh = new THREE.Mesh(openBodyGeo, bodyMat);
      bodyMesh.position.y = 0.075;
      openGroup.add(bodyMesh);

      const topTrim = new THREE.Mesh(openTrimGeo, openTrimMat);
      topTrim.position.set(0, 0.09, 0);
      openGroup.add(topTrim);

      this.group.add(openGroup);
      this.openPool.push({
        group: openGroup,
        bodyMat,
      });
    }
  }

  /**
   * Synchronize all visible 3D notes, sustains, and beat lines with `currentTime`.
   */
  public update(
    currentTime: number,
    notes: readonly ParsedChartNote[],
    beatLines: readonly ParsedBeatLine[],
    speed = HIGHWAY_SPEED_UNITS_PER_SEC,
  ): FrameHitState {
    const activeLanes: [boolean, boolean, boolean, boolean, boolean] = [
      false,
      false,
      false,
      false,
      false,
    ];
    let openHit = false;

    const lookaheadSec = Math.abs(HIGHWAY_HORIZON_Z) / speed;
    const lookbehindSec = HIGHWAY_PAST_Z / speed;
    const minVisibleTime = currentTime - lookbehindSec;
    const maxVisibleTime = currentTime + lookaheadSec;

    // 1. Update Beat & Measure Grid Lines
    let beatIdx = 0;
    for (let i = 0; i < beatLines.length; i += 1) {
      const b = beatLines[i];
      if (b.timeSeconds < minVisibleTime) continue;
      if (b.timeSeconds > maxVisibleTime) break;
      if (beatIdx >= this.beatPool.length) break;

      const z = -(b.timeSeconds - currentTime) * speed;
      const slot = this.beatPool[beatIdx];
      beatIdx += 1;

      slot.mesh.visible = true;
      slot.mesh.position.set(0, 0.008, z);
      slot.mesh.scale.set(1, 1, b.isMeasure ? 1.7 : 0.85);
      slot.mat.color.set(b.isMeasure ? '#454C5E' : '#232731');
      slot.mat.opacity = b.isMeasure ? 0.85 : 0.5;
    }
    for (let i = beatIdx; i < this.beatPool.length; i += 1) {
      this.beatPool[i].mesh.visible = false;
    }

    // 2. Update Notes, HOPOs, Open Bars, and Translucent Sustain Tails
    let gemIdx = 0;
    let openIdx = 0;
    let susIdx = 0;
    const hitWindowSec = 0.055;

    for (let i = 0; i < notes.length; i += 1) {
      const note = notes[i];

      // Check if note or its sustain is still within the visible window
      if (note.sustainEndTimeSeconds < minVisibleTime && note.timeSeconds < minVisibleTime) {
        continue;
      }
      if (note.timeSeconds > maxVisibleTime) {
        break;
      }

      // Check active strike receptor illumination
      const isStrikingHead = Math.abs(note.timeSeconds - currentTime) <= hitWindowSec;
      const isHoldingSustain =
        note.sustainTicks > 0 &&
        currentTime >= note.timeSeconds &&
        currentTime <= note.sustainEndTimeSeconds;

      if (isStrikingHead || isHoldingSustain) {
        if (note.isOpen || note.fret === 7) {
          openHit = true;
        } else {
          activeLanes[note.fret] = true;
        }
      }

      const fretColor = FRET_COLOR_LOOKUP[note.fret];

      // Render translucent sustain tail if note has sustain
      if (note.sustainDurationSeconds > 0.02 && susIdx < this.sustainPool.length) {
        // Clamp head to strike line (z = 0) while actively held
        const headTime =
          currentTime > note.timeSeconds && currentTime < note.sustainEndTimeSeconds
            ? currentTime
            : note.timeSeconds;
        const tailTime = Math.min(maxVisibleTime, note.sustainEndTimeSeconds);

        if (tailTime > headTime) {
          const headZ = -(headTime - currentTime) * speed;
          const tailZ = -(tailTime - currentTime) * speed;
          const lengthZ = Math.max(0.08, Math.abs(headZ - tailZ));
          const centerZ = (headZ + tailZ) / 2;

          const susSlot = this.sustainPool[susIdx];
          susIdx += 1;

          susSlot.mesh.visible = true;
          const laneX = note.isOpen ? 0 : LANE_X_POSITIONS[note.fret as 0 | 1 | 2 | 3 | 4];
          const widthX = note.isOpen ? 3.8 : 0.24;

          susSlot.mesh.position.set(laneX, 0.032, centerZ);
          susSlot.mesh.scale.set(widthX, 1, lengthZ);
          susSlot.mat.color.copy(fretColor);
          susSlot.mat.opacity = isHoldingSustain ? 0.86 : 0.62;
        }
      }

      // Hide note head once it has passed the strike line while its sustain burns down
      if (isHoldingSustain && currentTime - note.timeSeconds > 0.03) {
        continue;
      }

      const noteZ = -(note.timeSeconds - currentTime) * speed;
      if (noteZ > HIGHWAY_PAST_Z || noteZ < HIGHWAY_HORIZON_Z) {
        continue;
      }

      if (note.isOpen) {
        if (openIdx < this.openPool.length) {
          const openSlot = this.openPool[openIdx];
          openIdx += 1;
          openSlot.group.visible = true;
          openSlot.group.position.set(0, 0, noteZ);
          openSlot.bodyMat.emissiveIntensity = isStrikingHead ? 1.4 : 0.75;
        }
      } else if (gemIdx < this.gemPool.length) {
        const gemSlot = this.gemPool[gemIdx];
        gemIdx += 1;
        const laneX = LANE_X_POSITIONS[note.fret as 0 | 1 | 2 | 3 | 4];

        gemSlot.group.visible = true;
        gemSlot.group.position.set(laneX, 0, noteZ);
        gemSlot.bodyMat.color.copy(fretColor);
        gemSlot.bodyMat.emissive.copy(fretColor);
        gemSlot.bodyMat.emissiveIntensity = isStrikingHead
          ? 1.5
          : note.isHopo
            ? 0.85
            : 0.55;

        // HOPO notes have NO outer strum ring and use the bright bevel dome cap
        gemSlot.strumRingMesh.visible = !note.isHopo;
        gemSlot.strumCapMesh.visible = !note.isHopo;
        gemSlot.hopoDomeMesh.visible = note.isHopo;
        gemSlot.spHaloMesh.visible = note.inStarPower;

        const scale = note.isHopo ? 0.92 : 1.0;
        gemSlot.group.scale.set(scale, 1, scale);
      }
    }

    for (let i = gemIdx; i < this.gemPool.length; i += 1) {
      this.gemPool[i].group.visible = false;
    }
    for (let i = openIdx; i < this.openPool.length; i += 1) {
      this.openPool[i].group.visible = false;
    }
    for (let i = susIdx; i < this.sustainPool.length; i += 1) {
      this.sustainPool[i].mesh.visible = false;
    }

    return { activeLanes, openHit };
  }

  public dispose(): void {
    for (const g of this.sharedGeometries) g.dispose();
    for (const m of this.sharedMaterials) m.dispose();
    for (const item of this.gemPool) item.bodyMat.dispose();
    for (const item of this.openPool) item.bodyMat.dispose();
    for (const item of this.sustainPool) item.mat.dispose();
    for (const item of this.beatPool) item.mat.dispose();
  }
}
