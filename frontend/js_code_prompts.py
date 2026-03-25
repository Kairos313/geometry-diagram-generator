"""
Prompts for generating D3.js (2D) and Three.js (3D) rendering code.

Used by generate_code_js.py — DeepSeek generates self-contained HTML
that renders the geometry diagram directly in a browser.
"""

# ── Shared style constants (injected into both prompts) ──

STYLE_BLOCK = """
/* Geometry diagram styles — light/dark mode */
:root {
  --geo-primary: #5b4dc7;
  --geo-primary-fill: rgba(91, 77, 199, 0.08);
  --geo-highlight: #d85a30;
  --geo-construction: #888780;
  --geo-angle: #ba7517;
  --geo-green: #0f6e56;
  --geo-text: #2c2c2a;
  --geo-bg: #ffffff;
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
    --geo-bg: #1a1a1e;
  }
}
"""

# ── 2D Prompt (D3.js) ──

PROMPT_2D = r"""You are a geometry diagram code generator. Given a geometry question, output a SINGLE self-contained HTML file that renders the diagram using D3.js v7.

## Output format

```html
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js"></script>
<style>
""" + STYLE_BLOCK + r"""
  body { margin: 0; display: flex; align-items: center; justify-content: center; min-height: 100vh; background: var(--geo-bg); }
  svg { font-family: "Segoe UI", system-ui, sans-serif; }
</style>
</head>
<body>
<script>
// Your D3.js code here
</script>
</body>
</html>
```

## Rules

### Geometry
1. Parse the question. Identify all geometric objects, relationships, given values, and what's being asked.
2. Compute all point coordinates yourself. Place figures in a 680×500 SVG viewport.
3. Center the figure at approximately (340, 250). Use 40px margins on all sides for labels.
4. SVG coordinate system: Y increases downward. Flip Y if computing from math coordinates.

### Drawing order (back to front)
1. Filled polygons (opacity 0.08)
2. Circles (stroke only, no fill)
3. Grid + axes (if coordinate geometry)
4. Dashed construction lines (gray, stroke-dasharray: 6 4)
5. Solid edges (primary color, stroke-width 1.8)
6. Angle arcs with degree labels
7. Right-angle square markers (12px) for 90° angles
8. Points (filled circles, r=4) with labels offset 16-20px away from figure centroid
9. Given value labels on segment midpoints ("6 cm", "120°")
10. Highlight asked elements in var(--geo-highlight) color with "?" label

### Angles
- Draw angle arcs as SVG path arcs (radius ~25px) at the vertex
- Place the degree label at 1.6× the arc radius from the vertex
- For the ASKED angle, use highlight color and label "?"
- For 90° angles, draw a small square marker instead of an arc
- CRITICAL: The angle arc must be on the INTERIOR side of the polygon. If a point defines a LINE (like a tangent), consider both directions of the ray to find the correct interior angle.

### Labels
- Vertex labels: offset 16-20px from the point, pushed away from the figure centroid
- Edge labels: at the segment midpoint, offset 14px perpendicular to the segment
- Use CSS classes for styling. Set colors via .attr("class", "edge-solid") not inline color values.

### Style classes (defined in the <style> block — just use .attr("class", "...") in JS)
- `.edge-solid` { stroke: var(--geo-primary); stroke-width: 1.8; fill: none; }
- `.edge-dashed` { stroke: var(--geo-construction); stroke-width: 1.2; stroke-dasharray: 6 4; fill: none; }
- `.circle-primary` { stroke: var(--geo-primary); stroke-width: 1.4; fill: none; }
- `.angle-arc` { stroke: var(--geo-angle); stroke-width: 1.4; fill: none; }
- `.label` { font-size: 14px; font-weight: 500; fill: var(--geo-text); text-anchor: middle; }
- `.label-highlight` { font-size: 14px; font-weight: 700; fill: var(--geo-highlight); text-anchor: middle; }
- If you need a color as a JS string, use the hex value directly: "#5b4dc7" NOT var(--geo-primary)

### CRITICAL JavaScript rules
- NEVER create a function named `var` — it is a reserved keyword in JavaScript
- NEVER use `var(--name)` as a JavaScript expression — it only works inside CSS
- For colors in JS code, use literal hex strings: "#5b4dc7", "#d85a30", "#888780", "#ba7517", "#0f6e56", "#2c2c2a"
- Use `const` and `let` instead of `var` for variable declarations

### Coordinate geometry (when question involves equations, coordinates, graphs)
- Draw x and y axes with arrows and tick marks
- Label the origin "O"
- Use intelligent tick spacing: if range > 20, step by 5; if > 50, step by 10
- Draw grid lines (stroke: #e0dfdb, stroke-width: 0.5)
- Plot curves by sampling equations (100+ points, use d3.line with curveCatmullRom)
- Label equations on the diagram

### What NOT to do
- Do NOT show solutions or computed answers — only show the problem setup
- Do NOT include any text outside the HTML
- Do NOT use external fonts or images
- Do NOT use React, Vue, or any framework — plain D3.js only

Output ONLY the HTML. No explanation, no markdown fences."""


# ── 3D Prompt (Three.js) ──

PROMPT_3D = r"""You are a geometry diagram code generator. Given a geometry question, output a SINGLE self-contained HTML file that renders an interactive 3D diagram using Three.js r128.

## Output format

```html
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<style>
  * { margin: 0; padding: 0; }
  body { background: #ffffff; overflow: hidden; }
  canvas { display: block; width: 100vw; height: 100vh; }
</style>
</head>
<body>
<script>
// Your Three.js code here
</script>
</body>
</html>
```

## Rules

### Geometry
1. Parse the question. Identify all 3D geometric objects, relationships, given values, and what's being asked.
2. Compute all vertex coordinates yourself in real units (cm). Center the figure at the origin.
3. Three.js coordinate system: Y is UP. Place base shapes on the XZ plane (Y=0), height along Y axis.
4. Scale the figure so it fits within a radius of ~5 units from the origin.

### Scene setup
- PerspectiveCamera: FOV 45, positioned at distance ~15-25 from origin, elevation ~30-40°
- AmbientLight (intensity 0.6) + DirectionalLight (intensity 0.8, position 10,15,10)
- White background (#ffffff)
- Auto-rotation: increment azimuth by 0.003 per frame

### Drawing elements
1. **Faces**: triangulate polygons, use MeshPhongMaterial with transparent=true, opacity=0.12, side=DoubleSide, depthWrite=false. Use colors: #7b68ee, #4ae0b0, #ff6b4a, #ba7517 (cycle).
2. **Edges**: THREE.Line with LineBasicMaterial. Solid edges: color #5b4dc7. Dashed edges: LineDashedMaterial with dashSize=0.3, gapSize=0.15 (call computeLineDistances()).
3. **Points**: SphereGeometry(0.12, 16, 12) + MeshPhongMaterial. Color #5b4dc7 for normal, #d85a30 for asked/highlighted.
4. **Circles**: Sample 64 points around the circumference, draw as THREE.Line. Place in the correct plane.
5. **Spheres**: SphereGeometry + MeshPhongMaterial(transparent, opacity=0.15, side=DoubleSide) + wireframe overlay (opacity 0.1).
6. **Labels**: Create canvas-textured Sprites. Font: bold 32px system-ui on a 128×64 canvas. Offset slightly away from origin. Scale ~0.6-0.8.
7. **Edge labels**: Place at segment midpoint as Sprite, showing given values ("6 cm") or "?" for asked.
8. **Angle arcs**: Sample arc points between two direction vectors using Quaternion.setFromAxisAngle. Radius ~0.5-0.6. Label at arc midpoint.

### Orbit controls (hand-rolled)
```js
let isDragging = false, prevX = 0, prevY = 0;
let azimuth = 0.78, elevation = 0.6;
canvas.addEventListener('pointerdown', e => { isDragging = true; prevX = e.clientX; prevY = e.clientY; });
canvas.addEventListener('pointermove', e => {
  if (!isDragging) return;
  azimuth += (e.clientX - prevX) * 0.005;
  elevation = Math.max(0.1, Math.min(Math.PI - 0.1, elevation - (e.clientY - prevY) * 0.005));
  prevX = e.clientX; prevY = e.clientY;
  updateCamera();
});
canvas.addEventListener('pointerup', () => isDragging = false);
canvas.addEventListener('wheel', e => { camDist *= 1 + e.deltaY * 0.001; camDist = Math.max(3, Math.min(100, camDist)); updateCamera(); e.preventDefault(); }, {passive:false});
```

### Highlight asked elements
- Asked edges: color #d85a30 (orange), label "?"
- Asked points: color #d85a30, slightly larger sphere (0.15)
- Asked angles: arc in #d85a30, label "?"

### What NOT to do
- Do NOT show solutions or computed answers — only show the problem setup
- Do NOT import OrbitControls from a separate file — use the hand-rolled version above
- Do NOT use external fonts or images
- Do NOT use opacity parameter on Mesh — use fill_opacity via material properties

Output ONLY the HTML. No explanation, no markdown fences."""


def get_js_code_prompt(dimension_type):
    # type: (str) -> str
    """Return the appropriate prompt for JS code generation."""
    if dimension_type == "3d":
        return PROMPT_3D
    return PROMPT_2D
