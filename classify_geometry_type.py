#!/usr/bin/env python3
"""
Lightweight LLM-based classifier to determine geometry question type.

Uses a minimal prompt (~150 tokens) with Gemini Flash to classify questions as:
- 2d: Traditional 2D geometry
- 3d: Traditional 3D geometry
- coordinate_2d: 2D with coordinate system/graphing
- coordinate_3d: 3D with coordinate system/graphing

Cost: ~$0.0001 per classification (negligible)
Latency: ~0.5-1.5s
"""

import json
import logging
import re
import time
from typing import Optional

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


CLASSIFICATION_PROMPT = """Classify geometry question as: 2d, 3d, coordinate_2d, or coordinate_3d

STEP 1: Check for z-variable or 3D coordinates (HIGHEST PRIORITY):
- Points with 3 numbers like A(1,2,3) or (x,y,z) → coordinate_3d
- Equations with z like "x+y+z=6" or "z=4" → coordinate_3d
- Sphere/plane equations with z term → coordinate_3d
- Direction vectors with 3 components like (2,-1,2) → coordinate_3d
- Parametric equations with 3 components → coordinate_3d

STEP 2: If no z-variable, check for 2D coordinates:
- Points with 2 numbers like (3,4) or A(x,y) → coordinate_2d
- Equations like "x²+y²=25" → coordinate_2d
- Words: "plot", "graph", "cartesian" → coordinate_2d

STEP 3: If no coordinates, check for 3D shapes:
- Pyramid, cone, sphere, prism with lengths/angles (NOT equations) → 3d

STEP 4: Otherwise:
- Triangle, circle, polygon with lengths/angles → 2d

EXAMPLES (learn from these):

Q: "Plane 2x+y-z=4. Find intersection."
Think: Has "z" in equation → coordinate_3d
Answer: coordinate_3d

Q: "Sphere (x-2)²+(y-1)²+(z-3)²=25"
Think: Sphere equation with z term → coordinate_3d
Answer: coordinate_3d

Q: "Point A(1,2,3) to B(4,0,1). Find distance."
Think: Points have 3 coordinates → coordinate_3d
Answer: coordinate_3d

Q: "Direction vector d=(2,-1,2)"
Think: Vector has 3 components → coordinate_3d
Answer: coordinate_3d

Q: "Circle x²+y²=9. Find center."
Think: Equation with only x,y (no z) → coordinate_2d
Answer: coordinate_2d

Q: "Line through A(2,3) and B(6,-1)"
Think: Points have 2 coordinates → coordinate_2d
Answer: coordinate_2d

Q: "Pyramid with base 8cm and height 10cm"
Think: 3D shape with measurements (no coordinates) → 3d
Answer: 3d

Q: "Triangle ABC with sides 3,4,5cm"
Think: 2D shape with measurements (no coordinates) → 2d
Answer: 2d

Now classify this question:

Question: {question}

Think step-by-step, then output ONLY the type (2d, 3d, coordinate_2d, or coordinate_3d):"""


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
            - dimension_type: str ("2d", "3d", "coordinate_2d", "coordinate_3d")
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
                "max_output_tokens": 400,  # Allow for chain-of-thought reasoning + output
                "temperature": 0.0,  # Deterministic
            },
        )

        elapsed = time.time() - start

        # Extract text from response (handle thought_signature parts)
        raw_output = ""
        if response and hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                # Extract text from all text parts (skip thought_signature)
                for part in candidate.content.parts:
                    if hasattr(part, 'text') and part.text:
                        raw_output += part.text

        if not raw_output:
            logger.error(f"API returned no text content. Response: {response}")
            raise ValueError(f"API returned empty text. Full response available but no text parts found.")

        raw_output = raw_output.strip().lower()
        usage = response.usage_metadata

        # Parse output
        dimension_type = parse_classification_output(raw_output)

        # Estimate cost (Gemini Flash pricing)
        input_cost = (usage.prompt_token_count / 1e6) * 0.50  # $0.50 per 1M input tokens
        output_cost = (usage.candidates_token_count / 1e6) * 3.00  # $3.00 per 1M output tokens
        total_cost = input_cost + output_cost

        # Determine confidence based on response clarity
        confidence = "high" if dimension_type in raw_output else "medium"

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
    # type: (str) -> str
    """Parse the LLM output to extract dimension type.

    Handles various output formats:
    - "coordinate_2d"
    - "Type: coordinate_2d"
    - "Think: ... Answer: coordinate_2d"
    - "The question is coordinate_2d"
    - "coordinate" (ambiguous, defaults to coordinate_2d)
    """
    output = output.lower().strip()

    # Direct match
    if output in ("2d", "3d", "coordinate_2d", "coordinate_3d"):
        return output

    # Look for "Answer:" or "Type:" prefix (chain-of-thought)
    for prefix in ["answer:", "type:", "classification:"]:
        if prefix in output:
            # Extract text after the prefix
            after_prefix = output.split(prefix)[-1].strip()
            # Get the first word/token after prefix
            answer_token = after_prefix.split()[0].strip() if after_prefix else ""
            if answer_token in ("2d", "3d", "coordinate_2d", "coordinate_3d"):
                return answer_token

    # Try to find dimension types anywhere in the output (prioritize coordinate_3d)
    # Search in order of specificity to avoid false matches
    if "coordinate_3d" in output or "coordinate 3d" in output:
        return "coordinate_3d"
    elif "coordinate_2d" in output or "coordinate 2d" in output:
        return "coordinate_2d"
    elif output.startswith("coordinate"):
        # If just "coordinate" or "coordinate_", assume coordinate_2d (most common)
        logger.info(f"Got ambiguous 'coordinate' output, defaulting to coordinate_2d")
        return "coordinate_2d"

    # Look for standalone 3d/2d (but be careful not to match "coordinate_2d" partially)
    # Check for word boundaries
    import re
    if re.search(r'\b3d\b', output):
        return "3d"
    elif re.search(r'\b2d\b', output):
        return "2d"

    # Default fallback
    logger.warning(f"Could not parse classification output: {output}, defaulting to 2d")
    return "2d"


def fallback_classify(question_text):
    # type: (str) -> str
    """Fallback regex-based classification if LLM call fails."""
    text_lower = question_text.lower()

    # Check for coordinate mentions
    has_2d_coords = bool(re.search(r'\([0-9-]+\s*,\s*[0-9-]+\)', question_text))
    has_3d_coords = bool(re.search(r'\([0-9-]+\s*,\s*[0-9-]+\s*,\s*[0-9-]+\)', question_text))
    has_graphing = any(kw in text_lower for kw in ['plot', 'graph', 'coordinate', 'axis', 'cartesian'])

    if has_3d_coords or ('plot' in text_lower and 'z' in text_lower):
        return "coordinate_3d"
    elif has_2d_coords or has_graphing:
        return "coordinate_2d"
    elif any(kw in text_lower for kw in ['pyramid', 'cone', 'sphere', 'prism', 'height', 'slant', 'apex', 'vertex']):
        return "3d"
    else:
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
    print(f"Tokens: {result['tokens']}")
    print(f"Raw output: {result.get('raw_output', 'N/A')}")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
