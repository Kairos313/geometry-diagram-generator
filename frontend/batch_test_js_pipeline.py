#!/usr/bin/env python3
"""
Batch test runner for the 3-stage JS rendering pipeline.

Runs all test questions in parallel, saves individual HTML files,
and generates a gallery page.

Usage:
    python3 batch_test_js_pipeline.py                    # All 40 questions
    python3 batch_test_js_pipeline.py --test-set hkdse   # HKDSE only (20)
    python3 batch_test_js_pipeline.py --test-set coord   # Coordinate only (20)
    python3 batch_test_js_pipeline.py --dim 2d           # 2D only
    python3 batch_test_js_pipeline.py --dim 3d           # 3D only
    python3 batch_test_js_pipeline.py --workers 10       # Limit concurrency
"""

import argparse
import json
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Optional

# Add parent dir (repo root) and frontend dir to path
_FRONTEND_DIR = Path(__file__).parent
_ROOT_DIR = _FRONTEND_DIR.parent
sys.path.insert(0, str(_ROOT_DIR))
sys.path.insert(0, str(_FRONTEND_DIR))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def load_questions(test_set=None, dim_filter=None):
    # type: (Optional[str], Optional[str]) -> list
    """Load test questions from the test question files."""
    questions = []

    if test_set in (None, "hkdse", "hkdse_new"):
        from hkdse_test_questions import HKDSE_QUESTIONS_2D, HKDSE_QUESTIONS_3D
        if test_set != "hkdse_new":
            for q in HKDSE_QUESTIONS_2D:
                q.setdefault("test_set", "hkdse")
                questions.append(q)
            for q in HKDSE_QUESTIONS_3D:
                q.setdefault("test_set", "hkdse")
                questions.append(q)

    if test_set in (None, "hkdse_new"):
        from hkdse_new_questions import HKDSE_NEW_QUESTIONS
        for q in HKDSE_NEW_QUESTIONS:
            q.setdefault("test_set", "hkdse_new")
            questions.append(q)

    if test_set in (None, "coord"):
        from coordinate_test_questions import COORDINATE_QUESTIONS_2D_ORIGINAL, COORDINATE_QUESTIONS_3D
        for q in COORDINATE_QUESTIONS_2D_ORIGINAL:
            q.setdefault("test_set", "coord")
            questions.append(q)
        for q in COORDINATE_QUESTIONS_3D:
            q.setdefault("test_set", "coord")
            questions.append(q)

    # Apply dimension filter
    if dim_filter:
        if dim_filter == "2d":
            questions = [q for q in questions if q["dimension"] in ("2d", "coordinate_2d")]
        elif dim_filter == "3d":
            questions = [q for q in questions if q["dimension"] in ("3d", "coordinate_3d")]
        else:
            questions = [q for q in questions if q["dimension"] == dim_filter]

    return questions


def run_single(question, output_dir):
    # type: (dict, str) -> dict
    """Run the full pipeline for a single question."""
    from generate_js_pipeline import generate_diagram

    qid = question["id"]
    name = question.get("name", qid)
    dim = question.get("dimension", "auto")
    text = question["text"]

    output_path = os.path.join(output_dir, qid, "diagram.html")
    notes_path = os.path.join(output_dir, qid, "notes.txt")

    logger.info("[{}] Starting ({})...".format(qid, dim))
    start = time.time()

    try:
        result = generate_diagram(
            question_text=text,
            dimension_type=dim,
            output_path=output_path,
            max_retries=1,
        )
        duration = time.time() - start

        # Save notes
        if result.get("math_notes"):
            Path(notes_path).parent.mkdir(parents=True, exist_ok=True)
            Path(notes_path).write_text(result["math_notes"], encoding="utf-8")

        return {
            "question_id": qid,
            "name": name,
            "dimension": result.get("dimension", dim),
            "test_set": question.get("test_set", ""),
            "text": text[:200],
            "success": result["success"],
            "duration": duration,
            "tokens": result.get("tokens", {}),
            "error": result.get("error"),
            "output_path": output_path,
        }

    except Exception as e:
        duration = time.time() - start
        logger.error("[{}] Exception: {}".format(qid, e))
        return {
            "question_id": qid,
            "name": name,
            "dimension": dim,
            "test_set": question.get("test_set", ""),
            "text": text[:200],
            "success": False,
            "duration": duration,
            "tokens": {},
            "error": str(e),
            "output_path": output_path,
        }


def run_batch(questions, output_dir, max_workers=40):
    # type: (list, str, int) -> list
    """Run all questions in parallel."""
    results = []
    total = len(questions)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_q = {
            executor.submit(run_single, q, output_dir): q
            for q in questions
        }

        for i, future in enumerate(as_completed(future_to_q), 1):
            q = future_to_q[future]
            try:
                result = future.result()
                status = "PASS" if result["success"] else "FAIL"
                logger.info(
                    "[{}/{}] {} {} ({:.1f}s) {}".format(
                        i, total, status, result["question_id"],
                        result["duration"],
                        "- " + result["error"] if result.get("error") else ""
                    )
                )
                results.append(result)
            except Exception as e:
                logger.error("[{}/{}] {} crashed: {}".format(i, total, q["id"], e))
                results.append({
                    "question_id": q["id"],
                    "name": q.get("name", q["id"]),
                    "dimension": q.get("dimension", "?"),
                    "test_set": q.get("test_set", ""),
                    "text": q["text"][:200],
                    "success": False,
                    "duration": 0,
                    "tokens": {},
                    "error": str(e),
                    "output_path": "",
                })

    # Sort by question ID for consistent output
    results.sort(key=lambda r: r["question_id"])
    return results


def generate_gallery(results, output_path, output_dir):
    # type: (list, str, str) -> None
    """Generate a gallery HTML page that displays all diagrams."""

    total = len(results)
    passed = sum(1 for r in results if r["success"])
    failed = total - passed
    n_2d = sum(1 for r in results if r["dimension"] in ("2d", "coordinate_2d") and r["success"])
    n_3d = sum(1 for r in results if r["dimension"] in ("3d", "coordinate_3d") and r["success"])

    cards_html = []
    for r in results:
        dim = r["dimension"].replace("coordinate_", "")
        dim_label = r["dimension"].upper().replace("_", " ")
        is_coord = "coordinate" in r.get("dimension", "")
        badge_class = "badge-3d" if dim == "3d" else "badge-2d"
        test_set = r.get("test_set", "")

        # Token/cost info
        tokens = r.get("tokens", {})
        gemini_tok = 0
        ds_tok = 0
        if isinstance(tokens, dict):
            gemini_tok = tokens.get("gemini_math", {}).get("total", 0) if isinstance(tokens.get("gemini_math"), dict) else 0
            ds_tok = tokens.get("deepseek_js", {}).get("total", 0) if isinstance(tokens.get("deepseek_js"), dict) else 0

        if r["success"]:
            # Relative path from gallery to diagram
            rel_path = os.path.relpath(r["output_path"], os.path.dirname(output_path))
            render_html = '<iframe src="{}" loading="lazy"></iframe>'.format(rel_path)
        else:
            render_html = '<div class="error-msg">FAILED: {}</div>'.format(
                (r.get("error") or "Unknown error")[:200]
            )

        card = """
    <div class="card" data-dim="{dim}" data-set="{test_set}" data-status="{status}">
      <div class="card-header">
        <div class="card-title">
          <span class="{badge_class}">{dim_label}</span>
          <strong>{name}</strong>
        </div>
        <span class="qid">{qid}</span>
      </div>
      <div class="card-question">{text}</div>
      <div class="card-render">{render_html}</div>
      <div class="card-footer">{dur:.1f}s | Gemini: {gt} tok | DeepSeek: {dt} tok</div>
    </div>""".format(
            dim=dim,
            test_set=test_set,
            status="pass" if r["success"] else "fail",
            badge_class=badge_class,
            dim_label=dim_label,
            name=r["name"],
            qid=r["question_id"],
            text=r["text"],
            render_html=render_html,
            dur=r["duration"],
            gt=gemini_tok,
            dt=ds_tok,
        )
        cards_html.append(card)

    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>JS Pipeline Batch Results</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: #f5f5f0; color: #333; }}
.header {{ background: #fff; border-bottom: 1px solid #e0e0db; padding: 20px 32px; position: sticky; top: 0; z-index: 100; }}
.header h1 {{ font-size: 22px; font-weight: 600; margin-bottom: 8px; }}
.stats {{ display: flex; gap: 16px; font-size: 14px; color: #666; margin-bottom: 12px; }}
.stats span {{ background: #f0f0eb; padding: 3px 10px; border-radius: 4px; }}
.filters {{ display: flex; gap: 6px; }}
.filters button {{ padding: 5px 14px; border: 1px solid #d0d0cb; border-radius: 4px; background: #fff; cursor: pointer; font-size: 13px; }}
.filters button:hover {{ background: #f0f0eb; }}
.filters button.active {{ background: #5b4dc7; color: #fff; border-color: #5b4dc7; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(540px, 1fr)); gap: 20px; padding: 24px 32px; }}
.card {{ background: #fff; border-radius: 8px; border: 1px solid #e0e0db; overflow: hidden; }}
.card[data-status="fail"] {{ border-color: #d85a30; }}
.card-header {{ display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; border-bottom: 1px solid #f0f0eb; }}
.card-title {{ display: flex; align-items: center; gap: 8px; }}
.badge-2d {{ background: #e8f5e9; color: #2e7d32; padding: 2px 8px; border-radius: 3px; font-size: 11px; font-weight: 600; }}
.badge-3d {{ background: #e3f2fd; color: #1565c0; padding: 2px 8px; border-radius: 3px; font-size: 11px; font-weight: 600; }}
.qid {{ font-size: 12px; color: #999; font-family: monospace; }}
.card-question {{ padding: 10px 16px; font-size: 13px; color: #555; border-bottom: 1px solid #f0f0eb; max-height: 60px; overflow: hidden; }}
.card-render {{ height: 420px; background: #fafaf8; }}
.card-render iframe {{ width: 100%; height: 100%; border: none; }}
.error-msg {{ padding: 20px; color: #d85a30; font-size: 13px; }}
.card-footer {{ padding: 8px 16px; font-size: 12px; color: #888; border-top: 1px solid #f0f0eb; }}
</style>
</head>
<body>
<div class="header">
  <h1>JS Pipeline Batch Results</h1>
  <div class="stats">
    <span>Total: {total}</span>
    <span style="color:#2e7d32">Pass: {passed}</span>
    <span style="color:#d85a30">Fail: {failed}</span>
    <span>2D: {n_2d}</span>
    <span>3D: {n_3d}</span>
  </div>
  <div class="filters">
    <button class="active" onclick="filterCards('all')">All</button>
    <button onclick="filterCards('2d')">2D</button>
    <button onclick="filterCards('3d')">3D</button>
    <button onclick="filterCards('hkdse')">HKDSE</button>
    <button onclick="filterCards('coord')">Coordinate</button>
    <button onclick="filterCards('fail')">Failed</button>
  </div>
</div>
<div class="grid">
  {cards}
</div>
<script>
function filterCards(f) {{
  document.querySelectorAll('.filters button').forEach(function(b) {{ b.classList.remove('active'); }});
  event.target.classList.add('active');
  document.querySelectorAll('.card').forEach(function(c) {{
    let show = f === 'all'
      || (f === '2d' && c.dataset.dim === '2d')
      || (f === '3d' && c.dataset.dim === '3d')
      || (f === 'hkdse' && c.dataset.set === 'hkdse')
      || (f === 'coord' && c.dataset.set === 'coord')
      || (f === 'fail' && c.dataset.status === 'fail');
    c.style.display = show ? '' : 'none';
  }});
}}
</script>
</body>
</html>""".format(
        total=total,
        passed=passed,
        failed=failed,
        n_2d=n_2d,
        n_3d=n_3d,
        cards="\n".join(cards_html),
    )

    Path(output_path).write_text(html, encoding="utf-8")
    logger.info("Gallery saved to {}".format(output_path))


def print_summary(results, wall_time):
    # type: (list, float) -> None
    """Print summary table."""
    total = len(results)
    passed = sum(1 for r in results if r["success"])
    failed = total - passed
    n_2d_pass = sum(1 for r in results if r["dimension"] in ("2d", "coordinate_2d") and r["success"])
    n_2d_total = sum(1 for r in results if r["dimension"] in ("2d", "coordinate_2d"))
    n_3d_pass = sum(1 for r in results if r["dimension"] in ("3d", "coordinate_3d") and r["success"])
    n_3d_total = sum(1 for r in results if r["dimension"] in ("3d", "coordinate_3d"))

    avg_time = sum(r["duration"] for r in results) / total if total else 0

    # Estimate cost
    total_gemini_tokens = 0
    total_ds_tokens = 0
    for r in results:
        tokens = r.get("tokens", {})
        if isinstance(tokens, dict):
            gt = tokens.get("gemini_math", {})
            dt = tokens.get("deepseek_js", {})
            if isinstance(gt, dict):
                total_gemini_tokens += gt.get("total", 0)
            if isinstance(dt, dict):
                total_ds_tokens += dt.get("total", 0)

    # Rough cost estimates
    gemini_cost = total_gemini_tokens * 0.5 / 1_000_000  # ~$0.50/M tokens
    ds_cost = total_ds_tokens * 0.4 / 1_000_000  # ~$0.40/M tokens avg
    total_cost = gemini_cost + ds_cost

    print("\n" + "=" * 50)
    print("BATCH RESULTS")
    print("=" * 50)
    print("Total: {} | Pass: {} | Fail: {}".format(total, passed, failed))
    print("2D: {}/{} | 3D: {}/{}".format(n_2d_pass, n_2d_total, n_3d_pass, n_3d_total))
    print("Wall time: {:.1f}s | Avg per diagram: {:.1f}s".format(wall_time, avg_time))
    print("Tokens: Gemini={:,} | DeepSeek={:,}".format(total_gemini_tokens, total_ds_tokens))
    print("Est. cost: ${:.4f} (Gemini: ${:.4f}, DeepSeek: ${:.4f})".format(
        total_cost, gemini_cost, ds_cost
    ))

    if failed > 0:
        print("\nFailed questions:")
        for r in results:
            if not r["success"]:
                print("  {} - {}".format(r["question_id"], r.get("error", "?")[:80]))

    print("=" * 50)


def main():
    parser = argparse.ArgumentParser(description="Batch test JS pipeline")
    parser.add_argument("--test-set", choices=["hkdse", "coord", "hkdse_new"],
                        help="Test set to run (default: all)")
    parser.add_argument("--dim", choices=["2d", "3d", "coordinate_2d", "coordinate_3d"],
                        help="Filter by dimension type")
    parser.add_argument("--workers", type=int, default=40,
                        help="Max parallel workers (default: 40)")
    _default_output = str(_FRONTEND_DIR / "output" / "batch_js")
    parser.add_argument("--output-dir", default=_default_output,
                        help="Output directory for individual diagrams")
    parser.add_argument("--gallery", default="batch_gallery_js_pipeline.html",
                        help="Gallery HTML output path")
    args = parser.parse_args()

    questions = load_questions(test_set=args.test_set, dim_filter=args.dim)
    if not questions:
        print("No questions match the filters.")
        sys.exit(1)

    print("Running {} questions with {} workers...".format(len(questions), args.workers))

    wall_start = time.time()
    results = run_batch(questions, args.output_dir, max_workers=args.workers)
    wall_time = time.time() - wall_start

    # Generate gallery
    generate_gallery(results, args.gallery, args.output_dir)

    # Save raw results as JSON
    results_path = Path(args.output_dir) / "results.json"
    results_path.parent.mkdir(parents=True, exist_ok=True)
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print_summary(results, wall_time)
    print("\nGallery: {}".format(args.gallery))
    print("Results JSON: {}".format(results_path))


if __name__ == "__main__":
    main()
