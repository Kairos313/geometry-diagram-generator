# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Context

AI pipeline: Geometry questions (text/image) → Interactive HTML diagrams (D3.js/Three.js) or static diagrams (PNG/SVG/GIF)

**Preferred: JS Frontend Pipeline** (Mar 2026, production)
- Main entry: `frontend/generate_js_pipeline.py` (single) or `frontend/batch_test_js_ui.py` (batch)
- Generates interactive HTML diagrams — D3.js for 2D, Three.js for 3D
- 100% pass rate on 30 HKDSE questions, ~$0.007/diagram

**Legacy: 4-Stage Python Pipeline** (Feb 2025, still works)
- Main entry: `batch_test_focused.py`
- Old 2-stage pipeline moved to `legacy/` (uses comprehensive prompts, more expensive)

**4-Stage Pipeline (Classify → Blueprint → CodeGen → Execute):**

1. **Classification** → Gemini 3 Flash (~150 tokens, ~$0.0001)
   - Classifies into: `2d`, `3d`, `coordinate_2d`, `coordinate_3d`

2. **Blueprint** → Gemini 3 Flash (~8000 thinking tokens, ~$0.003-0.005)
   - Extracts geometry, calculates coordinates, outputs markdown tables

3. **Code Generation** → DeepSeek V3.2 (~4000 tokens, ~$0.005-0.012)
   - Generates matplotlib (2D) or manim (3D) render script

4. **Execution** → Local (no cost)
   - Runs generated code → produces PNG/GIF diagram

## Critical Environment Constraints

**Must know before coding:**
- **Python 3.9** - NO `X | None` syntax, use `Optional[X]` from typing
- **NO LaTeX** - Use `Text("label")` NOT `MathTex("label")` in Manim
- **Manim location** - `/Users/kairos/.local/bin/manim` (Python 3.13, separate from system Python)
- **Float arrays required** - `np.array([1.0, 0.0, 0.0])` NOT `np.array([1, 0, 0])` to avoid dtype errors

## Running the Pipeline

### Single Question (via batch test with single question)
```bash
# Use batch_test_focused.py - the 4-stage pipeline is the default
# For a single question, create a test file or use batch test interactively
python3 batch_test_focused.py --test-set hkdse --dim 2d  # Run HKDSE 2D questions

# Alternative: Call stages manually
python3 classify_geometry_type.py --question "Triangle ABC with AB = 12 cm..."
python3 generate_blueprint_focused.py --question-text "..." --dimension-type 2d
```

### Batch Testing (Web UI at http://127.0.0.1:5051)
```bash
# Use batch_test_focused.py - the new 4-stage pipeline
python3 batch_test_focused.py                          # 40 questions (all 4 types)
python3 batch_test_focused.py --test-set hkdse         # 20 HKDSE questions (2D + 3D)
python3 batch_test_focused.py --test-set coordinate    # 20 coordinate questions
python3 batch_test_focused.py --dim 3d                 # Filter to 3D only
python3 batch_test_focused.py --dim coordinate_2d      # Filter to coordinate 2D only
python3 batch_test_focused.py --workers 3              # Limit concurrency

# Old 2-stage pipeline (legacy, uses old prompts)
python3 batch_test.py --blueprint-model focused
```

## Architecture

### JS Frontend Pipeline (Preferred)

The `frontend/` directory contains the preferred rendering pipeline that generates interactive HTML diagrams using LLM-generated JavaScript (D3.js for 2D, Three.js for 3D).

**Pipeline: Classify → Hybrid Blueprint (Gemini) → JS Code (DeepSeek) → HTML**

See `frontend/CLAUDE.md` for full documentation.

Key advantages over the old Python pipeline:
- Interactive output (orbit/zoom for 3D, static SVG for 2D)
- No manim/matplotlib dependency — runs in any browser
- Faster rendering (~85s avg vs ~30-60s for Python, but no execution step needed)
- Same cost (~$0.007/diagram)
- 100% pass rate on 30 HKDSE questions

Running:
```bash
# Single question
python3 frontend/generate_js_pipeline.py -q "Triangle ABC..." --dim 2d

# Batch test (CLI)
python3 frontend/batch_test_js_pipeline.py --test-set hkdse_new

# Web UI with real-time progress
python3 frontend/batch_test_js_ui.py --port 5052
```

### 4-Stage Python Flow (Legacy — Classify → Blueprint → CodeGen → Execute)

```
Question Text/Image
    ↓
Stage 1: classify_geometry_type.py
    │ LLM: Gemini 3 Flash (150-token prompt, ~0.5-1.5s)
    │ Output: dimension_type ∈ {2d, 3d, coordinate_2d, coordinate_3d}
    ↓
Stage 2: generate_blueprint_focused.py
    │ LLM: Gemini 3 Flash (thinking_budget=8000, ~8-12s)
    │ Routes to focused prompt based on dimension_type
    │ Output: coordinates.json (compact JSON blueprint)
    ↓
Stage 3: generate_code_deepseek.py
    │ LLM: DeepSeek V3.2 Azure (via OpenRouter, ~6-10s)
    │ Output: render_code.py (self-contained matplotlib or manim script)
    ↓
Stage 4: Execute render_code.py
    │ 2D: python3 render_code.py (~2-5s)
    │ 3D: /Users/kairos/.local/bin/manim render ... (~30-60s)
    │ Output: diagram.png (2D) or diagram.gif (3D)
```

**Stage 1 (Classification):** 4-way classifier using minimal prompt
- Detects traditional geometry (2d/3d) vs coordinate geometry (coordinate_2d/coordinate_3d)
- 96% accuracy, negligible cost

**Stage 2 (Blueprint):** Coordinate calculation and geometry extraction
- Uses focused prompts (70% smaller than comprehensive)
- Outputs compact JSON format

**Stage 3 (Code Gen):** DeepSeek generates rendering code
- Maps coordinate_3d → 3d for code generation (both use manim)
- Retry logic on failure (max 2 attempts)

**Stage 4 (Execution):** Run generated code to produce final diagram
- 2D timeout: 120s, 3D timeout: 300s

**Dimension Types:**
- `2d` - Traditional 2D geometry (triangles, circles, polygons with lengths/angles)
- `3d` - Traditional 3D geometry (pyramids, prisms, spheres with lengths/angles)
- `coordinate_2d` - 2D with coordinate system (equations like x²+y²=25, graphing)
- `coordinate_3d` - 3D with coordinate system (points like (1,2,3), plane equations)

**Rendering routing:**
- 2D types → matplotlib (PNG/SVG, 1920×1080)
- 3D types → manim (GIF/MP4, 640×360 @ 15fps, 360° camera rotation)

**Code generation strategy:** Each problem = fresh self-contained script. No templates, no shared renderer, no file I/O. LLM generates complete working code from scratch every time.

### Key Files

| File | Purpose |
|------|---------|
| `batch_test_focused.py` | **Main entry point** - 4-stage pipeline with Flask UI |
| `classify_geometry_type.py` | Stage 1: Dimension classifier (Gemini 3 Flash) |
| `generate_blueprint_focused.py` | Stage 2: Focused blueprint generation (Gemini 3 Flash) |
| `generate_code_deepseek.py` | Stage 3: Code generation (DeepSeek V3.2 Azure) |
| `coordinate_geometry_prompts.py` | Focused prompts (4 specialized prompts for each type) |
| `manim_helpers.py` | 3D angle arc utilities (imported by generated code) |
| `matplotlib_helpers.py` | 2D matplotlib utilities |
| `legacy/geometry_pipeline.py` | Old 2-stage orchestrator (deprecated) |
| `legacy/batch_test.py` | Old batch test with comprehensive prompts (deprecated) |

**Test sets:** `geometry_test_questions.py` (10), `hkdse_test_questions.py` (35), `coordinate_test_questions.py` (40)

## API Configuration

**.env file at repo root:**
```
GEMINI_API_KEY=...        # For blueprint generation
OPENROUTER_API_KEY=...    # For DeepSeek code generation
```

**Gemini client (blueprint):**
```python
from google import genai
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
response = client.models.generate_content(
    model="gemini-3-flash-preview",
    contents=prompt,
    config={"max_output_tokens": 20000, "temperature": 0.1, "thinking_budget": 8000}
)
```

**DeepSeek client (code gen):**
```python
from openai import OpenAI
client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))
response = client.chat.completions.create(
    model="deepseek/deepseek-chat",  # DeepSeek V3.2 Azure (faster, cheaper)
    messages=[{"role": "user", "content": prompt}],
    max_tokens=4096,
    temperature=0.0
)
```

## Manim Code Generation Gotchas

**Critical for Stage 2 DeepSeek prompts:**

1. **Float arrays required** - `np.array([1.0, 0.0, 0.0])` NOT `np.array([1, 0, 0])`
2. **NO `opacity` param** - Use `fill_opacity` and `stroke_opacity` instead
3. **NO LaTeX** - `Text("3 cm")` NOT `MathTex("3\\text{ cm}")`
4. **Bold text** - `Text("?", weight=BOLD)` NOT `.set_weight("BOLD")`
5. **Line3D params** - Only `Line3D(start, end, color=, thickness=)` — do NOT pass `radius=`
6. **Cone positioning** - Base at center (not apex). Use `direction = (apex - base) / norm`, then `.shift(base)`
7. **Non-existent classes** - `Polyline`, `DashedLine3D`, `Arc3D`, `Prism` do NOT exist
8. **3D angle arcs** - Import and use `create_3d_angle_arc_with_connections(center, point1, point2)` from `manim_helpers.py`

## Blueprint Format (Stage 2 Output)

Compact JSON (not markdown). Schema varies by dimension type:

**2D / 3D (traditional geometry):**
```json
{
  "dimension": "2d",
  "axes": false,
  "scale": {"reference": "AB", "real": "10 cm", "units": 5.0},
  "points": {"A": [0.0, 0.0, 0.0], "B": [5.0, 0.0, 0.0], "C": [2.5, 4.33, 0.0]},
  "lines": [{"id": "line_AB", "from": "A", "to": "B"}, {"id": "line_AC", "from": "A", "to": "C", "style": "dashed"}],
  "circles": [{"id": "circle_O", "center": "O", "radius": 3.0}],
  "faces": [{"id": "face_ABC", "points": ["A", "B", "C"]}],
  "angles": [{"id": "angle_ABC", "vertex": "B", "p1": "A", "p2": "C", "value": 90.0}],
  "given": {"line_AB": "10 cm", "angle_ABC": "90°"},
  "asked": ["line_AC"]
}
```

**coordinate_2d** adds: `"axes": true`, `"grid": true`, `"coordinate_range": {"x_min": -1.0, "x_max": 8.0, "y_min": -1.0, "y_max": 11.0}`, `"curves": [{"id": "parabola_1", "equation": "y = x^2 - 4*x + 3", "points": [[0, 3], [2, -1], [4, 3]]}]`

**coordinate_3d** adds: `"planes": [{"id": "plane_ABC", "equation": "2x+y-z=4", "normal": [2.0, 1.0, -1.0]}]`, `"spheres": [{"id": "sphere_S1", "center": "C", "radius": 5.0}]`, `"vectors": [{"id": "vector_AB", "from": "A", "to": "B"}]`

Prompts are in `individual_prompts.py` — `get_prompt_for_dimension(dim)` and `get_code_prompt_for_dimension(dim)` return the right prompt for each stage.

## Cost Optimization

**Current stack (as of Feb 2025):**
- Gemini 3 Flash: $0.50/M input, $3.00/M output
- DeepSeek V3.2 Azure: $0.28/M input, $0.42/M output (via OpenRouter)

**Per-diagram cost breakdown (4-stage pipeline):**
1. Classification: ~$0.0001 (150 tokens, Gemini)
2. Blueprint: ~$0.003-0.005 (focused prompts, Gemini)
3. Code generation: ~$0.002-0.006 (DeepSeek V3.2)
4. Execution: $0 (local)

**Total: ~$0.005-0.011 per diagram** (significantly cheaper than old Gemini-only pipeline)

**Note:** The 4-stage focused pipeline is now the default. It's 38% cheaper than comprehensive prompts while maintaining quality.

## Common Workflows

**Debug a failed render:**
1. Check `output/render_code.py` for syntax errors
2. Run manually: `python3 output/render_code.py` (2D) or `/Users/kairos/.local/bin/manim render output/render_code.py GeometryScene -ql --format gif` (3D)
3. Check logs in `pipeline.log`

**Re-render from existing blueprint:**
```bash
# Generate code from existing blueprint
python3 generate_code_deepseek.py --blueprint coordinates.json --output-path output/diagram.png --dimension-type 2d

# Or re-execute existing render code
python3 output/render_code.py  # For 2D
/Users/kairos/.local/bin/manim render output/render_code.py GeometryScene -ql --format gif  # For 3D
```

**Test individual stages:**
```bash
# Stage 1: Classification
python3 classify_geometry_type.py --question "Triangle ABC with AB = 12 cm..."

# Stage 2: Blueprint (requires dimension type from Stage 1)
python3 generate_blueprint_focused.py --question-text "..." --dimension-type 2d --output-dir output

# Stage 3: Code generation (requires blueprint from Stage 2)
python3 generate_code_deepseek.py --blueprint coordinates.json --output-path output/diagram.png
```

## Troubleshooting

**Manim "command not found"** → Use full path `/Users/kairos/.local/bin/manim`

**"Response ended prematurely"p** → Use Google GenAI client for Gemini (NOT raw requests, LibreSSL issue)

**Generated code fails** → Check float arrays, opacity params, non-existent classes (see Manim gotchas)

**Batch test hangs** → Verify Flask port 5051 is free, check `pipeline.log`

## File Outputs

- **Main:** `output/diagram.{png|gif}`
- **Batch:** `output/batch/{test_id}/diagram.{png|gif}`
- **Temporary:** `coordinates.txt`, `render_code.py`, `coordinates.json` at root (overwritten each run)
