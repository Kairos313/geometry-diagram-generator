#!/usr/bin/env python3
"""
Lightweight LLM-based classifier to determine geometry question dimension.

Uses a minimal prompt (~80 tokens) with Gemini Flash to classify questions as:
- 2d: Flat/planar geometry — triangles, circles, coordinate geometry with x/y only,
      equations with x and y (e.g. y=2x+1, x²+y²=25), graph sketching, loci
- 3d: Any 3D geometry — pyramids, prisms, spheres, points with (x,y,z),
      plane equations with z (e.g. 2x+y-z=4), vectors with 3 components

Cost: ~$0.00005 per classification (negligible)
Latency: ~0.3-0.8s
"""

import json
import logging
import re
import time
from typing import Optional

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


CLASSIFICATION_PROMPT = """Classify this geometry question as 2d or 3d.

3d if ANY of these: points with 3 coords like A(1,2,3), z-variable in equations (x+y+z=6, plane 2x+y-z=4, 2x+y-2z=6), 3-component vectors (2,-1,2), spheres/prisms/pyramids/cones/tetrahedra/cubes/cylinders/cuboids with lengths, sphere equations with z like (x-2)²+(y-1)²+(z-3)²=25.
2d for everything else: triangles, circles, polygons with lengths/angles, AND coordinate geometry with only x/y (equations y=2x+1 or x²+y²=25, graphing, loci).

Q: "Pyramid base 8cm height 10cm" → 3d
Q: "Triangle ABC sides 3,4,5cm" → 2d
Q: "Plane 2x+y-z=4, find intersection" → 3d
Q: "Circle x²+y²=25, find tangent" → 2d
Q: "Point A(1,2,3) distance to B(4,0,1)" → 3d
Q: "Line through A(2,3) and B(6,-1)" → 2d
Q: "Sphere (x-2)²+(y-1)²+(z-3)²=25, plane z=6" → 3d
Q: "Planes x+2y-2z=6 and 2x-y+2z=9, dihedral angle" → 3d
Q: "Triangle PQR vertices P(1,0,2) Q(3,4,1) R(0,2,5)" → 3d
Q: "Cube ABCDEFGH side 4cm, find angle between diagonals" → 3d
Q: "Cylinder radius 3cm height 8cm, find shortest path" → 3d
Q: "Rectangular box 3cm by 4cm by 12cm, angle between diagonals" → 3d

Question: {question}

Answer (2d or 3d):"""


def classify_geometry_type(
    api_key,        # type: str
    question_text,  # type: str
    use_cache=True, # type: bool
):
    # type: (...) -> dict
    """Classify the geometry question type using LLM.

    Args:
        api_key: Gemini API key
        question_text: The geometry question text
        use_cache: Whether to cache results (default: True)

    Returns:
        dict with keys:
            - dimension_type: str ("2d" or "3d")
            - confidence: str ("high", "medium", "low") - based on response clarity
            - duration: float - API call duration in seconds
            - cost: float - Estimated cost in USD
            - tokens: int - Total tokens used
    """
    client = genai.Client(api_key=api_key)

    # Build prompt
    prompt = CLASSIFICATION_PROMPT.format(question=question_text[:500])  # Limit to 500 chars

    try:
        start = time.time()
        logger.info("Calling Gemini Flash for geometry type classification...")

        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt,
            config={
                "max_output_tokens": 50,   # Allow "Answer: 3d" with some padding
                "temperature": 0.0,        # Deterministic
                # No thinking_config: thinking hurts this simple binary classifier
                # (reasoning output introduces spurious 2d/3d mentions that break parsing)
            },
        )

        elapsed = time.time() - start

        # Extract text from response (handle thought_signature parts)
        raw_output = ""
        if response and hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            if (hasattr(candidate, 'content') and hasattr(candidate.content, 'parts')
                    and candidate.content.parts):
                # Extract text from all text parts (skip thought_signature)
                for part in candidate.content.parts:
                    if hasattr(part, 'text') and part.text:
                        raw_output += part.text

        if not raw_output:
            logger.error(f"API returned no text content. Response: {response}")
            raise ValueError(f"API returned empty text. Full response available but no text parts found.")

        raw_output = raw_output.strip().lower()
        usage = response.usage_metadata

        # Parse output; fall back to regex if LLM output is ambiguous
        dimension_type = parse_classification_output(raw_output)
        if dimension_type is None:
            dimension_type = fallback_classify(question_text)
            logger.warning(f"LLM output ambiguous ('{raw_output}'), using fallback: {dimension_type}")

        # Estimate cost (Gemini Flash pricing)
        input_cost = (usage.prompt_token_count / 1e6) * 0.50  # $0.50 per 1M input tokens
        output_cost = (usage.candidates_token_count / 1e6) * 3.00  # $3.00 per 1M output tokens
        total_cost = input_cost + output_cost

        # Determine confidence based on response clarity
        confidence = "high" if (dimension_type and dimension_type in raw_output) else "medium"

        logger.info(f"Classification result: {dimension_type} (confidence: {confidence}, {elapsed:.2f}s, ${total_cost:.6f})")

        return {
            "dimension_type": dimension_type,
            "confidence": confidence,
            "duration": elapsed,
            "cost": total_cost,
            "cost_hkd": total_cost * 7.8,  # Convert USD to HKD
            "tokens_used": usage.total_token_count,  # For backwards compatibility
            "tokens_input": usage.prompt_token_count,
            "tokens_output": usage.candidates_token_count,
            "tokens_total": usage.total_token_count,
            "raw_output": raw_output,
        }

    except Exception as e:
        logger.error(f"Classification failed: {e}")
        # Fallback to simple regex detection
        fallback_type = fallback_classify(question_text)
        logger.warning(f"Using fallback classification: {fallback_type}")

        return {
            "dimension_type": fallback_type,
            "confidence": "low",
            "duration": 0.0,
            "cost": 0.0,
            "tokens": 0,
            "raw_output": "fallback",
            "error": str(e),
        }


def parse_classification_output(output):
    # type: (str) -> Optional[str]
    """Parse the LLM output to extract dimension type.

    Returns "2d", "3d", or None if the output is ambiguous.

    Handles various output formats:
    - "2d" / "3d" (direct)
    - "Answer: 3d" (with prefix)
    - "The question is 2d" (inline)
    """
    output = output.lower().strip()

    # Direct match
    if output in ("2d", "3d"):
        return output

    # Single digit "3" or "2" — model truncated "3d"/"2d"
    if output.strip() == "3":
        return "3d"
    if output.strip() == "2":
        return "2d"

    # Look for "Answer:" or "Type:" prefix (chain-of-thought)
    for prefix in ["answer:", "type:", "classification:"]:
        if prefix in output:
            after_prefix = output.split(prefix)[-1].strip()
            answer_token = after_prefix.split()[0].strip() if after_prefix else ""
            if answer_token in ("2d", "3d"):
                return answer_token
            # Handle truncated digit after prefix
            if answer_token == "3":
                return "3d"
            if answer_token == "2":
                return "2d"

    # Search for standalone 3d/2d anywhere in output
    if re.search(r'\b3d\b', output):
        return "3d"
    elif re.search(r'\b2d\b', output):
        return "2d"

    # Could not parse — return None so caller can use regex fallback
    logger.warning(f"Could not parse classification output: '{output}', returning None")
    return None


def fallback_classify(question_text):
    # type: (str) -> str
    """Fallback regex-based classification if LLM call fails.

    Returns "2d" or "3d" only.
    """
    text_lower = question_text.lower()

    has_3d_coords = bool(re.search(r'\([0-9-]+\s*,\s*[0-9-]+\s*,\s*[0-9-]+\)', question_text))
    if has_3d_coords:
        return "3d"

    # z as math variable: handles z=, z-, z+, z^, standalone z, AND coefficients: 2z, 3z, (z-1)
    has_z_variable = bool(re.search(
        r'\bz\s*[-+*/=^(]'        # z followed by operator: z=, z-, z^
        r'|\bz\b'                  # standalone z word
        r'|[-+*/=(,\s]\d*z\b'     # operator/space then optional digit then z: +z, -2z, (3z
        r'|\d+z\b',                # digit immediately before z with no space: 2z, 12z
        text_lower
    ))
    if has_z_variable:
        return "3d"

    # Sphere with z in its equation
    if 'sphere' in text_lower and 'z' in text_lower:
        return "3d"

    if any(kw in text_lower for kw in ['pyramid', 'cone', 'prism', 'cuboid', 'tetrahedron',
                                        'cube', 'cylinder', 'rectangular box',
                                        'height', 'slant', 'apex']):
        return "3d"

    return "2d"


def main():
    """CLI for testing classification."""
    import argparse
    import os
    from dotenv import load_dotenv

    load_dotenv(".env")

    parser = argparse.ArgumentParser(description="Classify geometry question type")
    parser.add_argument("--question", required=True, help="Question text")
    parser.add_argument("--api-key", default=os.getenv("GEMINI_API_KEY"), help="Gemini API key")

    args = parser.parse_args()

    if not args.api_key:
        print("Error: GEMINI_API_KEY not set")
        return

    result = classify_geometry_type(args.api_key, args.question)

    print("\n" + "="*60)
    print(f"Question: {args.question[:100]}...")
    print("="*60)
    print(f"Type: {result['dimension_type']}")
    print(f"Confidence: {result['confidence']}")
    print(f"Duration: {result['duration']:.2f}s")
    print(f"Cost: ${result['cost']:.6f}")
    print(f"Tokens: {result.get('tokens_total', result.get('tokens', 0))}")
    print(f"Raw output: {result.get('raw_output', 'N/A')}")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
