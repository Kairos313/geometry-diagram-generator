# Coordinate Geometry Feature — Implementation Plan

> **Context:** This plan extends the existing geometry diagram pipeline to support HKDSE coordinate geometry problems (2D graphs, equations of lines/circles, linear programming, loci, graph transformations). The current pipeline generates synthetic geometry diagrams (triangles, prisms, etc.) via a 2-stage LLM pipeline: Question → Blueprint → Generated Code → Rendered Image.
>
> **Target exam:** HKDSE Mathematics Compulsory Part + Module 2 (Algebra & Calculus)
>
> **Current codebase:** `Geometry_v2/Geometry Test Questions/Full_Pipeline/`

---

## Architecture Decision: New Dimension Type

Add a third dimension type `coordinate` alongside `2d` and `3d`. Coordinate geometry problems differ fundamentally from synthetic geometry:

- They need **axes, grids, tick marks** (synthetic geometry has none)
- They plot **equations and functions**, not just point-to-point segments
- They use **algebraic labels** (`y = 2x + 3`) not geometric labels (`AB = 5 cm`)
- They may need **region shading** (linear programming) and **curve families**

The `coordinate` type always renders with matplotlib (like `2d`) but uses a completely different code generation prompt section.

---

## Phase 1: Pipeline Plumbing (do this first)

### Task 1.1: Add dimension detection for `coordinate` type

**File:** `generate_code.py`

In the `detect_dimension()` function, add detection for the new type. The blueprint will contain `DIMENSION: COORDINATE_2D`.

```python
# After the existing regex match for 2D/3D, add:
# Check for COORDINATE_2D or COORDINATE_3D
coord_match = re.search(r'\*{0,2}DIMENSION:\s*(COORDINATE_2D|COORDINATE_3D)\*{0,2}', blueprint_text, re.IGNORECASE)
if coord_match:
    return coord_match.group(1).lower()  # "coordinate_2d" or "coordinate_3d"
```

Update the routing logic below it:

```python
dimension_type = detect_dimension(blueprint_text)

if dimension_type == "coordinate_2d":
    target_library = "matplotlib"
    output_format = "png"
    prompt_section = "coordinate"  # NEW — selects coordinate-specific code gen prompt
elif dimension_type == "3d":
    target_library = "manim"
    output_format = "gif"
    prompt_section = "geometry_3d"
else:
    target_library = "matplotlib"
    output_format = "png"
    prompt_section = "geometry_2d"
```

### Task 1.2: Add prompt routing in `generate_code.py`

The `generate_code()` function currently sends the full `Blueprint_to_Code_Gemini` prompt for all problems. Add conditional prompt selection:

```python
from diagram_prompts import Blueprint_to_Code_Gemini, Blueprint_to_Code_Coordinate  # NEW import

if prompt_section == "coordinate":
    system_prompt = Blueprint_to_Code_Coordinate
else:
    system_prompt = Blueprint_to_Code_Gemini
```

### Task 1.3: Update `geometry_pipeline.py` orchestrator

No structural changes needed — the orchestrator calls Stage 1 then Stage 2 via subprocess. But update the CLI to accept `--problem-type` hint (optional):

```python
parser.add_argument('--problem-type', choices=['geometry', 'coordinate', 'auto'], default='auto',
                    help='Hint for problem classification')
```

Pass this to `generate_blueprint.py` as an argument so it can select the right blueprint prompt section.

---

## Phase 2: Blueprint Prompt Extension (Stage 1)

### Task 2.1: Extend `Question_to_Blueprint` in `diagram_prompts.py`

Add a new section to the existing `Question_to_Blueprint` prompt that handles coordinate geometry problems. Insert this **after the existing geometry blueprint instructions** but **before the closing instructions**.

The new section should instruct the LLM to output the following additional blueprint blocks when the problem involves coordinate geometry:

```markdown
### COORDINATE GEOMETRY BLUEPRINT ADDITIONS

When the question involves equations, graphs, coordinate axes, locus, or linear programming,
output `DIMENSION: COORDINATE_2D` and include these additional sections:

**F. Axis Configuration:**

| Axis | Min | Max | Step | Label |
| :--- | :--- | :--- | :--- | :--- |
| X | -2 | 8 | 1 | x |
| Y | -3 | 6 | 1 | y |

**G. Equations / Curves to Plot:**

| ID | Type | Equation | Domain | Style | Color | Category |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| eq_1 | line | y = 2x + 1 | [-2, 8] | solid | #2A9D8F | given |
| eq_2 | circle | (x-3)^2 + (y-2)^2 = 16 | full | solid | #264653 | given |
| eq_3 | parabola | y = x^2 - 4x + 3 | [-1, 5] | solid | #457B9D | derived |

**H. Special Points (intersections, vertices, tangent points):**

| Point | X | Y | Label | Category | Calculation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| P1 | 1.0 | 3.0 | A | given | Given point |
| P2 | 3.0 | 0.0 | — | derived | x-intercept of eq_1 |
| P3 | 5.0 | 2.0 | — | asked | Intersection of eq_1 and eq_2 |

**I. Regions (for linear programming / inequalities):**

| Region ID | Bounded By | Inequality | Shade Color | Opacity |
| :--- | :--- | :--- | :--- | :--- |
| region_1 | eq_1, eq_4, x-axis | y ≤ 2x+1 AND y ≥ 0 AND x ≤ 5 | #2A9D8F | 0.15 |

**J. Annotations (distances, angles, tangent lines):**

| Element | Type | From | To | Label | Category |
| :--- | :--- | :--- | :--- | :--- | :--- |
| ann_1 | distance | P1 | P2 | "?" | asked |
| ann_2 | tangent_line | — | — | tangent at P3 | derived |
| ann_3 | angle_mark | — | — | θ | asked |

**K. Display Features:**

- grid: true
- axis_arrows: true
- axis_equal: false (set true for circles)
- origin_visible: true
```

### Task 2.2: Add coordinate geometry examples to the prompt

Add 3 worked examples to the blueprint prompt covering the most common HKDSE patterns:

**Example 1 — Line-Circle intersection:**
```
Question: "A circle C has centre (3, 2) and radius 4. The line L: y = 2x + 1
intersects C at points A and B. Find the coordinates of A and B."

Expected blueprint output with DIMENSION: COORDINATE_2D, axis config,
equations table with the line and circle, special points for A and B marked as "asked".
```

**Example 2 — Linear programming:**
```
Question: "Maximize P = 3x + 2y subject to: x + y ≤ 6, 2x + y ≤ 8, x ≥ 0, y ≥ 0"

Expected blueprint with constraint lines, feasible region shading,
corner points computed, objective function line shown.
```

**Example 3 — Locus:**
```
Question: "A point P moves such that it is equidistant from A(1, 0) and B(5, 0).
Describe and sketch the locus of P."

Expected blueprint with the two fixed points, the locus equation (x = 3),
and the perpendicular bisector drawn.
```

### Task 2.3: Add classification logic to the blueprint prompt

Add this classification instruction near the top of the prompt:

```markdown
### STEP 0: CLASSIFY THE PROBLEM

Before doing anything else, classify the problem:

- If the question mentions: equations of lines, equations of circles, coordinate axes,
  gradients, intercepts, locus/loci, linear programming, inequalities with graphs,
  function graphs, curve sketching, tangent lines to curves, or asks to "sketch/draw
  the graph of" → Set DIMENSION: COORDINATE_2D

- If the question involves: 3D shapes, prisms, pyramids, spheres, angles between planes,
  space diagonals → Set DIMENSION: 3D

- If the question involves: triangles, polygons, circle theorems, angles in circles,
  congruence, similarity (without coordinate axes) → Set DIMENSION: 2D
```

---

## Phase 3: Code Generation Prompt (Stage 2)

### Task 3.1: Create `Blueprint_to_Code_Coordinate` prompt in `diagram_prompts.py`

This is the largest single task. Create a new prompt string variable. It should follow the same structure as `Blueprint_to_Code_Gemini` but with coordinate-geometry-specific rendering instructions.

**Key sections to include in the prompt:**

```markdown
## COORDINATE GEOMETRY CODE GENERATION

You are generating a self-contained matplotlib Python script that renders a coordinate
geometry diagram from the blueprint below.

### MANDATORY STRUCTURE

```python
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from matplotlib.patches import FancyArrowPatch

fig, ax = plt.subplots(1, 1, figsize=(12.8, 7.2), dpi=150)

# 1. CONFIGURE AXES from blueprint Section F
ax.set_xlim(X_MIN - padding, X_MAX + padding)
ax.set_ylim(Y_MIN - padding, Y_MAX + padding)
ax.set_aspect('equal')  # ONLY if blueprint says axis_equal: true
ax.grid(True, alpha=0.3, linestyle='--')
ax.axhline(y=0, color='#1A1A1A', linewidth=0.8)
ax.axvline(x=0, color='#1A1A1A', linewidth=0.8)

# 2. PLOT EQUATIONS from blueprint Section G
# For each equation, parse type and plot accordingly:
# - line: compute two endpoints from domain, plot with ax.plot()
# - circle: use matplotlib.patches.Circle or parametric
# - parabola/function: np.linspace over domain, compute y, ax.plot()

# 3. MARK SPECIAL POINTS from blueprint Section H
# - given points: solid dot, label offset
# - asked points: highlighted with accent color (#E63946)
# - derived points: smaller dot, subtle label

# 4. SHADE REGIONS from blueprint Section I
# - Use ax.fill_between() or ax.fill() with specified opacity

# 5. ADD ANNOTATIONS from blueprint Section J
# - distance: dashed line + label
# - tangent_line: draw tangent, label
# - angle_mark: Arc patch

# 6. STYLING
ax.set_facecolor('#FFFFFF')
fig.patch.set_facecolor('#FFFFFF')
# Remove top and right spines, keep bottom and left
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

plt.savefig('diagram.png', bbox_inches='tight', facecolor='white')
```

### COLOR PALETTE (same as existing pipeline)

- Background: #FFFFFF
- Axes/text: #1A1A1A
- Curve colors (cycle): #2A9D8F, #264653, #457B9D, #6A4C93, #E76F51
- Accent (asked elements): #E63946 with linewidth=2.5
- Region shading: use curve color at 0.15 opacity
- Grid: #CCCCCC at 0.3 opacity

### EQUATION RENDERING PATTERNS

**Lines** (y = mx + c, ax + by = c):
- Parse into slope-intercept form
- Plot over the axis domain with small extension
- Label the equation near the midpoint, offset from the line
- For vertical lines: ax.axvline()

**Circles** ((x-a)² + (y-b)² = r²):
- Use theta = np.linspace(0, 2*np.pi, 200)
- x = a + r*np.cos(theta), y = b + r*np.sin(theta)
- Mark centre with a small dot, label "O" or as specified
- ALWAYS set ax.set_aspect('equal') for circles

**Parabolas / Quadratics** (y = ax² + bx + c):
- Domain from blueprint or auto-compute to show vertex ± context
- Mark vertex with a point
- If axis of symmetry is relevant, draw as dashed line

**General functions** (for Module 2 — curve sketching):
- Plot using np.linspace with 500+ points for smoothness
- Handle discontinuities (tan, 1/x) by splitting domain at asymptotes
- Draw asymptotes as dashed lines with label

### AXIS SMARTNESS RULES

1. Always include the origin in view unless all action is far from it
2. Pad axes by 15% beyond the outermost element
3. Use integer tick marks at the step from blueprint Section F
4. Label axes with arrows at the positive end (use FancyArrowPatch or annotate)
5. For circles: MUST use ax.set_aspect('equal') — non-negotiable
6. Number the tick marks; skip labeling 0 on x-axis if y-axis label conflicts

### ANNOTATION RULES

- Equation labels: place near the curve, offset perpendicular to curve direction
- Point labels: offset by (0.2, 0.2) in data coordinates, use fontsize=11
- Asked elements: #E63946, linewidth=2.5, label with "?" or as specified
- Given elements: standard color, show value label
- Derived elements: draw but do NOT label unless blueprint says to

### LINEAR PROGRAMMING SPECIFICS

- Draw each constraint line across full axis domain
- Shade feasible region using fill_between or Polygon patch
- Mark all corner points of feasible region with dots and coordinate labels
- Draw the objective function line as dashed, labeled with arrow showing optimization direction
- Clearly mark the optimal point with accent color

### LOCUS SPECIFICS

- Draw the fixed elements (points, lines) that define the locus
- Draw the locus itself in accent color if it is the "asked" element
- If the locus is a standard curve (circle, line, parabola), label its equation
- Optionally mark 2-3 sample positions of the moving point to illustrate the locus
```

### Task 3.2: Add 3 code generation examples to the prompt

For each of the 3 blueprint examples from Task 2.2, include the expected generated matplotlib code as a reference example in the prompt. This is critical for code quality — the LLM needs to see the exact coding patterns you expect.

**Example structure in the prompt:**

```markdown
### EXAMPLE 1: Line-Circle Intersection

**Blueprint (abbreviated):**
[paste the blueprint from Task 2.2 Example 1]

**Expected generated code:**
```python
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

fig, ax = plt.subplots(1, 1, figsize=(12.8, 7.2), dpi=150)

# Axes
ax.set_xlim(-2, 9)
ax.set_ylim(-3, 8)
ax.set_aspect('equal')
ax.grid(True, alpha=0.3, linestyle='--', color='#CCCCCC')
ax.axhline(y=0, color='#1A1A1A', linewidth=0.8)
ax.axvline(x=0, color='#1A1A1A', linewidth=0.8)

# Circle: (x-3)^2 + (y-2)^2 = 16
theta = np.linspace(0, 2*np.pi, 200)
cx, cy, r = 3, 2, 4
ax.plot(cx + r*np.cos(theta), cy + r*np.sin(theta), color='#264653', linewidth=1.8)
ax.plot(cx, cy, 'o', color='#264653', markersize=4)
ax.annotate('C(3, 2)', (cx, cy), textcoords="offset points", xytext=(8, -12), fontsize=10, color='#264653')

# Line: y = 2x + 1
x_line = np.linspace(-2, 9, 200)
y_line = 2 * x_line + 1
ax.plot(x_line, y_line, color='#2A9D8F', linewidth=1.8)
ax.annotate('L: y = 2x + 1', (6, 13), fontsize=10, color='#2A9D8F')

# Intersection points (asked) — computed from solving simultaneously
# (These values come from the blueprint Section H)
ax.plot(1.0, 3.0, 'o', color='#E63946', markersize=7, zorder=5)
ax.annotate('A(1, 3)', (1.0, 3.0), textcoords="offset points", xytext=(10, 8), fontsize=11, color='#E63946', fontweight='bold')

ax.plot(5.0, 2.0, 'o', color='#E63946', markersize=7, zorder=5)
ax.annotate('B(5, 2)', (5.0, 2.0), textcoords="offset points", xytext=(10, -12), fontsize=11, color='#E63946', fontweight='bold')

# Styling
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
fig.patch.set_facecolor('#FFFFFF')
ax.set_facecolor('#FFFFFF')

plt.savefig('diagram.png', bbox_inches='tight', facecolor='white', dpi=150)
```
```

---

## Phase 4: Test Questions

### Task 4.1: Create coordinate geometry test set

Create a new file `coordinate_test_questions.py` with test cases organized by HKDSE topic. Use the same structure as the existing test questions in `batch_test.py`.

```python
COORDINATE_TEST_QUESTIONS = [
    # --- EQUATIONS OF STRAIGHT LINES (Unit 10) ---
    {
        "id": "coord_01",
        "question": "Find the equation of the straight line passing through A(2, 3) and B(6, -1). Sketch the line and mark the x-intercept and y-intercept.",
        "expected_type": "coordinate_2d",
        "topic": "straight_lines"
    },
    {
        "id": "coord_02",
        "question": "Two lines L1: 2x + y = 8 and L2: x - y = 1 intersect at point P. Find P and sketch both lines.",
        "expected_type": "coordinate_2d",
        "topic": "straight_lines"
    },
    {
        "id": "coord_03",
        "question": "The line L passes through A(1, 4) and is perpendicular to the line 3x - y + 2 = 0. Find the equation of L and sketch both lines.",
        "expected_type": "coordinate_2d",
        "topic": "straight_lines"
    },

    # --- EQUATIONS OF CIRCLES (Unit 13) ---
    {
        "id": "coord_04",
        "question": "A circle has centre C(3, -2) and passes through the point A(7, 1). Find the equation of the circle and sketch it.",
        "expected_type": "coordinate_2d",
        "topic": "circles"
    },
    {
        "id": "coord_05",
        "question": "The equation of a circle is x² + y² - 6x + 4y - 12 = 0. Find the centre and radius, then sketch the circle.",
        "expected_type": "coordinate_2d",
        "topic": "circles"
    },
    {
        "id": "coord_06",
        "question": "A circle C: (x-2)² + (y-3)² = 25 and the line L: y = x + 4. Find the points of intersection and determine whether L is a tangent, secant, or misses the circle. Sketch the diagram.",
        "expected_type": "coordinate_2d",
        "topic": "circles"
    },
    {
        "id": "coord_07",
        "question": "Find the equation of the tangent to the circle x² + y² = 25 at the point (3, 4). Sketch the circle and the tangent line.",
        "expected_type": "coordinate_2d",
        "topic": "circles"
    },

    # --- LINEAR PROGRAMMING (Unit 8) ---
    {
        "id": "coord_08",
        "question": "Maximize P = 5x + 4y subject to: x + y ≤ 6, 2x + y ≤ 10, x ≥ 0, y ≥ 0. Sketch the feasible region and find the optimal point.",
        "expected_type": "coordinate_2d",
        "topic": "linear_programming"
    },
    {
        "id": "coord_09",
        "question": "A company makes products A and B. Each unit of A requires 2 hours of labour and 1 kg of material. Each unit of B requires 1 hour of labour and 2 kg of material. Available: 100 hours, 80 kg. Profit: $30 per A, $20 per B. Maximize profit. Sketch the constraints and feasible region.",
        "expected_type": "coordinate_2d",
        "topic": "linear_programming"
    },

    # --- LOCI (Unit 12) ---
    {
        "id": "coord_10",
        "question": "A point P moves such that PA = PB where A = (1, 3) and B = (5, 1). Find the equation of the locus of P and sketch it.",
        "expected_type": "coordinate_2d",
        "topic": "loci"
    },
    {
        "id": "coord_11",
        "question": "A point P moves such that its distance from the point A(2, 0) is always 5 units. Find the equation of the locus of P and sketch it.",
        "expected_type": "coordinate_2d",
        "topic": "loci"
    },

    # --- GRAPH TRANSFORMATIONS (Unit 9) ---
    {
        "id": "coord_12",
        "question": "Sketch the graph of y = |2x - 3| and find the coordinates of the vertex.",
        "expected_type": "coordinate_2d",
        "topic": "graph_transformations"
    },
    {
        "id": "coord_13",
        "question": "The graph of y = f(x) = x² is transformed to y = 2f(x-1) + 3. Sketch both the original and transformed graphs on the same axes.",
        "expected_type": "coordinate_2d",
        "topic": "graph_transformations"
    },

    # --- FUNCTIONS & GRAPHS (Unit 2, 3) ---
    {
        "id": "coord_14",
        "question": "Sketch the graph of y = 2^x and y = log₂(x) on the same coordinate plane. Mark their relationship to the line y = x.",
        "expected_type": "coordinate_2d",
        "topic": "functions"
    },
    {
        "id": "coord_15",
        "question": "Sketch the graph of y = x² - 4x + 3. Mark the vertex, axis of symmetry, y-intercept, and x-intercepts.",
        "expected_type": "coordinate_2d",
        "topic": "functions"
    },
]
```

### Task 4.2: Add coordinate tests to `batch_test.py`

Import `COORDINATE_TEST_QUESTIONS` and add them to the test runner. Add a `--topic` filter flag so you can run subsets:

```bash
python batch_test.py --topic straight_lines
python batch_test.py --topic circles
python batch_test.py --topic all
```

---

## Phase 5: Iteration & Quality

### Task 5.1: Run the test suite and fix failures

Run all 15 coordinate test questions. Categorize failures:

1. **Blueprint failures** — LLM generates wrong coordinates, wrong equations, or wrong axis bounds → Fix by adding/improving examples in `Question_to_Blueprint` prompt
2. **Code generation failures** — Generated code has syntax errors or wrong matplotlib API usage → Fix by adding patterns/examples in `Blueprint_to_Code_Coordinate` prompt
3. **Rendering failures** — Code runs but output looks wrong (overlapping labels, wrong aspect ratio, clipped curves) → Fix by adding styling rules to the code gen prompt
4. **Classification failures** — Problem routed to wrong dimension type → Fix classification logic in Task 2.3

### Task 5.2: Common matplotlib pitfalls to preempt in the prompt

Add these as explicit warnings in `Blueprint_to_Code_Coordinate`:

```markdown
### COMMON PITFALLS — AVOID THESE

1. NEVER forget ax.set_aspect('equal') when plotting circles — they will look like ellipses
2. NEVER plot functions outside their mathematical domain (e.g., log(x) for x ≤ 0)
3. ALWAYS clip line plots to the axis domain — don't let them extend infinitely
4. ALWAYS use np.linspace with ≥200 points for smooth curves
5. NEVER place labels at the exact point — offset by at least (8, 8) in annotation points
6. For fill_between with multiple constraints, compute the intersection region explicitly
   using np.minimum / np.maximum — do NOT layer multiple fill_between calls with high opacity
7. Use zorder: grid=0, curves=1, shading=2, points=5, labels=10
8. For tangent lines: compute the tangent analytically, don't approximate with secant
9. Handle the case where a line is vertical (undefined slope) — use ax.axvline()
10. When labeling equations on curves, use ax.annotate with an arrow if the label is far from the curve
```

---

## File Change Summary

| File | Action | What changes |
|------|--------|-------------|
| `generate_code.py` | EDIT | Add `coordinate_2d` detection + prompt routing |
| `diagram_prompts.py` | EDIT | Add coordinate blueprint section to `Question_to_Blueprint` |
| `diagram_prompts.py` | EDIT | Add new `Blueprint_to_Code_Coordinate` prompt (~300 lines) |
| `geometry_pipeline.py` | EDIT (minor) | Add `--problem-type` CLI flag, pass to stage 1 |
| `generate_blueprint.py` | EDIT (minor) | Accept and use `--problem-type` hint |
| `coordinate_test_questions.py` | NEW | 15 test questions across 6 HKDSE topics |
| `batch_test.py` | EDIT | Import coordinate tests, add `--topic` filter |

**No new Python dependencies.** matplotlib and numpy are already installed.

---

## Execution Order

Work through these in sequence. Each phase produces testable output:

```
Phase 1 (Pipeline Plumbing)     → Can detect "coordinate_2d" and route to new prompt
Phase 2 (Blueprint Prompt)      → Questions produce valid coordinate blueprints
Phase 3 (Code Gen Prompt)       → Blueprints produce valid matplotlib code
Phase 4 (Test Questions)        → 15 questions to validate end-to-end
Phase 5 (Iterate)               → Fix failures until ≥80% pass rate
```

**Definition of Done for each phase:**

- Phase 1: A hardcoded coordinate blueprint fed to the pipeline produces a matplotlib script (even if ugly)
- Phase 2: "Find the equation of the line through (1,2) and (3,4)" produces a correct blueprint with DIMENSION: COORDINATE_2D
- Phase 3: The blueprint from Phase 2 produces a clean, correctly rendered diagram
- Phase 4: Test file runs, all questions attempt rendering
- Phase 5: ≥12/15 questions render correctly without manual intervention

---

## Example End-to-End Flow

**Input:**
```
"A circle C has centre (3, 2) and radius 4. The line L: y = 2x + 1 intersects C at two points. Sketch the diagram."
```

**Stage 1 output (coordinates.txt):**
```markdown
=== GEOMETRIC BLUEPRINT - COORDINATES ===

**DIMENSION: COORDINATE_2D**

### Part 3: Geometric Elements Breakdown

**F. Axis Configuration:**
| Axis | Min | Max | Step | Label |
| X | -3 | 9 | 1 | x |
| Y | -3 | 8 | 1 | y |

**G. Equations / Curves to Plot:**
| ID | Type | Equation | Domain | Style | Color | Category |
| eq_1 | circle | (x-3)^2 + (y-2)^2 = 16 | full | solid | #264653 | given |
| eq_2 | line | y = 2x + 1 | [-3, 9] | solid | #2A9D8F | given |

**H. Special Points:**
| Point | X | Y | Label | Category | Calculation |
| C | 3.0 | 2.0 | C(3,2) | given | Centre of circle |
| P1 | -0.6 | -0.2 | A | derived | Intersection |
| P2 | 3.4 | 7.8 | B | derived | Intersection |

**K. Display Features:**
- grid: true
- axis_arrows: true
- axis_equal: true
- origin_visible: true
```

**Stage 2 output:** Self-contained matplotlib script → renders `diagram.png`

**Final output:** A clean coordinate geometry diagram with the circle, line, intersection points labeled, axes with grid, proper aspect ratio.

---

## Future Extensions (not in this plan)

These are deliberately excluded to keep scope tight:

- **3D coordinate geometry** (planes, vectors, 3D lines) — add `COORDINATE_3D` with manim later
- **Curve sketching with calculus** (f'(x), f''(x) overlay) — Module 2, add after core works
- **Animation/locus tracing** — manim-based, separate feature
- **Interactive output** (Plotly/HTML) — future UX upgrade
- **Volume of revolution visualization** — Module 2, 3D feature
