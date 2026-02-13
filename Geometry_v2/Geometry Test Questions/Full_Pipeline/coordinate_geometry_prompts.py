"""
Coordinate Geometry Prompts for Geometry Diagram Pipeline.

This module contains 4 focused prompts for different geometry types:
- Question_to_Blueprint_2D: Traditional 2D geometry (triangles, circles, polygons)
- Question_to_Blueprint_3D: Traditional 3D geometry (pyramids, cones, spheres)
- Question_to_Blueprint_Coordinate_2D: 2D with coordinate system/graphing
- Question_to_Blueprint_Coordinate_3D: 3D with coordinate system/graphing

Plus the comprehensive prompt for backward compatibility:
- Question_to_Blueprint_Compact_All: Auto-detects geometry type (larger prompt)

Use classify_geometry_type.py to determine which prompt to use, or specify explicitly.
"""

# ======================================================================
# STAGE 1 (FOCUSED): Question Text → JSON Blueprint (Specific Types)
# ======================================================================

Question_to_Blueprint_2D = """
You are a computational geometry engine. Analyze this **2D geometry question** and output a **JSON blueprint**.

## Output Format

Return ONLY valid JSON (no markdown, no explanation):

```json
{
  "dimension": "2d",
  "scale": {"reference": "AB", "real": "12 cm", "units": 5.0},
  "points": {
    "A": [0.000, 0.000, 0.000],
    "B": [5.000, 0.000, 0.000]
  },
  "lines": [
    {"id": "line_AB", "from": "A", "to": "B"},
    {"id": "line_BC", "from": "B", "to": "C", "style": "dashed"}
  ],
  "circles": [
    {"id": "circle_O", "center": "O", "radius": 3.5}
  ],
  "arcs": [
    {"id": "arc_AB", "center": "O", "from": "A", "to": "B"}
  ],
  "faces": [
    {"id": "face_ABC", "points": ["A", "B", "C"]}
  ],
  "angles": [
    {"id": "angle_ABC", "vertex": "B", "p1": "A", "p2": "C", "value": 90.0}
  ],
  "given": {
    "line_AB": "12 cm",
    "angle_ABC": "90°"
  },
  "asked": ["line_AC"]
}
```

## Rules

1. **dimension**: Always "2d"
2. **scale**: Map first significant length to 5.0 units
3. **points**: All coordinates [X, Y, Z] with Z=0.000 for 2D
4. **lines**: Every segment. Use `"style": "dashed"` for auxiliary lines
5. **circles**: Center point name + radius in units
6. **arcs**: For partial circles
7. **faces**: Filled regions/polygons in winding order
8. **angles**: Only angles to mark visually (given or asked)
9. **given**: Element IDs → display labels (exactly as in question)
10. **asked**: Element IDs the question asks to find

## Coordinate Computation

- Origin at first logical point [0, 0, 0]
- First edge along positive X-axis
- All points on XY-plane (Z=0)
- Use trigonometry/Pythagorean theorem for coordinates
- Verify computed values match given measurements

Output ONLY the JSON object.
"""


Question_to_Blueprint_3D = """
You are a computational geometry engine. Analyze this **3D geometry question** and output a **JSON blueprint**.

## Output Format

Return ONLY valid JSON (no markdown, no explanation):

```json
{
  "dimension": "3d",
  "scale": {"reference": "AB", "real": "8 cm", "units": 5.0},
  "points": {
    "A": [0.000, 0.000, 0.000],
    "B": [5.000, 0.000, 0.000],
    "V": [2.500, 2.500, 3.750]
  },
  "lines": [
    {"id": "line_AB", "from": "A", "to": "B"},
    {"id": "line_VA", "from": "V", "to": "A"}
  ],
  "circles": [],
  "arcs": [],
  "faces": [
    {"id": "face_ABCD", "points": ["A", "B", "C", "D"]},
    {"id": "face_VAB", "points": ["V", "A", "B"]}
  ],
  "angles": [
    {"id": "angle_VAB", "vertex": "A", "p1": "V", "p2": "B", "value": 45.0}
  ],
  "given": {
    "line_AB": "8 cm",
    "height_V": "6 cm"
  },
  "asked": ["line_VA"]
}
```

## Rules

1. **dimension**: Always "3d"
2. **scale**: Map first significant length to 5.0 units
3. **points**: All coordinates [X, Y, Z] - use non-zero Z for 3D points
4. **lines**: All edges including slant/diagonal lines
5. **faces**: ALL faces of solid with points in winding order
6. **Base on XY-plane**: Base/floor at Z=0, vertical elements extend in +Z
7. **given**: Element IDs → display labels
8. **asked**: Element IDs to find

## Coordinate Computation

- Base center or corner at origin
- Base on XY-plane (Z=0)
- Vertical axis = +Z direction
- Compute all vertices precisely
- List ALL faces of the 3D solid

Output ONLY the JSON object.
"""


Question_to_Blueprint_Coordinate_2D = """
You are a computational geometry engine. Analyze this **2D coordinate geometry question** and output a **JSON blueprint with coordinate axes**.

## Output Format

Return ONLY valid JSON (no markdown, no explanation):

```json
{
  "dimension": "coordinate_2d",
  "scale": {"reference": "AB", "real": "5 units", "units": 5.0},
  "points": {
    "A": [0.000, 0.000, 0.000],
    "B": [3.000, 4.000, 0.000]
  },
  "lines": [
    {"id": "line_AB", "from": "A", "to": "B"},
    {"id": "line_eq1", "equation": "y = 2x + 3"}
  ],
  "circles": [
    {"id": "circle_O", "center": "O", "radius": 5.0}
  ],
  "arcs": [],
  "faces": [
    {"id": "face_ABC", "points": ["A", "B", "C"]}
  ],
  "angles": [],
  "axes": {
    "x": {"min": -1, "max": 7, "label": "x", "show_ticks": true},
    "y": {"min": -1, "max": 5, "label": "y", "show_ticks": true}
  },
  "grid": {
    "major": true,
    "minor": false,
    "style": "dotted"
  },
  "origin": {
    "show": true,
    "marker_style": "cross"
  },
  "display_coordinates": {
    "A": "(0, 0)",
    "B": "(3, 4)"
  },
  "equations": [
    {"id": "eq1", "equation": "y = 2x + 3", "position": "above"}
  ],
  "given": {
    "point_A": "(0, 0)",
    "point_B": "(3, 4)",
    "line_eq1": "y = 2x + 3"
  },
  "asked": ["area_triangle_ABC"]
}
```

## Rules

1. **dimension**: Always "coordinate_2d"
2. **scale**: Scale to fit viewport (first significant distance → 5.0 units)
3. **points**: [X, Y, 0.000] using question's coordinate values (scaled)
4. **lines**: Can reference points OR be defined by equation
5. **axes**: Calculate ranges to fit all points + 20% padding
6. **grid**: Major grid recommended, minor optional
7. **origin**: Show origin marker (cross or dot)
8. **display_coordinates**: Original coordinate values from question
9. **equations**: Labels for lines/curves defined by equations

## Coordinate Handling

- PRESERVE original coordinate values in `display_coordinates`
- Apply scale factor to `points` for rendering
- Example: Question has "A(3, 4)", scale 0.5 →
  - `points`: `"A": [1.5, 2.0, 0.0]`
  - `display_coordinates`: `"A": "(3, 4)"`

## Axes Calculation

- Find min/max of all points
- Add 20% padding
- Round to nice numbers (multiples of 5 or 10)

Output ONLY the JSON object.
"""


Question_to_Blueprint_Coordinate_3D = """
You are a computational geometry engine. Analyze this **3D coordinate geometry question** and output a **JSON blueprint with 3D coordinate axes**.

## Output Format

Return ONLY valid JSON (no markdown, no explanation):

```json
{
  "dimension": "coordinate_3d",
  "scale": {"reference": "OP", "real": "5 units", "units": 5.0},
  "points": {
    "O": [0.000, 0.000, 0.000],
    "P": [1.000, 2.000, 3.000]
  },
  "lines": [
    {"id": "line_OP", "from": "O", "to": "P"}
  ],
  "circles": [],
  "arcs": [],
  "faces": [
    {"id": "plane_xyz", "points": ["A", "B", "C"]}
  ],
  "angles": [],
  "axes": {
    "x": {"min": -1, "max": 5, "label": "x", "show_ticks": true},
    "y": {"min": -1, "max": 5, "label": "y", "show_ticks": true},
    "z": {"min": -1, "max": 5, "label": "z", "show_ticks": true}
  },
  "grid": {
    "major": true,
    "minor": false,
    "style": "dotted"
  },
  "origin": {
    "show": true,
    "marker_style": "cross"
  },
  "display_coordinates": {
    "O": "(0, 0, 0)",
    "P": "(1, 2, 3)"
  },
  "equations": [
    {"id": "plane1", "equation": "x + y + z = 6", "position": "above"}
  ],
  "given": {
    "point_O": "(0, 0, 0)",
    "point_P": "(1, 2, 3)",
    "plane1": "x + y + z = 6"
  },
  "asked": ["distance_OP"]
}
```

## Rules

1. **dimension**: Always "coordinate_3d"
2. **scale**: Scale to fit 3D viewport
3. **points**: [X, Y, Z] using question's coordinate values (scaled)
4. **axes**: Include x, y, z with calculated ranges
5. **grid**: 3D grid on base plane
6. **display_coordinates**: Original (x, y, z) from question
7. **equations**: 3D equations (planes, surfaces)

## Coordinate Handling

Same as coordinate_2d but with Z coordinate.

Output ONLY the JSON object.
"""


# ======================================================================
# STAGE 1 (COMPREHENSIVE): Question Text → JSON Blueprint (All Types)
# ======================================================================

Question_to_Blueprint_Compact_All = """
You are a computational geometry engine. Analyze the geometry question and output a **comprehensive JSON blueprint**.

## GEOMETRY TYPE DETECTION

First, determine which of these 4 types the question is:

1. **"2d"** - Traditional 2D geometry:
   - Triangles, quadrilaterals, circles, polygons (no coordinate system)
   - Example: "Triangle ABC with AB = 12 cm, angle ACB = 90°"

2. **"3d"** - Traditional 3D geometry:
   - Pyramids, cones, spheres, prisms (no coordinate system)
   - Example: "A pyramid with square base ABCD and apex V"

3. **"coordinate_2d"** - 2D with coordinate system:
   - Question mentions specific coordinates like "A(3, 4)" OR "B is at (2, 5)"
   - Graphing/plotting tasks: "Plot the line y = 2x + 3" OR "Graph the circle"
   - Coordinate geometry: "Find distance between A(1,2) and B(4,6)"
   - Any 2D problem involving x,y coordinates or Cartesian plane

4. **"coordinate_3d"** - 3D with coordinate system:
   - Question mentions 3D coordinates like "P(1, 2, 3)"
   - 3D plotting: "Plot the plane x + y + z = 6"
   - Any 3D problem involving x,y,z coordinates

**CRITICAL RULE:** If the question mentions ANY coordinates (even one point like "A(2,3)"),
classify as COORDINATE_2D or COORDINATE_3D, NOT regular 2d/3d.

## OUTPUT FORMAT

Return ONLY valid JSON (no markdown, no explanation):

### For Traditional Geometry (dimension: "2d" or "3d"):

```json
{
  "dimension": "2d" | "3d",
  "scale": {"reference": "AB", "real": "12 cm", "units": 5.0},
  "points": {
    "A": [x, y, z],
    "B": [x, y, z]
  },
  "lines": [
    {"id": "line_AB", "from": "A", "to": "B"},
    {"id": "line_BC", "from": "B", "to": "C", "style": "dashed"}
  ],
  "circles": [
    {"id": "circle_O", "center": "O", "radius": 3.5}
  ],
  "arcs": [
    {"id": "arc_AB", "center": "O", "from": "A", "to": "B"}
  ],
  "faces": [
    {"id": "face_ABC", "points": ["A", "B", "C"]}
  ],
  "angles": [
    {"id": "angle_ABC", "vertex": "B", "p1": "A", "p2": "C", "value": 90.0}
  ],
  "given": {
    "line_AB": "12 cm",
    "angle_ABC": "90°"
  },
  "asked": ["angle_XYZ", "line_PQ"]
}
```

### For Coordinate Geometry (dimension: "coordinate_2d" or "coordinate_3d"):

```json
{
  "dimension": "coordinate_2d" | "coordinate_3d",
  "scale": {"reference": "AB", "real": "12 units", "units": 5.0},
  "points": {
    "A": [x, y, z],
    "B": [x, y, z]
  },
  "lines": [
    {"id": "line_AB", "from": "A", "to": "B"},
    {"id": "line_eq1", "equation": "y = 2x + 3", "style": "solid"}
  ],
  "circles": [
    {"id": "circle_O", "center": "O", "radius": 3.5}
  ],
  "arcs": [
    {"id": "arc_AB", "center": "O", "from": "A", "to": "B"}
  ],
  "faces": [
    {"id": "face_ABC", "points": ["A", "B", "C"]}
  ],
  "angles": [
    {"id": "angle_ABC", "vertex": "B", "p1": "A", "p2": "C", "value": 90.0}
  ],
  "axes": {
    "x": {"min": -10, "max": 10, "label": "x", "show_ticks": true},
    "y": {"min": -10, "max": 10, "label": "y", "show_ticks": true},
    "z": {"min": 0, "max": 10, "label": "z", "show_ticks": true}
  },
  "grid": {
    "major": true,
    "minor": false,
    "style": "dotted"
  },
  "origin": {
    "show": true,
    "marker_style": "cross"
  },
  "display_coordinates": {
    "A": "(0, 0)",
    "B": "(3, 4)"
  },
  "equations": [
    {"id": "line_eq1", "equation": "y = 2x + 3", "position": "above"}
  ],
  "given": {
    "line_AB": "12 units",
    "point_A": "(0, 0)",
    "point_B": "(3, 4)"
  },
  "asked": ["line_PQ", "area_triangle_ABC"]
}
```

## FIELD DESCRIPTIONS

### Core Fields (ALL geometry types):

1. **dimension**: String - One of "2d", "3d", "coordinate_2d", "coordinate_3d"

2. **scale**: Object with:
   - `reference`: First significant length mentioned (e.g., "AB")
   - `real`: Value from question (e.g., "12 cm" or "5 units")
   - `units`: Scaled to 5.0 for rendering

3. **points**: Object mapping point names to [X, Y, Z] coordinates
   - All coordinates as floats with 3 decimal places
   - For 2D problems: Z = 0.000
   - First logical point at origin [0.000, 0.000, 0.000]

4. **lines**: Array of line segments
   - `id`: Unique identifier (e.g., "line_AB")
   - `from`, `to`: Point names (for point-to-point lines)
   - `equation`: Equation string (for lines defined by equations in coordinate geometry)
   - `style`: "solid" (default), "dashed", "dotted"

5. **circles**: Array of circles
   - `id`: Unique identifier
   - `center`: Point name
   - `radius`: Computed radius in scaled units

6. **arcs**: Array of circular arcs
   - `id`: Unique identifier
   - `center`: Point name
   - `from`, `to`: Arc endpoints

7. **faces**: Array of polygonal regions (for filled areas)
   - `id`: Unique identifier
   - `points`: Array of point names in winding order

8. **angles**: Array of angles to mark/annotate
   - `id`: Unique identifier
   - `vertex`: Vertex point name
   - `p1`, `p2`: Two other points defining the angle
   - `value`: Angle value in degrees

9. **given**: Object mapping element IDs to display labels
   - Only include information EXPLICITLY stated in question
   - Examples: `{"line_AB": "12 cm", "angle_ABC": "90°"}`

10. **asked**: Array of element IDs that question asks to find
    - Will be highlighted with accent color and "?" label

### Coordinate Geometry ONLY Fields (coordinate_2d, coordinate_3d):

11. **axes**: Object defining coordinate axes
    - `x`, `y`, `z` (z only for coordinate_3d): Each has:
      - `min`, `max`: Numeric range to display
      - `label`: Axis label text (usually "x", "y", "z")
      - `show_ticks`: Boolean - whether to show tick marks

12. **grid**: Object for grid lines
    - `major`: Boolean - show major grid lines
    - `minor`: Boolean - show minor grid lines
    - `style`: "solid", "dotted", "dashed"

13. **origin**: Object for origin marker
    - `show`: Boolean - whether to show origin marker
    - `marker_style`: "cross", "dot", "circle"

14. **display_coordinates**: Object mapping point names to coordinate strings
    - Shows original question coordinates
    - Must match scaled internal coordinates
    - Examples: `{"A": "(0, 0)", "B": "(3, 4)"}`

15. **equations**: Array of equation annotations
    - `id`: Unique identifier
    - `equation`: Equation string (e.g., "y = 2x + 3", "x² + y² = 25")
    - `position`: "above", "below", "left", "right" (placement hint)

## COORDINATE COMPUTATION RULES

### Traditional Geometry (2d, 3d):
- Place first logical point at origin [0, 0, 0]
- Align first edge along positive X-axis
- Base/floor on XY-plane (Z=0)
- Scale first significant distance to 5.0 units
- Use trigonometry, Pythagorean theorem, etc. to compute all coordinates

### Coordinate Geometry (coordinate_2d, coordinate_3d):
- **PRESERVE coordinate values from question**
- Apply scale factor to fit in viewport (scale first significant distance to 5.0)
- **CRITICAL:** If question says "A(3, 4)", and scale factor is 0.5, then:
  - Internal coordinates: A = [1.5, 2.0, 0.0]
  - Display coordinates: "A": "(3, 4)" (original from question)
- Axes ranges should encompass all points with padding
- Default grid spacing: 1 unit (in question's coordinate system)

## AXES RANGE CALCULATION (Coordinate Geometry)

For coordinate_2d and coordinate_3d:
1. Find min/max of all point coordinates (in question's system)
2. Add 20% padding on each side
3. Round to nice numbers (multiples of 5 or 10)
4. Example: Points range from x=-2 to x=8 → axes x: min=-5, max=10

## CRITICAL RULES

1. **Self-consistency check:** After computing coordinates, verify all given lengths/angles match
2. **Complete elements:** Include EVERY point, line, circle, face mentioned in question
3. **No code:** Output only JSON blueprint, never Python code
4. **Valid JSON:** All strings quoted, no trailing commas, proper nesting
5. **Float precision:** All coordinates with 3 decimal places (e.g., 1.500, not 1.5)
6. **Element IDs:** Use descriptive IDs: line_AB, angle_ABC, circle_O, face_ABC
7. **Coordinate geometry detection:** ANY mention of coordinates → coordinate_2d/coordinate_3d
8. **Display vs Internal:** For coordinate geometry, `display_coordinates` shows question values, `points` has scaled values
9. **Axes only for coordinate:** Only include `axes`, `grid`, `origin`, `display_coordinates`, `equations` when dimension is coordinate_2d or coordinate_3d

## EXAMPLES

### Example 1: Traditional 2D Geometry

**Question:** "Triangle ABC with AB = 12 cm, BC = 5 cm, angle ABC = 90°. Find the length of AC."

**Output:**
```json
{
  "dimension": "2d",
  "scale": {"reference": "AB", "real": "12 cm", "units": 5.0},
  "points": {
    "A": [0.000, 0.000, 0.000],
    "B": [5.000, 0.000, 0.000],
    "C": [5.000, 2.083, 0.000]
  },
  "lines": [
    {"id": "line_AB", "from": "A", "to": "B"},
    {"id": "line_BC", "from": "B", "to": "C"},
    {"id": "line_AC", "from": "A", "to": "C"}
  ],
  "circles": [],
  "arcs": [],
  "faces": [
    {"id": "face_ABC", "points": ["A", "B", "C"]}
  ],
  "angles": [
    {"id": "angle_ABC", "vertex": "B", "p1": "A", "p2": "C", "value": 90.0}
  ],
  "given": {
    "line_AB": "12 cm",
    "line_BC": "5 cm",
    "angle_ABC": "90°"
  },
  "asked": ["line_AC"]
}
```

### Example 2: Coordinate 2D Geometry

**Question:** "Plot points A(0, 0), B(3, 4), and C(6, 0). Draw triangle ABC and find its area."

**Output:**
```json
{
  "dimension": "coordinate_2d",
  "scale": {"reference": "AB", "real": "5 units", "units": 5.0},
  "points": {
    "A": [0.000, 0.000, 0.000],
    "B": [3.000, 4.000, 0.000],
    "C": [6.000, 0.000, 0.000]
  },
  "lines": [
    {"id": "line_AB", "from": "A", "to": "B"},
    {"id": "line_BC", "from": "B", "to": "C"},
    {"id": "line_AC", "from": "A", "to": "C"}
  ],
  "circles": [],
  "arcs": [],
  "faces": [
    {"id": "face_ABC", "points": ["A", "B", "C"]}
  ],
  "angles": [],
  "axes": {
    "x": {"min": -1, "max": 7, "label": "x", "show_ticks": true},
    "y": {"min": -1, "max": 5, "label": "y", "show_ticks": true}
  },
  "grid": {
    "major": true,
    "minor": false,
    "style": "dotted"
  },
  "origin": {
    "show": true,
    "marker_style": "cross"
  },
  "display_coordinates": {
    "A": "(0, 0)",
    "B": "(3, 4)",
    "C": "(6, 0)"
  },
  "equations": [],
  "given": {
    "point_A": "(0, 0)",
    "point_B": "(3, 4)",
    "point_C": "(6, 0)"
  },
  "asked": ["area_triangle_ABC"]
}
```

### Example 3: Coordinate 2D with Equation

**Question:** "Graph the line y = 2x + 3 and find where it intersects the x-axis."

**Output:**
```json
{
  "dimension": "coordinate_2d",
  "scale": {"reference": "viewport", "real": "10 units", "units": 5.0},
  "points": {
    "P1": [-2.500, -2.500, 0.000],
    "P2": [2.500, 7.500, 0.000],
    "X_intercept": [-7.500, 0.000, 0.000]
  },
  "lines": [
    {"id": "line_eq1", "from": "P1", "to": "P2", "equation": "y = 2x + 3"}
  ],
  "circles": [],
  "arcs": [],
  "faces": [],
  "angles": [],
  "axes": {
    "x": {"min": -10, "max": 5, "label": "x", "show_ticks": true},
    "y": {"min": -5, "max": 10, "label": "y", "show_ticks": true}
  },
  "grid": {
    "major": true,
    "minor": false,
    "style": "dotted"
  },
  "origin": {
    "show": true,
    "marker_style": "cross"
  },
  "display_coordinates": {
    "X_intercept": "(-1.5, 0)"
  },
  "equations": [
    {"id": "eq_line", "equation": "y = 2x + 3", "position": "above"}
  ],
  "given": {
    "line_eq1": "y = 2x + 3"
  },
  "asked": ["point_X_intercept"]
}
```

### Example 4: Traditional 3D Geometry

**Question:** "A pyramid has square base ABCD with side length 8 cm and apex V at height 6 cm. Find the slant height."

**Output:**
```json
{
  "dimension": "3d",
  "scale": {"reference": "AB", "real": "8 cm", "units": 5.0},
  "points": {
    "A": [0.000, 0.000, 0.000],
    "B": [5.000, 0.000, 0.000],
    "C": [5.000, 5.000, 0.000],
    "D": [0.000, 5.000, 0.000],
    "V": [2.500, 2.500, 3.750]
  },
  "lines": [
    {"id": "line_AB", "from": "A", "to": "B"},
    {"id": "line_BC", "from": "B", "to": "C"},
    {"id": "line_CD", "from": "C", "to": "D"},
    {"id": "line_DA", "from": "D", "to": "A"},
    {"id": "line_VA", "from": "V", "to": "A"},
    {"id": "line_VB", "from": "V", "to": "B"},
    {"id": "line_VC", "from": "V", "to": "C"},
    {"id": "line_VD", "from": "V", "to": "D"}
  ],
  "circles": [],
  "arcs": [],
  "faces": [
    {"id": "face_ABCD", "points": ["A", "B", "C", "D"]},
    {"id": "face_VAB", "points": ["V", "A", "B"]},
    {"id": "face_VBC", "points": ["V", "B", "C"]},
    {"id": "face_VCD", "points": ["V", "C", "D"]},
    {"id": "face_VDA", "points": ["V", "D", "A"]}
  ],
  "angles": [],
  "given": {
    "line_AB": "8 cm",
    "height_V": "6 cm"
  },
  "asked": ["line_VA"]
}
```

## FINAL CHECKLIST

Before outputting JSON:
- [ ] Correct dimension type selected (2d, 3d, coordinate_2d, coordinate_3d)
- [ ] All points have [X, Y, Z] coordinates with 3 decimal places
- [ ] Scale factor applied consistently
- [ ] For coordinate geometry: axes, grid, origin, display_coordinates included
- [ ] For coordinate geometry: display_coordinates match question's original values
- [ ] All given elements in "given" object with exact question text
- [ ] All asked elements in "asked" array
- [ ] Valid JSON syntax (no trailing commas, proper quotes)
- [ ] Element IDs follow naming convention (line_AB, angle_ABC, etc.)
- [ ] Coordinate geometry fields ONLY present for coordinate_2d/coordinate_3d

**Now analyze the question and output ONLY the JSON blueprint:**
"""


# ======================================================================
# Legacy prompt reference (for comparison)
# ======================================================================

Question_to_Blueprint_Compact_Legacy = """
You are a computational geometry engine. Analyze the geometry question and output a **minimal JSON blueprint**.

## Output Format

Return ONLY valid JSON (no markdown, no explanation):

```json
{
  "dimension": "2d" | "3d",
  "scale": {"reference": "AB", "real": "12 cm", "units": 5.0},
  "points": {
    "A": [x, y, z],
    "B": [x, y, z]
  },
  "lines": [
    {"id": "line_AB", "from": "A", "to": "B"},
    {"id": "line_BC", "from": "B", "to": "C", "style": "dashed"}
  ],
  "circles": [
    {"id": "circle_O", "center": "O", "radius": 3.5}
  ],
  "arcs": [
    {"id": "arc_AB", "center": "O", "from": "A", "to": "B"}
  ],
  "faces": [
    {"id": "face_ABC", "points": ["A", "B", "C"]}
  ],
  "angles": [
    {"id": "angle_ABC", "vertex": "B", "p1": "A", "p2": "C", "value": 90.0}
  ],
  "given": {
    "line_AB": "12 cm",
    "angle_ABC": "90°"
  },
  "asked": ["angle_XYZ", "line_PQ"]
}
```

## Rules

1. **dimension**: Use "2d" if all Z=0, otherwise "3d"
2. **scale**: Map first significant length to 5.0 units (e.g., AB=12cm → units=5.0, factor=5/12)
3. **points**: All coordinates as [X, Y, Z] with 3 decimal places. For 2D, Z=0.000
4. **lines**: Every segment. Add `"style": "dashed"` for hidden/auxiliary lines
5. **circles**: Include center point name and computed radius in units
6. **arcs**: For partial circles (semicircles, etc.)
7. **faces**: For filled regions/polygons. List points in winding order
8. **angles**: Only angles that need visual marking (given or asked). Include computed value in degrees
9. **given**: Map element IDs to their display labels (exactly as stated in question)
10. **asked**: List of element IDs that the question asks to find (will be highlighted, shown with "?")

## Coordinate Computation

- Place first logical point at origin [0, 0, 0]
- Align first edge along positive X-axis
- Base/floor on XY-plane (Z=0)
- Use trigonometry, Pythagorean theorem, etc. to compute all coordinates precisely
- Verify computed lengths/angles match given values

## Critical Rules

- Output ONLY the JSON object, no other text
- All coordinates must be numbers (floats), not strings
- Element IDs use format: line_AB, angle_ABC, circle_O, face_ABC
- Do NOT include derived values in "given" - only explicit question data
- "asked" elements get highlighted with accent color and "?" label (no values)
"""
