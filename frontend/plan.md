# Geometry question → automatic diagram generator

## What we're building

A system that takes any math geometry question as input and produces either an interactive SVG diagram (for 2D problems) or an interactive rotating 3D HTML scene (for 3D problems). The LLM does the hard work: parsing the question, solving the geometry, computing coordinates, and emitting a structured scene description. Two JS-based renderers — D3.js for 2D and Three.js for 3D — turn that description into a visual.

---

## Architecture overview

```
User question (natural language)
        │
        ▼
┌──────────────────┐
│   LLM layer      │  ← Parses question, classifies 2D vs 3D,
│   (Claude API)   │    solves geometry, computes coordinates
└──────────────────┘
        │
        ▼
┌──────────────────────────────────────────────┐
│  Unified geometry JSON schema                │
│  (vertices, edges, circles, labels, styles)  │
│  Single format for both 2D and 3D            │
└──────────────────────────────────────────────┘
        │
        ├──── type: "2d" ──▶  D3.js renderer  ────▶  Interactive SVG / PNG
        │                     (outputs SVG in DOM,
        │                      draggable, animated)
        │
        └──── type: "3d" ──▶  Three.js renderer ──▶  Interactive HTML / GIF
                              (WebGL canvas,
                               orbit, rotate)
```

### Why two JS renderers instead of one

**D3.js for 2D** because it generates SVG under the hood — you get interactivity (drag, hover, animate) while keeping all SVG advantages: lightweight (~2KB output), resolution-independent, exportable to PNG, embeddable in documents. A circle theorem diagram doesn't need WebGL.

**Three.js for 3D** because 3D orbit controls, perspective projection, and translucent surfaces require a WebGL canvas. D3 can't do this.

**What we avoid:** Using Three.js for 2D (overkill — 600KB library for a static diagram) or using raw SVG strings for 2D (no interactivity, fragile string concatenation, no collision detection).

**What we gain from unifying on JS:** A single schema format. The LLM doesn't need to know which renderer will be used — it emits the same JSON structure. Both renderers output self-contained HTML files with a CDN script tag. Both support interactivity. The primitives library is shared where possible (label offset math, midpoint calculation, angle computation).

---

## Phase 1: The geometry schema (the contract between LLM and renderers)

Define a single JSON schema that can describe any geometry scene. The `type` field determines which renderer processes it. Everything else is as similar as possible.

### 2D schema

```json
{
  "type": "2d",
  "viewport": { "width": 680, "height": 500 },
  "archetype": "circle-with-tangents",
  "interactive": {
    "draggable": ["P"],
    "animated": false
  },
  "elements": {
    "points": [
      { "id": "A", "x": 100, "y": 400, "label": "A", "style": "vertex" },
      { "id": "O", "x": 340, "y": 250, "label": "O", "style": "center" }
    ],
    "segments": [
      { "from": "A", "to": "B", "style": "solid", "label": null },
      { "from": "O", "to": "A", "style": "dashed", "label": "r = 6" }
    ],
    "circles": [
      { "center": "O", "radius": 180, "style": "thin" }
    ],
    "arcs": [
      { "center": "A", "radius": 40, "startAngle": 0, "endAngle": 35,
        "label": "35°", "style": "angle" }
    ],
    "lines": [
      { "through": "A", "angle": 0, "extent": 200, "label": "tangent TA" }
    ],
    "polygons": [
      { "vertices": ["A", "B", "C", "D"], "fill": "rgba(100,140,255,0.08)" }
    ],
    "rightAngleMarkers": [
      { "vertex": "A", "ray1": "O", "ray2": "T", "size": 12 }
    ],
    "annotations": [
      { "text": "Alternate segment theorem", "x": 200, "y": 440,
        "style": "note" }
    ]
  }
}
```

### 3D schema

```json
{
  "type": "3d",
  "camera": { "distance": 32, "elevation": 0.35, "azimuth": 0.78 },
  "autoRotate": true,
  "background": "#ffffff",
  "controls": [
    { "type": "slider", "param": "cutHeight", "min": 0, "max": 14.5,
      "default": 6, "label": "Height", "unit": "cm" }
  ],
  "elements": {
    "points": [
      { "id": "A", "x": -5, "y": 0, "z": -5, "label": "A",
        "color": "#7b68ee", "radius": 0.25 },
      { "id": "M", "x": -2.5, "y": 6, "z": -2.5, "label": "M",
        "color": "#ff6b4a", "radius": 0.35 }
    ],
    "edges": [
      { "from": "V", "to": "A", "style": "solid", "color": "#7b68ee" },
      { "from": "M", "to": "Mfoot", "style": "dashed", "color": "#ff6b4a",
        "label": "6 cm" }
    ],
    "faces": [
      { "vertices": ["A", "B", "C"], "color": "#7b68ee", "opacity": 0.12 }
    ],
    "solids": [
      { "type": "cone", "base": [0,0,0], "apex": [0,12,0], "radius": 5,
        "color": "#7b68ee", "opacity": 0.2 }
    ],
    "planes": [
      { "type": "square", "center": [0,0,0], "size": 10,
        "normal": [0,1,0], "opacity": 0.18 }
    ],
    "grid": { "size": 10, "divisions": 10 }
  },
  "legend": [
    { "color": "#7b68ee", "text": "Vertices" },
    { "color": "#ff6b4a", "text": "M (midpoint of VA)" },
    { "color": "#4ae0b0", "text": "Height = 12 cm" }
  ]
}
```

### Shared primitives across both schemas

| Geometry primitive     | 2D (D3)                   | 3D (Three.js)              |
|------------------------|---------------------------|-----------------------------|
| Points / vertices      | x, y, label, color        | x, y, z, label, color       |
| Line segments          | from → to, solid/dashed   | from → to, solid/dashed     |
| Infinite lines         | through + angle, or 2pts  | —                           |
| Circles                | center, radius            | —                           |
| Spheres                | —                         | center, radius, opacity     |
| Arcs (angle markers)   | center, start°, end°      | center, vectors, sweep      |
| Polygons / faces       | vertex list, fill         | vertex list, fill, opacity  |
| Right-angle markers    | vertex + 2 rays           | vertex + 2 rays             |
| Solids                 | —                         | type, params, opacity       |
| Planes                 | —                         | normal, point, size         |
| Annotations / labels   | text, position            | text, position              |
| Dimension lines        | from → to, label          | from → to, label            |

**Deliverable:** A TypeScript/JSON-Schema file that validates any geometry scene. A single `GeometryScene` type with a discriminated union on `type`.

---

## Phase 2: The 2D renderer (D3.js)

### 2.1 Why D3.js

| Criteria | Raw SVG strings | D3.js | Three.js (2D mode) |
|----------|----------------|-------|---------------------|
| Output format | SVG string | SVG in DOM | Canvas (raster) |
| Interactivity | None | Drag, hover, animate, transition | Full, but overkill |
| File size | ~2KB | ~10KB (output); 80KB (library CDN) | 600KB+ library |
| PNG export | resvg / Puppeteer | resvg / Puppeteer (SVG still in DOM) | Canvas.toDataURL() |
| Embed in docs | ✅ Copy SVG | ✅ Extract SVG from DOM | ❌ Raster only |
| Resolution independence | ✅ Vector | ✅ Vector | ❌ Pixel |
| Animated constructions | ❌ | ✅ D3 transitions | ✅ |
| Draggable points | ❌ | ✅ d3-drag | ✅ |
| Learning curve | Trivial | Moderate | High for 2D |
| Dark mode | CSS variables | CSS variables | Manual theme logic |

D3 is the sweet spot: SVG output (light, exportable, resolution-independent) with full interactivity.

### 2.2 Primitives library (shared math + D3-specific drawing)

The primitives library splits into two layers:

#### Layer 1: Pure math (shared between 2D and 3D)

No DOM dependencies. Pure functions that compute coordinates. Used by both renderers.

```typescript
// src/math/geometry.ts

pointOnCircle(center: Vec2, radius: number, angleDeg: number): Vec2
midpoint(p1: Vec2, p2: Vec2): Vec2
distance(p1: Vec2, p2: Vec2): number
angleBetween(vertex: Vec2, p1: Vec2, p2: Vec2): number
// Returns degrees, handling quadrant correctly

tangentPoints(circleCenter: Vec2, radius: number, external: Vec2): [Vec2, Vec2]
// Exact tangent point computation

intersectLineCircle(p1: Vec2, p2: Vec2, center: Vec2, r: number): Vec2[]
intersectLines(a1: Vec2, a2: Vec2, b1: Vec2, b2: Vec2): Vec2 | null

labelOffset(point: Vec2, centroid: Vec2, distance?: number): Vec2
// Pushes label away from figure center

arcSvgPath(center: Vec2, radius: number, startDeg: number, endDeg: number): string
// Correct SVG arc path with proper large-arc-flag and sweep-flag
// The #1 source of bugs in raw LLM SVG output

rightAnglePoints(vertex: Vec2, dir1: Vec2, dir2: Vec2, size?: number): Vec2[]
// Returns the three points of the right-angle square marker
```

#### Layer 2: D3 drawing functions

Takes a D3 selection (the SVG `<g>` group) and geometry data, appends SVG elements.

```typescript
// src/renderers/d3/primitives.ts

drawCircle(g: Selection, center: Vec2, radius: number, style: Style): Selection
drawSegment(g: Selection, from: Vec2, to: Vec2, style: Style): Selection
drawArc(g: Selection, center: Vec2, radius: number, start: number, end: number,
        label?: string): Selection
drawRightAngle(g: Selection, vertex: Vec2, dir1: Vec2, dir2: Vec2): Selection
drawPoint(g: Selection, pos: Vec2, label: string, style: Style): Selection
drawDimensionLine(g: Selection, from: Vec2, to: Vec2, label: string,
                  offset: number): Selection
drawPolygon(g: Selection, vertices: Vec2[], fill: string): Selection
drawAnnotation(g: Selection, pos: Vec2, text: string): Selection
```

Each function returns the D3 selection so you can chain `.call(drawCircle, ...)`.

### 2.3 Standard coordinate system and viewport

Fixed conventions that every 2D diagram follows:

- **Viewport:** 680 × 500px (`viewBox="0 0 680 500"`)
- **Safe area:** x = 40 to 640, y = 40 to 460 (40px margin on all sides for labels)
- **Coordinate system:** SVG-native (y-down). The LLM computes directly in this space.
- **Figure placement:** Center the primary shape at approximately (340, 250). Scale so it fills 60–70% of the viewport.
- **Label placement:** Vertex labels offset 16–20px from the vertex, pushed away from the figure centroid via `labelOffset()`.

### 2.4 Archetype templates

Most geometry questions fall into a small number of visual patterns. For each, define a layout template with default coordinates that the LLM adapts.

#### Archetype 1: Circle with inscribed polygon
**Triggers:** cyclic quadrilateral, inscribed angle, chord, arc
```
Circle center: (340, 250), radius: 170px
Labels: 20px radially outward from each vertex
Angle arcs: 30px radius, inside the polygon at each vertex
```

#### Archetype 2: Circle with external tangents
**Triggers:** tangent from external point, two tangents, secant-tangent
```
Circle center: (360, 250), radius: 140px
External point P: x = 80–120, y = 250
Tangent lines from P to computed tangent points
Radii to tangent points: dashed
```

#### Archetype 3: Triangle with special points
**Triggers:** centroid, incircle, circumcircle, orthocenter, medians, altitudes
```
Base AB: y ≈ 400, x = 140..540
Apex C: y ≈ 100–150, x ≈ 300–380
Construction lines: dashed, lighter color
```

#### Archetype 4: Parallel lines with transversal
**Triggers:** parallel lines, corresponding angles, alternate angles, co-interior
```
Line 1: y ≈ 180, full width
Line 2: y ≈ 350, full width
Transversal: (150, 80) to (530, 450)
Angle arcs at each intersection
```

#### Archetype 5: Two circles
**Triggers:** intersecting circles, tangent circles, common tangent, radical axis
```
Circle 1: center (240, 250)
Circle 2: center (440, 250)
Radii: proportional to problem values, scaled to fit
```

#### Archetype 6: Coordinate geometry on grid
**Triggers:** distance formula, midpoint, slope, line equation, y = mx + b
```
Origin: (340, 350)
Grid spacing: computed from coordinate range
Axes: with arrow markers
```

#### Archetype 7: Polygon with diagonals or midpoints
**Triggers:** quadrilateral, pentagon, hexagon, diagonals, midpoint theorem
```
Center: (340, 250), circumradius: 160–180px
Vertices: equally spaced or as specified
```

#### Archetype 8: Tangent-chord configuration
**Triggers:** tangent-chord angle, alternate segment theorem
```
Circle center: (340, 240)
Tangent point: bottom of circle, tangent line horizontal
Chord from tangent point to another point on circle
```

### 2.5 D3 renderer implementation

```typescript
// src/renderers/d3/renderer.ts

function renderGeometry2D(schema: Geometry2DSchema): string {
  // Create a detached SVG element (works in Node via jsdom, or in browser)
  const svg = d3.create("svg")
    .attr("viewBox", "0 0 680 500")
    .attr("xmlns", "http://www.w3.org/2000/svg");

  // Inject styles (CSS variables for light/dark mode)
  svg.append("style").text(getStyleSheet());

  // Defs: arrow marker, clip paths
  const defs = svg.append("defs");
  appendArrowMarker(defs);

  // Compute figure centroid for label offsets
  const centroid = computeCentroid(schema.elements.points);

  // === Render layers, back to front ===

  // Layer 1: Filled polygons
  const fillLayer = svg.append("g").attr("class", "layer-fills");
  for (const poly of schema.elements.polygons ?? []) {
    drawPolygon(fillLayer, resolveVertices(poly, schema), poly.fill);
  }

  // Layer 2: Circles
  const circleLayer = svg.append("g").attr("class", "layer-circles");
  for (const c of schema.elements.circles ?? []) {
    const center = resolvePoint(c.center, schema);
    drawCircle(circleLayer, center, c.radius, c.style);
  }

  // Layer 3: Construction lines (dashed)
  const constructionLayer = svg.append("g").attr("class", "layer-construction");
  for (const seg of (schema.elements.segments ?? []).filter(s => s.style === "dashed")) {
    const [from, to] = resolveSegment(seg, schema);
    drawSegment(constructionLayer, from, to, { dashed: true, label: seg.label });
  }

  // Layer 4: Solid edges
  const edgeLayer = svg.append("g").attr("class", "layer-edges");
  for (const seg of (schema.elements.segments ?? []).filter(s => s.style === "solid")) {
    const [from, to] = resolveSegment(seg, schema);
    drawSegment(edgeLayer, from, to, { dashed: false, label: seg.label });
  }

  // Layer 5: Infinite lines
  const lineLayer = svg.append("g").attr("class", "layer-lines");
  for (const line of schema.elements.lines ?? []) {
    drawInfiniteLine(lineLayer, line, schema);
  }

  // Layer 6: Angle arcs
  const arcLayer = svg.append("g").attr("class", "layer-arcs");
  for (const arc of schema.elements.arcs ?? []) {
    const center = resolvePoint(arc.center, schema);
    drawArc(arcLayer, center, arc.radius, arc.startAngle, arc.endAngle, arc.label);
  }

  // Layer 7: Right-angle markers
  for (const marker of schema.elements.rightAngleMarkers ?? []) {
    const [v, r1, r2] = resolveRightAngle(marker, schema);
    drawRightAngle(arcLayer, v, r1, r2);
  }

  // Layer 8: Points (on top)
  const pointLayer = svg.append("g").attr("class", "layer-points");
  for (const pt of schema.elements.points) {
    drawPoint(pointLayer, { x: pt.x, y: pt.y }, pt.label, pt.style, centroid);
  }

  // Layer 9: Annotations
  const annotationLayer = svg.append("g").attr("class", "layer-annotations");
  for (const ann of schema.elements.annotations ?? []) {
    drawAnnotation(annotationLayer, { x: ann.x, y: ann.y }, ann.text);
  }

  // === Interactivity (if requested) ===
  if (schema.interactive?.draggable?.length) {
    attachDragBehavior(svg, schema);
  }

  // Serialize to string (for file output or embedding)
  return svg.node().outerHTML;
}
```

### 2.6 Interactivity features (D3-powered)

These are capabilities that raw SVG can't provide. Each is optional — the schema's `interactive` field controls what's enabled.

#### Draggable points
```typescript
function attachDragBehavior(svg: Selection, schema: Schema) {
  const draggableIds = schema.interactive.draggable;

  for (const id of draggableIds) {
    const pointEl = svg.select(`[data-id="${id}"]`);

    const drag = d3.drag()
      .on("drag", (event) => {
        // Constrain to circle if point is on a circle
        const constraint = getConstraint(id, schema);
        let newPos = { x: event.x, y: event.y };

        if (constraint?.type === "on-circle") {
          newPos = projectOntoCircle(newPos, constraint.center, constraint.radius);
        }

        // Update point position
        updatePoint(svg, id, newPos, schema);

        // Recompute dependent elements (segments, arcs, labels)
        recomputeDependents(svg, id, schema);
      });

    pointEl.call(drag);
  }
}
```

**Use case:** "Move point C around the circle and observe how angle ACB changes." The student drags C, the angle arc and label update in real time.

#### Animated construction steps
```typescript
function animateConstruction(svg: Selection, schema: Schema) {
  const steps = schema.interactive.constructionSteps;
  let currentStep = 0;

  // Initially hide all elements
  svg.selectAll("[data-step]").style("opacity", 0);

  function showStep(n: number) {
    svg.selectAll(`[data-step="${n}"]`)
      .transition()
      .duration(600)
      .style("opacity", 1);
  }

  // Step controls (next/prev buttons below the SVG)
  // ...
}
```

**Use case:** "Step through the proof — first draw the triangle, then the circumscribed circle, then the perpendicular bisectors."

#### Hover tooltips
```typescript
// Hover over a vertex to see its coordinates
// Hover over a segment to see its length
// Hover over an angle arc to see its measure
```

Built with D3's `.on("mouseenter", ...).on("mouseleave", ...)` — no library needed.

### 2.7 Style system

Same palette as before, but now injected as a `<style>` block inside the SVG:

```css
:root {
  --geo-primary: #5b4dc7;
  --geo-primary-fill: rgba(91, 77, 199, 0.08);
  --geo-highlight: #d85a30;
  --geo-construction: #888780;
  --geo-angle: #ba7517;
  --geo-green: #0f6e56;
  --geo-text: #2c2c2a;
  --geo-annotation: #5f5e5a;
}

@media (prefers-color-scheme: dark) {
  :root {
    --geo-primary: #b8a9ff;
    --geo-primary-fill: rgba(184, 169, 255, 0.1);
    --geo-highlight: #ff6b4a;
    --geo-construction: #b4b2a9;
    --geo-angle: #ef9f27;
    --geo-green: #4ae0b0;
    --geo-text: #e8e6df;
    --geo-annotation: #b4b2a9;
  }
}

.edge-solid { stroke: var(--geo-primary); stroke-width: 1.5; }
.edge-dashed { stroke: var(--geo-construction); stroke-width: 0.8;
               stroke-dasharray: 5 3; }
.circle-primary { stroke: var(--geo-primary); stroke-width: 1; fill: none; }
.vertex { fill: var(--geo-primary); }
.vertex-highlight { fill: var(--geo-highlight); }
.label { font: 500 14px "Segoe UI", system-ui, sans-serif;
         fill: var(--geo-text); }
.angle-arc { stroke: var(--geo-angle); stroke-width: 1.2; fill: none; }
.angle-label { font: 400 12px "Segoe UI", system-ui, sans-serif;
               fill: var(--geo-angle); }
.annotation { font: 400 12px "Segoe UI", system-ui, sans-serif;
              fill: var(--geo-annotation); }
.draggable { cursor: grab; }
.draggable:active { cursor: grabbing; }
```

### 2.8 Post-processing validation

Identical logic to the previous plan, but now runs on the parsed schema before D3 rendering:

```typescript
function validateSchema(schema: Geometry2DSchema): ValidationResult {
  const issues: Issue[] = [];

  // 1. Bounds check — all points inside safe area
  for (const point of schema.elements.points) {
    if (point.x < 20 || point.x > 660 || point.y < 20 || point.y > 480) {
      issues.push({ type: 'out-of-bounds', element: point.id });
    }
  }

  // 2. Label overlap detection (estimate bounding boxes from text length)
  const labels = computeLabelBoundingBoxes(schema);
  for (let i = 0; i < labels.length; i++) {
    for (let j = i + 1; j < labels.length; j++) {
      if (boxesOverlap(labels[i], labels[j])) {
        issues.push({ type: 'label-overlap',
          elements: [labels[i].id, labels[j].id] });
      }
    }
  }

  // 3. Points on circle within 2px tolerance
  // 4. Arc sweep < 180° (unless explicitly reflex)
  // 5. Label-on-edge detection
  // ... (same as before)

  return { valid: issues.length === 0, issues, autoFixes: computeFixes(issues) };
}
```

Auto-fixes (nudge labels, re-center figure) are applied deterministically. Geometric errors trigger an LLM retry with the specific issue.

### 2.9 Export pipeline

| Format | Method | When to use |
|--------|--------|-------------|
| Interactive HTML | D3 renders in-browser, self-contained HTML with `<script src="d3 CDN">` | Chat widget, web app |
| Static SVG | `svg.node().outerHTML` — extract the SVG string after D3 renders | Embed in markdown, docs |
| PNG | resvg (fast, no browser) or Puppeteer (handles dark mode CSS) | Messaging, documents |

For the interactive HTML output:

```html
<!DOCTYPE html>
<html>
<head>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js"></script>
  <style>/* geo styles + dark mode */</style>
</head>
<body>
  <div id="diagram"></div>
  <script>
    const schema = /* embedded JSON */;
    renderGeometry2D(schema, d3.select("#diagram"));
  </script>
</body>
</html>
```

### 2.10 File structure

```
src/
  math/
    geometry.ts             ← Pure math: pointOnCircle, tangentPoints, intersect, etc.
    labelLayout.ts          ← Label offset, collision detection, nudge logic

  renderers/
    d3/
      renderer.ts           ← renderGeometry2D(schema) → SVG string or live DOM
      primitives.ts         ← drawCircle, drawArc, drawSegment, etc. (D3 selections)
      interactivity.ts      ← drag behaviors, animation steps, hover tooltips
      styles.ts             ← CSS class definitions, dark mode variables
      export.ts             ← SVG → HTML wrapper, SVG → PNG

    threejs/
      renderer.ts           ← renderGeometry3D(schema) → HTML string
      boilerplate.ts        ← scene, camera, lights, controls template
      primitives.ts         ← sphere, edge, label, plane, solid helpers
      export.ts             ← Puppeteer frame capture → GIF/MP4

  schema/
    types.ts                ← GeometryScene (discriminated union on type)
    validator.ts            ← Post-processing validation + auto-fix
    archetypes.ts           ← Default coordinates for 8 archetype templates
```

---

## Phase 3: The 3D renderer (Three.js)

A single function: `renderGeometry3D(schema) → HTML string`.

### Technology

Three.js loaded from CDN. The output is a self-contained HTML file with inline JavaScript — no build step.

### Implementation outline

```
render3D(schema):
    html = boilerplate(threeJsCDN, styles, legend)

    script = setupScene(background=schema.background, camera=schema.camera)
    script += addLights()
    script += addGrid(schema.grid)

    for plane in schema.planes:
        script += addTranslucentPlane(plane)

    for solid in schema.solids:
        script += addSolid(solid)    // cone, cylinder, sphere

    for face in schema.faces:
        script += addFace(vertices, color, opacity)

    for edge in schema.edges:
        script += addEdge(from, to, color, dashed?)

    for point in schema.points:
        script += addSphere(position, color, radius)
        script += addLabel(text, position, color)

    for arc in schema.arcs:
        script += addAngleArc3D(center, vec1, vec2, radius)

    for control in schema.controls:
        html += addSlider(control) or addToggle(control)

    script += orbitControls(autoRotate=schema.autoRotate)
    script += resizeHandler()
    script += animationLoop()

    return html + script
```

### Key design decisions

- **No build step.** Output is a single `.html` file. Three.js loaded via `<script src="cdnjs...">`. Everything self-contained.
- **Orbit controls are hand-rolled** (~40 lines: pointer events + wheel). Avoids importing OrbitControls separately.
- **Labels as canvas sprites.** `<canvas>` → `fillText` → `CanvasTexture` → `Sprite`. Always faces camera.
- **Dashed lines** via `THREE.LineDashedMaterial` + `computeLineDistances()`.
- **Background color is configurable** — schema `"background"` field. UI text colors auto-adapt.
- **Interactive controls** (sliders, toggles) specified in schema `"controls"` array. Each control calls a JS function that updates the scene (e.g., move a cutting plane, toggle flames).
- **3D solids** rendered via `THREE.ConeGeometry`, `THREE.CylinderGeometry`, `THREE.SphereGeometry` with translucent `MeshPhongMaterial`.
- **`setRotation(degrees)`** exposed globally for GIF export frame capture.

### File structure

```
src/
  renderers/
    threejs/
      renderer.ts           ← renderGeometry3D(schema) → HTML string
      boilerplate.ts        ← scene, camera, lights, controls template
      primitives.ts         ← sphere, edge, label, plane, solid helpers
      export.ts             ← Puppeteer frame capture → GIF/MP4
```

---

## Phase 4: The LLM layer (the brain)

This is where the real intelligence lives. The LLM must:

1. **Parse** the geometry question into structured facts
2. **Classify** as 2D or 3D
3. **Solve** the geometry (compute angles, lengths, coordinates)
4. **Select** an archetype (for 2D) or camera angle (for 3D)
5. **Decide** interactivity (what's draggable? animated? slider-controlled?)
6. **Emit** a valid geometry JSON schema

### System prompt design

```
You are a geometry visualization engine. Given a math geometry
question, you must:

1. Identify all geometric objects and their relationships.
2. Classify as 2D or 3D.
3. Solve for unknown values (angles, lengths, coordinates).
4. For 2D: select the closest archetype, compute (x, y) coordinates
   in a 680×500 viewport, and decide which points should be
   draggable (if the problem benefits from exploration).
5. For 3D: compute (x, y, z) coordinates in real units (cm),
   centered at origin, and decide if any interactive controls
   (sliders, toggles) would help the student explore.
6. Output a JSON object matching the GeometryScene schema.

## 2D coordinate rules
- Viewport: 680 × 500. Safe area: x=40..640, y=40..460.
- Center primary shape at (340, 250). Fill 60–70% of viewport.
- Labels 16–20px from vertices, away from figure centroid.
- Archetype templates: [listed with default coords]

## 3D coordinate rules
- Real units (cm). Center at origin. Base on xz-plane (y=0).
- Set background: "#ffffff" (default) or "#1a1a2e".

## Interactivity rules
- Mark a point as draggable if moving it would help illustrate
  the theorem (e.g., moving C on a circle to show inscribed angle
  is constant).
- Add a slider for 3D if a cross-section or parameter sweep is
  relevant (e.g., cutting plane height).
- Default: no interactivity. Only add it when it genuinely helps.

## Style rules
- Primary: #5b4dc7 (light) / #b8a9ff (dark)
- Highlight: #d85a30 (light) / #ff6b4a (dark)
- Construction: dashed, gray. Angles: amber. Right angle: 12px square.

Output ONLY valid JSON. No explanation.
```

### Classification heuristic

| Keywords present                          | Classification |
|-------------------------------------------|----------------|
| pyramid, prism, cone, sphere, cube, tetrahedron, 3D solid names | 3D |
| "height above", "perpendicular to plane", "slant height", "dihedral" | 3D |
| circle, tangent, chord, arc, inscribed, cyclic, triangle (flat) | 2D |
| Everything else | 2D (default) |

### Pipeline: question → schema → render

```
Question
    │
    ▼  Claude API call (system prompt + question)
    │
    ▼  JSON schema (type: "2d" or "3d")
    │
    ├─ validate(schema)
    │   ├─ pass → render
    │   └─ fail → auto-fix if possible, else retry LLM with error details
    │
    ├─ type: "2d" → renderGeometry2D(schema) → interactive SVG / HTML
    │
    └─ type: "3d" → renderGeometry3D(schema) → interactive HTML
```

---

## Phase 5: GIF export (for 3D scenes)

For contexts where an interactive HTML isn't suitable.

### Pipeline

```
HTML file
    │
    ▼  Puppeteer (headless Chrome)
    │  - Load HTML, wait for Three.js init
    │  - Call setRotation(0°), screenshot
    │  - Call setRotation(6°), screenshot
    │  - ... 60 frames total
    │
    ▼  gifski -o output.gif --fps 20 frame_*.png
    │
    ▼
  output.gif (3-second loop, ~2-4MB)
```

Requirements: the 3D HTML template exposes `window.setRotation(degrees)`. Frame count: 60 at 20fps = 3s smooth loop.

---

## Phase 6: End-to-end API

### Option A: As a library (Node.js)

```typescript
import { generateDiagram } from 'geometry-viz';

const result = await generateDiagram({
  question: "Two tangents PA and PB are drawn from external point P...",
  format: 'svg',        // 'svg' | 'png' | 'html' | 'gif'
  theme: 'light',       // 'light' | 'dark'
  interactive: true,    // enable draggable points / animation
  apiKey: process.env.ANTHROPIC_API_KEY
});

// result.answer   → "PA = 6√3 cm"
// result.file     → Buffer (SVG/PNG/HTML/GIF)
// result.schema   → The intermediate JSON for debugging
// result.type     → "2d" | "3d"
```

### Option B: As a web app

```
┌─────────────────────────────────────────────────────┐
│  Geometry Visualizer                                │
│                                                     │
│  ┌───────────────────────────────────────────────┐  │
│  │ Enter your geometry question...               │  │
│  └───────────────────────────────────────────────┘  │
│                                                     │
│  [Generate]                                         │
│                                                     │
│  ┌───────────────────────────────────────────────┐  │
│  │                                               │  │
│  │    ← interactive diagram renders here →       │  │
│  │    (D3 SVG for 2D / Three.js for 3D)         │  │
│  │                                               │  │
│  └───────────────────────────────────────────────┘  │
│                                                     │
│  Answer: PA = 6√3 cm ≈ 10.39 cm                   │
│                                                     │
│  💡 Try dragging point C around the circle!         │
│                                                     │
│  [Download SVG] [Download PNG] [Download HTML]      │
└─────────────────────────────────────────────────────┘
```

### Tech stack

| Layer      | Technology                            |
|------------|---------------------------------------|
| Frontend   | React + Tailwind (or plain HTML)      |
| API        | Node.js / Express (or serverless)     |
| LLM        | Claude API (Sonnet for speed, Opus for accuracy) |
| 2D render  | D3.js (v7, from CDN)                 |
| 3D render  | Three.js (r128, from CDN)            |
| Shared math| Pure TS geometry library (no deps)    |
| GIF export | Puppeteer + gifski (server-side)      |

---

## Phase 7: Handling edge cases and advanced geometry

### Geometry types to support

| Category                    | Examples                                        | Renderer | Archetype | Interactive |
|-----------------------------|-------------------------------------------------|----------|-----------|-------------|
| Circle theorems             | Tangent-chord, inscribed angles, cyclic quads   | D3 (2D)  | 1, 2, 8  | Drag point on circle |
| Triangle geometry           | Medians, altitudes, circumcircle, incircle      | D3 (2D)  | 3         | Drag vertex |
| Parallel lines + transversal| Corresponding angles, alternate angles          | D3 (2D)  | 4         | Drag transversal angle |
| Coordinate geometry         | Distance, midpoint, slope, line equations        | D3 (2D)  | 6         | Drag point, see coords |
| Locus problems              | Parabola, ellipse, set of points                | D3 (2D)  | 6         | Animate point, trace |
| Quadrilateral properties    | Parallelogram, rhombus, kite, trapezoid         | D3 (2D)  | 7         | Drag vertex |
| Two-circle problems         | Radical axis, common tangent, intersecting      | D3 (2D)  | 5         | Drag circle radius |
| Pyramids and prisms         | Surface area, slant height, cross-sections      | Three.js | —         | Cut-plane slider |
| Cones and cylinders         | Volume, slant height, unfolding                 | Three.js | —         | Cut-plane slider |
| Spheres                     | Great circles, tangent planes                   | Three.js | —         | Rotate, toggle planes |
| Combined solids             | Hemisphere on cylinder, cone on cube            | Three.js | —         | Explode / toggle parts |
| Vectors in 3D               | Cross product, plane equations, projections     | Three.js | —         | Drag vector endpoint |

### Known hard cases

1. **Curved surfaces in 3D**: Schema's `"solids"` array maps to Three.js geometry constructors. Translucent materials.

2. **Cross-sections of 3D solids**: Translucent solid + colored cross-section polygon + slider to move cutting plane.

3. **Loci and curves in 2D**: D3 makes this easier than raw SVG — use `d3.line().curve(d3.curveBasis)` to draw smooth curves through sampled points. Add `"curves"` element to 2D schema.

4. **Overlapping labels in 2D**: Validator detects and auto-fixes. D3's force simulation (`d3.forceSimulation`) can be used as a last resort to push labels apart without manual coordinate tweaking.

5. **Dynamic 2D problems** ("as point P moves along arc AB..."): D3 drag + constraint system. The point is constrained to the circle, dependent geometry recomputes on each drag event. This is a major advantage of D3 over raw SVG.

6. **Very dense diagrams**: Split into multiple schemas. Or use D3's animated construction steps to reveal layers progressively.

7. **Non-standard orientations**: Archetype provides default, LLM overrides when problem demands it.

---

## Implementation roadmap

| Phase | What                              | Effort    | Dependency | Key deliverable |
|-------|-----------------------------------|-----------|------------|-----------------|
| 1     | Unified JSON schema               | 2–3 days  | None       | TypeScript types + JSON Schema validator |
| 2.1   | Shared math library               | 2 days    | None       | `geometry.ts` — pure functions, no DOM |
| 2.2   | D3 primitives (drawing layer)     | 2 days    | 2.1        | `primitives.ts` — drawCircle, drawArc, etc. |
| 2.3   | D3 renderer (full pipeline)       | 2 days    | 2.2        | `renderGeometry2D()` function |
| 2.4   | Archetype templates               | 1 day     | 1          | `archetypes.ts` with 8 templates |
| 2.5   | Style system + dark mode          | 1 day     | 2.3        | `styles.ts` with CSS variables |
| 2.6   | Interactivity (drag, animate)     | 2 days    | 2.3        | `interactivity.ts` — drag, steps, hover |
| 2.7   | Post-processing validator         | 1 day     | 1          | `validator.ts` with auto-fix |
| 2.8   | 2D export (SVG, PNG, HTML)        | 0.5 days  | 2.3        | `export.ts` |
| 3     | 3D Three.js renderer              | 3–5 days  | 1, 2.1     | `renderGeometry3D()` function |
| 4     | LLM prompt + pipeline             | 3–5 days  | 1          | System prompt + classification + retry |
| 5     | GIF export                        | 1–2 days  | 3          | Puppeteer frame capture script |
| 6     | Web app / API wrapper             | 2–3 days  | 2, 3, 4   | Working end-to-end app |
| 7     | Edge cases + polish               | Ongoing   | 6          | Test against 50+ questions |

**Total MVP: ~3–4 weeks** for a single developer.

**Fast-track MVP: ~1.5 weeks** if you skip interactivity (Phase 2.6), skip GIF export (Phase 5), skip the web app (Phase 6), and use simpler D3 output without drag/animation. You still get the structured pipeline, consistent styling, and validation — just no interactive features.

### Priority order (if time-limited)

1. **Shared math library** — foundation for everything (2 days)
2. **D3 primitives + renderer** — core 2D output (4 days)
3. **Three.js renderer** — core 3D output (4 days)
4. **LLM prompt + pipeline** — ties it together (3 days)
5. **Style system** — visual polish (1 day)
6. **Validator** — catches LLM errors (1 day)
7. **Interactivity** — premium feature, add later (2 days)
8. **Archetypes** — improves LLM accuracy, add later (1 day)

---

## Testing strategy

### Unit tests

- **Shared math:** `pointOnCircle`, `tangentPoints`, `intersectLines` — edge cases for each (degenerate inputs, boundary angles, collinear points).
- **D3 primitives:** Render each primitive in isolation via jsdom, snapshot the SVG output.
- **Validator:** Feed schemas with known issues (overlapping labels, out-of-bounds points), verify detection and auto-fix.
- **Archetypes:** For each archetype, generate a reference schema, render, and confirm visual correctness.

### Integration tests

- **End-to-end:** 50 real geometry questions (25 2D, 25 3D) through the full pipeline. Manually verify each output.
- **Regression suite:** Question → expected schema pairs. Re-run after any prompt or renderer change.
- **Archetype coverage:** At least 5 test questions per archetype.
- **Interactivity:** For each draggable scenario, verify that constraints hold (point stays on circle, angle updates correctly).

### Visual QA checklist

**2D diagrams (D3):**
- [ ] All vertices labeled correctly
- [ ] No overlapping labels
- [ ] Points on circles are visually on the circle (within 2px)
- [ ] Dashed lines for construction / auxiliary
- [ ] Answer highlighted in coral/orange
- [ ] Angle arcs at correct vertices with correct sweep
- [ ] Right-angle markers where applicable
- [ ] Figure centered, 60–70% of viewport
- [ ] Light and dark mode both render correctly
- [ ] Draggable points (if enabled) stay constrained
- [ ] All coordinates within safe area

**3D diagrams (Three.js):**
- [ ] Labels face camera at all angles
- [ ] Smooth auto-rotation
- [ ] Dashed lines for hidden edges
- [ ] Legend matches color coding
- [ ] Sliders/toggles work correctly
- [ ] `setRotation()` works for GIF export
- [ ] Background color matches schema

---

## Cost estimate (per question)

| Component              | Cost               |
|------------------------|--------------------|
| Claude Sonnet API call | ~$0.01–0.03        |
| Claude Opus API call   | ~$0.05–0.15        |
| Validation retry (10% of calls) | ~$0.01   |
| GIF export (server)    | ~$0.001 (compute)  |
| **Total per question** | **~$0.01–0.15**    |

At scale (10,000 questions/day), Sonnet at ~$100–300/day. Opus for complex 3D or when Sonnet's coordinate accuracy falls short.

---

## Dependency summary

| Library | Version | Size (CDN) | Used by | Purpose |
|---------|---------|------------|---------|---------|
| D3.js   | 7.9.0   | ~80KB gzipped | 2D renderer | SVG generation + interactivity |
| Three.js| r128    | ~150KB gzipped | 3D renderer | WebGL 3D scenes |
| resvg   | latest  | N/A (server) | Export | SVG → PNG rasterization |
| Puppeteer| latest | N/A (server) | Export | GIF frame capture, dark-mode PNG |
| gifski  | latest  | N/A (server) | Export | High-quality GIF assembly |

No build tools required for the output files. Both D3 and Three.js load from CDN as a single `<script>` tag.