/**
 * TypeScript types matching the JSON output of generate_blueprint_focused.py.
 * This is the INPUT format — what the LLM produces.
 */

export interface BlueprintScale {
  reference: string;   // e.g. "AB" or "auto"
  real: string;        // e.g. "6 cm" or "1 unit"
  units: number;       // scaled length, e.g. 5.0
}

export interface BlueprintLine {
  id: string;          // e.g. "line_AB"
  from: string;        // point ID
  to: string;          // point ID
  style?: 'solid' | 'dashed';
}

export interface BlueprintCircle {
  id: string;          // e.g. "circle_O"
  center: string;      // point ID
  radius: number;
}

export interface BlueprintArc {
  id: string;
  center: string;      // point ID
  from: string;        // point ID (start of arc)
  to: string;          // point ID (end of arc)
}

export interface BlueprintFace {
  id: string;
  points: string[];    // point IDs forming the face
}

export interface BlueprintAngle {
  id: string;          // e.g. "angle_ABC"
  vertex: string;      // point ID
  p1: string;          // point ID on first ray
  p2: string;          // point ID on second ray
  value?: number;      // angle in degrees (may be absent if unknown)
}

export interface BlueprintCurve {
  id: string;
  equation: string;    // e.g. "y = x^2 - 4*x + 3"
  points?: number[][]; // pre-sampled points [[x, y], ...]
}

export interface BlueprintCoordinateRange {
  x_min: number;
  x_max: number;
  y_min: number;
  y_max: number;
  z_min?: number;
  z_max?: number;
}

export interface BlueprintPlane {
  id: string;
  equation: string;
  normal: [number, number, number];
}

export interface BlueprintSphere {
  id: string;
  center: string;      // point ID
  radius: number;
}

export interface BlueprintVector {
  id: string;
  from: string;
  to: string;
}

/**
 * The main blueprint JSON type — output of Stage 2.
 * Points are in real-unit geometry coordinates (not pixels).
 */
export interface BlueprintJSON {
  dimension: '2d' | '3d';
  axes?: boolean;
  grid?: boolean;
  scale: BlueprintScale;
  points: Record<string, [number, number, number]>;
  lines?: BlueprintLine[];
  circles?: BlueprintCircle[];
  arcs?: BlueprintArc[];
  faces?: BlueprintFace[];
  angles?: BlueprintAngle[];
  given?: Record<string, string | [number, number, number]>;
  asked?: string[];

  // Coordinate geometry extensions
  coordinate_range?: BlueprintCoordinateRange;
  curves?: BlueprintCurve[];

  // 3D coordinate extensions
  planes?: BlueprintPlane[];
  spheres?: BlueprintSphere[];
  vectors?: BlueprintVector[];
}
