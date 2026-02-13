#!/usr/bin/env python3
"""
Compare Blueprint Generation Methods: Compact JSON vs Structured Output

Runs the same test questions with both methods and generates a comparison report.

Usage:
    python3 compare_blueprint_methods.py --test-set hkdse
    python3 compare_blueprint_methods.py --test-set hkdse --dim 2d
    python3 compare_blueprint_methods.py --num-questions 10
"""

import argparse
import asyncio
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

# Import test questions
sys.path.insert(0, str(Path(__file__).parent))
from hkdse_test_questions import HKDSE_TEST_QUESTIONS, get_questions_by_dimension
from geometry_test_questions import GEOMETRY_TEST_QUESTIONS

load_dotenv(".env")

PRICING_GEMINI = {
    "input": 0.50,   # per million tokens
    "output": 3.00,
}


@dataclass
class BlueprintTestResult:
    question_id: str
    question_name: str
    question_text: str
    success: bool = False
    duration: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    dimension: str = ""
    error: Optional[str] = None


@dataclass
class ComparisonResult:
    compact: BlueprintTestResult
    structured: BlueprintTestResult


def run_blueprint_generation(question, api_key, method="compact"):
    """
    Run blueprint generation for a single question.

    Args:
        question: Question dict
        api_key: Gemini API key
        method: "compact" or "structured"
    """
    import uuid

    if method == "compact":
        from generate_blueprint import generate_blueprint
    else:  # structured
        from generate_blueprint_structured import generate_blueprint

    result = BlueprintTestResult(
        question_id=question["id"],
        question_name=question["name"],
        question_text=question["text"],
    )

    # Create temp output directory
    run_id = f"{question['id']}_{method}_{uuid.uuid4().hex[:6]}"
    output_dir = str(Path(__file__).parent / "output" / "comparison" / run_id)
    os.makedirs(output_dir, exist_ok=True)

    try:
        # Run blueprint generation
        kwargs = {
            "api_key": api_key,
            "question_text": question["text"],
            "output_dir": output_dir,
        }

        # Add compact flag only for compact mode
        if method == "compact":
            kwargs["compact"] = True

        bp_result = generate_blueprint(**kwargs)

        if bp_result["success"]:
            result.success = True
            result.duration = bp_result["api_call_duration"]
            result.prompt_tokens = bp_result["prompt_tokens"]
            result.completion_tokens = bp_result["completion_tokens"]
            result.total_tokens = bp_result["total_tokens"]
            result.dimension = bp_result.get("dimension", "")

            # Calculate cost
            result.cost = (
                (result.prompt_tokens / 1e6) * PRICING_GEMINI["input"] +
                (result.completion_tokens / 1e6) * PRICING_GEMINI["output"]
            )
        else:
            result.error = bp_result.get("error", "Unknown error")

    except Exception as e:
        result.error = str(e)

    return result


async def run_comparison_batch(questions: List[dict], api_key: str, max_workers: int = 5):
    """Run comparison for all questions in parallel."""

    results = []
    loop = asyncio.get_event_loop()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        tasks = []

        for q in questions:
            # Create tasks for both methods
            compact_task = loop.run_in_executor(
                executor, run_blueprint_generation, q, api_key, "compact"
            )
            structured_task = loop.run_in_executor(
                executor, run_blueprint_generation, q, api_key, "structured"
            )
            tasks.append((q["id"], compact_task, structured_task))

        # Wait for all tasks
        for q_id, compact_task, structured_task in tasks:
            try:
                compact_result = await compact_task
                structured_result = await structured_task

                comparison = ComparisonResult(
                    compact=compact_result,
                    structured=structured_result
                )
                results.append(comparison)

                # Print progress
                status_compact = "✓" if compact_result.success else "✗"
                status_struct = "✓" if structured_result.success else "✗"
                print(f"[{len(results)}/{len(questions)}] {compact_result.question_name}")
                print(f"  Compact: {status_compact} {compact_result.duration:.1f}s, "
                      f"{compact_result.total_tokens} tokens, ${compact_result.cost:.4f}")
                print(f"  Structured: {status_struct} {structured_result.duration:.1f}s, "
                      f"{structured_result.total_tokens} tokens, ${structured_result.cost:.4f}")

                if not compact_result.success:
                    print(f"    Compact error: {compact_result.error[:100]}")
                if not structured_result.success:
                    print(f"    Structured error: {structured_result.error[:100]}")

            except Exception as e:
                print(f"Error processing {q_id}: {e}")

    return results


def generate_report(results: List[ComparisonResult], output_file: str):
    """Generate a comparison report."""

    # Calculate statistics
    total_questions = len(results)

    compact_success = sum(1 for r in results if r.compact.success)
    structured_success = sum(1 for r in results if r.structured.success)

    compact_total_tokens = sum(r.compact.total_tokens for r in results)
    structured_total_tokens = sum(r.structured.total_tokens for r in results)

    compact_total_cost = sum(r.compact.cost for r in results)
    structured_total_cost = sum(r.structured.cost for r in results)

    compact_avg_duration = sum(r.compact.duration for r in results) / total_questions
    structured_avg_duration = sum(r.structured.duration for r in results) / total_questions

    # Generate markdown report
    report = f"""# Blueprint Generation Method Comparison

## Test Configuration
- **Total Questions**: {total_questions}
- **Date**: {time.strftime("%Y-%m-%d %H:%M:%S")}

## Success Rate

| Method | Success | Failure | Rate |
|--------|---------|---------|------|
| Compact JSON | {compact_success} | {total_questions - compact_success} | {compact_success/total_questions*100:.1f}% |
| Structured Output | {structured_success} | {total_questions - structured_success} | {structured_success/total_questions*100:.1f}% |

## Token Usage

| Method | Total Tokens | Input Tokens | Output Tokens | Avg per Question |
|--------|--------------|--------------|---------------|------------------|
| Compact JSON | {compact_total_tokens:,} | {sum(r.compact.prompt_tokens for r in results):,} | {sum(r.compact.completion_tokens for r in results):,} | {compact_total_tokens/total_questions:.0f} |
| Structured Output | {structured_total_tokens:,} | {sum(r.structured.prompt_tokens for r in results):,} | {sum(r.structured.completion_tokens for r in results):,} | {structured_total_tokens/total_questions:.0f} |
| **Difference** | **{structured_total_tokens - compact_total_tokens:+,}** | {sum(r.structured.prompt_tokens for r in results) - sum(r.compact.prompt_tokens for r in results):+,} | {sum(r.structured.completion_tokens for r in results) - sum(r.compact.completion_tokens for r in results):+,} | {(structured_total_tokens - compact_total_tokens)/total_questions:+.0f} |

## Cost Analysis

| Method | Total Cost | Cost per Question | Cost per Successful |
|--------|------------|-------------------|---------------------|
| Compact JSON | ${compact_total_cost:.4f} | ${compact_total_cost/total_questions:.4f} | ${compact_total_cost/compact_success if compact_success > 0 else 0:.4f} |
| Structured Output | ${structured_total_cost:.4f} | ${structured_total_cost/total_questions:.4f} | ${structured_total_cost/structured_success if structured_success > 0 else 0:.4f} |
| **Difference** | **${structured_total_cost - compact_total_cost:+.4f}** | **${(structured_total_cost - compact_total_cost)/total_questions:+.4f}** | - |

## Performance

| Method | Avg Duration | Total Time |
|--------|--------------|------------|
| Compact JSON | {compact_avg_duration:.2f}s | {sum(r.compact.duration for r in results):.1f}s |
| Structured Output | {structured_avg_duration:.2f}s | {sum(r.structured.duration for r in results):.1f}s |
| **Difference** | **{structured_avg_duration - compact_avg_duration:+.2f}s** | **{sum(r.structured.duration for r in results) - sum(r.compact.duration for r in results):+.1f}s** |

## Dimension Detection Accuracy

"""

    # Compare dimension detection for successful results
    dimension_matches = 0
    dimension_mismatches = []

    for r in results:
        if r.compact.success and r.structured.success:
            if r.compact.dimension == r.structured.dimension:
                dimension_matches += 1
            else:
                dimension_mismatches.append({
                    "question": r.compact.question_name,
                    "compact": r.compact.dimension,
                    "structured": r.structured.dimension,
                })

    both_success = sum(1 for r in results if r.compact.success and r.structured.success)
    if both_success > 0:
        report += f"- **Matching dimensions**: {dimension_matches}/{both_success} ({dimension_matches/both_success*100:.1f}%)\n\n"

        if dimension_mismatches:
            report += "### Dimension Mismatches\n\n"
            for m in dimension_mismatches:
                report += f"- **{m['question']}**: Compact={m['compact']}, Structured={m['structured']}\n"

    # Detailed results table
    report += "\n## Detailed Results\n\n"
    report += "| Question | Compact | Structured | Token Diff | Cost Diff |\n"
    report += "|----------|---------|------------|------------|----------|\n"

    for r in results:
        compact_status = "✓" if r.compact.success else f"✗ {r.compact.error[:30] if r.compact.error else 'Unknown'}"
        structured_status = "✓" if r.structured.success else f"✗ {r.structured.error[:30] if r.structured.error else 'Unknown'}"
        token_diff = r.structured.total_tokens - r.compact.total_tokens
        cost_diff = r.structured.cost - r.compact.cost

        report += f"| {r.compact.question_name} | {compact_status} | {structured_status} | {token_diff:+,} | ${cost_diff:+.4f} |\n"

    # Error analysis
    compact_errors = [r.compact for r in results if not r.compact.success]
    structured_errors = [r.structured for r in results if not r.structured.success]

    if compact_errors or structured_errors:
        report += "\n## Error Analysis\n\n"

        if compact_errors:
            report += f"### Compact JSON Errors ({len(compact_errors)})\n\n"
            for e in compact_errors:
                report += f"- **{e.question_name}**: {e.error}\n"
            report += "\n"

        if structured_errors:
            report += f"### Structured Output Errors ({len(structured_errors)})\n\n"
            for e in structured_errors:
                report += f"- **{e.question_name}**: {e.error}\n"

    # Write report
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n{'='*70}")
    print(f"Comparison report saved to: {output_file}")
    print(f"{'='*70}\n")

    # Print summary to console
    print("SUMMARY:")
    print(f"  Success Rate: Compact {compact_success}/{total_questions} ({compact_success/total_questions*100:.1f}%), "
          f"Structured {structured_success}/{total_questions} ({structured_success/total_questions*100:.1f}%)")
    print(f"  Total Tokens: Compact {compact_total_tokens:,}, Structured {structured_total_tokens:,} "
          f"({structured_total_tokens - compact_total_tokens:+,})")
    print(f"  Total Cost: Compact ${compact_total_cost:.4f}, Structured ${structured_total_cost:.4f} "
          f"(${structured_total_cost - compact_total_cost:+.4f})")
    print(f"  Avg Duration: Compact {compact_avg_duration:.2f}s, Structured {structured_avg_duration:.2f}s "
          f"({structured_avg_duration - compact_avg_duration:+.2f}s)")


async def main():
    parser = argparse.ArgumentParser(
        description="Compare blueprint generation methods: Compact JSON vs Structured Output"
    )
    parser.add_argument(
        "--test-set",
        choices=["hkdse", "geometry"],
        default="hkdse",
        help="Which test set to use (default: hkdse)"
    )
    parser.add_argument(
        "--dim",
        choices=["2d", "3d"],
        default=None,
        help="Filter by dimension (optional)"
    )
    parser.add_argument(
        "--num-questions",
        type=int,
        default=None,
        help="Limit number of questions to test (optional)"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=10,
        help="Number of concurrent workers (default: 10)"
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output markdown file for report (default: auto-generated)"
    )
    args = parser.parse_args()

    # Check API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not set")
        sys.exit(1)

    # Select questions
    if args.test_set == "hkdse":
        if args.dim:
            questions = get_questions_by_dimension(args.dim)
            test_set_name = f"HKDSE {args.dim.upper()}"
        else:
            questions = HKDSE_TEST_QUESTIONS
            test_set_name = "HKDSE (all)"
    else:  # geometry
        questions = GEOMETRY_TEST_QUESTIONS
        test_set_name = "Geometry"

    if args.num_questions:
        questions = questions[:args.num_questions]
        test_set_name += f" (first {args.num_questions})"

    print(f"{'='*70}")
    print(f"Blueprint Generation Method Comparison")
    print(f"{'='*70}")
    print(f"Test set: {test_set_name}")
    print(f"Questions: {len(questions)}")
    print(f"Workers: {args.workers}")
    print(f"{'='*70}\n")

    # Run comparison
    start_time = time.time()
    results = await run_comparison_batch(questions, api_key, max_workers=args.workers)
    total_time = time.time() - start_time

    print(f"\nAll tests completed in {total_time:.1f}s\n")

    # Generate report
    if args.output:
        output_file = args.output
    else:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_file = str(Path(__file__).parent / f"blueprint_comparison_{timestamp}.md")

    generate_report(results, output_file)


if __name__ == "__main__":
    asyncio.run(main())
