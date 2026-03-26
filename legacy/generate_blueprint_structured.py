#!/usr/bin/env python3
"""
Stage 1: Generate a geometric blueprint using Gemini's structured JSON output.

Uses Gemini-3-Flash with response_schema to guarantee valid JSON output.
This eliminates the need for JSON parsing and retry logic.

Output: coordinates.json

Usage:
    python3 generate_blueprint_structured.py --question-text "In triangle ABC, angle ACB = 90°, AD = 12cm, BC = 12cm."
    python3 generate_blueprint_structured.py --question-text question.txt --question-image question.png
"""

import argparse
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv(".env")

# Streamlined prompt for structured output
# The JSON schema enforces structure, so we focus only on geometric reasoning
STRUCTURED_BLUEPRINT_PROMPT = """
You are a computational geometry engine. Analyze the geometry question and compute precise coordinates for all geometric elements.

## Task
Compute exact 3D coordinates for all points, using proper geometric reasoning (similar triangles, Pythagorean theorem, trigonometry, etc.).

## Coordinate System & Scaling
- Choose a convenient origin (typically point A at origin)
- Map the first significant length to 5.0 units (e.g., if AB = 12 cm, then distance(A,B) = 5.0, so scale factor = 5/12)
- For 2D figures, all Z coordinates = 0.0
- Compute all coordinates with 3 decimal places precision

## Dimension Detection
- **2d**: Planar geometry (triangles, circles, quadrilaterals) where all points lie in XY plane (Z=0)
- **3d**: Solid geometry (pyramids, prisms, cones, polyhedra) with true 3D coordinates
- **coordinate_2d**: Coordinate geometry problems with explicit axes, grids, or algebraic curves

## Element Identification
- **Points**: Compute [x, y, z] for every labeled point
- **Lines**: List every edge/segment (use "dashed" style for auxiliary/hidden lines)
- **Circles**: Compute center and radius in coordinate units
- **Arcs**: For partial circles, specify center and endpoints
- **Faces**: For filled polygons, list vertices in winding order
- **Angles**: Only mark angles that are given or asked (compute value in degrees)
- **Shapes**: For 3D solids (cone, cylinder, sphere, hemisphere, etc.), declare them explicitly with their defining points and radius
- **Curves**: For coordinate geometry — ellipses, parabolas, hyperbolas with their equation coefficients
- **Annotations**: Marks for equal segments (ticks), parallel lines (arrows), right angles (square symbol), midpoints, tangent points

## Given & Asked
- **given**: Elements explicitly stated in the problem (e.g., "AB = 12 cm", "∠ABC = 90°")
- **asked**: Elements the question asks to find (will be marked with "?")

Focus on geometric accuracy. Use exact computation, not approximation.
"""

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Define the JSON schema for structured output
# NOTE: Gemini doesn't support additionalProperties, so we use arrays instead of dictionaries
BLUEPRINT_SCHEMA = {
    "type": "object",
    "properties": {
        "dimension": {
            "type": "string",
            "enum": ["2d", "3d", "coordinate_2d"],
            "description": "Geometry dimension type"
        },
        "scale": {
            "type": "object",
            "properties": {
                "reference": {"type": "string", "description": "Reference segment name (e.g., 'AB')"},
                "real": {"type": "string", "description": "Real-world measurement (e.g., '12 cm')"},
                "units": {"type": "number", "description": "Scale factor in coordinate units"}
            },
            "required": ["reference", "real", "units"]
        },
        "points": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Point name (e.g., 'A', 'B', 'C')"},
                    "coords": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 3,
                        "maxItems": 3,
                        "description": "3D coordinates [x, y, z]"
                    }
                },
                "required": ["name", "coords"]
            },
            "description": "Array of points with names and coordinates"
        },
        "lines": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "from": {"type": "string"},
                    "to": {"type": "string"},
                    "style": {"type": "string", "description": "Line style: 'solid' or 'dashed' (optional)"}
                },
                "required": ["id", "from", "to"]
            }
        },
        "circles": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "center": {"type": "string"},
                    "radius": {"type": "number"},
                    "style": {"type": "string", "description": "Circle style: 'solid' or 'dashed' (for hidden circles in 3D)"}
                },
                "required": ["id", "center", "radius"]
            }
        },
        "arcs": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "center": {"type": "string"},
                    "from": {"type": "string"},
                    "to": {"type": "string"},
                    "direction": {"type": "string", "description": "Arc direction: 'ccw' (counterclockwise, default) or 'cw' (clockwise)"},
                    "arc_type": {"type": "string", "description": "Arc extent: 'minor' (less than 180) or 'major' (more than 180)"}
                },
                "required": ["id", "center", "from", "to"]
            }
        },
        "faces": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "points": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "required": ["id", "points"]
            }
        },
        "angles": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "vertex": {"type": "string"},
                    "p1": {"type": "string"},
                    "p2": {"type": "string"},
                    "value": {"type": "number", "description": "Angle value in degrees"}
                },
                "required": ["id", "vertex", "p1", "p2", "value"]
            }
        },
        "curves": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "Curve identifier (e.g., 'ellipse_1', 'parabola_1')"},
                    "type": {
                        "type": "string",
                        "enum": ["ellipse", "parabola", "hyperbola", "line_function"],
                        "description": "Type of curve"
                    },
                    "equation": {"type": "string", "description": "Equation string (e.g., 'x^2/9 + y^2/4 = 1', 'y = x^2')"},
                    "center": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Center or vertex of the curve [x, y, z]"
                    },
                    "a": {"type": "number", "description": "Semi-major axis or focal parameter (0 if not applicable)"},
                    "b": {"type": "number", "description": "Semi-minor axis (0 if not applicable)"},
                    "rotation": {"type": "number", "description": "Rotation angle in degrees from x-axis (0 if axis-aligned)"}
                },
                "required": ["id", "type", "equation"]
            },
            "description": "Algebraic curves for coordinate geometry (ellipses, parabolas, hyperbolas)"
        },
        "annotations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["right_angle", "equal_length", "parallel", "midpoint", "tangent"],
                        "description": "Annotation type"
                    },
                    "elements": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Element IDs or point names this annotation applies to"
                    },
                    "group": {"type": "integer", "description": "Group number for equal-length ticks (1 = single tick, 2 = double tick, etc.)"}
                },
                "required": ["type", "elements"]
            },
            "description": "Visual annotations: right angle marks, equal length ticks, parallel arrows, midpoint dots, tangent indicators"
        },
        "shapes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "Shape identifier (e.g., 'cone_1', 'cylinder_1')"},
                    "type": {
                        "type": "string",
                        "enum": ["cone", "cylinder", "sphere", "hemisphere", "pyramid", "prism", "torus"],
                        "description": "Type of 3D shape"
                    },
                    "points": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Defining point names (e.g., apex + base center for cone)"
                    },
                    "radius": {"type": "number", "description": "Radius in coordinate units (0 if not applicable)"},
                    "height": {"type": "number", "description": "Height in coordinate units (0 if not applicable)"}
                },
                "required": ["id", "type", "points", "radius", "height"]
            },
            "description": "3D solid shapes (cone, cylinder, sphere, etc.) with defining geometry"
        },
        "given": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "Element ID"},
                    "label": {"type": "string", "description": "Display label"}
                },
                "required": ["id", "label"]
            },
            "description": "Array of given elements with IDs and display labels"
        },
        "asked": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of element IDs that are being asked for"
        }
    },
    "required": ["dimension", "scale", "points", "lines", "given", "asked"]
}


def extract_dimension_from_json(blueprint_json):
    # type: (dict) -> str
    """Extract dimension from a structured JSON blueprint.

    Returns '2d', '3d', or 'coordinate_2d'.
    """
    dim = blueprint_json.get("dimension", "2d").lower()
    if dim in ("2d", "3d", "coordinate_2d"):
        logger.info(f"Extracted dimension from structured JSON: {dim}")
        return dim
    logger.info(f"Unknown dimension '{dim}'; defaulting to 2d")
    return "2d"


def convert_structured_to_compact(structured_json):
    # type: (dict) -> dict
    """Convert structured array-based JSON to compact dict-based JSON.

    This converts:
    - points: array of {name, coords} → dict of {name: coords}
    - given: array of {id, label} → dict of {id: label}

    This ensures compatibility with the existing code generation stage.
    """
    compact = dict(structured_json)

    # Convert points array to dict
    if "points" in compact and isinstance(compact["points"], list):
        points_dict = {}
        for point in compact["points"]:
            points_dict[point["name"]] = point["coords"]
        compact["points"] = points_dict

    # Convert given array to dict
    if "given" in compact and isinstance(compact["given"], list):
        given_dict = {}
        for item in compact["given"]:
            given_dict[item["id"]] = item["label"]
        compact["given"] = given_dict

    return compact


def generate_blueprint(
    api_key,          # type: str
    question_text,    # type: str
    output_dir,       # type: str
    image_path=None,  # type: Optional[str]
):
    # type: (...) -> dict
    """Call Gemini to generate the geometric blueprint using structured output.

    Returns a dict with keys: success, blueprint, coordinates_file,
    api_call_duration, prompt_tokens, completion_tokens, total_tokens.
    """
    client = genai.Client(api_key=api_key)

    # Use the structured prompt (array-based format compatible with Gemini)
    prompt_template = STRUCTURED_BLUEPRINT_PROMPT
    logger.info("Using STRUCTURED JSON output with response_schema")

    # Build content parts
    text_prompt = (
        f"{prompt_template}\n\n"
        f"--- QUESTION ---\n{question_text}\n--- END QUESTION ---"
    )
    content_parts = [text_prompt]

    # Optionally attach the question image
    if image_path:
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        # Detect mime type from extension
        ext = Path(image_path).suffix.lower()
        mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp"}
        mime_type = mime_map.get(ext, "image/png")
        content_parts.append(types.Part.from_bytes(data=image_bytes, mime_type=mime_type))

    try:
        start = time.time()
        logger.info("Calling Gemini-3-Flash with structured output...")
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=content_parts,
            config={
                "max_output_tokens": 20000,
                "temperature": 0.1,
                "thinking_config": types.ThinkingConfig(thinking_budget=8000),
                "response_mime_type": "application/json",
                "response_schema": BLUEPRINT_SCHEMA,
            },
        )
        elapsed = time.time() - start

        # Parse the response (guaranteed to be valid JSON matching the schema)
        structured_json = json.loads(response.text)
        usage = response.usage_metadata

        # Convert structured format (arrays) to compact format (dicts)
        # This ensures compatibility with existing code generation stage
        blueprint_json = convert_structured_to_compact(structured_json)

        dimension = extract_dimension_from_json(blueprint_json)

        # Save as JSON file (in compact format for compatibility)
        os.makedirs(output_dir, exist_ok=True)
        coords_file = os.path.join(output_dir, "coordinates.json")
        with open(coords_file, "w", encoding="utf-8") as f:
            json.dump(blueprint_json, f, indent=2)
        logger.info(f"Structured JSON blueprint saved to: {coords_file}")

        # Also create a pretty text representation for the blueprint field
        blueprint_text = json.dumps(blueprint_json, indent=2)

        return {
            "success": True,
            "blueprint": blueprint_text,
            "dimension": dimension,
            "coordinates_file": coords_file,
            "api_call_duration": elapsed,
            "prompt_tokens": usage.prompt_token_count if usage else 0,
            "completion_tokens": usage.candidates_token_count if usage else 0,
            "total_tokens": usage.total_token_count if usage else 0,
        }

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse structured JSON response: {e}")
        return {"success": False, "error": f"JSON parsing failed: {e}"}
    except Exception as e:
        logger.error(f"Blueprint generation failed: {e}")
        return {"success": False, "error": str(e)}


# ======================================================================
# CLI
# ======================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Generate geometric blueprint using Gemini structured output"
    )
    parser.add_argument(
        "--question-text", required=True,
        help="Question text (literal string or path to a .txt file)",
    )
    parser.add_argument(
        "--question-image", default=None,
        help="Optional path to a question image file",
    )
    parser.add_argument(
        "--output-dir", default=None,
        help="Output directory for coordinates.json (default: script directory)",
    )
    args = parser.parse_args()

    # Resolve question text: if it's a file path, read the file
    question_text = args.question_text
    if os.path.isfile(question_text):
        with open(question_text, "r", encoding="utf-8") as f:
            question_text = f.read().strip()
        logger.info(f"Read question text from file: {args.question_text}")
    else:
        logger.info("Using literal question text from CLI argument")

    pipeline_dir = Path(__file__).parent
    output_dir = args.output_dir or str(pipeline_dir)

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY environment variable not set")
        sys.exit(1)

    if args.question_image and not os.path.exists(args.question_image):
        logger.error(f"Image not found: {args.question_image}")
        sys.exit(1)

    result = generate_blueprint(
        api_key=api_key,
        question_text=question_text,
        output_dir=output_dir,
        image_path=args.question_image,
    )

    if result["success"]:
        logger.info(
            f"Tokens: {result['total_tokens']} "
            f"(in: {result['prompt_tokens']}, out: {result['completion_tokens']}) "
            f"in {result['api_call_duration']:.1f}s"
        )
    else:
        logger.error(f"Blueprint generation failed: {result['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
