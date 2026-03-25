/**
 * Rendering schema types — the OUTPUT of the converter, INPUT to renderers.
 * All coordinates are resolved (no point-ID references, just numbers).
 */

export type Vec2 = { x: number; y: number };
export type Vec3 = { x: number; y: number; z: number };

// ── Style types ──

export type LineStyle = 'solid' | 'dashed';
export type PointStyle = 'vertex' | 'center' | 'highlight';

// ── 2D element types ──

export interface RenderPoint2D {
  id: string;
  pos: Vec2;
  label: string;
  style: PointStyle;
}

export interface RenderSegment2D {
  id: string;
  from: Vec2;
  to: Vec2;
  style: LineStyle;
  label?: string;        // midpoint label (e.g. "6 cm")
  highlight: boolean;
}

export interface RenderCircle2D {
  id: string;
  center: Vec2;
  radius: number;        // in viewport pixels
}

export interface RenderArc2D {
  id: string;
  center: Vec2;
  radius: number;        // arc display radius in pixels
  startAngle: number;    // degrees
  endAngle: number;      // degrees (CCW sweep from start to end)
  label?: string;        // e.g. "35°" or "?"
  highlight: boolean;
}

export interface RenderRightAngle2D {
  id: string;
  vertex: Vec2;
  p1: Vec2;              // point on first ray
  p2: Vec2;              // point on second ray
  size: number;          // marker size in pixels
}

export interface RenderPolygon2D {
  id: string;
  vertices: Vec2[];
  fill: string;          // CSS color with opacity
}

export interface RenderAxes2D {
  xRange: [number, number];  // [min, max] in viewport pixels
  yRange: [number, number];
  origin: Vec2;              // origin position in viewport pixels
  ticks: { pos: Vec2; label: string }[];
}

export interface RenderCurve2D {
  id: string;
  points: Vec2[];        // sampled points in viewport coords
}

export interface RenderAnnotation2D {
  text: string;
  pos: Vec2;
}

// ── 2D scene ──

export interface RenderScene2D {
  type: '2d';
  viewport: { width: number; height: number };
  centroid: Vec2;
  elements: {
    polygons: RenderPolygon2D[];
    circles: RenderCircle2D[];
    segments: RenderSegment2D[];
    arcs: RenderArc2D[];
    rightAngles: RenderRightAngle2D[];
    points: RenderPoint2D[];
    annotations: RenderAnnotation2D[];
    axes?: RenderAxes2D;
    curves: RenderCurve2D[];
  };
}

// ── 3D element types ──

export interface RenderPoint3D {
  id: string;
  pos: Vec3;
  label: string;
  style: PointStyle;
  color: string;
  radius: number;
}

export interface RenderEdge3D {
  id: string;
  from: Vec3;
  to: Vec3;
  style: LineStyle;
  color: string;
  label?: string;
  highlight: boolean;
}

export interface RenderFace3D {
  id: string;
  vertices: Vec3[];
  color: string;
  opacity: number;
}

export interface RenderAngleArc3D {
  id: string;
  center: Vec3;
  p1: Vec3;
  p2: Vec3;
  label?: string;
  highlight: boolean;
}

export interface RenderCircle3D {
  id: string;
  center: Vec3;
  radius: number;
  /** Normal vector of the circle's plane (default: Y-up) */
  normal: Vec3;
  color: string;
}

export interface RenderSphere3D {
  id: string;
  center: Vec3;
  radius: number;
  color: string;
  opacity: number;
}

export interface RenderAxes3D {
  xRange: [number, number];
  yRange: [number, number];
  zRange: [number, number];
}

// ── 3D scene ──

export interface RenderScene3D {
  type: '3d';
  camera: {
    distance: number;
    elevation: number;    // radians
    azimuth: number;      // radians
  };
  autoRotate: boolean;
  background: string;
  elements: {
    points: RenderPoint3D[];
    edges: RenderEdge3D[];
    faces: RenderFace3D[];
    angleArcs: RenderAngleArc3D[];
    circles: RenderCircle3D[];
    spheres: RenderSphere3D[];
    axes?: RenderAxes3D;
  };
}

// ── Union type ──

export type RenderScene = RenderScene2D | RenderScene3D;
