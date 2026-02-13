# Geometry Video Generator - Codebase Analysis

> Generated: 2025-02-06
> Branch: geometry_image

---

## 1. Project Structure

```
geometry-video-generator/
├── .claude/                           # Claude Code memory
├── .git/
├── .gitignore
└── Geometry_v2/
    └── Geometry Test Questions/
        └── Full_Pipeline/             # Main codebase
            ├── geometry_pipeline.py   # ENTRY POINT - orchestrator
            ├── generate_blueprint.py  # Stage 1
            ├── generate_code.py       # Stage 2
            ├── render_code.py         # Generated at runtime
            ├── render_geometry.py     # Thin wrapper for re-rendering
            ├── diagram_prompts.py     # LLM prompts (v2 pipeline)
            ├── pipeline_prompts.py    # Legacy prompts (video pipeline)
            ├── manim_helpers.py       # 3D angle arc utilities
            ├── batch_test.py          # Test harness with Flask UI
            ├── demo.py
            ├── test_pipeline.py
            ├── coordinates.txt        # Intermediate blueprint output
            ├── requirements.txt
            ├── .env                   # API keys (GEMINI_API_KEY)
            ├── output/                # Rendered diagrams
            │   └── batch/             # Batch test outputs
            ├── docker/                # Docker sandbox (unused currently)
            ├── media/                 # Manim media cache
            ├── legacy/                # Original 5-step video pipeline
            │   ├── video_pipeline/    # Audio+video generation scripts
            │   ├── renderers/         # matplotlib_2d.py, manim_3d.py
            │   └── README.md
            └── test_output/
```

**Language/Framework:** Python 3.9+ (system Python 3.9, Manim on Python 3.13)

**Entry Point:** `geometry_pipeline.py`

```bash
python3 geometry_pipeline.py --question-text "In triangle ABC, angle ACB = 90°..." --output-format png
```

---

## 2. Pipeline Architecture

The current v2 pipeline is a **2-stage** system:

```
┌─────────────────────┐     ┌────────────────────┐     ┌─────────────────┐
│  Question Text      │     │   coordinates.txt  │     │  PNG/SVG/GIF    │
│  (+ optional image) │────►│   (Blueprint)      │────►│  (final output) │
└─────────────────────┘     └────────────────────┘     └─────────────────┘
        │                           │                           │
        │ Stage 1                   │ Stage 2                   │
        │ generate_blueprint.py     │ generate_code.py          │
        │ Gemini 3 Flash            │ Gemini 3 Flash            │
        │ (thinking_budget=8000)    │ (thinking_budget=4096)    │
```

### Stage 1: Question → Blueprint

- **File:** `generate_blueprint.py` (lines 63-133)
- **LLM:** Gemini 3 Flash Preview (`gemini-3-flash-preview`) via Google GenAI
- **Prompt:** `Question_to_Blueprint` from `diagram_prompts.py` (lines 13-173)
- **Config:** `max_output_tokens=20000`, `temperature=0.1`, `thinking_budget=8000`
- **Output:** `coordinates.txt` - structured blueprint with:
  - Dimension declaration (`DIMENSION: 2D` or `DIMENSION: 3D`)
  - Point coordinate table (X, Y, Z)
  - Lines/edges with calculated lengths
  - Angles with calculated values
  - Faces/surfaces definitions
  - Display rules (given/derived/asked annotations)

### Stage 2: Blueprint → Rendered Diagram

- **File:** `generate_code.py` (lines 82-153)
- **LLM:** Gemini 3 Flash Preview via Google GenAI
- **Prompt:** `Blueprint_to_Code_Gemini` from `diagram_prompts.py` (lines 621-905)
- **Config:** `max_output_tokens=65536`, `temperature=0.0`, `thinking_budget=4096`
- **Output:** `render_code.py` (generated Python script) → executed → `diagram.png/gif`
- **Retry:** 1 retry with error context on execution failure

### Orchestration

- **File:** `geometry_pipeline.py` (lines 35-124)
- Calls stages sequentially via `subprocess.run()`
- Validates intermediate outputs exist

---

## 3. Rendering Layer

### 3.1 2D Diagrams (matplotlib)

- **Library:** matplotlib (via Agg backend)
- **Output formats:** PNG, SVG
- **Resolution:** 1920×1080 @ 150 DPI
- **Color palette:** Light theme with `#FFFFFF` background
  - Points: `#1A1A1A`
  - Lines cycle: `#2A9D8F`, `#264653`, `#457B9D`, `#6A4C93`, `#E76F51`
  - Accent (asked): `#E63946`
- **Execution:** System Python 3.9

### 3.2 3D Diagrams (Manim)

- **Library:** Manim Community (ThreeDScene)
- **Output formats:** GIF (854×480 @ 15fps), MP4
- **Rendering:** Ambient camera rotation animation (360° orbit)
- **Helpers:** `manim_helpers.py`
  - `create_3d_angle_arc_with_connections()` - smooth 3D angle arcs
  - `create_2d_angle_arc_geometric()` - 2D arcs using vector math
- **Execution:** Manim CLI at `/Users/kairos/.local/bin/manim` (Python 3.13)
- **LaTeX:** Not installed — uses `Text()` instead of `MathTex()`

### 3.3 Code Generation Pattern

**Each problem generates fresh code** — there is no shared rendering abstraction. The LLM generates a complete, self-contained `render_code.py` script with hardcoded coordinates and styling. This is intentional:

```
From diagram_prompts.py (Blueprint_to_Code_Gemini):
"Has **no external dependencies** beyond the target library and numpy."
"Completely self-contained — no file reading, no JSON parsing, no helper files"
```

The only shared utility is `manim_helpers.py` for 3D angle arcs (copied to output directory at runtime).

---

## 4. Problem Type Handling (2D vs 3D)

### 4.1 Dimension Detection

**Two-step classification** in `generate_code.py` (lines 39-79):

1. **Explicit declaration (preferred):** Stage 1 blueprint contains `DIMENSION: 2D` or `DIMENSION: 3D`

```python
match = re.search(r'\*{0,2}DIMENSION:\s*(2D|3D)\*{0,2}', blueprint_text, re.IGNORECASE)
```

2. **Fallback - Z-coordinate parsing:** If no declaration, parses point table for non-zero Z values

```python
# Match rows like:  | A | 0.000 | 0.000 | 0.000 | ...
row_pattern = re.compile(r"\|\s*\*{0,2}\w+\*{0,2}\s*\|\s*(-?[\d.]+)\s*\|...")
```

### 4.2 Routing Logic

```python
dimension_type = detect_dimension(blueprint_text)  # "2d" or "3d"
target_library = "matplotlib" if dimension_type == "2d" else "manim"
output_format = "png" if dimension_type == "2d" else "gif"
```

### 4.3 Adding New Problem Types

**Entirely prompt-based** — no code modules to add. The pipeline handles any geometry problem that:

1. Can be described in the blueprint format (points, lines, angles, faces)
2. Has a defined output format (2D static or 3D animated)

To add new patterns (e.g., coordinate geometry):

1. Update `Question_to_Blueprint` prompt with new output sections
2. Update `Blueprint_to_Code_Gemini` prompt with rendering instructions

---

## 5. Intermediate Representation

### 5.1 Format: Plain-text Markdown Tables (not JSON)

The blueprint in `coordinates.txt` is structured markdown, **not JSON or a dataclass**:

```markdown
### Part 3: Geometric Elements Breakdown

**A. Intrinsic Point Coordinates Table (X, Y, Z):**

| Point | X | Y | Z | Calculation Logic |
| :--- | :--- | :--- | :--- | :--- |
| **A** | 0.000 | 0.000 | 0.000 | Origin. |
| **B** | 5.000 | 0.000 | 0.000 | AB on X-axis |

**B. Lines, Edges, and Curves:**

| Element ID | Start Point | End Point | Calculated Length (Units) | Logic |
| :--- | :--- | :--- | :--- | :--- |
| **line_AB** | A | B | 5.000 | Given 3 cm. |
```

### 5.2 Why Not Structured JSON?

The LLM in Stage 2 parses this markdown directly from the prompt. Benefits:

- Human-readable for debugging
- Flexible for complex geometry descriptions
- No schema validation overhead
- LLM can understand context and relationships

---

## 6. Current Coordinate Geometry Support

**None currently implemented.**

The system is designed for **synthetic geometry** (triangles, polygons, circles, prisms, pyramids) with explicit point coordinates. There is no support for:

- Plotting equations (`y = mx + b`, `y = x²`)
- Graphing functions
- Coordinate axes with tick marks
- Number lines or grids

To add coordinate geometry support, you would need to:

1. Extend `Question_to_Blueprint` prompt to generate axis definitions, function expressions
2. Extend `Blueprint_to_Code_Gemini` prompt with matplotlib axis/function plotting instructions
3. Possibly add a third dimension type (`"coordinate"`) for routing

---

## 7. Config/Constants

### 7.1 Prompt Storage

**Separate file:** `diagram_prompts.py` (~900 lines)

- `Question_to_Blueprint` — Stage 1 prompt (lines 13-173)
- `Blueprint_to_Code` — Original Stage 2 prompt for Claude (lines 180-614, unused)
- `Blueprint_to_Code_Gemini` — Current Stage 2 prompt (lines 621-905)

### 7.2 API Configuration

- **Environment:** `.env` file with `GEMINI_API_KEY`
- **Client:** Google GenAI client (`from google import genai`)
- **Model:** `gemini-3-flash-preview`

### 7.3 Supported Problem Types

**Implicitly defined by prompts** — no config file. The prompt examples determine what the LLM can handle:

- 2D: triangles, quadrilaterals, circles, polygons
- 3D: prisms, pyramids, cubes, tetrahedra, cylinders

### 7.4 Color Palette (hardcoded in prompts)

```python
# Light theme
BACKGROUND = "#FFFFFF"
POINTS = "#1A1A1A"
ACCENT_ASKED = "#E63946"  # vivid red
LINES = ["#2A9D8F", "#264653", "#457B9D", "#6A4C93", "#E76F51", "#2D6A4F", "#B5838D"]
```

---

## 8. Output Delivery

### 8.1 Current: Saved to Disk

```
output/
├── diagram.png          # 2D output
├── diagram.gif          # 3D output
├── batch/
│   ├── 2d_01_abc123/
│   │   ├── coordinates.txt
│   │   ├── render_code.py
│   │   └── diagram.png
│   └── 3d_01_def456/
│       ├── coordinates.txt
│       ├── render_code.py
│       ├── manim_helpers.py
│       └── diagram.gif
```

### 8.2 Batch Testing UI

`batch_test.py` provides a Flask web interface:

- Runs 10 test questions (5 2D + 5 3D) in parallel
- Displays results at `http://127.0.0.1:5051`
- Shows per-question cost tracking (Gemini pricing)
- Serves output images via `/output/<path>` route

### 8.3 No API Endpoint

The system is **CLI-only**. To serve via API, you would wrap `GeometryPipeline` in a web framework (Flask/FastAPI).

---

## 9. Legacy Video Pipeline (archived)

The original 5-step video pipeline is in `legacy/`:

```
1. generate_solution_steps.py    → JSON solution breakdown
2. geo_scriptwriter_parallel.py  → Audio narration (ElevenLabs)
3. integrated_geometry_pipeline.py → Coordinate extraction
4. video_claude.py               → Manim scene code (Claude)
5. render_and_concatenate_scenes.py → Final video
```

This pipeline generated full educational videos with:

- Step-by-step voiceover narration
- Animated geometry constructions
- Khan Academy-style explanations

It was replaced by the simpler 2-stage diagram pipeline for faster iteration and lower costs.

---

## 10. Key Files Reference

| File | Purpose | Lines |
|------|---------|-------|
| `geometry_pipeline.py` | Main orchestrator, CLI entry point | 207 |
| `generate_blueprint.py` | Stage 1: Question → Blueprint | 199 |
| `generate_code.py` | Stage 2: Blueprint → Code → Render | 390 |
| `diagram_prompts.py` | All LLM prompts | 905 |
| `manim_helpers.py` | 3D angle arc utilities | 180 |
| `batch_test.py` | Parallel test runner with Flask UI | 716 |
| `render_geometry.py` | Thin wrapper for re-rendering | 28 |

---

## 11. Environment Notes

- **System Python:** 3.9 (no `X | None` syntax, use `Optional[X]`)
- **Manim Python:** 3.13 at `/Users/kairos/.local/bin/manim`
- **matplotlib:** Installed to user site-packages
- **LaTeX:** Not installed — avoid `MathTex`, use `Text`
- **API Client:** Use Google GenAI client (not raw requests due to LibreSSL issues)

---

## 12. Cost Estimates (Gemini 3 Flash)

Per question (from batch_test.py pricing):

| Stage | Input | Output |
|-------|-------|--------|
| Blueprint | $0.50/M tokens | $3.00/M tokens |
| CodeGen | $0.50/M tokens | $3.00/M tokens |

Typical per-question cost: ~$0.01-0.02

---

## 13. Sample Blueprint Output

```markdown
=== GEOMETRIC BLUEPRINT - COORDINATES ===

## Geometric Blueprint

**DIMENSION: 3D**

### Part 1: Geometric Context from Question

#### 1. QUESTION OBJECTIVE
A right triangular prism with base ABC (∠ABC = 90°) and height 10 cm.
Find the length of the space diagonal AF.

#### 2. GIVEN ELEMENTS
* **Given Lengths:** AB = 3 cm, BC = 4 cm, Height = 10 cm
* **Given Angles:** ∠ABC = 90°
* **Given Properties:** Right triangular prism

### Part 3: Geometric Elements Breakdown

**A. Intrinsic Point Coordinates Table (X, Y, Z):**

| Point | X | Y | Z | Calculation Logic |
| :--- | :--- | :--- | :--- | :--- |
| **A** | 0.000 | 0.000 | 0.000 | Origin. |
| **B** | 5.000 | 0.000 | 0.000 | AB on X-axis |
| **C** | 5.000 | 6.667 | 0.000 | BC parallel to Y-axis |
| **D** | 0.000 | 0.000 | 16.667 | Above A by height |
| **E** | 5.000 | 0.000 | 16.667 | Above B by height |
| **F** | 5.000 | 6.667 | 16.667 | Above C by height |

### Part 4: Display Rules

**E. Annotation Table:**

| Element | Category | Display Action |
| :--- | :--- | :--- |
| **line_AB** | given | Show length label "3 cm" |
| **line_BC** | given | Show length label "4 cm" |
| **line_AF** | asked | Highlight in accent color, label "?" |
| **line_AC** | derived | Draw line, NO label |
```
