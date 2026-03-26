/**
 * Coordinate projection: real-unit geometry coords → viewport pixels.
 */

import type { Vec2, Vec3 } from '../schema/render-types';

const VIEWPORT_W = 680;
const VIEWPORT_H = 500;
const MARGIN = 40;

const SAFE_X_MIN = MARGIN;
const SAFE_X_MAX = VIEWPORT_W - MARGIN;
const SAFE_Y_MIN = MARGIN;
const SAFE_Y_MAX = VIEWPORT_H - MARGIN;
const SAFE_W = SAFE_X_MAX - SAFE_X_MIN;
const SAFE_H = SAFE_Y_MAX - SAFE_Y_MIN;

export interface ProjectionResult2D {
  /** Maps point ID → viewport pixel position */
  points: Map<string, Vec2>;
  /** Scale factor: geometry units → pixels */
  scale: number;
  /** Centroid in viewport coords */
  centroid: Vec2;
  /** If axes mode, the origin in viewport coords */
  origin?: Vec2;
}

/**
 * Project blueprint points (real-unit coords) into a 680×500 SVG viewport.
 * - Centers the figure at (340, 250)
 * - Scales to fill ~65% of the safe area
 * - Flips Y axis (geometry Y-up → SVG Y-down)
 */
export function projectToViewport2D(
  points: Record<string, [number, number, number]>,
  axes?: boolean,
  coordinateRange?: { x_min: number; x_max: number; y_min: number; y_max: number },
): ProjectionResult2D {
  const ids = Object.keys(points);
  if (ids.length === 0) {
    return { points: new Map(), scale: 1, centroid: { x: VIEWPORT_W / 2, y: VIEWPORT_H / 2 } };
  }

  // Determine the bounding box
  let geoXMin: number, geoXMax: number, geoYMin: number, geoYMax: number;

  if (axes && coordinateRange) {
    // For coordinate geometry, use the explicit range
    geoXMin = coordinateRange.x_min;
    geoXMax = coordinateRange.x_max;
    geoYMin = coordinateRange.y_min;
    geoYMax = coordinateRange.y_max;
  } else {
    // For traditional geometry, compute from points
    const xs = ids.map(id => points[id][0]);
    const ys = ids.map(id => points[id][1]);
    geoXMin = Math.min(...xs);
    geoXMax = Math.max(...xs);
    geoYMin = Math.min(...ys);
    geoYMax = Math.max(...ys);

    // Add 10% padding
    const padX = Math.max((geoXMax - geoXMin) * 0.1, 0.5);
    const padY = Math.max((geoYMax - geoYMin) * 0.1, 0.5);
    geoXMin -= padX;
    geoXMax += padX;
    geoYMin -= padY;
    geoYMax += padY;
  }

  const geoW = geoXMax - geoXMin || 1;
  const geoH = geoYMax - geoYMin || 1;

  // Scale to fit the safe area (maintain aspect ratio)
  const fillFactor = axes ? 0.85 : 0.65;
  const scaleX = (SAFE_W * fillFactor) / geoW;
  const scaleY = (SAFE_H * fillFactor) / geoH;
  const scale = Math.min(scaleX, scaleY);

  // Center of the safe area
  const centerX = VIEWPORT_W / 2;
  const centerY = VIEWPORT_H / 2;

  // Center of the geometry bounding box
  const geoCenterX = (geoXMin + geoXMax) / 2;
  const geoCenterY = (geoYMin + geoYMax) / 2;

  const result = new Map<string, Vec2>();

  for (const id of ids) {
    const [gx, gy] = points[id];
    result.set(id, {
      x: centerX + (gx - geoCenterX) * scale,
      y: centerY - (gy - geoCenterY) * scale, // flip Y
    });
  }

  // Compute origin position for axes mode
  let origin: Vec2 | undefined;
  if (axes) {
    origin = {
      x: centerX + (0 - geoCenterX) * scale,
      y: centerY - (0 - geoCenterY) * scale,
    };
  }

  // Compute centroid
  let cx = 0, cy = 0;
  for (const p of result.values()) {
    cx += p.x;
    cy += p.y;
  }
  cx /= result.size;
  cy /= result.size;

  return { points: result, scale, centroid: { x: cx, y: cy }, origin };
}

/**
 * Project a single geometry coordinate to viewport (for circles, curves etc.).
 */
export function geoToViewport(
  gx: number, gy: number,
  geoCenterX: number, geoCenterY: number,
  scale: number,
  centerX: number = VIEWPORT_W / 2,
  centerY: number = VIEWPORT_H / 2,
): Vec2 {
  return {
    x: centerX + (gx - geoCenterX) * scale,
    y: centerY - (gy - geoCenterY) * scale,
  };
}

export interface Projection3DResult {
  points: Map<string, Vec3>;
  scale: number;
  maxRadius: number;
}

/**
 * Normalize 3D points: center at origin and scale for Three.js rendering.
 */
export function normalize3D(
  points: Record<string, [number, number, number]>,
): Projection3DResult {
  const ids = Object.keys(points);
  if (ids.length === 0) {
    return { points: new Map(), scale: 1, maxRadius: 0 };
  }

  // Compute centroid
  let cx = 0, cy = 0, cz = 0;
  for (const id of ids) {
    cx += points[id][0];
    cy += points[id][1];
    cz += points[id][2];
  }
  cx /= ids.length;
  cy /= ids.length;
  cz /= ids.length;

  // Center all points
  const centered = new Map<string, Vec3>();
  let maxRadius = 0;

  for (const id of ids) {
    const p: Vec3 = {
      x: points[id][0] - cx,
      y: points[id][2],       // Swap Y↔Z: blueprint Y/Z → Three.js Y (up)
      z: -(points[id][1] - cy), // Blueprint Y → Three.js -Z (into screen becomes towards viewer)
    };
    // Actually let's keep it simpler: blueprint coords are geometry coords
    // where Y is horizontal and Z is vertical (up). But blueprints vary.
    // The safest approach: keep X, swap Y→Z and Z→Y for Three.js
    centered.set(id, {
      x: points[id][0] - cx,
      y: points[id][2],        // blueprint Z (height) → Three.js Y (up)
      z: points[id][1] - cy,   // blueprint Y → Three.js Z
    });

    const r = Math.sqrt(
      (points[id][0] - cx) ** 2 +
      (points[id][1] - cy) ** 2 +
      (points[id][2]) ** 2
    );
    maxRadius = Math.max(maxRadius, r);
  }

  // Scale so the figure fits nicely (target radius ~5 units)
  const targetSize = 5;
  const scale = maxRadius > 0 ? targetSize / maxRadius : 1;

  const scaled = new Map<string, Vec3>();
  for (const [id, p] of centered) {
    scaled.set(id, {
      x: p.x * scale,
      y: p.y * scale,
      z: p.z * scale,
    });
  }

  return { points: scaled, scale, maxRadius: targetSize };
}

export { VIEWPORT_W, VIEWPORT_H, MARGIN };
