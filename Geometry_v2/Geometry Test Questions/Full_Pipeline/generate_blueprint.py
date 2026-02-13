#!/usr/bin/env python3
"""
Stage 1: Generate a geometric blueprint (coordinates.txt) from question text.

Uses Gemini-3-Flash via Google GenAI client with thinking enabled
to compute exact coordinates for every geometric element.

Output: coordinates.txt

Usage:
    python3 generate_blueprint.py --question-text "In triangle ABC, angle ACB = 90°, AD = 12cm, BC = 12cm."
    python3 generate_blueprint.py --question-text question.txt --question-image question.png
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

from diagram_prompts import Question_to_Blueprint_Compact

load_dotenv(".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def extract_dimension(blueprint_text):
    # type: (str) -> str
    """Extract the dimension declaration from the blueprint.

    Looks for 'DIMENSION: 2D', 'DIMENSION: 3D', or 'DIMENSION: COORDINATE_2D'.
    Returns '2d', '3d', or 'coordinate_2d'. Defaults to '2d' if not found.
    """
    # Check for COORDINATE_2D first
    coord_match = re.search(r'\*{0,2}DIMENSION:\s*(COORDINATE_2D)\*{0,2}', blueprint_text, re.IGNORECASE)
    if coord_match:
        logger.info("Extracted dimension from blueprint: coordinate_2d")
        return "coordinate_2d"

    # Look for explicit 2D/3D dimension declaration
    match = re.search(r'\*{0,2}DIMENSION:\s*(2D|3D)\*{0,2}', blueprint_text, re.IGNORECASE)
    if match:
        dim = match.group(1).lower()
        logger.info(f"Extracted dimension from blueprint: {dim}")
        return dim

    # Fallback: check for 3D keywords in the question objective
    if re.search(r'\b(prism|pyramid|cube|cuboid|sphere|cylinder|cone|tetrahedron|3D|three.?dimensional)\b',
                 blueprint_text[:2000], re.IGNORECASE):
        logger.info("Dimension not declared; inferring 3D from keywords")
        return "3d"

    logger.info("Dimension not declared; defaulting to 2D")
    return "2d"


def extract_dimension_from_json(blueprint_json):
    # type: (dict) -> str
    """Extract dimension from a compact JSON blueprint.

    Returns '2d', '3d', or 'coordinate_2d'.
    """
    dim = blueprint_json.get("dimension", "2d").lower()
    if dim in ("2d", "3d", "coordinate_2d"):
        logger.info(f"Extracted dimension from JSON blueprint: {dim}")
        return dim
    logger.info(f"Unknown dimension '{dim}'; defaulting to 2d")
    return "2d"


def parse_compact_blueprint(response_text):
    # type: (str) -> Optional[dict]
    """Parse a compact JSON blueprint from the response text.

    Handles markdown code blocks and raw JSON.
    Returns the parsed dict or None if parsing fails.
    """
    text = response_text.strip()

    # Remove markdown code block if present
    if text.startswith("```"):
        # Find the end of the opening fence
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1:]
        # Remove closing fence
        if text.endswith("```"):
            text = text[:-3].strip()
        elif "```" in text:
            text = text[:text.rfind("```")].strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON blueprint: {e}")
        return None


def generate_blueprint(
    api_key,          # type: str
    question_text,    # type: str
    output_dir,       # type: str
    image_path=None,  # type: Optional[str]
):
    # type: (...) -> dict
    """Call Gemini to generate the geometric blueprint.

    Returns a dict with keys: success, blueprint, coordinates_file,
    api_call_duration, prompt_tokens, completion_tokens, total_tokens.
    """
    client = genai.Client(api_key=api_key)

    prompt_template = Question_to_Blueprint_Compact

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
        logger.info("Calling Gemini-3-Flash for blueprint generation...")
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=content_parts,
            config={
                "max_output_tokens": 20000,
                "temperature": 0.1,
                "thinking_config": types.ThinkingConfig(thinking_budget=8000),
            },
        )
        elapsed = time.time() - start

        blueprint_text = response.text
        usage = response.usage_metadata

        # Parse JSON blueprint and extract dimension
        parsed_json = parse_compact_blueprint(blueprint_text)
        os.makedirs(output_dir, exist_ok=True)
        if parsed_json:
            dimension = extract_dimension_from_json(parsed_json)
            coords_file = os.path.join(output_dir, "coordinates.json")
            with open(coords_file, "w", encoding="utf-8") as f:
                json.dump(parsed_json, f, indent=2)
            logger.info(f"JSON blueprint saved to: {coords_file}")
        else:
            # Fallback: save raw text if JSON parsing fails
            dimension = extract_dimension(blueprint_text)
            coords_file = os.path.join(output_dir, "coordinates.txt")
            with open(coords_file, "w", encoding="utf-8") as f:
                f.write("=== GEOMETRIC BLUEPRINT (JSON PARSE FAILED) ===\n\n")
                f.write(blueprint_text)
            logger.warning(f"JSON parsing failed; saved raw text to: {coords_file}")

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

    except Exception as e:
        return {"success": False, "error": str(e)}


# ======================================================================
# CLI
# ======================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Generate geometric blueprint from question text"
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
        help="Output directory for coordinates.txt (default: script directory)",
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
