/**
 * Blueprint JSON → RenderScene converter.
 * This replaces Stage 3 (LLM code generation) with deterministic logic.
 */

import type { BlueprintJSON } from './blueprint-types';
import type {
  RenderScene, RenderScene2D, RenderScene3D,
  RenderSegment2D, RenderCircle2D, RenderArc2D, RenderRightAngle2D,
  RenderPolygon2D, RenderPoint2D, RenderAnnotation2D, RenderCurve2D,
  RenderAxes2D,
  RenderPoint3D, RenderEdge3D, RenderFace3D, RenderAngleArc3D,
  RenderCircle3D, RenderSphere3D,
  Vec2, Vec3,
} from './render-types';
import { projectToViewport2D, normalize3D, VIEWPORT_W, VIEWPORT_H } from '../math/projection';
import { computeAngleSweep, sampleEquation, centroid2, validateAngleArc } from '../math/geometry';

// ── Colors ──

const COLORS = {
  primary: '#5b4dc7',
  primaryFill: 'rgba(91, 77, 199, 0.08)',
  highlight: '#d85a30',
  construction: '#888780',
  angle: '#ba7517',
  text: '#2c2c2a',
  green: '#0f6e56',
};

const FACE_COLORS = [
  'rgba(91, 77, 199, 0.08)',
  'rgba(15, 110, 86, 0.08)',
  'rgba(186, 117, 23, 0.08)',
  'rgba(216, 90, 48, 0.08)',
];

const EDGE_COLORS_3D = ['#7b68ee', '#4ae0b0', '#ff6b4a', '#ba7517'];

// ── Label matching helper ──

/**
 * Resolve a given-label for a line/edge by trying multiple key formats.
 * Blueprints are inconsistent: the `given` dict may use "line_AD", "AD",
 * "DA", "line_DA", etc. for the same segment.
 */
function findGivenLabel(
  lineId: string,
  from: string,
  to: string,
  givenLabels: Map<string, string>,
): string | undefined {
  // 1. Exact match on line.id (e.g. "line_AD")
  if (givenLabels.has(lineId)) return givenLabels.get(lineId);
  // 2. Strip "line_" prefix (e.g. "AD")
  const stripped = lineId.replace(/^line_/, '');
  if (givenLabels.has(stripped)) return givenLabels.get(stripped);
  // 3. Reversed stripped name (e.g. "DA")
  const strippedRev = stripped.split('').reverse().join('');
  if (strippedRev !== stripped && givenLabels.has(strippedRev))
    return givenLabels.get(strippedRev);
  // 4. Point-name combinations (e.g. "AD", "DA")
  const fwd = from + to;
  const rev = to + from;
  if (fwd !== stripped && givenLabels.has(fwd)) return givenLabels.get(fwd);
  if (rev !== stripped && rev !== strippedRev && givenLabels.has(rev))
    return givenLabels.get(rev);
  // 5. With "line_" prefix on point-name combos (e.g. "line_AD", "line_DA")
  const fwdPrefixed = 'line_' + fwd;
  const revPrefixed = 'line_' + rev;
  if (fwdPrefixed !== lineId && givenLabels.has(fwdPrefixed))
    return givenLabels.get(fwdPrefixed);
  if (revPrefixed !== lineId && givenLabels.has(revPrefixed))
    return givenLabels.get(revPrefixed);
  return undefined;
}

// ── Main converter ──

export function convertBlueprint(blueprint: BlueprintJSON): RenderScene {
  if (blueprint.dimension === '3d') {
    return convert3D(blueprint);
  } else {
    return convert2D(blueprint);
  }
}

// ── 2D Conversion ──

function convert2D(bp: BlueprintJSON): RenderScene2D {
  const hasAxes = bp.axes === true;
  const proj = projectToViewport2D(bp.points, hasAxes, bp.coordinate_range);
  const askedSet = new Set(bp.asked ?? []);

  // Resolve a point ID to viewport coords
  const resolve = (id: string): Vec2 => {
    const p = proj.points.get(id);
    if (!p) throw new Error(`Unknown point ID: ${id}`);
    return p;
  };

  // Build given label map: element ID → label text
  const givenLabels = new Map<string, string>();
  if (bp.given) {
    for (const [key, val] of Object.entries(bp.given)) {
      if (typeof val === 'string') {
        givenLabels.set(key, val);
      }
    }
  }

  // ── Segments ──
  const segments: RenderSegment2D[] = (bp.lines ?? []).map(line => {
    const from = resolve(line.from);
    const to = resolve(line.to);
    const label = findGivenLabel(line.id, line.from, line.to, givenLabels);
    const isAsked = askedSet.has(line.id);
    const askedLabel = isAsked ? '?' : undefined;

    return {
      id: line.id,
      from,
      to,
      style: line.style ?? 'solid',
      label: label ?? askedLabel,
      highlight: isAsked,
    };
  });

  // ── Circles ──
  const circles: RenderCircle2D[] = (bp.circles ?? []).map(c => {
    const center = resolve(c.center);
    return {
      id: c.id,
      center,
      radius: c.radius * proj.scale,
    };
  });

  // ── Angles → Arcs + Right-angle markers ──
  const arcs: RenderArc2D[] = [];
  const rightAngles: RenderRightAngle2D[] = [];
  const ARC_RADIUS = 25; // pixels

  for (const angle of bp.angles ?? []) {
    const vertex = resolve(angle.vertex);
    const p1 = resolve(angle.p1);
    const p2 = resolve(angle.p2);

    // Check if it's a right angle
    if (angle.value !== undefined && Math.abs(angle.value - 90) < 0.5) {
      rightAngles.push({
        id: angle.id,
        vertex,
        p1,
        p2,
        size: 12,
      });
    } else {
      // Compute arc sweep — handles line-vs-ray ambiguity by trying
      // all four ray direction combinations when expectedDegrees is given
      const { startAngle, endAngle } = computeAngleSweep(vertex, p1, p2, angle.value);
      const isAsked = askedSet.has(angle.id);
      const givenLabel = givenLabels.get(angle.id);

      let label: string | undefined;
      if (isAsked) {
        label = '?';
      } else if (givenLabel) {
        label = givenLabel;
      } else if (angle.value !== undefined) {
        label = `${Math.round(angle.value)}°`;
      }

      // Validate the computed arc
      const allPts = Array.from(proj.points.values());
      const validation = validateAngleArc(
        angle.id, vertex, p1, p2,
        startAngle, endAngle,
        angle.value, allPts, ARC_RADIUS,
      );
      if (!validation.valid) {
        console.warn(`[angle-arc] ${angle.id}:`, validation.issues.join('; '));
      }

      arcs.push({
        id: angle.id,
        center: vertex,
        radius: ARC_RADIUS,
        startAngle,
        endAngle,
        label,
        highlight: isAsked,
      });
    }
  }

  // ── Polygons / Faces ──
  const polygons: RenderPolygon2D[] = (bp.faces ?? []).map((face, i) => ({
    id: face.id,
    vertices: face.points.map(resolve),
    fill: FACE_COLORS[i % FACE_COLORS.length],
  }));

  // ── Points ──
  const points: RenderPoint2D[] = Object.entries(bp.points).map(([id]) => {
    const pos = resolve(id);
    const isAsked = askedSet.has(id);
    return {
      id,
      pos,
      label: id,
      style: isAsked ? 'highlight' as const : 'vertex' as const,
    };
  });

  // ── Axes ──
  let axes: RenderAxes2D | undefined;
  if (hasAxes && bp.coordinate_range && proj.origin) {
    const cr = bp.coordinate_range;
    const ticks: { pos: Vec2; label: string }[] = [];

    // X-axis ticks (with intelligent decimation for large ranges)
    const xSpan = cr.x_max - cr.x_min;
    const xStep = xSpan > 100 ? 20 : xSpan > 50 ? 10 : xSpan > 20 ? 5 : xSpan > 10 ? 2 : 1;
    for (let x = Math.ceil(cr.x_min / xStep) * xStep; x <= Math.floor(cr.x_max); x += xStep) {
      if (x === 0) continue;
      const pos = projectPointToViewport(x, 0, bp, proj);
      ticks.push({ pos, label: String(x) });
    }
    // Y-axis ticks (with intelligent decimation for large ranges)
    const ySpan = cr.y_max - cr.y_min;
    const yStep = ySpan > 100 ? 20 : ySpan > 50 ? 10 : ySpan > 20 ? 5 : ySpan > 10 ? 2 : 1;
    for (let y = Math.ceil(cr.y_min / yStep) * yStep; y <= Math.floor(cr.y_max); y += yStep) {
      if (y === 0) continue;
      const pos = projectPointToViewport(0, y, bp, proj);
      ticks.push({ pos, label: String(y) });
    }

    axes = {
      xRange: [
        projectPointToViewport(cr.x_min, 0, bp, proj).x,
        projectPointToViewport(cr.x_max, 0, bp, proj).x,
      ],
      yRange: [
        projectPointToViewport(0, cr.y_max, bp, proj).y, // y_max maps to smaller SVG y
        projectPointToViewport(0, cr.y_min, bp, proj).y,
      ] as [number, number],
      origin: proj.origin,
      ticks,
    };
  }

  // ── Curves ──
  const curves: RenderCurve2D[] = [];
  if (bp.curves) {
    for (const curve of bp.curves) {
      const cr = bp.coordinate_range ?? { x_min: -10, x_max: 10, y_min: -10, y_max: 10 };
      let geoPoints: Vec2[];

      if (curve.points && curve.points.length > 0) {
        geoPoints = curve.points.map(p => ({ x: p[0], y: p[1] }));
      } else {
        geoPoints = sampleEquation(curve.equation, cr.x_min, cr.x_max, 200);
      }

      // Project to viewport
      const viewportPoints = geoPoints.map(p =>
        projectPointToViewport(p.x, p.y, bp, proj)
      );

      curves.push({ id: curve.id, points: viewportPoints });
    }
  }

  // ── Annotations ──
  const annotations: RenderAnnotation2D[] = [];

  return {
    type: '2d',
    viewport: { width: VIEWPORT_W, height: VIEWPORT_H },
    centroid: proj.centroid,
    elements: {
      polygons,
      circles,
      segments,
      arcs,
      rightAngles,
      points,
      annotations,
      axes,
      curves,
    },
  };
}

/** Helper: project a single geo coordinate using the projection info */
function projectPointToViewport(
  gx: number,
  gy: number,
  bp: BlueprintJSON,
  proj: { scale: number; centroid: Vec2; origin?: Vec2 },
): Vec2 {
  // Compute geo center from coordinate range or points
  const cr = bp.coordinate_range;
  let geoCenterX: number, geoCenterY: number;

  if (cr) {
    geoCenterX = (cr.x_min + cr.x_max) / 2;
    geoCenterY = (cr.y_min + cr.y_max) / 2;
  } else {
    const pts = Object.values(bp.points);
    const xs = pts.map(p => p[0]);
    const ys = pts.map(p => p[1]);
    geoCenterX = (Math.min(...xs) + Math.max(...xs)) / 2;
    geoCenterY = (Math.min(...ys) + Math.max(...ys)) / 2;
  }

  return {
    x: VIEWPORT_W / 2 + (gx - geoCenterX) * proj.scale,
    y: VIEWPORT_H / 2 - (gy - geoCenterY) * proj.scale,
  };
}

// ── 3D Conversion ──

function convert3D(bp: BlueprintJSON): RenderScene3D {
  const norm = normalize3D(bp.points);
  const askedSet = new Set(bp.asked ?? []);

  const resolve3 = (id: string): Vec3 => {
    const p = norm.points.get(id);
    if (!p) throw new Error(`Unknown point ID: ${id}`);
    return p;
  };

  // Build given label map
  const givenLabels = new Map<string, string>();
  if (bp.given) {
    for (const [key, val] of Object.entries(bp.given)) {
      if (typeof val === 'string') {
        givenLabels.set(key, val);
      }
    }
  }

  // ── Points ──
  const points: RenderPoint3D[] = Object.keys(bp.points).map((id, i) => {
    const pos = resolve3(id);
    const isAsked = askedSet.has(id);
    return {
      id,
      pos,
      label: id,
      style: isAsked ? 'highlight' as const : 'vertex' as const,
      color: isAsked ? COLORS.highlight : COLORS.primary,
      radius: 0.15,
    };
  });

  // ── Edges ──
  const edges: RenderEdge3D[] = (bp.lines ?? []).map((line, i) => {
    const from = resolve3(line.from);
    const to = resolve3(line.to);
    const isAsked = askedSet.has(line.id);
    const label = findGivenLabel(line.id, line.from, line.to, givenLabels);
    const askedLabel = isAsked ? '?' : undefined;

    return {
      id: line.id,
      from,
      to,
      style: line.style ?? 'solid',
      color: isAsked ? COLORS.highlight : COLORS.primary,
      label: label ?? askedLabel,
      highlight: isAsked,
    };
  });

  // ── Faces ──
  const faces: RenderFace3D[] = (bp.faces ?? []).map((face, i) => ({
    id: face.id,
    vertices: face.points.map(resolve3),
    color: EDGE_COLORS_3D[i % EDGE_COLORS_3D.length],
    opacity: 0.12,
  }));

  // ── Angle arcs ──
  const angleArcs: RenderAngleArc3D[] = (bp.angles ?? []).map(angle => {
    const isAsked = askedSet.has(angle.id);
    const givenLabel = givenLabels.get(angle.id);
    let label: string | undefined;
    if (isAsked) label = '?';
    else if (givenLabel) label = givenLabel;
    else if (angle.value !== undefined) label = `${Math.round(angle.value)}°`;

    return {
      id: angle.id,
      center: resolve3(angle.vertex),
      p1: resolve3(angle.p1),
      p2: resolve3(angle.p2),
      label,
      highlight: isAsked,
    };
  });

  // ── Circles (for cones, cylinders, etc.) ──
  const circles: RenderCircle3D[] = (bp.circles ?? []).map(c => {
    const center = resolve3(c.center);
    // Determine the plane normal from the center point's Z position
    // Blueprint circles typically lie in the XY plane at a given Z height
    // After our Y↔Z swap, the normal should be along Three.js Y axis
    const normal: Vec3 = { x: 0, y: 1, z: 0 };

    // Check if this is a horizontal circle (all points at same Z in blueprint)
    // by looking at the center's original blueprint coords
    const origCenter = bp.points[c.center];
    if (origCenter) {
      // Blueprint Z (height) maps to Three.js Y
      // Circle lies in the XZ plane at that Y height → normal is (0, 1, 0)
      // This is the common case for cones and cylinders
    }

    return {
      id: c.id,
      center,
      radius: c.radius * norm.scale,
      normal,
      color: COLORS.primary,
    };
  });

  // ── Spheres ──
  const spheres: RenderSphere3D[] = (bp.spheres ?? []).map(s => {
    const center = resolve3(s.center);
    return {
      id: s.id,
      center,
      radius: s.radius * norm.scale,
      color: COLORS.primary,
      opacity: 0.15,
    };
  });

  // ── Camera ──
  // Adjust camera distance for circles/spheres
  let maxExtent = norm.maxRadius;
  for (const c of circles) {
    const cr = Math.sqrt(c.center.x ** 2 + c.center.y ** 2 + c.center.z ** 2) + c.radius;
    maxExtent = Math.max(maxExtent, cr);
  }
  for (const s of spheres) {
    const sr = Math.sqrt(s.center.x ** 2 + s.center.y ** 2 + s.center.z ** 2) + s.radius;
    maxExtent = Math.max(maxExtent, sr);
  }
  const camDistance = Math.max(maxExtent * 3, 15);

  return {
    type: '3d',
    camera: {
      distance: camDistance,
      elevation: 0.6,  // ~34 degrees
      azimuth: 0.78,   // ~45 degrees
    },
    autoRotate: true,
    background: '#ffffff',
    elements: {
      points,
      edges,
      faces,
      angleArcs,
      circles,
      spheres,
    },
  };
}
