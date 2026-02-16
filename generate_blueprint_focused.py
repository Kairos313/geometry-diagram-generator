#!/usr/bin/env python3
"""
Stage 1: Generate geometric blueprint using LLM classifier + focused prompts.

This approach:
1. Uses LLM to classify question type (2d, 3d, coordinate_2d, coordinate_3d)
2. Selects appropriate focused prompt (~1200 tokens each, 70% smaller)
3. Generates blueprint with optimal prompt

Total cost: Classifier (~$0.0001) + Blueprint (~$0.003) = ~$0.0031
vs Comprehensive: ~$0.005
Savings: ~38% on blueprint generation

Output: coordinates.json (JSON blueprint)

Usage:
    python3 generate_blueprint_focused.py --question-text "Triangle ABC with AB = 12 cm..."
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types

from classify_geometry_type import classify_geometry_type
from coordinate_geometry_prompts import (
    Question_to_Blueprint_2D,
    Question_to_Blueprint_3D,
    Question_to_Blueprint_Coordinate_2D,
    Question_to_Blueprint_Coordinate_3D,
)

load_dotenv(".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def parse_compact_blueprint(text):
    # type: (str) -> Optional[dict]
    """Parse the compact JSON blueprint from the response text."""
    text = text.strip()

    # Remove markdown code blocks if present
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    else:
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
    dimension_type=None,  # type: Optional[str]
):
    # type: (...) -> dict
    """Call Gemini to generate geometric blueprint using classifier + focused prompts.

    Args:
        api_key: Gemini API key
        question_text: The geometry question text
        output_dir: Output directory for blueprint file
        image_path: Optional path to question image
        dimension_type: Optional explicit dimension type (skips classification)
                       One of: "2d", "3d", "coordinate_2d", "coordinate_3d"

    Returns:
        dict with keys: success, blueprint, coordinates_file, dimension,
        api_call_duration, prompt_tokens, completion_tokens, total_tokens,
        classifier_cost, blueprint_cost
    """
    client = genai.Client(api_key=api_key)

    classifier_cost = 0.0
    classifier_duration = 0.0

    # Step 1: Classify question type (if not provided)
    if dimension_type is None:
        logger.info("=== Step 1: Classifying question type ===")
        classify_result = classify_geometry_type(api_key, question_text)

        dimension_type = classify_result["dimension_type"]
        classifier_cost = classify_result["cost"]
        classifier_duration = classify_result["duration"]

        logger.info(f"Classification: {dimension_type} (confidence: {classify_result['confidence']}, "
                   f"{classifier_duration:.2f}s, ${classifier_cost:.6f})")
    else:
        logger.info(f"Using explicit dimension type: {dimension_type}")

    # Step 2: Select appropriate focused prompt
    prompt_map = {
        "2d": Question_to_Blueprint_2D,
        "3d": Question_to_Blueprint_3D,
        "coordinate_2d": Question_to_Blueprint_Coordinate_2D,
        "coordinate_3d": Question_to_Blueprint_Coordinate_3D,
    }

    prompt_template = prompt_map.get(dimension_type, Question_to_Blueprint_2D)
    logger.info(f"=== Step 2: Generating blueprint with {dimension_type} prompt ===")

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
        ext = Path(image_path).suffix.lower()
        mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp"}
        mime_type = mime_map.get(ext, "image/png")
        content_parts.append(types.Part.from_bytes(data=image_bytes, mime_type=mime_type))

    try:
        start = time.time()
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

        # Calculate blueprint cost
        input_cost = (usage.prompt_token_count / 1e6) * 0.50
        output_cost = (usage.candidates_token_count / 1e6) * 3.00
        blueprint_cost = input_cost + output_cost

        logger.info(f"Blueprint generated: {elapsed:.2f}s, ${blueprint_cost:.6f}")

        # Parse JSON blueprint
        parsed_json = parse_compact_blueprint(blueprint_text)
        os.makedirs(output_dir, exist_ok=True)

        if parsed_json:
            coords_file = os.path.join(output_dir, "coordinates.json")
            with open(coords_file, "w", encoding="utf-8") as f:
                json.dump(parsed_json, f, indent=2)
            logger.info(f"JSON blueprint saved to: {coords_file}")
        else:
            # Fallback: save raw text if JSON parsing fails
            coords_file = os.path.join(output_dir, "coordinates.txt")
            with open(coords_file, "w", encoding="utf-8") as f:
                f.write(f"=== GEOMETRIC BLUEPRINT ({dimension_type.upper()}) ===\n\n")
                f.write(blueprint_text)
            logger.warning(f"JSON parsing failed; saved raw text to: {coords_file}")

        total_cost = classifier_cost + blueprint_cost
        total_duration = classifier_duration + elapsed

        logger.info(f"=== Total: {total_duration:.2f}s, ${total_cost:.6f} ===")

        return {
            "success": True,
            "blueprint": blueprint_text,
            "coordinates_file": coords_file,
            "api_call_duration": elapsed,
            "total_duration": total_duration,
            "prompt_tokens": usage.prompt_token_count,
            "completion_tokens": usage.candidates_token_count,
            "total_tokens": usage.total_token_count,
            "dimension": dimension_type,
            "classifier_cost": classifier_cost,
            "blueprint_cost": blueprint_cost,
            "total_cost": total_cost,
        }

    except Exception as e:
        logger.error(f"Blueprint generation failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "api_call_duration": 0,
            "total_duration": classifier_duration,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "dimension": dimension_type,
            "classifier_cost": classifier_cost,
            "blueprint_cost": 0.0,
            "total_cost": classifier_cost,
        }


def main():
    parser = argparse.ArgumentParser(
        description="Generate geometric blueprint using LLM classifier + focused prompts"
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
        "--dimension-type",
        choices=["2d", "3d", "coordinate_2d", "coordinate_3d"],
        help="Explicit dimension type (skips classification)",
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
        dimension_type=args.dimension_type,
    )

    if result["success"]:
        print(f"\nSUCCESS!")
        print(f"Blueprint file: {result['coordinates_file']}")
        print(f"Dimension: {result['dimension']}")
        print(f"Total duration: {result['total_duration']:.2f}s")
        print(f"  - Classifier: {result.get('total_duration', 0) - result['api_call_duration']:.2f}s")
        print(f"  - Blueprint: {result['api_call_duration']:.2f}s")
        print(f"Total cost: ${result['total_cost']:.6f}")
        print(f"  - Classifier: ${result['classifier_cost']:.6f}")
        print(f"  - Blueprint: ${result['blueprint_cost']:.6f}")
        print(f"Tokens: {result['total_tokens']} (prompt: {result['prompt_tokens']}, completion: {result['completion_tokens']})")
    else:
        print(f"\nFAILED: {result.get('error', 'Unknown error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
