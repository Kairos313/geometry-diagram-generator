#!/usr/bin/env python3
"""
Parallel pipeline test runner — 10 geometry questions (5×2D, 5×3D).

Runs all tests concurrently using ThreadPoolExecutor, with each test
writing to its own isolated output directory.

Usage:
    /usr/local/bin/python3.13 test_pipeline.py
"""

import json
import os
import sys
import time
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

# Ensure we can import pipeline modules
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from dotenv import load_dotenv
load_dotenv(str(SCRIPT_DIR / ".env"))

from generate_blueprint import generate_blueprint
from generate_code import detect_dimension, generate_render_code, execute_code, ensure_helpers

# ---------------------------------------------------------------------------
# 10 Test Questions — 5 2D, 5 3D (each a different shape)
# ---------------------------------------------------------------------------

TEST_QUESTIONS = [
    # ---- 2D Questions (expect matplotlib) ----
    {
        "id": "01_right_triangle",
        "dim": "2d",
        "question": (
            "In right triangle ABC, angle ACB = 90°. "
            "The length AC = 6 cm and BC = 8 cm. "
            "Find the length of the hypotenuse AB."
        ),
    },
    {
        "id": "02_circle_tangent",
        "dim": "2d",
        "question": (
            "A circle with center O has a radius of 5 cm. "
            "Point P is outside the circle such that OP = 13 cm. "
            "A line from P is tangent to the circle at point T. "
            "Find the length of PT."
        ),
    },
    {
        "id": "03_parallelogram",
        "dim": "2d",
        "question": (
            "In parallelogram ABCD, AB = 10 cm, AD = 6 cm, "
            "and angle DAB = 60°. "
            "Find the length of diagonal AC."
        ),
    },
    {
        "id": "04_rhombus",
        "dim": "2d",
        "question": (
            "Rhombus ABCD has diagonals AC = 10 cm and BD = 24 cm. "
            "The diagonals intersect at point O. "
            "Find the side length of the rhombus."
        ),
    },
    {
        "id": "05_trapezoid",
        "dim": "2d",
        "question": (
            "In isosceles trapezoid ABCD, AB is parallel to CD. "
            "AB = 16 cm, CD = 10 cm, and the legs AD = BC = 5 cm. "
            "Find the height of the trapezoid."
        ),
    },
    # ---- 3D Questions (expect manim) ----
    {
        "id": "06_cube",
        "dim": "3d",
        "question": (
            "A cube ABCDEFGH has side length 6 cm, where ABCD is the bottom face "
            "and EFGH is the top face with E above A, F above B, G above C, H above D. "
            "M is the midpoint of edge FG. "
            "Find the distance from vertex A to point M."
        ),
    },
    {
        "id": "07_square_pyramid",
        "dim": "3d",
        "question": (
            "Square pyramid EABCD has a square base ABCD with side 8 cm. "
            "The apex E is directly above the center of the base. "
            "The height of the pyramid is 6 cm. "
            "Find the slant edge length EA."
        ),
    },
    {
        "id": "08_triangular_prism",
        "dim": "3d",
        "question": (
            "A right triangular prism has base triangle ABC where AB = 3 cm, "
            "BC = 4 cm, and angle ABC = 90°. The prism height is 10 cm, "
            "with top vertices D above A, E above B, and F above C. "
            "Find the length of the space diagonal AF."
        ),
    },
    {
        "id": "09_tetrahedron",
        "dim": "3d",
        "question": (
            "In regular tetrahedron ABCD, every edge has length 6 cm. "
            "Point M is the midpoint of edge BC. "
            "Find the length of AM."
        ),
    },
    {
        "id": "10_cuboid",
        "dim": "3d",
        "question": (
            "Rectangular box ABCDEFGH has length AB = 12 cm, width BC = 4 cm, "
            "and height AE = 3 cm. ABCD is the bottom face and EFGH is the top face "
            "with E above A, F above B, G above C, H above D. "
            "Find the space diagonal AG."
        ),
    },
]


def generate_demo_html(results, questions, base_output_dir, overall_duration):
    # type: (list, list, str, float) -> str
    """Generate an HTML demo page showing all test results with diagrams."""
    passed = sum(1 for r in results if r.get("success"))
    question_map = {q["id"]: q for q in questions}

    cards_html = []
    current_section = None
    for r in results:
        q = question_map.get(r["id"], {})
        dim = q.get("dim", r.get("detected_dim", "?"))

        # Section dividers
        if dim == "2d" and current_section != "2d":
            current_section = "2d"
            cards_html.append('  <div class="section-label">2D Questions (matplotlib &rarr; PNG)</div>')
        elif dim == "3d" and current_section != "3d":
            current_section = "3d"
            cards_html.append('  <div class="section-label">3D Questions (manim &rarr; GIF)</div>')

        is_pass = r.get("success", False)
        dim_class = "dim-2d" if dim == "2d" else "dim-3d"
        card_class = "card" if is_pass else "card failed"
        num = r["id"].split("_")[0]
        name = " ".join(w.capitalize() for w in r["id"].split("_")[1:])

        # Image or error placeholder
        if is_pass and r.get("output_file") and Path(r["output_file"]).exists():
            rel_path = os.path.relpath(r["output_file"], base_output_dir)
            size = Path(r["output_file"]).stat().st_size
            if size > 1024 * 1024:
                size_str = "{:.1f} MB".format(size / (1024 * 1024))
            else:
                size_str = "{:.1f} KB".format(size / 1024)
            img_html = '<img src="{}" alt="{}">'.format(rel_path, name)
        else:
            size_str = "&mdash;"
            err = r.get("error", "Unknown error")
            err_short = err.split(":")[0] if ":" in err else err[:40]
            img_html = '<div class="error">{}</div>'.format(err_short)

        badge = "badge-pass" if is_pass else "badge-fail"
        badge_text = "PASS" if is_pass else "FAIL"

        question_text = q.get("question", "").replace("°", "&deg;")

        timing = ""
        if r.get("total_duration") is not None:
            timing = "{:.0f}s".format(r["total_duration"])

        card = """  <div class="{}">
    <div class="card-header">
      <div class="card-num"><span class="{}">{}</span> {} <span class="dim">{}</span></div>
      <div class="card-question">{}</div>
    </div>
    <div class="card-img">{}</div>
    <div class="card-footer"><span class="badge {}">{}</span> <span>{}</span> <span>{}</span></div>
  </div>""".format(card_class, dim_class, num, name, dim.upper(),
                   question_text, img_html, badge, badge_text, size_str, timing)
        cards_html.append(card)

    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Geometry Diagram Pipeline &mdash; Test Results</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f0f0f; color: #e0e0e0; padding: 24px; }}
  h1 {{ text-align: center; font-size: 22px; font-weight: 600; margin-bottom: 6px; color: #fff; }}
  .subtitle {{ text-align: center; font-size: 13px; color: #888; margin-bottom: 24px; }}
  .grid {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 16px; }}
  .card {{ background: #1a1a1a; border-radius: 10px; overflow: hidden; border: 1px solid #2a2a2a; display: flex; flex-direction: column; }}
  .card.failed {{ opacity: 0.5; }}
  .card-header {{ padding: 12px 14px 10px; border-bottom: 1px solid #2a2a2a; }}
  .card-num {{ font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }}
  .card-num .dim {{ font-weight: 400; color: #888; margin-left: 6px; }}
  .dim-2d {{ color: #2A9D8F; }}
  .dim-3d {{ color: #E76F51; }}
  .card-question {{ font-size: 12px; line-height: 1.5; color: #bbb; }}
  .card-img {{ flex: 1; display: flex; align-items: center; justify-content: center; background: #fff; min-height: 160px; }}
  .card-img img {{ width: 100%; height: auto; display: block; }}
  .card-img .error {{ color: #666; font-size: 12px; padding: 20px; text-align: center; background: #111; width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; min-height: 160px; }}
  .card-footer {{ padding: 8px 14px; border-top: 1px solid #2a2a2a; font-size: 11px; color: #666; display: flex; justify-content: space-between; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: 600; }}
  .badge-pass {{ background: #1a3a2a; color: #4ade80; }}
  .badge-fail {{ background: #3a1a1a; color: #f87171; }}
  .section-label {{ grid-column: 1 / -1; font-size: 13px; font-weight: 600; color: #666; text-transform: uppercase; letter-spacing: 1px; padding: 8px 0 0; border-top: 1px solid #222; margin-top: 4px; }}
</style>
</head>
<body>

<h1>Geometry Diagram Pipeline &mdash; 10 Test Questions</h1>
<p class="subtitle">2-stage AI pipeline: Gemini 3 Flash (blueprint) + Gemini 3 Flash (render code) &nbsp;|&nbsp; {passed}/{total} passed in {duration:.0f}s</p>

<div class="grid">
{cards}
</div>

</body>
</html>""".format(
        passed=passed,
        total=len(results),
        duration=overall_duration,
        cards="\n\n".join(cards_html),
    )

    html_path = os.path.join(base_output_dir, "demo.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    return html_path


def run_single_test(test, api_key, base_output_dir):
    # type: (dict, str, str) -> dict
    """Run a single pipeline test end-to-end. Returns a result dict."""
    test_id = test["id"]
    question = test["question"]
    expected_dim = test["dim"]
    output_dir = os.path.join(base_output_dir, test_id)
    os.makedirs(output_dir, exist_ok=True)

    result = {
        "id": test_id,
        "expected_dim": expected_dim,
        "detected_dim": None,
        "success": False,
        "error": None,
        "stage1_duration": None,
        "stage1_tokens": None,
        "stage2_duration": None,
        "stage2_tokens": None,
        "exec_duration": None,
        "total_duration": None,
        "output_file": None,
    }

    total_start = time.time()

    try:
        # ---- Stage 1: Blueprint ----
        print("[{}] Stage 1: Generating blueprint...".format(test_id))
        bp_result = generate_blueprint(
            api_key=api_key,
            question_text=question,
            output_dir=output_dir,
        )

        if not bp_result["success"]:
            result["error"] = "Stage 1 failed: {}".format(bp_result.get("error", "unknown"))
            result["total_duration"] = round(time.time() - total_start, 1)
            return result

        result["stage1_duration"] = round(bp_result["api_call_duration"], 1)
        result["stage1_tokens"] = bp_result["total_tokens"]
        blueprint_text = bp_result["blueprint"]

        # ---- Detect Dimension ----
        dim_type = detect_dimension(blueprint_text)
        result["detected_dim"] = dim_type

        # ---- Stage 2: Generate Code ----
        output_format = "png" if dim_type == "2d" else "gif"
        output_path = os.path.join(output_dir, "diagram.{}".format(output_format))

        print("[{}] Stage 2: Generating {} code (detected {})...".format(
            test_id, "matplotlib" if dim_type == "2d" else "manim", dim_type))

        code_result = generate_render_code(
            api_key=api_key,
            blueprint_text=blueprint_text,
            output_path=output_path,
            output_format=output_format,
            dimension_type=dim_type,
            question_text=question,
        )

        if not code_result["success"]:
            result["error"] = "Stage 2 failed: {}".format(code_result.get("error", "unknown"))
            result["total_duration"] = round(time.time() - total_start, 1)
            return result

        result["stage2_duration"] = round(code_result["api_call_duration"], 1)
        result["stage2_tokens"] = code_result["total_tokens"]

        # Write render_code.py to test's own directory
        code_path = os.path.join(output_dir, "render_code.py")
        with open(code_path, "w", encoding="utf-8") as f:
            f.write(code_result["code"])

        # ---- Stage 3: Execute Code ----
        print("[{}] Stage 3: Executing code...".format(test_id))
        exec_start = time.time()
        timeout = 300 if dim_type == "3d" else 120
        exec_result = execute_code(code_path, timeout=timeout)
        result["exec_duration"] = round(time.time() - exec_start, 1)

        # Save execution logs
        with open(os.path.join(output_dir, "exec_stdout.txt"), "w") as f:
            f.write(exec_result.get("stdout", ""))
        with open(os.path.join(output_dir, "exec_stderr.txt"), "w") as f:
            f.write(exec_result.get("stderr", ""))

        if exec_result["success"] and Path(output_path).exists():
            result["success"] = True
            result["output_file"] = output_path
            size_kb = Path(output_path).stat().st_size / 1024
            print("[{}] SUCCESS — {} ({:.1f} KB)".format(test_id, output_format.upper(), size_kb))
        else:
            # Try retry with error context
            error_ctx = exec_result.get("stderr", "")[-2000:]
            if not error_ctx:
                error_ctx = "Script ran but output file not created at: {}".format(output_path)

            print("[{}] Execution failed, retrying with error context...".format(test_id))
            code_result2 = generate_render_code(
                api_key=api_key,
                blueprint_text=blueprint_text,
                output_path=output_path,
                output_format=output_format,
                dimension_type=dim_type,
                question_text=question,
                error_context=error_ctx,
            )

            if code_result2["success"]:
                with open(code_path, "w", encoding="utf-8") as f:
                    f.write(code_result2["code"])

                exec_result2 = execute_code(code_path, timeout=timeout)

                with open(os.path.join(output_dir, "exec_stdout_retry.txt"), "w") as f:
                    f.write(exec_result2.get("stdout", ""))
                with open(os.path.join(output_dir, "exec_stderr_retry.txt"), "w") as f:
                    f.write(exec_result2.get("stderr", ""))

                if exec_result2["success"] and Path(output_path).exists():
                    result["success"] = True
                    result["output_file"] = output_path
                    size_kb = Path(output_path).stat().st_size / 1024
                    print("[{}] SUCCESS (retry) — {} ({:.1f} KB)".format(
                        test_id, output_format.upper(), size_kb))
                else:
                    result["error"] = "Execution failed (2 attempts): {}".format(
                        exec_result2.get("stderr", "")[-500:])
            else:
                result["error"] = "Retry code gen failed: {}".format(
                    code_result2.get("error", "unknown"))

    except Exception as e:
        import traceback
        result["error"] = "Exception: {}\n{}".format(str(e), traceback.format_exc()[-500:])

    result["total_duration"] = round(time.time() - total_start, 1)
    return result


def main():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not set in .env")
        sys.exit(1)

    base_output_dir = str(SCRIPT_DIR / "test_output")
    # Clean previous test results
    if Path(base_output_dir).exists():
        shutil.rmtree(base_output_dir)
    os.makedirs(base_output_dir, exist_ok=True)

    print("=" * 70)
    print("GEOMETRY PIPELINE — PARALLEL TEST RUNNER")
    print("=" * 70)
    print("Questions: {} total ({} 2D, {} 3D)".format(
        len(TEST_QUESTIONS),
        sum(1 for q in TEST_QUESTIONS if q["dim"] == "2d"),
        sum(1 for q in TEST_QUESTIONS if q["dim"] == "3d"),
    ))
    print("Output: {}".format(base_output_dir))
    max_concurrent = 3
    print("Concurrency: {} threads".format(max_concurrent))
    print("=" * 70)

    overall_start = time.time()
    results = []

    with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
        futures = {
            executor.submit(run_single_test, test, api_key, base_output_dir): test
            for test in TEST_QUESTIONS
        }

        for future in as_completed(futures):
            test = futures[future]
            try:
                result = future.result()
                results.append(result)
                status = "PASS" if result["success"] else "FAIL"
                print("\n[{}] {} — {} (total: {}s)".format(
                    result["id"], status,
                    result.get("error", "OK")[:80] if not result["success"] else "OK",
                    result["total_duration"],
                ))
            except Exception as e:
                print("\n[{}] EXCEPTION: {}".format(test["id"], e))
                results.append({
                    "id": test["id"],
                    "success": False,
                    "error": str(e),
                })

    overall_duration = round(time.time() - overall_start, 1)

    # ---- Summary ----
    results.sort(key=lambda r: r["id"])
    passed = sum(1 for r in results if r.get("success"))
    failed = len(results) - passed

    print("\n" + "=" * 70)
    print("TEST RESULTS — {}/{} passed in {}s".format(passed, len(results), overall_duration))
    print("=" * 70)

    for r in results:
        status = "PASS" if r.get("success") else "FAIL"
        dim_match = ""
        if r.get("detected_dim") and r.get("expected_dim"):
            dim_match = " [dim: expected={}, detected={}{}]".format(
                r["expected_dim"], r["detected_dim"],
                "" if r["expected_dim"] == r["detected_dim"] else " MISMATCH",
            )

        timing = ""
        if r.get("stage1_duration") is not None:
            timing = " (S1: {}s/{}tok, S2: {}s/{}tok, exec: {}s)".format(
                r.get("stage1_duration", "?"),
                r.get("stage1_tokens", "?"),
                r.get("stage2_duration", "?"),
                r.get("stage2_tokens", "?"),
                r.get("exec_duration", "?"),
            )

        print("  {} {} — {}s total{}{}".format(
            status, r["id"], r.get("total_duration", "?"), dim_match, timing,
        ))

        if not r.get("success") and r.get("error"):
            # Print first line of error
            err_line = r["error"].split("\n")[0][:100]
            print("       Error: {}".format(err_line))

    # Save JSON report
    report_path = os.path.join(base_output_dir, "test_report.json")
    with open(report_path, "w") as f:
        json.dump({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_tests": len(results),
            "passed": passed,
            "failed": failed,
            "overall_duration": overall_duration,
            "results": results,
        }, f, indent=2)
    print("\nDetailed report: {}".format(report_path))

    # Generate demo HTML
    demo_path = generate_demo_html(results, TEST_QUESTIONS, base_output_dir, overall_duration)
    print("Demo page: {}".format(demo_path))

    # List output files
    print("\nOutput files:")
    for r in results:
        if r.get("output_file") and Path(r["output_file"]).exists():
            size = Path(r["output_file"]).stat().st_size / 1024
            print("  {} — {} ({:.1f} KB)".format(r["id"], r["output_file"], size))

    print("\n" + "=" * 70)
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
