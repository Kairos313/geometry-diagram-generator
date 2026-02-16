#!/usr/bin/env python3
"""
Stage 1 (DeepSeek): Generate a geometric blueprint from question text.

Uses DeepSeek-V3.2 via Azure OpenAI endpoint to compute exact coordinates
for every geometric element, producing a structured blueprint.

Same interface as generate_blueprint.py (Gemini) so they can be swapped
in batch_test.py via --blueprint-model deepseek.

Usage:
    python3 generate_blueprint_deepseek.py --question-text "In triangle ABC, angle ACB = 90°, AD = 12cm."
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
from openai import OpenAI

from diagram_prompts import Question_to_Blueprint_Coordinate_included, Question_to_Blueprint_Compact

load_dotenv(".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Azure endpoint for DeepSeek-V3.2
DEEPSEEK_ENDPOINT = "https://raksh-m4jj47jc-japaneast.services.ai.azure.com/openai/v1/"
DEEPSEEK_MODEL = "DeepSeek-V3.2"


def extract_dimension(blueprint_text):
    # type: (str) -> str
    """Extract the dimension declaration from the blueprint text.

    Returns '2d', '3d', or 'coordinate_2d'. Defaults to '2d'.
    """
    coord_match = re.search(r'\*{0,2}DIMENSION:\s*(COORDINATE_2D)\*{0,2}', blueprint_text, re.IGNORECASE)
    if coord_match:
        return "coordinate_2d"

    match = re.search(r'\*{0,2}DIMENSION:\s*(2D|3D)\*{0,2}', blueprint_text, re.IGNORECASE)
    if match:
        return match.group(1).lower()

    return "2d"


def extract_dimension_from_json(data):
    # type: (dict) -> str
    """Extract dimension from a parsed JSON blueprint."""
    dim = data.get("dimension", "2d").lower()
    if dim in ("2d", "3d", "coordinate_2d"):
        return dim

    # Fallback: check if any point has non-zero Z
    points = data.get("points", {})
    for coords in points.values():
        if isinstance(coords, (list, tuple)) and len(coords) >= 3:
            if abs(coords[2]) > 1e-6:
                return "3d"
    return "2d"


def parse_compact_blueprint(response_text):
    # type: (str) -> Optional[dict]
    """Parse a compact JSON blueprint from the response text."""
    text = response_text.strip()

    # Remove markdown code block if present
    if text.startswith("```"):
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1:]
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
    compact=False,    # type: bool
):
    # type: (...) -> dict
    """Call DeepSeek-V3.2 to generate the geometric blueprint.

    Args:
        compact: If True, use the compact JSON prompt.

    Returns a dict with keys: success, blueprint, coordinates_file,
    api_call_duration, prompt_tokens, completion_tokens, total_tokens.
    """
    client = OpenAI(
        base_url=DEEPSEEK_ENDPOINT,
        api_key=api_key,
    )

    # Select prompt based on compact mode
    if compact:
        prompt_template = Question_to_Blueprint_Compact
        logger.info("Using COMPACT JSON blueprint prompt (DeepSeek)")
    else:
        prompt_template = Question_to_Blueprint_Coordinate_included
        logger.info("Using VERBOSE markdown blueprint prompt (DeepSeek)")

    user_message = (
        f"{prompt_template}\n\n"
        f"--- QUESTION ---\n{question_text}\n--- END QUESTION ---"
    )

    # Note: DeepSeek via OpenAI API doesn't support image parts.
    # If image_path is provided, log a warning.
    if image_path:
        logger.warning("DeepSeek blueprint generation does not support question images; ignoring --question-image")

    messages = [
        {"role": "user", "content": user_message},
    ]

    try:
        start = time.time()
        logger.info("Calling DeepSeek-V3.2 for blueprint generation...")

        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=messages,
            max_tokens=20000,
            temperature=0.1,
        )
        elapsed = time.time() - start

        message = response.choices[0].message
        blueprint_text = message.content
        usage = response.usage

        # Extract dimension and save based on mode
        if compact:
            parsed_json = parse_compact_blueprint(blueprint_text)
            if parsed_json:
                dimension = extract_dimension_from_json(parsed_json)
                os.makedirs(output_dir, exist_ok=True)
                coords_file = os.path.join(output_dir, "coordinates.json")
                with open(coords_file, "w", encoding="utf-8") as f:
                    json.dump(parsed_json, f, indent=2)
                logger.info(f"Compact JSON blueprint saved to: {coords_file}")
            else:
                # Fallback: save raw text if JSON parsing fails
                dimension = extract_dimension(blueprint_text)
                os.makedirs(output_dir, exist_ok=True)
                coords_file = os.path.join(output_dir, "coordinates.txt")
                with open(coords_file, "w", encoding="utf-8") as f:
                    f.write("=== GEOMETRIC BLUEPRINT (JSON PARSE FAILED) ===\n\n")
                    f.write(blueprint_text)
                logger.warning(f"JSON parsing failed; saved raw text to: {coords_file}")
        else:
            dimension = extract_dimension(blueprint_text)
            os.makedirs(output_dir, exist_ok=True)
            coords_file = os.path.join(output_dir, "coordinates.txt")
            with open(coords_file, "w", encoding="utf-8") as f:
                f.write("=== GEOMETRIC BLUEPRINT - COORDINATES ===\n\n")
                f.write(blueprint_text)
            logger.info(f"Blueprint saved to: {coords_file}")

        return {
            "success": True,
            "blueprint": blueprint_text,
            "dimension": dimension,
            "coordinates_file": coords_file,
            "api_call_duration": elapsed,
            "prompt_tokens": usage.prompt_tokens if usage else 0,
            "completion_tokens": usage.completion_tokens if usage else 0,
            "total_tokens": usage.total_tokens if usage else 0,
        }

    except Exception as e:
        logger.error(f"DeepSeek blueprint generation failed: {e}")
        return {"success": False, "error": str(e)}


# ======================================================================
# CLI
# ======================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Generate geometric blueprint from question text using DeepSeek-V3.2"
    )
    parser.add_argument(
        "--question-text", required=True,
        help="Question text (literal string or path to a .txt file)",
    )
    parser.add_argument(
        "--output-dir", default="output",
        help="Directory for output files",
    )
    parser.add_argument(
        "--compact", action="store_true",
        help="Use compact JSON blueprint prompt",
    )
    args = parser.parse_args()

    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        logger.error("DEEPSEEK_API_KEY environment variable not set")
        sys.exit(1)

    question_text = args.question_text
    if os.path.isfile(question_text):
        with open(question_text, "r", encoding="utf-8") as f:
            question_text = f.read().strip()

    result = generate_blueprint(
        api_key=api_key,
        question_text=question_text,
        output_dir=args.output_dir,
        compact=args.compact,
    )

    if result["success"]:
        logger.info(
            f"Blueprint generated — Tokens: {result['total_tokens']} "
            f"(in: {result['prompt_tokens']}, out: {result['completion_tokens']}) "
            f"in {result['api_call_duration']:.1f}s"
        )
        logger.info(f"Dimension: {result['dimension']}")
        logger.info(f"Saved to: {result['coordinates_file']}")
    else:
        logger.error(f"Failed: {result['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
