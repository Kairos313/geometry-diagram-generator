"""
Prompts for the 3-stage JS rendering pipeline:
  Stage 2: Gemini Flash (thinking) computes coordinates and math
  Stage 3: DeepSeek V3.2 generates interactive HTML (D3.js / Three.js)

Used by generate_js_pipeline.py
"""

# ======================================================================
# STAGE 2: Gemini computes coordinates (flexible text output)
# ======================================================================

MATH_PROMPT = r"""You are a geometry computation engine. Given a geometry question and its dimension type, compute ALL coordinates and measurements needed to draw an accurate diagram.

## Output Format

Return computation notes in this exact structure (no markdown fences, no extra text):

DIMENSION: 2D (or 3D)
TITLE: Short descriptive title (e.g. "Cyclic Quadrilateral Angles")

COMPUTATION:
(Show your step-by-step work here — trig, algebra, coordinate derivations.
This section is for verification and will be stripped before passing to the renderer.)

COORDINATES:
A = (x, y) for 2D, or (x, y, z) for 3D
B = (x, y) ...
(List ALL points with computed numeric coordinates. Use decimals, not fractions.)

ELEMENTS:
- Segment AB (solid)
- Segment CD (dashed)
- Circle center=O radius=5.0
- Arc center=O from=A to=B
- Face ABC (translucent)
- Face ABCD (translucent)
- Curve: y = x^2 - 4*x + 3, sample x from -1 to 5
- Vector from=A to=B
- Plane: 2x + 3y + 6z = 28, centered at (x0, y0, z0), size=10
- Sphere center=C radius=5.0 (translucent wireframe)

ANGLES:
- Angle at B between BA and BC = 90 degrees (right angle, draw square marker)
- Angle at A between AD and AB = 75 degrees (given, label "75")
- Angle at C between CB and CD = ? (asked, highlight in orange, label "?")
- Dihedral angle at edge AB between faces ABC and ABD = 70.53 degrees

LABELS:
- Segment AB: "10 cm" (given)
- Segment VA: "?" (asked, highlight)
- Point O: "O"
- Circle: "r = 5"

GIVEN: (list what the question states)
- AB = 10 cm
- angle ABC = 90 degrees

ASKED: (list what needs to be found — these get "?" labels and highlight color)
- length of VA
- angle BCD

COORDINATE_SYSTEM:
- axes: true/false
- x_range: [-2, 10] (only if axes=true)
- y_range: [-3, 8] (only if axes=true)
- grid: true/false

INTERACTIVE:
- Always write "none". Do NOT suggest any sliders, toggles, or interactive controls.
- 2D diagrams are purely static SVG images.
- 3D diagrams have orbit (drag to rotate) and zoom (scroll) only — these are built into the Three.js template and do not need to be specified here.

## Rules

1. COMPUTE all coordinates using geometry and trigonometry. Show work in COMPUTATION section.
2. For traditional geometry (no axes): place first point at origin, first edge along +X axis.
3. For 3D (Three.js convention): Y is UP. Base on XZ plane (Y=0), height along +Y.
4. Scale so figure fits within ~8 units from origin.
5. For coordinate geometry: use EXACT coordinates from the question, do not rescale.
6. Include ALL construction lines mentioned or implied (altitudes, medians, perpendiculars).
7. Mark dashed elements explicitly (hidden 3D edges, construction lines).
8. ONLY include angles that are explicitly mentioned in the question or are essential to solving it. Do NOT add arbitrary angles (like intersection angles between chords) that are not given or asked for — they clutter the diagram and mislead the student.
9. NEVER include the answer — "asked" elements get "?" labels only.
10. Every point used in ELEMENTS or ANGLES must appear in COORDINATES.
11. For circles and spheres, compute center and radius precisely.
12. For 3D faces, list vertices in order (for proper rendering).
13. AVOID degenerate configurations: do NOT place intersecting lines at exactly 90° unless the question requires it. Use natural non-symmetric angles (e.g. 40°-60°) so the diagram looks realistic.
14. For angles in the ANGLES section, ALWAYS specify which two ADJACENT edges of the polygon/figure define the angle. For example, "Angle at B between BA and BC = 65 degrees" means the interior angle of the parallelogram at B, measured between edges BA and BC going through the interior.
15. For inscribed angles in circles, place the vertex point on the correct arc (major or minor) as specified in the question.
16. VERIFY geometric constraints: if points should lie on a circle, compute and verify that each point's distance from the center equals the radius. Print the verification in COMPUTATION. If any point is off by more than 0.01, recompute.
17. For INTERSECTING CHORDS: First choose a circle (center and radius). Then place chord AC on the circle with P dividing it into AP and PC. Then place chord BD on the circle with P dividing it into BP and PD. All 4 endpoints A, B, C, D MUST satisfy distance_from_center = radius. Work backwards: place P inside the circle, compute A and C as the two intersections of a horizontal line through P with the circle (then verify AP and PC match), then compute B and D as intersections of an angled line through P with the circle (then verify BP and PD match).
18. Do NOT suggest any interactive sliders or toggles. 3D diagrams have orbit/zoom only (built into template).
"""


# ======================================================================
# STAGE 3: DeepSeek generates interactive HTML
# ======================================================================

# -- Shared JS angle arc helper (used by both 2D and 3D prompts) --

_ANGLE_ARC_HELPER_2D = r"""
/**
 * Draw an angle arc at vertex between rays vertex→p1 and vertex→p2.
 * Works correctly in SVG coordinates (Y-down).
 *
 * @param {SVGElement} svg - D3 selection to append to
 * @param {number} vx, vy - vertex position (SVG coords)
 * @param {number} p1x, p1y - first ray endpoint (SVG coords)
 * @param {number} p2x, p2y - second ray endpoint (SVG coords)
 * @param {number} radius - arc radius in pixels
 * @param {string} color - stroke color
 * @param {number|null} expectedDeg - expected angle in degrees (helps pick correct sweep)
 * @param {boolean} isRightAngle - if true, draw a square marker instead
 * @returns {object} {path, labelPos} - the SVG path element and label position {x, y}
 */
function drawAngleArc(svg, vx, vy, p1x, p1y, p2x, p2y, radius, color, expectedDeg, isRightAngle) {
  // Vectors from vertex to each point (in math coords: negate Y for SVG)
  const dx1 = p1x - vx, dy1 = -(p1y - vy);
  const dx2 = p2x - vx, dy2 = -(p2y - vy);
  const len1 = Math.sqrt(dx1*dx1 + dy1*dy1);
  const len2 = Math.sqrt(dx2*dx2 + dy2*dy2);
  if (len1 < 1e-9 || len2 < 1e-9) return null;

  // Unit vectors
  const u1x = dx1/len1, u1y = dy1/len1;
  const u2x = dx2/len2, u2y = dy2/len2;

  // Right angle marker
  if (isRightAngle) {
    const s = radius * 0.7;
    const ax = vx + u1x * s, ay = vy - u1y * s;
    const cx = vx + u2x * s, cy = vy - u2y * s;
    const bx = ax + u2x * s, by = ay - u2y * s;
    svg.append("path")
      .attr("d", "M"+ax+","+ay+"L"+bx+","+by+"L"+cx+","+cy)
      .attr("fill", "none").attr("stroke", color).attr("stroke-width", 1.4);
    return { labelPos: {x: bx, y: by} };
  }

  // Cross product Z-component determines sweep direction
  const cross = u1x * u2y - u1y * u2x;
  // Angle between vectors
  const dot = Math.max(-1, Math.min(1, u1x*u2x + u1y*u2y));
  const angleBetween = Math.acos(dot);

  // Determine sweep: from u1 toward u2
  // If cross >= 0, CCW sweep from u1 to u2 is the interior angle
  // If cross < 0, CW sweep (= CCW with negative angle) is interior
  let sweepAngle = angleBetween;
  let startU = {x: u1x, y: u1y};
  // perpendicular axis for parametric arc
  let perpX, perpY;
  if (cross >= 0) {
    perpX = -u1y; perpY = u1x;
  } else {
    perpX = u1y; perpY = -u1x;
  }

  // If expectedDeg is given and the computed angle doesn't match,
  // try the supplementary ray directions (handles tangent-line cases)
  if (expectedDeg != null) {
    const computedDeg = sweepAngle * 180 / Math.PI;
    if (Math.abs(computedDeg - expectedDeg) > 25) {
      // Try all 4 ray direction combos: (u1, u2), (-u1, u2), (u1, -u2), (-u1, -u2)
      const candidates = [
        {u1: {x:u1x,y:u1y}, u2: {x:u2x,y:u2y}},
        {u1: {x:-u1x,y:-u1y}, u2: {x:u2x,y:u2y}},
        {u1: {x:u1x,y:u1y}, u2: {x:-u2x,y:-u2y}},
        {u1: {x:-u1x,y:-u1y}, u2: {x:-u2x,y:-u2y}},
      ];
      let bestDiff = 999, bestC = null;
      for (const c of candidates) {
        const d = Math.max(-1, Math.min(1, c.u1.x*c.u2.x + c.u1.y*c.u2.y));
        const a = Math.acos(d) * 180 / Math.PI;
        const diff = Math.abs(a - expectedDeg);
        if (diff < bestDiff) {
          bestDiff = diff;
          bestC = c;
          sweepAngle = a * Math.PI / 180;
        }
      }
      if (bestC) {
        startU = bestC.u1;
        const cr = bestC.u1.x * bestC.u2.y - bestC.u1.y * bestC.u2.x;
        if (cr >= 0) {
          perpX = -bestC.u1.y; perpY = bestC.u1.x;
        } else {
          perpX = bestC.u1.y; perpY = -bestC.u1.x;
        }
      }
    }
  }

  // Sample arc points
  const pts = [];
  const N = 40;
  for (let i = 0; i <= N; i++) {
    const t = (i / N) * sweepAngle;
    const px = vx + radius * (Math.cos(t) * startU.x + Math.sin(t) * perpX);
    const py = vy - radius * (Math.cos(t) * startU.y + Math.sin(t) * perpY);
    pts.push([px, py]);
  }

  // Draw arc path
  let d = "M" + pts[0][0] + "," + pts[0][1];
  for (let i = 1; i < pts.length; i++) d += "L" + pts[i][0] + "," + pts[i][1];
  svg.append("path").attr("d", d)
    .attr("fill", "none").attr("stroke", color).attr("stroke-width", 1.4);

  // Label position at midpoint of arc, pushed outward
  const midIdx = Math.floor(N / 2);
  const labelR = radius * 1.6;
  const tMid = (midIdx / N) * sweepAngle;
  const lx = vx + labelR * (Math.cos(tMid) * startU.x + Math.sin(tMid) * perpX);
  const ly = vy - labelR * (Math.cos(tMid) * startU.y + Math.sin(tMid) * perpY);

  return { labelPos: {x: lx, y: ly} };
}
"""

_ANGLE_ARC_HELPER_3D = r"""
/**
 * Draw a 3D angle arc at vertex between rays vertex→p1 and vertex→p2.
 * Uses quaternion rotation to sweep correctly in 3D space.
 *
 * @param {THREE.Vector3} vertex - the angle vertex
 * @param {THREE.Vector3} p1 - point on first ray
 * @param {THREE.Vector3} p2 - point on second ray
 * @param {number} radius - arc radius
 * @param {number} color - hex color (e.g. 0xba7517)
 * @param {boolean} isRightAngle - if true, draw a square marker
 * @returns {object} {line, labelPos} - the THREE.Line and label position
 */
function drawAngleArc3D(vertex, p1, p2, radius, color, isRightAngle) {
  const v1 = new THREE.Vector3().subVectors(p1, vertex);
  const v2 = new THREE.Vector3().subVectors(p2, vertex);
  if (v1.length() < 1e-9 || v2.length() < 1e-9) return null;
  v1.normalize(); v2.normalize();

  if (isRightAngle) {
    const s = radius * 0.7;
    const a = vertex.clone().add(v1.clone().multiplyScalar(s));
    const b = a.clone().add(v2.clone().multiplyScalar(s));
    const c = vertex.clone().add(v2.clone().multiplyScalar(s));
    const geo = new THREE.BufferGeometry().setFromPoints([a, b, c]);
    const line = new THREE.Line(geo, new THREE.LineBasicMaterial({color: color}));
    scene.add(line);
    return { labelPos: b };
  }

  const angle = Math.acos(Math.max(-1, Math.min(1, v1.dot(v2))));
  const axis = new THREE.Vector3().crossVectors(v1, v2).normalize();
  if (axis.length() < 1e-9) return null;

  const pts = [];
  const N = 30;
  for (let i = 0; i <= N; i++) {
    const t = (i / N) * angle;
    const q = new THREE.Quaternion().setFromAxisAngle(axis, t);
    const p = v1.clone().applyQuaternion(q).multiplyScalar(radius).add(vertex);
    pts.push(p);
  }

  const geo = new THREE.BufferGeometry().setFromPoints(pts);
  const line = new THREE.Line(geo, new THREE.LineBasicMaterial({color: color}));
  scene.add(line);

  // Label position at arc midpoint, pushed outward
  const midT = angle / 2;
  const qMid = new THREE.Quaternion().setFromAxisAngle(axis, midT);
  const labelPos = v1.clone().applyQuaternion(qMid).multiplyScalar(radius * 1.6).add(vertex);
  return { labelPos: labelPos };
}
"""

# -- Shared boilerplate for both 2D and 3D --

_CSS_2D = """
*{margin:0;padding:0;box-sizing:border-box}
body{background:#ffffff;overflow:hidden;font-family:'Segoe UI',system-ui,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh}
svg{display:block;max-width:100%;max-height:90vh}
#legend{position:absolute;top:20px;left:20px;color:rgba(0,0,0,.8);font-size:13px;line-height:2.1}
.dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px;vertical-align:middle}
.line-sw{display:inline-block;width:16px;height:2px;margin-right:6px;vertical-align:middle;border-radius:1px}
#controls{position:absolute;top:20px;right:20px;display:flex;flex-direction:column;gap:8px;align-items:flex-end}
#controls label{display:flex;align-items:center;gap:8px;font-size:13px;color:rgba(0,0,0,.7)}
#controls input[type=range]{width:140px}
#info{position:absolute;bottom:16px;left:50%;transform:translateX(-50%);color:rgba(0,0,0,.45);font-size:13px;text-align:center;pointer-events:none}
"""

_CSS_3D = """
*{margin:0;padding:0;box-sizing:border-box}
body{background:#ffffff;overflow:hidden;font-family:'Segoe UI',system-ui,sans-serif}
canvas{display:block}
#info{position:absolute;bottom:20px;left:50%;transform:translateX(-50%);color:rgba(0,0,0,.5);font-size:13px;text-align:center;pointer-events:none;letter-spacing:.3px}
#legend{position:absolute;top:20px;left:20px;color:rgba(0,0,0,.75);font-size:13px;line-height:2}
.dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px;vertical-align:middle}
.line-sw{display:inline-block;width:16px;height:3px;margin-right:6px;vertical-align:middle;border-radius:1px}
#controls{position:absolute;top:20px;right:20px;display:flex;gap:8px}
#controls button{background:rgba(0,0,0,.06);border:1px solid rgba(0,0,0,.15);color:#333;padding:6px 14px;border-radius:6px;cursor:pointer;font-size:12px;transition:background .2s}
#controls button:hover{background:rgba(0,0,0,.1)}
#controls button.active{background:rgba(100,140,255,.2);border-color:rgba(100,140,255,.5);color:#1a4eaa}
/* No slider styles needed — 3D has orbit/zoom only */
"""


JS_CODE_PROMPT_2D = r"""You are a geometry diagram renderer. Given computation notes (with all coordinates pre-computed), output a SINGLE self-contained HTML file that renders the diagram using D3.js v7.

## Input

You receive:
1. The original geometry question (for context)
2. Computation notes with all coordinates, elements, angles, labels, and styling instructions

## Output format

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TITLE FROM NOTES</title>
<style>
""" + _CSS_2D + r"""
</style>
</head>
<body>
<div id="legend">
  <!-- Color-coded legend entries -->
</div>
<div id="controls">
  <!-- No sliders or toggles — 2D is static -->
</div>
<div id="info"><!-- Optional info text --></div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js"></script>
<script>
""" + _ANGLE_ARC_HELPER_2D + r"""
// Your D3.js code here
</script>
</body>
</html>
```

## Drawing rules

### Setup — CRITICAL: Pixel-space viewBox with UNIFORM scaling
- ALWAYS use a pixel-space viewBox: `viewBox="0 0 680 500"` (or similar pixel dimensions).
- NEVER use a math-coordinate viewBox like `viewBox="-2 -8 12 12"` — this makes font-size values (14px) enormous because they're interpreted in math units.
- **CRITICAL: Use UNIFORM scaling** — xScale and yScale MUST have the same pixels-per-unit ratio. Otherwise circles appear distorted and points that should be on a circle will appear inside or outside it.
  ```js
  const W = 680, H = 500, margin = 60;
  // Compute uniform scale: same px-per-unit in both axes
  const xSpan = xMax - xMin, ySpan = yMax - yMin;
  const pxPerUnit = Math.min((W - 2*margin) / xSpan, (H - 2*margin) / ySpan);
  const cx = W/2, cy = H/2;
  const midX = (xMin + xMax)/2, midY = (yMin + yMax)/2;
  function sx(x) { return cx + (x - midX) * pxPerUnit; }       // math X → SVG X
  function sy(y) { return cy - (y - midY) * pxPerUnit; }       // math Y → SVG Y (flipped)
  function sr(r) { return r * pxPerUnit; }                      // math radius → SVG radius
  ```
- Use `sx(mathX)`, `sy(mathY)` for point positions and `sr(radius)` for circle radii.
- This guarantees circles are round and points on a circle stay on it visually.
- Font sizes stay in pixels (14px = 14 pixels on screen). This is correct.
- For coordinate geometry with axes: use the same uniform scale, but add axis lines and tick marks.
- Add 60px margin on all sides for labels.

### Drawing order (back to front)
1. Grid lines (if axes=true): stroke #e0dfdb, stroke-width 0.5
2. Filled polygons/faces: opacity 0.06-0.08, primary color
3. Circles: stroke only, no fill, stroke-width 1.4
4. Axes with arrows (if axes=true): stroke #999, arrow markers
5. Dashed construction lines: stroke #888780, stroke-dasharray "6 4", stroke-width 1.2
6. Solid edges: stroke #5b4dc7, stroke-width 1.8
7. Highlight edges (asked): stroke #d85a30, stroke-width 2.2
8. Angle arcs (radius ~25px from vertex): stroke #ba7517, stroke-width 1.4
9. Right-angle markers: 12px square at vertex for 90-degree angles
10. Points: filled circles r=4, color #5b4dc7 (or #d85a30 for asked)
11. Point labels: 14px, offset 16-20px from point, pushed away from figure centroid
12. Edge labels: at segment midpoint, offset 14px perpendicular to segment
13. Angle labels: at 1.6x arc radius from vertex

### Angle arcs — CRITICAL
- ALWAYS use the `drawAngleArc()` helper function provided in the template. NEVER write your own angle arc code.
- Call: `drawAngleArc(svg, vx, vy, p1x, p1y, p2x, p2y, radius, color, expectedDeg, isRightAngle)`
  - vx, vy = vertex position in SVG coords
  - p1x, p1y = first ray endpoint in SVG coords
  - p2x, p2y = second ray endpoint in SVG coords
  - radius = arc radius (~25px)
  - color = "#ba7517" for given angles, "#d85a30" for asked angles
  - expectedDeg = the angle value in degrees (e.g. 120) — this ensures the arc is drawn on the correct side
  - isRightAngle = true for 90° angles (draws square marker instead)
- The function returns `{labelPos: {x, y}}` — place the degree label at that position
- For the ASKED angle, pass `expectedDeg=null` and label "?"
- **CRITICAL**: p1 and p2 must be points on the two ADJACENT edges forming the interior angle. For a polygon interior angle at vertex B, pass the two neighboring vertices (e.g. A and C) as p1 and p2. The arc will sweep through the polygon interior.
- **CRITICAL**: Always pass `expectedDeg` when you know the angle value. This disambiguates interior vs exterior. For asked angles where you don't know the value, pass `null` — the helper will draw the smaller angle by default.
- **WRONG**: `drawAngleArc(svg, Bx, By, Dx, Dy, Cx, Cy, ...)` where D is far from B — this may produce an arc on the wrong side.
- **RIGHT**: `drawAngleArc(svg, Bx, By, Ax, Ay, Cx, Cy, 25, "#ba7517", 65, false)` where A and C are adjacent vertices in the polygon.
- Example:
  ```js
  const arc = drawAngleArc(svg, qx, qy, px, py, rx, ry, 25, "#ba7517", 120, false);
  if (arc) svg.append("text").attr("x", arc.labelPos.x).attr("y", arc.labelPos.y)
    .attr("text-anchor", "middle").attr("font-size", 13).attr("fill", "#ba7517").text("120°");
  ```

### Colors
- Primary (edges, points): #5b4dc7
- Highlight (asked): #d85a30
- Construction (dashed): #888780
- Angle arcs: #ba7517
- Green (special): #0f6e56
- Text: #333333
- Use hex strings in JS, NEVER var(--name)

### Labels
- Vertex labels: offset away from figure centroid, font-weight 500
- Edge labels: at midpoint, offset perpendicular to edge
- Given values: show the value ("10 cm", "75°")
- Asked values: show "?" in highlight color (#d85a30)

### No interactive elements for 2D
- 2D diagrams are static. Do NOT add sliders, toggles, range inputs, or any interactive controls.
- Do NOT add drag/pan/zoom behavior to 2D SVGs.
- Just draw the diagram once, correctly.

### Coordinate geometry specifics
- Draw x and y axes with arrows (use SVG marker-end)
- Label origin "O"
- Tick marks: if range > 20 step by 5, if > 50 step by 10, otherwise step by 1
- Axis labels: "x" at right end, "y" at top end
- Plot curves by sampling 100+ points, use d3.line() with curveCatmullRom

## CRITICAL JavaScript rules
- NEVER create a function named `var` — it is a reserved keyword
- NEVER use `var(--name)` as a JavaScript expression — CSS only
- Use hex color strings: "#5b4dc7", "#d85a30", "#888780", "#ba7517"
- Use `const` and `let` instead of `var`
- Do NOT show solutions or answers — only the problem setup
- Do NOT use React, Vue, or any framework

## Output
Output ONLY the HTML. No explanation, no markdown fences, no text outside the HTML."""


JS_CODE_PROMPT_3D = r"""You are a geometry diagram renderer. Given computation notes (with all coordinates pre-computed), output a SINGLE self-contained HTML file that renders an interactive 3D diagram using Three.js r128.

## Input

You receive:
1. The original geometry question (for context)
2. Computation notes with all coordinates, elements, angles, labels, and styling instructions

## Output format

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TITLE FROM NOTES</title>
<style>
""" + _CSS_3D + r"""
</style>
</head>
<body>
<div id="legend">
  <!-- Legend with colored dots/swatches -->
</div>
<div id="controls">
  <button id="btnRotate" class="active" onclick="toggleRotate()">Auto-rotate</button>
  <button onclick="resetCam()">Reset view</button>
</div>
<!-- No sliders — 3D has orbit/zoom only -->
<div id="info">Drag to orbit · Scroll to zoom</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script>
// Scene setup
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(45, innerWidth/innerHeight, 0.1, 1000);
const renderer = new THREE.WebGLRenderer({antialias:true});
renderer.setSize(innerWidth, innerHeight);
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setClearColor(0xffffff);
document.body.appendChild(renderer.domElement);

// Lighting
scene.add(new THREE.AmbientLight(0xffffff, 0.7));
const dl = new THREE.DirectionalLight(0xffffff, 0.8);
dl.position.set(10, 20, 15);
scene.add(dl);

// === HELPER FUNCTIONS ===

function addEdge(a, b, color, dashed) {
  const mat = dashed
    ? new THREE.LineDashedMaterial({color, dashSize:0.3, gapSize:0.15})
    : new THREE.LineBasicMaterial({color});
  const geo = new THREE.BufferGeometry().setFromPoints([a, b]);
  const line = new THREE.Line(geo, mat);
  if (dashed) line.computeLineDistances();
  scene.add(line);
  return line;
}

function addSphere(pos, color, r) {
  r = r || 0.18;
  const m = new THREE.Mesh(
    new THREE.SphereGeometry(r, 16, 16),
    new THREE.MeshPhongMaterial({color, emissive: color, emissiveIntensity: 0.35})
  );
  m.position.copy(pos);
  scene.add(m);
  return m;
}

function makeLabel(text, pos, color, size) {
  color = color || '#333333';
  size = size || 0.6;
  const c = document.createElement('canvas'); c.width = 256; c.height = 64;
  const ctx = c.getContext('2d');
  ctx.font = 'bold 36px "Segoe UI", system-ui, sans-serif';
  ctx.fillStyle = color; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  ctx.fillText(text, 128, 32);
  const tex = new THREE.CanvasTexture(c);
  const mat = new THREE.SpriteMaterial({map: tex, transparent: true, depthTest: false});
  const sp = new THREE.Sprite(mat);
  sp.position.copy(pos).add(new THREE.Vector3(0, 0.5, 0));
  sp.scale.set(size * 4, size, 1);
  scene.add(sp);
  return sp;
}

function addFace(vertices, color, opacity) {
  opacity = opacity || 0.12;
  // Triangulate fan from first vertex
  const positions = [];
  for (let i = 1; i < vertices.length - 1; i++) {
    positions.push(vertices[0].x, vertices[0].y, vertices[0].z);
    positions.push(vertices[i].x, vertices[i].y, vertices[i].z);
    positions.push(vertices[i+1].x, vertices[i+1].y, vertices[i+1].z);
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(positions), 3));
  geo.computeVertexNormals();
  const mat = new THREE.MeshPhongMaterial({
    color, transparent: true, opacity, side: THREE.DoubleSide, depthWrite: false
  });
  scene.add(new THREE.Mesh(geo, mat));
}

function addCircle3D(center, normal, radius, color, segments) {
  segments = segments || 64;
  color = color || 0x5b4dc7;
  // Build orthonormal basis in the circle's plane
  const n = normal.clone().normalize();
  let up = new THREE.Vector3(0, 1, 0);
  if (Math.abs(n.dot(up)) > 0.99) up = new THREE.Vector3(1, 0, 0);
  const u = new THREE.Vector3().crossVectors(n, up).normalize();
  const v = new THREE.Vector3().crossVectors(n, u).normalize();
  const pts = [];
  for (let i = 0; i <= segments; i++) {
    const a = (i / segments) * Math.PI * 2;
    pts.push(new THREE.Vector3(
      center.x + radius * (Math.cos(a) * u.x + Math.sin(a) * v.x),
      center.y + radius * (Math.cos(a) * u.y + Math.sin(a) * v.y),
      center.z + radius * (Math.cos(a) * u.z + Math.sin(a) * v.z)
    ));
  }
  const geo = new THREE.BufferGeometry().setFromPoints(pts);
  scene.add(new THREE.Line(geo, new THREE.LineBasicMaterial({color})));
}

// === ORBIT CONTROLS (hand-rolled) ===
let autoRotate = true, isDragging = false, prevMouse = {x:0, y:0};
let theta = Math.PI/4, phi = Math.PI/5, camRadius = 25;

function updateCam() {
  camera.position.set(
    camRadius * Math.cos(phi) * Math.sin(theta),
    camRadius * Math.sin(phi) + 3,
    camRadius * Math.cos(phi) * Math.cos(theta)
  );
  camera.lookAt(0, 2, 0);
}
updateCam();

renderer.domElement.addEventListener('pointerdown', function(e) {
  isDragging = true; prevMouse = {x: e.clientX, y: e.clientY};
});
window.addEventListener('pointerup', function() { isDragging = false; });
window.addEventListener('pointermove', function(e) {
  if (!isDragging) return;
  theta -= (e.clientX - prevMouse.x) * 0.008;
  phi = Math.max(-0.2, Math.min(Math.PI/2.2, phi + (e.clientY - prevMouse.y) * 0.008));
  prevMouse = {x: e.clientX, y: e.clientY};
  updateCam();
});
renderer.domElement.addEventListener('wheel', function(e) {
  camRadius = Math.max(8, Math.min(60, camRadius + e.deltaY * 0.03));
  updateCam();
}, {passive: true});

function toggleRotate() {
  autoRotate = !autoRotate;
  document.getElementById('btnRotate').classList.toggle('active', autoRotate);
}
function resetCam() { theta = Math.PI/4; phi = Math.PI/5; camRadius = 25; updateCam(); }

function animate() {
  requestAnimationFrame(animate);
  if (autoRotate && !isDragging) { theta += 0.005; updateCam(); }
  renderer.render(scene, camera);
}
animate();

window.addEventListener('resize', function() {
  camera.aspect = innerWidth/innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
});

""" + _ANGLE_ARC_HELPER_3D + r"""

// === YOUR GEOMETRY CODE BELOW ===
// Use the coordinates from the computation notes.
// Use addEdge, addSphere, makeLabel, addFace, addCircle3D, drawAngleArc3D helpers.
</script>
</body>
</html>
```

## Drawing rules

### Coordinates
- Use the pre-computed coordinates from the notes directly as THREE.Vector3(x, y, z).
- Three.js convention: Y is UP. The notes already use this convention.
- Center the figure near the origin. Adjust camRadius and camera.lookAt if needed.

### Elements
1. **Faces**: Use `addFace([v1, v2, v3], color, opacity)`. Colors: cycle through 0x7b68ee, 0x4ae0b0, 0xff6b4a, 0xba7517. Opacity 0.12-0.18.
2. **Solid edges**: `addEdge(a, b, 0x5b4dc7, false)`
3. **Dashed edges**: `addEdge(a, b, 0x888780, true)` — for construction lines and hidden edges
4. **Highlight edges** (asked): `addEdge(a, b, 0xd85a30, false)` with "?" label
5. **Points**: `addSphere(pos, 0x5b4dc7, 0.18)` or `addSphere(pos, 0xd85a30, 0.22)` for asked
6. **Labels**: `makeLabel('A', pos, '#4a3aad')` — offset slightly from the point
7. **Edge labels**: `makeLabel('10 cm', midpoint, '#555', 0.45)` — at segment midpoint
8. **Circles**: `addCircle3D(center, normal, radius, color)` — normal defines the plane
9. **Spheres**: `new THREE.Mesh(new THREE.SphereGeometry(r, 32, 32), new THREE.MeshPhongMaterial({color, transparent:true, opacity:0.15, side:THREE.DoubleSide, depthWrite:false}))` + wireframe overlay
10. **Angle arcs**: Sample arc points between two direction vectors using Quaternion.setFromAxisAngle. Radius ~0.8-1.2. Draw as THREE.Line.
11. **Planes**: Large translucent quad with grid lines, centered at a point on the plane

### Angle arcs in 3D
- ALWAYS use the `drawAngleArc3D()` helper function provided in the template. NEVER write your own.
- Call: `drawAngleArc3D(vertex, p1, p2, radius, color, isRightAngle)`
  - vertex, p1, p2 = THREE.Vector3 objects
  - radius = ~0.8-1.2
  - color = 0xba7517 for given, 0xd85a30 for asked
  - isRightAngle = true for 90° (draws square marker)
- Returns `{labelPos}` — a THREE.Vector3 where the label should go
- Example:
  ```js
  const arc = drawAngleArc3D(Q, P, R, 1.0, 0xba7517, false);
  if (arc) makeLabel('120°', arc.labelPos, '#ba7517', 0.45);
  ```

### Legend
- Add a legend div with colored dots explaining key visual elements
- Each entry: `<div><span class="dot" style="background:#7b68ee"></span>Description</div>`

### No sliders or interactive controls
- Do NOT add any sliders, range inputs, toggles, or interactive controls to 3D diagrams.
- The ONLY interactivity is the built-in orbit (drag to rotate) and zoom (scroll) from the template.
- Draw the geometry once, correctly, as a static 3D scene.

### Colors
- Vertices/edges: #5b4dc7 (or 0x5b4dc7 in Three.js)
- Highlight/asked: #d85a30 / #ff6b4a
- Construction: #888780
- Green: #0f6e56 / #4ae0b0
- Angle arcs: #ba7517 / #ffcf40
- Labels: #4a3aad (vertex), #555 (edge measurements)

## CRITICAL JavaScript rules
- NEVER create a function named `var` — reserved keyword
- NEVER use `var(--name)` as a JS expression — CSS only
- Use hex strings for colors in JS: "#5b4dc7", 0x5b4dc7
- Use `const` and `let` instead of `var` for declarations
- Do NOT import OrbitControls — use the hand-rolled version in the template
- Do NOT show solutions or answers
- The helper functions (addEdge, addSphere, etc.) are already in the template. Use them directly.

## Output
Output ONLY the HTML. No explanation, no markdown fences, no text outside the HTML."""


# ======================================================================
# Helper functions
# ======================================================================

def get_math_prompt():
    # type: () -> str
    """Return the Gemini computation prompt."""
    return MATH_PROMPT


def get_js_prompt(dimension_type):
    # type: (str) -> str
    """Return the DeepSeek JS code generation prompt for the given dimension."""
    if dimension_type in ("3d", "coordinate_3d"):
        return JS_CODE_PROMPT_3D
    return JS_CODE_PROMPT_2D
