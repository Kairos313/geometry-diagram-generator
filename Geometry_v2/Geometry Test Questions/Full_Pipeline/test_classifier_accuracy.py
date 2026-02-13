#!/usr/bin/env python3
"""
Test LLM Classifier Accuracy Against Expected Dimension Fields

This script samples questions from each dimension category (2d, 3d, coordinate_2d, coordinate_3d),
calls the LLM classifier for each using ASYNC/AWAIT with high concurrency, compares the output
with the expected dimension field, and generates an accuracy report.

Features:
- Async/await execution using asyncio (default: 50 concurrent requests)
- VERY fast - all 90 questions complete in ~10-20 seconds
- Real-time progress updates
- Detailed accuracy report with confusion matrix

Usage:
    python3 test_classifier_accuracy.py --sample-size 5
    python3 test_classifier_accuracy.py --sample-size all  # Test all 90 questions
    python3 test_classifier_accuracy.py --dimension coordinate_2d --sample-size 10
    python3 test_classifier_accuracy.py --sample-size all --concurrency 100  # Higher concurrency
"""

import os
import sys
import argparse
import random
from typing import Optional, List, Dict, Tuple
from collections import defaultdict
import asyncio
import time

# Import test question modules
from coordinate_test_questions import COORDINATE_TEST_QUESTIONS
from hkdse_test_questions import HKDSE_TEST_QUESTIONS
from geometry_test_questions import GEOMETRY_TEST_QUESTIONS

# Import classifier
from classify_geometry_type import classify_geometry_type


def sample_questions(
    all_questions,  # type: List[Dict]
    dimension=None,  # type: Optional[str]
    sample_size=5    # type: int
):
    # type: (...) -> List[Dict]
    """Sample questions from the question pool.

    Args:
        all_questions: List of all question dicts
        dimension: If specified, only sample from this dimension type
        sample_size: Number of questions to sample per dimension

    Returns:
        List of sampled question dicts
    """
    if dimension:
        # Filter by specific dimension
        filtered = [q for q in all_questions if q['dimension'] == dimension]
        if sample_size == 'all':
            return filtered
        return random.sample(filtered, min(sample_size, len(filtered)))

    # Sample from each dimension type
    dimension_types = set(q['dimension'] for q in all_questions)
    sampled = []

    for dim_type in sorted(dimension_types):
        dim_questions = [q for q in all_questions if q['dimension'] == dim_type]
        if sample_size == 'all':
            sampled.extend(dim_questions)
        else:
            num_to_sample = min(sample_size, len(dim_questions))
            sampled.extend(random.sample(dim_questions, num_to_sample))

    return sampled


async def classify_single_question_async(question, api_key, index, total):
    # type: (Dict, str, int, int) -> Dict
    """Classify a single question asynchronously and return result.

    Args:
        question: Question dict with 'id', 'text', 'dimension' fields
        api_key: Gemini API key
        index: Question number (1-indexed)
        total: Total number of questions

    Returns:
        Result dict with classification outcome
    """
    q_id = question['id']
    q_text = question['text']
    expected_dim = question['dimension']

    print(f"[{index}/{total}] Testing {q_id} (expected: {expected_dim})")

    try:
        # Run the synchronous classifier in an executor to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            classify_geometry_type,
            api_key,
            q_text,
            False  # use_cache=False for testing
        )

        predicted_dim = result['dimension_type']
        confidence = result.get('confidence', 'unknown')
        cost = result.get('cost_hkd', 0.0)
        tokens_used = result.get('tokens_used', 0)
        tokens_input = result.get('tokens_input', 0)
        tokens_output = result.get('tokens_output', 0)

        # Check if correct
        is_correct = (predicted_dim == expected_dim)
        status = "✓" if is_correct else "✗"

        print(f"  [{index}/{total}] {q_id}: {status} {predicted_dim} (expected: {expected_dim})")

        return {
            'id': q_id,
            'expected': expected_dim,
            'predicted': predicted_dim,
            'confidence': confidence,
            'correct': is_correct,
            'cost_hkd': cost,
            'tokens_used': tokens_used,
            'tokens_input': tokens_input,
            'tokens_output': tokens_output
        }

    except Exception as e:
        print(f"  [{index}/{total}] {q_id}: ERROR - {e}")
        return {
            'id': q_id,
            'expected': expected_dim,
            'predicted': 'ERROR',
            'confidence': 'N/A',
            'correct': False,
            'error': str(e)
        }


async def test_classifier_async(questions, api_key, concurrency=50):
    # type: (List[Dict], str, int) -> Tuple[List[Dict], Dict]
    """Test classifier on a list of questions asynchronously with high concurrency.

    Args:
        questions: List of question dicts with 'dimension' field
        api_key: Gemini API key
        concurrency: Maximum number of concurrent requests (default: 50)

    Returns:
        Tuple of (results list, summary dict)
    """
    results = []
    total_cost = 0.0
    total_tokens = 0
    total_tokens_input = 0
    total_tokens_output = 0
    correct = 0
    total = 0

    confusion_matrix = defaultdict(lambda: defaultdict(int))

    print(f"\nTesting classifier on {len(questions)} questions asynchronously...")
    print(f"Using concurrency limit: {concurrency}")
    print("=" * 80)

    start_time = time.time()

    # Create semaphore to limit concurrency
    semaphore = asyncio.Semaphore(concurrency)

    async def classify_with_semaphore(question, index):
        async with semaphore:
            return await classify_single_question_async(question, api_key, index, len(questions))

    # Create tasks for all questions
    tasks = [
        classify_with_semaphore(question, i)
        for i, question in enumerate(questions, 1)
    ]

    # Run all tasks concurrently and gather results
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results
    for result in results:
        if isinstance(result, Exception):
            print(f"  ERROR: {result}")
            continue

        # Update statistics
        total += 1
        if result.get('correct', False):
            correct += 1

        if 'cost_hkd' in result:
            total_cost += result['cost_hkd']
        if 'tokens_used' in result:
            total_tokens += result['tokens_used']
        if 'tokens_input' in result:
            total_tokens_input += result['tokens_input']
        if 'tokens_output' in result:
            total_tokens_output += result['tokens_output']

        # Update confusion matrix
        confusion_matrix[result['expected']][result['predicted']] += 1

    elapsed_time = time.time() - start_time

    # Sort results by question ID
    results = [r for r in results if not isinstance(r, Exception)]
    results.sort(key=lambda x: x['id'])

    # Calculate summary statistics
    accuracy = (correct / total * 100) if total > 0 else 0.0
    avg_cost = total_cost / total if total > 0 else 0.0
    avg_tokens = total_tokens / total if total > 0 else 0
    avg_tokens_input = total_tokens_input / total if total > 0 else 0
    avg_tokens_output = total_tokens_output / total if total > 0 else 0

    summary = {
        'total': total,
        'correct': correct,
        'wrong': total - correct,
        'accuracy_pct': accuracy,
        'total_cost_hkd': total_cost,
        'avg_cost_hkd': avg_cost,
        'total_tokens': total_tokens,
        'total_tokens_input': total_tokens_input,
        'total_tokens_output': total_tokens_output,
        'avg_tokens': avg_tokens,
        'avg_tokens_input': avg_tokens_input,
        'avg_tokens_output': avg_tokens_output,
        'elapsed_time': elapsed_time,
        'avg_time_per_question': elapsed_time / total if total > 0 else 0,
        'confusion_matrix': dict(confusion_matrix)
    }

    print(f"\n{'=' * 80}")
    print(f"Completed {total} classifications in {elapsed_time:.1f} seconds")
    print(f"Average: {elapsed_time / total:.2f} seconds per question")
    print(f"Speedup: ~{len(questions) / (elapsed_time / 2.0):.1f}x vs sequential (estimated)")

    return results, summary


def print_report(results, summary):
    # type: (List[Dict], Dict) -> None
    """Print test report to console."""
    print("\n" + "=" * 80)
    print("CLASSIFIER ACCURACY TEST REPORT")
    print("=" * 80)

    # Overall statistics
    print(f"\nOverall Accuracy: {summary['accuracy_pct']:.1f}% ({summary['correct']}/{summary['total']})")
    print(f"\nPerformance:")
    print(f"  Total Time: {summary['elapsed_time']:.1f} seconds")
    print(f"  Average Time per Question: {summary['avg_time_per_question']:.2f} seconds")
    print(f"\nCost:")
    print(f"  Total Cost: HKD ${summary['total_cost_hkd']:.6f}")
    print(f"  Average Cost per Question: HKD ${summary['avg_cost_hkd']:.6f}")
    print(f"\nTokens:")
    print(f"  Total Tokens: {summary['total_tokens']}")
    print(f"    - Input Tokens: {summary.get('total_tokens_input', 0)}")
    print(f"    - Output Tokens: {summary.get('total_tokens_output', 0)}")
    print(f"  Average Tokens per Question: {summary['avg_tokens']:.0f}")
    print(f"    - Avg Input: {summary.get('avg_tokens_input', 0):.0f}")
    print(f"    - Avg Output: {summary.get('avg_tokens_output', 0):.0f}")

    # Confusion matrix
    print("\nConfusion Matrix:")
    print("-" * 80)

    confusion = summary['confusion_matrix']
    all_dims = sorted(set(
        list(confusion.keys()) +
        [pred for preds in confusion.values() for pred in preds.keys()]
    ))

    # Header
    header_label = "Expected \\ Predicted"
    print(f"{header_label:<20}", end="")
    for dim in all_dims:
        print(f"{dim:>15}", end="")
    print()
    print("-" * 80)

    # Rows
    for expected in all_dims:
        print(f"{expected:<20}", end="")
        for predicted in all_dims:
            count = confusion.get(expected, {}).get(predicted, 0)
            if count > 0:
                print(f"{count:>15}", end="")
            else:
                print(f"{'-':>15}", end="")
        print()

    # Errors breakdown
    errors = [r for r in results if not r['correct']]
    if errors:
        print(f"\nMisclassifications ({len(errors)} total):")
        print("-" * 80)
        for err in errors:
            print(f"  {err['id']}: Expected={err['expected']}, Predicted={err['predicted']}")
    else:
        print("\n✓ No misclassifications!")

    # By-dimension accuracy
    print("\nAccuracy by Dimension:")
    print("-" * 80)
    dim_accuracy = defaultdict(lambda: {'correct': 0, 'total': 0})
    for r in results:
        dim_accuracy[r['expected']]['total'] += 1
        if r['correct']:
            dim_accuracy[r['expected']]['correct'] += 1

    for dim in sorted(dim_accuracy.keys()):
        stats = dim_accuracy[dim]
        pct = (stats['correct'] / stats['total'] * 100) if stats['total'] > 0 else 0.0
        print(f"  {dim:<20}: {pct:>5.1f}% ({stats['correct']}/{stats['total']})")


def main():
    parser = argparse.ArgumentParser(description="Test LLM classifier accuracy")
    parser.add_argument(
        '--sample-size',
        type=str,
        default='5',
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
        '--concurrency',
        type=int,
        default=50,
        help='Maximum number of concurrent requests (default: 50)'
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

    # Get API key
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable not set")
        sys.exit(1)

    # Set random seed
    random.seed(args.seed)

    # Combine all questions
    all_questions = COORDINATE_TEST_QUESTIONS + HKDSE_TEST_QUESTIONS + GEOMETRY_TEST_QUESTIONS

    print(f"Total questions available: {len(all_questions)}")
    if args.dimension:
        count = sum(1 for q in all_questions if q['dimension'] == args.dimension)
        print(f"Questions with dimension '{args.dimension}': {count}")

    # Sample questions
    questions = sample_questions(
        all_questions,
        dimension=args.dimension,
        sample_size=sample_size
    )

    if not questions:
        print("Error: No questions to test")
        sys.exit(1)

    # Run test asynchronously
    results, summary = asyncio.run(test_classifier_async(questions, api_key, concurrency=args.concurrency))

    # Print report
    print_report(results, summary)

    # Save results to file
    output_file = f"classifier_test_results_{args.dimension or 'all'}_{sample_size}.txt"
    with open(output_file, 'w') as f:
        f.write("CLASSIFIER ACCURACY TEST RESULTS\n")
        f.write("=" * 80 + "\n")
        f.write(f"Sample size: {sample_size} per dimension\n")
        f.write(f"Dimension filter: {args.dimension or 'all'}\n")
        f.write(f"Random seed: {args.seed}\n")
        f.write(f"\nAccuracy: {summary['accuracy_pct']:.1f}%\n")
        f.write(f"Total cost: HKD ${summary['total_cost_hkd']:.6f}\n")
        f.write(f"\nDetailed results:\n")
        for r in results:
            status = "✓" if r['correct'] else "✗"
            f.write(f"{status} {r['id']}: expected={r['expected']}, predicted={r['predicted']}\n")

    print(f"\nResults saved to: {output_file}")


if __name__ == "__main__":
    main()
