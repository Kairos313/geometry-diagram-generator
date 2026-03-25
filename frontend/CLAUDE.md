# Frontend JS Rendering Pipeline

Generates interactive geometry diagrams as self-contained HTML files using LLM-generated JavaScript (D3.js for 2D, Three.js for 3D).

## Pipeline

```
Question (text)
     │
     ▼
Stage 1: Classify (Gemini 3 Flash, ~0.5s, ~$0.0001)
     │   → "2d" or "3d"
     ▼
Stage 2: Hybrid Blueprint (Gemini 3 Flash + thinking, ~15s, ~$0.003)
     │   → hybrid blueprint (JSON format + quality rules), converted to text notes internally
     ▼
Stage 3: Generate JS (DeepSeek V3.2 Azure, ~60-150s, ~$0.003)
     │   → self-contained HTML with D3.js or Three.js
     ▼
Output: diagram.html (open in browser, no server needed)
```

**Cost per diagram: ~$0.007 avg | Total pipeline: ~85s avg | 30/30 HKDSE pass rate**

## Key Files

| File | Purpose |
|------|---------|
| `generate_js_pipeline.py` | Pipeline orchestrator: `compute_math()` → `generate_js()` → `generate_diagram()` |
| `js_pipeline_prompts.py` | Prompts for Stage 2 (Gemini math) and Stage 3 (DeepSeek JS). Contains `drawAngleArc` and `drawAngleArc3D` helper functions embedded in templates |
| `generate_code_js.py` | DeepSeek API caller + HTML extraction + JS postprocessing |
| `js_code_prompts.py` | Original simpler JS prompts (used by generate_code_js.py standalone mode) |
| `batch_test_js_pipeline.py` | CLI batch runner (parallel execution + gallery generation) |
| `batch_test_js_ui.py` | Flask web UI with real-time progress (port 5052) |
| `hkdse_new_questions.py` | 10 additional HKDSE-style test questions |

## Running

```bash
# Single question
python3 frontend/generate_js_pipeline.py -q "Triangle ABC with AB=12cm..." --dim 2d --output output/diagram.html

# Batch test (CLI)
python3 frontend/batch_test_js_pipeline.py --test-set hkdse_new    # 10 new questions
python3 frontend/batch_test_js_pipeline.py --test-set hkdse        # 20 HKDSE
python3 frontend/batch_test_js_pipeline.py --test-set coord        # 30 coordinate
python3 frontend/batch_test_js_pipeline.py                         # All 60

# Web UI (real-time progress at http://127.0.0.1:5052)
python3 frontend/batch_test_js_ui.py --test-set hkdse_new
```

## API Configuration

Uses `.env` at repo root (NOT in frontend/):
```
GEMINI_API_KEY=...        # Stage 1 + 2 (Gemini 3 Flash)
DEEPSEEK_API_KEY=...      # Stage 3 (DeepSeek V3.2 via Azure)
```

**DeepSeek endpoint:** `https://raksh-m4jj47jc-japaneast.services.ai.azure.com/openai/v1/`
**DeepSeek model:** `DeepSeek-V3.2`
**Gemini model:** `gemini-3-flash-preview`

## Prompt Architecture

`js_pipeline_prompts_hybrid.py` is the source of the Stage 2 (hybrid blueprint) prompt. The pipeline uses the hybrid prompt by default, which combines the old JSON blueprint format with new quality rules. The hybrid blueprint output is converted to text notes internally before being passed to Stage 3 (DeepSeek JS code generation).

`js_pipeline_prompts.py` contains the Stage 3 prompts and original Stage 2 prompt:

1. **`MATH_PROMPT` (hybrid)** — Gemini computes coordinates using hybrid prompt (JSON format + quality rules). Output is converted to structured text notes:
   ```
   DIMENSION: 2D
   TITLE: ...
   COMPUTATION: (step-by-step work, stripped before passing to DeepSeek)
   COORDINATES: A = (x, y), B = (x, y), ...
   ELEMENTS: Segment AB (solid), Circle center=O radius=5, ...
   ANGLES: Angle at B between BA and BC = 90 degrees (right angle)
   LABELS: Segment AB: "10 cm", ...
   GIVEN: ...
   ASKED: ...
   INTERACTIVE: none
   ```

2. **`JS_CODE_PROMPT_2D`** — DeepSeek generates D3.js SVG. Includes:
   - `drawAngleArc()` helper (handles interior/exterior disambiguation via `expectedDeg`)
   - Pixel-space viewBox rule (NEVER math-space viewBox)
   - Static diagrams only (no sliders)

3. **`JS_CODE_PROMPT_3D`** — DeepSeek generates Three.js HTML. Includes:
   - `drawAngleArc3D()` helper (quaternion-based arc in 3D)
   - `addEdge`, `addSphere`, `makeLabel`, `addFace`, `addCircle3D` helpers in template
   - Hand-rolled orbit controls (drag to rotate, scroll to zoom)
   - Auto-rotate toggle + reset view button
   - No sliders

## Critical Rules (embedded in prompts)

- **2D viewBox**: ALWAYS pixel-space (`viewBox="0 0 680 500"`), NEVER math-space. Use `d3.scaleLinear()` to map math→pixels.
- **Angle arcs**: ALWAYS use `drawAngleArc()` / `drawAngleArc3D()` helpers. NEVER write custom arc code.
- **No sliders**: 2D is static. 3D has orbit+zoom only.
- **No unnecessary elements**: Only include angles/labels explicitly mentioned in the question.
- **No answers**: Diagrams show problem setup only. Asked elements get "?" labels.
- **JS safety**: Never use `var` as function name. Never use `var(--css)` in JS. Use hex colors.
- **Geometric constraints**: Points on a circle must satisfy distance = radius. Verify in COMPUTATION section.
- **Uniform scaling for 2D circles**: Use the same scale factor for both X and Y axes to prevent circles from appearing as ellipses.

## Output Structure

```
frontend/output/
├── batch_js/           # 50 original questions
│   ├── coord_01/diagram.html
│   ├── hkdse_2d_01/diagram.html
│   └── ...
└── batch_js_new/       # 10 new HKDSE questions
    ├── hkdse_new_01/diagram.html
    └── ...
```

Each `diagram.html` is self-contained (loads D3/Three.js from CDN). No build step needed.

## Comparable Outputs

`comparable outputs/` contains 5 hand-crafted reference HTML files showing the target quality:
- `rotating_pyramid.html` — Three.js with orbit, legend, labels
- `tetrahedron_dihedral_angle.html` — dihedral angle arc
- `pyramid_cross_section.html` — interactive cutting plane slider
- `rotated_ellipse.html` — SVG with rotation slider
- `projection_reflection_plane.html` — 3D point projection/reflection
