#!/usr/bin/env python3
"""
Stage 1: Analyze a geometry question image and generate a solution JSON.

Uses Gemini-3-Flash via OpenRouter (OpenAI client) to read the question image,
solve the problem, and output a structured JSON with solution steps, geometric
element references, and a 2D/3D dimension classification.

Output: geometry_solution.json

Usage:
    python analyze_question.py --question-image "Math Questions/question_7.png"
"""

import argparse
import base64
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

from pipeline_prompts import Solution_Analysis_v1

load_dotenv(".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class QuestionAnalyzer:
    """Analyze a geometry question image and produce a solution JSON."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable not set")
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.api_key,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(self, question_image_path: str, output_dir: str) -> bool:
        """Run the full analysis pipeline.

        Returns True on success, False on failure.
        """
        if not os.path.exists(question_image_path):
            logger.error(f"Image not found: {question_image_path}")
            return False

        # Call Gemini
        result = self._call_gemini(question_image_path)
        if not result["success"]:
            logger.error(f"API call failed: {result.get('error')}")
            return False

        # Extract JSON from response
        solution_json = self._extract_json(result["content"])
        if solution_json is None:
            logger.error("Failed to extract JSON from API response")
            return False

        # Ensure dimension_type is present
        if "dimension_type" not in solution_json:
            solution_json["dimension_type"] = self._classify_dimension(solution_json)
            logger.info(f"Auto-classified dimension_type: {solution_json['dimension_type']}")

        # Save
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, "geometry_solution.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(solution_json, f, indent=2)
        logger.info(f"Saved solution to: {out_path}")

        # Also save raw response for debugging
        raw_path = os.path.join(output_dir, "geometry_solution_raw.txt")
        with open(raw_path, "w", encoding="utf-8") as f:
            f.write(result["content"])

        logger.info(
            f"Tokens: {result['total_tokens']} "
            f"(in: {result['prompt_tokens']}, out: {result['completion_tokens']}) "
            f"in {result['api_call_duration']:.1f}s"
        )
        return True

    # ------------------------------------------------------------------
    # Gemini API call
    # ------------------------------------------------------------------

    def _call_gemini(self, image_path: str) -> dict:
        """Call Gemini-3-Flash via OpenRouter with the question image."""
        try:
            base64_image = self._encode_image(image_path)

            start = time.time()
            logger.info("Calling Gemini-3-Flash via OpenRouter...")
            completion = self.client.chat.completions.create(
                model="google/gemini-3-flash-preview",
                max_tokens=50000,
                temperature=0.1,
                extra_headers={
                    "HTTP-Referer": "https://github.com/geometry-image-generator",
                    "X-Title": "Geometry Question Analyzer",
                },
                extra_body={
                    "reasoning": {"enabled": True},
                },
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": Solution_Analysis_v1},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}"
                                },
                            },
                        ],
                    }
                ],
            )
            elapsed = time.time() - start

            content = completion.choices[0].message.content
            usage = completion.usage

            return {
                "success": True,
                "content": content,
                "api_call_duration": elapsed,
                "prompt_tokens": usage.prompt_tokens if usage else 0,
                "completion_tokens": usage.completion_tokens if usage else 0,
                "total_tokens": usage.total_tokens if usage else 0,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    # ------------------------------------------------------------------
    # JSON extraction
    # ------------------------------------------------------------------

    def _extract_json(self, content: str) -> Optional[dict]:
        """Extract the solution JSON from the model's response text."""
        # Try code blocks first
        blocks = re.findall(r"```json\s*(.*?)```", content, re.DOTALL)
        for block in blocks:
            obj = self._try_parse(block.strip())
            if obj and "solution_steps" in obj:
                return obj
            # Handle visual_output wrapper from older prompt formats
            if obj and "visual_output" in obj:
                return obj["visual_output"]

        # Fallback: find the outermost JSON object
        brace_depth = 0
        start = -1
        for i, ch in enumerate(content):
            if ch == "{":
                if brace_depth == 0:
                    start = i
                brace_depth += 1
            elif ch == "}":
                brace_depth -= 1
                if brace_depth == 0 and start != -1:
                    obj = self._try_parse(content[start : i + 1])
                    if obj and "solution_steps" in obj:
                        return obj
                    start = -1

        logger.error("Could not extract valid JSON from response")
        return None

    def _try_parse(self, text: str) -> Optional[dict]:
        """Attempt to parse JSON text, with LaTeX escape fixing."""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        # Fix common LaTeX backslash issues
        try:
            fixed = re.sub(r"(?<!\\)\\(?![\\\"nrtbfu/])", r"\\\\", text)
            return json.loads(fixed)
        except json.JSONDecodeError:
            return None

    # ------------------------------------------------------------------
    # Dimension classification
    # ------------------------------------------------------------------

    @staticmethod
    def _classify_dimension(solution: dict) -> str:
        """Classify a problem as 2D or 3D from element types in the solution."""
        three_d_types = {
            "polyhedron", "pyramid", "prism", "sphere", "cone", "cylinder",
            "plane", "surface", "curved_solid", "dihedral_angle",
        }
        for step in solution.get("solution_steps", []):
            for sentence in step.get("sentences", []):
                for elem in sentence.get("geometric_elements", []):
                    if elem.get("element_type", "").lower() in three_d_types:
                        return "3d"
        return "2d"

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _encode_image(path: str) -> str:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")


# ======================================================================
# CLI entry point
# ======================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Analyze geometry question image and generate solution JSON"
    )
    parser.add_argument(
        "--question-image", required=True,
        help="Path to the question image file",
    )
    parser.add_argument(
        "--output-dir", default=None,
        help="Output directory (default: <pipeline_dir>/math_solution_pipeline)",
    )
    args = parser.parse_args()

    pipeline_dir = Path(__file__).parent
    output_dir = args.output_dir or str(pipeline_dir / "math_solution_pipeline")

    try:
        analyzer = QuestionAnalyzer()
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)

    success = analyzer.analyze(args.question_image, output_dir)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
