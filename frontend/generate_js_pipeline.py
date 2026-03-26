#!/usr/bin/env python3
"""
3-Stage JS Rendering Pipeline:
  Stage 1: Classify (Gemini Flash) -> "2d" or "3d"
  Stage 2: Compute Math (Gemini Flash + thinking) -> computation notes
  Stage 3: Generate JS (DeepSeek V3.2) -> self-contained HTML

Usage:
    python3 generate_js_pipeline.py --question "Triangle ABC with AB=12cm..." --dim auto
    python3 generate_js_pipeline.py --question "A pyramid VABCD..." --dim 3d --output output/diagram.html
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

# Add parent dir (repo root) to path for shared modules (classify_geometry_type, etc.)
_FRONTEND_DIR = Path(__file__).parent
_ROOT_DIR = _FRONTEND_DIR.parent
sys.path.insert(0, str(_ROOT_DIR))
sys.path.insert(0, str(_FRONTEND_DIR))

load_dotenv(_ROOT_DIR / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Azure endpoint for DeepSeek-V3.2
DEEPSEEK_ENDPOINT = "https://raksh-m4jj47jc-japaneast.services.ai.azure.com/openai/v1/"
DEEPSEEK_MODEL = "DeepSeek-V3.2"


def blueprint_json_to_notes(blueprint_str, question_text):
    # type: (str, str) -> str
    """Convert a JSON blueprint to the text computation notes format.

    This converts the structured JSON output from the hybrid blueprint prompt
    into the text notes format expected by the DeepSeek JS code generation stage.
    """
    try:
        bp = json.loads(blueprint_str)
    except json.JSONDecodeError:
        return "DIMENSION: 2D\nTITLE: Unknown\n\nRAW BLUEPRINT:\n" + blueprint_str

    dim = bp.get("dimension", "2d").upper()
    lines = []
    lines.append("DIMENSION: {}".format(dim))
    lines.append("TITLE: Geometry Diagram")
    lines.append("")

    # COORDINATES
    lines.append("COORDINATES:")
    points = bp.get("points", {})
    for name, coords in points.items():
        if len(coords) == 3 and abs(coords[2]) < 0.001:
            lines.append("{} = ({}, {})".format(name, coords[0], coords[1]))
        else:
            lines.append("{} = ({}, {}, {})".format(name, coords[0], coords[1], coords[2]))
    lines.append("")

    # ELEMENTS
    lines.append("ELEMENTS:")
    for line in bp.get("lines", []):
        style = line.get("style", "solid")
        lines.append("- Segment {} to {} ({})".format(line["from"], line["to"], style))

    for circle in bp.get("circles", []):
        lines.append("- Circle center={} radius={}".format(circle["center"], circle["radius"]))

    for arc in bp.get("arcs", []):
        lines.append("- Arc center={} from {} to {}".format(arc["center"], arc["from"], arc["to"]))

    for curve in bp.get("curves", []):
        eq = curve.get("equation", "")
        lines.append("- Curve: {}".format(eq))

    for face in bp.get("faces", []):
        pts = " ".join(face.get("points", []))
        style = face.get("style", "translucent")
        lines.append("- Face {} ({})".format(pts, style))

    for plane in bp.get("planes", []):
        eq = plane.get("equation", "")
        lines.append("- Plane: {}".format(eq))

    for sphere in bp.get("spheres", []):
        lines.append("- Sphere center={} radius={}".format(sphere["center"], sphere["radius"]))

    for vec in bp.get("vectors", []):
        lines.append("- Vector from {} to {}".format(vec["from"], vec["to"]))
    lines.append("")

    # ANGLES
    angles = bp.get("angles", [])
    if angles:
        lines.append("ANGLES:")
        asked = bp.get("asked", [])
        for angle in angles:
            v = angle.get("vertex", "?")
            p1 = angle.get("p1", "?")
            p2 = angle.get("p2", "?")
            val = angle.get("value")
            aid = angle.get("id", "")
            if aid in asked:
                lines.append("- Angle at {} between {}{} and {}{} = ? (asked, highlight)".format(
                    v, v, p1, v, p2))
            elif val is not None:
                lines.append("- Angle at {} between {}{} and {}{} = {} degrees".format(
                    v, v, p1, v, p2, val))
        lines.append("")

    # LABELS
    given = bp.get("given", {})
    asked = bp.get("asked", [])
    if given or asked:
        lines.append("LABELS:")
        for key, val in given.items():
            lines.append('- {}: "{}"'.format(key, val))
        for key in asked:
            lines.append('- {}: "?" (asked, highlight)'.format(key))
        lines.append("")

    # GIVEN / ASKED
    if given:
        lines.append("GIVEN:")
        for key, val in given.items():
            lines.append("- {} = {}".format(key, val))
        lines.append("")

    if asked:
        lines.append("ASKED:")
        for key in asked:
            lines.append("- {}".format(key))
        lines.append("")

    # COORDINATE_SYSTEM
    axes = bp.get("axes", False)
    lines.append("COORDINATE_SYSTEM:")
    lines.append("- axes: {}".format("true" if axes else "false"))
    if axes:
        cr = bp.get("coordinate_range", {})
        lines.append("- x_range: [{}, {}]".format(cr.get("x_min", -10), cr.get("x_max", 10)))
        lines.append("- y_range: [{}, {}]".format(cr.get("y_min", -10), cr.get("y_max", 10)))
        if "z_min" in cr:
            lines.append("- z_range: [{}, {}]".format(cr.get("z_min", -10), cr.get("z_max", 10)))
        lines.append("- grid: {}".format("true" if bp.get("grid", False) else "false"))
    lines.append("")

    lines.append("INTERACTIVE:")
    lines.append("- none")

    return "\n".join(lines)


def compute_math(
    question_text,      # type: str
    dimension_type,     # type: str
    api_key=None,       # type: Optional[str]
):
    # type: (...) -> dict
    """Stage 2: Call Gemini Flash with hybrid blueprint prompt, then convert to notes.

    Uses the hybrid blueprint prompt (structured JSON output) for better quality,
    then converts the JSON blueprint to text notes for Stage 3 (DeepSeek JS).

    Returns:
        dict with keys: success, notes, raw_notes, duration, tokens, error
    """
    from js_pipeline_prompts_hybrid import get_hybrid_blueprint_prompt

    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {"success": False, "notes": "", "raw_notes": "",
                "duration": 0, "tokens": {}, "error": "GEMINI_API_KEY not set"}

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        return {"success": False, "notes": "", "raw_notes": "",
                "duration": 0, "tokens": {}, "error": "google-genai package not installed"}

    client = genai.Client(api_key=api_key)
    system_prompt = get_hybrid_blueprint_prompt(dimension_type)

    user_message = "Question: {q}".format(q=question_text)

    try:
        start = time.time()
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=[
                {"role": "user", "parts": [{"text": system_prompt + "\n\n" + user_message}]}
            ],
            config={
                "max_output_tokens": 40000,
                "temperature": 0.1,
                "thinking_config": types.ThinkingConfig(thinking_budget=8000),
            },
        )
        duration = time.time() - start

        # Extract text from response
        raw_response = ""
        if response.candidates and response.candidates[0].content:
            for part in response.candidates[0].content.parts:
                if hasattr(part, "text") and part.text:
                    raw_response += part.text

        if not raw_response.strip():
            return {"success": False, "notes": "", "raw_notes": "",
                    "duration": duration, "tokens": {},
                    "error": "Empty response from Gemini"}

        # Extract token usage
        tokens = {}
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            um = response.usage_metadata
            tokens = {
                "prompt": getattr(um, "prompt_token_count", 0) or 0,
                "completion": getattr(um, "candidates_token_count", 0) or 0,
                "thinking": getattr(um, "thinking_token_count", 0) or 0,
                "total": getattr(um, "total_token_count", 0) or 0,
            }

        # Extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', raw_response)
        if not json_match:
            return {"success": False, "notes": "", "raw_notes": raw_response,
                    "duration": duration, "tokens": tokens,
                    "error": "No JSON found in Gemini response"}

        blueprint_json = json_match.group(0)

        # Convert JSON blueprint to text notes for Stage 3
        notes = blueprint_json_to_notes(blueprint_json, question_text)

        logger.info(
            "Gemini hybrid blueprint computed in {dur:.1f}s ({tok} tokens, {think} thinking)".format(
                dur=duration,
                tok=tokens.get("total", "?"),
                think=tokens.get("thinking", "?"),
            )
        )

        return {
            "success": True,
            "notes": notes,
            "raw_notes": raw_response,
            "duration": duration,
            "tokens": tokens,
            "error": None,
        }

    except Exception as e:
        logger.error("Gemini API error: {}".format(e))
        return {"success": False, "notes": "", "raw_notes": "",
                "duration": 0, "tokens": {}, "error": str(e)}


def generate_js(
    question_text,      # type: str
    computation_notes,  # type: str
    dimension_type,     # type: str
    api_key=None,       # type: Optional[str]
    error_context=None, # type: Optional[str]
):
    # type: (...) -> dict
    """Stage 3: Call DeepSeek to generate HTML from computation notes.

    Returns:
        dict with keys: success, html, duration, tokens, error
    """
    from js_pipeline_prompts import get_js_prompt
    from generate_code_js import extract_html, postprocess_js

    from openai import OpenAI

    if not api_key:
        api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        return {"success": False, "html": "", "duration": 0, "tokens": {},
                "error": "DEEPSEEK_API_KEY not set"}

    client = OpenAI(base_url=DEEPSEEK_ENDPOINT, api_key=api_key)
    system_prompt = get_js_prompt(dimension_type)

    user_message = (
        "=== ORIGINAL QUESTION ===\n"
        "{q}\n\n"
        "=== COMPUTATION NOTES ===\n"
        "{notes}\n"
        "=== END ==="
    ).format(q=question_text, notes=computation_notes)

    if error_context:
        user_message += (
            "\n\n--- PREVIOUS ATTEMPT FAILED ---\n"
            "The previous code produced this error:\n{err}\n"
            "Please fix the issue and generate corrected code.\n"
            "--- END ERROR ---"
        ).format(err=error_context)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    try:
        start = time.time()
        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=messages,
            max_tokens=16384,
            temperature=0.0,
        )
        duration = time.time() - start

        content = response.choices[0].message.content or ""
        tokens = {
            "prompt": response.usage.prompt_tokens if response.usage else 0,
            "completion": response.usage.completion_tokens if response.usage else 0,
            "total": response.usage.total_tokens if response.usage else 0,
        }

        html = extract_html(content)
        if not html:
            return {"success": False, "html": content, "duration": duration,
                    "tokens": tokens, "error": "No valid HTML found in response"}

        html = postprocess_js(html)

        logger.info(
            "DeepSeek JS generated in {dur:.1f}s ({tok} tokens, {chars} chars)".format(
                dur=duration, tok=tokens["total"], chars=len(html)
            )
        )

        return {
            "success": True,
            "html": html,
            "duration": duration,
            "tokens": tokens,
            "error": None,
        }

    except Exception as e:
        logger.error("DeepSeek API error: {}".format(e))
        return {"success": False, "html": "", "duration": 0, "tokens": {},
                "error": str(e)}


def generate_diagram(
    question_text,          # type: str
    dimension_type="auto",  # type: str
    output_path=None,       # type: Optional[str]
    max_retries=1,          # type: int
):
    # type: (...) -> dict
    """Full pipeline: classify (if auto) -> compute math -> generate JS -> save HTML.

    Returns dict with: success, html, dimension, duration, tokens, output_path, error, math_notes
    """
    total_start = time.time()
    all_tokens = {"gemini_math": {}, "deepseek_js": {}}

    # Stage 1: Classify if needed
    if dimension_type == "auto":
        from generate_code_js import classify_dimension
        dimension_type = classify_dimension(question_text)
        logger.info("Classified as: {}".format(dimension_type))

    # Normalize coordinate_* to plain 2d/3d for rendering
    render_dim = dimension_type.replace("coordinate_", "")

    # Stage 2: Compute math with Gemini
    logger.info("--- Stage 2: Computing math (Gemini Flash) ---")
    math_result = compute_math(question_text, dimension_type)
    all_tokens["gemini_math"] = math_result.get("tokens", {})

    if not math_result["success"]:
        return {
            "success": False,
            "html": "",
            "dimension": render_dim,
            "duration": time.time() - total_start,
            "tokens": all_tokens,
            "output_path": None,
            "error": "Math computation failed: {}".format(math_result["error"]),
            "math_notes": "",
        }

    math_notes = math_result["notes"]
    logger.info("Math notes: {} chars".format(len(math_notes)))

    # Stage 3: Generate JS with DeepSeek
    logger.info("--- Stage 3: Generating JS (DeepSeek V3.2) ---")
    js_result = generate_js(question_text, math_notes, render_dim)
    all_tokens["deepseek_js"] = js_result.get("tokens", {})

    # Retry on failure
    if not js_result["success"] and max_retries > 0:
        logger.warning("JS generation failed: {}. Retrying...".format(js_result["error"]))
        js_result = generate_js(
            question_text, math_notes, render_dim,
            error_context=js_result.get("error", "Unknown error"),
        )
        all_tokens["deepseek_js_retry"] = js_result.get("tokens", {})

    # Save output
    if js_result["success"] and output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(js_result["html"], encoding="utf-8")
        logger.info("Saved to {}".format(out))

    total_duration = time.time() - total_start
    logger.info("Pipeline completed in {:.1f}s".format(total_duration))

    return {
        "success": js_result["success"],
        "html": js_result.get("html", ""),
        "dimension": render_dim,
        "duration": total_duration,
        "tokens": all_tokens,
        "output_path": str(output_path) if output_path else None,
        "error": js_result.get("error"),
        "math_notes": math_notes,
    }


def main():
    parser = argparse.ArgumentParser(description="3-stage JS geometry pipeline")
    parser.add_argument("--question", "-q", required=True, help="Geometry question text")
    parser.add_argument("--dim", "-d", default="auto",
                        choices=["2d", "3d", "coordinate_2d", "coordinate_3d", "auto"],
                        help="Dimension type (default: auto-classify)")
    parser.add_argument("--output", "-o", default="output/diagram.html",
                        help="Output HTML file path")
    parser.add_argument("--save-notes", action="store_true",
                        help="Also save computation notes to a .txt file")
    args = parser.parse_args()

    result = generate_diagram(args.question, args.dim, args.output)

    if result["success"]:
        print("\nSuccess! Saved to {}".format(result["output_path"]))
        print("  Dimension: {}".format(result["dimension"]))
        print("  Duration: {:.1f}s".format(result["duration"]))

        # Print token breakdown
        tokens = result["tokens"]
        gemini_tok = tokens.get("gemini_math", {}).get("total", 0)
        ds_tok = tokens.get("deepseek_js", {}).get("total", 0)
        print("  Tokens: Gemini={}, DeepSeek={}".format(gemini_tok, ds_tok))

        if args.save_notes and result["math_notes"]:
            notes_path = Path(args.output).with_suffix(".notes.txt")
            notes_path.write_text(result["math_notes"], encoding="utf-8")
            print("  Notes saved to {}".format(notes_path))
    else:
        print("\nFailed: {}".format(result["error"]))
        sys.exit(1)


if __name__ == "__main__":
    main()
