#!/usr/bin/env python3
"""
Test Blueprint Generation with Individual Prompts

This script tests the 4 specialized blueprint generation prompts by:
1. Sampling questions from each dimension type
2. Generating blueprints using the appropriate specialized prompt
3. Validating JSON structure and key fields
4. Saving results for inspection

Usage:
    python3 test_blueprint_generation.py --sample-size 2
    python3 test_blueprint_generation.py --dimension coordinate_3d --sample-size 3
    python3 test_blueprint_generation.py --sample-size all  # Test all questions (slow!)
"""

import os
import sys
import argparse
import json
import time
from typing import Optional, List, Dict
from dotenv import load_dotenv

# Import test question modules
from coordinate_test_questions import COORDINATE_TEST_QUESTIONS
from hkdse_test_questions import HKDSE_TEST_QUESTIONS
from geometry_test_questions import GEOMETRY_TEST_QUESTIONS

# Import compact prompt
from diagram_prompts import Question_to_Blueprint_Compact

# Import Gemini client
from google import genai
from google.genai import types


def sample_questions_by_dimension(all_questions, dimension=None, sample_size=2):
    # type: (List[Dict], Optional[str], int) -> Dict[str, List[Dict]]
    """Sample questions organized by dimension type.

    Args:
        all_questions: List of all question dicts
        dimension: If specified, only sample from this dimension type
        sample_size: Number of questions to sample per dimension

    Returns:
        Dict mapping dimension type to list of sampled questions
    """
    import random

    # Group questions by dimension
    by_dimension = {
        "2d": [],
        "3d": [],
        "coordinate_2d": [],
        "coordinate_3d": []
    }

    for q in all_questions:
        dim = q.get("dimension")
        if dim in by_dimension:
            by_dimension[dim].append(q)

    # Sample from each dimension
    sampled = {}

    if dimension:
        # Only sample from specified dimension
        if dimension not in by_dimension:
            raise ValueError(f"Unknown dimension: {dimension}")

        questions = by_dimension[dimension]
        if sample_size == "all":
            sampled[dimension] = questions
        else:
            sampled[dimension] = random.sample(questions, min(sample_size, len(questions)))
    else:
        # Sample from all dimensions
        for dim, questions in by_dimension.items():
            if not questions:
                continue

            if sample_size == "all":
                sampled[dim] = questions
            else:
                sampled[dim] = random.sample(questions, min(sample_size, len(questions)))

    return sampled


def generate_blueprint(api_key, question_text, dimension_type):
    # type: (str, str, str) -> Dict
    """Generate blueprint JSON using the appropriate specialized prompt.

    Args:
        api_key: Gemini API key
        question_text: The geometry question text
        dimension_type: One of "2d", "3d", "coordinate_2d", "coordinate_3d"

    Returns:
        Dict with keys:
            - blueprint: Parsed JSON blueprint (or None if failed)
            - raw_output: Raw LLM output text
            - duration: API call duration in seconds
            - tokens_used: Total tokens used
            - tokens_input: Input tokens
            - tokens_output: Output tokens
            - cost_hkd: Estimated cost in HKD
            - error: Error message (if any)
    """
    client = genai.Client(api_key=api_key)

    # Use the compact prompt for all dimension types
    full_prompt = Question_to_Blueprint_Compact + "\n\n## Question:\n\n" + question_text

    try:
        start = time.time()

        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=full_prompt,
            config={
                "max_output_tokens": 8192,  # Large output for JSON blueprint
                "temperature": 0.0,  # Deterministic
                "response_mime_type": "application/json",  # Request JSON output
            },
        )

        elapsed = time.time() - start

        # Extract text from response
        raw_output = ""
        if response and hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                for part in candidate.content.parts:
                    if hasattr(part, 'text') and part.text:
                        raw_output += part.text

        if not raw_output:
            return {
                "blueprint": None,
                "raw_output": "",
                "duration": elapsed,
                "tokens_used": 0,
                "tokens_input": 0,
                "tokens_output": 0,
                "cost_hkd": 0.0,
                "error": "API returned empty text",
                "finish_reason": "EMPTY_RESPONSE"
            }

        raw_output = raw_output.strip()
        usage = response.usage_metadata

        # Check finish reason to understand why generation stopped
        finish_reason = None
        if response and hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, 'finish_reason'):
                finish_reason = str(candidate.finish_reason)

        # Try to parse JSON
        try:
            # Remove markdown code blocks if present
            if raw_output.startswith("```"):
                lines = raw_output.split("\n")
                # Remove first and last lines (```json and ```)
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                raw_output = "\n".join(lines)

            blueprint = json.loads(raw_output)
        except json.JSONDecodeError as e:
            blueprint = None
            error = f"JSON parse error: {e}"
        else:
            error = None

        # Calculate cost
        input_cost = (usage.prompt_token_count / 1e6) * 0.50  # $0.50 per 1M input tokens
        output_cost = (usage.candidates_token_count / 1e6) * 3.00  # $3.00 per 1M output tokens
        total_cost = input_cost + output_cost

        return {
            "blueprint": blueprint,
            "raw_output": raw_output,
            "duration": elapsed,
            "tokens_used": usage.total_token_count,
            "tokens_input": usage.prompt_token_count,
            "tokens_output": usage.candidates_token_count,
            "cost_hkd": total_cost * 7.8,
            "error": error,
            "finish_reason": finish_reason
        }

    except Exception as e:
        return {
            "blueprint": None,
            "raw_output": "",
            "duration": 0.0,
            "tokens_used": 0,
            "tokens_input": 0,
            "tokens_output": 0,
            "cost_hkd": 0.0,
            "error": str(e),
            "finish_reason": "EXCEPTION"
        }


def validate_blueprint(blueprint, dimension_type):
    # type: (Dict, str) -> List[str]
    """Validate blueprint structure and return list of issues found.

    Args:
        blueprint: Parsed blueprint JSON
        dimension_type: Expected dimension type

    Returns:
        List of validation error/warning messages (empty if valid)
    """
    issues = []

    if not blueprint:
        return ["Blueprint is None or empty"]

    # Check required fields
    required_fields = ["dimension", "points", "given", "asked"]
    for field in required_fields:
        if field not in blueprint:
            issues.append(f"Missing required field: {field}")

    # Check dimension matches
    if "dimension" in blueprint:
        actual_dim = blueprint["dimension"]
        # For coordinate types, just check 2d/3d matches
        expected_base = "2d" if "2d" in dimension_type else "3d"
        actual_base = actual_dim

        if actual_base != expected_base:
            issues.append(f"Dimension mismatch: expected {dimension_type}, got {actual_dim}")

    # Check axes field for coordinate geometry
    if "coordinate" in dimension_type:
        if "axes" not in blueprint:
            issues.append("Missing 'axes' field for coordinate geometry")
        elif blueprint.get("axes") != True:
            issues.append(f"Expected axes=true for coordinate geometry, got {blueprint.get('axes')}")
    else:
        if "axes" in blueprint and blueprint.get("axes") == True:
            issues.append("Traditional geometry should have axes=false")

    # Check coordinate_range for coordinate geometry
    if "coordinate" in dimension_type:
        if "coordinate_range" not in blueprint:
            issues.append("Missing 'coordinate_range' field for coordinate geometry")

    # Check points structure
    if "points" in blueprint:
        points = blueprint["points"]
        if not isinstance(points, dict):
            issues.append("'points' should be a dict")
        else:
            for point_name, coords in points.items():
                if not isinstance(coords, list):
                    issues.append(f"Point {point_name} coordinates should be a list")
                elif len(coords) != 3:
                    issues.append(f"Point {point_name} should have 3 coordinates, got {len(coords)}")

    return issues


def main():
    parser = argparse.ArgumentParser(description="Test blueprint generation with individual prompts")
    parser.add_argument(
        '--sample-size',
        type=str,
        default='2',
        help='Number of questions to sample per dimension (or "all" for all questions)'
    )
    parser.add_argument(
        '--dimension',
        type=str,
        default=None,
        choices=['2d', '3d', 'coordinate_2d', 'coordinate_3d'],
        help='Test only this dimension type'
    )
    parser.add_argument(
        '--seed',
        type=int,
        default=42,
        help='Random seed for sampling'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='blueprint_test_output',
        help='Directory to save blueprint JSON files'
    )

    args = parser.parse_args()

    # Parse sample size
    if args.sample_size.lower() == 'all':
        sample_size = 'all'
    else:
        try:
            sample_size = int(args.sample_size)
        except ValueError:
            print(f"Error: sample-size must be a number or 'all'")
            sys.exit(1)

    # Load environment and get API key
    load_dotenv(".env")
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable not set")
        sys.exit(1)

    # Set random seed
    import random
    random.seed(args.seed)

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    # Combine all questions
    all_questions = COORDINATE_TEST_QUESTIONS + HKDSE_TEST_QUESTIONS + GEOMETRY_TEST_QUESTIONS

    print(f"Total questions available: {len(all_questions)}")
    print(f"Sample size: {sample_size} per dimension")
    print(f"Output directory: {args.output_dir}")
    print()

    # Sample questions by dimension
    sampled = sample_questions_by_dimension(all_questions, args.dimension, sample_size)

    total_questions = sum(len(questions) for questions in sampled.values())
    print(f"Testing {total_questions} questions across {len(sampled)} dimension types")
    print("=" * 80)
    print()

    # Generate blueprints
    results = []
    total_cost = 0.0
    total_tokens = 0
    successful = 0
    failed = 0

    for dimension_type, questions in sorted(sampled.items()):
        print(f"\n{'=' * 80}")
        print(f"DIMENSION: {dimension_type.upper()} ({len(questions)} questions)")
        print(f"{'=' * 80}\n")

        for i, question in enumerate(questions, 1):
            q_id = question['id']
            q_text = question['text']

            print(f"[{i}/{len(questions)}] Generating blueprint for {q_id}...")

            # Generate blueprint
            result = generate_blueprint(api_key, q_text, dimension_type)

            # Validate blueprint
            issues = []
            if result["blueprint"]:
                issues = validate_blueprint(result["blueprint"], dimension_type)

            # Update statistics
            total_cost += result["cost_hkd"]
            total_tokens += result["tokens_used"]

            if result["error"] or issues:
                failed += 1
                status = "✗ FAILED"
            else:
                successful += 1
                status = "✓ SUCCESS"

            # Save result
            result_data = {
                "question_id": q_id,
                "question_text": q_text,
                "dimension_type": dimension_type,
                "blueprint": result["blueprint"],
                "raw_output": result["raw_output"],
                "validation_issues": issues,
                "error": result["error"],
                "duration": result["duration"],
                "tokens_input": result["tokens_input"],
                "tokens_output": result["tokens_output"],
                "cost_hkd": result["cost_hkd"],
                "finish_reason": result.get("finish_reason")
            }
            results.append(result_data)

            # Save to individual file
            output_file = os.path.join(args.output_dir, f"{q_id}_blueprint.json")
            with open(output_file, 'w') as f:
                json.dump(result_data, f, indent=2)

            # Print status
            print(f"  {status}")
            print(f"  Duration: {result['duration']:.2f}s")
            print(f"  Tokens: {result['tokens_used']} (input: {result['tokens_input']}, output: {result['tokens_output']})")
            print(f"  Cost: HKD ${result['cost_hkd']:.6f}")

            if result["error"]:
                print(f"  ERROR: {result['error']}")
                if result.get("finish_reason"):
                    print(f"  FINISH REASON: {result['finish_reason']}")

            if issues:
                print(f"  VALIDATION ISSUES:")
                for issue in issues:
                    print(f"    - {issue}")

            print()

    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"\nTotal questions tested: {total_questions}")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")
    print(f"  Success rate: {(successful / total_questions * 100) if total_questions > 0 else 0:.1f}%")
    print(f"\nTotal cost: HKD ${total_cost:.6f}")
    print(f"Average cost per question: HKD ${(total_cost / total_questions) if total_questions > 0 else 0:.6f}")
    print(f"\nTotal tokens: {total_tokens}")
    print(f"Average tokens per question: {(total_tokens / total_questions) if total_questions > 0 else 0:.0f}")

    # Save summary
    summary_file = os.path.join(args.output_dir, "_summary.json")
    summary = {
        "total_questions": total_questions,
        "successful": successful,
        "failed": failed,
        "total_cost_hkd": total_cost,
        "total_tokens": total_tokens,
        "results": results
    }
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"\nResults saved to: {args.output_dir}/")
    print(f"Summary: {summary_file}")
    print()


if __name__ == "__main__":
    main()
