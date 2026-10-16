import * as THREE from 'three';
import { LED_COLORS } from '../../theme/tokens';

export const LANE_X_POSITIONS = [-2.0, -1.0, 0.0, 1.0, 2.0] as const;

export const LANE_HEX_COLORS = [
  LED_COLORS.green,
  LED_COLORS.red,
  LED_COLORS.yellow,
  LED_COLORS.blue,
  LED_COLORS.orange,
] as const;

interface ReceptorParts {
  group: THREE.Group;
  colorRingMat: THREE.MeshStandardMaterial;
  coreMat: THREE.MeshBasicMaterial;
  coreMesh: THREE.Mesh;
  baseColor: THREE.Color;
}

/**
 * Three.js Strike Bar situated at z = 0 on the inclined 5-lane highway.
 * Houses 5 mechanical fret receptors (Green -> Orange) and a full-width
 * purple Open-Note strike bar that illuminates on note impacts and active sustains.
 */
export class StrikeBar {
  public readonly group: THREE.Group;
  private readonly receptors: ReceptorParts[] = [];
  private readonly openBarMat: THREE.MeshBasicMaterial;
  private readonly openBarMesh: THREE.Mesh;

  public constructor() {
    this.group = new THREE.Group();
    this.group.position.set(0, 0.02, 0);

    // 1. Machined anodized crossbar plate spanning all 5 lanes
    const barGeo = new THREE.BoxGeometry(5.3, 0.05, 0.36);
    const barMat = new THREE.MeshStandardMaterial({
      color: new THREE.Color('#181B22'),
      metalness: 0.75,
      roughness: 0.35,
    });
    const barMesh = new THREE.Mesh(barGeo, barMat);
    barMesh.position.set(0, 0, 0);
    this.group.add(barMesh);

    // Front and rear steel trim rails on the strike line
    const railGeo = new THREE.BoxGeometry(5.32, 0.065, 0.035);
    const railMat = new THREE.MeshStandardMaterial({
      color: new THREE.Color('#434958'),
      metalness: 0.85,
      roughness: 0.25,
    });
    const frontRail = new THREE.Mesh(railGeo, railMat);
    frontRail.position.set(0, 0.01, 0.17);
    const rearRail = new THREE.Mesh(railGeo, railMat);
    rearRail.position.set(0, 0.01, -0.17);
    this.group.add(frontRail, rearRail);

    // 2. Open Note purple strike flash bar across all 5 lanes
    const openGeo = new THREE.BoxGeometry(4.78, 0.09, 0.22);
    this.openBarMat = new THREE.MeshBasicMaterial({
      color: new THREE.Color(LED_COLORS.open),
      transparent: true,
      opacity: 0.0,
    });
    this.openBarMesh = new THREE.Mesh(openGeo, this.openBarMat);
    this.openBarMesh.position.set(0, 0.04, 0);
    this.group.add(this.openBarMesh);

    // 3. Five Fret Receptors (Green, Red, Yellow, Blue, Orange)
    const bezelGeo = new THREE.CylinderGeometry(0.41, 0.43, 0.07, 24);
    const bezelMat = new THREE.MeshStandardMaterial({
      color: new THREE.Color('#2A2E39'),
      metalness: 0.8,
      roughness: 0.3,
    });

    const ringGeo = new THREE.RingGeometry(0.24, 0.36, 24);
    ringGeo.rotateX(-Math.PI / 2);

    const coreGeo = new THREE.CylinderGeometry(0.21, 0.21, 0.08, 20);

    for (let i = 0; i < 5; i += 1) {
      const laneX = LANE_X_POSITIONS[i];
      const hex = LANE_HEX_COLORS[i];
      const baseColor = new THREE.Color(hex);

      const recGroup = new THREE.Group();
      recGroup.position.set(laneX, 0.02, 0);

      const bezelMesh = new THREE.Mesh(bezelGeo, bezelMat);
      recGroup.add(bezelMesh);

      const colorRingMat = new THREE.MeshStandardMaterial({
        color: baseColor,
        emissive: baseColor,
        emissiveIntensity: 0.45,
        metalness: 0.3,
        roughness: 0.3,
      });
      const ringMesh = new THREE.Mesh(ringGeo, colorRingMat);
      ringMesh.position.y = 0.04;
      recGroup.add(ringMesh);

      const coreMat = new THREE.MeshBasicMaterial({
        color: new THREE.Color('#0D0E11'),
      });
      const coreMesh = new THREE.Mesh(coreGeo, coreMat);
      coreMesh.position.y = 0.02;
      recGroup.add(coreMesh);

      this.group.add(recGroup);
      this.receptors.push({
        group: recGroup,
        colorRingMat,
        coreMat,
        coreMesh,
        baseColor,
      });
    }
  }

  /**
   * Update receptor illumination states for the current audio frame.
   *
   * @param activeLanes - Boolean tuple for lanes 0..4 indicating a note hit or sustain hold.
   * @param openHit - True when an Open Note (fret 7) is crossing the strike line.
   */
  public update(activeLanes: readonly boolean[], openHit: boolean): void {
    for (let i = 0; i < this.receptors.length; i += 1) {
      const rec = this.receptors[i];
      const lit = Boolean(activeLanes[i]);

      if (lit) {
        rec.colorRingMat.emissiveIntensity = 1.65;
        rec.coreMat.color.copy(rec.baseColor).lerp(new THREE.Color('#FFFFFF'), 0.45);
        rec.coreMesh.position.y = 0.065;
        rec.coreMesh.scale.set(1.08, 1.25, 1.08);
      } else {
        rec.colorRingMat.emissiveIntensity = 0.42;
        rec.coreMat.color.set('#0D0E11');
        rec.coreMesh.position.y = 0.02;
        rec.coreMesh.scale.set(1, 1, 1);
      }
    }

    if (openHit) {
      this.openBarMat.opacity = 0.9;
      this.openBarMesh.scale.set(1.01, 1.35, 1.15);
    } else {
      this.openBarMat.opacity = Math.max(0, this.openBarMat.opacity - 0.14);
      this.openBarMesh.scale.set(1, 1, 1);
    }
  }

  public dispose(): void {
    this.openBarMat.dispose();
    for (const rec of this.receptors) {
      rec.colorRingMat.dispose();
      rec.coreMat.dispose();
    }
  }
}
