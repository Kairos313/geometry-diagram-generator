#!/usr/bin/env python3
"""
Stage 1 (DeepSeek Direct): Generate a geometric blueprint from question text.

Uses deepseek-reasoner via direct DeepSeek API with reasoning/thinking mode
for accurate geometric calculations.

Same interface as generate_blueprint.py so it can be swapped in batch_test.py.

Usage:
    python3 generate_blueprint_deepseek_direct.py --question-text "In triangle ABC, angle ACB = 90°, AD = 12cm."
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

# Direct DeepSeek API endpoint
DEEPSEEK_ENDPOINT = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-reasoner"  # Reasoning mode for geometry calculations


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
    """Call DeepSeek-Reasoner to generate the geometric blueprint.

    Uses reasoning mode for accurate geometric calculations.

    Args:
        compact: If True, use the compact JSON prompt.

    Returns a dict with keys: success, blueprint, coordinates_file,
    api_call_duration, prompt_tokens, completion_tokens, total_tokens,
    reasoning_tokens (if available).
    """
    client = OpenAI(
        base_url=DEEPSEEK_ENDPOINT,
        api_key=api_key,
    )

    # Select prompt based on compact mode
    if compact:
        prompt_template = Question_to_Blueprint_Compact
        logger.info("Using COMPACT JSON blueprint prompt (DeepSeek Reasoner)")
    else:
        prompt_template = Question_to_Blueprint_Coordinate_included
        logger.info("Using VERBOSE markdown blueprint prompt (DeepSeek Reasoner)")

    user_message = (
        f"{prompt_template}\n\n"
        f"--- QUESTION ---\n{question_text}\n--- END QUESTION ---"
    )

    # Note: DeepSeek via OpenAI API doesn't support image parts.
    if image_path:
        logger.warning("DeepSeek blueprint generation does not support question images; ignoring --question-image")

    messages = [
        {"role": "user", "content": user_message},
    ]

    try:
        start = time.time()
        logger.info("Calling DeepSeek-Reasoner (with thinking) for blueprint generation...")

        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=messages,
            max_tokens=64000,  # DeepSeek Reasoner max limit (64K)
            temperature=0.1,
        )

        elapsed = time.time() - start

        # Extract reasoning content if available (thinking process)
        reasoning_content = getattr(response.choices[0].message, 'reasoning_content', None)
        reasoning_tokens = 0
        if reasoning_content:
            reasoning_tokens = len(reasoning_content.split())
            logger.info(f"Reasoning tokens used: {reasoning_tokens}")

        blueprint_text = response.choices[0].message.content
        usage = response.usage

        logger.info(f"API call completed in {elapsed:.2f}s")
        logger.info(f"Token usage - Input: {usage.prompt_tokens}, Output: {usage.completion_tokens}, Total: {usage.total_tokens}")

        if not blueprint_text or not blueprint_text.strip():
            error_msg = f"Empty response from DeepSeek (reasoning tokens: {reasoning_tokens}, output tokens: {usage.completion_tokens})"
            logger.error(error_msg)
            logger.error(f"Full response object: {response}")
            return {
                "success": False,
                "error": error_msg,
                "api_call_duration": elapsed,
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
            }

        # Determine dimension
        if compact:
            parsed = parse_compact_blueprint(blueprint_text)
            if parsed:
                dimension = extract_dimension_from_json(parsed)
            else:
                dimension = "2d"  # fallback
        else:
            dimension = extract_dimension(blueprint_text)

        # Save blueprint
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        if compact:
            coordinates_file = output_path / "coordinates.json"
            with open(coordinates_file, "w") as f:
                if parsed:
                    json.dump(parsed, f, indent=2)
                else:
                    f.write(blueprint_text)
            logger.info(f"Compact JSON blueprint saved to: {coordinates_file}")
        else:
            coordinates_file = output_path / "coordinates.txt"
            with open(coordinates_file, "w") as f:
                f.write(blueprint_text)
            logger.info(f"Blueprint saved to: {coordinates_file}")

        return {
            "success": True,
            "blueprint": blueprint_text,
            "coordinates_file": str(coordinates_file),
            "dimension": dimension,
            "api_call_duration": elapsed,
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
        }

    except Exception as e:
        logger.error(f"API call failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "api_call_duration": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }


def main():
    parser = argparse.ArgumentParser(description="Generate geometric blueprint using DeepSeek-Reasoner")
    parser.add_argument("--question-text", required=True, help="The geometry question text or path to text file")
    parser.add_argument("--question-image", help="Optional path to question image (not supported by DeepSeek)")
    parser.add_argument("--output-dir", default="output", help="Directory to save blueprint")
    parser.add_argument("--compact", action="store_true", help="Use compact JSON format")

    args = parser.parse_args()

    # Get API key
    api_key = os.getenv("NEW_DEEPSEEK_API_KEY")
    if not api_key:
        logger.error("NEW_DEEPSEEK_API_KEY environment variable not set")
        sys.exit(1)

    # Read question text from file if it's a path
    question_text = args.question_text
    if Path(question_text).is_file():
        with open(question_text, "r") as f:
            question_text = f.read().strip()

    # Generate blueprint
    result = generate_blueprint(
        api_key=api_key,
        question_text=question_text,
        output_dir=args.output_dir,
        image_path=args.question_image,
        compact=args.compact,
    )

    if result["success"]:
        print(f"✓ Blueprint generated successfully")
        print(f"  Dimension: {result.get('dimension', 'unknown')}")
        print(f"  Output: {result['coordinates_file']}")
        print(f"  Time: {result['api_call_duration']:.2f}s")
        print(f"  Tokens: {result['total_tokens']} ({result['prompt_tokens']} in, {result['completion_tokens']} out)")
        sys.exit(0)
    else:
        print(f"✗ Blueprint generation failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
