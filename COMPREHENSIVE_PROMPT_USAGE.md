# Comprehensive Coordinate Geometry Prompt - Usage Guide

## Overview

The comprehensive coordinate geometry prompt (`Question_to_Blueprint_Compact_All`) is an enhanced version of the blueprint generation system that intelligently handles **all 4 geometry types**:

1. **2D** - Traditional 2D geometry (triangles, circles, polygons)
2. **3D** - Traditional 3D geometry (pyramids, cones, spheres)
3. **COORDINATE_2D** - 2D with coordinate system/graphing
4. **COORDINATE_3D** - 3D with coordinate system/graphing

## Key Features

### Intelligent Type Detection

The prompt automatically detects the geometry type based on the question:

- **Coordinate mentions**: If question says "A(3, 4)" or "point P at (2, 5)" → COORDINATE_2D/3D
- **Graphing tasks**: "Plot the line y = 2x + 3" → COORDINATE_2D
- **Traditional geometry**: "Triangle ABC with AB = 12 cm" → 2D

### Enhanced Output for Coordinate Geometry

For coordinate geometry questions (COORDINATE_2D/COORDINATE_3D), the JSON blueprint includes:

- **axes**: Coordinate axes with ranges, labels, tick marks
- **grid**: Grid line configuration (major/minor, style)
- **origin**: Origin marker styling
- **display_coordinates**: Original coordinate values from question
- **equations**: Equation labels for lines/curves

### Backward Compatible

Traditional 2D/3D geometry questions work exactly as before - no coordinate-specific fields are added.

## Usage

### Method 1: Using batch_test.py

Run batch tests with the comprehensive prompt:

```bash
# Use comprehensive prompt for geometry tests
python3 batch_test.py --blueprint-model comprehensive

# Use comprehensive prompt for coordinate geometry tests
python3 batch_test.py --test-set coordinate --blueprint-model comprehensive

# Use comprehensive prompt for HKDSE tests
python3 batch_test.py --test-set hkdse --blueprint-model comprehensive

# Use comprehensive prompt with specific dimension filter
python3 batch_test.py --blueprint-model comprehensive --dim 2d
```

### Method 2: Direct Script Usage

Use the blueprint generator directly:

```bash
# Generate blueprint for a coordinate geometry question
python3 generate_blueprint_comprehensive.py \
  --question-text "Plot points A(0,0), B(3,4), and C(6,0). Draw triangle ABC and find its area." \
  --output-dir output/test

# Generate blueprint for a traditional geometry question
python3 generate_blueprint_comprehensive.py \
  --question-text "Triangle ABC with AB = 12 cm, angle ACB = 90°, BC = 5 cm. Find AC." \
  --output-dir output/test

# With image input
python3 generate_blueprint_comprehensive.py \
  --question-text question.txt \
  --question-image question.png \
  --output-dir output/test
```

### Method 3: Import in Python Code

```python
from generate_blueprint_comprehensive import generate_blueprint
import os

result = generate_blueprint(
    api_key=os.getenv("GEMINI_API_KEY"),
    question_text="Plot the line y = 2x + 3 and find its x-intercept.",
    output_dir="output",
    image_path=None  # Optional
)

if result["success"]:
    print(f"Blueprint saved to: {result['coordinates_file']}")
    print(f"Dimension type: {result['dimension']}")  # e.g., "coordinate_2d"
else:
    print(f"Error: {result['error']}")
```

## Example Questions & Detection

### Traditional 2D → dimension: "2d"
```
"Triangle ABC with AB = 12 cm, BC = 5 cm, angle ABC = 90°. Find AC."
```

### Traditional 3D → dimension: "3d"
```
"A pyramid with square base ABCD (side 8 cm) and apex V at height 6 cm. Find the slant height."
```

### Coordinate 2D → dimension: "coordinate_2d"
```
"Plot points A(0, 0), B(3, 4), C(6, 0). Draw triangle ABC and find its area."
"Graph the line y = 2x + 3 and find where it crosses the x-axis."
"Point A is at (2, 3) and point B is at (5, 7). Find the distance AB."
```

### Coordinate 3D → dimension: "coordinate_3d"
```
"Plot the point P(1, 2, 3) and find its distance from the origin."
"Graph the plane x + y + z = 6 in 3D space."
```

## JSON Output Examples

### Traditional 2D (No coordinate fields)
```json
{
  "dimension": "2d",
  "scale": {"reference": "AB", "real": "12 cm", "units": 5.0},
  "points": {
    "A": [0.000, 0.000, 0.000],
    "B": [5.000, 0.000, 0.000]
  },
  "lines": [...],
  "given": {"line_AB": "12 cm"},
  "asked": ["line_AC"]
}
```

### Coordinate 2D (With coordinate fields)
```json
{
  "dimension": "coordinate_2d",
  "scale": {"reference": "AB", "real": "5 units", "units": 5.0},
  "points": {
    "A": [0.000, 0.000, 0.000],
    "B": [3.000, 4.000, 0.000]
  },
  "lines": [...],
  "axes": {
    "x": {"min": -1, "max": 7, "label": "x", "show_ticks": true},
    "y": {"min": -1, "max": 5, "label": "y", "show_ticks": true}
  },
  "grid": {"major": true, "minor": false, "style": "dotted"},
  "origin": {"show": true, "marker_style": "cross"},
  "display_coordinates": {
    "A": "(0, 0)",
    "B": "(3, 4)"
  },
  "equations": [],
  "given": {"point_A": "(0, 0)", "point_B": "(3, 4)"},
  "asked": ["area_triangle_ABC"]
}
```

## Implementation Details

### Files Created

1. **coordinate_geometry_prompts.py** - Prompt definitions
   - `Question_to_Blueprint_Compact_All` - Main comprehensive prompt
   - `Question_to_Blueprint_Compact_Legacy` - Original prompt (reference)

2. **generate_blueprint_comprehensive.py** - Blueprint generator
   - Uses `Question_to_Blueprint_Compact_All` prompt
   - Handles all 4 geometry types
   - Outputs JSON blueprint with conditional fields

3. **batch_test.py** (modified) - Integration
   - Added `--blueprint-model comprehensive` option
   - Imports `generate_blueprint_comprehensive` when selected
   - Maintains backward compatibility

### Detection Logic

The prompt uses these rules to classify questions:

1. **Check for coordinates**: If question mentions coordinates like "A(2, 3)" → COORDINATE
2. **Check for 3D coordinates**: If coordinates have 3 values like "P(1, 2, 3)" → COORDINATE_3D
3. **Check for graphing keywords**: "plot", "graph", "Cartesian plane" → COORDINATE_2D
4. **Check for Z coordinates**: Non-zero Z values in geometry → 3D
5. **Default to 2D**: Traditional geometry without coordinates → 2D

### Scaling for Coordinate Geometry

For coordinate geometry, the prompt:
1. **Preserves** the original coordinate values in `display_coordinates`
2. **Scales** internal coordinates for rendering (first significant distance → 5.0 units)
3. **Calculates** axes ranges to fit all points with 20% padding

Example:
- Question: "A(0, 0), B(3, 4)" with scale factor 0.5
- Internal: `"A": [0.0, 0.0, 0.0]`, `"B": [1.5, 2.0, 0.0]`
- Display: `"A": "(0, 0)"`, `"B": "(3, 4)"`

## When to Use

### Use Comprehensive Prompt When:
- Testing coordinate geometry questions
- Questions mix traditional and coordinate geometry
- Need automatic detection of geometry type
- Want enhanced coordinate system visualization

### Use Original Prompt When:
- Only working with traditional geometry (no coordinates)
- Need faster processing (slightly less complex prompt)
- Backward compatibility with existing pipeline

## Testing

Run a comprehensive test with all geometry types:

```bash
# Test with 10 geometry questions (mixed 2D/3D)
python3 batch_test.py --blueprint-model comprehensive --workers 5

# Test with coordinate geometry questions
python3 batch_test.py --test-set coordinate --blueprint-model comprehensive

# Test with HKDSE questions
python3 batch_test.py --test-set hkdse --blueprint-model comprehensive

# Test all question types
python3 batch_test.py --test-set all --blueprint-model comprehensive
```

## Performance

- **Token usage**: Similar to original prompt (~10-15k tokens)
- **API cost**: Same as original (uses Gemini 3 Flash)
- **Latency**: ~5-10s per blueprint (depends on question complexity)
- **Accuracy**: Enhanced for coordinate geometry, maintains quality for traditional geometry

## Troubleshooting

### Issue: Coordinate geometry detected as traditional 2D

**Solution**: Ensure question explicitly mentions coordinates or uses coordinate terminology:
- ❌ "Point A at position 3, 4" → May be detected as 2D
- ✅ "Point A at (3, 4)" → Correctly detected as COORDINATE_2D

### Issue: Traditional geometry detected as coordinate geometry

**Solution**: Avoid using coordinate-like notation in traditional geometry questions:
- ❌ "Triangle with vertices at (0,0), (3,4), (6,0)" → Detected as COORDINATE_2D
- ✅ "Triangle ABC with AB = 12 cm" → Correctly detected as 2D

### Issue: Missing axes or grid in coordinate geometry output

**Solution**: Check that JSON parsing succeeded. If `coordinates.txt` exists instead of `coordinates.json`, the JSON parsing failed. Check the blueprint text for errors.

## Future Enhancements

Potential improvements:
- Support for polar coordinates
- Support for parametric equations
- 3D surface plotting
- Automatic equation label positioning
- Dynamic grid spacing based on coordinate ranges
