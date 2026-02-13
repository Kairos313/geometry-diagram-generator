#!/usr/bin/env python3
"""
Stage 1: Generate a comprehensive geometric blueprint from question text.

Uses the Question_to_Blueprint_Compact_All prompt that handles ALL 4 geometry types:
- 2D: Traditional 2D geometry
- 3D: Traditional 3D geometry
- COORDINATE_2D: 2D with coordinate system/graphing
- COORDINATE_3D: 3D with coordinate system/graphing

Uses Gemini-3-Flash via Google GenAI client with thinking enabled.

Output: coordinates.json (JSON blueprint)

Usage:
    python3 generate_blueprint_comprehensive.py --question-text "Plot points A(0,0), B(3,4)..."
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

from coordinate_geometry_prompts import Question_to_Blueprint_Compact_All

load_dotenv(".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def extract_dimension_from_json(blueprint_json):
    # type: (dict) -> str
    """Extract dimension from parsed JSON blueprint.

    Returns '2d', '3d', 'coordinate_2d', or 'coordinate_3d'.
    Defaults to '2d' if not found.
    """
    dimension = blueprint_json.get("dimension", "2d")

    # Normalize to lowercase
    dimension = dimension.lower()

    # Map variations
    dimension_map = {
        "2d": "2d",
        "3d": "3d",
        "coordinate_2d": "coordinate_2d",
        "coordinate_3d": "coordinate_3d",
        "coord_2d": "coordinate_2d",
        "coord_3d": "coordinate_3d",
    }

    normalized = dimension_map.get(dimension, "2d")
    logger.info(f"Extracted dimension from JSON: {normalized}")
    return normalized


def extract_dimension(blueprint_text):
    # type: (str) -> str
    """Extract the dimension declaration from blueprint text (fallback).

    Returns '2d', '3d', 'coordinate_2d', or 'coordinate_3d'.
    Defaults to '2d' if not found.
    """
    # Check for COORDINATE_3D first
    coord3d_match = re.search(r'\*{0,2}DIMENSION:\s*(COORDINATE_3D|coordinate_3d)\*{0,2}', blueprint_text, re.IGNORECASE)
    if coord3d_match:
        logger.info("Extracted dimension from blueprint: coordinate_3d")
        return "coordinate_3d"

    # Check for COORDINATE_2D
    coord2d_match = re.search(r'\*{0,2}DIMENSION:\s*(COORDINATE_2D|coordinate_2d)\*{0,2}', blueprint_text, re.IGNORECASE)
    if coord2d_match:
        logger.info("Extracted dimension from blueprint: coordinate_2d")
        return "coordinate_2d"

    # Check for regular 3D
    dim_match = re.search(r'\*{0,2}DIMENSION:\s*(3D|2D)\*{0,2}', blueprint_text, re.IGNORECASE)
    if dim_match:
        dim = dim_match.group(1).lower()
        logger.info(f"Extracted dimension from blueprint: {dim}")
        return dim

    # Fallback: check Z coordinates
    if re.search(r'\[\s*[\d.-]+\s*,\s*[\d.-]+\s*,\s*[1-9][\d.]*\s*\]', blueprint_text):
        logger.info("Detected 3D from non-zero Z coordinates")
        return "3d"

    logger.info("Defaulting to 2D (no dimension found)")
    return "2d"


def parse_compact_blueprint(text):
    # type: (str) -> Optional[dict]
    """Parse the compact JSON blueprint from the response text.

    Handles markdown code blocks and returns parsed JSON dict.
    """
    text = text.strip()

    # Remove markdown code blocks if present
    if text.startswith("```"):
        # Remove opening ```json or ```
        lines = text.split("\n")
        if lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    else:
        # Try to extract content between ``` markers
        if text.startswith("```"):
            text = text[3:].strip()
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
    """Call Gemini to generate the comprehensive geometric blueprint.

    Returns a dict with keys: success, blueprint, coordinates_file,
    api_call_duration, prompt_tokens, completion_tokens, total_tokens, dimension.
    """
    client = genai.Client(api_key=api_key)

    prompt_template = Question_to_Blueprint_Compact_All

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
        logger.info("Calling Gemini-3-Flash for comprehensive blueprint generation...")
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
                f.write("=== COMPREHENSIVE GEOMETRIC BLUEPRINT (JSON PARSE FAILED) ===\n\n")
                f.write(blueprint_text)
            logger.warning(f"JSON parsing failed; saved raw text to: {coords_file}")

        return {
            "success": True,
            "blueprint": blueprint_text,
            "coordinates_file": coords_file,
            "api_call_duration": elapsed,
            "prompt_tokens": usage.prompt_token_count,
            "completion_tokens": usage.candidates_token_count,
            "total_tokens": usage.total_token_count,
            "dimension": dimension,
        }

    except Exception as e:
        logger.error(f"Blueprint generation failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "api_call_duration": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }


def main():
    parser = argparse.ArgumentParser(
        description="Generate comprehensive geometric blueprint using Gemini-3-Flash"
    )
    parser.add_argument(
        "--question-text",
        required=True,
        help="Question text or path to question text file",
    )
    parser.add_argument(
        "--question-image",
        help="Path to question image (optional)",
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Output directory (default: output)",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("GEMINI_API_KEY"),
        help="Gemini API key (or use GEMINI_API_KEY env var)",
    )

    args = parser.parse_args()

    if not args.api_key:
        print("Error: GEMINI_API_KEY not set")
        sys.exit(1)

    # Read question text from file if it's a path
    question_text = args.question_text
    if Path(question_text).is_file():
        with open(question_text, "r", encoding="utf-8") as f:
            question_text = f.read().strip()

    result = generate_blueprint(
        api_key=args.api_key,
        question_text=question_text,
        output_dir=args.output_dir,
        image_path=args.question_image,
    )

    if result["success"]:
        print(f"\nSUCCESS!")
        print(f"Blueprint file: {result['coordinates_file']}")
        print(f"Dimension: {result['dimension']}")
        print(f"Duration: {result['api_call_duration']:.2f}s")
        print(f"Tokens: {result['total_tokens']} (prompt: {result['prompt_tokens']}, completion: {result['completion_tokens']})")
    else:
        print(f"\nFAILED: {result.get('error', 'Unknown error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
