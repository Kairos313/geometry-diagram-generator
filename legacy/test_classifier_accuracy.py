#!/usr/bin/env python3
"""
Test the accuracy of the classify_geometry_type API call across all test questions.
Maps coordinate_2d → 2d and coordinate_3d → 3d for comparison (classifier is 2-way).
"""
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

load_dotenv(".env")

from classify_geometry_type import classify_geometry_type
from geometry_test_questions import GEOMETRY_TEST_QUESTIONS
from hkdse_test_questions import HKDSE_TEST_QUESTIONS
from coordinate_test_questions import COORDINATE_TEST_QUESTIONS

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    print("ERROR: GEMINI_API_KEY not set")
    sys.exit(1)

def to_2way(dim):
    if dim in ("2d", "coordinate_2d"):
        return "2d"
    return "3d"

all_questions = []
for q in GEOMETRY_TEST_QUESTIONS:
    all_questions.append({"id": q["id"], "text": q["text"], "expected_4way": q["dimension"], "expected_2way": to_2way(q["dimension"])})
for q in HKDSE_TEST_QUESTIONS:
    all_questions.append({"id": q["id"], "text": q["text"], "expected_4way": q["dimension"], "expected_2way": to_2way(q["dimension"])})
for q in COORDINATE_TEST_QUESTIONS:
    all_questions.append({"id": q["id"], "text": q["text"], "expected_4way": q["dimension"], "expected_2way": to_2way(q["dimension"])})

print(f"Total questions: {len(all_questions)}")
print(f"  2d expected:  {sum(1 for q in all_questions if q['expected_2way'] == '2d')}")
print(f"  3d expected:  {sum(1 for q in all_questions if q['expected_2way'] == '3d')}")
print()

results = []

def test_one(q):
    result = classify_geometry_type(API_KEY, q["text"], use_cache=False)
    predicted = result["dimension_type"]
    correct = predicted == q["expected_2way"]
    return {
        "id": q["id"],
        "expected": q["expected_2way"],
        "expected_4way": q["expected_4way"],
        "predicted": predicted,
        "correct": correct,
        "confidence": result.get("confidence", "?"),
        "raw_output": result.get("raw_output", ""),
        "error": result.get("error"),
        "duration": result.get("duration", 0),
    }

start_all = time.time()
print("Running classifier on all questions (10 parallel workers)...")
print("-" * 70)

with ThreadPoolExecutor(max_workers=10) as executor:
    futures = {executor.submit(test_one, q): q for q in all_questions}
    done = 0
    for future in as_completed(futures):
        done += 1
        r = future.result()
        results.append(r)
        marker = "  " if r["correct"] else "X "
        print(f"{marker}[{done:2d}/{len(all_questions)}] {r['id']:30s} expected={r['expected']} got={r['predicted']} ({r['confidence']})")

total_time = time.time() - start_all

correct = [r for r in results if r["correct"]]
wrong = [r for r in results if not r["correct"]]

print()
print("=" * 70)
print(f"ACCURACY: {len(correct)}/{len(results)} = {100*len(correct)/len(results):.1f}%")
print(f"Total time: {total_time:.1f}s")
print()
for label in ["2d", "3d"]:
    group = [r for r in results if r["expected"] == label]
    gc = [r for r in group if r["correct"]]
    print(f"  {label}: {len(gc)}/{len(group)} = {100*len(gc)/len(group):.1f}%")

print()
print("Breakdown by 4-way type:")
for label in ["2d", "3d", "coordinate_2d", "coordinate_3d"]:
    group = [r for r in results if r["expected_4way"] == label]
    if not group:
        continue
    gc = [r for r in group if r["correct"]]
    print(f"  {label:20s}: {len(gc)}/{len(group)} = {100*len(gc)/len(group):.1f}%")

if wrong:
    print()
    print(f"FAILURES ({len(wrong)}):")
    for r in sorted(wrong, key=lambda x: x["id"]):
        print(f"  {r['id']:30s} expected={r['expected']} got={r['predicted']} raw='{r['raw_output'][:50]}'")
        if r.get("error"):
            print(f"    error: {r['error'][:80]}")
