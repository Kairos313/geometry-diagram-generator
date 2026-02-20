#!/usr/bin/env python3
"""
Individual Prompts for Each Dimension Type

This module contains specialized prompts for both stages of the geometry diagram pipeline:

STAGE 1 - Question → Blueprint:
  4-way (legacy): Question_to_Blueprint_2D, _3D, _Coordinate_2D, _Coordinate_3D
  2-way (adaptive, preferred): Question_to_Blueprint_2D_Adaptive, _3D_Adaptive
    - dimension output is always "2d" or "3d"
    - axes decision (true/false) is made internally based on question content

STAGE 2 - Blueprint → Code:
  4-way (legacy): Blueprint_to_Code_2D_DeepSeek, _3D_DeepSeek, _Coordinate_2D, _Coordinate_3D
  2-way (adaptive, preferred): Blueprint_to_Code_2D_Adaptive, _3D_Adaptive
    - reads blueprint["axes"] to branch between traditional and coordinate rendering

Helper functions:
  Legacy: get_prompt_for_dimension(dim)       → Stage 1, 4-way
          get_code_prompt_for_dimension(dim)  → Stage 2, 4-way
  Adaptive: get_adaptive_blueprint_prompt(dim)  → Stage 1, 2-way ("2d"/"3d" only)
            get_adaptive_code_prompt(dim)        → Stage 2, 2-way ("2d"/"3d" only)
"""

# ======================================================================
# TRADITIONAL 2D GEOMETRY (no coordinate system)
# ======================================================================

Question_to_Blueprint_2D = """You are a geometry blueprint generator. Convert this 2D geometry question to JSON.

IMPORTANT: Traditional 2D geometry (NO axes). Place first point at origin, first edge along +X axis.

Output ONLY this JSON structure:
{
  "dimension": "2d",
  "axes": false,
  "scale": {"reference": "AB", "real": "10 cm", "units": 5.0},
  "points": {"A": [0.0, 0.0, 0.0], "B": [5.0, 0.0, 0.0]},
  "lines": [{"id": "line_AB", "from": "A", "to": "B"}],
  "circles": [{"id": "circle_O", "center": "O", "radius": 3.0}],
  "arcs": [{"id": "arc_AB", "center": "O", "from": "A", "to": "B"}],
  "faces": [{"id": "face_ABC", "points": ["A", "B", "C"]}],
  "angles": [{"id": "angle_ABC", "vertex": "B", "p1": "A", "p2": "C", "value": 90.0}],
  "given": {"line_AB": "10 cm", "angle_ABC": "90°"},
  "asked": ["angle_XYZ"]
}

Rules:
- All points: [X, Y, 0.0] with Z=0
- Scale: map first length to 5.0 units
- Hidden lines: add "style": "dashed"
- Compute all coordinates using geometry/trig
- "given": only explicit question data
- "asked": elements to find (will show "?")
"""

# ======================================================================
# TRADITIONAL 3D GEOMETRY (no coordinate system)
# ======================================================================

Question_to_Blueprint_3D = """You are a 3D geometry blueprint generator. Convert this 3D geometry question to JSON.

IMPORTANT: Traditional 3D geometry (NO axes). Base on XY-plane (Z=0), height in +Z direction.

Output ONLY this JSON structure:
{
  "dimension": "3d",
  "axes": false,
  "scale": {"reference": "AB", "real": "8 cm", "units": 4.0},
  "points": {"A": [4.0, 0.0, 0.0], "B": [0.0, 0.0, 0.0], "V": [0.0, 0.0, 5.0]},
  "lines": [{"id": "line_AB", "from": "A", "to": "B"}, {"id": "line_VA", "from": "V", "to": "A", "style": "dashed"}],
  "circles": [{"id": "circle_base", "center": "O", "radius": 4.0}],
  "faces": [{"id": "face_ABC", "points": ["A", "B", "C"]}, {"id": "face_VAB", "points": ["V", "A", "B"]}],
  "angles": [{"id": "angle_ABC", "vertex": "B", "p1": "A", "p2": "C", "value": 90.0}],
  "given": {"line_AB": "8 cm", "line_height": "10 cm"},
  "asked": ["line_VA"]
}

Rules:
- All points: [X, Y, Z]
- Scale: map first length to 4-5 units
- Hidden edges: add "style": "dashed"
- Faces: list points in CCW order (right-hand rule)
- Compute coordinates using 3D geometry
- "given": only explicit question data
- "asked": elements to find (will show "?")
"""

# ======================================================================
# 2D COORDINATE GEOMETRY (with coordinate axes and equations)
# ======================================================================

Question_to_Blueprint_Coordinate_2D = """
You are a computational geometry engine. Analyze the 2D coordinate geometry question and output a **minimal JSON blueprint**.

**IMPORTANT**: This is 2D COORDINATE geometry (WITH axes, WITH equations). Use exact coordinates from the question.

## Output Format

Return ONLY a valid JSON object:

{
  "dimension": "2d",
  "axes": true,
  "grid": true,
  "coordinate_range": {"x_min": -2.0, "x_max": 10.0, "y_min": -2.0, "y_max": 8.0},
  "scale": {"reference": "auto", "real": "1 unit", "units": 1.0},
  "points": {
    "A": [2.0, 3.0, 0.0],
    "B": [6.0, -1.0, 0.0],
    "O": [0.0, 0.0, 0.0]
  },
  "lines": [
    {"id": "line_AB", "from": "A", "to": "B"},
    {"id": "x_axis", "from": "origin", "to": "x_positive", "style": "axis"},
    {"id": "y_axis", "from": "origin", "to": "y_positive", "style": "axis"}
  ],
  "circles": [
    {"id": "circle_C", "center": "C", "radius": 5.0}
  ],
  "curves": [
    {"id": "parabola_1", "equation": "y = x^2 - 4*x + 3", "type": "parametric"}
  ],
  "faces": [
    {"id": "region_feasible", "points": ["P1", "P2", "P3", "P4"], "style": "shaded"}
  ],
  "angles": [
    {"id": "angle_ABC", "vertex": "B", "p1": "A", "p2": "C", "value": 45.0}
  ],
  "given": {
    "point_A": "A(2, 3)",
    "line_L1": "y = 2x + 1"
  },
  "asked": ["point_intersection", "equation_line"]
}

## Rules

1. **dimension**: Always "2d"
2. **axes**: Always true (coordinate axes WILL be shown)
3. **grid**: true for showing grid lines (optional, use based on question context)
4. **coordinate_range**: Determine appropriate x/y ranges to show all geometry with some padding
5. **scale**: Use exact coordinates from question, then determine auto-scale to fit viewing window
   - Start with units=1.0 (1:1 mapping)
   - If coordinates are very large (>100) or very small (<0.1), adjust scale factor
   - Reference "auto" means automatic scaling
6. **points**: Use EXACT coordinates from question as [X, Y, 0.0]
7. **lines**: Segments, axes, equations of lines
8. **circles**: Use exact center and radius from question
9. **curves**: For parabolas, ellipses, hyperbolas, parametric curves, etc.
   - Include equation string for reference
10. **faces**: For shaded regions (feasible regions, areas under curves, etc.)
11. **angles**: Angles that need marking
12. **given**: Map to original coordinate/equation notation
13. **asked**: Elements to find and highlight

## Coordinate Computation

- Use EXACT coordinates from question text
- For points like A(2, 3), use [2.0, 3.0, 0.0]
- For equations like "y = 2x + 1", compute intersection/key points
- Origin is at [0.0, 0.0, 0.0]
- Calculate appropriate coordinate_range to fit all geometry with ~10% padding
- If final range is too large (>50 units) or too small (<5 units), adjust scale

## Auto-Scaling Logic

1. Collect all point coordinates
2. Find min/max for X and Y
3. Add 10-20% padding
4. If range > 50, scale down (units < 1.0)
5. If range < 5, scale up (units > 1.0)
6. Target viewing window: ~20-40 units in largest dimension

## Critical Rules

- Output ONLY the JSON object, no other text
- All coordinates must be numbers (floats), not strings
- Use EXACT coordinates from question, don't normalize to origin
- coordinate_range determines the viewing window
- Axes and grid WILL be rendered
- Element IDs: line_AB, circle_C, curve_parabola1, region_feasible
"""

# ======================================================================
# 3D COORDINATE GEOMETRY (with 3D axes and equations)
# ======================================================================

Question_to_Blueprint_Coordinate_3D = """
You are a computational geometry engine. Analyze the 3D coordinate geometry question and output a **minimal JSON blueprint**.

**IMPORTANT**: This is 3D COORDINATE geometry (WITH 3D axes, WITH equations). Use exact coordinates from the question.

## Output Format

Return ONLY a valid JSON object:

{
  "dimension": "3d",
  "axes": true,
  "grid": false,
  "coordinate_range": {"x_min": -2.0, "x_max": 6.0, "y_min": -2.0, "y_max": 5.0, "z_min": -1.0, "z_max": 8.0},
  "scale": {"reference": "auto", "real": "1 unit", "units": 1.0},
  "points": {
    "A": [1.0, 2.0, 3.0],
    "B": [4.0, 0.0, 1.0],
    "O": [0.0, 0.0, 0.0]
  },
  "lines": [
    {"id": "line_AB", "from": "A", "to": "B"},
    {"id": "x_axis", "from": "origin", "to": "x_positive", "style": "axis"},
    {"id": "y_axis", "from": "origin", "to": "y_positive", "style": "axis"},
    {"id": "z_axis", "from": "origin", "to": "z_positive", "style": "axis"}
  ],
  "planes": [
    {"id": "plane_ABC", "equation": "2x + y - z = 4", "points": ["A", "B", "C"], "normal": [2.0, 1.0, -1.0]}
  ],
  "spheres": [
    {"id": "sphere_S1", "center": "C", "radius": 5.0, "equation": "(x-2)^2 + (y-1)^2 + (z-3)^2 = 25"}
  ],
  "vectors": [
    {"id": "vector_AB", "from": "A", "to": "B", "components": [3.0, -2.0, -2.0]}
  ],
  "faces": [
    {"id": "face_plane_section", "points": ["P1", "P2", "P3", "P4"]}
  ],
  "angles": [
    {"id": "angle_dihedral", "vertex": "line_intersection", "p1": "normal1", "p2": "normal2", "value": 60.0}
  ],
  "given": {
    "point_A": "A(1, 2, 3)",
    "plane_P1": "2x + y - z = 4",
    "sphere_S1": "(x-2)^2 + (y-1)^2 + (z-3)^2 = 25"
  },
  "asked": ["point_intersection", "distance", "angle_dihedral"]
}

## Rules

1. **dimension**: Always "3d"
2. **axes**: Always true (3D coordinate axes WILL be shown: X, Y, Z)
3. **grid**: Usually false for 3D (optional grid on base XY plane)
4. **coordinate_range**: Determine appropriate x/y/z ranges to show all geometry with padding
5. **scale**: Use exact coordinates from question, then auto-scale to fit
   - Start with units=1.0
   - Adjust if coordinates are very large or very small
6. **points**: Use EXACT coordinates as [X, Y, Z]
7. **lines**: Segments, axes, edges
8. **planes**: Plane equations with normal vectors
   - Include equation string
   - List defining points if available
   - Include normal vector components
9. **spheres**: Use exact center and radius
   - Include equation string
10. **vectors**: Direction vectors, normal vectors
    - Store as from/to points or as components
11. **faces**: For plane sections, intersections, etc.
12. **angles**: Dihedral angles, angles between vectors/planes
13. **given**: Map to original notation
14. **asked**: Elements to find and highlight

## Coordinate Computation

- Use EXACT coordinates from question text
- For points like A(1, 2, 3), use [1.0, 2.0, 3.0]
- For plane equations, extract normal vector and defining points
- For spheres, extract center and radius from equation
- Origin at [0.0, 0.0, 0.0]
- Calculate appropriate coordinate_range for all dimensions (X, Y, Z)
- Add ~15% padding to ranges

## Auto-Scaling Logic (3D)

1. Collect all point coordinates
2. Find min/max for X, Y, and Z
3. Add 15-20% padding to each dimension
4. If any range > 50, scale down
5. If all ranges < 5, scale up
6. Target viewing box: ~20-40 units in largest dimension
7. Maintain aspect ratio for coordinate system

## Critical Rules

- Output ONLY the JSON object, no other text
- All coordinates must be numbers (floats), not strings
- Use EXACT coordinates from question, don't normalize to origin
- coordinate_range determines the 3D viewing volume
- 3D axes (X, Y, Z) WILL be rendered
- Element IDs: line_AB, plane_P1, sphere_S1, vector_d, face_section
- Planes use normal vectors for orientation
- Vectors can be represented as points (from→to) or components
"""


# ======================================================================
# STAGE 2 (DEEPSEEK): JSON Blueprint → 2D Matplotlib Code
# ======================================================================

Blueprint_to_Code_2D_DeepSeek = """
You are a Python visualization expert. Convert a JSON geometry blueprint into a matplotlib script.

## Input Format

You receive a JSON blueprint:
```json
{
  "dimension": "2d",
  "scale": {"reference": "AB", "real": "12 cm", "units": 5.0},
  "points": {"A": [0, 0, 0], "B": [5, 0, 0], "C": [2.5, 4.33, 0]},
  "lines": [{"id": "line_AB", "from": "A", "to": "B"}, ...],
  "circles": [{"id": "circle_O", "center": "O", "radius": 3.5}],
  "faces": [{"id": "face_ABC", "points": ["A", "B", "C"]}],
  "angles": [{"id": "angle_ABC", "vertex": "B", "p1": "A", "p2": "C", "value": 90.0}],
  "given": {"line_AB": "12 cm", "angle_ABC": "90°"},
  "asked": ["angle_XYZ"]
}
```

## Output: Single Python Script

Generate ONE complete `render_code.py` that:
- Uses matplotlib with `matplotlib.use('Agg')`
- Hardcodes all coordinates (no JSON parsing at runtime)
- Outputs to the specified path
- Imports angle arc helpers from `matplotlib_helpers` (it is in the same directory)

## MANDATORY Imports

Your script MUST start with these EXACT imports:

```python
#!/usr/bin/env python3
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from pathlib import Path
from matplotlib_helpers import draw_angle_arc, draw_right_angle_marker
```

**NEVER use `matplotlib.patheffects`** — it requires a separate import and is unnecessary.
**NEVER implement your own angle arc math** — always use `draw_angle_arc` and `draw_right_angle_marker` from `matplotlib_helpers`.

## Styling

- **Background:** `#FFFFFF`
- **Points:** `#1A1A1A`, size 8
- **Labels:** `#1A1A1A`, offset away from centroid
- **Lines:** Cycle colors: `#2A9D8F`, `#264653`, `#457B9D`, `#6A4C93`, `#E76F51`
- **Given annotations:** Show labels from `given` dict (e.g., "12 cm")
- **Asked elements:** Use `#E63946` accent, 2x thickness, "?" label (NO numerical value)
- **Asked line glow:** Draw TWO lines — wide glow (`linewidth=8, alpha=0.2, #E63946, zorder=1`) then main line (`linewidth=4, #E63946, zorder=2`)
- **Angle arcs:** Only for angles in `given` or `asked`. Use `draw_angle_arc` for all arcs.
- **Right angles (90°):** Use `draw_right_angle_marker` instead of `draw_angle_arc`.

## Label Validation (CRITICAL)

**ONLY render these as text labels:**
- ✅ **Point names:** Single letters or letter combinations: `"A"`, `"B"`, `"AB"`, `"O"`, `"V"`
- ✅ **Measurements:** Numbers with units: `"6 cm"`, `"12 cm"`, `"90°"`, `"3.5 cm"`
- ✅ **Asked markers:** Single character: `"?"` (for unknown values)

**NEVER render these as labels:**
- ❌ **Full sentences:** "Find shortest distance between skew lines AH and BF"
- ❌ **Descriptive phrases:** "midpoint of CF", "perpendicular from A to BC"
- ❌ **Question text:** Any text from the problem statement
- ❌ **Solution descriptions:** "distance is", "angle equals"
- ❌ **Multi-word explanations:** Any label with >5 words or >20 characters (except point IDs like "ABCD")

**Implementation:** Only use keys from the `points` dict for point labels, and values from the `given` dict for measurements. Ignore any other text in the blueprint.

## Figure Size

854 x 480 pixels, DPI 100 (`figsize=(8.54, 4.80)`)
**CRITICAL:** Always add `fig.subplots_adjust(left=0, right=1, top=1, bottom=0)` immediately after `plt.subplots()` so the axes fills the entire figure with no wasted margins.

## Angle Arc Drawing — ALWAYS use matplotlib_helpers

**For non-right angles (given):**
```python
draw_angle_arc(ax, vertex=points["B"], p1=points["A"], p2=points["C"],
               expected_degrees=75.0,  # from blueprint angles list
               radius=0.6, color='#264653', linewidth=1.5, zorder=3,
               label="75°", label_fontsize=10)
```

**For asked angles:**
```python
draw_angle_arc(ax, vertex=points["C"], p1=points["B"], p2=points["D"],
               expected_degrees=None,  # unknown — draws interior angle
               radius=0.7, color='#E63946', linewidth=2.5, zorder=3,
               label="?", label_color='#E63946', label_fontsize=12,
               label_fontweight='bold')
```

**For right angles (90°):**
```python
draw_right_angle_marker(ax, vertex=points["C"], p1=points["A"], p2=points["B"],
                        size=0.3, color='#264653', linewidth=1.5, zorder=3)
```

**CRITICAL:** NEVER use `matplotlib.patches.Arc` directly or compute `atan2` yourself.
NEVER implement custom arc math. ALWAYS call `draw_angle_arc` or `draw_right_angle_marker`.

## Scale-Aware Sizing (IMPORTANT)

Font sizes and offsets MUST scale with the coordinate range so labels stay proportional to the figure.
Compute these **after** defining `points` and use them for ALL text:

```python
all_x = [p[0] for p in points.values()]
all_y = [p[1] for p in points.values()]
extent = max((max(all_x) - min(all_x)), (max(all_y) - min(all_y)), 1)

# Scale-aware sizes — use these, NEVER hardcode fontsize
LABEL_SIZE = max(8, min(14, 120 / extent))        # vertex labels
ANNOT_SIZE = max(7, min(12, 100 / extent))         # given annotations
ASKED_SIZE = max(9, min(16, 140 / extent))         # "?" labels
LABEL_OFFSET = extent * 0.04                       # label offset from point
ANNOT_OFFSET = extent * 0.05                       # annotation perpendicular offset
```

Use `fontsize=LABEL_SIZE`, `fontsize=ANNOT_SIZE`, `fontsize=ASKED_SIZE` everywhere.
Use `LABEL_OFFSET` for vertex label offsets and `ANNOT_OFFSET` for annotation placement.

## Template

```python
#!/usr/bin/env python3
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from pathlib import Path
from matplotlib_helpers import draw_angle_arc, draw_right_angle_marker

# Coordinates from blueprint
points = {
    "A": np.array([x, y]),
    # ...
}

# Scale-aware sizing (MUST compute before drawing)
all_x = [p[0] for p in points.values()]
all_y = [p[1] for p in points.values()]
extent = max((max(all_x) - min(all_x)), (max(all_y) - min(all_y)), 1)
LABEL_SIZE = max(8, min(14, 120 / extent))
ANNOT_SIZE = max(7, min(12, 100 / extent))
ASKED_SIZE = max(9, min(16, 140 / extent))
LABEL_OFFSET = extent * 0.04
ANNOT_OFFSET = extent * 0.05

fig, ax = plt.subplots(figsize=(8.54, 4.80), dpi=100)
fig.subplots_adjust(left=0, right=1, top=1, bottom=0)   # axes fills entire figure
fig.patch.set_facecolor('#FFFFFF')
ax.set_facecolor('#FFFFFF')
ax.set_aspect('equal')
ax.axis('off')

# Draw faces (z=0)
# Draw lines (z=1-2, glow for asked)
# Draw angle arcs using draw_angle_arc / draw_right_angle_marker (z=3)
# Draw points (z=4)
# Draw labels — use fontsize=LABEL_SIZE and LABEL_OFFSET (z=5)
# Draw annotations — use fontsize=ANNOT_SIZE and ANNOT_OFFSET
# Draw asked "?" — use fontsize=ASKED_SIZE

# Auto-fit: pad to fill landscape frame (CRITICAL for correct aspect ratio)
# Generous padding ensures labels, tangent lines, and angle arcs remain fully visible
padding = 0.35  # Increased from 0.15 to prevent clipping of extended elements
x_range = max(all_x) - min(all_x) or 1
y_range = max(all_y) - min(all_y) or 1
target_ratio = 8.54 / 4.80  # landscape figsize ratio
data_ratio = x_range / y_range if y_range > 0 else target_ratio
x_center = (min(all_x) + max(all_x)) / 2
y_center = (min(all_y) + max(all_y)) / 2
if data_ratio < target_ratio:
    x_range = y_range * target_ratio
if data_ratio > target_ratio:
    y_range = x_range / target_ratio
ax.set_xlim(x_center - x_range/2 * (1 + padding), x_center + x_range/2 * (1 + padding))
ax.set_ylim(y_center - y_range/2 * (1 + padding), y_center + y_range/2 * (1 + padding))

Path("OUTPUT_PATH").parent.mkdir(parents=True, exist_ok=True)
plt.savefig("OUTPUT_PATH", dpi=100, facecolor='white')
plt.close()
print("Saved: OUTPUT_PATH")
```

## Critical Rules

1. **NEVER show solutions/answers** — only show "?" for asked elements
2. Only show labels for elements in `given` dict
3. **VALID LABELS ONLY:** Only render point names (A, B, C) and measurements (6 cm, 90°). NEVER render sentences, phrases, or question text.
4. **VALID VARIABLE NAMES:** Use only letters, digits, and underscores. NEVER use `?pos` or special characters in variable names. Use `asked_pos` or `question_mark_pos` instead.
5. Hardcode everything, no file I/O
6. **NEVER use `bbox_inches='tight'`** in savefig — the landscape-padded axis limits already ensure correct sizing
7. **ALWAYS import `draw_angle_arc, draw_right_angle_marker` from `matplotlib_helpers`** — NEVER implement arc math yourself
8. **NEVER use `matplotlib.patheffects`** — use a second thicker `ax.plot()` for glow effects instead
9. **ALWAYS use scale-aware font sizes** (`LABEL_SIZE`, `ANNOT_SIZE`, `ASKED_SIZE`) — NEVER hardcode `fontsize=12`
10. **Ensure FULL visibility** — The 0.35 padding ensures all elements (labels, tangents, angle arcs) fit completely within the frame. Never reduce this padding.
11. Output exactly ONE ```python code block

"""


# ======================================================================
# STAGE 2 (DEEPSEEK): JSON Blueprint → 3D Manim Code
# ======================================================================

Blueprint_to_Code_3D_DeepSeek = """
You are a Python 3D visualization expert. Convert a JSON geometry blueprint into a manim script.

## Input Format

You receive a JSON blueprint:
```json
{
  "dimension": "3d",
  "scale": {"reference": "AB", "real": "6 cm", "units": 5.0},
  "points": {"A": [0, 0, 0], "B": [5, 0, 0], "V": [2.5, 1.44, 4]},
  "lines": [{"id": "line_AB", "from": "A", "to": "B", "style": "dashed"}, ...],
  "faces": [{"id": "face_ABC", "points": ["A", "B", "C"]}],
  "angles": [{"id": "angle_AVB", "vertex": "V", "p1": "A", "p2": "B", "value": 60.0}],
  "given": {"line_AB": "6 cm"},
  "asked": ["angle_AVB"]
}
```

## Output: Single Python Script

Generate ONE complete `render_code.py` that:
- Uses manim for 3D rotating animation
- Hardcodes all coordinates (no JSON parsing)
- Outputs GIF to the specified path

## Manim Configuration

```python
config.background_color = "#FFFFFF"
config.pixel_height = 360
config.pixel_width = 640
config.frame_rate = 10
config.format = "gif"
config.output_file = "diagram"
```

## Styling

- **Background:** `#FFFFFF`
- **Points:** `Dot3D(color="#1A1A1A", radius=0.06)`
- **Labels:** `Text("A", color="#1A1A1A").scale(0.8)` — use `self.add_fixed_orientation_mobjects(label)` (NO `.rotate()` before it)
- **Lines:** `Line3D(start, end, color=HEX, thickness=0.02)`
- **Dashed lines:** Use `DashedLine(start, end, color=HEX, dash_length=0.15)` — **NEVER** `DashedVMobject(Line3D(...))`
- **Given annotations:** Show labels from `given` dict
- **Asked elements:** Use `#E63946`, 2x thickness, "?" label (NO numerical value)
- **Faces:** `Polygon` with `fill_opacity=0.08`, `stroke_opacity=0.3`

## Label Validation (CRITICAL)

**ONLY render these as text labels:**
- ✅ **Point names:** Single letters or letter combinations: `"A"`, `"B"`, `"AB"`, `"O"`, `"V"`
- ✅ **Measurements:** Numbers with units: `"6 cm"`, `"12 cm"`, `"90°"`, `"3.5 cm"`
- ✅ **Asked markers:** Single character: `"?"` (for unknown values)

**NEVER render these as labels:**
- ❌ **Full sentences:** "Find shortest distance between skew lines AH and BF"
- ❌ **Descriptive phrases:** "midpoint of CF", "perpendicular from A to BC"
- ❌ **Question text:** Any text from the problem statement
- ❌ **Solution descriptions:** "distance is", "angle equals"
- ❌ **Multi-word explanations:** Any label with >5 words or >20 characters (except point IDs like "ABCD")

**Implementation:** Only use keys from the `points` dict for point labels, and values from the `given` dict for measurements. Ignore any other text in the blueprint.

## Adaptive Scaling (CRITICAL)

```python
# 1. Compute centroid
all_coords = np.array(list(pts_raw.values()))
centroid = np.mean(all_coords, axis=0)

# 2. Max radius from centroid (for rotation safety)
centered = all_coords - centroid
max_radius = max(np.linalg.norm(c) for c in centered)

# 3. Scale to fit frame
TARGET_SIZE = 3.5  # conservative
SCALE_FACTOR = min(1.5, TARGET_SIZE / max_radius) if max_radius > 0 else 1.0

# 4. Apply
pts = {k: (v - centroid) * SCALE_FACTOR for k, v in pts_raw.items()}
```

## Template Structure

```python
#!/usr/bin/env python3
from manim import *
import numpy as np
import shutil
from pathlib import Path
from manim_helpers import (
    create_3d_angle_arc_with_connections,
    create_3d_coordinate_axes,
    create_sphere_wireframe,
)

config.background_color = "#FFFFFF"
# ... other config

pts_raw = {"A": np.array([0.0, 0.0, 0.0]), ...}  # ALWAYS use floats!

# Scaling code...

class GeometryScene(ThreeDScene):
    def construct(self):
        # Camera setup
        self.set_camera_orientation(phi=65*DEGREES, theta=-45*DEGREES, zoom=0.7)

        # Draw faces, lines, points, labels
        # ...

        # Rotation animation
        self.begin_ambient_camera_rotation(rate=TAU/4)  # Full 360° in 4 seconds
        self.wait(4)

# Post-render: move output file
```

## Critical Rules

1. **ALWAYS use float arrays:** `np.array([1.0, 0.0, 0.0])` NOT `np.array([1, 0, 0])`
2. **NEVER show solutions/answers** — only "?" for asked elements
3. **VALID LABELS ONLY:** Only render point names (A, B, C) and measurements (6 cm, 90°). NEVER render sentences, phrases, or question text.
4. **VALID VARIABLE NAMES:** Use only letters, digits, and underscores. NEVER use `?pos` or special characters in variable names. Use `asked_pos` or `question_mark_pos` instead.
5. **Non-existent classes:** `Polyline`, `DashedLine3D`, `Arc3D`, `Prism` do NOT exist
6. **Use `fill_opacity`/`stroke_opacity`** NOT `opacity`
7. **Line3D params:** Only `Line3D(start, end, color=, thickness=)` — NO `radius=`
8. **Dashed lines:** `DashedLine(start, end, color=HEX, dash_length=0.15)` — **NEVER** use `DashedVMobject(Line3D(...))`
9. **Text not MathTex:** Use `Text("label")` — no LaTeX
10. **Cone positioning:** Base at reference point, use `direction=` for apex direction
11. **No Cylinder class:** Use circles + lines instead
12. Use `from manim_helpers import (
    create_3d_angle_arc_with_connections,
    create_3d_coordinate_axes,
    create_sphere_wireframe,
)` for angle arcs

## Angle Arc Usage

```python
arc = create_3d_angle_arc_with_connections(
    center=pts["V"],
    point1=pts["A"],
    point2=pts["B"],
    radius=0.5,
    color="#E63946"  # accent for asked
)
self.add(arc)
```

## Output exactly ONE ```python code block.

"""


# ======================================================================
# STAGE 2 (COORDINATE): JSON Blueprint → 2D Matplotlib Code with Axes
# ======================================================================

Blueprint_to_Code_Coordinate_2D = """
You are a Python visualization expert. Convert a JSON coordinate geometry blueprint into a matplotlib script with axes and grid.

## Input Format

You receive a JSON blueprint:
```json
{
  "dimension": "2d",
  "axes": true,
  "grid": true,
  "coordinate_range": {"x_min": -1.0, "x_max": 8.0, "y_min": -1.0, "y_max": 11.0},
  "scale": {"reference": "auto", "real": "1 unit", "units": 1.0},
  "points": {"A": [2.0, 3.0, 0.0], "B": [6.0, -1.0, 0.0], "O": [0.0, 0.0, 0.0]},
  "lines": [
    {"id": "line_AB", "from": "A", "to": "B"},
    {"id": "x_axis", "style": "axis"},
    {"id": "y_axis", "style": "axis"}
  ],
  "circles": [{"id": "circle_C", "center": "C", "radius": 5.0}],
  "curves": [
    {"id": "parabola_1", "equation": "y = x^2 - 4*x + 3", "points": [[0, 3], [1, 0], [2, -1], [3, 0], [4, 3]]}
  ],
  "faces": [{"id": "region_feasible", "points": ["P1", "P2", "P3", "P4"], "style": "shaded"}],
  "given": {"line_AB": "y = 2x + 1"},
  "asked": ["point_intersection"]
}
```

## Output: Single Python Script

Generate ONE complete `render_code.py` that:
- Uses matplotlib with `matplotlib.use('Agg')`
- Renders coordinate axes with tick marks and labels
- Renders optional grid if `grid: true`
- Uses `coordinate_range` for xlim/ylim (NOT auto-fit)
- Hardcodes all coordinates (no JSON parsing at runtime)
- Imports angle arc helpers from `matplotlib_helpers`

## MANDATORY Imports

```python
#!/usr/bin/env python3
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from pathlib import Path
from matplotlib_helpers import draw_angle_arc, draw_right_angle_marker, draw_coordinate_axes
```

**NEVER use `matplotlib.patheffects`** — it requires a separate import and is unnecessary.

## Styling

- **Background:** `#FFFFFF`
- **Axes:** `#1A1A1A`, linewidth 1.5, with arrows at positive direction
- **Grid:** `#E0E0E0`, alpha 0.55, linewidth 0.5 (if `grid: true`)
- **Tick labels:** `#1A1A1A`, fontsize 9
- **Points:** `#1A1A1A`, size 8
- **Point labels:** `#1A1A1A`, **show ONLY the point name** (e.g., "A", "B", "P") **WITHOUT coordinates** — do NOT add "(x, y)" values
- **Lines:** Cycle colors: `#2A9D8F`, `#264653`, `#457B9D`, `#6A4C93`, `#E76F51`, linewidth 2.5
- **Curves:** Use line colors, linewidth 2.5
- **Shaded regions:** Fill with `#2A9D8F`, alpha 0.15
- **Given annotations:** Show labels from `given` dict (equations, measurements)
- **Asked elements:** Use `#E63946` accent, 2x thickness, "?" label (NO numerical value)

## Coordinate Axes Rendering (CRITICAL)

**ALWAYS render axes when `axes: true` using the helper function:**

```python
# Draw coordinate axes with arrows and labels (one line!)
draw_coordinate_axes(ax, x_min, x_max, y_min, y_max, arrow_size=0.15, zorder=0)
```

This helper draws:
- X and Y axis lines through the origin
- Arrow heads at the positive ends
- Axis labels ("x" and "y")

## Grid Rendering (CRITICAL)

**If `blueprint["grid"] == true`:**

```python
# Adaptive tick spacing based on coordinate range
x_range = x_max - x_min
y_range = y_max - y_min

# Target ~10-15 tick marks per axis
x_tick_spacing = max(1, round(x_range / 12))
y_tick_spacing = max(1, round(y_range / 12))

# Generate tick positions
x_ticks = np.arange(np.floor(x_min), np.ceil(x_max) + 1, x_tick_spacing)
y_ticks = np.arange(np.floor(y_min), np.ceil(y_max) + 1, y_tick_spacing)

# Draw grid
ax.set_xticks(x_ticks)
ax.set_yticks(y_ticks)
ax.grid(True, alpha=0.3, color='#E0E0E0', linewidth=0.5, zorder=0)

# Draw tick labels
ax.tick_params(axis='both', which='major', labelsize=9, colors='#1A1A1A')
```

**If `grid == false`:** Only draw axes, no grid or tick marks.

## Coordinate Range Usage (CRITICAL)

**NEVER auto-fit from points.** Use `coordinate_range` from blueprint:

```python
x_min = blueprint["coordinate_range"]["x_min"]
x_max = blueprint["coordinate_range"]["x_max"]
y_min = blueprint["coordinate_range"]["y_min"]
y_max = blueprint["coordinate_range"]["y_max"]

ax.set_xlim(x_min, x_max)
ax.set_ylim(y_min, y_max)
```

## Curve Rendering

**Curves come with pre-sampled points:**

```python
# From blueprint: {"id": "parabola_1", "equation": "y = x^2 - 4*x + 3", "points": [[0, 3], [1, 0], ...]}
curve_points = np.array([[0, 3], [1, 0], [2, -1], [3, 0], [4, 3]])
ax.plot(curve_points[:, 0], curve_points[:, 1], color='#2A9D8F', linewidth=2.0, zorder=2)

# Optional: label with equation
ax.text(curve_points[-1, 0] + 0.2, curve_points[-1, 1], "y = x² - 4x + 3",
        fontsize=9, color='#2A9D8F', ha='left', va='center')
```

## Shaded Regions

```python
# From blueprint faces with "style": "shaded"
region_vertices = [points["P1"][:2], points["P2"][:2], points["P3"][:2], points["P4"][:2]]
polygon = patches.Polygon(region_vertices, closed=True,
                         facecolor='#2A9D8F', edgecolor='none',
                         alpha=0.15, zorder=0)
ax.add_patch(polygon)
```

## Label Validation (CRITICAL)

**ONLY render these as text labels:**
- ✅ **Point names:** Single letters WITHOUT coordinates: `"A"`, `"B"`, `"O"`, `"P"`, `"P1"`
- ✅ **Measurements:** Numbers with units: `"6 cm"`, `"90°"`
- ✅ **Equations:** Short form: `"y = 2x + 1"`, `"x² + y² = 25"`
- ✅ **Asked markers:** Single character: `"?"`

**NEVER render these as labels:**
- ❌ **Coordinates in point labels:** "A(0, 8)", "B(4, 0)", "P(3, 2)" — coordinates clutter the diagram
- ❌ **Full sentences:** "Find the equation of the line"
- ❌ **Descriptive phrases:** "intersection of L1 and L2"
- ❌ **Question text:** Any text from the problem statement

## Point Labeling Example (CRITICAL)

```python
# ✅ CORRECT: Show only point name
for name, coord in points.items():
    x, y = coord[0], coord[1]
    ax.plot(x, y, 'o', color='#1A1A1A', markersize=8, zorder=4)
    ax.text(x + LABEL_OFFSET, y + LABEL_OFFSET, name,
            fontsize=LABEL_SIZE, color='#1A1A1A', ha='left', va='bottom', zorder=5)

# ❌ WRONG: Including coordinates clutters the diagram
ax.text(x, y, f'{name}({x}, {y})', ...)  # DO NOT DO THIS
```

## Scale-Aware Sizing

```python
# Compute extent from coordinate_range (NOT from points)
extent = max((x_max - x_min), (y_max - y_min), 1)

# Scale-aware sizes
LABEL_SIZE = max(8, min(14, 120 / extent))
ANNOT_SIZE = max(7, min(12, 100 / extent))
ASKED_SIZE = max(9, min(16, 140 / extent))
LABEL_OFFSET = extent * 0.04
ANNOT_OFFSET = extent * 0.05
```

## Template

```python
#!/usr/bin/env python3
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from pathlib import Path
from matplotlib_helpers import draw_angle_arc, draw_right_angle_marker, draw_coordinate_axes

# Coordinates from blueprint
points = {
    "A": np.array([x, y]),
    # ...
}

# Coordinate range from blueprint
x_min, x_max = -1.0, 8.0
y_min, y_max = -1.0, 11.0

# Scale-aware sizing
extent = max((x_max - x_min), (y_max - y_min), 1)
LABEL_SIZE = max(8, min(14, 120 / extent))
ANNOT_SIZE = max(7, min(12, 100 / extent))
ASKED_SIZE = max(9, min(16, 140 / extent))
LABEL_OFFSET = extent * 0.04
ANNOT_OFFSET = extent * 0.05

fig, ax = plt.subplots(figsize=(8.54, 4.80), dpi=100)
fig.patch.set_facecolor('#FFFFFF')
ax.set_facecolor('#FFFFFF')
ax.set_aspect('equal')
ax.axis('off')  # Turn off default axes, we draw custom ones

# Set coordinate range (CRITICAL)
ax.set_xlim(x_min, x_max)
ax.set_ylim(y_min, y_max)

# Draw coordinate axes with arrows and labels (z=0)
draw_coordinate_axes(ax, x_min, x_max, y_min, y_max, arrow_size=0.15, zorder=0)

# Draw grid if grid=true (z=0)
if grid_enabled:
    # ... adaptive tick spacing ...
    ax.grid(True, alpha=0.3, color='#E0E0E0', linewidth=0.5, zorder=0)

# Draw shaded regions (z=0)
# Draw curves from sampled points (z=1)
# Draw lines (z=1-2)
# Draw circles (z=2)
# Draw angle arcs (z=3)
# Draw points (z=4)
# Draw labels (z=5)

Path("OUTPUT_PATH").parent.mkdir(parents=True, exist_ok=True)
plt.savefig("OUTPUT_PATH", dpi=100, facecolor='white', bbox_inches='tight')
plt.close()
print("Saved: OUTPUT_PATH")
```

## Critical Rules

1. **NEVER show solutions/answers** — only "?" for asked elements
2. **Use coordinate_range for xlim/ylim** — NOT auto-fit from points
3. **ALWAYS draw axes when axes=true**
4. **Grid is optional** — only draw if `grid: true`
5. **Curves use pre-sampled points** — NO equation parsing
6. **Adaptive tick spacing** — target 10-15 ticks per axis
7. **VALID LABELS ONLY:** Point names, measurements, short equations. NO sentences.
8. **VALID VARIABLE NAMES:** Use only letters, digits, underscores. NO special characters.
9. **Import matplotlib_helpers** for angle arcs
10. Output exactly ONE ```python code block

"""


# ======================================================================
# STAGE 2 (COORDINATE): JSON Blueprint → 3D Manim Code with Axes
# ======================================================================

Blueprint_to_Code_Coordinate_3D = """
You are a Python 3D visualization expert. Convert a JSON coordinate geometry blueprint into a manim script with 3D axes.

## Input Format

You receive a JSON blueprint:
```json
{
  "dimension": "3d",
  "axes": true,
  "grid": false,
  "coordinate_range": {"x_min": -2.0, "x_max": 6.0, "y_min": -2.0, "y_max": 5.0, "z_min": -1.0, "z_max": 8.0},
  "scale": {"reference": "auto", "real": "1 unit", "units": 1.0},
  "points": {"A": [1.0, 2.0, 3.0], "B": [4.0, 0.0, 1.0], "O": [0.0, 0.0, 0.0]},
  "lines": [
    {"id": "line_AB", "from": "A", "to": "B"},
    {"id": "x_axis", "style": "axis"},
    {"id": "y_axis", "style": "axis"},
    {"id": "z_axis", "style": "axis"}
  ],
  "planes": [
    {"id": "plane_ABC", "equation": "2x + y - z = 4", "vertices": [[2, 0, 0], [0, 4, 0], [0, 0, -4], [1, 2, 0]]}
  ],
  "spheres": [
    {"id": "sphere_S1", "center": "C", "radius": 5.0, "wireframe_circles": 3}
  ],
  "vectors": [
    {"id": "vector_AB", "from": "A", "to": "B", "components": [3.0, -2.0, -2.0]}
  ],
  "given": {"plane_P1": "2x + y - z = 4"},
  "asked": ["distance"]
}
```

## Output: Single Python Script

Generate ONE complete `render_code.py` that:
- Uses manim for 3D rotating animation
- Renders 3D coordinate axes (X, Y, Z) with labels
- Renders planes as semi-transparent polygons (pre-computed vertices)
- Renders spheres as wireframe circles
- Renders vectors as arrows
- Uses `coordinate_range` for axis lengths (NO auto-scaling)
- Hardcodes all coordinates

## Manim Configuration

```python
config.background_color = "#FFFFFF"
config.pixel_height = 360
config.pixel_width = 640
config.frame_rate = 10
config.format = "gif"
config.output_file = "diagram"
```

## Styling

- **Background:** `#FFFFFF`
- **Axes:** `#1A1A1A`, thickness 0.025, with arrows
- **Axis labels:** `Text("X", color="#1A1A1A").scale(0.6)`
- **Grid (optional):** `NumberPlane` on XY plane, `#E0E0E0`
- **Points:** `Dot3D(color="#1A1A1A", radius=0.06)`
- **Point labels:** `Text("A", color="#1A1A1A").scale(0.8)` — **show ONLY point name WITHOUT coordinates** (e.g., "A", not "A(1, 2, 3)")
- **Lines:** `Line3D(start, end, color=HEX, thickness=0.025)`
- **Dashed lines:** `DashedLine(start, end, color=HEX, dash_length=0.15)`
- **Planes:** `Polygon` with `fill_opacity=0.12`, `stroke_opacity=0.4`
- **Spheres:** Wireframe circles with `stroke_opacity=0.5`
- **Vectors:** `Arrow3D` with `color="#E76F51"`, thickness 0.03
- **Asked elements:** `#E63946`, 2x thickness, "?" label

## 3D Coordinate Axes Rendering (CRITICAL)

**ALWAYS render 3D axes when `axes: true` using the helper function:**

```python
# Get coordinate range from blueprint
x_min, x_max = -2.0, 6.0
y_min, y_max = -2.0, 5.0
z_min, z_max = -1.0, 8.0

# Draw 3D coordinate axes with color-coded arrows and labels (just 3 lines!)
axes, labels = create_3d_coordinate_axes(
    (x_min, x_max), (y_min, y_max), (z_min, z_max)
)
self.add(axes)
self.add_fixed_orientation_mobjects(*labels)
```

This helper creates:
- X-axis (red accent `#C44536`) with "X" label
- Y-axis (green accent `#6A994E`) with "Y" label
- Z-axis (blue accent `#457B9D`) with "Z" label

## Plane Rendering (Pre-computed vertices)

**Planes come with pre-computed vertices:**

```python
# From blueprint: {"id": "plane_ABC", "vertices": [[2, 0, 0], [0, 4, 0], [0, 0, -4], [1, 2, 0]]}
plane_vertices = [np.array([2.0, 0.0, 0.0]), np.array([0.0, 4.0, 0.0]),
                  np.array([0.0, 0.0, -4.0]), np.array([1.0, 2.0, 0.0])]
plane = Polygon(*plane_vertices, color="#2A9D8F", fill_opacity=0.12, stroke_opacity=0.4)
self.add(plane)

# Optional: label with equation
plane_label = Text("2x + y - z = 4", color="#2A9D8F").scale(0.5)
plane_label.move_to(np.mean(plane_vertices, axis=0) + np.array([0.5, 0.5, 0.5]))
self.add(plane_label)
```

## Sphere Wireframe Rendering

**Spheres use wireframe circles using the helper function:**

```python
# From blueprint: {"id": "sphere_S1", "center": "C", "radius": 5.0, "wireframe_circles": 3}
wireframe = create_sphere_wireframe(
    center=pts["C"],
    radius=5.0,
    color="#457B9D",
    stroke_opacity=0.5
)
self.add(wireframe)
```

This helper creates 3 orthogonal circles:
- XY plane circle (horizontal)
- XZ plane circle (rotated 90° around X-axis)
- YZ plane circle (rotated 90° around Y-axis)

## Vector Rendering

**Vectors rendered as Arrow3D:**

```python
# From blueprint: {"id": "vector_AB", "from": "A", "to": "B"}
vector_arrow = Arrow3D(
    start=pts["A"],
    end=pts["B"],
    color="#E76F51",
    thickness=0.025
)
self.add(vector_arrow)

# Label with components
vector_label = Text("(3, -2, -2)", color="#E76F51").scale(0.6)
vector_label.move_to((pts["A"] + pts["B"]) / 2 + np.array([0.5, 0.5, 0.5]))
self.add(vector_label)
```

## Grid Rendering (Optional)

**If `grid: true`, render XY plane grid:**

```python
# NumberPlane on XY plane
xy_grid = NumberPlane(
    x_range=[x_min, x_max, 1],
    y_range=[y_min, y_max, 1],
    background_line_style={"stroke_color": "#E0E0E0", "stroke_opacity": 0.3}
)
xy_grid.shift(np.array([0, 0, 0]))  # At z=0
self.add(xy_grid)
```

## Coordinate Range Usage (CRITICAL)

**NEVER auto-scale or compute centroid.** Use exact coordinates and coordinate_range:

```python
# NO centroid computation
# NO scaling logic
# Use coordinates directly from blueprint

pts = {
    "A": np.array([1.0, 2.0, 3.0]),
    "B": np.array([4.0, 0.0, 1.0]),
    # ...
}

# Camera positioning based on coordinate_range center
x_center = (x_min + x_max) / 2
y_center = (y_min + y_max) / 2
z_center = (z_min + z_max) / 2

# Set camera to look at center
self.set_camera_orientation(phi=65*DEGREES, theta=-45*DEGREES, zoom=0.8)
self.camera.frame_center = np.array([x_center, y_center, z_center])
```

## Template Structure

```python
#!/usr/bin/env python3
from manim import *
import numpy as np
import shutil
from pathlib import Path
from manim_helpers import (
    create_3d_angle_arc_with_connections,
    create_3d_coordinate_axes,
    create_sphere_wireframe,
)

config.background_color = "#FFFFFF"
config.pixel_height = 360
config.pixel_width = 640
config.frame_rate = 10
config.format = "gif"
config.output_file = "diagram"

# Coordinate range from blueprint
x_min, x_max = -2.0, 6.0
y_min, y_max = -2.0, 5.0
z_min, z_max = -1.0, 8.0

# Points (ALWAYS use floats!)
pts = {
    "A": np.array([1.0, 2.0, 3.0]),
    "B": np.array([4.0, 0.0, 1.0]),
    "O": np.array([0.0, 0.0, 0.0])
}

class GeometryScene(ThreeDScene):
    def construct(self):
        # Camera setup
        x_center = (x_min + x_max) / 2
        y_center = (y_min + y_max) / 2
        z_center = (z_min + z_max) / 2

        self.set_camera_orientation(phi=65*DEGREES, theta=-45*DEGREES, zoom=0.8)
        self.camera.frame_center = np.array([x_center, y_center, z_center])

        # Draw 3D axes with labels
        # Draw grid if grid=true
        # Draw planes (pre-computed vertices)
        # Draw spheres (wireframe circles)
        # Draw vectors (Arrow3D)
        # Draw lines
        # Draw points
        # Draw labels

        # Rotation animation
        self.begin_ambient_camera_rotation(rate=TAU/4)  # Full 360° in 4 seconds
        self.wait(4)

# Post-render: move output file
output_dir = Path("OUTPUT_PATH").parent
output_dir.mkdir(parents=True, exist_ok=True)
media_dir = Path("media/videos/diagram/360p10")
if media_dir.exists():
    for gif_file in media_dir.glob("*.gif"):
        shutil.move(str(gif_file), "OUTPUT_PATH")
        print(f"Saved: OUTPUT_PATH")
        break
```

## Label Validation (CRITICAL)

**ONLY render these as text labels:**
- ✅ **Point names WITHOUT coordinates:** `"A"`, `"B"`, `"O"`, `"P"`, `"P1"` — do NOT add coordinates like "(1, 2, 3)"
- ✅ **Measurements:** `"6 cm"`, `"90°"`
- ✅ **Equations:** `"2x + y - z = 4"`, `"x² + y² + z² = 25"`
- ✅ **Vector components:** `"(3, -2, -2)"`
- ✅ **Asked markers:** `"?"`

**NEVER render these as labels:**
- ❌ **Coordinates in point labels:** "A(1, 2, 3)", "B(4, 0, 1)" — coordinates clutter the diagram
- ❌ **Full sentences**
- ❌ **Descriptive phrases**
- ❌ **Question text**

## Point Labeling Example (CRITICAL)

```python
# ✅ CORRECT: Show only point name
for name, coord in pts.items():
    dot = Dot3D(point=coord, color="#1A1A1A", radius=0.06)
    self.add(dot)
    label = Text(name, color="#1A1A1A").scale(0.8)
    label.move_to(coord + np.array([0.3, 0.3, 0.3]))
    self.add(label)

# ❌ WRONG: Including coordinates clutters the diagram
label = Text(f"{name}({coord[0]}, {coord[1]}, {coord[2]})", ...)  # DO NOT DO THIS
```

## Critical Rules

1. **ALWAYS use float arrays:** `np.array([1.0, 0.0, 0.0])` NOT `np.array([1, 0, 0])`
2. **NEVER show solutions/answers** — only "?" for asked elements
3. **Use coordinate_range for axes** — NO auto-scaling or centroid computation
4. **ALWAYS draw 3D axes when axes=true**
5. **Planes use pre-computed vertices** — NO plane equation solving
6. **Spheres use wireframe circles** — NO Surface class
7. **Vectors use Arrow3D**
8. **Grid is optional** — only draw if `grid: true`
9. **VALID LABELS ONLY:** Point names, measurements, equations. NO sentences.
10. **VALID VARIABLE NAMES:** Only letters, digits, underscores. NO special characters.
11. **Non-existent classes:** `Polyline`, `DashedLine3D`, `Arc3D`, `Prism` do NOT exist
12. **Use `fill_opacity`/`stroke_opacity`** NOT `opacity`
13. **Line3D params:** Only `Line3D(start, end, color=, thickness=)` — NO `radius=`
14. **Dashed lines:** `DashedLine(start, end, color=HEX, dash_length=0.15)`
15. **Text not MathTex:** Use `Text("label")` — no LaTeX
16. Output exactly ONE ```python code block

"""





# ======================================================================
# Prompt Selection Helpers
# ======================================================================

def get_prompt_for_dimension(dimension_type):
    # type: (str) -> str
    """Get the appropriate blueprint prompt for a given dimension type.

    Args:
        dimension_type: One of "2d", "3d", "coordinate_2d", "coordinate_3d"

    Returns:
        The corresponding blueprint prompt string

    Raises:
        ValueError: If dimension_type is not recognized
    """
    prompts = {
        "2d": Question_to_Blueprint_2D,
        "3d": Question_to_Blueprint_3D,
        "coordinate_2d": Question_to_Blueprint_Coordinate_2D,
        "coordinate_3d": Question_to_Blueprint_Coordinate_3D,
    }

    if dimension_type not in prompts:
        raise ValueError(
            f"Unknown dimension type: {dimension_type}. "
            f"Must be one of: {list(prompts.keys())}"
        )

    return prompts[dimension_type]


def get_code_prompt_for_dimension(dimension_type):
    # type: (str) -> str
    """Get the appropriate Blueprint_to_Code prompt for a given dimension type.

    Args:
        dimension_type: One of "2d", "3d", "coordinate_2d", "coordinate_3d"

    Returns:
        The corresponding Blueprint_to_Code prompt string

    Raises:
        ValueError: If dimension_type is not recognized
    """
    prompts = {
        "2d": Blueprint_to_Code_2D_DeepSeek,
        "3d": Blueprint_to_Code_3D_DeepSeek,
        "coordinate_2d": Blueprint_to_Code_Coordinate_2D,
        "coordinate_3d": Blueprint_to_Code_Coordinate_3D,
    }

    if dimension_type not in prompts:
        raise ValueError(
            f"Unknown dimension type: {dimension_type}. "
            f"Must be one of: {list(prompts.keys())}"
        )

    return prompts[dimension_type]



# ======================================================================
# Quick summary when run directly
# ======================================================================

if __name__ == "__main__":
    print("Individual Prompts for Each Dimension Type")
    print("=" * 70)
    print()

    print("STAGE 1: Question → Blueprint Prompts")
    print("-" * 70)
    blueprint_prompts = {
        "2d": ("Traditional 2D Geometry", Question_to_Blueprint_2D),
        "3d": ("Traditional 3D Geometry", Question_to_Blueprint_3D),
        "coordinate_2d": ("2D Coordinate Geometry", Question_to_Blueprint_Coordinate_2D),
        "coordinate_3d": ("3D Coordinate Geometry", Question_to_Blueprint_Coordinate_3D),
    }

    for dim_type, (description, prompt) in blueprint_prompts.items():
        print(f"{dim_type:15s} - {description}")
        print(f"  Length: {len(prompt):,} characters")
        has_axes = 'axes": true' in prompt
        has_grid = 'grid": true' in prompt
        print(f"  Axes: {'Yes' if has_axes else 'No'}")
        print(f"  Grid: {'Yes' if has_grid else 'No/Optional'}")
        print()

    print()
    print("STAGE 2: Blueprint → Code Prompts")
    print("-" * 70)
    code_prompts = {
        "2d": ("Traditional 2D → Matplotlib", Blueprint_to_Code_2D_DeepSeek),
        "3d": ("Traditional 3D → Manim", Blueprint_to_Code_3D_DeepSeek),
        "coordinate_2d": ("Coordinate 2D → Matplotlib (with axes)", Blueprint_to_Code_Coordinate_2D),
        "coordinate_3d": ("Coordinate 3D → Manim (with 3D axes)", Blueprint_to_Code_Coordinate_3D),
    }

    for dim_type, (description, prompt) in code_prompts.items():
        print(f"{dim_type:15s} - {description}")
        print(f"  Length: {len(prompt):,} characters")
        has_axes = 'axes' in description.lower()
        renderer = "matplotlib" if "Matplotlib" in description else "manim"
        print(f"  Renderer: {renderer}")
        print(f"  Axes: {'Yes' if has_axes else 'No'}")
        print()

    print()
    print("Usage:")
    print("-" * 70)
    print('  from individual_prompts import get_prompt_for_dimension, get_code_prompt_for_dimension')
    print()
    print('  # Get blueprint prompt')
    print('  blueprint_prompt = get_prompt_for_dimension("coordinate_2d")')
    print()
    print('  # Get code generation prompt')
    print('  code_prompt = get_code_prompt_for_dimension("coordinate_2d")')
    print()


# ======================================================================
# ADAPTIVE STAGE 1: Question → Blueprint (2-way: 2D or 3D)
#
# dimension output is always "2d" or "3d" — never coordinate_2d/3d.
# The LLM decides axes=true/false based on question content.
# axes=true adds: coordinate_range, curves (pre-sampled), planes, spheres, vectors.
# ======================================================================

Question_to_Blueprint_2D_Adaptive = """You are a geometry blueprint generator. Convert this 2D geometry question to JSON.

STEP 1 — DECIDE: set axes=true or axes=false.
  axes=false → traditional geometry: shapes described with lengths/angles/areas
               (triangles, polygons, circles with given radii, angle problems)
  axes=true  → coordinate geometry: equations (y=2x+1, x²+y²=25), graph sketching,
               loci, regions defined by inequalities, explicit coordinate frame needed

STEP 2 — OUTPUT the matching schema.

=== SCHEMA A: axes=false (traditional geometry) ===
{
  "dimension": "2d",
  "axes": false,
  "scale": {"reference": "AB", "real": "10 cm", "units": 5.0},
  "points": {"A": [0.0, 0.0, 0.0], "B": [5.0, 0.0, 0.0], "C": [2.5, 4.33, 0.0]},
  "lines": [{"id": "line_AB", "from": "A", "to": "B"}, {"id": "line_AC", "from": "A", "to": "C", "style": "dashed"}],
  "circles": [{"id": "circle_O", "center": "O", "radius": 3.0}],
  "arcs": [{"id": "arc_AB", "center": "O", "from": "A", "to": "B"}],
  "faces": [{"id": "face_ABC", "points": ["A", "B", "C"]}],
  "angles": [{"id": "angle_ABC", "vertex": "B", "p1": "A", "p2": "C", "value": 90.0}],
  "given": {"line_AB": "10 cm", "angle_ABC": "90°"},
  "asked": ["line_AC"]
}
Coordinate rules (axes=false):
- Place first named point at [0,0,0], first edge along +X axis
- Map first given length to 5.0 units; compute all other coords with trigonometry
- All points: [X, Y, 0.0] (Z always 0)
- Hidden/interior lines: add "style": "dashed"

=== SCHEMA B: axes=true (coordinate geometry) ===
{
  "dimension": "2d",
  "axes": true,
  "grid": true,
  "coordinate_range": {"x_min": -1.0, "x_max": 8.0, "y_min": -2.0, "y_max": 6.0},
  "scale": {"reference": "auto", "real": "1 unit", "units": 1.0},
  "points": {"A": [2.0, 3.0, 0.0], "B": [6.0, -1.0, 0.0], "O": [0.0, 0.0, 0.0]},
  "lines": [{"id": "line_L1", "from": "A", "to": "B"}],
  "circles": [{"id": "circle_C", "center": "C", "radius": 5.0}],
  "curves": [
    {"id": "curve_1", "equation": "y = x^2 - 4*x + 3",
     "points": [[0.0,3.0],[0.5,0.75],[1.0,0.0],[1.5,-0.25],[2.0,-1.0],[2.5,-0.25],[3.0,0.0],[3.5,0.75],[4.0,3.0]]}
  ],
  "faces": [{"id": "region_R", "points": ["P1", "P2", "P3", "P4"], "style": "shaded"}],
  "angles": [{"id": "angle_ABC", "vertex": "B", "p1": "A", "p2": "C", "value": 45.0}],
  "given": {"line_L1": "y = 2x + 1", "circle_C": "x² + y² = 25"},
  "asked": ["point_intersection"]
}
Coordinate rules (axes=true):
- Use EXACT coordinates from question as [X, Y, 0.0]; do NOT rescale to fit
- coordinate_range: cover all geometry with ~15% padding on each side
- curves: equation string + 8-12 pre-sampled [x, y] points evenly spaced across visible x-range
- grid: true for most coordinate questions; false only for very sparse diagrams

Common rules (both schemas):
- "given": only data explicitly stated in the question (lengths, angles, equations)
- "asked": element IDs that are unknown; these will be highlighted with "?"
- Output ONLY the JSON object, no explanation or markdown
"""


Question_to_Blueprint_3D_Adaptive = """You are a 3D geometry blueprint generator. Convert this 3D geometry question to JSON.

STEP 1 — DECIDE: set axes=true or axes=false.
  axes=false → traditional 3D geometry: shapes described with lengths/angles
               (pyramids, prisms, cuboids, cones, cylinders, tetrahedra)
  axes=true  → coordinate 3D geometry: explicit (x,y,z) points, plane equations
               (2x+y-z=4), vectors from origin, spheres with equations

STEP 2 — OUTPUT the matching schema.

=== SCHEMA A: axes=false (traditional 3D geometry) ===
{
  "dimension": "3d",
  "axes": false,
  "scale": {"reference": "AB", "real": "8 cm", "units": 4.0},
  "points": {"A": [4.0, 0.0, 0.0], "B": [0.0, 0.0, 0.0], "V": [2.0, 2.0, 5.0]},
  "lines": [
    {"id": "line_AB", "from": "A", "to": "B"},
    {"id": "line_VA", "from": "V", "to": "A", "style": "dashed"}
  ],
  "circles": [{"id": "circle_base", "center": "O", "radius": 4.0}],
  "faces": [
    {"id": "face_base", "points": ["A", "B", "C", "D"]},
    {"id": "face_VAB", "points": ["V", "A", "B"]}
  ],
  "angles": [{"id": "angle_VAB", "vertex": "A", "p1": "V", "p2": "B", "value": 60.0}],
  "given": {"line_AB": "8 cm", "line_VA": "10 cm"},
  "asked": ["angle_VAB"]
}
Coordinate rules (axes=false):
- Place base polygon on XY-plane (Z=0); height in +Z direction
- Map first given length to 4.0-5.0 units; compute all coords with 3D geometry
- Hidden edges: "style": "dashed"
- Faces: list points in CCW order when viewed from outside (right-hand rule)

=== SCHEMA B: axes=true (coordinate 3D geometry) ===
{
  "dimension": "3d",
  "axes": true,
  "grid": false,
  "coordinate_range": {"x_min": -1.0, "x_max": 6.0, "y_min": -1.0, "y_max": 5.0, "z_min": -1.0, "z_max": 8.0},
  "scale": {"reference": "auto", "real": "1 unit", "units": 1.0},
  "points": {"A": [1.0, 2.0, 3.0], "B": [4.0, 0.0, 1.0], "O": [0.0, 0.0, 0.0]},
  "lines": [{"id": "line_AB", "from": "A", "to": "B"}],
  "planes": [
    {"id": "plane_P1", "equation": "2x + y - z = 4",
     "vertices": [[2.0,0.0,0.0],[0.0,4.0,0.0],[0.0,0.0,-4.0],[1.0,2.0,0.0]]}
  ],
  "spheres": [{"id": "sphere_S1", "center": "C", "radius": 5.0}],
  "vectors": [{"id": "vec_OA", "from": "O", "to": "A", "components": [1.0, 2.0, 3.0]}],
  "faces": [{"id": "face_section", "points": ["P1", "P2", "P3"]}],
  "angles": [{"id": "angle_dihedral", "vertex": "B", "p1": "A", "p2": "C", "value": 60.0}],
  "given": {"point_A": "A(1, 2, 3)", "plane_P1": "2x + y - z = 4"},
  "asked": ["distance_AB"]
}
Coordinate rules (axes=true):
- Use EXACT (x,y,z) coordinates from question as [X, Y, Z]; do NOT rescale
- coordinate_range: cover all geometry with ~15% padding in all 3 dimensions
- planes: include equation string + 3-4 pre-computed boundary vertices (axis intercepts or clipped corners)
- spheres: point ID for center (must exist in "points") + scalar radius
- vectors: from/to point IDs + components array
- grid: false for 3D unless specifically a grid problem

Common rules (both schemas):
- "given": only data explicitly stated in the question
- "asked": element IDs to highlight with "?"
- Output ONLY the JSON object, no explanation or markdown
"""


# ======================================================================
# ADAPTIVE STAGE 2: Blueprint → Code (2-way: 2D matplotlib or 3D manim)
#
# Each prompt reads blueprint["axes"] and branches between:
#   axes=false → traditional rendering (auto-fit, no grid)
#   axes=true  → coordinate rendering (coordinate_range viewport, axes/grid/curves)
# ======================================================================

Blueprint_to_Code_2D_Adaptive = """You are a Python visualization expert. Convert a JSON geometry blueprint into a matplotlib script.

Read `blueprint["axes"]` FIRST — it determines which rendering mode to use.

## MANDATORY Imports

```python
#!/usr/bin/env python3
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from pathlib import Path
from matplotlib_helpers import draw_angle_arc, draw_right_angle_marker, draw_coordinate_axes
```

NEVER use `matplotlib.patheffects`.

## Figure Setup (both modes)

```python
fig, ax = plt.subplots(figsize=(8.54, 4.80), dpi=100)
fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
fig.patch.set_facecolor('#FFFFFF')
ax.set_facecolor('#FFFFFF')
ax.set_aspect('equal')
ax.axis('off')
```

## Styling (both modes)

- Points: `#1A1A1A`, markersize=8
- Lines: cycle `#2A9D8F`, `#264653`, `#457B9D`, `#6A4C93`, `#E76F51`, linewidth=2.0
- Given labels: values from `given` dict (e.g. "12 cm", "y = 2x+1")
- Asked elements: color `#E63946`, linewidth×2, label `"?"`
- Asked glow: two overlapping plots — `(linewidth=8, alpha=0.2, #E63946, zorder=1)` then `(linewidth=4, #E63946, zorder=2)`

## Label Validation (CRITICAL — both modes)

✅ Render: point names ("A", "B"), measurements ("6 cm", "90°"), short equations ("y = 2x+1"), "?"
❌ Never: sentences, phrases, question text, coordinates embedded in point labels ("A(2,3)")

## ── MODE: axes=false (Traditional Geometry) ──

```python
# Drop Z coordinate — use X,Y only
points = {
    "A": np.array([0.0, 0.0]),
    "B": np.array([5.0, 0.0]),
    # ...
}

# Scale-aware sizing
all_x = [p[0] for p in points.values()]
all_y = [p[1] for p in points.values()]
extent = max((max(all_x) - min(all_x)), (max(all_y) - min(all_y)), 1)
LABEL_SIZE   = max(8, min(14, 120 / extent))
ANNOT_SIZE   = max(7, min(12, 100 / extent))
ASKED_SIZE   = max(9, min(16, 140 / extent))
LABEL_OFFSET = extent * 0.04
ANNOT_OFFSET = extent * 0.05

# Drawing order: faces(z=0) → lines(z=1-2) → angle arcs(z=3) → points(z=4) → labels(z=5)

# Angle arcs — ALWAYS use helpers, NEVER implement arc math
draw_angle_arc(ax, vertex=points["B"], p1=points["A"], p2=points["C"],
               expected_degrees=75.0, radius=0.6, color='#264653', linewidth=1.5,
               zorder=3, label="75°", label_fontsize=ANNOT_SIZE)
draw_right_angle_marker(ax, vertex=points["C"], p1=points["A"], p2=points["B"],
                        size=extent * 0.06, color='#264653', linewidth=1.5, zorder=3)
# For asked angles: expected_degrees=None, color='#E63946', label="?", label_fontweight='bold'

# Landscape auto-fit viewport
padding = 0.35
x_range = max(all_x) - min(all_x) or 1
y_range = max(all_y) - min(all_y) or 1
target_ratio = 8.54 / 4.80
x_center = (min(all_x) + max(all_x)) / 2
y_center = (min(all_y) + max(all_y)) / 2
if x_range / y_range < target_ratio:
    x_range = y_range * target_ratio
else:
    y_range = x_range / target_ratio
ax.set_xlim(x_center - x_range / 2 * (1 + padding), x_center + x_range / 2 * (1 + padding))
ax.set_ylim(y_center - y_range / 2 * (1 + padding), y_center + y_range / 2 * (1 + padding))
```

## ── MODE: axes=true (Coordinate Geometry) ──

```python
# Exact coordinates — NO rescaling
points = {
    "A": np.array([2.0, 3.0]),
    "O": np.array([0.0, 0.0]),
    # ...
}

# Coordinate range from blueprint (NEVER auto-fit)
x_min, x_max = -1.0, 8.0   # hardcode from blueprint
y_min, y_max = -2.0, 6.0

ax.set_xlim(x_min, x_max)
ax.set_ylim(y_min, y_max)

# Scale-aware sizing from coordinate_range
extent = max((x_max - x_min), (y_max - y_min), 1)
LABEL_SIZE   = max(8, min(14, 120 / extent))
ANNOT_SIZE   = max(7, min(12, 100 / extent))
ASKED_SIZE   = max(9, min(16, 140 / extent))
LABEL_OFFSET = extent * 0.04
ANNOT_OFFSET = extent * 0.05

# Fix 1: Enable tick labels (ax.axis('off') suppresses them — re-enable for coordinate mode)
ax.tick_params(left=True, bottom=True, labelleft=True, labelbottom=True)
for spine in ax.spines.values():
    spine.set_visible(False)  # draw_coordinate_axes draws the arrow axes; hide default spines

# Draw coordinate axes (always when axes=true)
draw_coordinate_axes(ax, x_min, x_max, y_min, y_max, arrow_size=0.15, zorder=0)

# Draw grid if blueprint["grid"] == true
x_tick = max(1, round((x_max - x_min) / 12))
y_tick = max(1, round((y_max - y_min) / 12))
ax.set_xticks(np.arange(np.floor(x_min), np.ceil(x_max) + 1, x_tick))
ax.set_yticks(np.arange(np.floor(y_min), np.ceil(y_max) + 1, y_tick))
ax.grid(True, alpha=0.3, color='#E0E0E0', linewidth=0.5, zorder=0)
ax.tick_params(labelsize=9, colors='#1A1A1A')

# Curves — use pre-sampled points from blueprint (NO equation parsing)
# {"id":"curve_1","equation":"y=x^2-4x+3","points":[[0,3],[1,0],[2,-1],[3,0],[4,3]]}
curve_pts = np.array([[0.0,3.0],[1.0,0.0],[2.0,-1.0],[3.0,0.0],[4.0,3.0]])
ax.plot(curve_pts[:,0], curve_pts[:,1], color='#2A9D8F', linewidth=2.5, zorder=2)
# Label near last point — ax.text(curve_pts[-1,0]+0.2, curve_pts[-1,1], "y=x²-4x+3", ...)

# Fix 2: Circles — use patches.Circle with exact center + radius (NEVER plot as curve)
# {"id":"circle_O","center":"O","radius":5.0}  — center is a key in points dict
# cx, cy = points["O"]  (or use hardcoded values if center not in points)
circle = patches.Circle(
    (cx, cy), radius=r,
    fill=False, edgecolor='#2A9D8F', linewidth=2.0, zorder=2
)
ax.add_patch(circle)
# Equation label near top of circle
ax.text(cx, cy + r + LABEL_OFFSET, "x²+y²=25",
        fontsize=ANNOT_SIZE, ha='center', color='#2A9D8F', zorder=5)

# Fix 3: Reference lines — dashed lines from a point to the axes
# Draw when a line has style="reference" or connects a point to an axis intercept
# Drops from point P(px, py) down to x-axis and across to y-axis
ax.plot([px, px], [0, py], color='#AAAAAA', linewidth=1.0, linestyle='--', alpha=0.7, zorder=1)
ax.plot([0, px], [py, py], color='#AAAAAA', linewidth=1.0, linestyle='--', alpha=0.7, zorder=1)

# Shaded regions (faces with "style":"shaded")
verts = [points["P1"], points["P2"], points["P3"]]
ax.add_patch(patches.Polygon(verts, closed=True, facecolor='#2A9D8F', alpha=0.15, zorder=0))

# Drawing order: regions(z=0) → curves/lines(z=1-2) → circles(z=2) → arcs(z=3) → points(z=4) → labels(z=5)
```

## Save (both modes)

```python
Path("OUTPUT_PATH").parent.mkdir(parents=True, exist_ok=True)
plt.savefig("OUTPUT_PATH", dpi=100, facecolor='white')
plt.close()
print("Saved: OUTPUT_PATH")
```

## Critical Rules

1. Read `blueprint["axes"]` FIRST to determine mode
2. axes=false: auto-fit viewport (padding=0.35), scale-based coords, NO grid, NO axes lines
3. axes=true: use `coordinate_range` for xlim/ylim, draw axes via `draw_coordinate_axes`, optional grid, render curves from pre-sampled points
4. NEVER auto-fit when axes=true; NEVER use coordinate_range when axes=false
5. NEVER use `bbox_inches='tight'` in savefig
6. NEVER implement angle arc math — always call `draw_angle_arc` or `draw_right_angle_marker`
7. NEVER use `matplotlib.patheffects`
8. ALWAYS use scale-aware sizes (LABEL_SIZE, ANNOT_SIZE, ASKED_SIZE) — never hardcode fontsize
9. VALID VARIABLE NAMES: letters, digits, underscores only — NO `?pos` or special chars in names
10. Output exactly ONE ```python code block
11. axes=true: call `ax.tick_params(left=True, bottom=True, labelleft=True, labelbottom=True)` then hide spines — tick labels are suppressed by `ax.axis('off')` and must be re-enabled
12. axes=true: render `circles` with `patches.Circle((cx,cy), radius, fill=False)` — NEVER plot a circle as a sampled curve; NEVER skip circles present in the blueprint
"""


Blueprint_to_Code_3D_Adaptive = """You are a Python 3D visualization expert. Convert a JSON geometry blueprint into a manim script.

Read `blueprint["axes"]` FIRST — it determines which rendering mode to use.

## MANDATORY Script Header (both modes — ALWAYS include in this exact order)

```python
#!/usr/bin/env python3
from manim import *
import numpy as np
import shutil
from pathlib import Path
from manim_helpers import (
    create_3d_angle_arc_with_connections,
    create_3d_coordinate_axes,
    create_sphere_wireframe,
)

config.background_color = "#FFFFFF"
config.pixel_height = 360
config.pixel_width = 640
config.frame_rate = 10
config.format = "gif"
config.output_file = "diagram"
```

**CRITICAL**: The 6 `config.*` lines MUST appear at module level, immediately after the imports and BEFORE any function or class definition. If they are missing or placed inside a class, the background will be black and resolution will be wrong.

## Styling (both modes)

- Background: `#FFFFFF`
- Points: `Dot3D(color="#1A1A1A", radius=0.06)`
- Labels: `Text("A", color="#1A1A1A").scale(0.8)` via `add_fixed_orientation_mobjects`
- Lines: `Line3D(start, end, color=HEX, thickness=0.02)`
- Dashed: `DashedLine(start, end, color=HEX, dash_length=0.15)` — NEVER `DashedVMobject(Line3D(...))`
- Faces: `Polygon(*pts, fill_opacity=0.08, stroke_opacity=0.3)`
- Asked elements: `#E63946`, 2x thickness, `"?"` label

## Label Validation (CRITICAL — both modes)

✅ Render: point names ("A", "B"), measurements ("6 cm", "90°"), equations ("2x+y-z=4"), "?"
❌ Never: coordinates in point labels ("A(1,2,3)"), sentences, question text

## ── MODE: axes=false (Traditional 3D Geometry — centroid scaling) ──

```python
pts_raw = {
    "A": np.array([0.0, 0.0, 0.0]),
    "B": np.array([4.0, 0.0, 0.0]),
    # ... ALL values must be floats
}

# Centroid-based adaptive scaling (ensures figure fits during full 360° rotation)
all_coords = np.array(list(pts_raw.values()))
centroid = np.mean(all_coords, axis=0)
centered = all_coords - centroid
max_radius = max(np.linalg.norm(c) for c in centered)
TARGET_SIZE = 3.5
SCALE_FACTOR = min(1.5, TARGET_SIZE / max_radius) if max_radius > 0 else 1.0
pts = {k: (v - centroid) * SCALE_FACTOR for k, v in pts_raw.items()}

LABEL_OFFSET = max(0.2, min(0.4, 0.35 / SCALE_FACTOR))

class GeometryScene(ThreeDScene):
    def construct(self):
        self.set_camera_orientation(phi=65*DEGREES, theta=-45*DEGREES, zoom=0.7)

        # Draw faces (fill_opacity=0.08, stroke_opacity=0.3)
        # Draw solid lines (Line3D) and dashed lines (DashedLine)
        # Draw angle arcs (create_3d_angle_arc_with_connections)
        # Draw points (Dot3D)
        # Draw labels (Text, self.add_fixed_orientation_mobjects(label) — NO .rotate() before it)
        # NO coordinate axes shown in this mode

        self.begin_ambient_camera_rotation(rate=TAU/4)  # Full 360° in 4 seconds
        self.wait(4)
```

Labels (axes=false) — billboard, always face camera:
```python
label = Text("A", color="#1A1A1A").scale(0.8)
label.move_to(pts["A"] + np.array([LABEL_OFFSET, LABEL_OFFSET, LABEL_OFFSET]))
self.add_fixed_orientation_mobjects(label)  # NO .rotate() before this
```

Angle arcs (axes=false):
```python
arc = create_3d_angle_arc_with_connections(
    center=pts["V"], point1=pts["A"], point2=pts["B"],
    radius=0.5, color="#264653"   # use "#E63946" for asked angles
)
self.add(arc)
```

## ── MODE: axes=true (Coordinate 3D Geometry — center+scale, then draw axes) ──

```python
# Raw coordinates from blueprint — ALL floats
pts_raw = {
    "A": np.array([1.0, 2.0, 3.0]),
    "O": np.array([0.0, 0.0, 0.0]),
    # ...
}

# Coordinate range from blueprint
x_min, x_max = -1.0, 6.0
y_min, y_max = -1.0, 5.0
z_min, z_max = -1.0, 8.0

# Center + scale ALL geometry so the scene fits inside the camera frame.
# DO NOT use camera.frame_center — it does not work reliably in manim ThreeDScene.
data_center = np.array([(x_min + x_max) / 2.0,
                         (y_min + y_max) / 2.0,
                         (z_min + z_max) / 2.0], dtype=float)
max_extent = max(x_max - x_min, y_max - y_min, z_max - z_min, 1.0)
COORD_SCALE = min(1.5, 7.0 / max_extent)   # map largest dimension to ~7 manim units

pts = {k: (v - data_center) * COORD_SCALE for k, v in pts_raw.items()}

# Scale the coordinate ranges for the axis helper
x_min_s = (x_min - data_center[0]) * COORD_SCALE
x_max_s = (x_max - data_center[0]) * COORD_SCALE
y_min_s = (y_min - data_center[1]) * COORD_SCALE
y_max_s = (y_max - data_center[1]) * COORD_SCALE
z_min_s = (z_min - data_center[2]) * COORD_SCALE
z_max_s = (z_max - data_center[2]) * COORD_SCALE

# Plane bounding-box clip helper — place OUTSIDE the class, at module level
def plane_polygon_verts(normal, d_orig, xr, yr, zr, center, scale):
    # Transform plane equation ax+by+cz=d to shifted/scaled space, clip to box.
    a, b, c = float(normal[0]), float(normal[1]), float(normal[2])
    d = d_orig - a*center[0] - b*center[1] - c*center[2]
    d *= scale
    a_s, b_s, c_s = a / scale, b / scale, c / scale   # normal in scaled space
    pts_out = []
    for y in [yr[0], yr[1]]:
        for z in [zr[0], zr[1]]:
            if abs(a_s) > 1e-9:
                x = (d/scale - b_s*y - c_s*z) / a_s
                if xr[0] <= x <= xr[1]: pts_out.append(np.array([x, y, z], dtype=float))
    for x in [xr[0], xr[1]]:
        for z in [zr[0], zr[1]]:
            if abs(b_s) > 1e-9:
                y = (d/scale - a_s*x - c_s*z) / b_s
                if yr[0] <= y <= yr[1]: pts_out.append(np.array([x, y, z], dtype=float))
    for x in [xr[0], xr[1]]:
        for y in [yr[0], yr[1]]:
            if abs(c_s) > 1e-9:
                z = (d/scale - a_s*x - b_s*y) / c_s
                if zr[0] <= z <= zr[1]: pts_out.append(np.array([x, y, z], dtype=float))
    if len(pts_out) < 3:
        return pts_out
    ctr = sum(pts_out) / len(pts_out)
    n_hat = np.array([a, b, c], dtype=float)
    n_hat /= (np.linalg.norm(n_hat) + 1e-9)
    u = pts_out[0] - ctr
    u -= np.dot(u, n_hat) * n_hat
    u /= (np.linalg.norm(u) + 1e-9)
    v = np.cross(n_hat, u)
    return sorted(pts_out, key=lambda p: np.arctan2(np.dot(p - ctr, v), np.dot(p - ctr, u)))

class GeometryScene(ThreeDScene):
    def construct(self):
        self.set_camera_orientation(phi=65*DEGREES, theta=-45*DEGREES, zoom=0.9)

        # Draw 3D coordinate axes spanning the scaled range
        axes_group, ax_labels = create_3d_coordinate_axes(
            (x_min_s, x_max_s), (y_min_s, y_max_s), (z_min_s, z_max_s)
        )
        self.add(axes_group)
        self.add_fixed_orientation_mobjects(*ax_labels)

        # Planes — clip to scaled bounding box, then label with equation
        # {"id":"plane_P1","equation":"2x+y-z=4","normal":[2,1,-1]}
        verts = plane_polygon_verts([2.0,1.0,-1.0], 4.0,
                                    (x_min_s,x_max_s), (y_min_s,y_max_s), (z_min_s,z_max_s),
                                    data_center, COORD_SCALE)
        if len(verts) >= 3:
            plane = Polygon(*verts, color="#2A9D8F", fill_opacity=0.15, stroke_opacity=0.5)
            self.add(plane)
            # Equation label — ALWAYS label planes with their equation
            plane_label = Text("2x+y-z=4", color="#2A9D8F").scale(0.45)
            plane_label.move_to(sum(verts)/len(verts) + np.array([0.3, 0.3, 0.3]))
            self.add_fixed_orientation_mobjects(plane_label)

        # Spheres — wireframe circles (apply center shift + scale)
        # {"id":"sphere_S1","center":"C","radius":5.0}
        wireframe = create_sphere_wireframe(
            center=pts["C"],
            radius=5.0 * COORD_SCALE,
            color="#457B9D", stroke_opacity=0.6
        )
        self.add(wireframe)

        # Vectors — Arrow3D
        # {"id":"vec_OA","from":"O","to":"A"}
        arrow = Arrow3D(start=pts["O"], end=pts["A"], color="#E76F51", thickness=0.025)
        self.add(arrow)

        # Lines, points, labels — same pattern as axes=false mode

        self.begin_ambient_camera_rotation(rate=TAU/4)  # Full 360° in 4 seconds
        self.wait(4)
```

## Post-Render (both modes)

```python
output_dir = Path("OUTPUT_PATH").parent
output_dir.mkdir(parents=True, exist_ok=True)
media_dir = Path("media/videos/diagram/360p10")
if media_dir.exists():
    for gif_file in media_dir.glob("*.gif"):
        shutil.move(str(gif_file), "OUTPUT_PATH")
        print("Saved: OUTPUT_PATH")
        break
```

## Critical Rules

1. Read `blueprint["axes"]` FIRST to determine mode
2. **Config FIRST**: the 6 `config.*` lines MUST appear at module level immediately after imports — BEFORE any `def` or `class`. Missing config = black background + wrong resolution.
3. axes=false: centroid scaling (TARGET_SIZE=3.5), NO coordinate axes rendered
4. axes=true: apply `data_center` + `COORD_SCALE` to ALL pts; use scaled ranges for `create_3d_coordinate_axes`; NEVER use `self.camera.frame_center` (unreliable in ThreeDScene)
5. axes=true planes: use `plane_polygon_verts(normal, d_orig, xr, yr, zr, data_center, COORD_SCALE)` — pass both `data_center` and `COORD_SCALE`; ALWAYS add a `Text` equation label to every plane
6. axes=true spheres: apply `COORD_SCALE` to the radius: `radius = blueprint_radius * COORD_SCALE`
7. ALWAYS use float arrays: `np.array([1.0, 0.0, 0.0])` NOT `np.array([1, 0, 0])`
8. Non-existent classes: `Polyline`, `DashedLine3D`, `Arc3D`, `Prism` do NOT exist in manim
9. Use `fill_opacity`/`stroke_opacity` NOT `opacity`
10. Line3D params: only `Line3D(start, end, color=, thickness=)` — NO `radius=`
11. Dashed: `DashedLine(start, end, ...)` — NEVER `DashedVMobject(Line3D(...))`
12. Text not MathTex — no LaTeX
13. Cone: base at reference point, `direction=` points toward apex
14. VALID VARIABLE NAMES: letters, digits, underscores only — NO special chars
15. Output exactly ONE ```python code block
"""


# ======================================================================
# Adaptive Prompt Selection Helpers
# ======================================================================

def get_adaptive_blueprint_prompt(dimension_type):
    # type: (str) -> str
    """Get the adaptive Stage 1 blueprint prompt for a given dimension type.

    The adaptive prompts accept "2d" or "3d" only (not coordinate_2d/3d).
    The LLM decides internally whether axes=true based on question content.

    Args:
        dimension_type: "2d" or "3d"

    Returns:
        The corresponding adaptive blueprint prompt string
    """
    # Map coordinate types to their base dimension
    _base = dimension_type.replace("coordinate_", "")
    prompts = {
        "2d": Question_to_Blueprint_2D_Adaptive,
        "3d": Question_to_Blueprint_3D_Adaptive,
    }
    if _base not in prompts:
        raise ValueError(
            "Unknown dimension type: {}. Must be '2d' or '3d' (or 'coordinate_2d'/'coordinate_3d').".format(
                dimension_type
            )
        )
    return prompts[_base]


def get_adaptive_code_prompt(dimension_type):
    # type: (str) -> str
    """Get the adaptive Stage 2 code generation prompt for a given dimension type.

    The adaptive prompts read blueprint["axes"] to branch between
    traditional and coordinate rendering automatically.

    Args:
        dimension_type: "2d" or "3d" (coordinate_2d/3d also accepted, mapped to base)

    Returns:
        The corresponding adaptive code generation prompt string
    """
    _base = dimension_type.replace("coordinate_", "")
    prompts = {
        "2d": Blueprint_to_Code_2D_Adaptive,
        "3d": Blueprint_to_Code_3D_Adaptive,
    }
    if _base not in prompts:
        raise ValueError(
            "Unknown dimension type: {}. Must be '2d' or '3d'.".format(dimension_type)
        )
    return prompts[_base]
