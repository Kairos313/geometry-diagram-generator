# Geometry Diagram Generator

AI pipeline that converts geometry questions into interactive HTML diagrams using D3.js and Three.js.

## How It Works

3-stage LLM pipeline: **Classify** -> **Blueprint** -> **JS Code** -> **HTML**

1. **Classify** (Gemini 2.5 Flash) -- determines dimension type: 2D, 3D, coordinate 2D, or coordinate 3D
2. **Blueprint** (Gemini 2.5 Flash) -- extracts geometry, calculates coordinates, outputs structured JSON
3. **JS Code** (DeepSeek V3.2) -- generates a self-contained HTML file with embedded JavaScript

Output formats:
- 2D diagrams: static SVG via D3.js v7
- 3D diagrams: interactive WebGL via Three.js r128 (drag to orbit, scroll to zoom)

## Quick Start

```bash
# Install dependencies
pip install google-genai openai python-dotenv flask

# Add API keys to .env at project root:
#   GEMINI_API_KEY=...
#   DEEPSEEK_API_KEY=...

# Single question
python3 frontend/generate_js_pipeline.py -q "Triangle ABC with AB=12cm, BC=8cm, angle ABC=60 degrees. Find AC." --dim 2d

# Batch test (all 60 questions, parallel)
python3 frontend/batch_test_js_pipeline.py --workers 60

# Web UI with real-time progress
python3 frontend/batch_test_js_ui.py --port 5052
```

## Examples

Six example diagrams are included in `frontend/examples/`:

| File | Type | Description |
|------|------|-------------|
| `2d_cyclic_quadrilateral.html` | 2D | Cyclic quadrilateral |
| `2d_exterior_angle.html` | 2D | Exterior angle |
| `2d_line_circle_intersection.html` | 2D | Line-circle intersection |
| `2d_parallelogram_diagonal.html` | 2D | Parallelogram diagonal |
| `3d_cuboid_space_diagonal.html` | 3D | Cuboid space diagonal |
| `3d_pyramid_slant_height.html` | 3D | Square pyramid slant height |

Open any `.html` file in a browser -- no server needed. 3D diagrams support drag-to-orbit and scroll-to-zoom.

## Performance

- **60/60** pass rate on HKDSE + coordinate geometry questions
- **$0.007** average cost per diagram
- **~85s** average generation time per diagram
- **~2 min** wall time for 60 questions running in parallel

## Project Structure

```
frontend/                        # JS rendering pipeline (preferred)
  generate_js_pipeline.py        # Main orchestrator
  batch_test_js_pipeline.py      # CLI batch runner
  batch_test_js_ui.py            # Flask web UI
  examples/                      # 6 example output diagrams
legacy/                          # Old Python pipeline (matplotlib/manim)
classify_geometry_type.py        # Shared dimension classifier
hkdse_test_questions.py          # HKDSE test questions
coordinate_test_questions.py     # Coordinate geometry test questions
```

## API Costs

| Provider | Role | Cost per diagram |
|----------|------|-----------------|
| Gemini 2.5 Flash | Classification + blueprint | ~$0.003 |
| DeepSeek V3.2 | JS code generation | ~$0.004 |
| **Total** | | **~$0.007** |

## Tech Stack

Python 3.9, Gemini 2.5 Flash, DeepSeek V3.2, D3.js v7, Three.js r128
