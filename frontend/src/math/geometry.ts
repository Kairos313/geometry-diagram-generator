/**
 * Pure math utilities — no DOM dependencies.
 * Ported from matplotlib_helpers.py battle-tested logic.
 */

import type { Vec2, Vec3 } from '../schema/render-types';

export function distance2(a: Vec2, b: Vec2): number {
  return Math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2);
}

export function distance3(a: Vec3, b: Vec3): number {
  return Math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2);
}

export function midpoint2(a: Vec2, b: Vec2): Vec2 {
  return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
}

export function midpoint3(a: Vec3, b: Vec3): Vec3 {
  return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2, z: (a.z + b.z) / 2 };
}

export function normalize2(v: Vec2): Vec2 {
  const len = Math.sqrt(v.x * v.x + v.y * v.y);
  if (len < 1e-9) return { x: 0, y: 0 };
  return { x: v.x / len, y: v.y / len };
}

export function sub2(a: Vec2, b: Vec2): Vec2 {
  return { x: a.x - b.x, y: a.y - b.y };
}

export function add2(a: Vec2, b: Vec2): Vec2 {
  return { x: a.x + b.x, y: a.y + b.y };
}

export function scale2(v: Vec2, s: number): Vec2 {
  return { x: v.x * s, y: v.y * s };
}

/**
 * Compute the angle (in degrees) of the ray from origin to point,
 * measured CCW from the positive X axis. Range: (-180, 180].
 */
export function angleDeg(v: Vec2): number {
  return Math.atan2(v.y, v.x) * (180 / Math.PI);
}

/**
 * Compute angle arc sweep parameters between two rays from a vertex.
 *
 * Handles the line-vs-ray ambiguity: in geometry problems, a point like T
 * on a tangent defines a LINE through vertex, not just a ray. The 35° angle
 * between tangent TA and chord AB is measured from the tangent's OTHER
 * direction (away from T), not from vertex→T directly.
 *
 * When expectedDegrees is given, this function tries all four ray-direction
 * combinations (original and flipped-180° for each ray) to find the sweep
 * that best matches the expected value.
 *
 * Returns { startAngle, endAngle } in degrees for a CCW arc in math-space.
 * svgArcPath expects these math-convention angles and handles Y-flip internally.
 */
export function computeAngleSweep(
  vertex: Vec2,
  p1: Vec2,
  p2: Vec2,
  expectedDegrees?: number,
): { startAngle: number; endAngle: number } {
  // Negate Y to convert from SVG-space (Y-down) to math-space (Y-up).
  const v1 = { x: p1.x - vertex.x, y: -(p1.y - vertex.y) };
  const v2 = { x: p2.x - vertex.x, y: -(p2.y - vertex.y) };

  if (Math.sqrt(v1.x * v1.x + v1.y * v1.y) < 1e-9 ||
      Math.sqrt(v2.x * v2.x + v2.y * v2.y) < 1e-9) {
    return { startAngle: 0, endAngle: 0 };
  }

  const a1 = angleDeg(v1);
  const a2 = angleDeg(v2);

  if (expectedDegrees !== undefined) {
    // Try all combinations of ray directions (original + flipped 180°).
    // This handles cases where a point defines a LINE (tangent, extended side)
    // rather than just a ray — the expected angle may be between the
    // opposite direction of one ray and the other ray.
    const candidates: { start: number; sweep: number }[] = [];

    for (const sa of [a1, a1 + 180]) {
      for (const ea of [a2, a2 + 180]) {
        const sweep = ((ea - sa) % 360 + 360) % 360 || 360;
        candidates.push({ start: sa, sweep });
        // Also try the reverse direction (CW = the other CCW sweep)
        const revSweep = 360 - sweep;
        if (revSweep > 0 && revSweep < 360) {
          candidates.push({ start: ea, sweep: revSweep });
        }
      }
    }

    // Pick the candidate whose sweep is closest to expectedDegrees
    let best = candidates[0];
    let bestDiff = Math.abs(candidates[0].sweep - expectedDegrees);

    for (const c of candidates) {
      const diff = Math.abs(c.sweep - expectedDegrees);
      if (diff < bestDiff) {
        bestDiff = diff;
        best = c;
      }
    }

    return { startAngle: best.start, endAngle: best.start + best.sweep };
  } else {
    // No expected angle — draw the smaller (interior) angle
    const sweep12 = ((a2 - a1) % 360 + 360) % 360;
    const sweep21 = ((a1 - a2) % 360 + 360) % 360;

    if (sweep12 <= 180) {
      return { startAngle: a1, endAngle: a1 + sweep12 };
    } else {
      return { startAngle: a2, endAngle: a2 + sweep21 };
    }
  }
}

/**
 * Generate SVG arc path string.
 * This is the #1 source of bugs in raw SVG — correct large-arc-flag and sweep-flag.
 *
 * startDeg/endDeg are in mathematical convention (CCW from +X).
 * SVG Y is flipped (down = positive), so we negate Y in the path.
 */
export function svgArcPath(
  cx: number,
  cy: number,
  r: number,
  startDeg: number,
  endDeg: number,
): string {
  const startRad = startDeg * (Math.PI / 180);
  const endRad = endDeg * (Math.PI / 180);

  // In SVG coordinate space (Y-down), we negate the Y component
  const x1 = cx + r * Math.cos(startRad);
  const y1 = cy - r * Math.sin(startRad);
  const x2 = cx + r * Math.cos(endRad);
  const y2 = cy - r * Math.sin(endRad);

  // Sweep angle in degrees
  let sweep = ((endDeg - startDeg) % 360 + 360) % 360;
  if (sweep === 0) sweep = 360;

  const largeArcFlag = sweep > 180 ? 1 : 0;
  // SVG sweep-flag: 0 = CW in SVG space. Since we negated Y,
  // a CCW math arc becomes CW in SVG. So sweep-flag = 0.
  const sweepFlag = 0;

  return `M ${x1} ${y1} A ${r} ${r} 0 ${largeArcFlag} ${sweepFlag} ${x2} ${y2}`;
}

/**
 * Compute the three corners of a right-angle square marker.
 * Ported from matplotlib_helpers.py draw_right_angle_marker (lines 126-146).
 *
 * Returns [corner1, corner2, corner3] — draw as a polyline.
 */
export function rightAngleCorners(
  vertex: Vec2,
  p1: Vec2,
  p2: Vec2,
  size: number,
): [Vec2, Vec2, Vec2] {
  const v1 = sub2(p1, vertex);
  const v2 = sub2(p2, vertex);

  const d1 = scale2(normalize2(v1), size);
  const d2 = scale2(normalize2(v2), size);

  const corner1 = add2(vertex, d1);
  const corner2 = add2(add2(vertex, d1), d2);
  const corner3 = add2(vertex, d2);

  return [corner1, corner2, corner3];
}

/**
 * Push a label position away from the figure centroid.
 */
export function labelOffset(
  point: Vec2,
  centroid: Vec2,
  dist: number = 18,
): Vec2 {
  const dir = sub2(point, centroid);
  const len = Math.sqrt(dir.x * dir.x + dir.y * dir.y);
  if (len < 1e-9) {
    return { x: point.x, y: point.y - dist };
  }
  return {
    x: point.x + (dir.x / len) * dist,
    y: point.y + (dir.y / len) * dist,
  };
}

/**
 * Compute centroid of a set of 2D points.
 */
export function centroid2(points: Vec2[]): Vec2 {
  if (points.length === 0) return { x: 0, y: 0 };
  let sx = 0, sy = 0;
  for (const p of points) {
    sx += p.x;
    sy += p.y;
  }
  return { x: sx / points.length, y: sy / points.length };
}

/**
 * Compute centroid of a set of 3D points.
 */
export function centroid3(points: Vec3[]): Vec3 {
  if (points.length === 0) return { x: 0, y: 0, z: 0 };
  let sx = 0, sy = 0, sz = 0;
  for (const p of points) {
    sx += p.x;
    sy += p.y;
    sz += p.z;
  }
  return { x: sx / points.length, y: sy / points.length, z: sz / points.length };
}

/**
 * Simple expression evaluator for equations like "y = x^2 - 4*x + 3".
 * Samples the equation over a range and returns [x, y] points.
 */
export function sampleEquation(
  equation: string,
  xMin: number,
  xMax: number,
  numSamples: number = 100,
): Vec2[] {
  // Extract the RHS of "y = ..."
  const match = equation.match(/y\s*=\s*(.+)/i);
  if (!match) return [];

  let expr = match[1].trim();
  // Convert ^ to ** for JS eval
  expr = expr.replace(/\^/g, '**');
  // Convert implicit multiplication: 4x -> 4*x
  expr = expr.replace(/(\d)([x])/gi, '$1*$2');

  const points: Vec2[] = [];
  const step = (xMax - xMin) / numSamples;

  for (let i = 0; i <= numSamples; i++) {
    const x = xMin + i * step;
    try {
      // Create a function that evaluates the expression with x
      const fn = new Function('x', 'Math', `return ${expr};`);
      const y = fn(x, Math) as number;
      if (isFinite(y)) {
        points.push({ x, y });
      }
    } catch {
      // Skip invalid evaluations
    }
  }

  return points;
}

// ── Angle arc validation ──

export interface AngleValidationResult {
  id: string;
  valid: boolean;
  expectedSweep?: number;
  actualSweep: number;
  sweepError: number;
  arcMidpoint: Vec2;
  /** Whether the arc midpoint lies inside the polygon formed by nearby edges */
  arcInsideShape: boolean;
  issues: string[];
}

/**
 * Validate that an angle arc is drawn correctly:
 * 1. The arc sweep matches the expected angle value (within tolerance)
 * 2. The arc midpoint lies on the correct side (inside the figure)
 *
 * Call this after computing arc parameters to catch misplaced arcs.
 */
export function validateAngleArc(
  id: string,
  vertex: Vec2,
  p1: Vec2,
  p2: Vec2,
  startAngle: number,
  endAngle: number,
  expectedDegrees: number | undefined,
  allPoints: Vec2[],
  arcRadius: number,
): AngleValidationResult {
  const issues: string[] = [];
  const sweep = ((endAngle - startAngle) % 360 + 360) % 360;

  // Check 1: sweep matches expected value
  let sweepError = 0;
  if (expectedDegrees !== undefined) {
    sweepError = Math.abs(sweep - expectedDegrees);
    if (sweepError > 5) {
      issues.push(
        `Sweep ${sweep.toFixed(1)}° doesn't match expected ${expectedDegrees}° (error: ${sweepError.toFixed(1)}°)`
      );
    }
  }

  // Compute arc midpoint (for checking if it's inside the figure)
  const midAngleRad = ((startAngle + endAngle) / 2) * (Math.PI / 180);
  const arcMidpoint: Vec2 = {
    x: vertex.x + arcRadius * Math.cos(midAngleRad),
    y: vertex.y - arcRadius * Math.sin(midAngleRad), // SVG Y-flip
  };

  // Check 2: arc midpoint should be roughly inside the convex hull of
  // nearby points (simple heuristic: closer to centroid than the vertex is)
  const centroid = centroid2(allPoints);
  const vertexDistToCentroid = distance2(vertex, centroid);
  const arcMidDistToCentroid = distance2(arcMidpoint, centroid);
  const arcInsideShape = arcMidDistToCentroid < vertexDistToCentroid * 1.3;

  if (!arcInsideShape && allPoints.length > 2) {
    issues.push(
      `Arc midpoint appears to be outside the figure (dist to centroid: ${arcMidDistToCentroid.toFixed(0)} vs vertex: ${vertexDistToCentroid.toFixed(0)})`
    );
  }

  return {
    id,
    valid: issues.length === 0,
    expectedSweep: expectedDegrees,
    actualSweep: sweep,
    sweepError,
    arcMidpoint,
    arcInsideShape,
    issues,
  };
}
